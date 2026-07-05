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
    st.write(f"👤 Employee ID: {st.session_state['employee_id']}")
    st.caption(f"Role: {role.title()}")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("## 🚚 Logistics BI")

    if not allowed_menu:
        st.warning("No access has been assigned to your role yet. Contact the admin.")
        st.stop()

    menu = st.radio(
        "Navigation",
        allowed_menu
    )

    if menu == "📄 Reports":
        st.markdown("### 🔍 Search Report")

        search_text = st.text_input("Search by report name")

        if search_text:
            for department, reports in REPORTS_VISIBLE.items():
                for report_name in reports.keys():
                    if search_text.lower() in report_name.lower():
                        if st.button(report_name, key=f"search_{report_name}", use_container_width=True):
                            st.session_state["selected_report"] = report_name
                            st.rerun()

        st.markdown("### 📁 Report Folders")

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

    st.markdown("#### Quick Actions")

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