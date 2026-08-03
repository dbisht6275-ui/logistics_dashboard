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
            margin: 0 0 10px 0;
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

        div[data-testid="stRadio"] {
            margin-top: -4px;
            margin-bottom: 2px;
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
            sheet_name="Branch Delivery",
        )

    output.seek(0)
    return output.getvalue()


# =========================================================
# DEFAULT DATES
# =========================================================
def get_default_dates():
    today = date.today()

    current_month_start = today.replace(day=1)

    previous_month_end = (
        current_month_start - timedelta(days=1)
    )

    previous_month_start = (
        previous_month_end.replace(day=1)
    )

    previous_three_month_end = (
        previous_month_start - timedelta(days=1)
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

    try:
        one_year_start = today.replace(
            year=today.year - 1
        )
    except ValueError:
        one_year_start = today.replace(
            year=today.year - 1,
            day=28,
        )

    return {
        "today": today,
        "current_month_start": current_month_start,
        "previous_month_start": previous_month_start,
        "previous_month_end": previous_month_end,
        "previous_three_month_start": previous_three_month_start,
        "previous_three_month_end": previous_three_month_end,
        "one_year_start": one_year_start,
    }


# =========================================================
# AGGRID DATA CLEANING
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
# DYNAMIC COLUMN NAME
# =========================================================
def format_date_range(
    period_number,
    period_label,
    from_date,
    to_date,
    is_ftl=False,
):
    column_name = (
        f"{period_number}. {period_label} "
        f"({from_date.strftime('%d-%m-%Y')} "
        f"TO {to_date.strftime('%d-%m-%Y')})"
    )

    if is_ftl:
        column_name += " FTL"
    else:
        column_name += " NON-FTL"

    return column_name


# =========================================================
# THREE-PERIOD REPORT
# ORIGINAL SQL LOGIC RETAINED
# =========================================================
def get_Branch_wise_delivery_turnover(
    date1_from,
    date1_to,
    date2_from,
    date2_to,
    date3_from,
    date3_to,
):
    try:
        # -------------------------------------------------
        # DATE VALIDATION
        # -------------------------------------------------
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

        # -------------------------------------------------
        # SQL DATE FORMAT
        # -------------------------------------------------
        from1_sql = date1_from.strftime("%Y-%m-%d")
        to1_sql = date1_to.strftime("%Y-%m-%d")

        from2_sql = date2_from.strftime("%Y-%m-%d")
        to2_sql = date2_to.strftime("%Y-%m-%d")

        from3_sql = date3_from.strftime("%Y-%m-%d")
        to3_sql = date3_to.strftime("%Y-%m-%d")

        # -------------------------------------------------
        # DYNAMIC COLUMN NAMES
        # -------------------------------------------------
        col1_non_ftl = format_date_range(
            1,
            "PREVIOUS 3 MONTHS",
            date1_from,
            date1_to,
            False,
        )

        col2_non_ftl = format_date_range(
            2,
            "PREVIOUS MONTH",
            date2_from,
            date2_to,
            False,
        )

        col3_non_ftl = format_date_range(
            3,
            "CURRENT MONTH",
            date3_from,
            date3_to,
            False,
        )

        col1_ftl = format_date_range(
            1,
            "PREVIOUS 3 MONTHS",
            date1_from,
            date1_to,
            True,
        )

        col2_ftl = format_date_range(
            2,
            "PREVIOUS MONTH",
            date2_from,
            date2_to,
            True,
        )

        col3_ftl = format_date_range(
            3,
            "CURRENT MONTH",
            date3_from,
            date3_to,
            True,
        )

        engine = get_engine()

        # =================================================
        # ORIGINAL SQL QUERY
        # =================================================
        query = f"""
        SELECT 
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            BRANCHES.BRANCH,

            SUM(
                CASE
                    WHEN CN.FTL <> 'Y'
                         AND CN.GRDT BETWEEN
                             '{from1_sql}' AND '{to1_sql}'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 300000
                    ELSE 0
                END
            ) AS [{col1_non_ftl}],

            SUM(
                CASE
                    WHEN CN.FTL <> 'Y'
                         AND CN.GRDT BETWEEN
                             '{from2_sql}' AND '{to2_sql}'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 100000
                    ELSE 0
                END
            ) AS [{col2_non_ftl}],

            SUM(
                CASE
                    WHEN CN.FTL <> 'Y'
                         AND CN.GRDT BETWEEN
                             '{from3_sql}' AND '{to3_sql}'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 100000
                    ELSE 0
                END
            ) AS [{col3_non_ftl}],

            SUM(
                CASE
                    WHEN CN.FTL = 'Y'
                         AND CN.GRDT BETWEEN
                             '{from1_sql}' AND '{to1_sql}'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 300000
                    ELSE 0
                END
            ) AS [{col1_ftl}],

            SUM(
                CASE
                    WHEN CN.FTL = 'Y'
                         AND CN.GRDT BETWEEN
                             '{from2_sql}' AND '{to2_sql}'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 100000
                    ELSE 0
                END
            ) AS [{col2_ftl}],

            SUM(
                CASE
                    WHEN CN.FTL = 'Y'
                         AND CN.GRDT BETWEEN
                             '{from3_sql}' AND '{to3_sql}'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 100000
                    ELSE 0
                END
            ) AS [{col3_ftl}]

        FROM CNMT CN

        INNER JOIN STATIONMAST DEST
            ON DEST.STNCODE = CN.DESTCODE

        LEFT JOIN STATIONMAST MRG
            ON MRG.STNCODE = DEST.MERGESTNCODE

        CROSS APPLY
        (
            SELECT 
                CASE COALESCE(
                    MRG.STNNAME,
                    DEST.STNNAME
                )
                    WHEN 'BIRGUNJ'
                        THEN 'RAXAUL'

                    WHEN 'BHAIRAHAWA'
                        THEN 'SUNAULI'

                    WHEN 'BIRATNAGAR'
                        THEN 'JOGBANI'

                    WHEN 'NEPALGUNJ'
                        THEN 'RUPAIDIHA'

                    WHEN 'DHANGURI'
                        THEN 'PALIA'

                    ELSE COALESCE(
                        MRG.STNNAME,
                        DEST.STNNAME
                    )
                END AS BRANCH

        ) AS BRANCHES

        LEFT JOIN VIEWSTATIONMAST ZONE
            ON ZONE.STNNAME = BRANCHES.BRANCH

        WHERE
            CN.GRDT BETWEEN
                '{from1_sql}' AND '{to3_sql}'

        GROUP BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            BRANCHES.BRANCH

        ORDER BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            BRANCHES.BRANCH
        """

        df = pd.read_sql(
            query,
            engine,
        )

        return prepare_dataframe_for_aggrid(df)

    except Exception as error:
        st.error(
            f"Branch Wise Delivery Turnover report error: "
            f"{error}"
        )
        return pd.DataFrame()


# =========================================================
# ONE-YEAR REPORT
# SAME BRANCH MAPPING AND QUERY STRUCTURE
# =========================================================
def get_branch_wise_delivery_one_year_turnover(
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
            f"TO {year_to.strftime('%d-%m-%Y')}"
        )

        engine = get_engine()

        query = f"""
        SELECT 
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            BRANCHES.BRANCH,

            SUM(
                CASE
                    WHEN CN.FTL <> 'Y'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 1200000.0
                    ELSE 0
                END
            ) AS [{period_name} NON-FTL],

            SUM(
                CASE
                    WHEN CN.FTL = 'Y'
                    THEN
                        (CN.TAMOUNT - CN.SERVICETAX)
                        / 1200000.0
                    ELSE 0
                END
            ) AS [{period_name} FTL],

            SUM(
                (CN.TAMOUNT - CN.SERVICETAX)
                / 1200000.0
            ) AS [{period_name} TOTAL]

        FROM CNMT CN

        INNER JOIN STATIONMAST DEST
            ON DEST.STNCODE = CN.DESTCODE

        LEFT JOIN STATIONMAST MRG
            ON MRG.STNCODE = DEST.MERGESTNCODE

        CROSS APPLY
        (
            SELECT 
                CASE COALESCE(
                    MRG.STNNAME,
                    DEST.STNNAME
                )
                    WHEN 'BIRGUNJ'
                        THEN 'RAXAUL'

                    WHEN 'BHAIRAHAWA'
                        THEN 'SUNAULI'

                    WHEN 'BIRATNAGAR'
                        THEN 'JOGBANI'

                    WHEN 'NEPALGUNJ'
                        THEN 'RUPAIDIHA'

                    WHEN 'DHANGURI'
                        THEN 'PALIA'

                    ELSE COALESCE(
                        MRG.STNNAME,
                        DEST.STNNAME
                    )
                END AS BRANCH

        ) AS BRANCHES

        LEFT JOIN VIEWSTATIONMAST ZONE
            ON ZONE.STNNAME = BRANCHES.BRANCH

        WHERE
            CN.GRDT BETWEEN
                '{from_sql}' AND '{to_sql}'

        GROUP BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            BRANCHES.BRANCH

        ORDER BY
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            BRANCHES.BRANCH
        """

        df = pd.read_sql(
            query,
            engine,
        )

        return prepare_dataframe_for_aggrid(df)

    except Exception as error:
        st.error(
            f"Branch Wise Delivery one-year report error: "
            f"{error}"
        )
        return pd.DataFrame()


# =========================================================
# REPORT DISPLAY
# =========================================================
def display_branch_delivery_report(
    df,
    report_type,
):
    if df is None or df.empty:
        st.warning("No data found.")
        return

    try:
        gb = GridOptionsBuilder.from_dataframe(df)

        gb.configure_default_column(
            sortable=True,
            filter=True,
            resizable=True,
            minWidth=105,
        )

        if "ZONENAME" in df.columns:
            gb.configure_column(
                "ZONENAME",
                header_name="Zone",
                pinned="left",
                minWidth=150,
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
                header_name="Delivery Branch",
                pinned="left",
                minWidth=180,
            )

        for column in df.columns[3:]:
            gb.configure_column(
                column,
                type=["numericColumn"],
                minWidth=175,
            )

        grid_options = gb.build()

        AgGrid(
            df,
            gridOptions=grid_options,
            height=500,
            theme="streamlit",
            enable_enterprise_modules=False,
            allow_unsafe_jscode=False,
            key=f"branch_delivery_grid_{report_type}",
        )

    except Exception:
        st.dataframe(
            df,
            use_container_width=True,
            height=500,
            hide_index=True,
        )

    excel_file = to_excel(df)

    if report_type == "One Year Average":
        file_name = (
            "BranchWiseDeliveryOneYearTurnover.xlsx"
        )
        export_key = (
            "branch_delivery_one_year_export"
        )
    else:
        file_name = "BranchWiseDeliveryTurnover.xlsx"
        export_key = (
            "branch_delivery_comparison_export"
        )

    st.download_button(
        label="📥 Export To Excel",
        data=excel_file,
        file_name=file_name,
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
        key=export_key,
    )


# =========================================================
# MAIN UI
# =========================================================
def show_branch_wise_delivery_turnover():
    apply_report_css()

    defaults = get_default_dates()

    st.markdown(
        '<div class="report-title">'
        'Branch Wise Delivery Turnover Report'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="report-subtitle">'
        'Delivery branch-wise Non-FTL and FTL '
        'turnover analysis'
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
        key="branch_delivery_report_type",
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
                key="branch_delivery_p1_from",
            )

            d1_to = st.date_input(
                "To",
                value=defaults[
                    "previous_three_month_end"
                ],
                format="DD-MM-YYYY",
                key="branch_delivery_p1_to",
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
                key="branch_delivery_p2_from",
            )

            d2_to = st.date_input(
                "To",
                value=defaults[
                    "previous_month_end"
                ],
                format="DD-MM-YYYY",
                key="branch_delivery_p2_to",
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
                key="branch_delivery_p3_from",
            )

            d3_to = st.date_input(
                "To",
                value=defaults["today"],
                format="DD-MM-YYYY",
                key="branch_delivery_p3_to",
            )

        if st.button(
            "Generate Report",
            use_container_width=True,
            key="generate_branch_delivery_comparison",
        ):
            with st.spinner(
                "Generating Branch Wise Delivery report..."
            ):
                df = get_Branch_wise_delivery_turnover(
                    d1_from,
                    d1_to,
                    d2_from,
                    d2_to,
                    d3_from,
                    d3_to,
                )

            display_branch_delivery_report(
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
                key="branch_delivery_year_from",
            )

        with year_col2:
            year_to = st.date_input(
                "To Date",
                value=defaults["today"],
                format="DD-MM-YYYY",
                key="branch_delivery_year_to",
            )

        if st.button(
            "Generate One Year Report",
            use_container_width=True,
            key="generate_branch_delivery_one_year",
        ):
            with st.spinner(
                "Generating one-year Branch Delivery report..."
            ):
                df = (
                    get_branch_wise_delivery_one_year_turnover(
                        year_from,
                        year_to,
                    )
                )

            display_branch_delivery_report(
                df,
                report_type,
            )


# =========================================================
# FUNCTION ALIASES
# =========================================================
def show_BranchWiseDeliveryTurnover():
    show_branch_wise_delivery_turnover()


def show_Branch_wise_delivery_turnover():
    show_branch_wise_delivery_turnover()