import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.roles import (
    get_role_for_employee,
    get_data_scope_for_employee,
)


def check_login(username: str, password: str):
    """
    Validate the user's login credentials.

    Username comparison:
        - Case-insensitive
        - Ignores spaces before and after the username

    Password comparison:
        - Case-sensitive for security

    Returns:
        tuple:
            (True, employee_id) when login succeeds
            (False, None) when login fails
    """

    try:
        engine = get_engine()

        # Remove accidental spaces entered before or after the username.
        clean_username = username.strip()

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT
                        USERNAME,
                        PASSWORD,
                        EMPLOYEEID
                    FROM USERMAST
                    WHERE LOWER(TRIM(USERNAME)) = LOWER(TRIM(:username))
                      AND (
                            EXPIRED IS NULL
                            OR LOWER(TRIM(EXPIRED)) <> 'y'
                          )
                    """
                ),
                {
                    "username": clean_username
                },
            )

            row = result.fetchone()

        # Password remains case-sensitive.
        if row and row[1] == password:
            return True, row[2]

        return False, None

    except Exception as e:
        # Display database error on the Streamlit page.
        st.error(f"Database error: {e}")
        return False, None


def login_page():
    """
    Display the Streamlit login page and authenticate the user.
    """

    # Custom styling for the login page.
    st.markdown(
        """
        <style>

        .main .block-container {
            max-width: 900px;
            padding-top: 40px;
        }

        .login-card {
            width: 280px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 35px rgba(0, 0, 0, 0.12);
            border: 1px solid #eeeeee;
            text-align: center;
            margin-bottom: 20px;
        }

        .login-title {
            font-size: 30px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
        }

        .login-subtitle {
            color: #6b7280;
            font-size: 15px;
        }

        div.stButton > button {
            background: linear-gradient(90deg, #0f766e, #2563eb);
            color: white;
            border: none;
            border-radius: 10px;
            height: 45px;
            font-weight: 600;
        }

        div.stButton > button:hover {
            color: white;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )

    # Keep the login form in the centre column.
    col1, col2, col3 = st.columns([3, 2, 3])

    with col2:
        st.markdown(
            """
            <div class="login-card">
                <div class="login-title">
                    Dashboard Login
                </div>

                <div class="login-subtitle">
                    Secure login to continue
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Login input fields.
        username = st.text_input(
            "Username",
            placeholder="Enter your username",
            key="login_username",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key="login_password",
        )

        # Login button.
        if st.button(
            "Login",
            use_container_width=True,
            key="login_button",
        ):
            # Validate that both fields have been entered.
            if not username.strip() or not password:
                st.warning("Enter username and password")
                return

            success, employee_id = check_login(
                username=username,
                password=password,
            )

            if success:
                # Load the employee's role and permitted data scope.
                role = get_role_for_employee(employee_id)
                data_scope = get_data_scope_for_employee(employee_id)

                # Save authenticated-user information in session state.
                st.session_state["logged_in"] = True
                st.session_state["employee_id"] = employee_id
                st.session_state["role"] = role
                st.session_state["data_scope"] = data_scope

                # Save a cleaned version of the entered username.
                st.session_state["username"] = username.strip()

                # Reload the Streamlit application after successful login.
                st.rerun()

            else:
                st.error("Invalid username or password")
