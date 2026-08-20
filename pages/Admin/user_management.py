import pandas as pd
import streamlit as st

from services.roles import (
    load_roles,
    load_permissions,
    load_data_scope,
    save_roles,
    save_permissions,
    save_data_scope,
    DATA_DIR,
)

# Fallback lists used only if app.py hasn't populated session_state yet
# (app.py sets these automatically so this admin page always stays in
# sync with whatever menu items / reports actually exist in the app)
FALLBACK_MENU_ITEMS = [
    "🏠 Overview",
    "📊 Comparison",
    "📈 Branch Analysis",
    "👥 Customer Analysis",
    "🚛 Service Analysis",
    "📄 Reports",
    "🛠️ User Management",
]

FALLBACK_REPORTS = [
    "📊 Zone Booking Turnover",
    "📋 GR Costing Head Wise",
]


def _inject_user_management_css():
    st.markdown("""
    <style>
    .um-hero{padding:20px 24px;border:1px solid #dbe7f3;border-radius:14px;
      background:linear-gradient(135deg,#f8fbff 0%,#eef6ff 100%);margin-bottom:16px}
    .um-title{font-size:28px;font-weight:750;color:#102a43;margin:0}
    .um-subtitle{color:#627d98;margin-top:5px;font-size:14px}
    .um-card-title{font-size:18px;font-weight:700;color:#163a5f;margin-bottom:2px}
    .um-card-note{font-size:13px;color:#718096;margin-bottom:14px}
    div[data-testid="stDataEditor"]{border:1px solid #dbe7f3;border-radius:12px;overflow:hidden}
    div[data-testid="stTabs"] button[role="tab"]{font-weight:650;padding:12px 18px}
    div[data-testid="stTabs"] button[aria-selected="true"]{color:#1261a0;border-bottom-color:#1261a0}
    div[data-testid="stMetric"]{background:#fff;border:1px solid #dbe7f3;border-radius:12px;padding:12px 16px}
    </style>
    """, unsafe_allow_html=True)


