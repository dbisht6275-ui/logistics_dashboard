import streamlit as st
from datetime import datetime
from services.login import login_page
from services.roles import get_allowed_menu, get_allowed_reports, clear_role_cache

from pages.Home.overview_tab import show_overview
from pages.Home.comparison_tab import show_comparison
from pages.Home.Customer_Analysis import show_CustomerAnalysis
from pages.Home.Service_Analysis import show_service_level
from pages.Home.Outstanding_Analysis import show_OutstandingAnalysis
from pages.IT.zone_booking_turnover import show_ZoneBookingTurnover

from pages.Accounts.GrCostingHeadWise import show_GrCostingHeadWise
from pages.Admin.user_management import show_UserManagement


st.set_page_config(
    page_title="Sugam Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================
# Sidebar styling (professional / enterprise theme)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Keep the application content close to the top. */
[data-testid="stHeader"] {
    height: 2.1rem;
    background: transparent;
}
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stDecoration"] { display: none; }
.main .block-container { padding-top: 1.05rem !important; }

/* ============================================================
   SUGAM sidebar shell — visual-only update.
   All menu values, role checks, report routing and button logic
   remain unchanged in the Python code below.
   ============================================================ */
[data-testid="stSidebar"] {
    width: 242px !important;
    min-width: 242px !important;
    background: linear-gradient(180deg, #123568 0%, #0b2a58 58%, #08244d 100%);
    border-right: 1px solid rgba(7, 28, 63, .45);
    box-shadow: 5px 0 18px rgba(15, 42, 82, .12);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding: 0 12px 12px !important;
}
[data-testid="stSidebar"] * { box-sizing: border-box; }


/* ============================================================
   Highly visible sidebar expand / collapse controls.
   These selectors cover current and older Streamlit DOM names.
   Visual-only: no sidebar state or routing logic is changed.
   ============================================================ */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"] {
    z-index: 999999 !important;
}

[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"] {
    width: 38px !important;
    min-width: 38px !important;
    height: 38px !important;
    min-height: 38px !important;
    padding: 7px !important;
    border: 2px solid #ffffff !important;
    border-radius: 10px !important;
    background: linear-gradient(145deg, #3182f6 0%, #1761d2 62%, #104eae 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 0 #0a3c8d, 0 7px 14px rgba(4, 29, 72, .35) !important;
    opacity: 1 !important;
    visibility: visible !important;
    transform: none !important;
    transition: transform .15s ease, box-shadow .15s ease, background .15s ease !important;
}

[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"]:hover {
    background: linear-gradient(145deg, #4d98ff 0%, #1f70e8 62%, #1558c0 100%) !important;
    transform: translateY(-1px) scale(1.04) !important;
    box-shadow: 0 5px 0 #0a3c8d, 0 10px 18px rgba(4, 29, 72, .42) !important;
}

[data-testid="stSidebarCollapsedControl"] button:active,
[data-testid="stSidebarCollapseButton"] button:active,
[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"]:active {
    transform: translateY(2px) !important;
    box-shadow: 0 1px 0 #0a3c8d, 0 4px 8px rgba(4, 29, 72, .30) !important;
}

[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebar"] button[data-testid="stBaseButton-headerNoPadding"] svg {
    width: 23px !important;
    height: 23px !important;
    color: #ffffff !important;
    fill: none !important;
    stroke: #ffffff !important;
    stroke-width: 3 !important;
    opacity: 1 !important;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,.25));
}

/* Keep the expand button away from the browser edge when sidebar is closed. */
[data-testid="stSidebarCollapsedControl"] {
    top: 10px !important;
    left: 10px !important;
}

/* Brand block matching the shared reference layout. */
.sugam-logo-wrap {
    min-height: 78px;
    margin: 0 -12px 10px;
    padding: 15px 15px 13px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(5, 28, 63, .36);
    border-bottom: 1px solid rgba(255,255,255,.10);
}
.sugam-logo-mark {
    position: relative;
    width: 35px;
    height: 31px;
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
.sugam-logo-copy { min-width: 0; line-height: 1; }
.sugam-logo-name {
    color: #ffffff;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: 1.5px;
}
.sugam-logo-sub {
    margin-top: 4px;
    color: #cbd8ea;
    font-size: 8px;
    font-weight: 700;
    letter-spacing: 3.1px;
}

/* Navigation. */
.sugam-nav-label {
    margin: 10px 7px 6px;
    color: #91a9c9;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.4px;
    text-transform: uppercase;
}
[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 3px !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label {
    min-height: 39px;
    margin: 0 !important;
    padding: 8px 10px !important;
    display: flex !important;
    align-items: center !important;
    border: 1px solid transparent;
    border-radius: 7px;
    background: transparent;
    transition: background .14s ease, border-color .14s ease, transform .14s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(255,255,255,.075);
    transform: translateX(1px);
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, #1f70e8 0%, #1761d2 100%);
    border-color: rgba(123,184,255,.32);
    box-shadow: 0 5px 12px rgba(3, 35, 83, .28), inset 0 1px 0 rgba(255,255,255,.15);
}
[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label p {
    margin: 0 !important;
    color: #d9e5f4 !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    line-height: 1.2 !important;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Report controls. */
[data-testid="stSidebar"] input[type="text"] {
    min-height: 37px;
    color: #eef5ff !important;
    background: rgba(255,255,255,.07) !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    border-radius: 7px !important;
}
[data-testid="stSidebar"] input[type="text"]::placeholder { color: #9fb2cc !important; }
[data-testid="stSidebar"] [data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,.10) !important;
    border-radius: 7px !important;
    background: rgba(255,255,255,.045) !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    color: #dce7f5 !important;
    font-size: 11px !important;
}

/* Bottom operational card. */
.sugam-sidebar-spacer { height: 12px; }
.sugam-refresh-card {
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

/* Profile card at the foot of the navigation, as in the reference. */
.sugam-profile-card {
    margin-top: 9px;
    padding: 9px;
    display: flex;
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

/* Sidebar buttons: refresh and logout keep their original Python callbacks. */
[data-testid="stSidebar"] .stButton > button {
    min-height: 34px;
    border-radius: 7px !important;
    border: 1px solid rgba(255,255,255,.12) !important;
    color: #dce8f7 !important;
    background: rgba(255,255,255,.055) !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: rgba(112,174,255,.55) !important;
    background: rgba(45,127,240,.18) !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stButton > button p {
    color: inherit !important;
    font-size: inherit !important;
}

.sugam-session-meta {
    margin-top: 5px;
    color: #8095b1;
    font-size: 8px;
    text-align: center;
}
.sugam-footer {
    padding: 7px 0 0;
    color: #6680a1;
    font-size: 8px;
    text-align: center;
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
    "🏠 Revenue Overview",
    "📊 Comparison",
    "📈 Outstanding Analysis",
    "👥 Customer Analysis",
    "🚛 Service Analysis",
    "📄 Reports",
    "🛠️ User Management",
]


REPORTS = {
    "🖥️ IT Reports": {
        "📊 Zone Booking Turnover": show_ZoneBookingTurnover,

    },
    "💰 Accounts Reports": {
        "📋 GR Costing Head Wise": show_GrCostingHeadWise,
    }
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

allowed_menu = get_allowed_menu(role)          # e.g. ["🏠 Overview", "📊 Comparison", ...]
allowed_reports = get_allowed_reports(role)    # e.g. {"📊 Zone Booking Turnover"}

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
# Resolve logged-in user's display name
# =========================
# NOTE: login.py isn't available to check exactly which session_state key it
# sets for the user's name. This tries the common ones in order, and falls
# back to "Employee {id}" if none are present, so nothing breaks either way.
# If your login.py stores it under a different key, add that key to this list.
_username_keys = ["username", "full_name", "name", "user_name", "employee_name", "display_name"]
display_name = next(
    (st.session_state[k] for k in _username_keys if st.session_state.get(k)),
    f"Employee {st.session_state.get('employee_id', '')}"
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
                <div class="sugam-logo-sub">LOGISTICS</div>
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
        st.markdown('<div class="sugam-nav-label">Search Report</div>', unsafe_allow_html=True)

        search_text = st.text_input(
            "Search by report name",
            label_visibility="collapsed",
            placeholder="🔍 Search report",
            key="sidebar_report_search",
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

        st.markdown('<div class="sugam-nav-label">Report Folders</div>', unsafe_allow_html=True)

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
        st.session_state.clear()
        st.rerun()

    st.markdown(
        '<div class="sugam-footer">Sugam Dashboard · v1.0</div>',
        unsafe_allow_html=True,
    )


if menu == "🏠 Revenue Overview":
    show_overview()

elif menu == "📊 Comparison":
    show_comparison()

elif menu == "📈 Outstanding Analysis":
    show_OutstandingAnalysis()

elif menu == "👥 Customer Analysis":
    show_CustomerAnalysis()

elif menu == "🚛 Service Analysis":
    show_service_level()

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
