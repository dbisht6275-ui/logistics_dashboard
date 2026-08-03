import pandas as pd
from datetime import datetime, timedelta

from services.database import get_connection


def get_bangladesh_delivery_turnover(
        date1_from, date1_to,
        date2_from, date2_to,
        date3_from, date3_to):

    conn = None

    try:
        # =====================================================
        # DATE CONVERSION
        # =====================================================

        from1_dt = datetime.strptime(date1_from, "%d-%m-%Y")
        to1_dt = datetime.strptime(date1_to, "%d-%m-%Y")

        from2_dt = datetime.strptime(date2_from, "%d-%m-%Y")
        to2_dt = datetime.strptime(date2_to, "%d-%m-%Y")

        from3_dt = datetime.strptime(date3_from, "%d-%m-%Y")
        to3_dt = datetime.strptime(date3_to, "%d-%m-%Y")

        # Validate date ranges
        if from1_dt > to1_dt:
            raise ValueError("Period 1 From Date cannot be after To Date.")

        if from2_dt > to2_dt:
            raise ValueError("Period 2 From Date cannot be after To Date.")

        if from3_dt > to3_dt:
            raise ValueError("Period 3 From Date cannot be after To Date.")

        # Exclusive end dates to include the full selected To Date
        to1_exclusive = to1_dt + timedelta(days=1)
        to2_exclusive = to2_dt + timedelta(days=1)
        to3_exclusive = to3_dt + timedelta(days=1)

        # =====================================================
        # DYNAMIC COLUMN NAMES
        # =====================================================

        def format_date_range(from_date, to_date, is_ftl=False):
            from_month = from_date.strftime("%b-%y").upper()
            to_month = to_date.strftime("%b-%y").upper()

            if (
                from_date.year == to_date.year
                and from_date.month == to_date.month
            ):
                column_name = to_month
            else:
                column_name = f"{from_month} TO {to_month}"

            if is_ftl:
                column_name += " (FTL)"

            return column_name

        col1_non_ftl = format_date_range(
            from1_dt,
            to1_dt,
            is_ftl=False,
        )

        col2_non_ftl = format_date_range(
            from2_dt,
            to2_dt,
            is_ftl=False,
        )

        col3_non_ftl = format_date_range(
            from3_dt,
            to3_dt,
            is_ftl=False,
        )

        col1_ftl = format_date_range(
            from1_dt,
            to1_dt,
            is_ftl=True,
        )

        col2_ftl = format_date_range(
            from2_dt,
            to2_dt,
            is_ftl=True,
        )

        col3_ftl = format_date_range(
            from3_dt,
            to3_dt,
            is_ftl=True,
        )

        # =====================================================
        # DATABASE CONNECTION
        # =====================================================

        conn = get_connection()

        # =====================================================
        # SQL QUERY
        # =====================================================

        query = f"""
            SELECT
                ZONE.ZONENAME,
                ZONE.HUBNAME,
                ORG.STNNAME AS BRANCH,

                SUM(
                    CASE
                        WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                             AND CN.GRDT >= ?
                             AND CN.GRDT < ?
                        THEN (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 300000.0
                        ELSE 0
                    END
                ) AS [{col1_non_ftl}],

                SUM(
                    CASE
                        WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                             AND CN.GRDT >= ?
                             AND CN.GRDT < ?
                        THEN (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                        ELSE 0
                    END
                ) AS [{col2_non_ftl}],

                SUM(
                    CASE
                        WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                             AND CN.GRDT >= ?
                             AND CN.GRDT < ?
                        THEN (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                        ELSE 0
                    END
                ) AS [{col3_non_ftl}],

                SUM(
                    CASE
                        WHEN ISNULL(CN.FTL, 'N') = 'Y'
                             AND CN.GRDT >= ?
                             AND CN.GRDT < ?
                        THEN (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 300000.0
                        ELSE 0
                    END
                ) AS [{col1_ftl}],

                SUM(
                    CASE
                        WHEN ISNULL(CN.FTL, 'N') = 'Y'
                             AND CN.GRDT >= ?
                             AND CN.GRDT < ?
                        THEN (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                        ELSE 0
                    END
                ) AS [{col2_ftl}],

                SUM(
                    CASE
                        WHEN ISNULL(CN.FTL, 'N') = 'Y'
                             AND CN.GRDT >= ?
                             AND CN.GRDT < ?
                        THEN (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                        ELSE 0
                    END
                ) AS [{col3_ftl}]

            FROM CNMT CN WITH (NOLOCK)

            INNER JOIN STATIONMAST ORG
                ON ORG.STNCODE = CN.ORGCODE

            INNER JOIN VIEWSTATIONMAST ZONE
                ON ZONE.STNCODE = CN.ORGCODE

            INNER JOIN STATIONMAST DST
                ON DST.STNCODE = CN.DESTCODE

            WHERE
                CN.GRTYPE <> 'N'

                AND (
                    UPPER(LTRIM(RTRIM(ISNULL(DST.COUNTRY, ''))))
                        = 'BANGLADESH'

                    OR UPPER(LTRIM(RTRIM(ISNULL(DST.STNNAME, ''))))
                        IN ('PETRAPOLE', 'MYMENSINGH')
                )

                AND (
                    (CN.GRDT >= ? AND CN.GRDT < ?)
                    OR
                    (CN.GRDT >= ? AND CN.GRDT < ?)
                    OR
                    (CN.GRDT >= ? AND CN.GRDT < ?)
                )

            GROUP BY
                ZONE.ZONENAME,
                ZONE.HUBNAME,
                ORG.STNNAME

            ORDER BY
                ZONE.ZONENAME,
                ZONE.HUBNAME,
                ORG.STNNAME
        """

        parameters = [
            # Period 1 Non-FTL
            from1_dt,
            to1_exclusive,

            # Period 2 Non-FTL
            from2_dt,
            to2_exclusive,

            # Period 3 Non-FTL
            from3_dt,
            to3_exclusive,

            # Period 1 FTL
            from1_dt,
            to1_exclusive,

            # Period 2 FTL
            from2_dt,
            to2_exclusive,

            # Period 3 FTL
            from3_dt,
            to3_exclusive,

            # Overall WHERE date conditions
            from1_dt,
            to1_exclusive,

            from2_dt,
            to2_exclusive,

            from3_dt,
            to3_exclusive,
        ]

        df = pd.read_sql_query(
            query,
            conn,
            params=parameters,
        )

        if df.empty:
            return [], []

        # =====================================================
        # DATA CLEANING
        # =====================================================

        text_columns = [
            "ZONENAME",
            "HUBNAME",
            "BRANCH",
        ]

        for column in text_columns:
            if column in df.columns:
                df[column] = (
                    df[column]
                    .fillna("Unknown")
                    .astype(str)
                    .str.strip()
                )

        numeric_columns = [
            column
            for column in df.columns
            if column not in text_columns
        ]

        for column in numeric_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            ).fillna(0.0)

        df[numeric_columns] = df[numeric_columns].round(2)

        columns = list(df.columns)
        rows = df.values.tolist()

        return columns, rows

    except Exception as error:
        print(
            "Error in get_bangladesh_delivery_turnover:",
            error,
        )
        return [], []

    finally:
        if conn is not None:
            conn.close()