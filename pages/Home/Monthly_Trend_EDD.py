from io import BytesIO
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine

SQL_QUERY = text(r"""
SELECT
    '_' + CAST(YEAR(D.GRDT) AS VARCHAR) + '_' +
    RIGHT('0' + CAST(MONTH(D.GRDT) AS VARCHAR), 2) + '_' +
    DATENAME(MONTH, D.GRDT) + '_' AS [SALE MONTH],
    ORG.STNNAME AS ORIGIN,
    D.GRDT,
    RIGHT('0' + CAST(DAY(D.GRDT) AS VARCHAR), 2) + '-' +
    UPPER(LEFT(DATENAME(MONTH, D.GRDT), 3)) + '-' +
    CAST(YEAR(D.GRDT) AS VARCHAR) AS GR_DT,
    D.GRNO,
    DEST.STNNAME AS DESTINATION,
    D.CNGR,
    D.CNGE,
    D.AWEIGHT,
    D.CWEIGHT,
    ORG.HUBNAME AS [BOOKING CIRCLE],
    ORG.ZONENAME AS [BOOKING ZONE],
    DEST.HUBNAME AS [DESTINATION CIRCLE],
    DEST.ZONENAME AS [DESTINATION ZONE],
    DEST.COUNTRY AS DESTCOUNTRY,
    D.EXPECTEDDELIVERYDT AS [E.D.D],
    CASE
        WHEN D.DESTCODE = ARR.BRANCHCODE THEN ARR.VEHICLE_ARRIVAL_DT
        WHEN GP.DRNO IS NOT NULL THEN ARR.VEHICLE_ARRIVAL_DT
    END AS [FINAL ARRIVAL DT],
    DATEADD(HOUR, TAT.SDHOUR, D.GRDT) AS [TAT_E.D.D]
FROM CNMT D WITH (NOLOCK)
INNER JOIN VIEWSTATIONMAST ORG
    ON ORG.STNCODE = D.ORGCODE
INNER JOIN VIEWSTATIONMAST DEST
    ON DEST.STNCODE = D.DESTCODE
LEFT JOIN (
    SELECT GRNO, BRANCHCODE, ARRIVALDT, VEHICLE_ARRIVAL_DT
    FROM (
        SELECT
            GRNO,
            BRANCHCODE,
            ARRIVALDT,
            VEHICLE_ARRIVAL_DT,
            ROW_NUMBER() OVER (
                PARTITION BY GRNO
                ORDER BY VEHICLE_ARRIVAL_DT DESC, ARRIVALDT DESC
            ) AS RN
        FROM VW_GRARRIVALDETAILS
    ) A
    WHERE RN = 1
) ARR
    ON D.GRNO = ARR.GRNO
LEFT JOIN (
    SELECT *
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY GRNO
                ORDER BY DRDT DESC
            ) AS RN
        FROM VIEWALLCOMPANIESGATEPASS
        WHERE COMPANYID IN ('26498132', '26498133', '26498134', '26498135')
          AND CANCEL <> 'Y'
    ) G
    WHERE RN = 1
) GP
    ON D.GRNO = GP.GRNO
LEFT JOIN (
    SELECT ORGCODE, DESTCODE, SDHOUR
    FROM (
        SELECT
            ORGCODE,
            DESTCODE,
            SDHOUR,
            ROW_NUMBER() OVER (
                PARTITION BY ORGCODE, DESTCODE
                ORDER BY SDHOUR DESC
            ) AS RN
        FROM TATMAST
        WHERE TATTYPE = 'D'
    ) X
    WHERE RN = 1
) TAT
    ON TAT.ORGCODE = D.ORGCODE
   AND TAT.DESTCODE = D.DESTCODE
WHERE D.FTL = 'N'
  AND D.GRTYPE <> 'N'
  AND D.GRDT >= :from_date
  AND D.GRDT < DATEADD(DAY, 1, :to_date)
""")


# Increment this value whenever the SQL source or returned columns change.
# It is part of the Streamlit cache key and prevents an old query result from
# being reused after deployment.
EDD_DATA_CACHE_VERSION = "8.6.1"



@st.cache_data(ttl=900, show_spinner=False)
def load_sql_data(
    from_date: date,
    to_date: date,
    cache_version: str = EDD_DATA_CACHE_VERSION,
) -> pd.DataFrame:
    # cache_version is intentionally unused by SQL. It only invalidates stale
    # Streamlit cache entries when this page's data source changes.
    del cache_version

    with get_engine().connect() as connection:
        return pd.read_sql_query(
            SQL_QUERY,
            connection,
            params={"from_date": from_date, "to_date": to_date},
        )


