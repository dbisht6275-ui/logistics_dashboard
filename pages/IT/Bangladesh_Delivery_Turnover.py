import streamlit as st
import pandas as pd
from services.database import get_engine
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder


# ------------------------------------
# EXCEL EXPORT FUNCTION
# ------------------------------------
def to_excel(df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Report"
        )

    output.seek(0)
    return output.getvalue()


# ------------------------------------
# AGGRID DATA CLEANING
# ------------------------------------
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
                errors="coerce"
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


# ------------------------------------
# PERIOD COLUMN NAME
# ------------------------------------
def format_period_column(
    period_number,
    from_date,
    to_date,
    is_ftl=False
):
    period_name = (
        f"{period_number}. "
        f"{from_date.strftime('%d-%m-%Y')} "
        f"TO "
        f"{to_date.strftime('%d-%m-%Y')}"
    )

    if is_ftl:
        period_name += " FTL"
    else:
        period_name += " NON-FTL"

    return period_name


# ------------------------------------
# THREE-PERIOD DATA FUNCTION
# ------------------------------------
def get_bangladesh_delivery_turnover(
    date1_from,
    date1_to,
    date2_from,
    date2_to,
    date3_from,
    date3_to
):
    try:
        if date1_from > date1_to:
            raise ValueError(
                "Period 1 From Date cannot be after To Date."
            )

        if date2_from > date2_to:
            raise ValueError(
                "Period 2 From Date cannot be after To Date."
            )

        if date3_from > date3_to:
            raise ValueError(
                "Period 3 From Date cannot be after To Date."
            )

        from1_sql = date1_from.strftime("%Y-%m-%d")
        to1_sql = date1_to.strftime("%Y-%m-%d")

        from2_sql = date2_from.strftime("%Y-%m-%d")
        to2_sql = date2_to.strftime("%Y-%m-%d")

        from3_sql = date3_from.strftime("%Y-%m-%d")
        to3_sql = date3_to.strftime("%Y-%m-%d")

        col1_non_ftl = format_period_column(
            1, date1_from, date1_to, False
        )

        col2_non_ftl = format_period_column(
            2, date2_from, date2_to, False
        )

        col3_non_ftl = format_period_column(
            3, date3_from, date3_to, False
        )

        col1_ftl = format_period_column(
            1, date1_from, date1_to, True
        )

        col2_ftl = format_period_column(
            2, date2_from, date2_to, True
        )

        col3_ftl = format_period_column(
            3, date3_from, date3_to, True
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

        df = pd.read_sql(query, engine)

        return prepare_dataframe_for_aggrid(df)

    except Exception as error:
        st.error(
            f"Bangladesh three-period report error: {error}"
        )
        return pd.DataFrame()


# ------------------------------------
# ONE-YEAR DATA FUNCTION
# ------------------------------------
def get_bangladesh_one_year_turnover(
    year_from,
    year_to
):
    try:
        if year_from > year_to:
            raise ValueError(
                "Year From Date cannot be after Year To Date."
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

        df = pd.read_sql(query, engine)

        return prepare_dataframe_for_aggrid(df)

    except Exception as error:
        st.error(
            f"Bangladesh one-year report error: {error}"
        )
        return pd.DataFrame()


# ------------------------------------
# REPORT DISPLAY FUNCTION
# ------------------------------------
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
            minWidth=110
        )

        for column in df.columns[3:]:
            gb.configure_column(
                column,
                type=["numericColumn"]
            )

        grid_options = gb.build()

        AgGrid(
            df,
            gridOptions=grid_options,
            height=500,
            theme="streamlit",
            enable_enterprise_modules=False,
            allow_unsafe_jscode=False,
            key=f"bangladesh_grid_{report_type}"
        )

    except Exception:
        st.dataframe(
            df,
            use_container_width=True,
            height=500,
            hide_index=True
        )

    excel_file = to_excel(df)

    if report_type == "One Year Total":
        file_name = "BangladeshOneYearTurnover.xlsx"
        download_key = "bd_one_year_export"
    else:
        file_name = "BangladeshDeliveryTurnover.xlsx"
        download_key = "bd_three_period_export"

    st.download_button(
        label="📥 Export To Excel",
        data=excel_file,
        file_name=file_name,
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
        key=download_key
    )


# -----------------------------------
# MAIN UI FUNCTION
# -----------------------------------
def show_bangladesh_delivery_turnover():
    st.title("Bangladesh Delivery Turnover")

    report_type = st.radio(
        "Report Type",
        [
            "3 Period Comparison",
            "One Year Total",
        ],
        horizontal=True,
        key="bd_report_type"
    )

    if report_type == "3 Period Comparison":
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### Period 1")

            d1_from = st.date_input(
                "From",
                format="DD-MM-YYYY",
                key="bd_p1_from"
            )

            d1_to = st.date_input(
                "To",
                format="DD-MM-YYYY",
                key="bd_p1_to"
            )

        with col2:
            st.markdown("### Period 2")

            d2_from = st.date_input(
                "From",
                format="DD-MM-YYYY",
                key="bd_p2_from"
            )

            d2_to = st.date_input(
                "To",
                format="DD-MM-YYYY",
                key="bd_p2_to"
            )

        with col3:
            st.markdown("### Period 3")

            d3_from = st.date_input(
                "From",
                format="DD-MM-YYYY",
                key="bd_p3_from"
            )

            d3_to = st.date_input(
                "To",
                format="DD-MM-YYYY",
                key="bd_p3_to"
            )

        if st.button(
            "Generate Report",
            use_container_width=True,
            key="bd_generate_three_period"
        ):
            with st.spinner("Generating report..."):
                df = get_bangladesh_delivery_turnover(
                    d1_from,
                    d1_to,
                    d2_from,
                    d2_to,
                    d3_from,
                    d3_to
                )

            display_report(df, report_type)

    else:
        st.markdown("### One Year Period")

        year_col1, year_col2 = st.columns(2)

        with year_col1:
            year_from = st.date_input(
                "Year From",
                format="DD-MM-YYYY",
                key="bd_year_from"
            )

        with year_col2:
            year_to = st.date_input(
                "Year To",
                format="DD-MM-YYYY",
                key="bd_year_to"
            )

        if st.button(
            "Generate One Year Report",
            use_container_width=True,
            key="bd_generate_one_year"
        ):
            with st.spinner(
                "Generating one-year report..."
            ):
                df = get_bangladesh_one_year_turnover(
                    year_from,
                    year_to
                )

            display_report(df, report_type)


# -----------------------------------
# OPTIONAL ALIAS
# -----------------------------------
def show_bangladesh_turnover():
    show_bangladesh_delivery_turnover()
