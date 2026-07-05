import json
import os
import streamlit as st

# Project root (one level up from services/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROLES_FILE = os.path.join(BASE_DIR, "config", "roles.json")
PERMISSIONS_FILE = os.path.join(BASE_DIR, "config", "role_permissions.json")
DATA_SCOPE_FILE = os.path.join(BASE_DIR, "config", "data_scope.json")

# Safest fallback role if an employee_id is missing from roles.json
DEFAULT_ROLE = "viewer"


@st.cache_data(show_spinner=False)
def load_roles():
    """Returns { "employee_id": "role_name", ... } from config/roles.json"""
    try:
        with open(ROLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        st.error("roles.json is not valid JSON. Please check the file.")
        return {}


@st.cache_data(show_spinner=False)
def load_permissions():
    """Returns { "role_name": {"menu": [...], "reports": [...]}, ... } from config/role_permissions.json"""
    try:
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        st.error("role_permissions.json is not valid JSON. Please check the file.")
        return {}


def get_role_for_employee(employee_id):
    """Looks up the role for a given employee_id. Falls back to DEFAULT_ROLE if not found."""
    roles = load_roles()
    return roles.get(str(employee_id), DEFAULT_ROLE)


def get_permissions_for_role(role):
    permissions = load_permissions()
    return permissions.get(role, permissions.get(DEFAULT_ROLE, {"menu": [], "reports": []}))


def get_allowed_menu(role):
    """Ordered list of sidebar menu items this role is allowed to see."""
    return get_permissions_for_role(role).get("menu", [])


def get_allowed_reports(role):
    """Set of report names (as used as keys inside REPORTS in app.py) this role can open."""
    return set(get_permissions_for_role(role).get("reports", []))


@st.cache_data(show_spinner=False)
def load_data_scope():
    """Returns { "employee_id": {"zone": "..."} | {"circle": "..."} | {"branch": "..."} | {}, ... }
    from config/data_scope.json. An empty dict {} (or the employee_id being absent entirely)
    means no restriction — that employee sees all data."""
    try:
        with open(DATA_SCOPE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        st.error("data_scope.json is not valid JSON. Please check the file.")
        return {}


def get_data_scope_for_employee(employee_id):
    """Returns the data-scope dict for this employee, e.g. {"zone": "Nepal Zone"}.
    Returns {} if the employee has no restriction (sees all data)."""
    scopes = load_data_scope()
    return scopes.get(str(employee_id), {})


def clear_role_cache():
    """Call this (e.g. from a 'Refresh Data' button) if roles.json / role_permissions.json / data_scope.json changed."""
    load_roles.clear()
    load_permissions.clear()
    load_data_scope.clear()