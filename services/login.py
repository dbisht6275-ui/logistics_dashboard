import time
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.roles import (
    get_role_for_employee,
    get_data_scope_for_employee,
)


def check_login(username: str, password: str):
    """
    Validate username and password from USERMAST.

    Current behaviour preserved from the original code:
    - Username is case-insensitive.
    - Password is case-insensitive.
    - Leading/trailing spaces are ignored.
    - Expired users are not allowed.
    - Employee name is retrieved from EMPLOYEEMAST.
    """
    try:
        clean_username = username.strip()
        clean_password = password.strip()

        engine = get_engine()

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT TOP 1
                        U.USERNAME,
                        U.EMPLOYEEID,
                        EMP.EMPNAME AS EMPLOYEE_NAME
                    FROM USERMAST U
                    INNER JOIN EMPLOYEEMAST EMP
                        ON EMP.EMPLOYEEID = U.EMPLOYEEID
                    WHERE LOWER(LTRIM(RTRIM(U.USERNAME))) =
                          LOWER(LTRIM(RTRIM(:username)))
                      AND LOWER(LTRIM(RTRIM(U.PASSWORD))) =
                          LOWER(LTRIM(RTRIM(:password)))
                      AND (
                            U.EXPIRED IS NULL
                            OR LOWER(LTRIM(RTRIM(U.EXPIRED))) <> 'y'
                          )
                    """
                ),
                {
                    "username": clean_username,
                    "password": clean_password,
                },
            )

            row = result.mappings().first()

        if row:
            return True, row["EMPLOYEEID"], row["EMPLOYEE_NAME"]

        return False, None, None

    except Exception as e:
        st.error(f"Database error: {e}")
        return False, None, None


def login_page():
    """Display a compact, responsive Streamlit login page."""

    st.set_page_config(
        page_title="Sugam Group | Login",
        page_icon="🔐",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    st.markdown(
        """
<style>
/* ---------- App ---------- */
.stApp {
    background:
        radial-gradient(circle at 10% 5%, rgba(64,153,255,.14), transparent 30%),
        radial-gradient(circle at 92% 94%, rgba(27,91,211,.12), transparent 32%),
        linear-gradient(145deg, #f7faff 0%, #eef5ff 100%);
}

#MainMenu, header, footer {
    visibility: hidden;
}

