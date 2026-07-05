import json
import pandas as pd
import streamlit as st

from services.roles import (
    ROLES_FILE,
    PERMISSIONS_FILE,
    DATA_SCOPE_FILE,
    load_roles,
    load_permissions,
    load_data_scope,
    clear_role_cache,
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


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def show_UserManagement():
    # Extra defense-in-depth: even if role_permissions.json is ever
    # misconfigured, only admins can actually use this page.
    if st.session_state.get("role") != "admin":
        st.error("Only admins can access User Management.")
        st.stop()

    st.markdown("### 🛠️ User Management")
    st.caption("Manage which employees have which role, and what each role is allowed to see.")

    all_menu_items = st.session_state.get("_all_menu_items", FALLBACK_MENU_ITEMS)
    all_reports = st.session_state.get("_all_reports", FALLBACK_REPORTS)

    tab1, tab2, tab3 = st.tabs(["👤 Employee Roles", "🔐 Role Permissions", "📍 Data Scope"])

    # =====================================================
    # Tab 1: Employee ID -> Role  (config/roles.json)
    # =====================================================
    with tab1:
        roles = load_roles()
        permissions = load_permissions()
        role_options = list(permissions.keys()) or ["viewer"]

        st.markdown("#### Employees")
        st.caption("Add, edit, or remove rows below, then click Save.")

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
                _save_json(ROLES_FILE, new_roles)
                clear_role_cache()
                st.success("Employee roles saved.")
                st.rerun()

    # =====================================================
    # Tab 2: Role -> Menu + Reports  (config/role_permissions.json)
    # =====================================================
    with tab2:
        permissions = load_permissions()
        role_names = list(permissions.keys())

        st.markdown("#### Select a role to edit, or create a new one")

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
            default=[m for m in current_menu if m in all_menu_items]
        )

        report_selection = st.multiselect(
            "Allowed reports",
            all_reports,
            default=[r for r in current_reports if r in all_reports]
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
                    _save_json(PERMISSIONS_FILE, permissions)
                    clear_role_cache()
                    st.success(f"Role '{target_role}' saved.")
                    st.rerun()

        with col_delete:
            if selected != "➕ Create new role":
                if st.button("🗑️ Delete Role", use_container_width=True):
                    if selected == "admin":
                        st.error("The 'admin' role cannot be deleted — you'd lock yourself out.")
                    else:
                        permissions.pop(selected, None)
                        _save_json(PERMISSIONS_FILE, permissions)
                        clear_role_cache()
                        st.warning(f"Role '{selected}' deleted.")
                        st.rerun()

        st.divider()
        st.markdown("##### Preview")
        st.json({target_role or "(unnamed)": {"menu": menu_selection, "reports": report_selection}})

    # =====================================================
    # Tab 3: Employee -> Data Scope (zone/circle/branch)  (config/data_scope.json)
    # =====================================================
    with tab3:
        st.markdown("#### Restrict employees to a specific Zone / Circle / Branch")
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
                _save_json(DATA_SCOPE_FILE, new_scope)
                clear_role_cache()
                st.success("Data scope saved. Affected employees will see the restriction on next login.")
                st.rerun()