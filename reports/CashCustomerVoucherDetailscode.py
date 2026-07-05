import pyodbc
import pandas as pd
from datetime import datetime

def get_Cash_Customer_Ledger_details_code   (date1_from, date1_to, cngr_code_filter=None):
    if cngr_code_filter:
        cngr_filter_value = f"'{cngr_code_filter}'"   
    else:
        cngr_filter_value = "NULL"                   
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
            'DATABASE=GreenTransSugamParivahan;'
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
        DECLARE @LedgerCode VARCHAR(10) = '0000000259';
        DECLARE @CNGRCodeFilter VARCHAR(20) = {cngr_filter_value};

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
        SELECT V.VNO, V.VDATE, CNGR.CODE, CNGR.NAME,
                V.REFNO, 'BILL' AS DOCUMENTTYPE, BH.BILLNO AS DOCUMENTNO, V.DRAMOUNT, '0' AS CRAMOUNT,
                V.BRANCHCODE, V.BRANCHNAME, CAST(BH.BILLAMOUNT AS VARCHAR)
        FROM #VOUCHER V
        INNER JOIN BILLHEAD BH WITH (NOLOCK) ON BH.VNO = V.VNO
        LEFT JOIN CNGRCNGEMAST CNGR ON CNGR.CODE = BH.CNGRCODE
            WHERE V.LEDCODE = @LedgerCode
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND V.DRNOTENO IS NULL
                AND V.CRNOTENO IS NULL
                AND V.DRAMOUNT > 0
                AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR CNGR.CODE = @CNGRCodeFilter);

        -- BILL CANCELLED
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGR.CODE, CNGR.NAME,
            V.REFNO, 'BILL CANCELLED' AS DOCUMENTTYPE, BH.BILLNO AS DOCUMENTNO, 0, V.CRAMOUNT,
            V.BRANCHCODE, V.BRANCHNAME, CAST(CONCAT('-', BH.BILLAMOUNT) AS VARCHAR)
        FROM #VOUCHER V
        INNER JOIN BILLHEAD BH WITH (NOLOCK) ON BH.CANCELVNO = V.VNO
        LEFT JOIN CNGRCNGEMAST CNGR ON CNGR.CODE = BH.CNGRCODE
            WHERE V.LEDCODE = @LedgerCode
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND V.DRNOTENO IS NULL
                AND V.CRNOTENO IS NULL
                AND V.CRAMOUNT > 0
                AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR CNGR.CODE = @CNGRCodeFilter);

        -- MONEY RECEIPT
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGR.CODE, CNGR.NAME,
        V.REFNO, 'MR' AS DOCUMENTTYPE, CAST(MD.MRNO AS VARCHAR) AS DOCUMENTNO, 0, V.CRAMOUNT,
        V.BRANCHCODE, V.BRANCHNAME,
        CAST(CONCAT('-', ISNULL(MD.RECDAMOUNT, 0) + ISNULL(MD.TDSAMOUNT, 0) + ISNULL(MD.CLAIM, 0) + ISNULL(MD.BANKCHARGES, 0)) AS VARCHAR)
        FROM #VOUCHER V
        INNER JOIN MRHEAD MH WITH (NOLOCK) ON MH.VNO = V.VNO
        INNER JOIN MRDETAIL MD WITH (NOLOCK) ON MD.MRNO = MH.MRNO    
        LEFT JOIN CNGRCNGEMAST CNGR ON CNGR.CODE = MD.CNGRCODE
            WHERE V.LEDCODE = @LedgerCode
                AND MD.CUSTCODE = '0000004565'
                AND V.VDATE BETWEEN @StartDate AND @EndDate
                AND MH.CANCEL <> 'Y' AND MH.CREDITNOTE <> 'Y'
                AND V.CRAMOUNT > 0
                AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR CNGR.CODE = @CNGRCodeFilter);

        -- REVERSE MR
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGR.CODE, CNGR.NAME,
            V.REFNO, 'REVERSE MR' AS DOCUMENTTYPE, CAST(BH.MRNO AS VARCHAR) AS DOCUMENTNO, V.DRAMOUNT, 0,
            V.BRANCHCODE, V.BRANCHNAME, CAST(ISNULL(Mh.RECDAMOUNT, 0) + ISNULL(Mh.TDSAMOUNT, 0) + ISNULL(Mh.CLAIM, 0) + ISNULL(Mh.BANKCHARGES, 0) AS VARCHAR)
        FROM #VOUCHER V
        INNER JOIN REVERSEMR BH WITH (NOLOCK) ON V.VNO = BH.VNO
        LEFT OUTER JOIN MRDETAIL MH WITH (NOLOCK) ON MH.MRNO = BH.MRNO
        LEFT OUTER JOIN CNGRCNGEMAST CNGR ON CNGR.CODE = MH.CNGRCODE
                    WHERE V.LEDCODE = @LedgerCode   
                        AND MH.CUSTCODE = '0000004565'
                        AND V.VDATE BETWEEN @StartDate AND @EndDate
                        AND BH.CANCEL <> 'Y'
                        AND V.DRAMOUNT > 0
                        AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR CNGR.CODE = @CNGRCodeFilter);

        -- CUSTOMER REFUND
        INSERT INTO #VoucherDetails
        SELECT V.VNO, V.VDATE, CNGR.CODE, CNGR.NAME,
        CAST(V.REFNO AS VARCHAR) AS REFNO, 'CUSTOMER REFUND' AS DOCUMENTTYPE, CAST(CR.MRNO AS VARCHAR) AS DOCUMENTNO, V.DRAMOUNT, 0,
        V.BRANCHCODE, V.BRANCHNAME, CAST(V.DRAMOUNT AS VARCHAR)
        FROM #VOUCHER V
        INNER JOIN CUSTOMERREFUND CR WITH (NOLOCK) ON V.VNO = CR.VNO
        LEFT OUTER JOIN MRHEAD MH WITH (NOLOCK) ON MH.MRNO = CR.MRNO
        OUTER APPLY (SELECT TOP 1 MD.CNGRCODE CODE, CNGR.NAME
                    FROM MRDETAIL MD WITH (NOLOCK)
                    LEFT JOIN CNGRCNGEMAST CNGR ON CNGR.CODE = MD.CNGRCODE
                    WHERE MD.MRNO = MH.MRNO
                    AND MD.CNGRCODE IS NOT NULL) CNGR
                    WHERE V.LEDCODE = @LedgerCode
                        AND CR.CANCEL <> 'Y'
                        AND V.DRAMOUNT > 0
                        AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR CNGR.CODE = @CNGRCodeFilter);
        -- CREDIT NOTE MR1
        INSERT INTO #VoucherDetails
        SELECT V.VNO,V.VDATE,CBH.CNGRCODE AS CODE,BCNGR.NAME AS NAME,
        REPLACE(V.REFNO,'CREDIT NOTE # ','') AS REFNO,'CREDIT NOTE MR1' AS  DOCUMENTTYPE,
        CAST(CRNO.MRNO AS VARCHAR) AS DOCUMENTNO,0,V.CRAMOUNT,
        V.BRANCHCODE,V.BRANCHNAME,CAST(CONCAT('-',CMD.REBATE) AS NVARCHAR(25)) AS BILLAMOUNT
        FROM #VOUCHER V
        inner JOIN MRHEAD CRNO WITH(NOLOCK) ON CRNO.CREDITNOTENO=REPLACE(V.REFNO,'CREDIT NOTE # ','') AND CRNO.CANCEL<>'Y'
        inner JOIN MRDETAIL CMD WITH (NOLOCK) ON CMD.MRNO=CRNO.MRNO
        inner JOIN BILLHEAD CBH WITH (NOLOCK) ON CBH.BILLNO=CMD.BILLNO
        inner JOIN CNGRCNGEMAST BCNGR WITH (NOLOCK) ON BCNGR.CODE=CBH.CNGRCODE
            WHERE V.LEDCODE = @LedgerCode
            AND V.VDATE BETWEEN @StartDate AND @EndDate
            AND V.REFNO LIKE '%CREDIT NOTE #%'
            AND V.CRAMOUNT > 0
            AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR CBH.CNGRCODE = @CNGRCodeFilter)
            AND V.VNO NOT IN (
                    SELECT  V.VNO FROM #VOUCHER V
                                    INNER JOIN MRHEAD MH WITH (NOLOCK) ON MH.VNO=V.VNO
                                    inner JOIN MRDETAIL MD WITH (NOLOCK) ON md.mrno=Mh.mrno and mh.cancel<>'y'
                                    inner JOIN BILLHEAD BH WITH (NOLOCK) ON BH.BILLNO=MD.BILLNO AND BH.CANCEL<>'Y'
                                    inner JOIN CNGRCNGEMAST CNGR ON CNGR.CODE=MD.CNGRCODE
                        WHERE V.LEDCODE = @LedgerCode
                    AND V.VDATE BETWEEN @StartDate AND @EndDate
                    AND V.CRAMOUNT > 0 AND MH.CREDITNOTE = 'y'
            );

        -- CREDIT NOTE MR
        INSERT INTO #VoucherDetails
        SELECT  V.VNO,V.VDATE,CNGR.CODE AS CODE,CNGR.NAME AS NAME,
        REPLACE(V.REFNO,'CREDIT NOTE # ','') AS REFNO,'CREDIT NOTE MR' AS  DOCUMENTTYPE,
        CAST(MD.MRNO AS VARCHAR) AS DOCUMENTNO,0,V.CRAMOUNT,
        V.BRANCHCODE,V.BRANCHNAME,CAST(CONCAT('-',MD.REBATE) AS NVARCHAR(25)) AS BILLAMOUNT
        FROM #VOUCHER V
        INNER JOIN MRHEAD MH WITH (NOLOCK) ON MH.VNO=V.VNO
        inner JOIN MRDETAIL MD WITH (NOLOCK) ON md.mrno=Mh.mrno and mh.cancel<>'y'
        inner JOIN BILLHEAD BH WITH (NOLOCK) ON BH.BILLNO=MD.BILLNO AND BH.CANCEL<>'Y'
        inner JOIN CNGRCNGEMAST CNGR ON CNGR.CODE=MD.CNGRCODE
                    WHERE V.LEDCODE = @LedgerCode
                        AND V.VDATE BETWEEN @StartDate AND @EndDate
                        AND V.CRAMOUNT > 0
                        AND MH.CREDITNOTE = 'y'
                        AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR CNGR.CODE = @CNGRCodeFilter);

        
        -- DIRECT ENTRIES
        INSERT INTO #VoucherDetails
        SELECT v.vno,v.vdate,null as code,null as name,
        V.REFNO,'DIRECT' AS DOCUMENTTYPE,NULL AS DOCUMENTNO,V.DRAMOUNT,V.CRAMOUNT,
        V.BRANCHCODE,V.BRANCHNAME,
        CASE 
            WHEN v.DRAMOUNT > 0 THEN CAST(v.DRAMOUNT AS NVARCHAR(25))
            WHEN v.CRAMOUNT > 0 THEN CAST(CONCAT('-', v.CRAMOUNT) AS NVARCHAR(25))
            ELSE '0'
        END AS BILLAMOUNT
        FROM #VOUCHER v
        WHERE V.VDATE BETWEEN @StartDate AND @EndDate
                AND V.LEDCODE = @LedgerCode 
                AND v.cancel <> 'y'
                AND (NULLIF(@CNGRCodeFilter, '') IS NULL OR @CNGRCodeFilter = '')
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
        print("Error:", e)
        return [], []