def _normalise_column_name(value: str) -> str:
    """Normalise SQL column labels so spaces, dots and underscores do not matter."""
    return "".join(character for character in str(value).strip().casefold() if character.isalnum())


def _resolve_column(df: pd.DataFrame, *candidates: str) -> str:
    """Return the actual DataFrame column matching one of the requested labels."""
    actual_by_normalised = {
        _normalise_column_name(column): column
        for column in df.columns
    }

    for candidate in candidates:
        actual = actual_by_normalised.get(_normalise_column_name(candidate))
        if actual is not None:
            return actual

    raise KeyError(
        f"Required column not returned by SQL function. Expected one of {candidates}. "
        f"Available columns: {list(df.columns)}"
    )


def prepare_detail_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out.columns = [str(column).strip() for column in out.columns]

    grdt_col = _resolve_column(out, "GRDT", "GR DT")
    edd_col = _resolve_column(out, "E.D.D", "EDD")
    tat_edd_col = _resolve_column(
        out,
        "TAT_E.D.D",
        "TAT E.D.D",
        "TAT_EDD",
        "TAT EDD",
    )
    final_arrival_col = _resolve_column(
        out,
        "FINAL ARRIVAL DT",
        "Final Arrival Dt",
        "finalarrival",
    )
    cweight_col = _resolve_column(out, "CWEIGHT", "C WEIGHT", "CHARGED WEIGHT")

    # Keep stable canonical names for all downstream calculations and exports.
    out["GRDT"] = pd.to_datetime(out[grdt_col], errors="coerce")
    out["E.D.D"] = pd.to_datetime(out[edd_col], errors="coerce")
    out["TAT_E.D.D"] = pd.to_datetime(out[tat_edd_col], errors="coerce")
    out["FINAL ARRIVAL DT"] = pd.to_datetime(out[final_arrival_col], errors="coerce")
    out["CWEIGHT"] = pd.to_numeric(out[cweight_col], errors="coerce").fillna(0)

    out["MONTH_START"] = out["GRDT"].dt.to_period("M").dt.to_timestamp()
    out["TAT_MAPPED"] = out["TAT_E.D.D"].notna()
    out["ON_TIME"] = out["TAT_MAPPED"] & (out["FINAL ARRIVAL DT"] <= out["E.D.D"])
    out["BREACHED"] = out["TAT_MAPPED"] & (out["FINAL ARRIVAL DT"] > out["E.D.D"])

    delay = (
        out["FINAL ARRIVAL DT"].dt.normalize()
        - out["E.D.D"].dt.normalize()
    ).dt.days
    out["DELAY_DAYS"] = np.where(out["BREACHED"], delay, np.nan)
    return out


def calculate_monthly_summary(detail: pd.DataFrame) -> pd.DataFrame:
    columns = ["Month", "Total CN", "On-Time CN", "OTD %", "Breached CN", "Breach %", "Avg Delay (days)", "Charged Wt (MT)", "TAT Mapped %"]
    if detail.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for month_start, group in detail.groupby("MONTH_START", dropna=True):
        # The SQL function already returns one distinct row per GRNO.
        # Therefore, row counts are the consignment counts.
        total_cn = len(group)
        on_time_cn = int(group["ON_TIME"].sum())
        breached_cn = int(group["BREACHED"].sum())
        mapped_cn = int(group["TAT_MAPPED"].sum())
        avg_delay = group.loc[group["BREACHED"], "DELAY_DAYS"].mean()
        charged_weight_mt = group.groupby("GRNO")["CWEIGHT"].max().sum() / 1000

        rows.append({
            "MONTH_START": month_start,
            "Month": month_start.strftime("%b %Y"),
            "Total CN": int(total_cn),
            "On-Time CN": int(on_time_cn),
            "OTD %": round(on_time_cn / total_cn * 100, 1) if total_cn else 0.0,
            "Breached CN": int(breached_cn),
            "Breach %": round(breached_cn / total_cn * 100, 1) if total_cn else 0.0,
            "Avg Delay (days)": round(float(avg_delay), 1) if pd.notna(avg_delay) else 0.0,
            "Charged Wt (MT)": round(float(charged_weight_mt)),
            "TAT Mapped %": round(mapped_cn / total_cn * 100, 1) if total_cn else 0.0,
        })

    return pd.DataFrame(rows).sort_values("MONTH_START").drop(columns="MONTH_START")[columns]



