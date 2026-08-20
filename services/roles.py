import json
import os
import shutil
import tempfile
import streamlit as st

# Project root (one level up from services/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# In production set USER_MANAGEMENT_DATA_DIR to a persistent/mounted directory.
# The config directory remains the zero-configuration local-development fallback.
DATA_DIR = os.path.abspath(
    os.environ.get("USER_MANAGEMENT_DATA_DIR", os.path.join(BASE_DIR, "config"))
)
ROLES_FILE = os.path.join(DATA_DIR, "roles.json")
PERMISSIONS_FILE = os.path.join(DATA_DIR, "role_permissions.json")
DATA_SCOPE_FILE = os.path.join(DATA_DIR, "data_scope.json")

# Safest fallback role if an employee_id is missing from roles.json
DEFAULT_ROLE = "viewer"


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default.copy()
    except json.JSONDecodeError:
        backup = f"{path}.bak"
        try:
            with open(backup, "r", encoding="utf-8") as f:
                recovered = json.load(f)
            st.warning(f"Recovered {os.path.basename(path)} from its last valid backup.")
            return recovered
        except (FileNotFoundError, json.JSONDecodeError):
            st.error(f"{os.path.basename(path)} is not valid JSON and no valid backup exists.")
            return default.copy()


def _atomic_save_json(path, data):
    """Atomically write, verify and back up a JSON configuration file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".user_mgmt_", suffix=".json", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        with open(temp_path, "r", encoding="utf-8") as handle:
            verified = json.load(handle)
        if verified != data:
            raise IOError("Saved data verification failed")
        if os.path.exists(path):
            shutil.copy2(path, f"{path}.bak")
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@st.cache_data(show_spinner=False)
def load_roles():
    """Returns {employee_id: role_name}."""
    return _load_json(ROLES_FILE, {})


@st.cache_data(show_spinner=False)
def load_permissions():
    return _load_json(PERMISSIONS_FILE, {})


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
    return _load_json(DATA_SCOPE_FILE, {})


def save_roles(data):
    _atomic_save_json(ROLES_FILE, data)
    clear_role_cache()


def save_permissions(data):
    _atomic_save_json(PERMISSIONS_FILE, data)
    clear_role_cache()


def save_data_scope(data):
    _atomic_save_json(DATA_SCOPE_FILE, data)
    clear_role_cache()


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
