"""Independent, aggregated financial-year revenue for Overview.

Requires Streamlit secrets DB_USER, DB_PASSWORD, DB_SERVER, DB_PORT, DB_NAME
and YEARLY_REVENUE_SQL. The SQL must use the same revenue rules as
services/data_loader.py, return FinancialYear and Revenue, and accept
:start_date (inclusive) and :end_date (exclusive) bind parameters.
"""
from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


@st.cache_resource(show_spinner=False)
def _build_yearly_revenue_engine():
    """Reuse the same pymssql/Streamlit-secrets connection convention."""
    connection_url = URL.create(
        "mssql+pymssql",
        username=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_SERVER"],
        port=int(st.secrets["DB_PORT"]),
        database=st.secrets["DB_NAME"],
    )
    return create_engine(connection_url, pool_pre_ping=True)


def load_five_year_revenue_totals(financial_years):
    """Get totals for consecutive April-March FYs using one grouped SQL query."""
    years = list(financial_years)
    if not years:
        return {}
    starts = [int(fy.split("-")[0]) for fy in years]
    if sorted(starts) != list(range(min(starts), max(starts) + 1)):
        raise ValueError("Financial years must be consecutive")

    sql = st.secrets.get("YEARLY_REVENUE_SQL")
    if not sql:
        raise RuntimeError(
            "YEARLY_REVENUE_SQL is missing in Streamlit secrets. "
            "Set an aggregate query matching services/data_loader.py; "
            "it must return FinancialYear, Revenue and use :start_date/:end_date."
        )

    params = {
        "start_date": date(min(starts), 4, 1),
        "end_date": date(max(starts) + 1, 4, 1),
    }
    with _build_yearly_revenue_engine().connect() as conn:
        data = pd.read_sql_query(text(sql), conn, params=params)

    if not {"FinancialYear", "Revenue"}.issubset(data.columns):
        raise ValueError("Yearly SQL must return FinancialYear and Revenue columns")

    totals = {}
    for fy, revenue in zip(data["FinancialYear"], data["Revenue"]):
        fy = str(fy)
        if fy in years:
            totals[fy] = float(revenue) if pd.notna(revenue) else 0.0
    return totals
