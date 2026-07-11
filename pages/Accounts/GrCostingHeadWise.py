import streamlit as st
import pandas as pd
from services.database import get_engine
from datetime import datetime
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    output.seek(0)
    return output


def get_GR_CostingHeadwise(date1_from, date1_to):
    try:
        from1_dt = datetime.strptime(date1_from, "%d-%m-%Y").strftime("%Y-%m-%d")
        to1_dt = datetime.strptime(date1_to, "%d-%m-%Y").strftime("%Y-%m-%d")

        engine = get_engine()

        query = f"""
        DECLARE @FromDate DATE = '{from1_dt}';
        DECLARE @ToDate DATE = '{to1_dt}';
        DECLARE @SQL NVARCHAR(MAX);
        DECLARE @COLUMNNAMES NVARCHAR(MAX);

        SELECT @COLUMNNAMES = STRING_AGG(QUOTENAME(DOCUMENTTYPE), ',')
        FROM
        (
            SELECT DISTINCT DOCUMENTTYPE
            FROM DBO.GREENTRANSWEB_GRWISEPNLDETAIL_V7('00000', @FromDate, @ToDate, '')
        ) A;

        SET @SQL = '
        SELECT 
            zone,
            circle,
            origin,
            BRANCHCODE,
            GRNO,
            GRDT,
            CNGR,
            CNGE,
            GRTYPE,
            DESTINATION,
            TOTAL_FREIGHT,
            ' + @COLUMNNAMES + '
        FROM
        (
            SELECT 
                ORG.ZONENAME AS ZONE,
                ORG.HUBNAME AS circle,
                ORG.STNNAME AS ORIGIN,
                D.BRANCHCODE,
                D.GRNO,
                CN.GRDT,
                CN.CNGR,
                CN.CNGE,
                CASE CN.GRTYPE
                    WHEN ''T'' THEN ''TOPAY''
                    WHEN ''R'' THEN ''T.B.B''
                    WHEN ''C'' THEN ''PAID''
                    WHEN ''F'' THEN ''F.O.C''
                    ELSE ''UNKNOWN''
                END AS GRTYPE,
                DEST.STNNAME AS DESTINATION,
                (CN.TAMOUNT - CN.SERVICETAX) AS TOTAL_FREIGHT,
                D.DOCUMENTTYPE,
                D.EXPENSE
            FROM 
                DBO.GREENTRANSWEB_GRWISEPNLDETAIL_V7(''00000'', ''' + CONVERT(VARCHAR, @FromDate, 23) + ''', ''' + CONVERT(VARCHAR, @ToDate, 23) + ''', '''') D
                INNER JOIN CNMT CN ON CN.GRNO = D.GRNO
                INNER JOIN VIEWSTATIONMAST ORG ON ORG.STNCODE = CN.ORGCODE
                LEFT JOIN VIEWSTATIONMAST DEST ON DEST.STNCODE = CN.DESTCODE
            WHERE 
                D.EXPENSE > 0
        ) AS SOURCEDATA
        PIVOT
        (
            SUM(EXPENSE)
            FOR DOCUMENTTYPE IN (' + @COLUMNNAMES + ')
        ) AS PIVOTEDDATA;
        ';

        EXEC SP_EXECUTESQL @SQL;
        """

        df = pd.read_sql(query, engine)

        return df.round(2)

    except Exception as e:
        st.error(f"Error: {str(e)}")
        return pd.DataFrame()


def show_GrCostingHeadWise():
    st.title("📊 GR Costing Head-wise")

    col1, col2 = st.columns(2)

    with col1:
        d1_from = st.date_input("From", key="p1_from")

    with col2:
        d1_to = st.date_input("To", key="p1_to")

    if st.button("🚀 Generate Report", use_container_width=True):

        from_date = d1_from.strftime("%d-%m-%Y")
        to_date = d1_to.strftime("%d-%m-%Y")

        with st.spinner("Generating report..."):
            df = get_GR_CostingHeadwise(from_date, to_date)

        if not df.empty:
            st.success("Report generated successfully!")

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
                file_name="GrCostingHeadWise.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.warning("No data found for selected date range.")