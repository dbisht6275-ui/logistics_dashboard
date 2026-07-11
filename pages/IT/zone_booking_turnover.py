import streamlit as st
import pandas as pd
from services.database import get_engine
from datetime import datetime
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder


# ------------------------------------
# EXCEL EXPORT FUNCTION
# ------------------------------------
def to_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")

    output.seek(0)
    return output


# ------------------------------------
# DATA FUNCTION
# ------------------------------------
def get_zone_wise_booking_turnover(
        date1_from, date1_to,
        date2_from, date2_to,
        date3_from, date3_to):

    try:

        from1_sql = date1_from.strftime("%Y-%m-%d")
        to1_sql = date1_to.strftime("%Y-%m-%d")

        from2_sql = date2_from.strftime("%Y-%m-%d")
        to2_sql = date2_to.strftime("%Y-%m-%d")

        from3_sql = date3_from.strftime("%Y-%m-%d")
        to3_sql = date3_to.strftime("%Y-%m-%d")

        part1 = f"1. {date1_from.strftime('%d-%b-%y').upper()} TO {date1_to.strftime('%d-%b-%y').upper()}"
        part2 = f"2. {date2_from.strftime('%d-%b-%y').upper()} TO {date2_to.strftime('%d-%b-%y').upper()}"
        part3 = f"3. {date3_from.strftime('%d-%b-%y').upper()} TO {date3_to.strftime('%d-%b-%y').upper()}"

        engine = get_engine()

        query = f"""
        SELECT S.PARTICULAR,
               S.ZONENAME,
               SUM(S.LTL) AS LTL,
               SUM(S.FTL) AS FTL,
               SUM(S.TOTAL) AS TOTAL,
               (SUM(S.LTL)*100.0)/NULLIF(SUM(S.TOTAL),0) AS [% (LTL/TOTAL)],
               (SUM(S.NPBKG)*100.0)/NULLIF(SUM(S.TOTAL),0) AS [% (NEPAL/TOTAL)]
        FROM
        (
            SELECT '{part1}' AS PARTICULAR,
                   ZONE.ZONENAME,
                   IIF(CN.FTL<>'Y',(CN.TAMOUNT-CN.SERVICETAX)/300000.0,0) AS LTL,
                   IIF(CN.FTL='Y',(CN.TAMOUNT-CN.SERVICETAX)/300000.0,0) AS FTL,
                   (CN.TAMOUNT-CN.SERVICETAX)/300000.0 AS TOTAL,
                   IIF(DST.ZONECODE='A0006',(CN.TAMOUNT-CN.SERVICETAX)/300000.0,0) AS NPBKG
            FROM CNMT CN WITH(NOLOCK)
            INNER JOIN VIEWSTATIONMAST ZONE ON ZONE.STNCODE=CN.ORGCODE
            LEFT JOIN STATIONMAST DST ON DST.STNCODE=CN.DESTCODE
            WHERE CN.GRDT BETWEEN '{from1_sql}' AND '{to1_sql}'
            AND CN.GRTYPE<>'N'

            UNION ALL

            SELECT '{part2}',
                   ZONE.ZONENAME,
                   IIF(CN.FTL<>'Y',(CN.TAMOUNT-CN.SERVICETAX)/100000.0,0),
                   IIF(CN.FTL='Y',(CN.TAMOUNT-CN.SERVICETAX)/100000.0,0),
                   (CN.TAMOUNT-CN.SERVICETAX)/100000.0,
                   IIF(DST.ZONECODE='A0006',(CN.TAMOUNT-CN.SERVICETAX)/100000.0,0)
            FROM CNMT CN WITH(NOLOCK)
            INNER JOIN VIEWSTATIONMAST ZONE ON ZONE.STNCODE=CN.ORGCODE
            LEFT JOIN STATIONMAST DST ON DST.STNCODE=CN.DESTCODE
            WHERE CN.GRDT BETWEEN '{from2_sql}' AND '{to2_sql}'
            AND CN.GRTYPE<>'N'

            UNION ALL

            SELECT '{part3}',
                   ZONE.ZONENAME,
                   IIF(CN.FTL<>'Y',(CN.TAMOUNT-CN.SERVICETAX)/100000.0,0),
                   IIF(CN.FTL='Y',(CN.TAMOUNT-CN.SERVICETAX)/100000.0,0),
                   (CN.TAMOUNT-CN.SERVICETAX)/100000.0,
                   IIF(DST.ZONECODE='A0006',(CN.TAMOUNT-CN.SERVICETAX)/100000.0,0)
            FROM CNMT CN WITH(NOLOCK)
            INNER JOIN VIEWSTATIONMAST ZONE ON ZONE.STNCODE=CN.ORGCODE
            LEFT JOIN STATIONMAST DST ON DST.STNCODE=CN.DESTCODE
            WHERE CN.GRDT BETWEEN '{from3_sql}' AND '{to3_sql}'
            AND CN.GRTYPE<>'N'
        ) S
        GROUP BY S.PARTICULAR,S.ZONENAME
        ORDER BY S.ZONENAME,S.PARTICULAR
        """

        df = pd.read_sql(query, engine)

        return df.round(2)

    except Exception as e:
        st.error(str(e))
        return pd.DataFrame()


# -----------------------------------
# NEW UI FUNCTION
# -----------------------------------
def show_ZoneBookingTurnover():

    st.title("Zone Wise Booking Turnover")

    df = pd.DataFrame()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Period 1")
        d1_from = st.date_input("From", key="p1_from")
        d1_to = st.date_input("To", key="p1_to")

    with col2:
        st.markdown("### Period 2")
        d2_from = st.date_input("From", key="p2_from")
        d2_to = st.date_input("To", key="p2_to")

    with col3:
        st.markdown("### Period 3")
        d3_from = st.date_input("From", key="p3_from")
        d3_to = st.date_input("To", key="p3_to")

    if st.button("Generate Report", use_container_width=True):

        df = get_zone_wise_booking_turnover(
            d1_from,
            d1_to,
            d2_from,
            d2_to,
            d3_from,
            d3_to
        )

        if not df.empty:

            gb = GridOptionsBuilder.from_dataframe(df)

            gb.configure_default_column(
                sortable=True,
                filter=True,
                resizable=True
            )

            grid_options = gb.build()

            AgGrid(
                df,
                gridOptions=grid_options,
                height=500,
                fit_columns_on_grid_load=True
            )

            excel_file = to_excel(df)

            st.download_button(
                label="📥 Export To Excel",
                data=excel_file,
                file_name="ZoneWiseBookingTurnover.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        else:
            st.warning("No data found.")