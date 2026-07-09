import streamlit as st
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from services.database import get_connection


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _run_query(query):
    """
    Runs the query on a fresh connection each attempt.
    If the connection dies mid-query (network drop / server timeout),
    this closes it and retries with a brand new connection up to 3 times.
    """
    conn = get_connection()
    try:
        return pd.read_sql(query, conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass


@st.cache_data(ttl=3600)
def load_booking_data(start_date, end_date, view_type="origin"):

    # -------- ORIGIN VIEW --------
    if view_type == "origin":

        query = f"""
        SELECT
            CASE
                WHEN MONTH(cn.grdt) >= 4
                    THEN YEAR(cn.grdt)
                ELSE YEAR(cn.grdt) - 1
            END AS YR,
            CASE
                WHEN MONTH(cn.grdt) >= 4
                    THEN MONTH(cn.grdt)-3
                ELSE MONTH(cn.grdt)+9
            END AS FIN_MONTH,
            v.zonename AS Zone,
            v.hubname AS Circle,
            v.stnname AS Branch,
            cn.cngrcode,
            cngr.name AS Consignor,
            IIF(cn.ftl='y','FTL','LTL') AS LoadType,
            COUNT(*) AS ShipmentCount,
            SUM(cn.aweight) AS ActualWeight,
            SUM(cn.cweight) AS ChargeWeight,
            SUM(cn.tamount-cn.servicetax) AS Revenue,
            AVG(
                DATEDIFF(
                    DAY,
                    cn.expecteddeliverydt,
                    gp.deliverydt
                )
            ) AS AvgDelayDays,

            MAX(
                DATEDIFF(
                    DAY,
                    cn.expecteddeliverydt,
                    gp.deliverydt
                )
            ) AS MaxDelayDays

        FROM cnmt cn
        INNER JOIN viewstationmast v ON v.stncode=cn.orgcode
        INNER JOIN cngrcngemast cngr ON cngr.code=cn.cngrcode
        LEFT JOIN
        (
            SELECT 
                grno,
                MAX(drdt) AS deliverydt
            FROM viewallcompaniesgatepass
            WHERE cancel <> 'y'
            GROUP BY grno
        ) gp ON gp.grno = cn.grno

    WHERE cn.grdt between '{start_date}' and '{end_date}' and
            v.zonename<>'Head office'
            AND cn.grtype<>'n'
        GROUP BY
            CASE
                WHEN MONTH(cn.grdt) >= 4
                    THEN YEAR(cn.grdt)
                ELSE YEAR(cn.grdt) - 1
            END,
            CASE
                WHEN MONTH(cn.grdt)>=4
                    THEN MONTH(cn.grdt)-3
                ELSE MONTH(cn.grdt)+9
            END,
            v.zonename,
            v.hubname,
            v.stnname,
            cn.cngrcode,
            cngr.name,
            IIF(cn.ftl='y','FTL','LTL')
        """

    # -------- DESTINATION VIEW --------
    else:

        query = f"""
        SELECT
            CASE
                WHEN MONTH(cn.grdt) >= 4 THEN YEAR(cn.grdt)
                ELSE YEAR(cn.grdt) - 1
            END AS YR,

            CASE
                WHEN MONTH(cn.grdt) >= 4 THEN MONTH(cn.grdt) - 3
                ELSE MONTH(cn.grdt) + 9
            END AS FIN_MONTH,

            z.zonename AS Zone,
            z.hubname AS Circle,
            ISNULL(m.stnname, v.stnname) AS Branch,
            cn.cngecode AS ConsigneeCode,
            cnge.name AS Consignee,
            IIF(cn.ftl = 'y', 'FTL', 'LTL') AS LoadType,

            COUNT(*) AS ShipmentCount,
            SUM(cn.aweight) AS ActualWeight,
            SUM(cn.cweight) AS ChargeWeight,
            SUM(cn.tamount - cn.servicetax) AS Revenue,

            AVG(DATEDIFF(DAY, cn.expecteddeliverydt, gp.deliverydt)) AS AvgDelayDays,
            MAX(DATEDIFF(DAY, cn.expecteddeliverydt, gp.deliverydt)) AS MaxDelayDays

        FROM cnmt cn
        INNER JOIN stationmast v ON v.stncode = cn.destcode
        INNER JOIN cngrcngemast cngr ON cngr.code = cn.cngrcode
        INNER JOIN cngrcngemast cnge ON cnge.code = cn.cngecode
        LEFT JOIN stationmast m ON m.stncode = v.mergestncode
        LEFT JOIN viewstationmast z ON z.stncode = ISNULL(m.stncode, v.stncode)
        LEFT JOIN
                (
                    SELECT 
                        grno,
                        MAX(drdt) AS deliverydt
                    FROM viewallcompaniesgatepass
                    WHERE cancel <> 'y'
                    GROUP BY grno
                ) gp ON gp.grno = cn.grno

        WHERE cn.grdt between '{start_date}' and '{end_date}' and 
            cn.grtype <> 'n'
        GROUP BY
            CASE
                WHEN MONTH(cn.grdt) >= 4
                    THEN YEAR(cn.grdt)
                ELSE YEAR(cn.grdt) - 1
            END,
            CASE
                WHEN MONTH(cn.grdt) >= 4
                    THEN MONTH(cn.grdt) - 3
                ELSE MONTH(cn.grdt) + 9
            END,
            z.zonename,
            z.hubname,
            ISNULL(m.stnname, v.stnname),
            cn.cngecode,
            cnge.name,
            IIF(cn.ftl='y','FTL','LTL')
        """

    return _run_query(query)


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31"
    )