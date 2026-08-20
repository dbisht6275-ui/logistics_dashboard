import base64
import json
import os
import shutil
import tempfile
import requests
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

GITHUB_PATHS = {
    "roles": "config/roles.json",
    "permissions": "config/role_permissions.json",
    "scope": "config/data_scope.json",
}


def _github_settings():
    """Read GitHub persistence settings without ever logging the token."""
    try:
        section = st.secrets.get("user_management", {})
        repository = str(section.get("repository", "")).strip()
        branch = str(section.get("branch", "main")).strip() or "main"
        token = str(section.get("github_token", "")).strip()
    except Exception:
        return None
    if not repository or "/" not in repository or not token:
        return None
    return {"repository": repository, "branch": branch, "token": token}


def github_storage_enabled():
    return _github_settings() is not None


def _github_headers(token):
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "streamlit-user-management",
    }


def _github_content_url(settings, repo_path):
    return (
        f"https://api.github.com/repos/{settings['repository']}"
        f"/contents/{repo_path}"
    )


def _github_load_json(repo_path, default):
    settings = _github_settings()
    if settings is None:
        return None
    response = requests.get(
        _github_content_url(settings, repo_path),
        headers=_github_headers(settings["token"]),
        params={"ref": settings["branch"]},
        timeout=20,
    )
    if response.status_code == 404:
        return default.copy()
    response.raise_for_status()
    payload = response.json()
    decoded = base64.b64decode(payload["content"]).decode("utf-8")
    return json.loads(decoded)


def _github_save_json(repo_path, data, label):
    """Create/update a repository JSON file, retrying one SHA conflict."""
    settings = _github_settings()
    if settings is None:
        raise RuntimeError(
            "GitHub persistence is not configured in Streamlit Secrets."
        )
    url = _github_content_url(settings, repo_path)
    headers = _github_headers(settings["token"])
    encoded = base64.b64encode(
        (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    ).decode("ascii")

    for attempt in range(2):
        current = requests.get(
            url,
            headers=headers,
            params={"ref": settings["branch"]},
            timeout=20,
        )
        if current.status_code not in (200, 404):
            current.raise_for_status()
        body = {
            "message": f"Update {label} from User Management",
            "content": encoded,
            "branch": settings["branch"],
        }
        if current.status_code == 200:
            body["sha"] = current.json()["sha"]
        saved = requests.put(url, headers=headers, json=body, timeout=30)
        if saved.status_code in (200, 201):
            return
        if saved.status_code in (409, 422) and attempt == 0:
            continue
        saved.raise_for_status()
    raise RuntimeError(f"Could not save {label} after retrying a GitHub conflict.")


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
    if github_storage_enabled():
        try:
            return _github_load_json(GITHUB_PATHS["roles"], {})
        except (requests.RequestException, ValueError, KeyError) as exc:
            st.warning(f"GitHub roles could not be loaded; using local fallback. ({exc})")
    return _load_json(ROLES_FILE, {})


@st.cache_data(show_spinner=False)
def load_permissions():
    if github_storage_enabled():
        try:
            return _github_load_json(GITHUB_PATHS["permissions"], {})
        except (requests.RequestException, ValueError, KeyError) as exc:
            st.warning(f"GitHub permissions could not be loaded; using local fallback. ({exc})")
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
    if github_storage_enabled():
        try:
            return _github_load_json(GITHUB_PATHS["scope"], {})
        except (requests.RequestException, ValueError, KeyError) as exc:
            st.warning(f"GitHub data scope could not be loaded; using local fallback. ({exc})")
    return _load_json(DATA_SCOPE_FILE, {})


def save_roles(data):
    if github_storage_enabled():
        _github_save_json(GITHUB_PATHS["roles"], data, "employee roles")
    _atomic_save_json(ROLES_FILE, data)
    clear_role_cache()


def save_permissions(data):
    if github_storage_enabled():
        _github_save_json(GITHUB_PATHS["permissions"], data, "role permissions")
    _atomic_save_json(PERMISSIONS_FILE, data)
    clear_role_cache()


def save_data_scope(data):
    if github_storage_enabled():
        _github_save_json(GITHUB_PATHS["scope"], data, "employee data scope")
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
