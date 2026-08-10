import streamlit as st
from sqlalchemy import text
from textwrap import dedent

from services.database import get_engine
from services.roles import (
    get_role_for_employee,
    get_data_scope_for_employee,
)


def check_login(username: str, password: str):
    """
    Validate username and password from USERMAST.

    Login behaviour:
    - Username is case-insensitive.
    - Password is case-insensitive.
    - Leading and trailing spaces are ignored.
    - Expired users are not allowed.
    - Employee name is retrieved from EMPLOYEEMAST.

    Returns:
        tuple:
            (True, employee_id, employee_name) when login succeeds.
            (False, None, None) when login fails.
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
            employee_id = row["EMPLOYEEID"]
            employee_name = row["EMPLOYEE_NAME"]

            return True, employee_id, employee_name

        return False, None, None

    except Exception as e:
        st.error(f"Database error: {e}")
        return False, None, None


def login_page():
    """
    Display the Streamlit login page and authenticate the user.
    """

    st.markdown(
        dedent(
            """
            <style>
                /* ---------- Page ---------- */
                .stApp {
                    background:
                        radial-gradient(circle at 5% 5%, rgba(219, 239, 255, 0.75), transparent 28%),
                        radial-gradient(circle at 95% 95%, rgba(224, 241, 255, 0.8), transparent 30%),
                        #f8fbff;
                }

                .main .block-container {
                    width: 100%;
                    max-width: 100%;
                    padding-top: 28px;
                    padding-bottom: 24px;
                    padding-left: 18px;
                    padding-right: 18px;
                    box-sizing: border-box;
                }

                /* Center the login content and keep it compact on desktop */
                .login-shell {
                    width: 100%;
                    max-width: 460px;
                    margin: 0 auto;
                }

                /* Hide Streamlit's default chrome */
                #MainMenu {visibility: hidden;}
                header {visibility: hidden;}
                footer {visibility: hidden;}

                /* ---------- Header / Brand ---------- */
                .brand-area {
                    text-align: center;
                    padding: 8px 0 20px 0;
                }

                .brand-logo {
                    width: 68px;
                    height: 68px;
                    margin: 0 auto 10px auto;
                    border-radius: 20px;
                    background: linear-gradient(145deg, #1597e8, #1f5ed8);
                    color: white;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 30px;
                    font-weight: 800;
                    letter-spacing: -2px;
                    box-shadow: 0 10px 25px rgba(31, 94, 216, 0.25);
                }

                .brand-name {
                    color: #102a56;
                    font-size: 23px;
                    font-weight: 800;
                    letter-spacing: 3px;
                    margin: 0;
                }

                .brand-tagline {
                    color: #71809a;
                    font-size: 12px;
                    letter-spacing: 2.5px;
                    margin-top: 4px;
                }

                .portal-title {
                    color: #10233f;
                    font-size: 31px;
                    font-weight: 750;
                    text-align: center;
                    margin-top: 20px;
                    line-height: 1.2;
                }

                .portal-subtitle {
                    color: #778398;
                    font-size: 15px;
                    text-align: center;
                    margin-top: 7px;
                }

                .secure-line {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 9px;
                    color: #52657f;
                    font-size: 14px;
                    margin: 18px 0 20px 0;
                }

                .secure-icon {
                    width: 25px;
                    height: 25px;
                    border-radius: 50%;
                    background: #e8f3ff;
                    color: #1769d2;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                }

                /* ---------- Login Card ---------- */
                .login-card {
                    background: rgba(255, 255, 255, 0.96);
                    border: 1px solid #e4ebf4;
                    border-radius: 24px;
                    padding: 28px 28px 24px 28px;
                    box-shadow: 0 18px 50px rgba(31, 55, 86, 0.12);
                    margin: 0 auto;
                }

                .field-heading {
                    color: #20324d;
                    font-size: 14px;
                    font-weight: 650;
                    margin: 2px 0 7px 0;
                }

                /* Streamlit inputs */
                div[data-baseweb="input"] {
                    border-radius: 12px;
                }

                div[data-baseweb="input"] > div {
                    background: #f5f8fc;
                    border: 1px solid #e2e9f2;
                    border-radius: 12px;
                    min-height: 50px;
                }

                div[data-baseweb="input"] > div:focus-within {
                    border-color: #3987e8;
                    box-shadow: 0 0 0 3px rgba(57, 135, 232, 0.12);
                }

                div[data-baseweb="input"] input {
                    color: #25364f;
                    font-size: 15px;
                }

                div[data-baseweb="input"] input::placeholder {
                    color: #98a3b3;
                }

                /* Remove default Streamlit label because custom labels are used */
                div[data-testid="stTextInput"] label {
                    display: none;
                }

                /* Login button */
                div.stButton > button,
                button[kind="primaryFormSubmit"] {
                    width: 100%;
                    min-height: 50px;
                    background: linear-gradient(100deg, #188fe6, #2464dc);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 700;
                    letter-spacing: 0.3px;
                    box-shadow: 0 10px 22px rgba(36, 100, 220, 0.22);
                    transition: all 0.2s ease;
                }

                div.stButton > button:hover,
                button[kind="primaryFormSubmit"]:hover {
                    color: white;
                    border: none;
                    transform: translateY(-1px);
                    box-shadow: 0 13px 26px rgba(36, 100, 220, 0.28);
                    background: linear-gradient(100deg, #1184d9, #1d58cf);
                }

                div.stButton > button:active,
                button[kind="primaryFormSubmit"]:active {
                    color: white;
                    transform: translateY(0);
                }

                /* Space around form elements */
                div[data-testid="stForm"] {
                    border: 0;
                    padding: 0;
                    background: transparent;
                }

                .safe-note {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                    color: #718096;
                    font-size: 12px;
                    margin-top: 20px;
                    padding-top: 18px;
                    border-top: 1px solid #edf1f6;
                }

                .safe-shield {
                    color: #2474d8;
                    font-size: 15px;
                }

                /* ---------- Restricted Access ---------- */
                .restricted-box {
                    background: #edf6ff;
                    border: 1px solid #dcecff;
                    border-radius: 16px;
                    padding: 14px 16px;
                    margin-top: 18px;
                    text-align: center;
                    color: #5a6d86;
                    font-size: 12px;
                    line-height: 1.55;
                }

                .restricted-title {
                    color: #355273;
                    font-weight: 700;
                    font-size: 13px;
                    margin-bottom: 2px;
                }

                .footer-note {
                    text-align: center;
                    color: #8a96a8;
                    font-size: 11px;
                    margin-top: 22px;
                    line-height: 1.7;
                }

                /* Error / warning polish */
                div[data-testid="stAlert"] {
                    border-radius: 12px;
                    margin-top: 12px;
                }

                /* ---------- Mobile ---------- */
                /* Desktop */
                @media (min-width: 901px) {
                    .main .block-container {
                        padding-top: 45px;
                    }

                    .brand-area {
                        padding-bottom: 24px;
                    }

                    .portal-title {
                        font-size: 34px;
                    }

                    .login-card {
                        padding: 30px 30px 25px 30px;
                    }
                }

                /* Tablet */
                @media (min-width: 601px) and (max-width: 900px) {
                    .login-shell {
                        max-width: 470px;
                    }
                }

                /* Mobile */
                @media (max-width: 600px) {
                    .main .block-container {
                        padding-top: 14px;
                        padding-left: 12px;
                        padding-right: 12px;
                        padding-bottom: 16px;
                    }

                    .login-shell {
                        width: 100%;
                        max-width: 100%;
                    }

                    .brand-area {
                        padding-bottom: 10px;
                    }

                    .brand-logo {
                        width: 58px;
                        height: 58px;
                        border-radius: 17px;
                        font-size: 25px;
                    }

                    .brand-name {
                        font-size: 19px;
                        letter-spacing: 2.2px;
                    }

                    .brand-tagline {
                        font-size: 9px;
                        letter-spacing: 1.8px;
                    }

                    .portal-title {
                        font-size: 26px;
                        margin-top: 15px;
                    }

                    .portal-subtitle {
                        font-size: 13px;
                    }

                    .secure-line {
                        margin: 14px 0 16px 0;
                        font-size: 13px;
                    }

                    .login-card {
                        width: 100%;
                        border-radius: 19px;
                        padding: 22px 17px 19px 17px;
                    }

                    div[data-baseweb="input"] > div {
                        min-height: 48px;
                    }

                    div.stButton > button,
                    button[kind="primaryFormSubmit"] {
                        min-height: 49px;
                    }

                    .restricted-box {
                        margin-top: 14px;
                        padding: 12px 12px;
                    }

                    .footer-note {
                        margin-top: 17px;
                    }
                }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )

    # ---------- Brand / Portal Header ----------
    st.markdown(
        """
        <div class="brand-area">
            <div class="brand-logo">SG</div>
            <div class="brand-name">SUGAM GROUP</div>
            <div class="brand-tagline">REDEFINING LOGISTICS</div>

            <div class="portal-title">Logistics Analytics Portal</div>
            <div class="portal-subtitle">Business Intelligence Dashboard</div>

            <div class="secure-line">
                <span class="secure-icon">✓</span>
                <span>Secure login to continue</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- Login Card ----------
    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    with st.form(
        key="login_form",
        clear_on_submit=False,
    ):
        st.markdown('<div class="field-heading">Username</div>', unsafe_allow_html=True)

        username = st.text_input(
            label="Username",
            placeholder="Enter your username",
            key="login_username",
            label_visibility="collapsed",
        )

        st.markdown(
            '<div style="height:12px;"></div>'
            '<div class="field-heading">Password</div>',
            unsafe_allow_html=True,
        )

        password = st.text_input(
            label="Password",
            type="password",
            placeholder="Enter your password",
            key="login_password",
            label_visibility="collapsed",
        )

        st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)

        login_clicked = st.form_submit_button(
            label="↪  LOGIN",
            use_container_width=True,
        )

    st.markdown(
        """
        <div class="safe-note">
            <span class="safe-shield">🛡</span>
            <span>Your data is safe and secure</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Security Notice ----------
    st.markdown(
        """
        <div class="restricted-box">
            <div class="restricted-title">🔒 Restricted Access</div>
            This system is for authorized users only.<br>
            All dashboard access is subject to company security policies.
        </div>

        <div class="footer-note">
            © 2026 Sugam Group &nbsp;|&nbsp; Internal Use Only<br>
            All rights reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- Authentication ----------
    if login_clicked:
        if not username.strip() or not password.strip():
            st.warning("Please enter username and password.")
            return

        success, employee_id, employee_name = check_login(
            username=username,
            password=password,
        )

        if success:
            try:
                role = get_role_for_employee(employee_id)

                data_scope = get_data_scope_for_employee(employee_id)

                st.session_state["logged_in"] = True
                st.session_state["employee_id"] = employee_id
                st.session_state["employee_name"] = (
                    employee_name
                    if employee_name
                    else username.strip()
                )
                st.session_state["role"] = role
                st.session_state["data_scope"] = data_scope
                st.session_state["username"] = username.strip()

                st.rerun()

            except Exception as e:
                st.session_state["logged_in"] = False

                st.error(
                    "Login successful, but user access "
                    f"could not be loaded: {e}"
                )

        else:
            st.error("Invalid username or password.")


if __name__ == "__main__":
    login_page()
