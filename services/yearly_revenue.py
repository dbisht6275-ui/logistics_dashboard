"""Filter-independent financial-year revenue chart data.

Fast path: a database-side dbo.GetFiveYearRevenueTotals procedure returning
FinancialYear and Revenue. This procedure must be implemented by the DB team
using the same revenue rules as dbo.GetRevenueDataFromCache.

Compatible fallback: call the existing GetRevenueDataFromCache once per FY and
sum its REVENUE column. This path requires no schema assumptions, but the
first uncached load can be slower because the procedure returns booking rows.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd
import streamlit as st
from sqlalchemy import text
from services.database import get_engine

_FAST_SQL = text('''
    EXEC dbo.GetFiveYearRevenueTotals
        @StartDate = :start_date,
        @EndDate = :end_date,
        @ViewType = :view_type
''')
_EXISTING_SQL = text('''
    EXEC dbo.GetRevenueDataFromCache
        @StartDate = :start_date,
        @EndDate = :end_date,
        @ViewType = :view_type
''')


def _validate_years(financial_years):
    years = tuple(str(x) for x in financial_years)
    if not years:
        return years, []
    starts = []
    for fy in years:
        a, b = (int(x) for x in fy.split('-'))
        if b != a + 1:
            raise ValueError(f'Invalid financial year: {fy}')
        starts.append(a)
    if starts != list(range(min(starts), max(starts) + 1)):
        raise ValueError('Financial years must be consecutive and oldest first')
    return years, starts


def _fast_totals(years, starts):
    # Check availability before EXEC. Avoid swallowing unrelated DB errors.
    with get_engine().connect() as conn:
        proc_exists = conn.execute(text("SELECT OBJECT_ID('dbo.GetFiveYearRevenueTotals', 'P')")).scalar()
        if proc_exists is None:
            return None
        result = pd.read_sql_query(_FAST_SQL, conn, params={
            'start_date': date(min(starts), 4, 1),
            'end_date': date(max(starts) + 1, 3, 31),
            'view_type': 'ORIGIN',
        })
    if not {'FinancialYear', 'Revenue'}.issubset(result.columns):
        raise ValueError('GetFiveYearRevenueTotals must return FinancialYear and Revenue')
    aggregate = result.groupby('FinancialYear')['Revenue'].sum()
    return {fy: float(aggregate[fy]) for fy in years if fy in aggregate.index and pd.notna(aggregate[fy])}


def _fallback_one_year(fy):
    start = int(fy.split('-')[0])
    with get_engine().connect() as conn:
        # This existing stored procedure returns booking rows, not just totals.
        # Chunk rows to keep peak memory lower when supported by the driver.
        chunks = pd.read_sql_query(_EXISTING_SQL, conn, params={
            'start_date': f'{start}-04-01',
            'end_date': f'{start + 1}-03-31',
            'view_type': 'ORIGIN',
        }, chunksize=50000)
        total = 0.0
        for part in chunks:
            if 'REVENUE' not in part.columns:
                raise ValueError('Existing booking procedure did not return REVENUE')
            total += float(pd.to_numeric(part['REVENUE'], errors='coerce').sum())
        return fy, total


@st.cache_data(ttl=86400, show_spinner=False, max_entries=3)
def load_five_year_revenue_totals(financial_years):
    years, starts = _validate_years(financial_years)
    if not years:
        return {}
    fast = _fast_totals(years, starts)
    if fast is not None:
        return fast
    # Fallback uses only 2 concurrent DB requests to limit server load.
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix='historical-revenue') as pool:
        return dict(pool.map(_fallback_one_year, years))
