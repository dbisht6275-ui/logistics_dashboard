import streamlit as st
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import Counter
import runpy
import threading
import time
import uuid
from services.login import login_page
from services.roles import get_allowed_menu, get_allowed_reports, clear_role_cache

from pages.Home.overview_tab import show_overview
from pages.Home.PNL_Analysis import show_pnl_dashboard
from pages.Home.Net_Profit_Analysis import show_net_profit_dashboard
from pages.Home.comparison_tab import show_comparison
from pages.Home.Customer_Analysis import show_CustomerAnalysis

from pages.Home.Outstanding_Analysis import show_OutstandingAnalysis
from pages.Home.Monthly_Trend_EDD import show_monthly_trend_edd
from pages.Home.Stock_Operations import show_stock_operations
from pages.IT.zone_booking_turnover import show_ZoneBookingTurnover
from pages.IT.Bangladesh_Delivery_Turnover import show_bangladesh_delivery_turnover
from pages.IT.BookingSummaryTurnover import show_booking_summary_turnover
from pages.IT.ZoneWiseDeliveryTurnover import show_zone_wise_delivery_turnover
from pages.IT.BranchWiseDeliveryTurnover import show_branch_wise_delivery_turnover
from pages.IT.DeliverySummaryTurnover import show_delivery_summary_turnover
from pages.IT.BranchWiseBookingTurnover import show_branch_wise_booking_turnover
from pages.IT.BookingWeightSummaryTurnover import show_booking_weight_summary_turnover

from pages.Accounts.GrCostingHeadWise import show_GrCostingHeadWise
from pages.Admin.user_management import show_UserManagement


