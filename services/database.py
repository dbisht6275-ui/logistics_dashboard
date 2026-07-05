import streamlit as st
import pymssql
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def get_connection():
    """
    Creates a fresh database connection.
    Retries up to 3 times (waiting 3 seconds between attempts) if the
    connection fails or times out -- this handles transient network drops
    between Streamlit Cloud and the SQL Server.
    """
    return pymssql.connect(
        server=st.secrets["DB_SERVER"],
        port=int(st.secrets["DB_PORT"]),
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_NAME"],
        login_timeout=30,   # max time to establish the connection
        timeout=180,        # max time to wait for a query to finish
    )