def calculate_unmapped_branch_summary(detail: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Booking Zone",
        "Booking Circle",
        "Origin Branch",
        "Total CN",
        "TAT Not Mapped CN",
        "TAT Not Mapped %",
    ]

    if detail.empty:
        return pd.DataFrame(columns=columns)

    required = ["BOOKING ZONE", "BOOKING CIRCLE", "ORIGIN", "TAT_MAPPED"]
    missing = [column for column in required if column not in detail.columns]
    if missing:
        raise KeyError(
            "Branch-wise TAT mapping view cannot be prepared because these columns "
            f"are missing: {missing}"
        )

    rows = []
    grouped = detail.groupby(
        ["BOOKING ZONE", "BOOKING CIRCLE", "ORIGIN"],
        dropna=False,
    )

    for (zone, circle, origin), group in grouped:
        total_cn = len(group)
        unmapped_cn = int((~group["TAT_MAPPED"]).sum())

        if unmapped_cn == 0:
            continue

        rows.append({
            "Booking Zone": "" if pd.isna(zone) else str(zone),
            "Booking Circle": "" if pd.isna(circle) else str(circle),
            "Origin Branch": "" if pd.isna(origin) else str(origin),
            "Total CN": int(total_cn),
            "TAT Not Mapped CN": unmapped_cn,
            "TAT Not Mapped %": round(unmapped_cn / total_cn * 100, 1) if total_cn else 0.0,
        })

    if not rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["TAT Not Mapped CN", "TAT Not Mapped %", "Origin Branch"],
            ascending=[False, False, True],
        )
        .reset_index(drop=True)[columns]
    )


def fmt_integer(value):
    return "" if value == "" or pd.isna(value) else f"{int(round(float(value))):,}"


def fmt_percent(value):
    return "" if value == "" or pd.isna(value) else f"{float(value):.1f}%"


def fmt_delay(value):
    if value == "" or pd.isna(value):
        return ""
    value = float(value)
    return f"+{value:.1f}" if value > 0 else f"{value:.1f}"


def display_frame(summary: pd.DataFrame) -> pd.DataFrame:
    out = summary.copy()
    for col in ["Total CN", "On-Time CN", "Breached CN", "Charged Wt (MT)"]:
        out[col] = out[col].map(fmt_integer)
    for col in ["OTD %", "Breach %", "TAT Mapped %"]:
        out[col] = out[col].map(fmt_percent)
    out["Avg Delay (days)"] = out["Avg Delay (days)"].map(fmt_delay)
    return out


def dataframe_to_excel(summary: pd.DataFrame, detail: pd.DataFrame, unmapped_branches: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="Monthly Summary")
        detail.to_excel(writer, index=False, sheet_name="Raw Data")
        unmapped_branches.to_excel(writer, index=False, sheet_name="TAT Not Mapped Branches")
        for ws in writer.sheets.values():
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for cells in ws.columns:
                width = min(max(max(len(str(c.value)) if c.value is not None else 0 for c in cells) + 2, 10), 35)
                ws.column_dimensions[cells[0].column_letter].width = width
    return output.getvalue()


def build_html_table(summary: pd.DataFrame) -> str:
    shown = display_frame(summary)
    headers = "".join(f"<th>{col}</th>" for col in shown.columns)
    rows = []
    for _, row in shown.iterrows():
        tr_class = "live-row"
        cells = []
        for col in shown.columns:
            css = ""
            if col == "Month": css = "month-cell"
            elif col in ("On-Time CN", "OTD %"): css = "good-cell"
            elif col in ("Breached CN", "Breach %"): css = "bad-cell"
            elif col == "Avg Delay (days)": css = "delay-cell"
            elif col == "TAT Mapped %": css = "mapped-cell"
            cells.append(f'<td class="{css}">{row[col]}</td>')
        rows.append(f'<tr class="{tr_class}">{"".join(cells)}</tr>')

    return f'<div class="table-wrap"><table class="edd-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'




