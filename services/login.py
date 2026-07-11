import streamlit as st
from sqlalchemy import text
from services.database import get_engine
from services.roles import get_role_for_employee, get_data_scope_for_employee


def check_login(username, password):
    try:
        engine = get_engine()

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT USERNAME, PASSWORD, EMPLOYEEID
                    FROM USERMAST
                    WHERE USERNAME = :username AND EXPIRED <> 'y'
                """),
                {"username": username}
            )
            row = result.fetchone()

        if row and row[1] == password:
            return True, row[2]

        return False, None

    except Exception as e:
        st.error(f"DB Error: {e}")
        return False, None


def login_page():

    st.markdown("""
    <style>

    .main .block-container{
        max-width:900;
        padding-top:40px;
    }

    .login-card{
        width:280px;
        margin:auto;
        background:white;
        padding:30px;
        border-radius:20px;
        box-shadow:0 10px 35px rgba(0,0,0,0.12);
        border:1px solid #eeeeee;
        text-align:center;
        margin-bottom:20px;
    }

    .login-title{
        font-size:30px;
        font-weight:600;
        color:#1f2937;
        margin-bottom:5px;
    }

    .login-subtitle{
        color:#6b7280;
        font-size:15px;
    }

    div.stButton > button{
        background:linear-gradient(90deg,#0f766e,#2563eb);
        color:white;
        border:none;
        border-radius:10px;
        height:45px;
        font-weight:600;
    }

    div.stButton > button:hover{
        color:white;
    }

    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([3, 2, 3])

    with col2:

        st.markdown("""
        <div class="login-card">
            <div class="login-title">
                Dashboard Login 
            </div>
            <div class="login-subtitle">
                Secure login to continue
            </div>
        </div>
        """, unsafe_allow_html=True)

        username = st.text_input(
            "Username",
            placeholder="Enter your username"
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password"
        )

        if st.button("Login", use_container_width=True):

            if not username or not password:
                st.warning("Enter username and password")
                return

            success, employee_id = check_login(username, password)

            if success:
                role = get_role_for_employee(employee_id)
                data_scope = get_data_scope_for_employee(employee_id)

                st.session_state["logged_in"] = True
                st.session_state["employee_id"] = employee_id
                st.session_state["role"] = role
                st.session_state["data_scope"] = data_scope
                # NEW: store the username so the sidebar (app.py) can show it
                # instead of just the Employee ID.
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid Login")