.main .block-container,
[data-testid="stMainBlockContainer"] {
    max-width: 450px;
    padding-top: 2.25rem;
    padding-bottom: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

/* ---------- Brand ---------- */
.sg-brand {
    text-align: center;
    margin: 0 0 .75rem 0;
}

.sg-logo {
    width: 64px;
    height: 64px;
    margin: 0 auto .55rem auto;
    border-radius: 19px;
    background: linear-gradient(145deg, #159be8 0%, #194fc6 100%);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -1.5px;
    box-shadow: 0 12px 28px rgba(31,94,216,.25), inset 0 1px 0 rgba(255,255,255,.3);
}

.sg-name {
    color: #102a56;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 2.7px;
    line-height: 1.1;
}

.sg-tagline {
    color: #71809a;
    font-size: 9px;
    letter-spacing: 2.2px;
    margin-top: 5px;
}

.sg-title {
    color: #10233f;
    font-size: 24px;
    font-weight: 750;
    line-height: 1.15;
    margin-top: 1.1rem;
}

.sg-subtitle {
    color: #778398;
    font-size: 13px;
    margin-top: .25rem;
}

.sg-secure {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    margin-top: .7rem;
    padding: 5px 10px;
    border-radius: 999px;
    background: rgba(231,242,255,.95);
    border: 1px solid rgba(84,148,224,.16);
    color: #46617f;
    font-size: 12px;
}

/* ---------- Form card ---------- */
[data-testid="stForm"] {
    background: rgba(255,255,255,.98);
    border: 1px solid rgba(215,225,239,.95) !important;
    border-radius: 20px;
    padding: 1.35rem 1.35rem 1.05rem 1.35rem;
    box-shadow: 0 18px 48px rgba(31,55,86,.12), 0 2px 8px rgba(31,55,86,.04);
}

.field-heading {
    color: #20324d;
    font-size: 13px;
    font-weight: 650;
    margin: 0 0 5px 1px;
}

div[data-baseweb="input"] > div {
    background: #f7f9fc;
    border: 1px solid #e2e9f2;
    border-radius: 10px;
    min-height: 44px;
}

div[data-baseweb="input"] > div:focus-within {
    border-color: #3987e8;
    background: #fff;
    box-shadow: 0 0 0 3px rgba(57,135,232,.12);
}

div[data-baseweb="input"] input {
    color: #25364f;
    font-size: 14px;
}

div[data-baseweb="input"] input::placeholder {
    color: #98a3b3;
}

div[data-testid="stTextInput"] label {
    display: none;
}

button[kind="primaryFormSubmit"] {
    width: 100%;
    min-height: 44px;
    border: 0;
    border-radius: 11px;
    background: linear-gradient(100deg, #168fdf, #2058cf);
    color: white;
    font-size: 14px;
    font-weight: 750;
    letter-spacing: .4px;
    box-shadow: 0 9px 20px rgba(36,100,220,.24);
    transition: transform .16s ease, box-shadow .16s ease, background .16s ease;
}

button[kind="primaryFormSubmit"]:hover {
    border: 0;
    color: white;
    background: linear-gradient(100deg, #1184d9, #1d58cf);
    transform: translateY(-1px);
    box-shadow: 0 11px 24px rgba(36,100,220,.28);
}

button[kind="primaryFormSubmit"]:active {
    transform: translateY(0);
}

button[kind="primaryFormSubmit"]:focus-visible {
    outline: 3px solid rgba(57,135,232,.22);
    outline-offset: 2px;
}

.sg-safe {
    text-align: center;
    color: #718096;
    font-size: 11px;
    margin-top: .7rem;
}

.sg-restricted {
    background: rgba(237,246,255,.90);
    border: 1px solid #dcecff;
    border-radius: 12px;
    padding: 9px 12px;
    margin-top: .7rem;
    text-align: center;
    color: #5a6d86;
    font-size: 10.5px;
    line-height: 1.45;
}

.sg-restricted strong {
    color: #355273;
    font-size: 11px;
}

.sg-footer {
    text-align: center;
    color: #8a96a8;
    font-size: 9.5px;
    margin-top: .65rem;
    line-height: 1.45;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
    margin-top: .65rem;
}

/* Circular progress indicator displayed while authentication is running. */
div[data-testid="stSpinner"] {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: .65rem;
    margin: .8rem auto .1rem auto;
    color: #365a87;
    font-size: 13px;
    font-weight: 650;
}

div[data-testid="stSpinner"] svg {
    color: #1f67d7;
}

/* ---------- Small screens ---------- */
@media (max-width: 600px) {
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        max-width: 100%;
        padding-top: .7rem;
        padding-left: .75rem;
        padding-right: .75rem;
        padding-bottom: .6rem;
    }

    .sg-logo {
        width: 50px;
        height: 50px;
        border-radius: 14px;
        font-size: 22px;
        margin-bottom: .4rem;
    }

    .sg-name {
        font-size: 17px;
        letter-spacing: 2.1px;
    }

    .sg-tagline {
        font-size: 8px;
        letter-spacing: 1.7px;
    }

    .sg-title {
        font-size: 21px;
        margin-top: .75rem;
    }

    .sg-subtitle {
        font-size: 12px;
    }

    [data-testid="stForm"] {
        border-radius: 15px;
        padding: .95rem .9rem .8rem .9rem;
    }

    div[data-baseweb="input"] > div,
    button[kind="primaryFormSubmit"] {
        min-height: 42px;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )

    # IMPORTANT:
    # Keep the HTML at the left edge of the string.
    # Indented HTML can be rendered by Markdown as a literal code block.
    st.markdown(
        """<div class="sg-brand">
<div class="sg-logo">SG</div>
<div class="sg-name">SUGAM GROUP</div>
<div class="sg-title">Logistics Analytics Portal</div>
<div class="sg-secure"><span>✓</span><span>Secure login to continue</span></div>
</div>""",
        unsafe_allow_html=True,
    )

    with st.form(key="login_form", clear_on_submit=False):
        st.markdown(
            '<div class="field-heading">Username</div>',
            unsafe_allow_html=True,
        )
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username",
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="field-heading" style="margin-top:7px;">Password</div>',
            unsafe_allow_html=True,
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password",
            label_visibility="collapsed",
        )

        login_clicked = st.form_submit_button(
            "SIGN IN  →",
            width="stretch",
        )

        st.markdown(
            '<div class="sg-safe">🛡 Your data is safe and secure</div>',
            unsafe_allow_html=True
        )

    st.markdown(
        """<div class="sg-restricted">
<strong>🔒 Restricted Access</strong><br>
This system is for authorized users only. Dashboard access is subject to company security policies.
</div>""",
        unsafe_allow_html=True,
    )

    if login_clicked:
        if not username.strip() or not password.strip():
            st.warning("Please enter username and password.")
            return

        login_started = time.perf_counter()

        # The spinner remains visible through authentication and access setup.
        with st.spinner("Signing you in securely..."):
            success, employee_id, employee_name = check_login(
                username=username,
                password=password,
            )

            auth_seconds = time.perf_counter() - login_started

            if success:
                try:
                    access_started = time.perf_counter()

                # Role and data-scope are independent lookups. Fetch them in
                # parallel so login waits for the slower lookup instead of the
                # sum of both lookup times.
                    with ThreadPoolExecutor(
                        max_workers=2,
                        thread_name_prefix="login-access",
                    ) as executor:
                        role_future = executor.submit(
                            get_role_for_employee,
                            employee_id,
                        )
                        scope_future = executor.submit(
                            get_data_scope_for_employee,
                            employee_id,
                        )

                        role = role_future.result()
                        data_scope = scope_future.result()

                    access_seconds = time.perf_counter() - access_started

                    st.session_state["logged_in"] = True
                    st.session_state["employee_id"] = employee_id
                    st.session_state["employee_name"] = (
                        employee_name if employee_name else username.strip()
                    )
                    st.session_state["role"] = role
                    st.session_state["data_scope"] = data_scope
                    st.session_state["username"] = username.strip()

                    print(
                        f"[Login Timing] auth={auth_seconds:.2f}s | "
                        f"access={access_seconds:.2f}s | "
                        f"total={time.perf_counter() - login_started:.2f}s"
                    )

                    st.rerun()

                except Exception as e:
                    st.session_state["logged_in"] = False
                    st.error(
                        "Login successful, but user access could not be loaded: "
                        f"{e}"
                    )
            else:
                st.error("Invalid username or password.")


if __name__ == "__main__":
    login_page()
