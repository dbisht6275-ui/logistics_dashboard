import pyodbc
import pandas as pd
from datetime import datetime

def get_Branch_wise_delivery_turnover(
        date1_from, date1_to,
        date2_from, date2_to,
        date3_from, date3_to):

    try:
        # Date conversion
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

        # 🆕 DYNAMIC COLUMN NAMES
        def format_date_range(from_date, to_date, is_ftl=False):
            from_month = from_date.strftime("%b-%y")
            to_month = to_date.strftime("%b-%y")
            
            if from_date.month == to_date.month:
                # Single month: "DEC-25"
                return f"{to_month}{( ' (FTL)' if is_ftl else '' )}"
            else:
                # Range: "SEP-25 TO NOV-25"
                return f"{from_month} TO {to_month}{( ' (FTL)' if is_ftl else '' )}"

        # Generate dynamic column names
        col1_non_ftl = format_date_range(from1_dt, to1_dt, False)
        col2_non_ftl = format_date_range(from2_dt, to2_dt, False)
        col3_non_ftl = format_date_range(from3_dt, to3_dt, False)
        
        col1_ftl = format_date_range(from1_dt, to1_dt, True)
        col2_ftl = format_date_range(from2_dt, to2_dt, True)
        col3_ftl = format_date_range(from3_dt, to3_dt, True)

        print(f"📊 Dynamic Columns:")
        print(f"NON FTL: {col1_non_ftl} | {col2_non_ftl} | {col3_non_ftl}")
        print(f"FTL: {col1_ftl} | {col2_ftl} | {col3_ftl}")

        conn = pyodbc.connect(
            'DRIVER={ODBC Driver 18 for SQL Server};'
            'SERVER=142.79.224.75,21443;'
            'DATABASE=GreenTransSugamParivahan;'
            'UID=data_analytics;'
            'PWD=User@1234;'
            'Encrypt=yes;'
            'TrustServerCertificate=yes;'
        )

        # ✅ FIXED SQL QUERY
        query = f"""
        SELECT 
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            BRANCHES.BRANCH,
            SUM(CASE WHEN CN.FTL <> 'Y' AND CN.GRDT BETWEEN '{from1_sql}' AND '{to1_sql}' 
                THEN (CN.TAMOUNT - CN.SERVICETAX)/300000 ELSE 0 END) AS [{col1_non_ftl}],
            SUM(CASE WHEN CN.FTL <> 'Y' AND CN.GRDT BETWEEN '{from2_sql}' AND '{to2_sql}' 
                THEN (CN.TAMOUNT - CN.SERVICETAX)/100000 ELSE 0 END) AS [{col2_non_ftl}],
            SUM(CASE WHEN CN.FTL <> 'Y' AND CN.GRDT BETWEEN '{from3_sql}' AND '{to3_sql}' 
                THEN (CN.TAMOUNT - CN.SERVICETAX)/100000 ELSE 0 END) AS [{col3_non_ftl}],
            SUM(CASE WHEN CN.FTL = 'Y' AND CN.GRDT BETWEEN '{from1_sql}' AND '{to1_sql}' 
                THEN (CN.TAMOUNT - CN.SERVICETAX)/300000 ELSE 0 END) AS [{col1_ftl}],
            SUM(CASE WHEN CN.FTL = 'Y' AND CN.GRDT BETWEEN '{from2_sql}' AND '{to2_sql}' 
                THEN (CN.TAMOUNT - CN.SERVICETAX)/100000 ELSE 0 END) AS [{col2_ftl}],
            SUM(CASE WHEN CN.FTL = 'Y' AND CN.GRDT BETWEEN '{from3_sql}' AND '{to3_sql}' 
                THEN (CN.TAMOUNT - CN.SERVICETAX)/100000 ELSE 0 END) AS [{col3_ftl}]
        FROM CNMT CN
        INNER JOIN STATIONMAST DEST ON DEST.STNCODE = CN.DESTCODE
        LEFT JOIN STATIONMAST MRG ON MRG.STNCODE = DEST.MERGESTNCODE
        CROSS APPLY (
            SELECT 
                CASE COALESCE(MRG.STNNAME, DEST.STNNAME)
                    WHEN 'BIRGUNJ' THEN 'RAXAUL'
                    WHEN 'BHAIRAHAWA' THEN 'SUNAULI'
                    WHEN 'BIRATNAGAR' THEN 'JOGBANI'
                    WHEN 'NEPALGUNJ' THEN 'RUPAIDIHA'
                    WHEN 'DHANGURI' THEN 'PALIA'
                    ELSE COALESCE(MRG.STNNAME, DEST.STNNAME)
                END AS BRANCH
        ) AS BRANCHES
        LEFT JOIN VIEWSTATIONMAST ZONE ON ZONE.STNNAME = BRANCHES.BRANCH
        WHERE CN.GRDT BETWEEN '{from1_sql}' AND '{to3_sql}'
        GROUP BY ZONE.ZONENAME, ZONE.HUBNAME, BRANCHES.BRANCH
        ORDER BY ZONE.ZONENAME, ZONE.HUBNAME, BRANCHES.BRANCH
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