def show_monthly_trend_edd():
    st.markdown("""
    <style>
    .stApp {background:#fff}.main .block-container{padding-top:.7rem;max-width:1600px}
    .title-panel{background:#071629;border-top:5px solid #2f69d8;border-bottom:2px solid #2f69d8;padding:12px 10px 10px}
    .title-panel h1{color:white;margin:0;font-size:28px;font-weight:800}
    .subtitle-panel{background:#071629;color:#7891ba;font-style:italic;padding:8px 10px 10px;margin-bottom:20px;font-size:15px}
    .table-wrap{overflow-x:auto;border-left:1px solid #c7d0dd;border-right:1px solid #c7d0dd}
    table.edd-table{width:100%;border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px;text-align:center}
    .edd-table th{background:#071629;color:#00d9ff;padding:12px 8px;border:1px solid #c9d1dc;font-weight:800}
    .edd-table td{padding:10px 8px;border:1px solid #c9d1dc;background:#f7f9fc;font-weight:600;white-space:nowrap}
    .edd-table .month-cell{background:#f1f5fa;color:#24344d;font-weight:800}.edd-table .live-row .month-cell{background:#a9e9f6;color:#00799c}
    .edd-table .good-cell{background:#d0f2e6;color:#008b4c;font-weight:800}.edd-table .bad-cell{background:#ffc9cf;color:#cf202b;font-weight:800}
    .edd-table .delay-cell{background:#ffedbc;color:#c88200;font-weight:800}.edd-table .mapped-cell{background:#a9e9f6;color:#047eaa}
        #MainMenu,footer{visibility:hidden}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="title-panel"><h1>Monthly Trend EDD · Where we were and where we are</h1></div>
    <div class="subtitle-panel">Select any From Date and To Date to view the monthly EDD trend from live SQL data.</div>
    """, unsafe_allow_html=True)

    today = date.today()
    default_from = today.replace(day=1)

    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 0.7])
    with filter_col1:
        from_date = st.date_input(
            "From Date",
            value=default_from,
            key="monthly_trend_edd_from_date",
        )
    with filter_col2:
        to_date = st.date_input(
            "To Date",
            value=today,
            key="monthly_trend_edd_to_date",
        )
    with filter_col3:
        st.write("")
        st.write("")
        run_report = st.button(
            "Run Report",
            type="primary",
            use_container_width=True,
            key="monthly_trend_edd_run",
        )

    # Do not query SQL until the user explicitly presses Run Report.
    if not run_report:
        st.info("Select the From Date and To Date, then click **Run Report**.")
        return

    if from_date > to_date:
        st.error("The From date cannot be later than the To date.")
        return

    try:
        # A fresh query is executed only when Run Report is pressed.
        load_sql_data.clear()

        with st.spinner("Loading EDD data from SQL Server..."):
            raw_df = load_sql_data(from_date, to_date)

        detail_df = prepare_detail_data(raw_df)
        final_summary = calculate_monthly_summary(detail_df)
        unmapped_branch_summary = calculate_unmapped_branch_summary(detail_df)

        if final_summary.empty:
            st.warning("No records were found for the selected date range.")
        else:
            latest = final_summary.iloc[-1]
            cols = st.columns(5)
            cols[0].metric("Latest Month", latest["Month"])
            cols[1].metric("Total CN", fmt_integer(latest["Total CN"]))
            cols[2].metric("OTD", fmt_percent(latest["OTD %"]))
            cols[3].metric("Breach", fmt_percent(latest["Breach %"]))
            cols[4].metric("TAT Mapped", fmt_percent(latest["TAT Mapped %"]))

            st.markdown(build_html_table(final_summary), unsafe_allow_html=True)
            st.download_button(
                "Download Excel",
                data=dataframe_to_excel(final_summary, detail_df, unmapped_branch_summary),
                file_name=f"Monthly_Trend_EDD_{from_date:%Y%m%d}_{to_date:%Y%m%d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            st.subheader("Branches Where TAT E.D.D Is Not Mapped")
            if unmapped_branch_summary.empty:
                st.success("TAT E.D.D is mapped for all branches in the selected period.")
            else:
                unmapped_display = unmapped_branch_summary.copy()
                unmapped_display["Total CN"] = unmapped_display["Total CN"].map(fmt_integer)
                unmapped_display["TAT Not Mapped CN"] = unmapped_display["TAT Not Mapped CN"].map(fmt_integer)
                unmapped_display["TAT Not Mapped %"] = unmapped_display["TAT Not Mapped %"].map(fmt_percent)
                st.dataframe(
                    unmapped_display,
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "Download TAT Not Mapped Branches",
                    data=unmapped_branch_summary.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"TAT_Not_Mapped_Branches_{from_date:%Y%m%d}_{to_date:%Y%m%d}.csv",
                    mime="text/csv",
                    key="download_tat_unmapped_branches",
                )

            with st.expander("View consignment-level data"):
                st.dataframe(detail_df, use_container_width=True, hide_index=True)

            with st.expander("Metric definitions used"):
                st.markdown("""
    - **Total CN:** Total rows returned by the SQL function (one row per distinct GRNO).
    - **On-Time CN:** Final Arrival DT is on or before E.D.D.
    - **OTD %:** On-Time CN / Total CN.
    - **Breached CN:** Final Arrival DT is after E.D.D.
    - **Breach %:** Breached CN / Total CN.
    - **Avg Delay:** Average positive delay among breached consignments.
    - **Charged Wt (MT):** Maximum CWEIGHT per GRNO, summed and divided by 1,000.
    - **TAT Mapped %:** Rows where TAT_E.D.D is available / Total CN.
    - **TAT Not Mapped Branches:** Origin branches having at least one row where TAT_E.D.D is blank.
    """)
    except Exception as exc:
        st.error("The report could not be loaded.")
        st.exception(exc)
        st.info("Check the existing SQL credentials, database permissions, and database object names.")
