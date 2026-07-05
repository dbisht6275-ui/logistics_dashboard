import pyodbc
import pandas as pd
from datetime import datetime


def get_Booking_Weight_Summary_Turnover(
        date1_from, date1_to,
        date2_from, date2_to,
        date3_from, date3_to):

    try:
        # -----------------------------
        # DATE CONVERSION
        # -----------------------------
        from1_dt = datetime.strptime(date1_from, "%d-%m-%Y")
        to1_dt   = datetime.strptime(date1_to, "%d-%m-%Y")

        from2_dt = datetime.strptime(date2_from, "%d-%m-%Y")
        to2_dt   = datetime.strptime(date2_to, "%d-%m-%Y")

        from3_dt = datetime.strptime(date3_from, "%d-%m-%Y")
        to3_dt   = datetime.strptime(date3_to, "%d-%m-%Y")

        from1_sql = from1_dt.strftime("%Y-%m-%d")
        to1_sql   = to1_dt.strftime("%Y-%m-%d")

        from2_sql = from2_dt.strftime("%Y-%m-%d")
        to2_sql   = to2_dt.strftime("%Y-%m-%d")

        from3_sql = from3_dt.strftime("%Y-%m-%d")
        to3_sql   = to3_dt.strftime("%Y-%m-%d")

        # -----------------------------
        # DYNAMIC PARTICULAR
        # -----------------------------
        part1 = f"1. {from1_dt.strftime('%d-%b-%y').upper()} TO {to1_dt.strftime('%d-%b-%y').upper()}"
        part2 = f"2. {from2_dt.strftime('%d-%b-%y').upper()} TO {to2_dt.strftime('%d-%b-%y').upper()}"
        part3 = f"3. {from3_dt.strftime('%d-%b-%y').upper()} TO {to3_dt.strftime('%d-%b-%y').upper()}"

        total1 = "1.1 TOTAL:-"
        total2 = "2.1 TOTAL:-"
        total3 = "3.1 TOTAL:-"
        
        # -----------------------------
        # DATABASE CONNECTION
        # -----------------------------
        conn = pyodbc.connect(
                'DRIVER={ODBC Driver 18 for SQL Server};'
                'SERVER=142.79.224.75,21443;'
                'DATABASE=GreenTransSugamParivahan;'
                'UID=data_analytics;'
                'PWD=User@1234;'
                'Encrypt=yes;'
                'TrustServerCertificate=yes;'
            )

        # -----------------------------
        # DYNAMIC SQL
        # -----------------------------
        query = f"""
            SELECT S.PARTICULAR,
                   S.ZONENAME,
                   SUM(S.SML) AS LTL,
                   SUM(S.FTL) AS FTL,
                   SUM(S.TOTAL) AS TOTAL
            FROM
            (
                SELECT '{part1}' AS PARTICULAR, ZONE.ZONENAME,
                       IIF(CN.FTL<>'Y',(CN.AWEIGHT)/3000,0) AS SML,
                       IIF(CN.FTL='Y',(CN.AWEIGHT)/3000,0) AS FTL,
                       CN.AWEIGHT/3000 AS TOTAL
                FROM CNMT CN WITH (NOLOCK)
                INNER JOIN VIEWSTATIONMAST ZONE ON ZONE.STNCODE = CN.ORGCODE
                WHERE CN.GRDT BETWEEN '{from1_sql}' AND '{to1_sql}'
                AND CN.GRTYPE<>'N'

                UNION ALL

                SELECT '{total1}', NULL,
                       IIF(CN.FTL<>'Y',(CN.AWEIGHT)/3000,0),
                       IIF(CN.FTL='Y',(CN.AWEIGHT)/3000,0),
                       CN.AWEIGHT/3000
                FROM CNMT CN WITH (NOLOCK)
                WHERE CN.GRDT BETWEEN '{from1_sql}' AND '{to1_sql}'
                AND CN.GRTYPE<>'N'

                UNION ALL

                SELECT '{part2}', ZONE.ZONENAME,
                       IIF(CN.FTL<>'Y',(CN.AWEIGHT)/1000,0),
                       IIF(CN.FTL='Y',(CN.AWEIGHT)/1000,0),
                       CN.AWEIGHT/1000
                FROM CNMT CN WITH (NOLOCK)
                INNER JOIN VIEWSTATIONMAST ZONE ON ZONE.STNCODE = CN.ORGCODE
                WHERE CN.GRDT BETWEEN '{from2_sql}' AND '{to2_sql}'
                AND CN.GRTYPE<>'N'

                UNION ALL

                SELECT '{total2}', NULL,
                       IIF(CN.FTL<>'Y',(CN.AWEIGHT)/1000,0),
                       IIF(CN.FTL='Y',(CN.AWEIGHT)/1000,0),
                       CN.AWEIGHT/1000
                FROM CNMT CN WITH (NOLOCK)
                WHERE CN.GRDT BETWEEN '{from2_sql}' AND '{to2_sql}'
                AND CN.GRTYPE<>'N'

                UNION ALL

                SELECT '{part3}', ZONE.ZONENAME,
                       IIF(CN.FTL<>'Y',(CN.AWEIGHT)/1000,0),
                       IIF(CN.FTL='Y',(CN.AWEIGHT)/1000,0),
                       CN.AWEIGHT/1000
                FROM CNMT CN WITH (NOLOCK)
                INNER JOIN VIEWSTATIONMAST ZONE ON ZONE.STNCODE = CN.ORGCODE
                WHERE CN.GRDT BETWEEN '{from3_sql}' AND '{to3_sql}'
                AND CN.GRTYPE<>'N'

                UNION ALL

                SELECT '{total3}', NULL,
                       IIF(CN.FTL<>'Y',(CN.AWEIGHT)/1000,0),
                       IIF(CN.FTL='Y',(CN.AWEIGHT)/1000,0),
                       CN.AWEIGHT/1000
                FROM CNMT CN WITH (NOLOCK)
                WHERE CN.GRDT BETWEEN '{from3_sql}' AND '{to3_sql}'
                AND CN.GRTYPE<>'N'

            ) AS S
            GROUP BY S.PARTICULAR, S.ZONENAME
            ORDER BY 
            S.PARTICULAR,
            IIF(S.ZONENAME='NORTH EAST ZONE',1,
            IIF(S.ZONENAME='EAST ZONE',2,
            IIF(S.ZONENAME='NORTH ZONE',3,
            IIF(S.ZONENAME='SOUTH ZONE',4,
            IIF(S.ZONENAME='WEST ZONE',5,
            IIF(S.ZONENAME='NEPAL ZONE',6,7)))))),
            S.ZONENAME
            """

        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            return [], []

        df = df.round(2)

        columns = list(df.columns)
        rows = df.values.tolist()

        return columns, rows

    except Exception as e:
        print("Error:", e)
        return [], []