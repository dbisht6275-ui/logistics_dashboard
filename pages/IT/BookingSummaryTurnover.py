import streamlit as st
import pandas as pd

from datetime import date, timedelta
from io import BytesIO

from services.database import get_engine
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
            margin: 0 0 12px 0;
        }

        .period-title {
            font-size: 15px;
            font-weight: 700;
            color: #17365d;
            margin-bottom: 2px;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.55rem;
        }

        div[data-testid="stDateInput"] {
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

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Booking Summary",
        )

    output.seek(0)
    return output.getvalue()


# =========================================================
# DEFAULT DATE RANGES
# =========================================================
def get_default_dates():
    today = date.today()

    current_month_start = today.replace(day=1)

    previous_month_end = (
        current_month_start
        - timedelta(days=1)
    )

    previous_month_start = (
        previous_month_end.replace(day=1)
    )

    previous_three_month_end = (
        previous_month_start
        - timedelta(days=1)
    )

    start_month = previous_three_month_end.month - 2
    start_year = previous_three_month_end.year

    while start_month <= 0:
        start_month += 12
        start_year -= 1

    previous_three_month_start = date(
        start_year,
        start_month,
        1,
    )

    return {
        "today": today,
        "current_month_start": current_month_start,
        "previous_month_start": previous_month_start,
        "previous_month_end": previous_month_end,
        "previous_three_month_start": previous_three_month_start,
        "previous_three_month_end": previous_three_month_end,
    }


