import streamlit as st
import pymssql

def get_connection():
    return pymssql.connect(
        server=st.secrets["DB_SERVER"],
        port=int(st.secrets["DB_PORT"]),
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_NAME"],
    )