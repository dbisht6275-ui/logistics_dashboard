import streamlit as st
import pandas as pd
import time 
from sqlalchemy import text
from services.database import get_engine

@st.cache_data(ttl=1800)
def load_booking_data(start_date, end_date, view_type="origin"):

    t0 = time.time()
    engine = get_engine()

    query = text("""
        EXEC dbo.RevenueDataForPythonDashboard
            @StartDate=:start_date,
            @EndDate=:end_date,
            @ViewType=:view_type
    """)

    with engine.connect() as conn:
        df = pd.read_sql(
            query,
            conn,
            params={
                "start_date": start_date,
                "end_date": end_date,
                "view_type": view_type.upper()
            }
        )
    elapsed = time.time() - t0
    st.write(f"⏱️ load_booking_data({start_date} to {end_date}) took {elapsed:.1f}s, rows: {len(df)}")

    return df


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31"
    )