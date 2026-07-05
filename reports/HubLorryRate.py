import pyodbc
import pandas as pd
from datetime import datetime

def get_Hub_Lorry_Rate(date1_from, date1_to):

    try:
        # ---------------------------------
        # CONVERT INPUT DATE
        # ---------------------------------
        from1_dt = datetime.strptime(date1_from, "%d-%m-%Y")
        to1_dt   = datetime.strptime(date1_to, "%d-%m-%Y")

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
        # SQL QUERY
        # ---------------------------------
        query = """
            DECLARE @FromDate DATE = ?
            DECLARE @ToDate   DATE = ?
            DECLARE @LoadType CHAR(1) = NULL   -- 'F' = FTL , NULL = LTL

            DECLARE @CurrentMonthStart DATE
            DECLARE @NextMonthStart DATE
            DECLARE @LastMonthStart DATE

            SET @CurrentMonthStart = DATEFROMPARTS(YEAR(@ToDate), MONTH(@ToDate), 1)
            SET @NextMonthStart = DATEADD(MONTH, 1, @CurrentMonthStart)
            SET @LastMonthStart = DATEADD(MONTH, -1, @CurrentMonthStart)

            ;WITH LHC_BASE AS
            (
                SELECT 
                    LH.LHCNO,
                    LH.LHCDT,
                    BR.STNNAME AS LHC_BRANCH,
                    LH.TOTCWEIGHT,
                    VCOST.amount AS hirecost
                FROM LHCHEAD LH
                INNER JOIN VIEWLHCREGISTER LAMT 
                    ON LAMT.LHCNO = LH.LHCNO
                INNER JOIN LHCHEADDETAIL LTL 
                    ON LTL.LHCNO = LH.LHCNO 
                    AND (
                        (@LoadType = 'F' AND LTL.LHCTYPE = 'F')
                        OR (@LoadType IS NULL AND (LTL.LHCTYPE <> 'F' OR LTL.LHCTYPE IS NULL))
                    )
                INNER JOIN LHCEXPENSE VCOST 
                    ON VCOST.LHCNO = LH.LHCNO 
                    AND VCOST.mfexpcode = 'M0001'
                INNER JOIN VIEWSTATIONMAST BR 
                    ON BR.STNCODE = LH.BRANCHCODE
                WHERE LH.LHCDT >= @FromDate
                AND LH.LHCDT < DATEADD(DAY,1,@ToDate)
                AND LH.CANCEL <> 'Y'
                AND EXISTS (
                        SELECT 1
                        FROM LHCDETAIL LD
                        WHERE LD.LHCNO = LH.LHCNO
                        AND LD.MANIFESTTYPE = 'O'
                )
            ),

            TOST_DATA AS
            (
                SELECT 
                    X.LHCNO,
                    STRING_AGG(X.STNNAME, ', ') AS NEW_TOST
                FROM
                (
                    SELECT DISTINCT
                        L.LHCNO,
                        DST.STNNAME
                    FROM LHCDETAIL L
                    INNER JOIN MFHEAD IH 
                        ON IH.MANIFESTNO = L.MANIFESTNO
                        AND IH.CANCEL <> 'Y'
                    INNER JOIN VIEWSTATIONMAST DST 
                        ON DST.STNCODE = IH.TOST
                    WHERE L.MANIFESTTYPE = 'O'
                ) X
                GROUP BY X.LHCNO
            )

            SELECT 
                B.LHC_BRANCH,
                ISNULL(T.NEW_TOST,'') AS NEW_TOST,
                B.TOTCWEIGHT AS [GT WT],

                MAX(ROUND(B.hirecost / NULLIF(B.TOTCWEIGHT,0), 2)) AS [HIGHEST RATE],
                ROUND(AVG(B.hirecost / NULLIF(B.TOTCWEIGHT,0)), 2) AS [AVG RATE],
                MIN(ROUND(B.hirecost / NULLIF(B.TOTCWEIGHT,0), 2)) AS [LOWEST RATE],

                COUNT(B.LHCNO) AS TOTALTRIP,
                SUM(B.hirecost) AS TotalHireCost,

                -------- Last Month --------
                ROUND(AVG(CASE 
                    WHEN B.LHCDT >= @LastMonthStart 
                    AND B.LHCDT < @CurrentMonthStart
                    THEN B.hirecost / NULLIF(B.TOTCWEIGHT,0)
                END),2) AS [Last Month Rate],

                COUNT(CASE 
                    WHEN B.LHCDT >= @LastMonthStart 
                    AND B.LHCDT < @CurrentMonthStart
                    THEN 1 END) AS [Last Month No of Trip],

                SUM(CASE 
                    WHEN B.LHCDT >= @LastMonthStart 
                    AND B.LHCDT < @CurrentMonthStart
                    THEN B.hirecost END) AS [Last Month Hire Cost],

                -------- Current Month --------
                ROUND(AVG(CASE 
                    WHEN B.LHCDT >= @CurrentMonthStart 
                    AND B.LHCDT < @NextMonthStart
                    THEN B.hirecost / NULLIF(B.TOTCWEIGHT,0)
                END),2) AS [Current Month Rate],

                COUNT(CASE 
                    WHEN B.LHCDT >= @CurrentMonthStart 
                    AND B.LHCDT < @NextMonthStart
                    THEN 1 END) AS [Current Month No of Trip],

                SUM(CASE 
                    WHEN B.LHCDT >= @CurrentMonthStart 
                    AND B.LHCDT < @NextMonthStart
                    THEN B.hirecost END) AS [Current Month Hire Cost]

            FROM LHC_BASE B
            LEFT JOIN TOST_DATA T 
                ON T.LHCNO = B.LHCNO

            GROUP BY 
                B.LHC_BRANCH,
                B.TOTCWEIGHT,
                T.NEW_TOST

            ORDER BY 
                B.LHC_BRANCH,
                B.TOTCWEIGHT
        """

        # ---------------------------------
        # RUN QUERY
        # ---------------------------------
        df = pd.read_sql(query, conn, params=[from1_dt, to1_dt])

        columns = list(df.columns)
        rows = df.values.tolist()

        conn.close()

        return columns, rows
    
    except Exception as e:
        print("Error:", e)
        return [], []
