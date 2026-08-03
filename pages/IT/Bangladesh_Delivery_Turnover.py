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
            sheet_name="Report",
        )

    output.seek(0)
    return output.getvalue()


# ------------------------------------
# DYNAMIC COLUMN NAME FUNCTION
# ------------------------------------
def format_date_range(
    period_number,
    from_date,
    to_date,
    is_ftl=False,
):
    """
    Creates unique headings even when two selected
    periods cover the same month.
    """

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

    return f"{period_number}. {column_name}"


# ------------------------------------
# DATAFRAME CLEANING FOR AGGRID
# ------------------------------------
def prepare_dataframe_for_aggrid(df):
    """
    Convert SQL-returned values into JSON-safe values
    before passing the DataFrame to AgGrid.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    clean_df = df.copy()

    # Make every column name a unique string.
    new_columns = []
    used_columns = {}

    for column in clean_df.columns:
        column_name = str(column).strip()

        if column_name in used_columns:
            used_columns[column_name] += 1
            column_name = (
                f"{column_name}_{used_columns[column_name]}"
            )
        else:
            used_columns[column_name] = 1

        new_columns.append(column_name)

    clean_df.columns = new_columns

    text_columns = [
        "ZONENAME",
        "HUBNAME",
        "BRANCH",
    ]

    # Clean text columns.
    for column in text_columns:
        if column in clean_df.columns:
            clean_df[column] = (
                clean_df[column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

    # Convert all remaining columns to regular floats.
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

    # Replace unsupported special values.
    clean_df = clean_df.replace(
        {
            float("inf"): 0.0,
            float("-inf"): 0.0,
        }
    )

    return clean_df


# ------------------------------------
# DATA FUNCTION
# ------------------------------------
def get_bangladesh_delivery_turnover(
    date1_from,
    date1_to,
    date2_from,
    date2_to,
    date3_from,
    date3_to,
):
    try:
        # ------------------------------------
        # DATE VALIDATION
        # ------------------------------------
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

        # ------------------------------------
        # DATE CONVERSION FOR SQL
        # ------------------------------------
        from1_sql = date1_from.strftime("%Y-%m-%d")
        to1_sql = date1_to.strftime("%Y-%m-%d")

        from2_sql = date2_from.strftime("%Y-%m-%d")
        to2_sql = date2_to.strftime("%Y-%m-%d")

        from3_sql = date3_from.strftime("%Y-%m-%d")
        to3_sql = date3_to.strftime("%Y-%m-%d")

        # ------------------------------------
        # DYNAMIC AND UNIQUE COLUMN NAMES
        # ------------------------------------
        col1_non_ftl = format_date_range(
            1,
            date1_from,
            date1_to,
            False,
        )

        col2_non_ftl = format_date_range(
            2,
            date2_from,
            date2_to,
            False,
        )

        col3_non_ftl = format_date_range(
            3,
            date3_from,
            date3_to,
            False,
        )

        col1_ftl = format_date_range(
            1,
            date1_from,
            date1_to,
            True,
        )

        col2_ftl = format_date_range(
            2,
            date2_from,
            date2_to,
            True,
        )

        col3_ftl = format_date_range(
            3,
            date3_from,
            date3_to,
            True,
        )

        engine = get_engine()

        # ------------------------------------
        # SQL QUERY
        # ------------------------------------
        query = f"""
        SELECT
            ZONE.ZONENAME,
            ZONE.HUBNAME,
            ORG.STNNAME AS BRANCH,

            SUM(
                CASE
                    WHEN ISNULL(CN.FTL, 'N') <> 'Y'
                    AND CN.GRDT BETWEEN
                        '{from1_sql}' AND '{to1_sql}'
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
                    AND CN.GRDT BETWEEN
                        '{from2_sql}' AND '{to2_sql}'
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
                    AND CN.GRDT BETWEEN
                        '{from3_sql}' AND '{to3_sql}'
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
                    AND CN.GRDT BETWEEN
                        '{from1_sql}' AND '{to1_sql}'
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
                    AND CN.GRDT BETWEEN
                        '{from2_sql}' AND '{to2_sql}'
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
                    AND CN.GRDT BETWEEN
                        '{from3_sql}' AND '{to3_sql}'
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
            CN.GRDT BETWEEN
                '{from1_sql}' AND '{to3_sql}'

            AND CN.GRTYPE <> 'N'

            AND
            (
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
                ) IN
                (
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
            f"Bangladesh report error: {error}"
        )
        return pd.DataFrame()


# -----------------------------------
# UI FUNCTION
# -----------------------------------
def show_bangladesh_delivery_turnover():

    st.title("Bangladesh Delivery Turnover")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Period 1")

        d1_from = st.date_input(
            "From",
            key="bd_p1_from",
        )

        d1_to = st.date_input(
            "To",
            key="bd_p1_to",
        )

    with col2:
        st.markdown("### Period 2")

        d2_from = st.date_input(
            "From",
            key="bd_p2_from",
        )

        d2_to = st.date_input(
            "To",
            key="bd_p2_to",
        )

    with col3:
        st.markdown("### Period 3")

        d3_from = st.date_input(
            "From",
            key="bd_p3_from",
        )

        d3_to = st.date_input(
            "To",
            key="bd_p3_to",
        )

    if st.button(
        "Generate Report",
        use_container_width=True,
        key="bd_generate_report",
    ):

        if d1_from > d1_to:
            st.error(
                "Period 1 From Date cannot be after To Date."
            )
            return

        if d2_from > d2_to:
            st.error(
                "Period 2 From Date cannot be after To Date."
            )
            return

        if d3_from > d3_to:
            st.error(
                "Period 3 From Date cannot be after To Date."
            )
            return

        with st.spinner("Generating report..."):
            df = get_bangladesh_delivery_turnover(
                d1_from,
                d1_to,
                d2_from,
                d2_to,
                d3_from,
                d3_to,
            )

        if df.empty:
            st.warning("No data found.")
            return

        # ------------------------------------
        # AGGRID
        # ------------------------------------
        try:
            gb = GridOptionsBuilder.from_dataframe(df)

            gb.configure_default_column(
                sortable=True,
                filter=True,
                resizable=True,
                minWidth=110,
            )

            # Configure numeric columns.
            for column in df.columns[3:]:
                gb.configure_column(
                    column,
                    type=["numericColumn"],
                    valueFormatter=(
                        "Number(params.value).toFixed(2)"
                    ),
                )

            grid_options = gb.build()

            AgGrid(
                df,
                gridOptions=grid_options,
                height=500,
                theme="streamlit",
                enable_enterprise_modules=False,
                allow_unsafe_jscode=False,
                key="bangladesh_delivery_grid",
            )

        except Exception as grid_error:
            # Keep the report usable even if AgGrid has a
            # package compatibility issue.
            st.warning(
                "AgGrid could not display the report. "
                "Showing the standard report table instead."
            )

            st.code(str(grid_error))

            st.dataframe(
                df,
                use_container_width=True,
                height=500,
                hide_index=True,
            )

        # ------------------------------------
        # EXCEL DOWNLOAD
        # ------------------------------------
        excel_file = to_excel(df)

        st.download_button(
            label="📥 Export To Excel",
            data=excel_file,
            file_name="BangladeshDeliveryTurnover.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key="bd_export_excel",
        )