# =========================================================
# DATAFRAME CLEANING
# =========================================================
def prepare_dataframe_for_aggrid(df):
    if df is None or df.empty:
        return pd.DataFrame()

    clean_df = df.copy()

    clean_df.columns = [
        str(column).strip()
        for column in clean_df.columns
    ]

    text_columns = [
        "PARTICULAR",
        "ZONENAME",
    ]

    for column in text_columns:
        if column in clean_df.columns:
            clean_df[column] = (
                clean_df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    numeric_columns = [
        column
        for column in clean_df.columns
        if column not in text_columns
    ]

    for column in numeric_columns:
        clean_df[column] = (
            pd.to_numeric(
                clean_df[column],
                errors="coerce",
            )
            .fillna(0.0)
            .astype(float)
            .round(2)
        )

    clean_df = clean_df.replace(
        {
            float("inf"): 0.0,
            float("-inf"): 0.0,
        }
    )

    return clean_df


# =========================================================
# BOOKING SUMMARY DATA FUNCTION
# =========================================================
def get_Booking_summary_trunover(
    date1_from,
    date1_to,
    date2_from,
    date2_to,
    date3_from,
    date3_to,
):
    try:
        # ---------------------------------------------
        # DATE VALIDATION
        # ---------------------------------------------
        if date1_from > date1_to:
            raise ValueError(
                "Previous 3 Months: From Date cannot "
                "be after To Date."
            )

        if date2_from > date2_to:
            raise ValueError(
                "Previous Month: From Date cannot "
                "be after To Date."
            )

        if date3_from > date3_to:
            raise ValueError(
                "Current Month: From Date cannot "
                "be after To Date."
            )

        # ---------------------------------------------
        # SQL DATE FORMAT
        # ---------------------------------------------
        from1_sql = date1_from.strftime("%Y-%m-%d")
        to1_sql = date1_to.strftime("%Y-%m-%d")

        from2_sql = date2_from.strftime("%Y-%m-%d")
        to2_sql = date2_to.strftime("%Y-%m-%d")

        from3_sql = date3_from.strftime("%Y-%m-%d")
        to3_sql = date3_to.strftime("%Y-%m-%d")

        # ---------------------------------------------
        # PARTICULAR NAMES IN DD-MM-YYYY FORMAT
        # ---------------------------------------------
        part1 = (
            "1. PREVIOUS 3 MONTHS "
            f"({date1_from.strftime('%d-%m-%Y')} "
            f"TO {date1_to.strftime('%d-%m-%Y')})"
        )

        part2 = (
            "2. PREVIOUS MONTH "
            f"({date2_from.strftime('%d-%m-%Y')} "
            f"TO {date2_to.strftime('%d-%m-%Y')})"
        )

        part3 = (
            "3. CURRENT MONTH "
            f"({date3_from.strftime('%d-%m-%Y')} "
            f"TO {date3_to.strftime('%d-%m-%Y')})"
        )

        total1 = "1.1 TOTAL"
        total2 = "2.1 TOTAL"
        total3 = "3.1 TOTAL"

        engine = get_engine()

        # =================================================
        # ORIGINAL BOOKING SUMMARY SQL
        # =================================================
        query = f"""
        SELECT
            S.PARTICULAR,
            S.ZONENAME,
            SUM(S.SML) AS LTL,
            SUM(S.FTL) AS FTL,
            SUM(S.TOTAL) AS TOTAL,

            (
                SUM(S.SML) * 100.0
            ) / NULLIF(
                SUM(S.TOTAL),
                0
            ) AS [% (SML.+LTL/TOTAL)],

            (
                SUM(S.NPBKG) * 100.0
            ) / NULLIF(
                SUM(S.TOTAL),
                0
            ) AS [% (NEPAL/TOTAL)]

        FROM
        (
            SELECT
                '{part1}' AS PARTICULAR,
                ZONE.ZONENAME,

                IIF(
                    CN.FTL <> 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 300000.0,
                    0
                ) AS SML,

                IIF(
                    CN.FTL = 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 300000.0,
                    0
                ) AS FTL,

                (
                    CN.TAMOUNT
                    - CN.SERVICETAX
                ) / 300000.0 AS TOTAL,

                IIF(
                    DST.ZONECODE = 'A0006',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 300000.0,
                    0
                ) AS NPBKG

            FROM CNMT CN WITH(NOLOCK)

            INNER JOIN STATIONMAST ORG
                ON ORG.STNCODE = CN.ORGCODE

            INNER JOIN VIEWSTATIONMAST ZONE
                ON ZONE.STNCODE = CN.ORGCODE

            LEFT JOIN STATIONMAST DST
                ON DST.STNCODE = CN.DESTCODE

            WHERE
                CN.GRDT >= '{from1_sql}'

                AND CN.GRDT < DATEADD(
                    DAY,
                    1,
                    '{to1_sql}'
                )

                AND CN.GRTYPE <> 'N'

            UNION ALL

            SELECT
                '{total1}',
                NULL,

                IIF(
                    CN.FTL <> 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 300000.0,
                    0
                ),

                IIF(
                    CN.FTL = 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 300000.0,
                    0
                ),

                (
                    CN.TAMOUNT
                    - CN.SERVICETAX
                ) / 300000.0,

                IIF(
                    DST.ZONECODE = 'A0006',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 300000.0,
                    0
                )

            FROM CNMT CN WITH(NOLOCK)

            INNER JOIN STATIONMAST ORG
                ON ORG.STNCODE = CN.ORGCODE

            INNER JOIN VIEWSTATIONMAST ZONE
                ON ZONE.STNCODE = CN.ORGCODE

            LEFT JOIN STATIONMAST DST
                ON DST.STNCODE = CN.DESTCODE

            WHERE
                CN.GRDT >= '{from1_sql}'

                AND CN.GRDT < DATEADD(
                    DAY,
                    1,
                    '{to1_sql}'
                )

                AND CN.GRTYPE <> 'N'

            UNION ALL

            SELECT
                '{part2}',
                ZONE.ZONENAME,

                IIF(
                    CN.FTL <> 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                IIF(
                    CN.FTL = 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                (
                    CN.TAMOUNT
                    - CN.SERVICETAX
                ) / 100000.0,

                IIF(
                    DST.ZONECODE = 'A0006',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                )

            FROM CNMT CN WITH(NOLOCK)

            INNER JOIN STATIONMAST ORG
                ON ORG.STNCODE = CN.ORGCODE

            INNER JOIN VIEWSTATIONMAST ZONE
                ON ZONE.STNCODE = CN.ORGCODE

            LEFT JOIN STATIONMAST DST
                ON DST.STNCODE = CN.DESTCODE

            WHERE
                CN.GRDT >= '{from2_sql}'

                AND CN.GRDT < DATEADD(
                    DAY,
                    1,
                    '{to2_sql}'
                )

                AND CN.GRTYPE <> 'N'

            UNION ALL

            SELECT
                '{total2}',
                NULL,

                IIF(
                    CN.FTL <> 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                IIF(
                    CN.FTL = 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                (
                    CN.TAMOUNT
                    - CN.SERVICETAX
                ) / 100000.0,

                IIF(
                    DST.ZONECODE = 'A0006',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                )

            FROM CNMT CN WITH(NOLOCK)

            INNER JOIN STATIONMAST ORG
                ON ORG.STNCODE = CN.ORGCODE

            INNER JOIN VIEWSTATIONMAST ZONE
                ON ZONE.STNCODE = CN.ORGCODE

            LEFT JOIN STATIONMAST DST
                ON DST.STNCODE = CN.DESTCODE

            WHERE
                CN.GRDT >= '{from2_sql}'

                AND CN.GRDT < DATEADD(
                    DAY,
                    1,
                    '{to2_sql}'
                )

                AND CN.GRTYPE <> 'N'

            UNION ALL

            SELECT
                '{part3}',
                ZONE.ZONENAME,

                IIF(
                    CN.FTL <> 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                IIF(
                    CN.FTL = 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                (
                    CN.TAMOUNT
                    - CN.SERVICETAX
                ) / 100000.0,

                IIF(
                    DST.ZONECODE = 'A0006',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                )

            FROM CNMT CN WITH(NOLOCK)

            INNER JOIN STATIONMAST ORG
                ON ORG.STNCODE = CN.ORGCODE

            INNER JOIN VIEWSTATIONMAST ZONE
                ON ZONE.STNCODE = CN.ORGCODE

            LEFT JOIN STATIONMAST DST
                ON DST.STNCODE = CN.DESTCODE

            WHERE
                CN.GRDT >= '{from3_sql}'

                AND CN.GRDT < DATEADD(
                    DAY,
                    1,
                    '{to3_sql}'
                )

                AND CN.GRTYPE <> 'N'

            UNION ALL

            SELECT
                '{total3}',
                NULL,

                IIF(
                    CN.FTL <> 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                IIF(
                    CN.FTL = 'Y',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                ),

                (
                    CN.TAMOUNT
                    - CN.SERVICETAX
                ) / 100000.0,

                IIF(
                    DST.ZONECODE = 'A0006',
                    (
                        CN.TAMOUNT
                        - CN.SERVICETAX
                    ) / 100000.0,
                    0
                )

            FROM CNMT CN WITH(NOLOCK)

            INNER JOIN STATIONMAST ORG
                ON ORG.STNCODE = CN.ORGCODE

            INNER JOIN VIEWSTATIONMAST ZONE
                ON ZONE.STNCODE = CN.ORGCODE

            LEFT JOIN STATIONMAST DST
                ON DST.STNCODE = CN.DESTCODE

            WHERE
                CN.GRDT >= '{from3_sql}'

                AND CN.GRDT < DATEADD(
                    DAY,
                    1,
                    '{to3_sql}'
                )

                AND CN.GRTYPE <> 'N'

        ) AS S

        GROUP BY
            S.PARTICULAR,
            S.ZONENAME

        ORDER BY
            S.PARTICULAR,

            IIF(
                S.ZONENAME = 'NORTH EAST ZONE',
                1,
                IIF(
                    S.ZONENAME = 'EAST ZONE',
                    2,
                    IIF(
                        S.ZONENAME = 'NORTH ZONE',
                        3,
                        IIF(
                            S.ZONENAME = 'SOUTH ZONE',
                            4,
                            IIF(
                                S.ZONENAME = 'WEST ZONE',
                                5,
                                IIF(
                                    S.ZONENAME = 'NEPAL ZONE',
                                    6,
                                    7
                                )
                            )
                        )
                    )
                )
            ),

            S.ZONENAME
        """

        df = pd.read_sql(
            query,
            engine,
        )

        return prepare_dataframe_for_aggrid(df)

    except Exception as error:
        st.error(
            f"Booking Summary Turnover report error: {error}"
        )
        return pd.DataFrame()


# =========================================================
# REPORT DISPLAY
# =========================================================
def display_booking_summary_report(df):
    if df is None or df.empty:
        st.warning("No data found.")
        return

    try:
        gb = GridOptionsBuilder.from_dataframe(df)

        gb.configure_default_column(
            sortable=True,
            filter=True,
            resizable=True,
            minWidth=110,
        )

        if "PARTICULAR" in df.columns:
            gb.configure_column(
                "PARTICULAR",
                header_name="Period",
                pinned="left",
                minWidth=290,
            )

        if "ZONENAME" in df.columns:
            gb.configure_column(
                "ZONENAME",
                header_name="Zone",
                pinned="left",
                minWidth=160,
            )

        for column in df.columns[2:]:
            gb.configure_column(
                column,
                type=["numericColumn"],
                minWidth=135,
            )

        grid_options = gb.build()

        AgGrid(
            df,
            gridOptions=grid_options,
            height=500,
            theme="streamlit",
            enable_enterprise_modules=False,
            allow_unsafe_jscode=False,
            key="booking_summary_turnover_grid",
        )

    except Exception:
        st.dataframe(
            df,
            use_container_width=True,
            height=500,
            hide_index=True,
        )

    excel_file = to_excel(df)

    st.download_button(
        label="📥 Export To Excel",
        data=excel_file,
        file_name="BookingSummaryTurnover.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
        key="booking_summary_export",
    )


# =========================================================
# MAIN UI FUNCTION
# =========================================================
def show_BookingSummaryTurnover():
    apply_report_css()

    defaults = get_default_dates()

    st.markdown(
        '<div class="report-title">'
        'Booking Summary Turnover Report'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="report-subtitle">'
        'Zone-wise LTL, FTL, total and Nepal booking analysis'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(
        3,
        gap="small",
    )

    with col1:
        st.markdown(
            '<div class="period-title">'
            'Previous 3 Months'
            '</div>',
            unsafe_allow_html=True,
        )

        d1_from = st.date_input(
            "From",
            value=defaults[
                "previous_three_month_start"
            ],
            format="DD-MM-YYYY",
            key="booking_summary_p1_from",
        )

        d1_to = st.date_input(
            "To",
            value=defaults[
                "previous_three_month_end"
            ],
            format="DD-MM-YYYY",
            key="booking_summary_p1_to",
        )

    with col2:
        st.markdown(
            '<div class="period-title">'
            'Previous Month'
            '</div>',
            unsafe_allow_html=True,
        )

        d2_from = st.date_input(
            "From",
            value=defaults[
                "previous_month_start"
            ],
            format="DD-MM-YYYY",
            key="booking_summary_p2_from",
        )

        d2_to = st.date_input(
            "To",
            value=defaults[
                "previous_month_end"
            ],
            format="DD-MM-YYYY",
            key="booking_summary_p2_to",
        )

    with col3:
        st.markdown(
            '<div class="period-title">'
            'Current Month'
            '</div>',
            unsafe_allow_html=True,
        )

        d3_from = st.date_input(
            "From",
            value=defaults[
                "current_month_start"
            ],
            format="DD-MM-YYYY",
            key="booking_summary_p3_from",
        )

        d3_to = st.date_input(
            "To",
            value=defaults["today"],
            format="DD-MM-YYYY",
            key="booking_summary_p3_to",
        )

    if st.button(
        "Generate Report",
        use_container_width=True,
        key="generate_booking_summary_report",
    ):
        with st.spinner(
            "Generating Booking Summary Turnover report..."
        ):
            df = get_Booking_summary_trunover(
                d1_from,
                d1_to,
                d2_from,
                d2_to,
                d3_from,
                d3_to,
            )

        display_booking_summary_report(df)


# =========================================================
# OPTIONAL FUNCTION ALIASES
# =========================================================
def show_booking_summary_turnover():
    show_BookingSummaryTurnover()


def show_Booking_summary_trunover():
    show_BookingSummaryTurnover()