import io
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.pnl_data_loader import load_pnl_data_pair
from services.data_loader import get_date_range

# =====================================================
# Constants
# =====================================================
MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
MONTH_MAP = {1: "Apr", 2: "May", 3: "Jun", 4: "Jul", 5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov", 9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"}
QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]
QUARTER_MAP = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2", 7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"}
FY_OPTIONS = [
    "Select FY", "2026-2027", "2025-2026", "2024-2025",
    "2023-2024", "2022-2023", "2021-2022", "2020-2021",
]
TOP_N_OPTIONS = [10, 20, 30, 40]


# =====================================================
# Styling
# =====================================================
def _inject_pnl_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 100% !important;
            padding: .35rem .75rem .90rem !important;
        }
        div[data-testid="stVerticalBlock"] { gap: .38rem !important; }
        div[data-testid="stHorizontalBlock"] { gap: .50rem !important; align-items: flex-start !important; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] { min-width: 0 !important; }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #dce5ef !important;
            border-radius: 14px !important;
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%) !important;
            box-shadow: 0 7px 18px rgba(15,42,67,.075), inset 0 1px 0 #ffffff !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: .58rem .68rem !important; }

        .pnl-title { color:#102a43; font-size:19px; font-weight:850; letter-spacing:-.25px; margin:0; }
        .pnl-subtitle { color:#64748b; font-size:11px; margin-top:2px; }
        .section-title { font-size:14px; font-weight:700; color:#0f2744; margin:1px 0 6px 1px; }

        .filter-summary { display:flex; flex-wrap:wrap; gap:7px; min-height:30px; align-items:center; }
        .filter-chip {
            display:inline-flex; align-items:center; min-height:27px; padding:5px 12px;
            border:1px solid #b8d1f2; border-radius:999px; background:#f5f9ff;
            color:#31557d; font-size:10.5px; font-weight:600; white-space:nowrap;
        }

        div[data-testid="stSelectbox"] { display:flex !important; flex-direction:column !important; gap:5px !important; }
        div[data-testid="stSelectbox"] > label,
        div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
            min-height:20px !important; line-height:20px !important; margin:0 0 1px 2px !important;
            font-size:9.5px !important; color:#243b53 !important; white-space:nowrap !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height:38px !important; height:38px !important; border:1px solid #cbd9ea !important;
            border-radius:10px !important; background:linear-gradient(180deg,#ffffff,#f5f8fc) !important;
        }

        .kpi-card {
            position:relative; min-height:76px; padding:8px 9px 9px;
            border:1px solid #cbd5e1; border-radius:13px;
            background:linear-gradient(145deg,#ffffff 0%,#f8fafc 48%,#e7edf5 100%);
            box-shadow:0 4px 0 #c2ccd9,0 8px 13px rgba(15,23,42,.14),inset 1px 1px 0 #fff;
        }
        .kpi-head { display:grid; grid-template-columns:minmax(0,1fr) 26px; gap:5px; align-items:center; }
        .kpi-title { color:var(--accent); font-size:10px; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .kpi-icon { width:26px; height:26px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:14px; background:#fff; border:1px solid #d6e0eb; }
        .kpi-value { color:#102a43; font-size:16px; font-weight:900; margin-top:3px; line-height:1.08; white-space:nowrap; }
        .kpi-footer { display:flex; justify-content:space-between; align-items:center; gap:5px; margin-top:5px; }
        .kpi-ly { color:#64748b; font-size:8.5px; font-weight:600; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
        .kpi-growth { padding:2px 6px; border:1px solid; border-radius:999px; font-size:8.5px; font-weight:700; white-space:nowrap; }

        [data-testid="stDataFrame"] { border:1px solid #e2eaf3; border-radius:10px; overflow:hidden; }
        [data-testid="stDataFrame"] table { font-size:11px; }

        div[data-testid="stDownloadButton"] > button,
        .stButton > button { border-radius:8px !important; min-height:34px !important; font-size:10px !important; font-weight:800 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# Data helpers
# =====================================================
def _normalized_name(value: str) -> str:
    return str(value).strip().replace("_", "").replace(" ", "").casefold()


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    if df is None:
        return None
    column_map = {_normalized_name(c): c for c in df.columns}
    for candidate in candidates:
        found = column_map.get(_normalized_name(candidate))
        if found is not None:
            return found
    return None


def normalize_pnl_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise SP output without changing accounting values."""
    if df is None:
        return pd.DataFrame()

    out = df.copy()
    aliases = {
        "COMPNAME": ["COMPNAME", "compname", "company", "companyname"],
        "zone": ["zone", "zonename"],
        "circle": ["circle", "circlename", "hubname"],
        "branch": ["branch", "branchname"],
        "grno": ["grno", "gr_no", "grnumber"],
        "grdt": ["grdt", "grdate", "bookingdate"],
        "GRTYPE": ["GRTYPE", "grtype"],
        "LOADTYPE": ["LOADTYPE", "loadtype", "load_type"],
        "FIN_MONTH": ["FIN_MONTH", "fin_month", "financialmonth"],
        "REVENUE": ["REVENUE", "revenue", "business"],
        "EXPENSE": ["EXPENSE", "expense", "expenses", "cost"],
        "PNL": ["PNL", "pnl", "profitloss", "profit_loss", "profitandloss"],
        "Consignor": ["Consignor", "consignor"],
        "Consignee": ["Consignee", "consignee"],
        "Route": ["Route", "route", "routename"],
        "COUNTRY": ["COUNTRY", "country", "countryname"],
        "Customer": ["Customer", "customer", "customername", "Consignor"],
    }

    rename_map = {}
    for target, candidates in aliases.items():
        source = _find_column(out, candidates)
        if source is not None and source != target:
            rename_map[source] = target
    out = out.rename(columns=rename_map)

    for col in ["REVENUE", "EXPENSE", "PNL", "FIN_MONTH"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    if "grdt" in out.columns:
        out["grdt"] = pd.to_datetime(out["grdt"], errors="coerce")

    for col in ["COMPNAME", "zone", "circle", "branch", "GRTYPE", "LOADTYPE"]:
        if col in out.columns:
            out[col] = out[col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")

    if "FIN_MONTH" in out.columns:
        out["FIN_MONTH"] = out["FIN_MONTH"].astype(int)
        out["Month"] = out["FIN_MONTH"].map(MONTH_MAP)
        out["Quarter"] = out["FIN_MONTH"].map(QUARTER_MAP)

    return out


def validate_pnl_data(df: pd.DataFrame) -> list[str]:
    required = ["COMPNAME", "zone", "circle", "branch", "grno", "grdt", "LOADTYPE", "FIN_MONTH", "REVENUE", "EXPENSE", "PNL"]
    return [col for col in required if col not in df.columns]


def get_previous_fy(fy: str) -> str:
    start_year, end_year = map(int, fy.split("-"))
    return f"{start_year - 1}-{end_year - 1}"


def get_conversion(conversion_type: str) -> tuple[float, str]:
    return (100_000, "Lac") if conversion_type == "Lac" else (10_000_000, "Cr")


def amount_text(value: float, conversion_type: str) -> str:
    divisor, unit = get_conversion(conversion_type)
    return f"₹{value / divisor:,.2f} {unit}"


def pct_change(current: float, previous: float) -> float:
    if previous is None or pd.isna(previous) or previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100


def pnl_margin(revenue: float, pnl: float) -> float:
    return (pnl / revenue * 100) if revenue else 0.0


def _apply_filter(df: pd.DataFrame, column: str, selected: str) -> pd.DataFrame:
    if selected == "All" or column not in df.columns:
        return df
    return df[df[column] == selected]


def _safe_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return sorted(values.unique().tolist(), key=str.casefold)


def calculate_pnl_kpis(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "revenue": 0.0, "expense": 0.0, "pnl": 0.0, "margin": 0.0,
            "ftl_pnl": 0.0, "ltl_pnl": 0.0, "profit_gr": 0, "loss_gr": 0,
            "avg_pnl_gr": 0.0,
        }

    revenue = float(df["REVENUE"].sum())
    expense = float(df["EXPENSE"].sum())
    pnl = float(df["PNL"].sum())
    gr_count = int(df["grno"].nunique()) if "grno" in df.columns else len(df)

    return {
        "revenue": revenue,
        "expense": expense,
        "pnl": pnl,
        "margin": pnl_margin(revenue, pnl),
        "ftl_pnl": float(df.loc[df["LOADTYPE"].eq("FTL"), "PNL"].sum()),
        "ltl_pnl": float(df.loc[df["LOADTYPE"].eq("LTL"), "PNL"].sum()),
        "profit_gr": int(df.loc[df["PNL"] > 0, "grno"].nunique()),
        "loss_gr": int(df.loc[df["PNL"] < 0, "grno"].nunique()),
        "avg_pnl_gr": pnl / gr_count if gr_count else 0.0,
    }


# =====================================================
# UI helpers
# =====================================================
def render_kpi_card(title: str, value: str, previous: str, growth: float, icon: str, accent: str, reverse_good: bool = False) -> None:
    positive = growth <= 0 if reverse_good else growth >= 0
    color = "#15803d" if positive else "#dc2626"
    border = "#86efac" if positive else "#fda4af"
    arrow = "▲" if growth >= 0 else "▼"
    html = (
        f'<div class="kpi-card" style="--accent:{accent};">'
        f'<div class="kpi-head"><div class="kpi-title">{escape(title)}</div><div class="kpi-icon">{icon}</div></div>'
        f'<div class="kpi-value">{escape(value)}</div>'
        f'<div class="kpi-footer"><span class="kpi-ly">LY: {escape(previous)}</span>'
        f'<span class="kpi-growth" style="color:{color};border-color:{border};background:#fff;">{arrow} {abs(growth):.1f}%</span></div>'
        f'</div>'
    )
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_header() -> st.delta_generator.DeltaGenerator:
    with st.container(border=True):
        left, right = st.columns([7, 1], gap="small", vertical_alignment="center")
        with left:
            st.markdown(
                '<div><div class="pnl-title">P&amp;L Dashboard</div>'
                '<div class="pnl-subtitle">Executive profitability view across company, geography, load type and branch</div></div>',
                unsafe_allow_html=True,
            )
        with right:
            export_placeholder = st.empty()
    return export_placeholder


def build_monthly_comparison(df: pd.DataFrame, prev_df: pd.DataFrame, divisor: float) -> pd.DataFrame:
    current = df.groupby("Month", observed=False, as_index=False).agg(
        Revenue=("REVENUE", "sum"), Expense=("EXPENSE", "sum"), PNL=("PNL", "sum")
    )
    previous = prev_df.groupby("Month", observed=False, as_index=False).agg(
        PY_PNL=("PNL", "sum")
    ) if prev_df is not None and not prev_df.empty else pd.DataFrame(columns=["Month", "PY_PNL"])

    result = current.merge(previous, on="Month", how="left")
    result["Month"] = pd.Categorical(result["Month"], MONTH_ORDER, ordered=True)
    result = result.sort_values("Month")
    for col in ["Revenue", "Expense", "PNL", "PY_PNL"]:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0) / divisor
    result["Margin %"] = result.apply(lambda r: (r["PNL"] / r["Revenue"] * 100) if r["Revenue"] else 0, axis=1)
    return result


def build_group_summary(df: pd.DataFrame, prev_df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    current = df.groupby(group_col, dropna=False, as_index=False).agg(
        Revenue=("REVENUE", "sum"), Expense=("EXPENSE", "sum"), PNL=("PNL", "sum"), GRs=("grno", "nunique")
    )
    previous = prev_df.groupby(group_col, dropna=False, as_index=False).agg(PY_PNL=("PNL", "sum")) \
        if prev_df is not None and not prev_df.empty and group_col in prev_df.columns \
        else pd.DataFrame(columns=[group_col, "PY_PNL"])
    summary = current.merge(previous, on=group_col, how="left")
    summary["PY_PNL"] = pd.to_numeric(summary["PY_PNL"], errors="coerce").fillna(0)
    summary["Margin %"] = summary.apply(lambda r: pnl_margin(r["Revenue"], r["PNL"]), axis=1)
    summary["Growth %"] = summary.apply(lambda r: pct_change(r["PNL"], r["PY_PNL"]), axis=1)
    return summary



def growth_label(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"


def build_pnl_yoy_trend(
    current_df: pd.DataFrame,
    previous_df: pd.DataFrame,
    trend_type: str,
    date_col: str,
    fy_start,
    prev_fy_start,
    divisor: float,
) -> pd.DataFrame:
    """Build Current FY versus LY P&L trend for daily, weekly, monthly or quarterly views."""
    cur = current_df[[c for c in [date_col, "PNL", "FIN_MONTH"] if c in current_df.columns]].copy()
    prev = (
        previous_df[[c for c in [date_col, "PNL", "FIN_MONTH"] if c in previous_df.columns]].copy()
        if previous_df is not None and not previous_df.empty
        else pd.DataFrame()
    )

    cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty and date_col in prev.columns:
        prev[date_col] = pd.to_datetime(prev[date_col], errors="coerce")

    fy_start_ts = pd.to_datetime(fy_start)
    prev_fy_start_ts = pd.to_datetime(prev_fy_start)

    if trend_type == "Daily":
        current = cur.groupby(cur[date_col].dt.date, dropna=True)["PNL"].sum().reset_index()
        current.columns = ["Period", "PNL"]
        current["Key"] = (pd.to_datetime(current["Period"]) - fy_start_ts).dt.days
        if not prev.empty:
            previous = prev.groupby(prev[date_col].dt.date, dropna=True)["PNL"].sum().reset_index()
            previous.columns = ["Period", "PY_PNL"]
            previous["Key"] = (pd.to_datetime(previous["Period"]) - prev_fy_start_ts).dt.days
        else:
            previous = pd.DataFrame(columns=["Key", "PY_PNL"])

    elif trend_type == "Weekly":
        current = cur.groupby(cur[date_col].dt.to_period("W"))["PNL"].sum().reset_index()
        current["Period"] = current[date_col].astype(str)
        current["Key"] = (current[date_col].dt.start_time - fy_start_ts).dt.days // 7
        current = current.drop(columns=[date_col])
        if not prev.empty:
            previous = prev.groupby(prev[date_col].dt.to_period("W"))["PNL"].sum().reset_index()
            previous["Key"] = (previous[date_col].dt.start_time - prev_fy_start_ts).dt.days // 7
            previous = previous.rename(columns={"PNL": "PY_PNL"}).drop(columns=[date_col])
        else:
            previous = pd.DataFrame(columns=["Key", "PY_PNL"])

    elif trend_type == "Quarterly":
        cur["Period"] = cur["FIN_MONTH"].map(QUARTER_MAP)
        current = cur.groupby("Period", observed=False)["PNL"].sum().reset_index()
        current["Period"] = pd.Categorical(current["Period"], QUARTER_ORDER, ordered=True)
        current = current.sort_values("Period")
        current["Key"] = current["Period"].astype(str)
        if not prev.empty:
            prev["Key"] = prev["FIN_MONTH"].map(QUARTER_MAP)
            previous = prev.groupby("Key", observed=False)["PNL"].sum().reset_index().rename(columns={"PNL": "PY_PNL"})
        else:
            previous = pd.DataFrame(columns=["Key", "PY_PNL"])

    else:
        cur["Period"] = cur["FIN_MONTH"].map(MONTH_MAP)
        current = cur.groupby("Period", observed=False)["PNL"].sum().reset_index()
        current["Period"] = pd.Categorical(current["Period"], MONTH_ORDER, ordered=True)
        current = current.sort_values("Period")
        current["Key"] = current["Period"].astype(str)
        if not prev.empty:
            prev["Key"] = prev["FIN_MONTH"].map(MONTH_MAP)
            previous = prev.groupby("Key", observed=False)["PNL"].sum().reset_index().rename(columns={"PNL": "PY_PNL"})
        else:
            previous = pd.DataFrame(columns=["Key", "PY_PNL"])

    current["P&L Display"] = pd.to_numeric(current["PNL"], errors="coerce").fillna(0) / divisor
    if not previous.empty:
        previous["LY P&L Display"] = pd.to_numeric(previous["PY_PNL"], errors="coerce").fillna(0) / divisor
        current = current.merge(previous[["Key", "LY P&L Display"]], on="Key", how="left")
    else:
        current["LY P&L Display"] = 0.0

    current["Growth %"] = current.apply(
        lambda row: pct_change(row["P&L Display"], row["LY P&L Display"])
        if row["LY P&L Display"] != 0 else None,
        axis=1,
    )
    current["Growth Label"] = current["Growth %"].apply(growth_label)
    return current


def _ranking_summary(df: pd.DataFrame, prev_df: pd.DataFrame, column: str) -> pd.DataFrame:
    current = df.groupby(column, dropna=False, as_index=False).agg(
        PNL=("PNL", "sum"), Revenue=("REVENUE", "sum"), GRs=("grno", "nunique")
    )
    previous = (
        prev_df.groupby(column, dropna=False, as_index=False).agg(PY_PNL=("PNL", "sum"))
        if prev_df is not None and not prev_df.empty and column in prev_df.columns
        else pd.DataFrame(columns=[column, "PY_PNL"])
    )
    result = current.merge(previous, on=column, how="left")
    result["PY_PNL"] = pd.to_numeric(result["PY_PNL"], errors="coerce").fillna(0)
    total = float(result["PNL"].sum())
    result["Share %"] = result["PNL"].apply(lambda value: value / total * 100 if total else 0)
    result["Growth %"] = result.apply(lambda row: pct_change(row["PNL"], row["PY_PNL"]), axis=1)
    return result


def _render_ranking_table(
    data: pd.DataFrame,
    name_col: str,
    title: str,
    unit: str,
    divisor: float,
    top_n: int,
) -> None:
    with st.container(border=True):
        st.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
        ranked = data.sort_values("PNL", ascending=False).head(top_n).copy()
        if ranked.empty:
            st.info("No data is available for the selected filters.")
            return
        ranked.insert(0, "Rank", range(1, len(ranked) + 1))
        ranked["P&L"] = ranked["PNL"] / divisor
        display = ranked[["Rank", name_col, "P&L", "Share %", "Growth %", "GRs"]]
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            height=min(465, 78 + (len(display) * 35)),
            column_config={
                "Rank": st.column_config.NumberColumn("#", format="%d", width="small"),
                name_col: st.column_config.TextColumn(name_col, width="large"),
                "P&L": st.column_config.NumberColumn(f"P&L ({unit})", format="%.2f"),
                "Share %": st.column_config.NumberColumn("% Share", format="%.2f%%"),
                "Growth %": st.column_config.NumberColumn("vs LY", format="%.1f%%"),
                "GRs": st.column_config.NumberColumn("GRs", format="%d"),
            },
        )


# =====================================================
# Main page
# =====================================================
def show_pnl_dashboard() -> None:
    _inject_pnl_css()
    export_placeholder = render_header()

    filter_cols = st.columns(10, gap="small")
    with filter_cols[0]:
        view_type = st.selectbox("⇄ View Type", ["Origin", "Destination"], key="pnl_view_type")
    with filter_cols[1]:
        fy = st.selectbox("◷ Financial Year", FY_OPTIONS, key="pnl_fy")

    if fy == "Select FY":
        st.info("Please select financial year")
        return

    # Temporary testing restriction: the P&L SP is currently loaded only for FY 2026-27.
    if fy != "2026-2027":
        st.warning("P&L testing is currently available only for FY 2026-2027.")
        return

    start_date, end_date = get_date_range(fy)
    prev_fy = get_previous_fy(fy)
    prev_start, prev_end = get_date_range(prev_fy)

    with st.spinner("Loading P&L data..."):
        raw_df, raw_prev_df = load_pnl_data_pair(
            start_date,
            end_date,
            prev_start,
            prev_end,
            view_type.lower(),
        )

    df = normalize_pnl_columns(raw_df)
    prev_df = normalize_pnl_columns(raw_prev_df)

    if df.empty:
        st.warning("No P&L data found for the selected financial year.")
        return

    missing = validate_pnl_data(df)
    if missing:
        st.error(f"Missing columns returned by stored procedure: {missing}")
        st.write("Available columns:", list(df.columns))
        return

    data_scope = st.session_state.get("data_scope", {}) or {}
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    if locked_branch:
        branch_rows = df[df["branch"].astype(str).str.casefold() == str(locked_branch).casefold()]
        if not branch_rows.empty:
            locked_branch = branch_rows["branch"].iloc[0]
            locked_circle = branch_rows["circle"].iloc[0]
            locked_zone = branch_rows["zone"].iloc[0]
    elif locked_circle:
        circle_rows = df[df["circle"].astype(str).str.casefold() == str(locked_circle).casefold()]
        if not circle_rows.empty:
            locked_circle = circle_rows["circle"].iloc[0]
            locked_zone = circle_rows["zone"].iloc[0]

    # Current-year cascading filters
    with filter_cols[2]:
        company = st.selectbox("▥ Company", ["All"] + _safe_options(df, "COMPNAME"), key="pnl_company")
    df = _apply_filter(df, "COMPNAME", company)

    with filter_cols[3]:
        if locked_zone:
            zone = locked_zone
            st.selectbox("◉ Zone", [zone], disabled=True, key="pnl_zone_locked")
        else:
            zone = st.selectbox("◉ Zone", ["All"] + _safe_options(df, "zone"), key="pnl_zone")
    df = _apply_filter(df, "zone", zone)

    with filter_cols[4]:
        if locked_circle:
            circle = locked_circle
            st.selectbox("◎ Circle", [circle], disabled=True, key="pnl_circle_locked")
        else:
            circle = st.selectbox("◎ Circle", ["All"] + _safe_options(df, "circle"), key="pnl_circle")
    df = _apply_filter(df, "circle", circle)

    with filter_cols[5]:
        if locked_branch:
            branch = locked_branch
            st.selectbox("⌂ Branch", [branch], disabled=True, key="pnl_branch_locked")
        else:
            branch = st.selectbox("⌂ Branch", ["All"] + _safe_options(df, "branch"), key="pnl_branch")
    df = _apply_filter(df, "branch", branch)

    with filter_cols[6]:
        available_quarters = [q for q in QUARTER_ORDER if q in df["Quarter"].dropna().tolist()]
        quarter = st.selectbox("▦ Quarter", ["All"] + available_quarters, key="pnl_quarter")
    df = _apply_filter(df, "Quarter", quarter)

    with filter_cols[7]:
        available_months = [m for m in MONTH_ORDER if m in df["Month"].dropna().tolist()]
        month = st.selectbox("▣ Month", ["All"] + available_months, key="pnl_month")
    df = _apply_filter(df, "Month", month)

    with filter_cols[8]:
        load_type = st.selectbox("▤ Load Type", ["All"] + _safe_options(df, "LOADTYPE"), key="pnl_loadtype")
    df = _apply_filter(df, "LOADTYPE", load_type)

    with filter_cols[9]:
        conversion_type = st.selectbox("₹ Conversion", ["Crore", "Lac"], key="pnl_conversion")

    divisor, unit = get_conversion(conversion_type)

    # Apply identical filters to LY data
    for column, selected in [
        ("COMPNAME", company), ("zone", zone), ("circle", circle), ("branch", branch),
        ("Quarter", quarter), ("Month", month), ("LOADTYPE", load_type),
    ]:
        prev_df = _apply_filter(prev_df, column, selected)

    chips = [
        ("FY", fy), ("View", view_type), ("Company", company), ("Zone", zone),
        ("Circle", circle), ("Branch", branch), ("Quarter", quarter),
        ("Month", month), ("Load", load_type), ("Unit", conversion_type),
    ]
    chip_html = "".join(
        f'<span class="filter-chip">{escape(label)}: {escape(str(value))}</span>'
        for label, value in chips if value not in (None, "", "All")
    )
    st.markdown(f'<div class="filter-summary">{chip_html}</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    # Lazy CSV export
    safe_fy = fy.replace("/", "-")
    export_key = f"pnl_export_ready_{view_type}_{safe_fy}"
    with export_placeholder:
        if not st.session_state.get(export_key, False):
            if st.button("⬇ Prepare CSV", key=f"prepare_{export_key}", width="content"):
                st.session_state[export_key] = True
                st.rerun()
        else:
            st.download_button(
                "⬇ Download CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"pnl_dashboard_{view_type.lower()}_{safe_fy}.csv",
                mime="text/csv",
                key=f"download_{export_key}",
                width="content",
                on_click=lambda: st.session_state.update({export_key: False}),
            )

    current = calculate_pnl_kpis(df)
    previous = calculate_pnl_kpis(prev_df)

    kpi_specs = [
        ("Revenue", amount_text(current["revenue"], conversion_type), amount_text(previous["revenue"], conversion_type), pct_change(current["revenue"], previous["revenue"]), "💰", "#2563eb", False),
        ("Expense", amount_text(current["expense"], conversion_type), amount_text(previous["expense"], conversion_type), pct_change(current["expense"], previous["expense"]), "🧾", "#dc2626", True),
        ("P&L", amount_text(current["pnl"], conversion_type), amount_text(previous["pnl"], conversion_type), pct_change(current["pnl"], previous["pnl"]), "📈", "#16a34a" if current["pnl"] >= 0 else "#dc2626", False),
        ("P&L Margin", f'{current["margin"]:.2f}%', f'{previous["margin"]:.2f}%', current["margin"] - previous["margin"], "🎯", "#7c3aed", False),
        ("FTL P&L", amount_text(current["ftl_pnl"], conversion_type), amount_text(previous["ftl_pnl"], conversion_type), pct_change(current["ftl_pnl"], previous["ftl_pnl"]), "🚛", "#2563eb", False),
        ("LTL P&L", amount_text(current["ltl_pnl"], conversion_type), amount_text(previous["ltl_pnl"], conversion_type), pct_change(current["ltl_pnl"], previous["ltl_pnl"]), "🚚", "#0f766e", False),
        ("Profit GR", f'{current["profit_gr"]:,}', f'{previous["profit_gr"]:,}', pct_change(current["profit_gr"], previous["profit_gr"]), "✅", "#16a34a", False),
        ("Loss GR", f'{current["loss_gr"]:,}', f'{previous["loss_gr"]:,}', pct_change(current["loss_gr"], previous["loss_gr"]), "⚠️", "#dc2626", True),
        ("Avg P&L / GR", f'₹{current["avg_pnl_gr"]:,.0f}', f'₹{previous["avg_pnl_gr"]:,.0f}', pct_change(current["avg_pnl_gr"], previous["avg_pnl_gr"]), "📦", "#d97706", False),
    ]

    kpi_cols = st.columns(9, gap="small")
    for col, spec in zip(kpi_cols, kpi_specs):
        with col:
            render_kpi_card(*spec)

    # =====================================================
    # Overview-style P&L insights and visuals
    # =====================================================
    trend_left, load_right = st.columns([1.20, 0.80], gap="small")

    with trend_left:
        with st.container(border=True):
            title_col, period_col = st.columns([2, 2])
            total_growth = pct_change(current["pnl"], previous["pnl"]) if previous["pnl"] else None
            badge_color = "#166534" if total_growth is None or total_growth >= 0 else "#dc2626"
            with title_col:
                st.markdown(
                    f'<div class="section-title">P&L Trend '
                    f'<span style="font-size:11px;color:{badge_color};">'
                    f'({growth_label(total_growth)} vs LY)</span></div>',
                    unsafe_allow_html=True,
                )
            with period_col:
                trend_type = st.segmented_control(
                    "P&L trend period",
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    default="Monthly",
                    label_visibility="collapsed",
                    key="pnl_trend_type",
                ) or "Monthly"

            trend_df = build_pnl_yoy_trend(
                df, prev_df, trend_type, "grdt", start_date, prev_start, divisor
            )
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=trend_df["Period"], y=trend_df["LY P&L Display"],
                name=f"LY ({prev_fy})", marker_color="#cbd5e1",
                text=trend_df["LY P&L Display"], texttemplate="%{text:.2f}",
                textposition="outside", cliponaxis=False,
                hovertemplate=f"<b>%{{x}}</b><br>LY P&L: ₹%{{y:.2f}} {unit}<extra></extra>",
            ))
            fig_trend.add_trace(go.Bar(
                x=trend_df["Period"], y=trend_df["P&L Display"],
                name=f"Current ({fy})", marker_color="#16a34a",
                text=trend_df["P&L Display"], texttemplate="%{text:.2f}",
                textposition="outside", cliponaxis=False,
                hovertemplate=f"<b>%{{x}}</b><br>Current P&L: ₹%{{y:.2f}} {unit}<extra></extra>",
            ))
            fig_trend.add_hline(y=0, line_color="#64748b", line_width=1)
            fig_trend.update_layout(
                barmode="group", height=330, margin=dict(l=5, r=5, t=24, b=5),
                plot_bgcolor="#f8fafc", paper_bgcolor="rgba(0,0,0,0)",
                yaxis_title=f"P&L ({unit})", xaxis_title="",
                legend=dict(orientation="h", y=1.08, x=0),
            )
            st.plotly_chart(fig_trend, width="stretch", config={"displayModeBar": False})

    with load_right:
        with st.container(border=True):
            st.markdown('<div class="section-title">P&L by Load Type (CY)</div>', unsafe_allow_html=True)
            load_summary = df.groupby("LOADTYPE", as_index=False)["PNL"].sum()
            load_summary = load_summary[load_summary["LOADTYPE"].isin(["FTL", "LTL"])]
            load_values = {
                row["LOADTYPE"]: float(row["PNL"])
                for _, row in load_summary.iterrows()
            }
            ftl_value = load_values.get("FTL", 0.0)
            ltl_value = load_values.get("LTL", 0.0)
            # A pie cannot represent negative values. Use absolute slice size while showing signed P&L.
            pie_values = [abs(ftl_value), abs(ltl_value)]
            if sum(pie_values) == 0:
                st.info("No FTL/LTL P&L is available for the selected filters.")
            else:
                fig_load = go.Figure(go.Pie(
                    labels=["FTL", "LTL"], values=pie_values, hole=0.66,
                    marker=dict(colors=["#2563eb", "#0f766e"], line=dict(color="#ffffff", width=2)),
                    customdata=[[ftl_value / divisor], [ltl_value / divisor]],
                    textinfo="label+percent",
                    hovertemplate=f"<b>%{{label}}</b><br>P&L: ₹%{{customdata[0]:.2f}} {unit}<extra></extra>",
                ))
                fig_load.update_layout(
                    height=330, margin=dict(l=5, r=5, t=10, b=5),
                    paper_bgcolor="rgba(0,0,0,0)", showlegend=True,
                    legend=dict(orientation="h", y=-0.02, x=0.28),
                    annotations=[dict(
                        text=f"₹{current['pnl'] / divisor:.2f}<br>{unit} P&L",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=15, color="#0f172a"),
                    )],
                )
                st.plotly_chart(fig_load, width="stretch", config={"displayModeBar": False})

    zone_left, country_right = st.columns([0.80, 1.20], gap="small")

    with zone_left:
        with st.container(border=True):
            st.markdown('<div class="section-title">P&L by Zone</div>', unsafe_allow_html=True)
            zone_df = df.groupby("zone", as_index=False)["PNL"].sum().sort_values("PNL", ascending=False)
            if zone_df.empty:
                st.info("No zone P&L is available for the selected filters.")
            else:
                zone_df["P&L Display"] = zone_df["PNL"] / divisor
                fig_zone = px.bar(
                    zone_df.sort_values("PNL"), x="P&L Display", y="zone",
                    orientation="h", text="P&L Display",
                    color="P&L Display", color_continuous_scale="RdYlGn",
                )
                fig_zone.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
                fig_zone.add_vline(x=0, line_color="#64748b", line_width=1)
                fig_zone.update_layout(
                    height=360, margin=dict(l=5, r=28, t=8, b=5),
                    xaxis_title=f"P&L ({unit})", yaxis_title="",
                    plot_bgcolor="#f8fafc", paper_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_zone, width="stretch", config={"displayModeBar": False})

    with country_right:
        with st.container(border=True):
            st.markdown('<div class="section-title">Zone-wise Country P&L</div>', unsafe_allow_html=True)
            if view_type != "Origin":
                st.info("Zone-wise Country P&L is available in Origin view.")
            elif "COUNTRY" not in df.columns:
                st.info("COUNTRY column is not available in the P&L dataset.")
            else:
                matrix_source = df.groupby(["zone", "COUNTRY"], dropna=False)["PNL"].sum().reset_index()
                matrix_source["P&L"] = matrix_source["PNL"] / divisor
                matrix = matrix_source.pivot(index="zone", columns="COUNTRY", values="P&L").fillna(0)
                matrix["Total"] = matrix.sum(axis=1)
                matrix = matrix.sort_values("Total", ascending=False).reset_index()
                st.dataframe(
                    matrix,
                    width="stretch", hide_index=True, height=360,
                    column_config={
                        col: st.column_config.NumberColumn(col, format="%.2f")
                        for col in matrix.columns if col != "zone"
                    },
                )

    customer_col = "Customer" if "Customer" in df.columns else ("Consignor" if "Consignor" in df.columns else None)
    route_col = "Route" if "Route" in df.columns else None

    rank_left, rank_right = st.columns(2, gap="small")
    with rank_left:
        customer_top_n = st.selectbox(
            "Top N Customers", TOP_N_OPTIONS, index=0, key="pnl_customer_top_n"
        )
        if customer_col:
            customer_rank = _ranking_summary(df, prev_df, customer_col)
            _render_ranking_table(
                customer_rank, customer_col,
                f"Top {customer_top_n} Customers by P&L", unit, divisor, customer_top_n,
            )
        else:
            with st.container(border=True):
                st.info("Customer/Consignor column is not available in the P&L dataset.")

    with rank_right:
        route_top_n = st.selectbox(
            "Top N Routes", TOP_N_OPTIONS, index=0, key="pnl_route_top_n"
        )
        if route_col:
            route_rank = _ranking_summary(df, prev_df, route_col)
            _render_ranking_table(
                route_rank, route_col,
                f"Top {route_top_n} Routes by P&L", unit, divisor, route_top_n,
            )
        else:
            with st.container(border=True):
                st.info("Route column is not available in the P&L dataset.")

    branch_summary = build_group_summary(df, prev_df, "branch")
    with st.container(border=True):
        st.markdown('<div class="section-title">Branches by P&L</div>', unsafe_allow_html=True)
        pnl_slab_options = [
            "All", "Loss", "₹0–5 Lac", "₹5–10 Lac", "₹10–25 Lac",
            "₹25–50 Lac", "₹50 Lac & Above",
        ]
        selected_slab = st.segmented_control(
            "Branch P&L slab", pnl_slab_options, default="All",
            key="top_branch_pnl_slab", label_visibility="collapsed", width="stretch",
        ) or "All"
        slab_ranges = {
            "All": (None, None), "Loss": (None, 0), "₹0–5 Lac": (0, 500000),
            "₹5–10 Lac": (500000, 1000000), "₹10–25 Lac": (1000000, 2500000),
            "₹25–50 Lac": (2500000, 5000000), "₹50 Lac & Above": (5000000, None),
        }
        lower, upper = slab_ranges[selected_slab]
        branch_rank = branch_summary.copy()
        if selected_slab == "Loss":
            branch_rank = branch_rank[branch_rank["PNL"] < 0]
        else:
            if lower is not None:
                branch_rank = branch_rank[branch_rank["PNL"] >= lower]
            if upper is not None:
                branch_rank = branch_rank[branch_rank["PNL"] < upper]
        branch_rank = branch_rank.sort_values("PNL", ascending=False)
        if branch_rank.empty:
            st.info(f"No branch falls in the {selected_slab} P&L slab.")
        else:
            branch_rank["P&L Display"] = branch_rank["PNL"] / divisor
            branch_rank["Revenue Display"] = branch_rank["Revenue"] / divisor
            branch_rank["Expense Display"] = branch_rank["Expense"] / divisor
            st.dataframe(
                branch_rank[["branch", "P&L Display", "Revenue Display", "Expense Display", "Margin %", "GRs"]],
                width="stretch", hide_index=True, height=430,
                column_config={
                    "branch": st.column_config.TextColumn("Branch", width="large"),
                    "P&L Display": st.column_config.NumberColumn(f"P&L ({unit})", format="%.2f"),
                    "Revenue Display": st.column_config.NumberColumn(f"Revenue ({unit})", format="%.2f"),
                    "Expense Display": st.column_config.NumberColumn(f"Expense ({unit})", format="%.2f"),
                    "Margin %": st.column_config.NumberColumn("Margin %", format="%.2f%%"),
                    "GRs": st.column_config.NumberColumn("GRs", format="%d"),
                },
            )

    monthly = build_monthly_comparison(df, prev_df, divisor)

    # Detailed tabs
    tab1, tab2, tab3 = st.tabs(["Branch Summary", "Monthly Summary", "Detailed GR Records"])

    with tab1:
        display = branch_summary.sort_values("PNL", ascending=False).copy()
        for col in ["Revenue", "Expense", "PNL", "PY_PNL"]:
            display[col] = display[col] / divisor
        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            height=430,
            column_config={
                "Revenue": st.column_config.NumberColumn(f"Revenue ({unit})", format="%.2f"),
                "Expense": st.column_config.NumberColumn(f"Expense ({unit})", format="%.2f"),
                "PNL": st.column_config.NumberColumn(f"P&L ({unit})", format="%.2f"),
                "PY_PNL": st.column_config.NumberColumn(f"LY P&L ({unit})", format="%.2f"),
                "Margin %": st.column_config.NumberColumn("Margin %", format="%.2f%%"),
                "Growth %": st.column_config.NumberColumn("Growth %", format="%.1f%%"),
                "GRs": st.column_config.NumberColumn("GRs", format="%d"),
            },
        )

    with tab2:
        monthly_display = monthly.copy()
        st.dataframe(
            monthly_display,
            width="stretch",
            hide_index=True,
            column_config={
                "Revenue": st.column_config.NumberColumn(f"Revenue ({unit})", format="%.2f"),
                "Expense": st.column_config.NumberColumn(f"Expense ({unit})", format="%.2f"),
                "PNL": st.column_config.NumberColumn(f"P&L ({unit})", format="%.2f"),
                "PY_PNL": st.column_config.NumberColumn(f"LY P&L ({unit})", format="%.2f"),
                "Margin %": st.column_config.NumberColumn("Margin %", format="%.2f%%"),
            },
        )

    with tab3:
        detail_columns = [
            col for col in [
                "COMPNAME", "zone", "circle", "branch", "grno", "grdt", "GRTYPE",
                "LOADTYPE", "Customer", "Consignor", "Consignee", "Route", "COUNTRY", "REVENUE",
                "DELIVERYINCOME", "ADDITIONALFREIGHT", "OTHERINCOME", "RAW_EXPENSE",
                "EXPENSE", "PNL",
            ] if col in df.columns
        ]
        detail_df = df[detail_columns].copy()
        search_text = st.text_input("Search GR, branch, customer or route", key="pnl_detail_search")
        if search_text:
            mask = detail_df.astype(str).apply(
                lambda col: col.str.contains(search_text, case=False, na=False)
            ).any(axis=1)
            detail_df = detail_df[mask]

        st.dataframe(
            detail_df,
            width="stretch",
            hide_index=True,
            height=460,
            column_config={
                "REVENUE": st.column_config.NumberColumn("Revenue/Freight (₹)", format="₹%.0f"),
                "DELIVERYINCOME": st.column_config.NumberColumn("Delivery Income (₹)", format="₹%.0f"),
                "ADDITIONALFREIGHT": st.column_config.NumberColumn("Additional Freight (₹)", format="₹%.0f"),
                "OTHERINCOME": st.column_config.NumberColumn("Other Income (₹)", format="₹%.0f"),
                "RAW_EXPENSE": st.column_config.NumberColumn("Raw Expense (₹)", format="₹%.0f"),
                "EXPENSE": st.column_config.NumberColumn("Adjusted Expense (₹)", format="₹%.0f"),
                "PNL": st.column_config.NumberColumn("P&L (₹)", format="₹%.0f"),
                "grdt": st.column_config.DateColumn("GR Date", format="DD-MMM-YYYY"),
            },
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            detail_df.to_excel(writer, index=False, sheet_name="GR Detail")
            branch_summary.to_excel(writer, index=False, sheet_name="Branch Summary")
            monthly.to_excel(writer, index=False, sheet_name="Monthly Summary")
        excel_buffer.seek(0)

        st.download_button(
            "Download P&L analysis (Excel)",
            data=excel_buffer.getvalue(),
            file_name=f"pnl_analysis_{view_type.lower()}_{safe_fy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="pnl_excel_download",
            width="content",
        )


# Optional alias if your app menu expects a shorter function name.
def show_pnl() -> None:
    show_pnl_dashboard()
