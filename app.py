import streamlit as st
from services.login import login_page
from services.roles import get_allowed_menu, get_allowed_reports, clear_role_cache

from pages.Home.overview_tab import show_overview
from pages.Home.comparison_tab import show_comparison
from pages.Home.Customer_Analysis import show_CustomerAnalysis
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Sidebar base */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B1B33 0%, #0F2340 100%);
    font-family: 'Inter', -apple-system, sans-serif;
    border-right: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stSidebar"] * {
    color: #E9EEF6;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.2rem;
}

/* Profile card */
.sugam-profile-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.sugam-avatar {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: linear-gradient(135deg, #F5A623, #E0821A);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}
.sugam-profile-text {
    line-height: 1.35;
}
.sugam-emp-id {
    font-size: 13.5px;
    font-weight: 600;
    color: #F2F5FA;
}
.sugam-role-badge {
    display: inline-block;
    margin-top: 4px;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #F5A623;
    background: rgba(245,166,35,0.13);
    padding: 2px 9px;
    border-radius: 20px;
}

/* Logout / secondary buttons in sidebar */
[data-testid="stSidebar"] .stButton button {
    background: transparent;
    border: 1px solid rgba(255,255,255,0.14);
    color: #C7D2E3;
    border-radius: 8px;
    font-weight: 500;
    font-size: 13.5px;
    transition: all 0.15s ease;
}
[data-testid="stSidebar"] .stButton button:hover {
    border-color: #E24C4C;
    color: #FF7A7A;
    background: rgba(226,76,76,0.08);
}

/* Brand lockup */
.sugam-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 4px 0 16px 0;
    padding-bottom: 14px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}
.sugam-brand-icon {
    width: 32px;
    height: 32px;
    background: rgba(245,166,35,0.15);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
}
.sugam-brand-text {
    font-size: 14.5px;
    font-weight: 700;
    letter-spacing: 0.01em;
    color: #F2F5FA;
    line-height: 1.2;
}
.sugam-brand-sub {
    font-size: 10px;
    color: #7C8CA6;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-top: 1px;
}

/* Section label (Navigation / Quick Actions etc.) */
.sugam-section-label {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #5E6E88;
    margin: 4px 0 8px 2px;
}

/* Navigation radio group -> styled nav list */
[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 2px;
}
[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: transparent;
    border-radius: 8px;
    padding: 9px 10px !important;
    margin: 0 !important;
    border-left: 3px solid transparent;
    transition: background 0.15s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
    background: rgba(255,255,255,0.05);
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: rgba(245,166,35,0.13);
    border-left: 3px solid #F5A623;
}
[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
    display: none;
}
[data-testid="stSidebar"] div[role="radiogroup"] label p {
    font-size: 13.8px;
    font-weight: 500;
    color: #D3DCEA;
    margin: 0;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
    color: #FFFFFF;
    font-weight: 600;
}

/* Expanders (report folders) */
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
}

/* Text input (report search) */
[data-testid="stSidebar"] input[type="text"] {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    color: #E9EEF6;
}

/* Dividers */
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.08) !important;
    margin: 14px 0 !important;
}

/* Caption / small text */
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {
    color: #7C8CA6 !important;
}
</style>
""", unsafe_allow_html=True)


# Full list of menu items that exist in the app (before role-based filtering).
# Used for routing below, and read by the User Management admin page so its
# checkboxes always match what's actually available here.
FULL_MENU_ITEMS = [
    "🏠 Overview",
    "📊 Comparison",
    "📈 Branch Analysis",
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


with st.sidebar:
    # ---- Profile card ----
    st.markdown(f"""
        <div class="sugam-profile-card">
            <div class="sugam-avatar">👤</div>
            <div class="sugam-profile-text">
                <div class="sugam-emp-id">Employee ID: {st.session_state['employee_id']}</div>
                <span class="sugam-role-badge">{role.title()}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    # ---- Brand lockup ----
    st.markdown("""
        <div class="sugam-brand">
            <div class="sugam-brand-icon">🚚</div>
            <div>
                <div class="sugam-brand-text">Logistics BI</div>
                <div class="sugam-brand-sub">Sugam Dashboard</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not allowed_menu:
        st.warning("No access has been assigned to your role yet. Contact the admin.")
        st.stop()

    st.markdown('<div class="sugam-section-label">Navigation</div>', unsafe_allow_html=True)
    menu = st.radio(
        "Navigation",
        allowed_menu,
        label_visibility="collapsed"
    )

    if menu == "📄 Reports":
        st.markdown('<div class="sugam-section-label">Search Report</div>', unsafe_allow_html=True)

        search_text = st.text_input("Search by report name", label_visibility="collapsed", placeholder="🔍 Search by report name")

        if search_text:
            for department, reports in REPORTS_VISIBLE.items():
                for report_name in reports.keys():
                    if search_text.lower() in report_name.lower():
                        if st.button(report_name, key=f"search_{report_name}", use_container_width=True):
                            st.session_state["selected_report"] = report_name
                            st.rerun()

        st.markdown('<div class="sugam-section-label">Report Folders</div>', unsafe_allow_html=True)

        if not REPORTS_VISIBLE:
            st.info("No reports assigned to your role.")
        else:
            for department, reports in REPORTS_VISIBLE.items():
                with st.expander(department, expanded=False):
                    for report_name in reports.keys():
                        if st.button(report_name, key=f"{department}_{report_name}", use_container_width=True):
                            st.session_state["selected_report"] = report_name
                            st.rerun()

    st.divider()

    st.markdown('<div class="sugam-section-label">Quick Actions</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        clear_role_cache()
        st.success("Data refreshed!")


if menu == "🏠 Overview":
    show_overview()

elif menu == "📊 Comparison":
    show_comparison()

elif menu == "📈 Branch Analysis":
    st.info("Branch Analysis page coming soon.")

elif menu == "👥 Customer Analysis":
    show_CustomerAnalysis()

elif menu == "🚛 Service Analysis":
    st.info("Service Analysis page coming soon.")

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