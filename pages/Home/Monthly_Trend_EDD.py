import os
from io import BytesIO
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

LIVE_DATA_START = pd.Timestamp("2026-04-01")

BASELINE_Q1 = pd.DataFrame([
    {"Month": "Jan 2026", "Total CN": 10688, "On-Time CN": 3548, "OTD %": 33.2, "Breached CN": 5679, "Breach %": 53.1, "Avg Delay (days)": 3.0, "Charged Wt (MT)": 7118, "TAT Mapped %": 85.0},
    {"Month": "Feb 2026", "Total CN": 9962, "On-Time CN": 2997, "OTD %": 30.1, "Breached CN": 5420, "Breach %": 54.4, "Avg Delay (days)": 3.6, "Charged Wt (MT)": 7118, "TAT Mapped %": 83.0},
    {"Month": "Mar 2026", "Total CN": 4134, "On-Time CN": 1367, "OTD %": 33.1, "Breached CN": 1992, "Breach %": 48.2, "Avg Delay (days)": 2.1, "Charged Wt (MT)": 3179, "TAT Mapped %": 80.0},
])

Q1_GOAL = {"Month": "Q1 Goal", "Total CN": "", "On-Time CN": "", "OTD %": 41.8, "Breached CN": "", "Breach %": 20.0, "Avg Delay (days)": 1.5, "Charged Wt (MT)": "", "TAT Mapped %": ""}

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
    END AS [FINAL ARRIVAL DT]
