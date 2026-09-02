import streamlit as st
from datetime import datetime
from pathlib import Path
import runpy
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

try:
    from pages.IT.service_analysis import show_service_level
except ImportError:
    def show_service_level():
        st.warning("🚛 Service Analysis page not found. Please create pages/IT/service_analysis.py")


def show_tariff_rate_dashboard():
    app_directory = Path(__file__).resolve().parent
    dashboard_file = app_directory / "pages" / "Home" / "tariff_rate_dashboard.py"

    if not dashboard_file.is_file():
        st.error(f"Tariff dashboard not found at: {dashboard_file}")
        return

    runpy.run_path(str(dashboard_file), run_name="tariff_rate_dashboard")


st.set_page_config(
    page_title="Sugam Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -------------------------
# Helpers
# -------------------------
def menu_icon(label: str) -> str:
    if not label:
        return "•"
    first = label.split()[0]
    return first if first else "•"


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

st.session_state["_all_menu_items"] = FULL_MENU_ITEMS
st.session_state["_all_reports"] = [name for reports in REPORTS.values() for name in reports.keys()]

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "selected_report" not in st.session_state:
    st.session_state["selected_report"] = None
if "sidebar_compact_mode" not in st.session_state:
    st.session_state["sidebar_compact_mode"] = False

if not st.session_state["logged_in"]:
    login_page()
    st.stop()


# -------------------------
# Role-based access setup
# -------------------------
role = st.session_state.get("role", "viewer")
allowed_menu = list(get_allowed_menu(role) or [])
allowed_reports = set(get_allowed_reports(role))
allowed_reports.add("📅 Monthly Trend EDD")

if "📦 Tariff Rate Dashboard" not in allowed_menu:
    if "📊 Comparison" in allowed_menu:
        tariff_position = allowed_menu.index("📊 Comparison") + 1
    else:
        tariff_position = min(1, len(allowed_menu))
    allowed_menu.insert(tariff_position, "📦 Tariff Rate Dashboard")

if "📦 Stock Operations" not in allowed_menu:
    stock_position = allowed_menu.index("🏠 Business Overview") + 1 if "🏠 Business Overview" in allowed_menu else 0
    allowed_menu.insert(stock_position, "📦 Stock Operations")

REPORTS_VISIBLE = {
    department: {
        report_name: report_fn
        for report_name, report_fn in reports.items()
        if report_name in allowed_reports
    }
    for department, reports in REPORTS.items()
}
REPORTS_VISIBLE = {dept: reports for dept, reports in REPORTS_VISIBLE.items() if reports}

if not allowed_menu:
    st.warning("No access has been assigned to your role yet. Contact the admin.")
    st.stop()

if "selected_menu" not in st.session_state or st.session_state["selected_menu"] not in allowed_menu:
    st.session_state["selected_menu"] = allowed_menu[0]

if "employee_name" not in st.session_state:
    st.session_state["employee_name"] = st.session_state.get(
        "username",
        f"Employee {st.session_state.get('employee_id', '')}",
    )

display_name = st.session_state.get("employee_name") or st.session_state.get(
    "username",
    f"Employee {st.session_state.get('employee_id', '')}",
)

_name_parts = [p for p in str(display_name).replace("Employee", "").strip().split() if p]
if _name_parts:
    initials = "".join(p[0].upper() for p in _name_parts[:2])
else:
    initials = "👤"

if "_login_time" not in st.session_state:
    st.session_state["_login_time"] = datetime.now().strftime("%I:%M %p")

today_str = datetime.now().strftime("%d %b %Y")
compact_mode = st.session_state.get("sidebar_compact_mode", False)
sidebar_width = "86px" if compact_mode else "242px"


# -------------------------
# CSS
# -------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    [data-testid="stHeader"] {{
        height: 2.1rem;
        background: transparent;
    }}
    [data-testid="stToolbar"] {{ right: 1rem; }}
    [data-testid="stDecoration"] {{ display: none; }}
    .main .block-container {{
        padding-top: 1.05rem !important;
        width: 100% !important;
        max-width: 100% !important;
    }}

    [data-testid="stSidebar"] {{
        width: {sidebar_width} !important;
        min-width: {sidebar_width} !important;
        max-width: {sidebar_width} !important;
        flex: 0 0 {sidebar_width} !important;
        background: linear-gradient(180deg, #123568 0%, #0b2a58 58%, #08244d 100%);
        border-right: 1px solid rgba(7, 28, 63, .45);
        box-shadow: 5px 0 18px rgba(15, 42, 82, .12);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        transition: width .18s ease, min-width .18s ease, max-width .18s ease !important;
    }}

    [data-testid="stSidebar"] > div:first-child,
    [data-testid="stSidebar"] [data-testid="stSidebarContent"],
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
        padding-top: 0 !important;
        margin-top: 0 !important;
    }}

    [data-testid="stSidebar"] [data-testid="stSidebarContent"],
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
        padding-left: {'8px' if compact_mode else '12px'} !important;
        padding-right: {'8px' if compact_mode else '12px'} !important;
        padding-bottom: 12px !important;
    }}

    [data-testid="stSidebar"] * {{ box-sizing: border-box; }}

    .sugam-logo-wrap {{
        min-height: {'52px' if compact_mode else '56px'};
        margin: 0 {'-8px' if compact_mode else '-12px'} 10px;
        padding: {'8px 8px' if compact_mode else '7px 15px 7px'};
        display: flex;
        align-items: center;
        justify-content: {'center' if compact_mode else 'flex-start'};
        gap: 10px;
        background: rgba(5, 28, 63, .36);
        border-bottom: 1px solid rgba(255,255,255,.10);
    }}

    .sugam-logo-mark {{
        position: relative;
        width: 35px;
        height: 31px;
        flex: 0 0 35px;
    }}

    .sugam-logo-mark::before,
    .sugam-logo-mark::after {{
        content: "";
        position: absolute;
        left: 2px;
        width: 30px;
        height: 9px;
        border-radius: 3px 8px 3px 8px;
        background: linear-gradient(90deg, #ef233c, #d90429);
        transform: skewX(-28deg) rotate(-12deg);
        box-shadow: 0 2px 5px rgba(217,4,41,.24);
    }}

    .sugam-logo-mark::before {{ top: 4px; }}
    .sugam-logo-mark::after {{ top: 17px; left: 6px; width: 25px; }}
    .sugam-logo-copy {{ min-width: 0; line-height: 1; }}
    .sugam-logo-name {{
        color: #ffffff;
        font-size: 17px;
        font-weight: 800;
        letter-spacing: 1.5px;
    }}

    .sugam-nav-label {{
        margin: 10px 7px 6px;
        color: #91a9c9;
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1.4px;
        text-transform: uppercase;
        text-align: {'center' if compact_mode else 'left'};
    }}

    .sugam-toggle-wrap {{ margin: 0 0 8px 0; }}
    .sugam-toggle-wrap .stButton > button {{
        min-height: 34px;
        border-radius: 8px !important;
        border: 1px solid rgba(255,255,255,.15) !important;
        color: #ffffff !important;
        background: rgba(255,255,255,.06) !important;
        font-size: 12px !important;
        font-weight: 700 !important;
    }}
    .sugam-toggle-wrap .stButton > button:hover {{
        border-color: rgba(112,174,255,.55) !important;
        background: rgba(45,127,240,.18) !important;
    }}

    [data-testid="stSidebar"] div[role="radiogroup"] {{ gap: 3px !important; }}
    [data-testid="stSidebar"] div[role="radiogroup"] label {{
        min-height: 39px;
        margin: 0 !important;
        padding: 8px 10px !important;
        display: flex !important;
        align-items: center !important;
        border: 1px solid transparent;
        border-radius: 7px;
        background: transparent;
        transition: background .14s ease, border-color .14s ease, transform .14s ease;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: rgba(255,255,255,.075);
        transform: translateX(1px);
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: linear-gradient(90deg, #1f70e8 0%, #1761d2 100%);
        border-color: rgba(123,184,255,.32);
        box-shadow: 0 5px 12px rgba(3, 35, 83, .28), inset 0 1px 0 rgba(255,255,255,.15);
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
        display: none !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label p {{
        margin: 0 !important;
        color: #d9e5f4 !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
    }}
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
        color: #ffffff !important;
        font-weight: 700 !important;
    }}

    .compact-nav .stButton > button {{
        min-height: 42px !important;
        height: 42px !important;
        padding: 0 !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,.12) !important;
        background: rgba(255,255,255,.05) !important;
        color: #eef5ff !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    .compact-nav .stButton > button:hover {{
        border-color: rgba(112,174,255,.55) !important;
        background: rgba(45,127,240,.18) !important;
        color: #ffffff !important;
    }}
    .compact-selected .stButton > button {{
        background: linear-gradient(180deg, #287dff 0%, #1761d2 100%) !important;
        border-color: rgba(123,184,255,.35) !important;
        box-shadow: 0 5px 12px rgba(3, 35, 83, .28) !important;
        color: #ffffff !important;
    }}

    .compact-current {{
        margin: 6px 0 10px;
        color: #aec2da;
        font-size: 8.5px;
        text-align: center;
        line-height: 1.3;
        word-break: break-word;
    }}

    [data-testid="stSidebar"] input[type="text"] {{
        min-height: 37px;
        color: #eef5ff !important;
        background: rgba(255,255,255,.07) !important;
        border: 1px solid rgba(255,255,255,.12) !important;
        border-radius: 7px !important;
    }}
    [data-testid="stSidebar"] input[type="text"]::placeholder {{ color: #9fb2cc !important; }}
    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        border: 1px solid rgba(255,255,255,.10) !important;
        border-radius: 7px !important;
        background: rgba(255,255,255,.045) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p {{
        color: #dce7f5 !important;
        font-size: 11px !important;
    }}

    .sugam-sidebar-spacer {{ height: 12px; }}
    .sugam-refresh-card {{
        margin-top: 12px;
        padding: 11px 11px 9px;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 8px;
        background: rgba(3, 25, 58, .32);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.035);
    }}
    .sugam-refresh-head {{
        display: flex;
        align-items: center;
        gap: 8px;
        color: #edf5ff;
        font-size: 10px;
        font-weight: 700;
    }}
    .sugam-refresh-icon {{
        width: 24px;
        height: 24px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        color: #8fc5ff;
        background: rgba(44,126,229,.15);
    }}
    .sugam-refresh-time {{
        margin-top: 3px;
        color: #91a6c2;
        font-size: 9px;
        font-weight: 500;
    }}
    .sugam-auto-row {{
        margin-top: 9px;
        padding-top: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-top: 1px solid rgba(255,255,255,.08);
        color: #aabbd1;
        font-size: 9px;
    }}
    .sugam-static-toggle {{
        width: 31px;
        height: 16px;
        padding: 2px;
        display: inline-flex;
        justify-content: flex-end;
        border-radius: 99px;
        background: #2d7ff0;
        box-shadow: inset 0 1px 3px rgba(0,0,0,.24);
    }}
    .sugam-static-toggle span {{
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,.24);
    }}

    .sugam-profile-card {{
        margin-top: 9px;
        padding: 9px;
        display: flex;
        align-items: center;
        gap: 9px;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 8px;
        background: rgba(3, 25, 58, .35);
    }}
    .sugam-avatar {{
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
    }}
    .sugam-status-dot {{
        position: absolute;
        right: -1px;
        bottom: -1px;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: #34d399;
        border: 2px solid #0a2a58;
    }}
    .sugam-profile-text {{ min-width: 0; flex: 1; line-height: 1.2; }}
    .sugam-user-name {{
        overflow: hidden;
        color: #ffffff;
        font-size: 10.5px;
        font-weight: 700;
        white-space: nowrap;
        text-overflow: ellipsis;
    }}
    .sugam-user-meta {{
        margin-top: 3px;
        color: #98aac2;
        font-size: 8.5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .sugam-role-badge {{
        margin-left: auto;
        color: #a8bad1;
        font-size: 8px;
        font-weight: 700;
        text-transform: uppercase;
    }}

    [data-testid="stSidebar"] .stButton > button {{
        border-radius: 7px !important;
        box-shadow: none !important;
    }}

    .compact-bottom .stButton > button {{
        min-height: 40px !important;
        height: 40px !important;
        font-size: 16px !important;
        padding: 0 !important;
        border: 1px solid rgba(255,255,255,.12) !important;
        color: #dce8f7 !important;
        background: rgba(255,255,255,.055) !important;
    }}
    .compact-bottom .stButton > button:hover {{
        border-color: rgba(112,174,255,.55) !important;
        background: rgba(45,127,240,.18) !important;
        color: #ffffff !important;
    }}

    .sugam-session-meta {{
        margin-top: 5px;
        color: #8095b1;
        font-size: 8px;
        text-align: center;
    }}
    .sugam-footer {{
        padding: 7px 0 0;
        color: #6680a1;
        font-size: 8px;
        text-align: center;
    }}

    .report-grid-head {{
        margin-bottom: 10px;
        padding: 14px 16px;
        border: 1px solid #dbe5f1;
        border-radius: 12px;
        background: #f8fbff;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------
# Sidebar rendering
# -------------------------
with st.sidebar:
    if compact_mode:
        st.markdown(
            """
            <div class="sugam-logo-wrap">
                <div class="sugam-logo-mark" aria-hidden="true"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
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

    st.markdown('<div class="sugam-toggle-wrap">', unsafe_allow_html=True)
    if st.button("⇤" if compact_mode else "⇥", use_container_width=True, key="sidebar_compact_toggle"):
        st.session_state["sidebar_compact_mode"] = not compact_mode
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if compact_mode:
        st.markdown('<div class="sugam-nav-label">Menu</div>', unsafe_allow_html=True)
        for item in allowed_menu:
            selected_class = "compact-selected" if st.session_state["selected_menu"] == item else "compact-nav"
            st.markdown(f'<div class="{selected_class}">', unsafe_allow_html=True)
            if st.button(menu_icon(item), key=f"compact_menu_{item}", use_container_width=True, help=item):
                st.session_state["selected_menu"] = item
                if item != "📄 Reports":
                    st.session_state["selected_report"] = None
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="compact-current">{st.session_state["selected_menu"].replace(menu_icon(st.session_state["selected_menu"]), "", 1).strip()}</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="compact-bottom">', unsafe_allow_html=True)
        if st.button("↻", use_container_width=True, key="compact_refresh", help="Refresh Data"):
            st.cache_data.clear()
            clear_role_cache()
            st.success("Data refreshed!")
        if st.button("🚪", use_container_width=True, key="compact_logout", help="Logout"):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="sugam-footer">SUGAM</div>', unsafe_allow_html=True)

    else:
        st.markdown('<div class="sugam-nav-label">Navigation</div>', unsafe_allow_html=True)
        current_index = allowed_menu.index(st.session_state["selected_menu"]) if st.session_state["selected_menu"] in allowed_menu else 0
        menu_choice = st.radio(
            "Navigation",
            allowed_menu,
            index=current_index,
            label_visibility="collapsed",
            key="sidebar_main_navigation",
        )
        st.session_state["selected_menu"] = menu_choice

        if menu_choice == "📄 Reports":
            st.markdown(
                """
                <style>
                section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
                    color: #111827 !important;
                    -webkit-text-fill-color: #111827 !important;
                    background-color: #ffffff !important;
                    caret-color: #111827 !important;
                }
                section[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder {
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
                key="report_search_sidebar",
            )

            if search_text:
                for department, reports in REPORTS_VISIBLE.items():
                    for report_name in reports.keys():
                        if search_text.lower() in report_name.lower():
                            if st.button(report_name, key=f"search_{report_name}", use_container_width=True):
                                st.session_state["selected_report"] = report_name
                                st.rerun()

            st.markdown('<div class="sugam-nav-label">Report Folders</div>', unsafe_allow_html=True)
            if not REPORTS_VISIBLE:
                st.info("No reports assigned to your role.")
            else:
                for department, reports in REPORTS_VISIBLE.items():
                    with st.expander(department, expanded=False):
                        for report_name in reports.keys():
                            if st.button(report_name, key=f"{department}_{report_name}", use_container_width=True):
                                st.session_state["selected_report"] = report_name
                                st.rerun()

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

        if st.button("🔄 Refresh Data", use_container_width=True, key="sidebar_refresh_data"):
            st.cache_data.clear()
            clear_role_cache()
            st.success("Data refreshed!")

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

        if st.button("🚪 Logout", use_container_width=True, key="sidebar_logout"):
            st.session_state.clear()
            st.rerun()

        st.markdown('<div class="sugam-footer">Sugam Dashboard · v1.0</div>', unsafe_allow_html=True)


menu = st.session_state["selected_menu"]


# -------------------------
# Page routing
# -------------------------
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

elif menu == "🛠️ User Management":
    show_UserManagement()

elif menu == "📄 Reports":
    if compact_mode:
        st.markdown(
            """
            <div class="report-grid-head">
                <strong>Reports</strong><br>
                Select a report below. In compact sidebar mode, report selection opens here in the main area.
            </div>
            """,
            unsafe_allow_html=True,
        )

        search_text = st.text_input("Search report", placeholder="Search report", key="report_search_main")
        if not REPORTS_VISIBLE:
            st.info("No reports assigned to your role.")
        else:
            for department, reports in REPORTS_VISIBLE.items():
                matching_reports = {
                    name: fn for name, fn in reports.items()
                    if not search_text or search_text.lower() in name.lower()
                }
                if not matching_reports:
                    continue
                with st.expander(department, expanded=True):
                    for report_name in matching_reports.keys():
                        if st.button(report_name, key=f"main_{department}_{report_name}", use_container_width=True):
                            st.session_state["selected_report"] = report_name
                            st.rerun()

    selected = st.session_state.get("selected_report")

    if selected is None:
        st.info("Please select a report from the sidebar or from the report list above.")

    elif selected not in allowed_reports:
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
