import streamlit as st
from sqlalchemy import create_engine
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(3),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def get_engine():

    connection_string = (
        f"mssql+pymssql://"
        f"{st.secrets['DB_USER']}:{st.secrets['DB_PASSWORD']}"
        f"@{st.secrets['DB_SERVER']}:{st.secrets['DB_PORT']}"
        f"/{st.secrets['DB_NAME']}"
    )

    engine = create_engine(
        connection_string,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10,
    )

    return engine