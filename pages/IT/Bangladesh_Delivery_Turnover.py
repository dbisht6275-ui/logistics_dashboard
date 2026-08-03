import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from services.bangladesh_delivery_turnover import (
    get_bangladesh_delivery_turnover,
)


# =========================================================
# EXCEL FILE
# =========================================================

def create_bangladesh_turnover_excel(
    report_df: pd.DataFrame,
) -> bytes:

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

        worksheet = writer.sheets["Bangladesh Turnover"]

        worksheet.freeze_panes = "D2"
        worksheet.auto_filter.ref = worksheet.dimensions

        # Header formatting
        for cell in worksheet[1]:
            cell.font = cell.font.copy(bold=True)

        # Number formatting
        for row in worksheet.iter_rows(
            min_row=2,
            min_col=4,
            max_col=worksheet.max_column,
        ):
            for cell in row:
                cell.number_format = "0.00"

        # Automatic column width
        for column_cells in worksheet.columns:
            column_letter = column_cells[0].column_letter

            max_length = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells
            )

            worksheet.column_dimensions[column_letter].width = min(
                max_length + 3,
                35,
            )

    output.seek(0)
    return output.getvalue()


# =========================================================
# REPORT TOTAL ROW
# =========================================================

def add_total_row(dataframe: pd.DataFrame) -> pd.DataFrame:

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
        total_row["ZONENAME"] = "GRAND TOTAL"

    for column in numeric_columns:
        total_row[column] = report_df[column].sum()

    return pd.concat(
        [
            report_df,
            pd.DataFrame([total_row]),
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
            background:linear-gradient(180deg,#ffffff,#faf8ff);
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
                Branch-wise Non-FTL and FTL delivery turnover report
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------
    # DEFAULT DATES
    # -----------------------------------------------------

    today = date.today()

    current_month_start = today.replace(day=1)

    previous_month_end = (
        current_month_start - timedelta(days=1)
    )

    previous_month_start = (
        previous_month_end.replace(day=1)
    )

    period1_end = (
        previous_month_start - timedelta(days=1)
    )

    period1_start = (
        period1_end.replace(day=1)
        - timedelta(days=62)
    ).replace(day=1)

    # -----------------------------------------------------
    # DATE FILTERS
    # -----------------------------------------------------

    with st.container(border=True):

        st.markdown(
            "<div style='font-size:15px;font-weight:700;"
            "color:#35256f;margin-bottom:8px;'>"
            "Select Report Periods"
            "</div>",
            unsafe_allow_html=True,
        )

        period1_col, period2_col, period3_col = st.columns(
            3,
            gap="medium",
        )

        with period1_col:

            st.markdown("**Period 1**")

            date1_from = st.date_input(
                "From Date",
                value=period1_start,
                format="DD-MM-YYYY",
                key="bd_turnover_date1_from",
            )

            date1_to = st.date_input(
                "To Date",
                value=period1_end,
                format="DD-MM-YYYY",
                key="bd_turnover_date1_to",
            )

        with period2_col:

            st.markdown("**Period 2**")

            date2_from = st.date_input(
                "From Date",
                value=previous_month_start,
                format="DD-MM-YYYY",
                key="bd_turnover_date2_from",
            )

            date2_to = st.date_input(
                "To Date",
                value=previous_month_end,
                format="DD-MM-YYYY",
                key="bd_turnover_date2_to",
            )

        with period3_col:

            st.markdown("**Period 3**")

            date3_from = st.date_input(
                "From Date",
                value=current_month_start,
                format="DD-MM-YYYY",
                key="bd_turnover_date3_from",
            )

            date3_to = st.date_input(
                "To Date",
                value=today,
                format="DD-MM-YYYY",
                key="bd_turnover_date3_to",
            )

        generate_report = st.button(
            "Generate Report",
            type="primary",
            width="stretch",
            key="generate_bangladesh_turnover",
        )

    if not generate_report:
        return

    # -----------------------------------------------------
    # DATE VALIDATION
    # -----------------------------------------------------

    date_ranges = [
        ("Period 1", date1_from, date1_to),
        ("Period 2", date2_from, date2_to),
        ("Period 3", date3_from, date3_to),
    ]

    for period_name, from_date, to_date in date_ranges:

        if from_date > to_date:
            st.error(
                f"{period_name}: From Date cannot be after To Date."
            )
            return

    # -----------------------------------------------------
    # LOAD DATA
    # -----------------------------------------------------

    try:

        with st.spinner(
            "Loading Bangladesh delivery turnover report..."
        ):

            columns, rows = get_bangladesh_delivery_turnover(
                date1_from.strftime("%d-%m-%Y"),
                date1_to.strftime("%d-%m-%Y"),
                date2_from.strftime("%d-%m-%Y"),
                date2_to.strftime("%d-%m-%Y"),
                date3_from.strftime("%d-%m-%Y"),
                date3_to.strftime("%d-%m-%Y"),
            )

    except Exception as error:

        st.error("Unable to generate the report.")
        st.exception(error)
        return

    if not columns or not rows:

        st.warning(
            "No Bangladesh delivery turnover data was found "
            "for the selected periods."
        )
        return

    dataframe = pd.DataFrame(
        rows,
        columns=columns,
    )

    # -----------------------------------------------------
    # CLEAN DATA
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
            )

    for column in numeric_columns:

        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).fillna(0.0).round(2)

    report_dataframe = add_total_row(dataframe)

    # -----------------------------------------------------
    # COLUMN CONFIGURATION
    # -----------------------------------------------------

    column_configuration = {}

    if "ZONENAME" in report_dataframe.columns:

        column_configuration["ZONENAME"] = (
            st.column_config.TextColumn(
                "Zone",
                width="medium",
            )
        )

    if "HUBNAME" in report_dataframe.columns:

        column_configuration["HUBNAME"] = (
            st.column_config.TextColumn(
                "Hub",
                width="medium",
            )
        )

    if "BRANCH" in report_dataframe.columns:

        column_configuration["BRANCH"] = (
            st.column_config.TextColumn(
                "Branch",
                width="large",
            )
        )

    for column in numeric_columns:

        column_configuration[column] = (
            st.column_config.NumberColumn(
                column,
                format="%.2f",
                width="small",
            )
        )

    # -----------------------------------------------------
    # REPORT TABLE
    # -----------------------------------------------------

    st.markdown(
        "<div style='font-size:17px;font-weight:700;"
        "color:#251b4f;margin:15px 0 8px;'>"
        "Bangladesh Delivery Turnover Report"
        "</div>",
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
        "Turnover values are displayed in ₹ lakh."
    )

    # -----------------------------------------------------
    # DOWNLOAD BUTTONS
    # -----------------------------------------------------

    excel_data = create_bangladesh_turnover_excel(
        report_dataframe
    )

    csv_data = report_dataframe.to_csv(
        index=False,
    ).encode("utf-8-sig")

    download_excel_col, download_csv_col = st.columns(2)

    with download_excel_col:

        st.download_button(
            "Download Excel",
            data=excel_data,
            file_name=(
                "bangladesh_delivery_turnover_"
                f"{date1_from:%Y%m%d}_"
                f"{date3_to:%Y%m%d}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            width="stretch",
            key="download_bangladesh_turnover_excel",
        )

    with download_csv_col:

        st.download_button(
            "Download CSV",
            data=csv_data,
            file_name=(
                "bangladesh_delivery_turnover_"
                f"{date1_from:%Y%m%d}_"
                f"{date3_to:%Y%m%d}.csv"
            ),
            mime="text/csv",
            width="stretch",
            key="download_bangladesh_turnover_csv",
        )


# =========================================================
# MENU ALIAS
# =========================================================

def show_bangladesh_turnover():
    show_bangladesh_delivery_turnover()


# =========================================================
# DIRECT RUN
# =========================================================

if __name__ == "__main__":

    st.set_page_config(
        page_title="Bangladesh Delivery Turnover",
        page_icon="📄",
        layout="wide",
    )

    show_bangladesh_delivery_turnover()