st.set_page_config(
    page_title="Sugam Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ✅ FIX: Import missing functions
try:
    from pages.IT.service_analysis import show_service_level
except ImportError:
    def show_service_level():
        st.warning("🚛 Service Analysis page not found. Please create pages/IT/service_analysis.py")


# ============================================================
# LIVE USAGE ANALYTICS - NO DATABASE
# ============================================================
# This store lives only in the current Streamlit/AWS Python process.
# It is intentionally NOT written to SQL/MySQL or any external database.
# Counts reset whenever the app process restarts/redeploys.
APP_TZ = ZoneInfo("Asia/Kolkata")
ACTIVE_WINDOW_SECONDS = 15 * 60  # Keep aligned with your app's inactivity/logout window.


@st.cache_resource(show_spinner=False)
def get_usage_store():
    return {
        "lock": threading.RLock(),
        "sessions": {},
        "page_opens": Counter(),
        "page_users": {},
        "events": [],
        "started_at": datetime.now(APP_TZ),
    }


def _usage_session_id():
    if "_usage_session_id" not in st.session_state:
        st.session_state["_usage_session_id"] = uuid.uuid4().hex
    return st.session_state["_usage_session_id"]


def _usage_employee_key():
    employee_id = str(st.session_state.get("employee_id", "")).strip()
    username = str(st.session_state.get("username", "")).strip()
    employee_name = str(st.session_state.get("employee_name", "")).strip()
    return employee_id or username or employee_name or _usage_session_id()


def _cleanup_stale_usage_sessions(store, now_ts):
    stale_ids = [
        sid
        for sid, info in store["sessions"].items()
        if now_ts - info.get("last_seen", 0) > ACTIVE_WINDOW_SECONDS
    ]
    for sid in stale_ids:
        store["sessions"].pop(sid, None)


def track_usage(page_name, count_open=True):
    """Mark this Streamlit session active and optionally count a real page change."""
    store = get_usage_store()
    now_ts = time.time()
    sid = _usage_session_id()
    employee_key = _usage_employee_key()

    employee_name = (
        st.session_state.get("employee_name")
        or st.session_state.get("username")
        or f"Employee {st.session_state.get('employee_id', '')}"
    )

    with store["lock"]:
        _cleanup_stale_usage_sessions(store, now_ts)
        store["sessions"][sid] = {
            "session_id": sid,
            "employee_key": employee_key,
            "employee_id": st.session_state.get("employee_id", "-"),
            "employee_name": str(employee_name),
            "role": str(st.session_state.get("role", "viewer")).title(),
            "page": page_name,
            "last_seen": now_ts,
        }

        # Count only when the user actually changes page/report.
        previous_page = st.session_state.get("_usage_last_page")
        is_new_page = previous_page != page_name
        should_count = count_open and is_new_page and page_name != "📊 Usage Analytics"

        if should_count:
            store["page_opens"][page_name] += 1
            store["page_users"].setdefault(page_name, set()).add(employee_key)
            store["events"].append({
                "time": now_ts,
                "employee_name": str(employee_name),
                "employee_id": st.session_state.get("employee_id", "-"),
                "page": page_name,
            })
            # Keep memory bounded.
            if len(store["events"]) > 500:
                del store["events"][:-500]

    st.session_state["_usage_last_page"] = page_name


def unregister_usage_session():
    sid = st.session_state.get("_usage_session_id")
    if not sid:
        return
    store = get_usage_store()
    with store["lock"]:
        store["sessions"].pop(sid, None)


def _ago_text(seconds):
    seconds = max(0, int(seconds))
    if seconds < 15:
        return "Just now"
    if seconds < 60:
        return f"{seconds} sec ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    return f"{hours} hr ago"


def get_usage_snapshot():
    store = get_usage_store()
    now_ts = time.time()

    with store["lock"]:
        _cleanup_stale_usage_sessions(store, now_ts)
        sessions = [dict(v) for v in store["sessions"].values()]
        page_opens = dict(store["page_opens"])
        page_users = {k: len(v) for k, v in store["page_users"].items()}
        events = [dict(e) for e in store["events"][-25:]]
        started_at = store["started_at"]

    # One row per employee, even if the same employee has multiple tabs/sessions.
    active_by_employee = {}
    for session in sessions:
        key = session["employee_key"]
        if key not in active_by_employee or session["last_seen"] > active_by_employee[key]["last_seen"]:
            active_by_employee[key] = session

    active_rows = []
    for session in sorted(active_by_employee.values(), key=lambda x: x["last_seen"], reverse=True):
        active_rows.append({
            "Employee": session["employee_name"],
            "Employee ID": session["employee_id"],
            "Role": session["role"],
            "Current Dashboard": session["page"],
            "Last Active": _ago_text(now_ts - session["last_seen"]),
        })

    usage_rows = [
        {
            "Dashboard / Report": page,
            "Opens": opens,
            "Unique Users": page_users.get(page, 0),
        }
        for page, opens in sorted(page_opens.items(), key=lambda item: item[1], reverse=True)
    ]

    recent_rows = []
    for event in reversed(events):
        event_dt = datetime.fromtimestamp(event["time"], APP_TZ)
        recent_rows.append({
            "Time": event_dt.strftime("%d %b %I:%M:%S %p"),
            "Employee": event["employee_name"],
            "Employee ID": event["employee_id"],
            "Opened": event["page"],
        })

    return {
        "active_users": len(active_by_employee),
        "active_sessions": len(sessions),
        "active_rows": active_rows,
        "usage_rows": usage_rows,
        "recent_rows": recent_rows,
        "total_opens": sum(page_opens.values()),
        "most_used": usage_rows[0]["Dashboard / Report"] if usage_rows else "-",
        "most_used_opens": usage_rows[0]["Opens"] if usage_rows else 0,
        "started_at": started_at,
    }


def _render_usage_live_panel():
    # Keep the admin's own session active while this live panel refreshes.
    track_usage("📊 Usage Analytics", count_open=False)
    snapshot = get_usage_snapshot()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 Active Users Now", snapshot["active_users"])
    c2.metric("🖥️ Active Sessions", snapshot["active_sessions"])
    c3.metric(
        "🏆 Most Used Dashboard",
        snapshot["most_used"].replace("📄 Reports › ", "").replace("📊 ", ""),
        f'{snapshot["most_used_opens"]} opens' if snapshot["most_used_opens"] else None,
    )
    c4.metric("📈 Total Page Opens", snapshot["total_opens"])

    st.markdown("### Active Users")
    if snapshot["active_rows"]:
        st.dataframe(
            snapshot["active_rows"],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No active users detected right now.")

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown("### Dashboard Usage")
        if snapshot["usage_rows"]:
            st.dataframe(
                snapshot["usage_rows"],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Usage will start appearing after users open dashboards.")

    with right:
        st.markdown("### Recent Activity")
        if snapshot["recent_rows"]:
            st.dataframe(
                snapshot["recent_rows"],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No activity has been recorded in this app process yet.")

    st.caption(
        "Live tracking uses application memory only — no database writes. "
        f"Active means activity within the last {ACTIVE_WINDOW_SECONDS // 60} minutes. "
        f"Tracking started {snapshot['started_at'].strftime('%d %b %Y %I:%M %p')} IST and resets after an app restart/redeploy."
    )


def show_usage_analytics():
    st.markdown(
        """
        <style>
        .usage-analytics-title {
            margin-bottom: .15rem;
            font-size: 1.75rem;
            font-weight: 800;
            color: #0f2f63;
        }
        .usage-analytics-subtitle {
            margin-bottom: 1rem;
            color: #64748b;
            font-size: .92rem;
        }
        </style>
        <div class="usage-analytics-title">📊 Usage Analytics</div>
        <div class="usage-analytics-subtitle">
            Live user activity and dashboard popularity without changing your database.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Streamlit fragments provide a lightweight live refresh on newer versions.
    # Fallback keeps the page fully usable on older Streamlit versions.
    if hasattr(st, "fragment"):
        @st.fragment(run_every="10s")
        def _live_usage_fragment():
            _render_usage_live_panel()

        _live_usage_fragment()
    else:
        if st.button("↻ Refresh Live Data", key="usage_manual_refresh"):
            st.rerun()
        _render_usage_live_panel()


def show_tariff_rate_dashboard():
    app_directory = Path(__file__).resolve().parent

    dashboard_file = (
        app_directory
        / "pages"
        / "Home"
        / "tariff_rate_dashboard.py"
    )

    if not dashboard_file.is_file():
        st.error(
            f"Tariff dashboard not found at: {dashboard_file}"
        )
        return

    runpy.run_path(
        str(dashboard_file),
        run_name="tariff_rate_dashboard",
    )


# =========================
# Sidebar styling (professional / enterprise theme)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ============================================================
   OPTION 3 - HOVER SIDEBAR (FIXED)
   - Resting state: clean 72px icon rail
   - Hover state: full 242px sidebar
   - No blank space above SUGAM
   - No native Streamlit radio circles / collapse control
   - Bottom cards and action buttons stay hidden in icon rail
   ============================================================ */

[data-testid="stHeader"] {
    height: 2.1rem;
    background: transparent;
}
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stDecoration"] { display: none; }
.main .block-container {
    padding-top: 1.05rem !important;
    width: 100% !important;
    max-width: 100% !important;
}

/* Sidebar shell. */
[data-testid="stSidebar"] {
    width: 72px !important;
    min-width: 72px !important;
    max-width: 72px !important;
    flex: 0 0 72px !important;
    background: linear-gradient(180deg, #123568 0%, #0b2a58 58%, #08244d 100%);
    border-right: 1px solid rgba(7, 28, 63, .45);
    box-shadow: 4px 0 14px rgba(15, 42, 82, .12);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    overflow: hidden !important;
    transition: width .14s ease, min-width .14s ease, max-width .14s ease, flex-basis .14s ease !important;
    z-index: 9999 !important;
}

[data-testid="stSidebar"]:hover {
    width: 242px !important;
    min-width: 242px !important;
    max-width: 242px !important;
    flex: 0 0 242px !important;
    overflow: hidden !important;
}

/* Remove ALL Streamlit sidebar header space and native hide/unhide controls. */
[data-testid="stSidebarHeader"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}

[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebar"] [data-testid="stSidebarContent"],
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"],
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding-left: 8px !important;
    padding-right: 8px !important;
    padding-bottom: 10px !important;
    overflow-x: hidden !important;
}

[data-testid="stSidebar"]:hover [data-testid="stSidebarContent"],
[data-testid="stSidebar"]:hover [data-testid="stSidebarUserContent"] {
    padding-left: 12px !important;
    padding-right: 12px !important;
}

[data-testid="stSidebar"] * { box-sizing: border-box; }

/* Keep the dashboard using all remaining width. */
[data-testid="stAppViewContainer"] > .main,
[data-testid="stAppViewContainer"] main,
section.main {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    margin-left: 0 !important;
}
[data-testid="stAppViewContainer"] .main .block-container {
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}

/* ---------------- Brand ---------------- */
.sugam-logo-wrap {
    height: 58px;
    min-height: 58px;
    margin: 0 -8px 8px;
    padding: 0 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: rgba(5, 28, 63, .36);
    border-bottom: 1px solid rgba(255,255,255,.10);
    white-space: nowrap;
    overflow: hidden;
}

[data-testid="stSidebar"]:hover .sugam-logo-wrap {
    margin-left: -12px;
    margin-right: -12px;
    padding: 0 15px;
    justify-content: flex-start;
}

.sugam-logo-mark {
    position: relative;
    width: 35px;
    height: 31px;
    min-width: 35px;
    flex: 0 0 35px;
}
.sugam-logo-mark::before,
.sugam-logo-mark::after {
    content: "";
    position: absolute;
    left: 2px;
    width: 30px;
    height: 9px;
    border-radius: 3px 8px 3px 8px;
    background: linear-gradient(90deg, #ef233c, #d90429);
    transform: skewX(-28deg) rotate(-12deg);
    box-shadow: 0 2px 5px rgba(217,4,41,.24);
}
.sugam-logo-mark::before { top: 4px; }
.sugam-logo-mark::after { top: 17px; left: 6px; width: 25px; }

.sugam-logo-copy {
    display: none;
    min-width: 0;
    line-height: 1;
}
[data-testid="stSidebar"]:hover .sugam-logo-copy {
    display: block;
}
.sugam-logo-name {
    color: #ffffff;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 1.5px;
}

/* ---------------- Navigation ---------------- */
.sugam-nav-label {
    display: none;
}
[data-testid="stSidebar"]:hover .sugam-nav-label {
    display: block;
    margin: 10px 7px 6px;
    color: #91a9c9;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    white-space: nowrap;
}

[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 5px !important;
}

[data-testid="stSidebar"] div[role="radiogroup"] label {
    min-height: 44px !important;
    width: 52px !important;
    margin: 0 auto !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    border: 1px solid transparent !important;
    border-radius: 10px !important;
    background: transparent !important;
    overflow: hidden !important;
    white-space: nowrap !important;
}

[data-testid="stSidebar"]:hover div[role="radiogroup"] label {
    width: 100% !important;
    min-height: 39px !important;
    margin: 0 !important;
    padding: 8px 10px !important;
    justify-content: flex-start !important;
}

/* Hide every native radio circle across Streamlit DOM variants. */
[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
[data-testid="stSidebar"] div[role="radiogroup"] label > div:has(input[type="radio"]),
[data-testid="stSidebar"] div[role="radiogroup"] label [data-baseweb="radio"] > div:first-child,
[data-testid="stSidebar"] div[role="radiogroup"] label [role="radio"] > div:first-child,
[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child:not([data-testid="stMarkdownContainer"]) {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(255,255,255,.075) !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(180deg, #2d82fb 0%, #1761d2 100%) !important;
    border-color: rgba(123,184,255,.36) !important;
    box-shadow: 0 5px 12px rgba(3, 35, 83, .28), inset 0 1px 0 rgba(255,255,255,.15) !important;
}

/* In rail mode the text itself is clipped to the emoji icon. */
[data-testid="stSidebar"] div[role="radiogroup"] label p {
    display: block !important;
    width: 25px !important;
    max-width: 25px !important;
    margin: 0 !important;
    padding: 0 !important;
    color: #e7eff9 !important;
    font-size: 18px !important;
    font-weight: 500 !important;
    line-height: 1.05 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: clip !important;
}

[data-testid="stSidebar"]:hover div[role="radiogroup"] label p {
    width: auto !important;
    max-width: none !important;
    color: #d9e5f4 !important;
    font-size: 12px !important;
    line-height: 1.2 !important;
    overflow: visible !important;
}

[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* ---------------- Reports controls ---------------- */
/* Completely remove report/search controls from the rail so nothing is clipped. */
[data-testid="stSidebar"] [data-testid="stTextInput"],
[data-testid="stSidebar"] [data-testid="stExpander"] {
    display: none !important;
}
[data-testid="stSidebar"]:hover [data-testid="stTextInput"] {
    display: block !important;
}
[data-testid="stSidebar"]:hover [data-testid="stExpander"] {
    display: block !important;
}
[data-testid="stSidebar"]:hover input[type="text"] {
    min-height: 37px !important;
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
    background: #ffffff !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    border-radius: 7px !important;
}
[data-testid="stSidebar"]:hover input[type="text"]::placeholder {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"]:hover [data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,.10) !important;
    border-radius: 7px !important;
    background: rgba(255,255,255,.045) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    color: #dce7f5 !important;
    font-size: 11px !important;
}

/* ---------------- Bottom content ---------------- */
.sugam-sidebar-spacer,
.sugam-refresh-card,
.sugam-profile-card,
.sugam-session-meta,
.sugam-footer {
    display: none !important;
}

[data-testid="stSidebar"]:hover .sugam-sidebar-spacer {
    display: block !important;
    height: 12px;
}
[data-testid="stSidebar"]:hover .sugam-refresh-card {
    display: block !important;
    margin-top: 12px;
    padding: 11px 11px 9px;
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 8px;
    background: rgba(3, 25, 58, .32);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
}
.sugam-refresh-head {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #edf5ff;
    font-size: 10px;
    font-weight: 700;
}
.sugam-refresh-icon {
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    color: #8fc5ff;
    background: rgba(44,126,229,.15);
}
.sugam-refresh-time {
    margin-top: 3px;
    color: #91a6c2;
    font-size: 9px;
    font-weight: 500;
}
.sugam-auto-row {
    margin-top: 9px;
    padding-top: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-top: 1px solid rgba(255,255,255,.08);
    color: #aabbd1;
    font-size: 9px;
}
.sugam-static-toggle {
    width: 31px;
    height: 16px;
    padding: 2px;
    display: inline-flex;
    justify-content: flex-end;
    border-radius: 99px;
    background: #2d7ff0;
    box-shadow: inset 0 1px 3px rgba(0,0,0,.24);
}
.sugam-static-toggle span {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,.24);
}

[data-testid="stSidebar"]:hover .sugam-profile-card {
    display: flex !important;
    margin-top: 9px;
    padding: 9px;
    align-items: center;
    gap: 9px;
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 8px;
    background: rgba(3, 25, 58, .35);
}
.sugam-avatar {
    position: relative;
    width: 34px;
    height: 34px;
    flex: 0 0 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    color: #184170;
    background: linear-gradient(145deg, #f7fbff, #dcecff);
    font-size: 11px;
    font-weight: 800;
    border: 2px solid rgba(255,255,255,.75);
}
.sugam-status-dot {
    position: absolute;
    right: -1px;
    bottom: -1px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #34d399;
    border: 2px solid #0a2a58;
}
.sugam-profile-text { min-width: 0; flex: 1; line-height: 1.2; }
.sugam-user-name {
    overflow: hidden;
    color: #ffffff;
    font-size: 10.5px;
    font-weight: 700;
    white-space: nowrap;
    text-overflow: ellipsis;
}
.sugam-user-meta {
    margin-top: 3px;
    color: #98aac2;
    font-size: 8.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.sugam-role-badge {
    margin-left: auto;
    color: #a8bad1;
    font-size: 8px;
    font-weight: 700;
    text-transform: uppercase;
}
[data-testid="stSidebar"]:hover .sugam-session-meta {
    display: block !important;
    margin-top: 5px;
    color: #8095b1;
    font-size: 8px;
    text-align: center;
}
[data-testid="stSidebar"]:hover .sugam-footer {
    display: block !important;
    padding: 7px 0 0;
    color: #6680a1;
    font-size: 8px;
    text-align: center;
}

/* Hide every sidebar action button in rail mode. Reveal them only on hover. */
[data-testid="stSidebar"] .stButton {
    display: none !important;
}
[data-testid="stSidebar"]:hover .stButton {
    display: block !important;
}
[data-testid="stSidebar"]:hover .stButton > button {
    min-height: 34px;
    width: 100%;
    padding: 0 10px !important;
    border-radius: 7px !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    color: #dce8f7 !important;
    background: rgba(255,255,255,.055) !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"]:hover .stButton > button:hover {
    border-color: rgba(112,174,255,.55) !important;
    background: rgba(45,127,240,.18) !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"]:hover .stButton > button p {
    color: inherit !important;
    font-size: inherit !important;
}

[data-testid="stSidebar"] hr {
    margin: 10px 0 !important;
    border-color: rgba(255,255,255,.08) !important;
}
</style>
""", unsafe_allow_html=True)


# Full list of menu items that exist in the app (before role-based filtering).
# Used for routing below, and read by the User Management admin page so its
# checkboxes always match what's actually available here.
FULL_MENU_ITEMS = [
    "🏠 Business Overview",
    "💹 P&L Dashboard",
    "💰 Net Profit Dashboard",
    "📊 Comparison",
    "📦 Tariff Rate Dashboard",
    "📈 Outstanding Analysis",
    "📅 Monthly Trend EDD",
    "👥 Customer Analysis",
    "🚛 Service Analysis",
    "📦 Stock Operations",
    "📄 Reports",
    "📊 Usage Analytics",
    "🛠️ User Management",
]


REPORTS = {
    "🖥️ IT Reports": {
        "📊 Zone Booking Turnover": show_ZoneBookingTurnover,
        "📋 Bangladesh Delivery Turnover": show_bangladesh_delivery_turnover,
        "📈 Booking Summary Turnover": show_booking_summary_turnover,
        "📊 Zone Wise Delivery Turnover": show_zone_wise_delivery_turnover,
        "📊 Branch Wise Delivery Turnover": show_branch_wise_delivery_turnover,
        "📊 Delivery Summary Turnover": show_delivery_summary_turnover,
        "📊 Branch Wise Booking Turnover": show_branch_wise_booking_turnover,
        "⚖️ Booking Weight Summary": show_booking_weight_summary_turnover,
        
    },
    "💰 Accounts Reports": {
        "📋 GR Costing Head Wise": show_GrCostingHeadWise,
    },
}

# Expose to the User Management page so it never drifts out of sync
# with the menu items / reports actually defined here.
st.session_state["_all_menu_items"] = FULL_MENU_ITEMS
st.session_state["_all_reports"] = [name for reports in REPORTS.values() for name in reports.keys()]


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if "selected_report" not in st.session_state:
    st.session_state["selected_report"] = None


if not st.session_state["logged_in"]:
    login_page()
    st.stop()


# =========================
# Role-based access setup
# =========================
role = st.session_state.get("role", "viewer")

allowed_menu = list(get_allowed_menu(role) or [])  # e.g. ["🏠 Overview", "📊 Comparison", ...]
allowed_reports = set(get_allowed_reports(role))    # e.g. {"📊 Zone Booking Turnover"}
# Make the new EDD report immediately available in the Reports menu.
allowed_reports.add("📅 Monthly Trend EDD")

# Tariff dashboard is a primary navigation page, not a report-folder item.
# Keep it available to every authenticated role.
if "📦 Tariff Rate Dashboard" not in allowed_menu:
    if "📊 Comparison" in allowed_menu:
        tariff_position = allowed_menu.index("📊 Comparison") + 1
    else:
        tariff_position = min(1, len(allowed_menu))
    allowed_menu.insert(tariff_position, "📦 Tariff Rate Dashboard")

# Stock Operations is a core operational page. Data-scope restrictions are
# enforced inside the page for branch/circle/zone users.
if "📦 Stock Operations" not in allowed_menu:
    stock_position = allowed_menu.index("🏠 Business Overview") + 1 \
        if "🏠 Business Overview" in allowed_menu else 0
    allowed_menu.insert(stock_position, "📦 Stock Operations")

# Usage Analytics is a system/admin page and does not require a database permission row.
if role.lower() == "admin" and "📊 Usage Analytics" not in allowed_menu:
    analytics_position = allowed_menu.index("🛠️ User Management") \
        if "🛠️ User Management" in allowed_menu else len(allowed_menu)
    allowed_menu.insert(analytics_position, "📊 Usage Analytics")
else:
    # Defense-in-depth: never expose live employee usage to non-admin roles.
    allowed_menu = [item for item in allowed_menu if item != "📊 Usage Analytics"]

# Only keep report entries this role is allowed to see, in every department folder
REPORTS_VISIBLE = {
    department: {
        report_name: report_fn
        for report_name, report_fn in reports.items()
        if report_name in allowed_reports
    }
    for department, reports in REPORTS.items()
}
# Drop departments that end up empty for this role
REPORTS_VISIBLE = {dept: reports for dept, reports in REPORTS_VISIBLE.items() if reports}


# =========================
# Resolve logged-in employee name
# =========================
# login.py saves the employee name under the "employee_name" key.
# Keep a safe fallback so the dashboard still works for older sessions.
if "employee_name" not in st.session_state:
    st.session_state["employee_name"] = st.session_state.get(
        "username",
        f"Employee {st.session_state.get('employee_id', '')}",
    )

display_name = st.session_state.get("employee_name") or st.session_state.get(
    "username",
    f"Employee {st.session_state.get('employee_id', '')}",
)

# Initials for the avatar badge (e.g. "Rahul Sharma" -> "RS", "Rahul" -> "R")
_name_parts = [p for p in str(display_name).replace("Employee", "").strip().split() if p]
if _name_parts:
    initials = "".join(p[0].upper() for p in _name_parts[:2])
else:
    initials = "👤"

# Role badge color class
_role_class_map = {
    "admin": "sugam-role-admin",
    "manager": "sugam-role-manager",
    "viewer": "sugam-role-viewer",
}
role_class = _role_class_map.get(role.lower(), "sugam-role-viewer")

# Session meta (current date + login time, shown once per session)
if "_login_time" not in st.session_state:
    st.session_state["_login_time"] = datetime.now().strftime("%I:%M %p")

today_str = datetime.now().strftime("%d %b %Y")


with st.sidebar:
    # ==========================================================
    # Brand header — visual placement only; no routing logic changed.
    # ==========================================================
    st.markdown(
        """
        <div class="sugam-logo-wrap">
            <div class="sugam-logo-mark" aria-hidden="true"></div>
            <div class="sugam-logo-copy">
                <div class="sugam-logo-name">SUGAM</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not allowed_menu:
        st.warning("No access has been assigned to your role yet. Contact the admin.")
        st.stop()

    # ==========================================================
    # Navigation — same role-filtered menu values and same radio.
    # ==========================================================
    st.markdown('<div class="sugam-nav-label">Navigation</div>', unsafe_allow_html=True)
    menu = st.radio(
        "Navigation",
        allowed_menu,
        label_visibility="collapsed",
        key="sidebar_main_navigation",
    )

    # Existing reports search/folder logic is preserved exactly.
    if menu == "📄 Reports":

        # Keep the sidebar fully expanded while the Reports section is selected.
        # This prevents report search/folders/buttons from disappearing when the
        # mouse moves away from the sidebar in hover mode.
        st.markdown(
            """
            <style>
            [data-testid="stSidebar"] {
                width: 242px !important;
                min-width: 242px !important;
                max-width: 242px !important;
                flex: 0 0 242px !important;
                overflow: hidden !important;
            }

            [data-testid="stSidebar"] [data-testid="stSidebarContent"],
            [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
                padding-left: 12px !important;
                padding-right: 12px !important;
            }

            [data-testid="stSidebar"] .sugam-logo-wrap {
                margin-left: -12px !important;
                margin-right: -12px !important;
                padding: 0 15px !important;
                justify-content: flex-start !important;
            }

            [data-testid="stSidebar"] .sugam-logo-copy,
            [data-testid="stSidebar"] .sugam-nav-label,
            [data-testid="stSidebar"] [data-testid="stTextInput"],
            [data-testid="stSidebar"] [data-testid="stExpander"],
            [data-testid="stSidebar"] .sugam-sidebar-spacer,
            [data-testid="stSidebar"] .sugam-refresh-card,
            [data-testid="stSidebar"] .sugam-session-meta,
            [data-testid="stSidebar"] .sugam-footer,
            [data-testid="stSidebar"] .stButton {
                display: block !important;
            }

            [data-testid="stSidebar"] .sugam-profile-card {
                display: flex !important;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label {
                width: 100% !important;
                min-height: 39px !important;
                margin: 0 !important;
                padding: 8px 10px !important;
                justify-content: flex-start !important;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label p {
                width: auto !important;
                max-width: none !important;
                color: #d9e5f4 !important;
                font-size: 12px !important;
                line-height: 1.2 !important;
                overflow: visible !important;
            }

            [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
                color: #ffffff !important;
                font-weight: 700 !important;
            }

            [data-testid="stSidebar"] .stButton > button {
                min-height: 34px !important;
                width: 100% !important;
                padding: 0 10px !important;
                border-radius: 7px !important;
                border: 1px solid rgba(255,255,255,.12) !important;
                color: #dce8f7 !important;
                background: rgba(255,255,255,.055) !important;
                font-size: 10px !important;
                font-weight: 600 !important;
                box-shadow: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ---------------------------------
        # SEARCH REPORT
        # ---------------------------------
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"]
            div[data-testid="stTextInput"] input {
                color: #111827 !important;
                -webkit-text-fill-color: #111827 !important;
                background-color: #ffffff !important;
                caret-color: #111827 !important;
            }

            section[data-testid="stSidebar"]
            div[data-testid="stTextInput"] input::placeholder {
                color: #64748b !important;
                -webkit-text-fill-color: #64748b !important;
                opacity: 1 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        search_text = st.text_input(
            "SEARCH REPORT",
            placeholder="Search report",
            key="report_search",
        )

        if search_text:
            for department, reports in REPORTS_VISIBLE.items():
                for report_name in reports.keys():
                    if search_text.lower() in report_name.lower():
                        if st.button(
                            report_name,
                            key=f"search_{report_name}",
                            use_container_width=True,
                        ):
                            st.session_state["selected_report"] = report_name
                            st.rerun()

        st.markdown(
            '<div class="sugam-nav-label">Report Folders</div>',
            unsafe_allow_html=True,
        )

        if not REPORTS_VISIBLE:
            st.info("No reports assigned to your role.")
        else:
            for department, reports in REPORTS_VISIBLE.items():
                with st.expander(department, expanded=False):
                    for report_name in reports.keys():
                        if st.button(
                            report_name,
                            key=f"{department}_{report_name}",
                            use_container_width=True,
                        ):
                            st.session_state["selected_report"] = report_name
                            st.rerun()

    # ==========================================================
    # Operational status card. The displayed toggle is decorative;
    # Refresh Data below retains the original cache-clearing logic.
    # ==========================================================
    st.markdown('<div class="sugam-sidebar-spacer"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="sugam-refresh-card">
            <div class="sugam-refresh-head">
                <span class="sugam-refresh-icon">↻</span>
                <span>
                    Data Last Refreshed
                    <div class="sugam-refresh-time">{today_str} · {st.session_state['_login_time']}</div>
                </span>
            </div>
            <div class="sugam-auto-row">
                <span>Auto Refresh</span>
                <span class="sugam-static-toggle" title="Visual status only"><span></span></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Original refresh behavior: clear Streamlit data cache and role cache.
    if st.button("🔄 Refresh Data", use_container_width=True, key="sidebar_refresh_data"):
        st.cache_data.clear()
        clear_role_cache()
        st.success("Data refreshed!")

    # ==========================================================
    # User profile at the bottom, matching the shared design.
    # ==========================================================
    st.markdown(
        f"""
        <div class="sugam-profile-card">
            <div class="sugam-avatar">
                {initials}
                <span class="sugam-status-dot"></span>
            </div>
            <div class="sugam-profile-text">
                <div class="sugam-user-name" title="{display_name}">{display_name}</div>
                <div class="sugam-user-meta">
                    ID: {st.session_state.get('employee_id', '-')} · {role.title()}
                </div>
            </div>
            <span class="sugam-role-badge">⌄</span>
        </div>
        <div class="sugam-session-meta">Logged in {st.session_state['_login_time']}</div>
        """,
        unsafe_allow_html=True,
    )

    # Original logout behavior preserved.
    if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
        unregister_usage_session()
        st.session_state.clear()
        st.rerun()

    st.markdown(
        '<div class="sugam-footer">Sugam Dashboard · v1.0</div>',
        unsafe_allow_html=True,
    )


# ==========================================================
# Live usage heartbeat / page-open tracking (memory only)
# ==========================================================
if menu == "📄 Reports" and st.session_state.get("selected_report"):
    _current_usage_page = f"📄 Reports › {st.session_state.get('selected_report')}"
else:
    _current_usage_page = menu

track_usage(_current_usage_page, count_open=True)


if menu == "🏠 Business Overview":
    show_overview()

elif menu == "📦 Stock Operations":
    show_stock_operations()

elif menu == "💹 P&L Dashboard":
    show_pnl_dashboard()

elif menu == "💰 Net Profit Dashboard":
    show_net_profit_dashboard()

elif menu == "📊 Comparison":
    show_comparison()

elif menu == "📦 Tariff Rate Dashboard":
    show_tariff_rate_dashboard()

elif menu == "📈 Outstanding Analysis":
    show_OutstandingAnalysis()

elif menu == "👥 Customer Analysis":
    show_CustomerAnalysis()

elif menu == "📅 Monthly Trend EDD":
    show_monthly_trend_edd()

elif menu == "🚛 Service Analysis":
    show_service_level()

elif menu == "📊 Usage Analytics":
    if role.lower() == "admin":
        show_usage_analytics()
    else:
        st.error("You do not have access to Usage Analytics.")

elif menu == "🛠️ User Management":
    show_UserManagement()

elif menu == "📄 Reports":

    selected = st.session_state.get("selected_report")

    if selected is None:
        st.info("Please select a report from the sidebar.")

    elif selected not in allowed_reports:
        # Defense-in-depth: covers the case where role changed after a report was already selected
        st.error("You don't have access to this report.")
        st.session_state["selected_report"] = None

    else:
        report_found = False

        for department, reports in REPORTS_VISIBLE.items():
            if selected in reports:
                reports[selected]()
                report_found = True
                break

        if not report_found:
            st.error("Selected report not found.")
