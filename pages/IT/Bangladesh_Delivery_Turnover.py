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
    return output


# ------------------------------------
# DYNAMIC COLUMN NAME FUNCTION
# ------------------------------------
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


# ------------------------------------
# DATA FUNCTION
# ------------------------------------
def get_bangladesh_delivery_turnover(
        date1_from, date1_to,
        date2_from, date2_to,
        date3_from, date3_to):

    try:
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
        # DYNAMIC COLUMN NAMES
        # ------------------------------------
        col1_non_ftl = format_date_range(
            date1_from,
            date1_to,
            False,
        )

        col2_non_ftl = format_date_range(
            date2_from,
            date2_to,
            False,
        )

        col3_non_ftl = format_date_range(
            date3_from,
            date3_to,
            False,
        )

        col1_ftl = format_date_range(
            date1_from,
            date1_to,
            True,
        )

        col2_ftl = format_date_range(
            date2_from,
            date2_to,
            True,
        )

        col3_ftl = format_date_range(
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
                         AND CN.GRDT BETWEEN '{from1_sql}' AND '{to1_sql}'
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
                         AND CN.GRDT BETWEEN '{from2_sql}' AND '{to2_sql}'
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
                         AND CN.GRDT BETWEEN '{from3_sql}' AND '{to3_sql}'
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
                         AND CN.GRDT BETWEEN '{from1_sql}' AND '{to1_sql}'
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
                         AND CN.GRDT BETWEEN '{from2_sql}' AND '{to2_sql}'
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
                         AND CN.GRDT BETWEEN '{from3_sql}' AND '{to3_sql}'
                    THEN (
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
            CN.GRDT BETWEEN '{from1_sql}' AND '{to3_sql}'

            AND CN.GRTYPE <> 'N'

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

        return df.round(2)

    except Exception as e:
        st.error(str(e))
        return pd.DataFrame()


# -----------------------------------
# UI FUNCTION
# -----------------------------------
def show_bangladesh_delivery_turnover():

    st.title("Bangladesh Delivery Turnover")

    df = pd.DataFrame()

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

        df = get_bangladesh_delivery_turnover(
            d1_from,
            d1_to,
            d2_from,
            d2_to,
            d3_from,
            d3_to,
        )

        if not df.empty:

            gb = GridOptionsBuilder.from_dataframe(df)

            gb.configure_default_column(
                sortable=True,
                filter=True,
                resizable=True,
            )

            grid_options = gb.build()

            AgGrid(
                df,
                gridOptions=grid_options,
                height=500,
                fit_columns_on_grid_load=True,
            )

            excel_file = to_excel(df)

            st.download_button(
                label="📥 Export To Excel",
                data=excel_file,
                file_name="BangladeshDeliveryTurnover.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="bd_export_excel",
            )

        else:
            st.warning("No data found.")