FROM CNMT D WITH (NOLOCK)
INNER JOIN VIEWSTATIONMAST ORG ON ORG.STNCODE = D.ORGCODE
INNER JOIN VIEWSTATIONMAST DEST ON DEST.STNCODE = D.DESTCODE
LEFT JOIN (
    SELECT GRNO, BRANCHCODE, ARRIVALDT, VEHICLE_ARRIVAL_DT
    FROM (
        SELECT GRNO, BRANCHCODE, ARRIVALDT, VEHICLE_ARRIVAL_DT,
               ROW_NUMBER() OVER (
                   PARTITION BY GRNO
                   ORDER BY VEHICLE_ARRIVAL_DT DESC, ARRIVALDT DESC
               ) AS RN
        FROM VW_GRARRIVALDETAILS
    ) A
    WHERE RN = 1
) ARR ON D.GRNO = ARR.GRNO
LEFT JOIN (
    SELECT *
    FROM (
        SELECT *,
               ROW_NUMBER() OVER (
                   PARTITION BY GRNO
                   ORDER BY DRDT DESC
               ) AS RN
        FROM VIEWALLCOMPANIESGATEPASS
        WHERE COMPANYID IN ('26498132','26498133','26498134','26498135')
          AND CANCEL <> 'Y'
    ) G
    WHERE RN = 1
) GP ON D.GRNO = GP.GRNO
WHERE D.FTL = 'N'
AND ORG.HUBNAME IN (
    'DELHI-NCR','GUJARAT','GUJARAT - ADI','GUJARAT - BRD','GUJARAT - VAPI',
    'JHARKHAND CIRCLE','MAHARASHTRA','MAHARASHTRA - MUM','NCR AGENCIES',
    'NCR OFFICE','PATNA CIRCLE','PUNJAB CIRCLE','REST OF GUJARAT CIRCLE',
    'REST OF MAHARASHTRA CIRCLE','SILIGURI-HUB','WEST BENGAL',
    'WEST BENGAL - KOL','WEST BENGAL - SLG','ASSAM - NE'
)
AND DEST.HUBNAME IN (
    'INDO BORDER CIRCLE','NEPAL CIRCLE','WEST BENGAL','WEST BENGAL - KOL',
    'WEST BENGAL - SLG','SILIGURI-HUB','ASSAM - NE','JHARKHAND CIRCLE'
)
AND D.GRTYPE <> 'N'
AND D.GRDT >= :from_date
AND D.GRDT < DATEADD(DAY, 1, :to_date)
""")


def _secret_value(*names: str, default: str = "") -> str:
    """Read existing project credentials from Streamlit secrets or environment variables."""
    for name in names:
        try:
            if name in st.secrets and st.secrets[name] not in (None, ""):
                return str(st.secrets[name])
        except Exception:
            pass

        value = os.getenv(name)
        if value not in (None, ""):
            return str(value)

    # Also support nested [database] / [sql] sections in secrets.toml.
    for section_name in ("database", "sql", "mssql", "db"):
        try:
            section = st.secrets.get(section_name, {})
            for name in names:
                if name in section and section[name] not in (None, ""):
                    return str(section[name])
        except Exception:
            pass

    return default


@st.cache_resource(show_spinner=False)
def get_engine():
    """Create a SQLAlchemy engine using pymssql already installed in the project."""
    server = _secret_value("DB_SERVER", "SERVER", "SQL_SERVER", "host")
    database = _secret_value("DB_DATABASE", "DATABASE", "SQL_DATABASE", "database")
    username = _secret_value("DB_USERNAME", "DB_USER", "UID", "USERNAME", "user")
    password = _secret_value("DB_PASSWORD", "PWD", "PASSWORD", "password")
    port_text = _secret_value("DB_PORT", "PORT", "SQL_PORT", "port", default="1433")

    if not all([server, database, username, password]):
        raise ValueError(
            "Existing SQL credentials were not found. Expected DB_SERVER, "
            "DB_DATABASE, DB_USERNAME and DB_PASSWORD in Streamlit secrets "
            "or environment variables."
        )

    # Supports values such as server,1433 or server:1433.
    port = int(port_text or 1433)
    if "," in server:
        server, embedded_port = server.rsplit(",", 1)
        if embedded_port.isdigit():
            port = int(embedded_port)
    elif server.count(":") == 1:
        host_part, embedded_port = server.rsplit(":", 1)
        if embedded_port.isdigit():
            server = host_part
            port = int(embedded_port)

    connection_url = URL.create(
        drivername="mssql+pymssql",
        username=username,
        password=password,
        host=server,
        port=port,
        database=database,
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True,
        pool_recycle=1800,
    )


@st.cache_data(ttl=900, show_spinner=False)
def load_sql_data(from_date: date, to_date: date) -> pd.DataFrame:
    with get_engine().connect() as connection:
        return pd.read_sql_query(SQL_QUERY, connection, params={"from_date": from_date, "to_date": to_date})


def prepare_detail_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    out = df.copy()
    out["GRDT"] = pd.to_datetime(out["GRDT"], errors="coerce")
    out["E.D.D"] = pd.to_datetime(out["E.D.D"], errors="coerce")
    out["FINAL ARRIVAL DT"] = pd.to_datetime(out["FINAL ARRIVAL DT"], errors="coerce")
    out["CWEIGHT"] = pd.to_numeric(out["CWEIGHT"], errors="coerce").fillna(0)
    out["MONTH_START"] = out["GRDT"].dt.to_period("M").dt.to_timestamp()
    out["TAT_MAPPED"] = out["E.D.D"].notna() & out["FINAL ARRIVAL DT"].notna()
    out["ON_TIME"] = out["TAT_MAPPED"] & (out["FINAL ARRIVAL DT"] <= out["E.D.D"])
    out["BREACHED"] = out["TAT_MAPPED"] & (out["FINAL ARRIVAL DT"] > out["E.D.D"])
    delay = (out["FINAL ARRIVAL DT"].dt.normalize() - out["E.D.D"].dt.normalize()).dt.days
    out["DELAY_DAYS"] = np.where(out["BREACHED"], delay, np.nan)
    return out


def calculate_monthly_summary(detail: pd.DataFrame) -> pd.DataFrame:
    columns = ["Month", "Total CN", "On-Time CN", "OTD %", "Breached CN", "Breach %", "Avg Delay (days)", "Charged Wt (MT)", "TAT Mapped %"]
    if detail.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for month_start, group in detail.groupby("MONTH_START", dropna=True):
        total_cn = group["GRNO"].nunique()
        on_time_cn = group.loc[group["ON_TIME"], "GRNO"].nunique()
        breached_cn = group.loc[group["BREACHED"], "GRNO"].nunique()
        mapped_cn = group.loc[group["TAT_MAPPED"], "GRNO"].nunique()
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


def combine_baseline_and_live(live_summary: pd.DataFrame) -> pd.DataFrame:
    live = live_summary.copy()
    if not live.empty:
        live_dates = pd.to_datetime(live["Month"], format="%b %Y", errors="coerce")
        live = live.loc[live_dates >= LIVE_DATA_START]
    combined = pd.concat([BASELINE_Q1, live], ignore_index=True)
    combined["_sort"] = pd.to_datetime(combined["Month"], format="%b %Y", errors="coerce")
    return combined.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)


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


def dataframe_to_excel(summary: pd.DataFrame, detail: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="Monthly Summary")
        detail.to_excel(writer, index=False, sheet_name="Raw Data")
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
        month_date = pd.to_datetime(row["Month"], format="%b %Y", errors="coerce")
        tr_class = "live-row" if pd.notna(month_date) and month_date >= LIVE_DATA_START else "baseline-row"
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

    goal_cells = []
    for col in shown.columns:
        value = Q1_GOAL.get(col, "")
        if col in ("OTD %", "Breach %"): value = fmt_percent(value)
        elif col == "Avg Delay (days)": value = fmt_delay(value)
        css = "goal-label" if col == "Month" else ""
        if col in ("OTD %", "Breach %", "Avg Delay (days)"): css += " goal-value"
        goal_cells.append(f'<td class="{css.strip()}">{value}</td>')

    return f'<div class="table-wrap"><table class="edd-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows)}<tr class="spacer-row"><td colspan="9"></td></tr><tr class="goal-row">{"".join(goal_cells)}</tr></tbody></table></div>'




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
    .edd-table .spacer-row td{height:18px;padding:0;background:#fff;border-left:none;border-right:none}.edd-table .goal-row td{background:#f0f3f8;color:#d92772;font-weight:800}
    .edd-table .goal-row .goal-label{background:#f52c7b;color:white}.edd-table .goal-row .goal-value{background:#ffc4de}
    #MainMenu,footer{visibility:hidden}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="title-panel"><h1>Monthly Trend EDD · Where we were and where we are</h1></div>
    <div class="subtitle-panel">Q4 FY26 (Jan–Mar 2026) baseline hardcoded. Apr 2026 onwards = live from current data. Q1 Goal at bottom.</div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Report Filters")
        from_date = st.date_input("Live data from", value=date(2026, 4, 1), min_value=date(2026, 4, 1))
        to_date = st.date_input("Live data to", value=date.today(), min_value=date(2026, 4, 1))
        include_baseline = st.checkbox("Include Jan-Mar baseline", value=True)
        st.button("Refresh Report", type="primary", use_container_width=True)
        st.caption("Uses the SQL credentials already configured in this dashboard.")

    if from_date > to_date:
        st.error("The From date cannot be later than the To date.")
        st.stop()

    try:
        with st.spinner("Loading EDD data from SQL Server..."):
            raw_df = load_sql_data(from_date, to_date)
        detail_df = prepare_detail_data(raw_df)
        live_summary = calculate_monthly_summary(detail_df)
        final_summary = combine_baseline_and_live(live_summary) if include_baseline else live_summary

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
                data=dataframe_to_excel(final_summary, detail_df),
                file_name=f"Monthly_Trend_EDD_{from_date:%Y%m%d}_{to_date:%Y%m%d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            with st.expander("View consignment-level data"):
                st.dataframe(detail_df, use_container_width=True, hide_index=True)

            with st.expander("Metric definitions used"):
                st.markdown("""
    - **Total CN:** Distinct GRNO.
    - **On-Time CN:** Final Arrival DT is on or before E.D.D.
    - **OTD %:** On-Time CN / Total CN.
    - **Breached CN:** Final Arrival DT is after E.D.D.
    - **Breach %:** Breached CN / Total CN.
    - **Avg Delay:** Average positive delay among breached consignments.
    - **Charged Wt (MT):** Maximum CWEIGHT per GRNO, summed and divided by 1,000.
    - **TAT Mapped %:** GRNO with both E.D.D and Final Arrival DT / Total CN.
    """)
    except Exception as exc:
        st.error("The report could not be loaded.")
        st.exception(exc)
        st.info("Check the existing SQL credentials, database permissions, and database object names.")
