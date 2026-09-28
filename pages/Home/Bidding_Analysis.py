import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from datetime import date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource(show_spinner=False)
def get_bidding_engine():
    """
    Uses the same SQL Server connection pattern requested by the user:
    SQLAlchemy + pymssql + Streamlit secrets.
    """

    def _build_engine():
        connection_url = URL.create(
            "mssql+pymssql",
            username=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_SERVER"],
            port=int(st.secrets["DB_PORT"]),
            database=st.secrets["DB_NAME"],
        )

        return create_engine(
            connection_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=2,
            max_overflow=1,
        )

    return _build_engine()


# ============================================================
# SQL
# ============================================================

BIDDING_SQL = text(
    r"""
    WITH CTE AS
    (
        SELECT
            BP.BIDID,
            BP.VENDCODE,
            MAX(VD.VENDNAME) AS VENDNAME,
            MAX(
                COALESCE(
                    TRY_CONVERT(DECIMAL(18,2), BP.BIDAMOUNT),
                    0
                )
            ) AS BIDAMOUNT
        FROM BIDAMOUNT BP
        INNER JOIN BIDDETAIL BDD
            ON BDD.BIDID = BP.BIDID
           AND BDD.VENDCODE = BP.VENDCODE
        INNER JOIN VENDMAST VD
            ON VD.VENDCODE = BP.VENDCODE
        WHERE ISNULL(BP.CANCEL,'N') <> 'Y'
        GROUP BY
            BP.BIDID,
            BP.VENDCODE
    ),

    RANKED AS
    (
        SELECT
            *,
            ROW_NUMBER() OVER
            (
                PARTITION BY BIDID
                ORDER BY BIDAMOUNT ASC, VENDCODE ASC
            ) AS RN
        FROM CTE
    ),

    TOP3 AS
    (
        SELECT
            BIDID,

            MAX(CASE WHEN RN = 1 THEN VENDNAME END) AS L_1_NAME,
            MAX(CASE WHEN RN = 1 THEN BIDAMOUNT END) AS L_1_AMOUNT,

            MAX(CASE WHEN RN = 2 THEN VENDNAME END) AS L_2_NAME,
            MAX(CASE WHEN RN = 2 THEN BIDAMOUNT END) AS L_2_AMOUNT,

            MAX(CASE WHEN RN = 3 THEN VENDNAME END) AS L_3_NAME,
            MAX(CASE WHEN RN = 3 THEN BIDAMOUNT END) AS L_3_AMOUNT
