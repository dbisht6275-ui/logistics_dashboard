import streamlit as st
import pandas as pd

from datetime import date, timedelta
from io import BytesIO

from services.database import get_engine
from st_aggrid import AgGrid, GridOptionsBuilder


# =========================================================
# PAGE CSS
# =========================================================
def apply_report_css():
    st.markdown(
        """
        <style>
        /* Reduce main page spacing */
        .main .block-container {
            max-width: 100%;
            padding-top: 1rem;
            padding-left: 1.4rem;
            padding-right: 1.4rem;
            padding-bottom: 1rem;
        }

        /* Compact report title */
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

        /* Compact section title */
        .period-title {
            font-size: 15px;
            font-weight: 700;
            color: #17365d;
            margin-bottom: 2px;
        }

        /* Reduce widget vertical spacing */
        div[data-testid="stVerticalBlock"] {
            gap: 0.55rem;
        }

        div[data-testid="stDateInput"] {
            margin-bottom: 0;
        }

        div[data-testid="stRadio"] {
            margin-top: -4px;
            margin-bottom: 2px;
        }

        /* Compact button */
        div.stButton > button {
            min-height: 38px;
            font-weight: 600;
        }

        /* Compact labels */
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
            sheet_name="Report",
        )

    output.seek(0)
    return output.getvalue()


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
        "ZONENAME",
        "HUBNAME",
        "BRANCH",
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
# DATE HELPERS
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

    start_month = (
        previous_three_month_end.month - 2
    )

    start_year = previous_three_month_end.year

    while start_month <= 0:
        start_month += 12
        start_year -= 1

    previous_three_month_start = date(
        start_year,
        start_month,
        1,
    )

    one_year_start = date(
        today.year - 1,
        today.month,
        today.day,
    )

    return {
        "today": today,
        "current_month_start": current_month_start,
        "previous_month_start": previous_month_start,
        "previous_month_end": previous_month_end,
        "previous_three_month_start": (
            previous_three_month_start
        ),
        "previous_three_month_end": (
            previous_three_month_end
        ),
        "one_year_start": one_year_start,
    }


def format_period_column(
    period_number,
    period_label,
    from_date,
    to_date,
    is_ftl=False,
):
    period_name = (
        f"{period_number}. {period_label} "
        f"({from_date.strftime('%d-%m-%Y')} "
        f"TO {to_date.strftime('%d-%m-%Y')})"
    )

    if is_ftl:
        period_name += " FTL"
    else:
        period_name += " NON-FTL"

    return period_name


# =========================================================
# THREE-PERIOD REPORT
# =========================================================
def get_bangladesh_delivery_turnover(
    date1_from,
    date1_to,
    date2_from,
    date2_to,
    date3_from,
    date3_to,
):
    try:
        if date1_from > date1_to:
            raise ValueError(
                "Previous 3 Months: From Date "
                "cannot be after To Date."
            )

        if date2_from > date2_to:
            raise ValueError(
                "Previous Month: From Date "
                "cannot be after To Date."
            )

        if date3_from > date3_to:
            raise ValueError(
                "Current Month: From Date "
                "cannot be after To Date."
            )

        from1_sql = date1_from.strftime("%Y-%m-%d")
        to1_sql = date1_to.strftime("%Y-%m-%d")

        from2_sql = date2_from.strftime("%Y-%m-%d")
        to2_sql = date2_to.strftime("%Y-%m-%d")

        from3_sql = date3_from.strftime("%Y-%m-%d")
        to3_sql = date3_to.strftime("%Y-%m-%d")

        col1_non_ftl = format_period_column(
            1,
            "PREVIOUS 3 MONTHS",
            date1_from,
            date1_to,
            False,
        )

        col2_non_ftl = format_period_column(
            2,
            "PREVIOUS MONTH",
            date2_from,
            date2_to,
            False,
        )

        col3_non_ftl = format_period_column(
            3,
            "CURRENT MONTH",
            date3_from,
            date3_to,
            False,
        )

        col1_ftl = format_period_column(
            1,
            "PREVIOUS 3 MONTHS",
            date1_from,
            date1_to,
            True,
        )

        col2_ftl = format_period_column(
            2,
            "PREVIOUS MONTH",
            date2_from,
            date2_to,
            True,
        )

        col3_ftl = format_period_column(
            3,
            "CURRENT MONTH",
            date3_from,
            date3_to,
            True,
        )

        engine = get_engine()

        query = f"""
        SELECT
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            ORG.STNNAME AS BRANCH,

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                         AND CN.GRDT >= '{from1_sql}'
                         AND CN.GRDT < DATEADD(
                             DAY,
                             1,
                             '{to1_sql}'
                         )
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 300000.0
                    ELSE 0
                END
            ) AS [{col1_non_ftl}],

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                         AND CN.GRDT >= '{from2_sql}'
                         AND CN.GRDT < DATEADD(
                             DAY,
                             1,
                             '{to2_sql}'
                         )
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                    ELSE 0
                END
            ) AS [{col2_non_ftl}],

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                         AND CN.GRDT >= '{from3_sql}'
                         AND CN.GRDT < DATEADD(
                             DAY,
                             1,
                             '{to3_sql}'
                         )
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                    ELSE 0
                END
            ) AS [{col3_non_ftl}],

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') = 'Y'
                         AND CN.GRDT >= '{from1_sql}'
                         AND CN.GRDT < DATEADD(
                             DAY,
                             1,
                             '{to1_sql}'
                         )
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 300000.0
                    ELSE 0
                END
            ) AS [{col1_ftl}],

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') = 'Y'
                         AND CN.GRDT >= '{from2_sql}'
                         AND CN.GRDT < DATEADD(
                             DAY,
                             1,
                             '{to2_sql}'
                         )
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                    ELSE 0
                END
            ) AS [{col2_ftl}],

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') = 'Y'
                         AND CN.GRDT >= '{from3_sql}'
                         AND CN.GRDT < DATEADD(
                             DAY,
                             1,
                             '{to3_sql}'
                         )
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 100000.0
                    ELSE 0
                END
            ) AS [{col3_ftl}]

        FROM CNMT CN WITH(NOLOCK)

        INNER JOIN STATIONMAST ORG
            ON ORG.STNCODE = CN.ORGCODE

        INNER JOIN VIEWSTATIONMAST ZONE
            ON ZONE.STNCODE = CN.ORGCODE

        INNER JOIN STATIONMAST DST
            ON DST.STNCODE = CN.DESTCODE

        WHERE
            CN.GRTYPE <> 'N'

            AND (
                (
                    CN.GRDT >= '{from1_sql}'
                    AND CN.GRDT < DATEADD(
                        DAY,
                        1,
                        '{to1_sql}'
                    )
                )
                OR
                (
                    CN.GRDT >= '{from2_sql}'
                    AND CN.GRDT < DATEADD(
                        DAY,
                        1,
                        '{to2_sql}'
                    )
                )
                OR
                (
                    CN.GRDT >= '{from3_sql}'
                    AND CN.GRDT < DATEADD(
                        DAY,
                        1,
                        '{to3_sql}'
                    )
                )
            )

            AND (
                UPPER(
                    LTRIM(
                        RTRIM(
                            ISNULL(DST.COUNTRY, '')
                        )
                    )
                ) = 'BANGLADESH'

                OR

                UPPER(
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

        GROUP BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            ORG.STNNAME

        ORDER BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            ORG.STNNAME
        """

        df = pd.read_sql(
            query,
            engine,
        )

        return prepare_dataframe_for_aggrid(df)

    except Exception as error:
        st.error(
            f"Bangladesh comparison report error: {error}"
        )
        return pd.DataFrame()


# =========================================================
# ONE-YEAR REPORT
# =========================================================
def get_bangladesh_one_year_turnover(
    year_from,
    year_to,
):
    try:
        if year_from > year_to:
            raise ValueError(
                "One Year From Date cannot be after To Date."
            )

        from_sql = year_from.strftime("%Y-%m-%d")
        to_sql = year_to.strftime("%Y-%m-%d")

        period_name = (
            f"{year_from.strftime('%d-%m-%Y')} "
            f"TO "
            f"{year_to.strftime('%d-%m-%Y')}"
        )

        engine = get_engine()

        query = f"""
        SELECT
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            ORG.STNNAME AS BRANCH,

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 1200000.0
                    ELSE 0
                END
            ) AS [{period_name} NON-FTL],

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') = 'Y'
                    THEN
                        (
                            ISNULL(CN.TAMOUNT, 0)
                            - ISNULL(CN.SERVICETAX, 0)
                        ) / 1200000.0
                    ELSE 0
                END
            ) AS [{period_name} FTL],

            SUM(
                (
                    ISNULL(CN.TAMOUNT, 0)
                    - ISNULL(CN.SERVICETAX, 0)
                ) / 1200000.0
            ) AS [{period_name} TOTAL]

        FROM CNMT CN WITH(NOLOCK)

        INNER JOIN STATIONMAST ORG
            ON ORG.STNCODE = CN.ORGCODE

        INNER JOIN VIEWSTATIONMAST ZONE
            ON ZONE.STNCODE = CN.ORGCODE

        INNER JOIN STATIONMAST DST
            ON DST.STNCODE = CN.DESTCODE

        WHERE
            CN.GRDT >= '{from_sql}'

            AND CN.GRDT < DATEADD(
                DAY,
                1,
                '{to_sql}'
            )

            AND CN.GRTYPE <> 'N'

            AND (
                UPPER(
                    LTRIM(
                        RTRIM(
                            ISNULL(DST.COUNTRY, '')
                        )
                    )
                ) = 'BANGLADESH'

                OR

                UPPER(
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

        GROUP BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            ORG.STNNAME

        ORDER BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            ORG.STNNAME
        """

        df = pd.read_sql(
            query,
            engine,
        )

        return prepare_dataframe_for_aggrid(df)

    except Exception as error:
        st.error(
            f"Bangladesh one-year report error: {error}"
        )
        return pd.DataFrame()


# =========================================================
# REPORT DISPLAY
# =========================================================
def display_report(df, report_type):
    if df is None or df.empty:
        st.warning("No data found.")
        return

    try:
        gb = GridOptionsBuilder.from_dataframe(df)

        gb.configure_default_column(
            sortable=True,
            filter=True,
            resizable=True,
            minWidth=115,
        )

        if "ZONENAME" in df.columns:
            gb.configure_column(
                "ZONENAME",
                header_name="Zone",
                pinned="left",
                minWidth=140,
            )

        if "HUBNAME" in df.columns:
            gb.configure_column(
                "HUBNAME",
                header_name="Hub",
                pinned="left",
                minWidth=150,
            )

        if "BRANCH" in df.columns:
            gb.configure_column(
                "BRANCH",
                header_name="Branch",
                pinned="left",
                minWidth=170,
            )

        for column in df.columns[3:]:
            gb.configure_column(
                column,
                type=["numericColumn"],
                minWidth=180,
            )

        grid_options = gb.build()

        AgGrid(
            df,
            gridOptions=grid_options,
            height=470,
            theme="streamlit",
            enable_enterprise_modules=False,
            allow_unsafe_jscode=False,
            key=f"bangladesh_grid_{report_type}",
        )

    except Exception:
        st.dataframe(
            df,
            use_container_width=True,
            height=470,
            hide_index=True,
        )

    excel_file = to_excel(df)

    if report_type == "One Year Average":
        file_name = "BangladeshOneYearTurnover.xlsx"
        download_key = "bd_one_year_export"
    else:
        file_name = "BangladeshDeliveryTurnover.xlsx"
        download_key = "bd_comparison_export"

    st.download_button(
        label="📥 Export To Excel",
        data=excel_file,
        file_name=file_name,
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
        key=download_key,
    )


# =========================================================
# MAIN PAGE
# =========================================================
def show_bangladesh_delivery_turnover():
    apply_report_css()

    defaults = get_default_dates()

    st.markdown(
        '<div class="report-title">'
        'Bangladesh Delivery Turnover Report'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="report-subtitle">'
        'Branch-wise Bangladesh delivery turnover analysis'
        '</div>',
        unsafe_allow_html=True,
    )

    report_type = st.radio(
        "Report Type",
        [
            "Period Comparison",
            "One Year Average",
        ],
        horizontal=True,
        key="bd_report_type",
    )

    if report_type == "Period Comparison":
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
                key="bd_p1_from",
            )

            d1_to = st.date_input(
                "To",
                value=defaults[
                    "previous_three_month_end"
                ],
                format="DD-MM-YYYY",
                key="bd_p1_to",
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
                key="bd_p2_from",
            )

            d2_to = st.date_input(
                "To",
                value=defaults[
                    "previous_month_end"
                ],
                format="DD-MM-YYYY",
                key="bd_p2_to",
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
                key="bd_p3_from",
            )

            d3_to = st.date_input(
                "To",
                value=defaults["today"],
                format="DD-MM-YYYY",
                key="bd_p3_to",
            )

        if st.button(
            "Generate Report",
            use_container_width=True,
            key="bd_generate_comparison",
        ):
            with st.spinner(
                "Generating Bangladesh report..."
            ):
                df = get_bangladesh_delivery_turnover(
                    d1_from,
                    d1_to,
                    d2_from,
                    d2_to,
                    d3_from,
                    d3_to,
                )

            display_report(
                df,
                report_type,
            )

    else:
        st.markdown(
            '<div class="period-title">'
            'One Year Period'
            '</div>',
            unsafe_allow_html=True,
        )

        year_col1, year_col2 = st.columns(
            2,
            gap="small",
        )

        with year_col1:
            year_from = st.date_input(
                "From Date",
                value=defaults["one_year_start"],
                format="DD-MM-YYYY",
                key="bd_year_from",
            )

        with year_col2:
            year_to = st.date_input(
                "To Date",
                value=defaults["today"],
                format="DD-MM-YYYY",
                key="bd_year_to",
            )

        if st.button(
            "Generate One Year Report",
            use_container_width=True,
            key="bd_generate_one_year",
        ):
            with st.spinner(
                "Generating one-year Bangladesh report..."
            ):
                df = get_bangladesh_one_year_turnover(
                    year_from,
                    year_to,
                )

            display_report(
                df,
                report_type,
            )


# =========================================================
# OPTIONAL ALIAS
# =========================================================
def show_bangladesh_turnover():
    show_bangladesh_delivery_turnover()
