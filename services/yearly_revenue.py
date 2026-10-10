"""Independent grouped SQL Server revenue summary for the Overview dashboard.

IMPORTANT: Set YEARLY_REVENUE_SQL to a SELECT whose resulting columns are
FinancialYear and Revenue. It MUST use the identical booking status, exclusions,
revenue expression and booking-date logic as services/data_loader.py.

For speed, aggregate in SQL; NEVER return booking-level records.
"""
import os
from datetime import date

import pandas as pd


def _setting(name):
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name)
    except (FileNotFoundError, KeyError, AttributeError):
        return None


def load_five_year_revenue_totals(financial_years):
    """Run one parameterized FY-bounded aggregate query returning 5 annual totals."""
    sql = _setting("YEARLY_REVENUE_SQL")
    conn_str = _setting("SQL_SERVER_CONNECTION_STRING")
    if not sql or not conn_str:
        raise RuntimeError(
            "Direct SQL setup needed: supply YEARLY_REVENUE_SQL and "
            "SQL_SERVER_CONNECTION_STRING in Streamlit secrets or environment. "
            "The revenue expression/table must match services/data_loader.py."
        )
    years = list(financial_years)
    if not years:
        return {}
    starts = [int(y.split("-")[0]) for y in years]
    if sorted(starts) != list(range(min(starts), max(starts) + 1)):
        raise ValueError("Financial years must be consecutive")
    start_date = date(min(starts), 4, 1)
    end_date = date(max(starts) + 1, 4, 1)
    # SQL must accept two positional parameters: start_date (inclusive),
    # end_date (exclusive). Example shape (adapt to the actual booking SQL):
    # SELECT CONCAT(YEAR(DATEADD(month,-3, grdt)), '-',
    #               YEAR(DATEADD(month,-3, grdt))+1) AS FinancialYear,
    #        SUM(<EXACT ORIGINAL REVENUE EXPRESSION>) AS Revenue
    # FROM <ORIGINAL BOOKING SOURCE>
    # WHERE grdt >= ? AND grdt < ? AND <ORIGINAL STATUS FILTERS>
    # GROUP BY YEAR(DATEADD(month,-3, grdt))
    # Never interpolate dates into SQL yourself.
    import pyodbc
    with pyodbc.connect(conn_str, timeout=20) as conn:
        data = pd.read_sql_query(sql, conn, params=(start_date, end_date))
    needed = {"FinancialYear", "Revenue"}
    if not needed.issubset(data.columns):
        raise ValueError("Yearly revenue SQL must return FinancialYear, Revenue columns")
    result = {}
    for row in data.itertuples(index=False):
        fy = str(getattr(row, "FinancialYear"))
        if fy in years:
            result[fy] = float(getattr(row, "Revenue") or 0)
    return result
