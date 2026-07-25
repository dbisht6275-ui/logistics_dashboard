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
    Validate the username and password from USERMAST.

    Login behaviour:
    - Username is case-insensitive.
    - Password is case-insensitive.
    - Leading and trailing spaces are ignored.
    - Expired users are not allowed to log in.
    - Employee name is retrieved from EMPLOYEEMAST.

    Returns:
        tuple:
            (True, employee_id, employee_name) when login is successful.
            (False, None, None) when login fails.
    """

    try:
        # Remove accidental spaces from entered credentials.
        clean_username = username.strip()
        clean_password = password.strip()

        # Create database engine.
        engine = get_engine()

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT
                        U.USERNAME,
                        U.EMPLOYEEID,
                        EMP.EMPNAME AS EMPLOYEE_NAME
                    FROM USERMAST U
                    INNER JOIN EMPLOYEEMAST EMP
                        ON EMP.EMPLOYEEID = U.EMPLOYEEID
                    WHERE LOWER(TRIM(U.USERNAME)) = LOWER(TRIM(:username))
                      AND LOWER(TRIM(U.PASSWORD)) = LOWER(TRIM(:password))
                      AND (
                            U.EXPIRED IS NULL
                            OR LOWER(TRIM(U.EXPIRED)) <> 'y'
                          )
                    LIMIT 1
                    """
                ),
                {
                    "username": clean_username,
                    "password": clean_password,
                },
            )

            # mappings() allows column names to be used.
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

    # CSS styling for the complete login page.
    st.markdown(
        dedent(
            """
            <style>
                /* Main Streamlit page container */
                .main .block-container {
                    max-width: 900px;
                    padding-top: 40px;
                    padding-bottom: 40px;
                }

                /* Login heading card */
                .login-card {
                    width: 100%;
                    background: white;
                    padding: 28px 20px;
                    border-radius: 20px;
                    box-shadow: 0 10px 35px rgba(0, 0, 0, 0.12);
                    border: 1px solid #eeeeee;
                    text-align: center;
                    margin-bottom: 20px;
                    box-sizing: border-box;
                }

                /* Main login heading */
                .login-title {
                    font-size: 30px;
                    font-weight: 600;
                    color: #1f2937;
                    margin-bottom: 5px;
                    line-height: 1.25;
                }

                /* Login subtitle */
                .login-subtitle {
                    color: #6b7280;
                    font-size: 15px;
                    margin-top: 6px;
                }

                /* Input field styling */
                div[data-baseweb="input"] > div {
                    border-radius: 10px;
                }

                /* Login button styling */
                div.stButton > button {
                    width: 100%;
                    background: linear-gradient(
                        90deg,
                        #0f766e,
                        #2563eb
                    );
                    color: white;
                    border: none;
                    border-radius: 10px;
                    height: 45px;
                    font-weight: 600;
                }

                /* Login button hover styling */
                div.stButton > button:hover {
                    color: white;
                    border: none;
                    background: linear-gradient(
                        90deg,
                        #115e59,
                        #1d4ed8
                    );
                }

                /* Login button active styling */
                div.stButton > button:active {
                    color: white;
                    border: none;
                }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )

    # Create a centred login section.
    left_col, login_col, right_col = st.columns([3, 2, 3])

    with login_col:

        # Login heading card.
        st.markdown(
            dedent(
                """
                <div class="login-card">
                    <div class="login-title">
                        Dashboard Login
                    </div>

                    <div class="login-subtitle">
                        Secure login to continue
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

        # Use a form so pressing Enter also submits the login.
        with st.form(
            key="login_form",
            clear_on_submit=False,
        ):
            # Username input.
            username = st.text_input(
                label="Username",
                placeholder="Enter your username",
                key="login_username",
            )

            # Password input.
            password = st.text_input(
                label="Password",
                type="password",
                placeholder="Enter your password",
                key="login_password",
            )

            # Login button.
            login_clicked = st.form_submit_button(
                label="Login",
                use_container_width=True,
            )

        if login_clicked:

            # Check whether both fields contain a value.
            if not username.strip() or not password.strip():
                st.warning("Please enter username and password.")
                return

            # Check credentials against the database.
            success, employee_id, employee_name = check_login(
                username=username,
                password=password,
            )

            if success:
                try:
                    # Retrieve employee role and data access rights.
                    role = get_role_for_employee(employee_id)

                    data_scope = get_data_scope_for_employee(
                        employee_id
                    )

                    # Save authenticated user information.
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

                    # Reload the application after login.
                    st.rerun()

                except Exception as e:
                    # Clear login state if role or scope loading fails.
                    st.session_state["logged_in"] = False

                    st.error(
                        "Login successful, but user access "
                        f"could not be loaded: {e}"
                    )

            else:
                st.error("Invalid username or password.")


# Direct execution support.
# Run using:
# streamlit run login.py
if __name__ == "__main__":
    login_page()
