import io
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from services.database import get_connection


# =========================================================
# DATA FUNCTION
# =========================================================

def get_bangladesh_delivery_turnover(
    date1_from,
    date1_to,
    date2_from,
    date2_to,
    date3_from,
    date3_to,
):
    """
    Returns Bangladesh delivery turnover branch-wise for
    three selected date periods.

    Return:
        columns: list
        rows: list
    """

    conn = None

    try:
        # -------------------------------------------------
        # DATE CONVERSION
        # -------------------------------------------------

        from1_dt = datetime.strptime(date1_from, "%d-%m-%Y")
        to1_dt = datetime.strptime(date1_to, "%d-%m-%Y")

        from2_dt = datetime.strptime(date2_from, "%d-%m-%Y")
        to2_dt = datetime.strptime(date2_to, "%d-%m-%Y")

        from3_dt = datetime.strptime(date3_from, "%d-%m-%Y")
        to3_dt = datetime.strptime(date3_to, "%d-%m-%Y")

        if from1_dt > to1_dt:
            raise ValueError(
                "Period 1 From Date cannot be after To Date."
            )

        if from2_dt > to2_dt:
            raise ValueError(
                "Period 2 From Date cannot be after To Date."
            )

        if from3_dt > to3_dt:
            raise ValueError(
                "Period 3 From Date cannot be after To Date."
            )

        # Exclusive end dates include the complete To Date
        to1_exclusive = to1_dt + timedelta(days=1)
        to2_exclusive = to2_dt + timedelta(days=1)
        to3_exclusive = to3_dt + timedelta(days=1)

        # -------------------------------------------------
        # DYNAMIC COLUMN NAMES
        # -------------------------------------------------

        def format_date_range(
            from_date,
            to_date,
            is_ftl=False,
        ):
            from_month = from_date.strftime("%b-%y").upper()
            to_month = to_date.strftime("%b-%y").upper()

            if (
                from_date.year == to_date.year
                and from_date.month == to_date.month
            ):
                column_name = to_month
            else:
                column_name = (
                    f"{from_month} TO {to_month}"
                )

            if is_ftl:
                column_name += " (FTL)"

            return column_name

        col1_non_ftl = format_date_range(
            from1_dt,
            to1_dt,
        )

        col2_non_ftl = format_date_range(
            from2_dt,
            to2_dt,
        )

        col3_non_ftl = format_date_range(
            from3_dt,
            to3_dt,
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

        # -------------------------------------------------
        # DATABASE CONNECTION
        # -------------------------------------------------

        conn = get_connection()

        # -------------------------------------------------
        # SQL QUERY
        # -------------------------------------------------

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
                    UPPER(
                        LTRIM(
                            RTRIM(
                                ISNULL(DST.COUNTRY, '')
                            )
                        )
                    ) = 'BANGLADESH'

                    OR UPPER(
                        LTRIM(
                            RTRIM(
                                ISNULL(DST.STNNAME, '')
                            )
                        )
                    ) IN (
                        'PETRAPOLE',
                        'MYMENSINGH'
                    )
                )

                AND (
                    (
                        CN.GRDT >= ?
                        AND CN.GRDT < ?
                    )
                    OR
                    (
                        CN.GRDT >= ?
                        AND CN.GRDT < ?
                    )
                    OR
                    (
                        CN.GRDT >= ?
                        AND CN.GRDT < ?
                    )
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
            # Non-FTL periods
            from1_dt,
            to1_exclusive,

            from2_dt,
            to2_exclusive,

            from3_dt,
            to3_exclusive,

            # FTL periods
            from1_dt,
            to1_exclusive,

            from2_dt,
            to2_exclusive,

            from3_dt,
            to3_exclusive,

            # Main WHERE date ranges
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

        # -------------------------------------------------
        # DATA CLEANING
        # -------------------------------------------------

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
                    .replace("", "Unknown")
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

        df[numeric_columns] = (
            df[numeric_columns]
            .round(2)
        )

        return (
            list(df.columns),
            df.values.tolist(),
        )

    except Exception as error:
        print(
            "Error in Bangladesh Delivery Turnover:",
            error,
        )
        return [], []

    finally:
        if conn is not None:
            conn.close()


# =========================================================
# EXCEL EXPORT
# =========================================================

def create_bangladesh_turnover_excel(
    report_df,
):
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        report_df.to_excel(
            writer,
            index=False,
            sheet_name="Bangladesh Turnover",
        )

        worksheet = writer.sheets[
            "Bangladesh Turnover"
        ]

        worksheet.freeze_panes = "D2"
        worksheet.auto_filter.ref = (
            worksheet.dimensions
        )

        # Header bold
        for cell in worksheet[1]:
            cell.font = cell.font.copy(
                bold=True
            )

        # Numeric format from column 4 onwards
        if worksheet.max_column >= 4:
            for row in worksheet.iter_rows(
                min_row=2,
                min_col=4,
                max_col=worksheet.max_column,
            ):
                for cell in row:
                    cell.number_format = "0.00"

        # Auto column width
        for column_cells in worksheet.columns:
            column_letter = (
                column_cells[0].column_letter
            )

            max_length = 0

            for cell in column_cells:
                value = (
                    ""
                    if cell.value is None
                    else str(cell.value)
                )

                max_length = max(
                    max_length,
                    len(value),
                )

            worksheet.column_dimensions[
                column_letter
            ].width = min(
                max_length + 3,
                35,
            )

    output.seek(0)
    return output.getvalue()


# =========================================================
# TOTAL ROW
# =========================================================

def add_bangladesh_total_row(
    dataframe,
):
    report_df = dataframe.copy()

    text_columns = [
        "ZONENAME",
        "HUBNAME",
        "BRANCH",
    ]

    numeric_columns = [
        column
        for column in report_df.columns
        if column not in text_columns
    ]

    for column in numeric_columns:
        report_df[column] = pd.to_numeric(
            report_df[column],
            errors="coerce",
        ).fillna(0.0)

    total_row = {
        column: ""
        for column in report_df.columns
    }

    if "ZONENAME" in total_row:
        total_row["ZONENAME"] = (
            "GRAND TOTAL"
        )

    for column in numeric_columns:
        total_row[column] = round(
            report_df[column].sum(),
            2,
        )

    total_df = pd.DataFrame(
        [total_row]
    )

    return pd.concat(
        [
            report_df,
            total_df,
        ],
        ignore_index=True,
    )


# =========================================================
# STREAMLIT UI
# =========================================================

def show_bangladesh_delivery_turnover():
    st.markdown(
        """
        <div style="
            padding:14px 18px;
            border:1px solid #ddd6fe;
            border-radius:14px;
            background:linear-gradient(
                180deg,
                #ffffff,
                #faf8ff
            );
            margin-bottom:14px;
        ">
            <div style="
                color:#251b4f;
                font-size:21px;
                font-weight:800;
            ">
                Bangladesh Delivery Turnover
            </div>

            <div style="
                color:#6b7280;
                font-size:12px;
                margin-top:3px;
            ">
                Branch-wise Non-FTL and FTL
                delivery turnover report
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------
    # DEFAULT DATES
    # -----------------------------------------------------

    today = date.today()

    current_month_start = (
        today.replace(day=1)
    )

    previous_month_end = (
        current_month_start
        - timedelta(days=1)
    )

    previous_month_start = (
        previous_month_end.replace(day=1)
    )

    period1_end = (
        previous_month_start
        - timedelta(days=1)
    )

    # Default Period 1: previous three complete months
    period1_start = (
        period1_end.replace(day=1)
        - timedelta(days=62)
    ).replace(day=1)

    # -----------------------------------------------------
    # FILTER SECTION
    # -----------------------------------------------------

    with st.container(border=True):
        st.markdown(
            """
            <div style="
                font-size:15px;
                font-weight:700;
                color:#35256f;
                margin-bottom:8px;
            ">
                Select Report Periods
            </div>
            """,
            unsafe_allow_html=True,
        )

        period1_col, period2_col, period3_col = (
            st.columns(
                3,
                gap="medium",
            )
        )

        with period1_col:
            st.markdown("**Period 1**")

            date1_from = st.date_input(
                "From Date",
                value=period1_start,
                format="DD-MM-YYYY",
                key="bd_date1_from",
            )

            date1_to = st.date_input(
                "To Date",
                value=period1_end,
                format="DD-MM-YYYY",
                key="bd_date1_to",
            )

        with period2_col:
            st.markdown("**Period 2**")

            date2_from = st.date_input(
                "From Date",
                value=previous_month_start,
                format="DD-MM-YYYY",
                key="bd_date2_from",
            )

            date2_to = st.date_input(
                "To Date",
                value=previous_month_end,
                format="DD-MM-YYYY",
                key="bd_date2_to",
            )

        with period3_col:
            st.markdown("**Period 3**")

            date3_from = st.date_input(
                "From Date",
                value=current_month_start,
                format="DD-MM-YYYY",
                key="bd_date3_from",
            )

            date3_to = st.date_input(
                "To Date",
                value=today,
                format="DD-MM-YYYY",
                key="bd_date3_to",
            )

        generate_report = st.button(
            "Generate Report",
            type="primary",
            use_container_width=True,
            key="bd_generate_report",
        )

    if not generate_report:
        return

    # -----------------------------------------------------
    # DATE VALIDATION
    # -----------------------------------------------------

    date_ranges = [
        (
            "Period 1",
            date1_from,
            date1_to,
        ),
        (
            "Period 2",
            date2_from,
            date2_to,
        ),
        (
            "Period 3",
            date3_from,
            date3_to,
        ),
    ]

    for (
        period_name,
        from_date,
        to_date,
    ) in date_ranges:

        if from_date > to_date:
            st.error(
                f"{period_name}: From Date "
                f"cannot be after To Date."
            )
            return

    # -----------------------------------------------------
    # LOAD REPORT
    # -----------------------------------------------------

    with st.spinner(
        "Loading Bangladesh delivery "
        "turnover report..."
    ):
        columns, rows = (
            get_bangladesh_delivery_turnover(
                date1_from.strftime(
                    "%d-%m-%Y"
                ),
                date1_to.strftime(
                    "%d-%m-%Y"
                ),
                date2_from.strftime(
                    "%d-%m-%Y"
                ),
                date2_to.strftime(
                    "%d-%m-%Y"
                ),
                date3_from.strftime(
                    "%d-%m-%Y"
                ),
                date3_to.strftime(
                    "%d-%m-%Y"
                ),
            )
        )

    if not columns or not rows:
        st.warning(
            "No Bangladesh delivery turnover "
            "data was found for the selected "
            "periods."
        )
        return

    dataframe = pd.DataFrame(
        rows,
        columns=columns,
    )

    # -----------------------------------------------------
    # CLEAN REPORT DATA
    # -----------------------------------------------------

    text_columns = [
        "ZONENAME",
        "HUBNAME",
        "BRANCH",
    ]

    numeric_columns = [
        column
        for column in dataframe.columns
        if column not in text_columns
    ]

    for column in text_columns:
        if column in dataframe.columns:
            dataframe[column] = (
                dataframe[column]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
                .replace("", "Unknown")
            )

    for column in numeric_columns:
        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).fillna(0.0).round(2)

    report_dataframe = (
        add_bangladesh_total_row(
            dataframe
        )
    )

    # -----------------------------------------------------
    # COLUMN CONFIGURATION
    # -----------------------------------------------------

    column_configuration = {}

    if "ZONENAME" in report_dataframe.columns:
        column_configuration[
            "ZONENAME"
        ] = st.column_config.TextColumn(
            "Zone",
            width="medium",
        )

    if "HUBNAME" in report_dataframe.columns:
        column_configuration[
            "HUBNAME"
        ] = st.column_config.TextColumn(
            "Hub",
            width="medium",
        )

    if "BRANCH" in report_dataframe.columns:
        column_configuration[
            "BRANCH"
        ] = st.column_config.TextColumn(
            "Branch",
            width="large",
        )

    for column in numeric_columns:
        column_configuration[
            column
        ] = st.column_config.NumberColumn(
            column,
            format="%.2f",
            width="small",
        )

    # -----------------------------------------------------
    # REPORT TABLE
    # -----------------------------------------------------

    st.markdown(
        """
        <div style="
            font-size:17px;
            font-weight:700;
            color:#251b4f;
            margin:15px 0 8px;
        ">
            Bangladesh Delivery Turnover Report
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        report_dataframe,
        width="stretch",
        height=560,
        hide_index=True,
        column_config=column_configuration,
    )

    st.caption(
        "Turnover values are displayed "
        "in ₹ lakh."
    )

    # -----------------------------------------------------
    # DOWNLOADS
    # -----------------------------------------------------

    excel_data = (
        create_bangladesh_turnover_excel(
            report_dataframe
        )
    )

    csv_data = (
        report_dataframe
        .to_csv(index=False)
        .encode("utf-8-sig")
    )

    excel_col, csv_col = st.columns(2)

    with excel_col:
        st.download_button(
            "Download Excel",
            data=excel_data,
            file_name=(
                "bangladesh_delivery_turnover_"
                f"{date1_from:%Y%m%d}_"
                f"{date3_to:%Y%m%d}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml."
                "sheet"
            ),
            use_container_width=True,
            key="bd_download_excel",
        )

    with csv_col:
        st.download_button(
            "Download CSV",
            data=csv_data,
            file_name=(
                "bangladesh_delivery_turnover_"
                f"{date1_from:%Y%m%d}_"
                f"{date3_to:%Y%m%d}.csv"
            ),
            mime="text/csv",
            use_container_width=True,
            key="bd_download_csv",
        )


# Optional alias
def show_bangladesh_turnover():
    show_bangladesh_delivery_turnover()
