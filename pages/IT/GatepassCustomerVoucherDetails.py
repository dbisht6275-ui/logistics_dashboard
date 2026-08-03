import streamlit as st
import pyodbc
import pandas as pd

from datetime import date, datetime
from io import BytesIO

from st_aggrid import AgGrid, GridOptionsBuilder


# =========================================================
# PAGE FORMATTING
# =========================================================
def apply_report_css():
    st.markdown(
        """
        <style>
        .main .block-container {
            max-width: 100%;
            padding-top: 1rem;
            padding-left: 1.4rem;
            padding-right: 1.4rem;
            padding-bottom: 1rem;
        }

        .report-title {
            font-size: 24px;
            font-weight: 700;
            color: #17365d;
            margin: 0 0 2px 0;
            line-height: 1.2;
        }

        .report-subtitle {
            font-size: 12px;
            color: #64748b;
            margin: 0 0 10px 0;
        }

        .filter-title {
            font-size: 15px;
            font-weight: 700;
            color: #17365d;
            margin-bottom: 2px;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.55rem;
        }

        div[data-testid="stDateInput"],
        div[data-testid="stTextInput"] {
            margin-bottom: 0;
        }

        div.stButton > button {
            min-height: 38px;
            font-weight: 600;
        }

        label[data-testid="stWidgetLabel"] p {
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# EXCEL EXPORT
# =========================================================
def to_excel(df):
    output = BytesIO()

    export_df = df.copy()
    if "VDATE" in export_df.columns:
        export_df["VDATE"] = pd.to_datetime(
            export_df["VDATE"],
            errors="coerce",
        ).dt.strftime("%d-%m-%Y")

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(
            writer,
            index=False,
            sheet_name="Voucher Details",
        )

    output.seek(0)
    return output.getvalue()


# =========================================================
# DATAFRAME CLEANING
# =========================================================
def prepare_dataframe_for_display(df):
    if df is None or df.empty:
        return pd.DataFrame()

    clean_df = df.copy()
    clean_df.columns = [str(column).strip() for column in clean_df.columns]

    if "VDATE" in clean_df.columns:
        clean_df["VDATE"] = pd.to_datetime(
            clean_df["VDATE"],
            errors="coerce",
        ).dt.strftime("%d-%m-%Y")

    for column in ["DRAMOUNT", "CRAMOUNT"]:
        if column in clean_df.columns:
            clean_df[column] = (
                pd.to_numeric(clean_df[column], errors="coerce")
                .fillna(0.0)
                .astype(float)
                .round(2)
            )

    text_columns = [
        column
        for column in clean_df.columns
        if column not in ["DRAMOUNT", "CRAMOUNT"]
    ]

    for column in text_columns:
        clean_df[column] = clean_df[column].fillna("").astype(str)

    return clean_df


def get_Gatepass_customer_Ledger_details_code   (date1_from, date1_to, cnge_code_filter=None):
    if cnge_code_filter:
        safe_cnge_code = str(cnge_code_filter).strip().replace("'", "''")
        cnge_filter_value = f"'{safe_cnge_code}'"
    else:
        cnge_filter_value = "NULL"                   
    try:
        # ---------------------------------
        # CONVERT INPUT DATES
        # ---------------------------------
        from1_dt = datetime.strptime(date1_from, "%d-%m-%Y").strftime('%Y-%m-%d')
        to1_dt   = datetime.strptime(date1_to, "%d-%m-%Y").strftime('%Y-%m-%d')

        # ---------------------------------
        # SQL CONNECTION
        # ---------------------------------
        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 18 for SQL Server};'
            'SERVER=142.79.224.75,21443;'
            'DATABASE=GreenTransSugamExpress;'
            'UID=data_analytics;'
            'PWD=User@1234;'
            'Encrypt=yes;'
            'TrustServerCertificate=yes;'
        )

        # ---------------------------------
        # SQL QUERY (Full Temp Table Logic)
        # ---------------------------------
        query = f"""
        DECLARE @StartDate DATE = '{from1_dt}';
        DECLARE @EndDate DATE = '{to1_dt}';
        DECLARE @LedgerCode VARCHAR(10) = '0000010744';
        DECLARE @CNGECodeFilter VARCHAR(20) = {cnge_filter_value};

        SET NOCOUNT ON;

        -- Filter Voucher Data Once
        SELECT *
        INTO #VOUCHER
        FROM VIEWVOUCHERDETAILS
        WHERE LEDCODE=@LedgerCode
          AND VDATE BETWEEN @StartDate AND @EndDate
          AND CANCEL<>'Y';

        CREATE INDEX IX_VOUCHER_VNO ON #VOUCHER(VNO);

        -- Result Table
        CREATE TABLE #VoucherDetails (
            VNO VARCHAR(50),
            VDATE DATE,
            CODE VARCHAR(50),
            NAME VARCHAR(255),
            REFNO VARCHAR(255),
            DOCUMENTTYPE VARCHAR(50),
            DOCUMENTNO VARCHAR(50),
            DRAMOUNT DECIMAL(18,2),
            CRAMOUNT DECIMAL(18,2),
            BRANCHCODE VARCHAR(50),
            BRANCHNAME VARCHAR(255),
            BILLAMOUNT VARCHAR(255)
        );

        CREATE INDEX IX_VD_VNO ON #VoucherDetails(VNO);

        -- BILL
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGe.CODE, CNGe.NAME,
                V.REFNO, 'BILL' AS DOCUMENTTYPE, BH.BILLNO AS DOCUMENTNO, V.DRAMOUNT, '0' AS CRAMOUNT,
                V.BRANCHCODE, V.BRANCHNAME, CAST(BH.BILLAMOUNT AS VARCHAR)
            FROM #VOUCHER V
            INNER JOIN BILLHEAD BH WITH (NOLOCK) ON BH.VNO = V.VNO
            LEFT JOIN CNGRCNGEMAST CNGe ON CNGe.CODE = BH.CNGeCODE
            WHERE V.LEDCODE = @LedgerCode
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND V.DRNOTENO IS NULL
                AND V.CRNOTENO IS NULL
                AND V.DRAMOUNT > 0
                AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CNGe.CODE = @CNGECodeFilter);

        -- BILL CANCELLED
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGe.CODE, CNGe.NAME,
                V.REFNO, 'BILL CANCELLED' AS DOCUMENTTYPE, BH.BILLNO AS DOCUMENTNO, 0, V.CRAMOUNT,
                V.BRANCHCODE, V.BRANCHNAME, CAST(CONCAT('-', BH.BILLAMOUNT) AS VARCHAR)
            FROM #VOUCHER V
            INNER JOIN BILLHEAD BH WITH (NOLOCK) ON BH.CANCELVNO = V.VNO
            LEFT JOIN CNGRCNGEMAST CNGe ON CNGe.CODE = BH.CNGeCODE
            WHERE V.LEDCODE = @LedgerCode
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND V.DRNOTENO IS NULL
                AND V.CRNOTENO IS NULL
                AND V.CRAMOUNT > 0
                AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CNGe.CODE = @CNGECodeFilter);

        -- MONEY RECEIPT
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGe.CODE, CNGe.NAME,
                V.REFNO, 'MR' AS DOCUMENTTYPE, CAST(MD.MRNO AS VARCHAR) AS DOCUMENTNO, 0, V.CRAMOUNT,
                V.BRANCHCODE, V.BRANCHNAME,
                CAST(CONCAT('-', ISNULL(MD.RECDAMOUNT, 0) + ISNULL(MD.TDSAMOUNT, 0) + ISNULL(MD.CLAIM, 0) + ISNULL(MD.BANKCHARGES, 0)) AS VARCHAR)
            FROM #VOUCHER V
            INNER JOIN MRHEAD MH WITH (NOLOCK) ON MH.VNO = V.VNO
            INNER JOIN MRDETAIL MD WITH (NOLOCK) ON MD.MRNO = MH.MRNO    
            LEFT JOIN CNGRCNGEMAST CNGe ON CNGe.CODE = MD.CNGECODE
            WHERE V.LEDCODE = @LedgerCode
                AND MD.CUSTCODE = '0000004565'
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND MH.CANCEL <> 'Y' AND MH.CREDITNOTE <> 'Y'
                AND V.CRAMOUNT > 0
                AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CNGe.CODE = @CNGECodeFilter);

        -- REVERSE MR
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGe.CODE, CNGe.NAME,
                V.REFNO, 'REVERSE MR' AS DOCUMENTTYPE, CAST(BH.MRNO AS VARCHAR) AS DOCUMENTNO, V.DRAMOUNT, 0,
                V.BRANCHCODE, V.BRANCHNAME, CAST(ISNULL(MH.RECDAMOUNT, 0) + ISNULL(MH.TDSAMOUNT, 0) + ISNULL(MH.CLAIM, 0) + ISNULL(MH.BANKCHARGES, 0) AS VARCHAR)
            FROM #VOUCHER V
            INNER JOIN REVERSEMR BH WITH (NOLOCK) ON V.VNO = BH.VNO
            LEFT JOIN MRDETAIL MH WITH (NOLOCK) ON MH.MRNO = BH.MRNO
            LEFT JOIN CNGRCNGEMAST CNGe ON CNGe.CODE = MH.CNGECODE
            WHERE V.LEDCODE = @LedgerCode   
                AND MH.CUSTCODE = '0000004565'
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND BH.CANCEL <> 'Y'
                AND V.DRAMOUNT > 0
                AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CNGe.CODE = @CNGECodeFilter);

        -- CUSTOMER REFUND
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGe.CODE, CNGe.NAME,
                CAST(V.REFNO AS VARCHAR) AS REFNO, 'CUSTOMER REFUND' AS DOCUMENTTYPE, CAST(CR.MRNO AS VARCHAR) AS DOCUMENTNO, V.DRAMOUNT, 0,
                V.BRANCHCODE, V.BRANCHNAME, CAST(V.DRAMOUNT AS VARCHAR)
            FROM #VOUCHER V
            INNER JOIN CUSTOMERREFUND CR WITH (NOLOCK) ON V.VNO = CR.VNO
            LEFT JOIN MRHEAD MH WITH (NOLOCK) ON MH.MRNO = CR.MRNO
            OUTER APPLY (SELECT TOP 1 MD.CNGECODE CODE, CNGE.NAME
                        FROM MRDETAIL MD WITH (NOLOCK)
                        LEFT JOIN CNGRCNGEMAST CNGE ON CNGE.CODE = MD.CNGECODE
                        WHERE MD.MRNO = MH.MRNO
                        AND MD.CNGECODE IS NOT NULL) CNGe
            WHERE V.LEDCODE = @LedgerCode
                AND CR.CANCEL <> 'Y'
                AND V.DRAMOUNT > 0
                AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CNGe.CODE = @CNGECodeFilter);
        -- CREDIT NOTE MR1
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CBH.CNGECODE AS CODE, BCNGE.NAME AS NAME,
                REPLACE(V.REFNO, 'CREDIT NOTE # ', '') AS REFNO, 'CREDIT NOTE MR1' AS DOCUMENTTYPE,
                CAST(CRNO.MRNO AS VARCHAR) AS DOCUMENTNO, 0, V.CRAMOUNT,
                V.BRANCHCODE, V.BRANCHNAME, CAST(CONCAT('-', CMD.REBATE) AS NVARCHAR(25)) AS BILLAMOUNT
        FROM #VOUCHER V
        INNER JOIN MRHEAD CRNO WITH(NOLOCK) ON CRNO.CREDITNOTENO = REPLACE(V.REFNO, 'CREDIT NOTE # ', '') AND CRNO.CANCEL <> 'Y'
        INNER JOIN MRDETAIL CMD WITH (NOLOCK) ON CMD.MRNO = CRNO.MRNO
        INNER JOIN BILLHEAD CBH WITH (NOLOCK) ON CBH.BILLNO = CMD.BILLNO
        INNER JOIN CNGRCNGEMAST BCNGE WITH (NOLOCK) ON BCNGE.CODE = CBH.CNGECODE
        WHERE V.LEDCODE = @LedgerCode
        AND V.VDATE BETWEEN @StartDate AND @EndDate
        AND V.REFNO LIKE '%CREDIT NOTE #%'
        AND V.CRAMOUNT > 0
        AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CBH.CNGECODE = @CNGECodeFilter)
        AND V.VNO NOT IN (
                SELECT V.VNO FROM #VOUCHER V
                INNER JOIN MRHEAD MH WITH (NOLOCK) ON MH.VNO = V.VNO
                INNER JOIN MRDETAIL MD WITH (NOLOCK) ON MD.MRNO = MH.MRNO AND MH.CANCEL <> 'y'
                INNER JOIN BILLHEAD BH WITH (NOLOCK) ON BH.BILLNO = MD.BILLNO AND BH.CANCEL <> 'Y'
                INNER JOIN CNGRCNGEMAST CNGe ON CNGe.CODE = MD.CNGECODE
                    WHERE V.LEDCODE = @LedgerCode
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND V.CRAMOUNT > 0 AND MH.CREDITNOTE = 'y'
        );

        -- CREDIT NOTE MR
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGe.CODE AS CODE, CNGe.NAME AS NAME,
                REPLACE(V.REFNO, 'CREDIT NOTE # ', '') AS REFNO, 'CREDIT NOTE MR' AS DOCUMENTTYPE,
                CAST(MD.MRNO AS VARCHAR) AS DOCUMENTNO, 0, V.CRAMOUNT,
                V.BRANCHCODE, V.BRANCHNAME, CAST(CONCAT('-', MD.REBATE) AS NVARCHAR(25)) AS BILLAMOUNT
            FROM #VOUCHER V
            INNER JOIN MRHEAD MH WITH (NOLOCK) ON MH.VNO = V.VNO
            INNER JOIN MRDETAIL MD WITH (NOLOCK) ON MD.MRNO = MH.MRNO AND MH.CANCEL <> 'y'
            INNER JOIN BILLHEAD BH WITH (NOLOCK) ON BH.BILLNO = MD.BILLNO AND BH.CANCEL <> 'Y'
            INNER JOIN CNGRCNGEMAST CNGe ON CNGe.CODE = MD.CNGECODE
            WHERE V.LEDCODE = @LedgerCode
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND V.CRAMOUNT > 0
                AND MH.CREDITNOTE = 'y'
                AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CNGe.CODE = @CNGECodeFilter);

        -- Insert data into #VoucherDetails (BL DEBIT CREDIT NOTE)
            INSERT INTO #VoucherDetails
            SELECT v.vno, v.vdate, CNGe.CODE, CNGe.NAME, v.REFNO,
                'BL-DRCRNOTE' AS DOCUMENTTYPE, 
                SUBSTRING(v.REFNO, CHARINDEX('INVOICE # ', v.REFNO) + 10, CHARINDEX(' - ', v.REFNO) - (CHARINDEX('INVOICE # ', v.REFNO) + 10)) AS DOCUMENTNO, 
                v.DRAMOUNT, v.CRAMOUNT,
                v.BRANCHCODE, v.BRANCHNAME,
                CASE 
                    WHEN v.DRAMOUNT > 0 THEN CAST(v.DRAMOUNT AS NVARCHAR(25))
                    WHEN v.CRAMOUNT > 0 THEN CAST(CONCAT('-', v.CRAMOUNT) AS NVARCHAR(25))
                    ELSE '0'
                END AS BILLAMOUNT
            FROM #VOUCHER v
            INNER JOIN BILLHEAD BH WITH (NOLOCK) ON BH.billno = SUBSTRING(v.REFNO, CHARINDEX('INVOICE # ', v.REFNO) + 10, CHARINDEX(' - ', v.REFNO) - (CHARINDEX('INVOICE # ', v.REFNO) + 10))
            LEFT JOIN CNGRCNGEMAST CNGe ON CNGe.CODE = BH.CNGeCODE
            WHERE V.VDATE BETWEEN @StartDate AND @EndDate
            AND V.LEDCODE = @LedgerCode 
            AND v.cancel <> 'y' 
            AND v.DRCRNOTECATEGORY = 'BL'
            AND (NULLIF(@CNGECodeFilter, '') IS NULL OR CNGe.CODE = @CNGECodeFilter);

        -- DIRECT ENTRIES
        INSERT INTO #VoucherDetails
        SELECT v.vno, v.vdate, null as code, null as name,
                V.REFNO, 'DIRECT' AS DOCUMENTTYPE, null AS DOCUMENTNO, v.DRAMOUNT, v.CRAMOUNT,
                v.BRANCHCODE, v.BRANCHNAME,
                CASE 
                    WHEN v.DRAMOUNT > 0 THEN CAST(v.DRAMOUNT AS NVARCHAR(25))
                    WHEN v.CRAMOUNT > 0 THEN CAST(CONCAT('-', v.CRAMOUNT) AS NVARCHAR(25))
                    ELSE '0'
                END AS BILLAMOUNT
            FROM #VOUCHER v
            WHERE V.VDATE BETWEEN @StartDate AND @EndDate
            AND V.LEDCODE = @LedgerCode 
            AND v.cancel <> 'y'
            AND (NULLIF(@CNGECodeFilter, '') IS NULL OR @CNGECodeFilter = '')
            AND V.VNO NOT IN (SELECT VNO FROM #VoucherDetails);

        -- FINAL RESULT
        SELECT * FROM #VoucherDetails ;
        

        DROP TABLE #VoucherDetails;
        DROP TABLE #VOUCHER;
        """

        # ---------------------------------
        # RUN QUERY
        # ---------------------------------
        df = pd.read_sql(query, conn)
        conn.close()

        columns = list(df.columns)
        rows = df.values.tolist()
        return columns, rows

    except Exception as e:
        st.error(f"Gatepass Customer Voucher Details error: {e}")
        return [], []

# =========================================================
# REPORT DISPLAY
# =========================================================
def display_gatepass_customer_voucher_report(df):
    if df is None or df.empty:
        st.warning("No data found for the selected filters.")
        return

    try:
        gb = GridOptionsBuilder.from_dataframe(df)

        gb.configure_default_column(
            sortable=True,
            filter=True,
            resizable=True,
            minWidth=110,
        )

        column_widths = {
            "VNO": 130,
            "VDATE": 115,
            "CODE": 120,
            "NAME": 220,
            "REFNO": 220,
            "DOCUMENTTYPE": 150,
            "DOCUMENTNO": 145,
            "DRAMOUNT": 125,
            "CRAMOUNT": 125,
            "BRANCHCODE": 125,
            "BRANCHNAME": 180,
            "BILLAMOUNT": 135,
        }

        for column, width in column_widths.items():
            if column in df.columns:
                gb.configure_column(
                    column,
                    minWidth=width,
                    pinned="left" if column in ["VNO", "VDATE"] else None,
                )

        for column in ["DRAMOUNT", "CRAMOUNT"]:
            if column in df.columns:
                gb.configure_column(
                    column,
                    type=["numericColumn"],
                    minWidth=125,
                )

        grid_options = gb.build()

        AgGrid(
            df,
            gridOptions=grid_options,
            height=520,
            theme="streamlit",
            enable_enterprise_modules=False,
            allow_unsafe_jscode=False,
            key="gatepass_customer_voucher_grid",
        )

    except Exception:
        st.dataframe(
            df,
            use_container_width=True,
            height=520,
            hide_index=True,
        )

    excel_file = to_excel(df)

    st.download_button(
        label="📥 Export To Excel",
        data=excel_file,
        file_name="GatepassCustomerVoucherDetails.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
        key="gatepass_customer_voucher_export",
    )


# =========================================================
# MAIN UI
# =========================================================
def show_gatepass_customer_voucher_details():
    apply_report_css()

    st.markdown(
        '<div class="report-title">'
        'Gatepass Customer Voucher Details Report'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="report-subtitle">'
        'Voucher-wise bill, receipt, refund, credit note and direct-entry details'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="filter-title">Report Filters</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1.15], gap="small")

    with col1:
        date_from = st.date_input(
            "From Date",
            value=date.today().replace(day=1),
            format="DD-MM-YYYY",
            key="gatepass_voucher_date_from",
        )

    with col2:
        date_to = st.date_input(
            "To Date",
            value=date.today(),
            format="DD-MM-YYYY",
            key="gatepass_voucher_date_to",
        )

    with col3:
        cnge_code_filter = st.text_input(
            "Consignee Code (Optional)",
            placeholder="Enter exact consignee code",
            key="gatepass_voucher_cnge_code",
        )

    if st.button(
        "Generate Report",
        use_container_width=True,
        key="generate_gatepass_customer_voucher_report",
    ):
        if date_from > date_to:
            st.error("From Date cannot be after To Date.")
            return

        with st.spinner("Generating voucher details report..."):
            columns, rows = get_Gatepass_customer_Ledger_details_code(
                date_from.strftime("%d-%m-%Y"),
                date_to.strftime("%d-%m-%Y"),
                cnge_code_filter.strip() or None,
            )

        if not columns or not rows:
            st.warning("No data found for the selected filters.")
            return

        df = pd.DataFrame(rows, columns=columns)
        df = prepare_dataframe_for_display(df)
        display_gatepass_customer_voucher_report(df)


# =========================================================
# FUNCTION ALIASES
# =========================================================
def show_GatepassCustomerVoucherDetails():
    show_gatepass_customer_voucher_details()


def show_gatepass_customer_ledger_details():
    show_gatepass_customer_voucher_details()
