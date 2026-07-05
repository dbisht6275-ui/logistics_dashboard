import streamlit as st
import pandas as pd
from services.database import get_connection


@st.cache_data(ttl=1800)
def load_booking_data(start_date, end_date, view_type="origin"):

    conn = get_connection()

    # -------- ORIGIN VIEW --------
    if view_type == "origin":

        query = f"""
        SELECT 
            v.zonename as zone,
            v.hubname as circle,
            v.stnname as branch,
            v.isagency,
            cn.grno,

            CASE 
                WHEN cn.grtype='t' THEN 'TOPAY'
                WHEN cn.grtype='r' THEN 'TBB'
                WHEN cn.grtype='C' THEN 'PAID'
                ELSE ''
            END AS GRTYPE,
            cn.grdt,
            cn.cngrcode,
            cngr.name as consignor,
            cn.cngecode,
            cnge.name as consignee,
            cn.aweight,
            cn.cweight,
            CASE 
                WHEN MONTH(cn.grdt) >= 4
                    THEN MONTH(cn.grdt) - 3
                ELSE MONTH(cn.grdt) + 9
            END AS FIN_MONTH,

            IIF(cn.ftl='y','FTL','LTL') AS LOADTYPE,
            dest.stnname as destination,
            (cn.tamount - cn.servicetax) AS REVENUE,
            CASE
                WHEN (DeST.COUNTRY = 'BANGLADESH' OR DEST.STNNAME IN ('PETRAPOLE', 'MYMENSINGH')) THEN 'B.DESH'
                WHEN DEST.COUNTRY = 'BHUTAN' THEN 'BHUTAN'
                WHEN DEST.zonecode = 'A0006' THEN 'NEPAL'
                WHEN DEST.COUNTRY NOT IN ('BANGLADESH', 'BHUTAN') AND DEST.zonecode <> 'A0006' THEN 'DOMESTIC' 
            ELSE ''
            END AS COUNTRY,
            cn.expecteddeliverydt,
            gp.deliverydt


        FROM cnmt cn
        INNER JOIN viewstationmast v
            ON v.stncode = cn.orgcode
        inner join stationmast dest on dest.stncode=cn.destcode
        inner join cngrcngemast cngr on cngr.code=cn.cngrcode
        inner join cngrcngemast cnge on cnge.code=cn.cngecode
        outer apply (select max(d.drdt) as deliverydt from viewallcompaniesgatepass d where d.grno=cn.grno and d.cancel<>'y') gp
        WHERE cn.grdt BETWEEN '{start_date}' AND '{end_date}' and v.zonename<>'Head office'
          AND cn.grtype <> 'n'
        """

    # -------- DESTINATION VIEW --------
    else:

        query = f"""
        SELECT 
            z.zonename as zone,
            z.hubname as circle,
            ISNULL(m.stnname, v.stnname) as branch,
            z.isagency,
            cn.grno,

            CASE
                WHEN cn.grtype='t' THEN 'TOPAY'
                WHEN cn.grtype='r' THEN 'TBB'
                WHEN cn.grtype='C' THEN 'PAID'
                ELSE ''
            END AS GRTYPE,

            cn.grdt,
            cn.cngrcode,
            cngr.name as consignor,
            cn.cngecode,
            cnge.name as consignee,
            cn.aweight,
            cn.cweight,

            CASE
                WHEN MONTH(cn.grdt) >= 4
                    THEN MONTH(cn.grdt) - 3
                ELSE MONTH(cn.grdt) + 9
            END AS FIN_MONTH,

            IIF(cn.ftl='y','FTL','LTL') AS LOADTYPE,

            (cn.tamount - cn.servicetax) AS REVENUE,
            cn.expecteddeliverydt,
            gp.deliverydt

        FROM cnmt cn

        INNER JOIN stationmast v
            ON v.stncode = cn.destcode
        inner join cngrcngemast cngr on cngr.code=cn.cngrcode
        inner join cngrcngemast cnge on cnge.code=cn.cngecode
        LEFT JOIN stationmast m
            ON v.mergestncode = m.stncode

        LEFT JOIN viewstationmast z
            ON z.stncode = ISNULL(m.mergestncode, cn.destcode)
        outer apply (select max(d.drdt) as deliverydt from viewallcompaniesgatepass d where d.grno=cn.grno and d.cancel<>'y') gp
        WHERE cn.grdt BETWEEN '{start_date}' AND '{end_date}'
          AND cn.grtype <> 'n'
        """

    df = pd.read_sql(query, conn)

    return df


# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31"
    )