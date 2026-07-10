import streamlit as st
import pandas as pd
from services.database import get_connection


@st.cache_data(ttl=1800)
def load_booking_data(start_date, end_date, view_type="origin"):

    conn = get_connection()

    query = "EXEC dbo.RevenueDataForPythonDashboard ?, ?, ?"

    df = pd.read_sql(
        query,
        conn,
        params=[start_date, end_date, view_type.upper()]
    )

    return df


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31"
    )