def show_UserManagement():
    # Extra defense-in-depth: even if role_permissions.json is ever
    # misconfigured, only admins can actually use this page.
    if st.session_state.get("role") != "admin":
        st.error("Only admins can access User Management.")
        st.stop()

    _inject_user_management_css()
    st.markdown("""
    <div class="um-hero"><div class="um-title">🛡️ User Access Management</div>
    <div class="um-subtitle">Control employee roles, module permissions and operational data access from one secure workspace.</div></div>
    """, unsafe_allow_html=True)

    all_menu_items = st.session_state.get("_all_menu_items", FALLBACK_MENU_ITEMS)
    all_reports = st.session_state.get("_all_reports", FALLBACK_REPORTS)

    summary_roles = load_roles()
    summary_permissions = load_permissions()
    summary_scopes = load_data_scope()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Employees", len(summary_roles))
    m2.metric("Access Roles", len(summary_permissions))
    m3.metric("Restricted Users", sum(bool(v) for v in summary_scopes.values()))
    m4.metric("Storage", "Persistent" if "USER_MANAGEMENT_DATA_DIR" in __import__("os").environ else "Local")

    tab1, tab2, tab3 = st.tabs(["👤 Employee Roles", "🔐 Role Permissions", "📍 Data Scope"])

    # =====================================================
    # Tab 1: Employee ID -> Role  (config/roles.json)
    # =====================================================
    with tab1:
        roles = load_roles()
        permissions = load_permissions()
        role_options = list(permissions.keys()) or ["viewer"]

        st.markdown('<div class="um-card-title">Employee Role Directory</div>', unsafe_allow_html=True)
        st.markdown('<div class="um-card-note">Add, edit or remove employee access assignments, then save the verified directory.</div>', unsafe_allow_html=True)

        rows = [{"Employee ID": emp_id, "Role": role} for emp_id, role in roles.items()]
        roles_df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Employee ID", "Role"])

        edited_df = st.data_editor(
            roles_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Employee ID": st.column_config.TextColumn("Employee ID", required=True),
                "Role": st.column_config.SelectboxColumn("Role", options=role_options, required=True),
            },
            key="roles_editor"
        )

        if st.button("💾 Save Employee Roles", type="primary"):
            new_roles = {}
            has_error = False

            for _, row in edited_df.iterrows():
                emp_id = str(row.get("Employee ID", "")).strip()
                role = row.get("Role")

                if not emp_id:
                    continue

                if role not in role_options:
                    st.error(f"Unknown role '{role}' for employee {emp_id}. Create that role first in the 'Role Permissions' tab.")
                    has_error = True
                    continue

                new_roles[emp_id] = role

            if not has_error:
                save_roles(new_roles)
                st.success("Employee roles saved.")
                st.rerun()

    # =====================================================
    # Tab 2: Role -> Menu + Reports  (config/role_permissions.json)
    # =====================================================
    with tab2:
        permissions = load_permissions()
        role_names = list(permissions.keys())

        st.markdown('<div class="um-card-title">Role Permission Matrix</div>', unsafe_allow_html=True)
        st.markdown('<div class="um-card-note">Choose a role and assign only the modules and reports required for that job.</div>', unsafe_allow_html=True)

        selected = st.selectbox("Role", role_names + ["➕ Create new role"])

        if selected == "➕ Create new role":
            new_role_name = st.text_input(
                "New role name (lowercase, no spaces)",
                placeholder="e.g. branch_head"
            )
            target_role = new_role_name.strip().lower().replace(" ", "_")
            current_menu, current_reports = [], []
        else:
            target_role = selected
            current_menu = permissions.get(selected, {}).get("menu", [])
            current_reports = permissions.get(selected, {}).get("reports", [])

        menu_selection = st.multiselect(
            "Allowed sidebar menu items",
            all_menu_items,
            default=[m for m in current_menu if m in all_menu_items],
            key=f"permission_menu_{target_role or 'new'}",
        )

        report_selection = st.multiselect(
            "Allowed reports",
            all_reports,
            default=[r for r in current_reports if r in all_reports],
            key=f"permission_reports_{target_role or 'new'}",
        )

        col_save, col_delete = st.columns(2)

        with col_save:
            if st.button("💾 Save Role", type="primary", use_container_width=True):
                if not target_role:
                    st.error("Please enter a role name.")
                else:
                    permissions[target_role] = {
                        "menu": menu_selection,
                        "reports": report_selection,
                    }
                    save_permissions(permissions)
                    st.success(f"Role '{target_role}' saved.")
                    st.rerun()

        with col_delete:
            if selected != "➕ Create new role":
                if st.button("🗑️ Delete Role", use_container_width=True):
                    if selected == "admin":
                        st.error("The 'admin' role cannot be deleted — you'd lock yourself out.")
                    else:
                        permissions.pop(selected, None)
                        save_permissions(permissions)
                        st.warning(f"Role '{selected}' deleted.")
                        st.rerun()

        st.divider()
        st.markdown("##### Preview")
        st.json({target_role or "(unnamed)": {"menu": menu_selection, "reports": report_selection}})

    # =====================================================
    # Tab 3: Employee -> Data Scope (zone/circle/branch)  (config/data_scope.json)
    # =====================================================
    with tab3:
        st.markdown('<div class="um-card-title">Employee Data Scope</div>', unsafe_allow_html=True)
        st.caption(
            "Leave 'Scope Type' as None to give an employee full data access (no restriction). "
            "Value must match the exact spelling used in the data (e.g. 'Nepal Zone', 'NCR Circle', 'Noida')."
        )

        data_scope = load_data_scope()

        scope_rows = []
        for emp_id, scope in data_scope.items():
            if not scope:
                scope_rows.append({"Employee ID": emp_id, "Scope Type": "None", "Value": ""})
            else:
                # scope is expected to have exactly one key: zone / circle / branch
                key = next(iter(scope), None)
                scope_rows.append({
                    "Employee ID": emp_id,
                    "Scope Type": key.capitalize() if key else "None",
                    "Value": scope.get(key, "") if key else ""
                })

        scope_df = pd.DataFrame(scope_rows) if scope_rows else pd.DataFrame(
            columns=["Employee ID", "Scope Type", "Value"]
        )

        edited_scope_df = st.data_editor(
            scope_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Employee ID": st.column_config.TextColumn("Employee ID", required=True),
                "Scope Type": st.column_config.SelectboxColumn(
                    "Scope Type", options=["None", "Zone", "Circle", "Branch"], required=True
                ),
                "Value": st.column_config.TextColumn(
                    "Value", help="e.g. Nepal Zone / NCR Circle / Noida — leave blank if Scope Type is None"
                ),
            },
            key="data_scope_editor"
        )

        if st.button("💾 Save Data Scope", type="primary"):
            new_scope = {}
            has_error = False

            for _, row in edited_scope_df.iterrows():
                emp_id = str(row.get("Employee ID", "")).strip()
                scope_type = row.get("Scope Type", "None")
                value = str(row.get("Value", "")).strip()

                if not emp_id:
                    continue

                if scope_type == "None" or not value:
                    new_scope[emp_id] = {}
                else:
                    new_scope[emp_id] = {scope_type.lower(): value}

            if not has_error:
                save_data_scope(new_scope)
                st.success("Data scope saved. Affected employees will see the restriction on next login.")
                st.rerun()
