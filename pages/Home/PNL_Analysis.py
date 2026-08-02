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
TOP_N_OPTIONS = [10, 20, 30, 40]
QUARTER_MAP = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2", 7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"}
FY_OPTIONS = [
    "Select FY", "2026-2027", "2025-2026", "2024-2025",
    "2023-2024", "2022-2023", "2021-2022", "2020-2021",
]


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
        "Route": ["Route", "route"],
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




def build_pnl_yoy_trend(current_df, previous_df, trend_type, date_col, fy_start, prev_fy_start):
    cur = current_df[[date_col, "PNL", "FIN_MONTH"]].copy()
    prev = previous_df[[date_col, "PNL", "FIN_MONTH"]].copy() if previous_df is not None and not previous_df.empty else pd.DataFrame()
    cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty:
        prev[date_col] = pd.to_datetime(prev[date_col], errors="coerce")
    fy_start_ts = pd.to_datetime(fy_start)
    prev_start_ts = pd.to_datetime(prev_fy_start)
    if trend_type == "Daily":
        trend = cur.groupby(cur[date_col].dt.date)["PNL"].sum().reset_index(); trend.columns = ["Period", "PNL"]
        trend["Key"] = (pd.to_datetime(trend["Period"]) - fy_start_ts).dt.days
        py = prev.groupby(prev[date_col].dt.date)["PNL"].sum().reset_index() if not prev.empty else pd.DataFrame()
        if not py.empty:
            py.columns = ["Period", "PY_PNL"]; py["Key"] = (pd.to_datetime(py["Period"]) - prev_start_ts).dt.days
    elif trend_type == "Weekly":
        trend = cur.groupby(cur[date_col].dt.to_period("W"))["PNL"].sum().reset_index()
        trend["Period"] = trend[date_col].astype(str); trend["Key"] = (trend[date_col].dt.start_time - fy_start_ts).dt.days // 7
        trend = trend.drop(columns=[date_col])
        py = prev.groupby(prev[date_col].dt.to_period("W"))["PNL"].sum().reset_index() if not prev.empty else pd.DataFrame()
        if not py.empty:
            py["Key"] = (py[date_col].dt.start_time - prev_start_ts).dt.days // 7
            py = py.rename(columns={"PNL": "PY_PNL"}).drop(columns=[date_col])
    elif trend_type == "Quarterly":
        trend = cur.assign(Period=cur["FIN_MONTH"].map(QUARTER_MAP)).groupby("Period")["PNL"].sum().reset_index()
        trend["Period"] = pd.Categorical(trend["Period"], QUARTER_ORDER, ordered=True); trend = trend.sort_values("Period"); trend["Key"] = trend["Period"].astype(str)
        py = prev.assign(Key=prev["FIN_MONTH"].map(QUARTER_MAP)).groupby("Key")["PNL"].sum().reset_index().rename(columns={"PNL": "PY_PNL"}) if not prev.empty else pd.DataFrame()
    else:
        trend = cur.assign(Period=cur["FIN_MONTH"].map(MONTH_MAP)).groupby("Period")["PNL"].sum().reset_index()
        trend["Period"] = pd.Categorical(trend["Period"], MONTH_ORDER, ordered=True); trend = trend.sort_values("Period"); trend["Key"] = trend["Period"].astype(str)
        py = prev.assign(Key=prev["FIN_MONTH"].map(MONTH_MAP)).groupby("Key")["PNL"].sum().reset_index().rename(columns={"PNL": "PY_PNL"}) if not prev.empty else pd.DataFrame()
    if py.empty:
        py = pd.DataFrame(columns=["Key", "PY_PNL"])
    trend = trend.merge(py[["Key", "PY_PNL"]], on="Key", how="left")
    trend["PY_PNL"] = pd.to_numeric(trend["PY_PNL"], errors="coerce").fillna(0)
    return trend


def render_top_n_pnl_table(
    df,
    prev_df,
    group_col,
    entity_name,
    unit,
    divisor,
    widget_key,
    subtitle="",
):
    """Render the Overview-style Top-N insight table using P&L instead of business."""
    title_col, selector_col = st.columns(
        [4.2, 1.0],
        gap="small",
        vertical_alignment="center",
    )

    with selector_col:
        top_n = st.selectbox(
            f"{entity_name} to display",
            TOP_N_OPTIONS,
            index=0,
            format_func=lambda value: f"Top {value}",
            key=f"{widget_key}_top_n",
            label_visibility="collapsed",
        )

    with title_col:
        st.markdown(
            f"<div style='font-size:18px;font-weight:400;color:#0f2744;"
            f"margin:1px 0 9px 2px;'>Top {top_n} {entity_name} by P&amp;L</div>"
            f"<div style='font-size:12px;font-weight:400;color:#64748b;"
            f"margin-top:-4px;'>{escape(subtitle)}</div>",
            unsafe_allow_html=True,
        )

    current_data = df[[group_col, "PNL"]].copy()
    current_data[group_col] = (
        current_data[group_col]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
    )
    current_rank = (
        current_data[current_data[group_col].ne("Unknown")]
        .groupby(group_col, dropna=False)["PNL"]
        .sum()
        .reset_index(name="Current PNL")
    )

    if (
        prev_df is not None
        and not prev_df.empty
        and group_col in prev_df.columns
        and "PNL" in prev_df.columns
    ):
        previous_data = prev_df[[group_col, "PNL"]].copy()
        previous_data[group_col] = (
            previous_data[group_col]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
        )
        previous_rank = (
            previous_data[previous_data[group_col].ne("Unknown")]
            .groupby(group_col, dropna=False)["PNL"]
            .sum()
            .reset_index(name="Previous PNL")
        )
    else:
        previous_rank = pd.DataFrame(columns=[group_col, "Previous PNL"])

    ranking = current_rank.merge(previous_rank, on=group_col, how="left")
    ranking["Previous PNL"] = pd.to_numeric(
        ranking["Previous PNL"], errors="coerce"
    ).fillna(0.0)
    ranking["P&L Display"] = (
        pd.to_numeric(ranking["Current PNL"], errors="coerce").fillna(0.0)
        / divisor
    ).round(2)

    # Share is based on absolute P&L so mixed profit/loss values remain meaningful.
    total_abs_pnl = float(ranking["Current PNL"].abs().sum())
    ranking["Share %"] = (
        ranking["Current PNL"].abs() / total_abs_pnl * 100
        if total_abs_pnl else 0.0
    )
    ranking["Growth %"] = ranking.apply(
        lambda row: pct_change(row["Current PNL"], row["Previous PNL"])
        if row["Previous PNL"] != 0 else None,
        axis=1,
    )
    ranking = (
        ranking.sort_values("Current PNL", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    if ranking.empty:
        st.info(f"No {entity_name.lower()} P&L is available for the selected filters.")
        return

    max_abs_value = max(float(ranking["P&L Display"].abs().max()), 1.0)
    prefix = "cust" if entity_name == "Customers" else "route"
    bar_gradient = (
        "linear-gradient(90deg,#60a5fa,#2563eb)"
        if prefix == "cust"
        else "linear-gradient(90deg,#2dd4bf,#0f766e)"
    )
    singular_name = "Customer" if entity_name == "Customers" else "Route"
    rows = []

    for idx, row in ranking.iterrows():
        pnl_display = float(row["P&L Display"] or 0)
        share_pct = float(row["Share %"] or 0)
        bar_width = min((abs(pnl_display) / max_abs_value) * 100, 100)
        growth = row["Growth %"]

        if pd.isna(growth):
            growth_html = f"<span class='{prefix}-growth new'>NEW</span>"
        else:
            positive = growth >= 0
            growth_class = "up" if positive else "down"
            growth_arrow = "▲" if positive else "▼"
            growth_html = (
                f"<span class='{prefix}-growth {growth_class}'>"
                f"{growth_arrow} {abs(growth):.1f}%</span>"
            )

        full_name = escape(str(row[group_col]))
        value_color = "#0f172a" if pnl_display >= 0 else "#dc2626"
        rows.append(
            "<tr>"
            f"<td class='{prefix}-rank'>{idx + 1}</td>"
            f"<td class='{prefix}-name' title='{full_name}'>{full_name}</td>"
            f"<td class='{prefix}-revenue'>"
            f"<div class='{prefix}-value' style='color:{value_color};'>"
            f"₹{pnl_display:.2f} {escape(str(unit))}</div>"
            f"<div class='{prefix}-bar-track'>"
            f"<div class='{prefix}-bar-fill' style='width:{bar_width:.1f}%'></div>"
            "</div></td>"
            f"<td class='{prefix}-share'>{share_pct:.1f}%</td>"
            f"<td class='{prefix}-yoy'>{growth_html}</td>"
            "</tr>"
        )

    table_html = f"""
    <style>
        .{prefix}-insight-wrap {{
            width:100%; overflow-x:auto; margin-top:5px;
            border:1px solid #e2e8f0; border-radius:10px;
            background:#ffffff;
        }}
        .{prefix}-insight-table {{
            width:100%; border-collapse:collapse;
            table-layout:fixed; font-size:12px; color:#334155;
        }}
        .{prefix}-insight-table th {{
            padding:7px 6px; background:#f8fafc;
            color:#64748b; font-size:12px; font-weight:400;
            text-align:left; border-bottom:1px solid #e2e8f0;
            white-space:nowrap;
        }}
        .{prefix}-insight-table td {{
            padding:8px 6px; border-bottom:1px solid #edf2f7;
            vertical-align:middle;
        }}
        .{prefix}-insight-table tr:last-child td {{border-bottom:0;}}
        .{prefix}-insight-table tbody tr:hover {{background:#f8fbff;}}
        .{prefix}-rank {{
            width:4%; padding-left:2px !important; padding-right:2px !important;
            text-align:center; font-weight:400; color:#64748b;
        }}
        .{prefix}-name {{
            width:38%; padding-left:3px !important;
            font-weight:400; color:#1e293b;
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }}
        .{prefix}-revenue {{width:32%;}}
        .{prefix}-value {{font-weight:400; margin-bottom:3px;}}
        .{prefix}-bar-track {{
            width:100%; height:5px; border-radius:999px;
            background:#e8eef8; overflow:hidden;
        }}
        .{prefix}-bar-fill {{
            height:5px; border-radius:999px;
            background:{bar_gradient};
        }}
        .{prefix}-share {{
            width:12%; text-align:right; font-weight:400; color:#475569;
        }}
        .{prefix}-yoy {{width:14%; text-align:right;}}
        .{prefix}-growth {{
            display:inline-block; min-width:50px; text-align:right;
            font-size:11px; font-weight:400;
        }}
        .{prefix}-growth.up {{color:#16a34a;}}
        .{prefix}-growth.down {{color:#dc2626;}}
        .{prefix}-growth.new {{color:#7c3aed;}}
    </style>
    <div class="{prefix}-insight-wrap">
        <table class="{prefix}-insight-table">
            <colgroup>
                <col style="width:4%">
                <col style="width:38%">
                <col style="width:32%">
                <col style="width:12%">
                <col style="width:14%">
            </colgroup>
            <thead>
                <tr>
                    <th style="text-align:center;">#</th>
                    <th>{singular_name}</th>
                    <th>P&amp;L ({escape(str(unit))})</th>
                    <th style="text-align:right;">% Share</th>
                    <th style="text-align:right;">vs LY</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>
    """

    if hasattr(st, "html"):
        st.html(table_html)
    else:
        st.markdown(table_html, unsafe_allow_html=True)

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
    # STEP 1: Overview-style P&L Trend, Load Type and Company
    # =====================================================
    st.markdown("<div aria-hidden='true' style='height:4px'></div>", unsafe_allow_html=True)

    row1, row2 = st.columns([1.20, 0.80])

    with row1:
        with st.container(border=True):
            title_col, filter_col = st.columns([2, 2])

            total_growth = pct_change(current["pnl"], previous["pnl"])
            with title_col:
                trend_badge_color = "#166534" if total_growth >= 0 else "#dc2626"
                trend_arrow = "▲" if total_growth >= 0 else "▼"
                st.markdown(
                    f"<div style='font-size:14px;font-weight:400;color:#0f172a;'>P&L Trend "
                    f"<span style='font-size:11px;font-weight:700;color:{trend_badge_color};'>"
                    f"({trend_arrow} {abs(total_growth):.1f}% vs LY)</span></div>",
                    unsafe_allow_html=True,
                )

            with filter_col:
                trend_type = st.segmented_control(
                    "P&L trend period",
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    default="Monthly",
                    label_visibility="collapsed",
                    key="pnl_trend_type",
                ) or "Monthly"

            trend_df = build_pnl_yoy_trend(
                df, prev_df, trend_type, "grdt", start_date, prev_start
            )
            trend_df["Current P&L"] = pd.to_numeric(
                trend_df["PNL"], errors="coerce"
            ).fillna(0) / divisor
            trend_df["Previous P&L"] = pd.to_numeric(
                trend_df["PY_PNL"], errors="coerce"
            ).fillna(0) / divisor
            trend_df["Growth %"] = trend_df.apply(
                lambda r: pct_change(r["Current P&L"], r["Previous P&L"]),
                axis=1,
            )
            trend_df["Growth Label"] = trend_df["Growth %"].apply(
                lambda value: f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"
            )

            fig_yoy = go.Figure()
            fig_yoy.add_trace(
                go.Bar(
                    x=trend_df["Period"],
                    y=trend_df["Previous P&L"],
                    name=f"LY ({prev_fy})",
                    marker=dict(
                        color="#cbd5e1",
                        line=dict(color="#94a3b8", width=1.3),
                    ),
                    text=trend_df["Previous P&L"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#475569", family="Arial"),
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>LY P&L: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )
            fig_yoy.add_trace(
                go.Bar(
                    x=trend_df["Period"],
                    y=trend_df["Current P&L"],
                    name=f"Current ({fy})",
                    marker=dict(
                        color="#2563eb",
                        line=dict(color="#1e3a8a", width=1.3),
                    ),
                    text=trend_df["Current P&L"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#1d4ed8", family="Arial"),
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>Current P&L: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )

            all_trend_values = pd.concat(
                [
                    trend_df["Current P&L"].abs(),
                    trend_df["Previous P&L"].abs(),
                ],
                ignore_index=True,
            )
            trend_max = all_trend_values.max()
            trend_max = trend_max if pd.notna(trend_max) and trend_max > 0 else 1

            if len(trend_df) <= 40:
                for _, trend_row in trend_df.iterrows():
                    growth_value = float(trend_row["Growth %"] or 0)
                    label_color = "#166534" if growth_value >= 0 else "#dc2626"
                    current_value = float(trend_row["Current P&L"] or 0)
                    previous_value = float(trend_row["Previous P&L"] or 0)
                    positive_top = max(current_value, previous_value, 0)
                    negative_bottom = min(current_value, previous_value, 0)
                    gap = trend_max * (0.24 if trend_type == "Monthly" else 0.16)
                    annotation_y = positive_top + gap if positive_top > 0 else negative_bottom - gap
                    fig_yoy.add_annotation(
                        x=trend_row["Period"],
                        y=annotation_y,
                        text=trend_row["Growth Label"],
                        showarrow=False,
                        font=dict(size=12, color=label_color, family="Arial"),
                    )

            fig_yoy.add_hline(y=0, line_color="#64748b", line_width=1)
            fig_yoy.update_layout(
                barmode="group",
                height=310,
                margin=dict(l=8, r=8, t=24, b=8),
                plot_bgcolor="#f8fafc",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    x=0,
                    font=dict(size=11),
                ),
                font=dict(size=11, family="Arial"),
                xaxis_title="",
                yaxis_title=f"P&L ({unit})",
                bargap=0.22,
                bargroupgap=0.08,
            )
            fig_yoy.update_xaxes(
                showgrid=False,
                showline=False,
                zeroline=False,
                tickfont=dict(size=11),
            )
            fig_yoy.update_yaxes(
                showgrid=False,
                showline=False,
                zeroline=False,
                tickfont=dict(size=11),
                title_font=dict(size=12),
            )
            st.plotly_chart(
                fig_yoy,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )

    with row2:
        LOAD_TITLE_FONT = 16
        LOAD_CENTER_VALUE_FONT = 19
        LOAD_CENTER_LABEL_FONT = 12
        LOAD_LABEL_FONT = 14
        LOAD_VALUE_FONT = 14
        LOAD_SUBTEXT_FONT = 12

        COMPANY_TITLE_FONT = 16
        COMPANY_NAME_FONT = 13
        COMPANY_VALUE_FONT = 13
        COMPANY_SUBTEXT_FONT = 11

        # P&L by Load Type — same Overview layout with LY arrow indicators.
        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:{LOAD_TITLE_FONT}px;font-weight:600;'
                f'color:#0f172a;margin:0 0 5px 0;line-height:1.1;">'
                f'P&L by Load Type (CY)</div>',
                unsafe_allow_html=True,
            )

            ftl = float(df.loc[df["LOADTYPE"].eq("FTL"), "PNL"].sum())
            ltl = float(df.loc[df["LOADTYPE"].eq("LTL"), "PNL"].sum())
            prev_ftl = float(
                prev_df.loc[prev_df["LOADTYPE"].eq("FTL"), "PNL"].sum()
            ) if prev_df is not None and not prev_df.empty else 0.0
            prev_ltl = float(
                prev_df.loc[prev_df["LOADTYPE"].eq("LTL"), "PNL"].sum()
            ) if prev_df is not None and not prev_df.empty else 0.0

            load_abs_total = abs(ftl) + abs(ltl)
            ftl_share = abs(ftl) / load_abs_total * 100 if load_abs_total else 0
            ltl_share = abs(ltl) / load_abs_total * 100 if load_abs_total else 0
            ftl_yoy = pct_change(ftl, prev_ftl)
            ltl_yoy = pct_change(ltl, prev_ltl)

            load_chart_col, load_legend_col = st.columns(
                [0.80, 1.20],
                gap="small",
                vertical_alignment="center",
            )

            with load_chart_col:
                fig_load = go.Figure(
                    data=[
                        go.Pie(
                            labels=["FTL", "LTL"],
                            values=[abs(ftl), abs(ltl)],
                            customdata=[ftl / divisor, ltl / divisor],
                            hole=0.66,
                            sort=False,
                            rotation=0,
                            direction="clockwise",
                            marker=dict(
                                colors=["#2563eb", "#0f766e"],
                                line=dict(color="#ffffff", width=1.5),
                            ),
                            textinfo="none",
                            hovertemplate=(
                                "<b>%{label}</b><br>"
                                f"P&L: ₹%{{customdata:.2f}} {unit}<br>"
                                "Share: %{percent}<extra></extra>"
                            ),
                        )
                    ]
                )
                fig_load.update_layout(
                    height=165,
                    margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    annotations=[
                        dict(
                            x=0.5,
                            y=0.55,
                            text=f"<b>₹{(ftl + ltl) / divisor:.2f} {unit}</b>",
                            showarrow=False,
                            font=dict(
                                size=LOAD_CENTER_VALUE_FONT,
                                color="#0f172a",
                                family="Arial",
                            ),
                        ),
                        dict(
                            x=0.5,
                            y=0.39,
                            text="Total P&L",
                            showarrow=False,
                            font=dict(
                                size=LOAD_CENTER_LABEL_FONT,
                                color="#64748b",
                                family="Arial",
                            ),
                        ),
                    ],
                )
                st.plotly_chart(
                    fig_load,
                    width="stretch",
                    config={"displayModeBar": False, "responsive": True},
                )

            with load_legend_col:
                def _load_row(label, value, share, py_value, growth, dot_color):
                    growth_color = "#16a34a" if growth >= 0 else "#dc2626"
                    growth_arrow = "▲" if growth >= 0 else "▼"
                    value_color = "#0f172a" if value >= 0 else "#dc2626"
                    return (
                        '<div style="display:grid;'
                        'grid-template-columns:13px minmax(40px,.75fr) minmax(84px,auto) minmax(48px,auto);'
                        'align-items:center;gap:8px;">'
                        f'<span style="width:11px;height:11px;border-radius:50%;background:{dot_color};display:inline-block;"></span>'
                        f'<span style="font-size:{LOAD_LABEL_FONT}px;font-weight:600;color:#334155;">{label}</span>'
                        f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;color:{value_color};white-space:nowrap;">'
                        f'₹{value / divisor:.2f} {unit}</span>'
                        f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;color:#334155;white-space:nowrap;text-align:right;">'
                        f'{share:.1f}%</span>'
                        f'<span style="grid-column:2/5;font-size:{LOAD_SUBTEXT_FONT}px;color:#64748b;white-space:nowrap;">'
                        f'LY ₹{py_value / divisor:.2f} {unit} · '
                        f'<span style="color:{growth_color};font-weight:700;">'
                        f'{growth_arrow} {abs(growth):.1f}%</span></span>'
                        '</div>'
                    )

                load_legend_html = (
                    '<div style="display:flex;flex-direction:column;gap:15px;padding:4px 0;line-height:1.2;">'
                    + _load_row("FTL", ftl, ftl_share, prev_ftl, ftl_yoy, "#2563eb")
                    + _load_row("LTL", ltl, ltl_share, prev_ltl, ltl_yoy, "#0f766e")
                    + '</div>'
                )
                if hasattr(st, "html"):
                    st.html(load_legend_html)
                else:
                    st.markdown(load_legend_html, unsafe_allow_html=True)

        # P&L by Company — same Overview layout with LY arrow indicators.
        company_df = (
            df.groupby("COMPNAME", dropna=False)["PNL"]
            .sum()
            .reset_index()
            .rename(columns={"COMPNAME": "Company", "PNL": "CY PNL"})
        )
        company_df["Company"] = company_df["Company"].fillna("Unknown").astype(str)

        if prev_df is not None and not prev_df.empty and "COMPNAME" in prev_df.columns:
            prev_company_df = (
                prev_df.groupby("COMPNAME", dropna=False)["PNL"]
                .sum()
                .reset_index()
                .rename(columns={"COMPNAME": "Company", "PNL": "PY PNL"})
            )
            prev_company_df["Company"] = (
                prev_company_df["Company"].fillna("Unknown").astype(str)
            )
        else:
            prev_company_df = pd.DataFrame(columns=["Company", "PY PNL"])

        company_df = company_df.merge(prev_company_df, on="Company", how="left")
        company_df["PY PNL"] = pd.to_numeric(
            company_df["PY PNL"], errors="coerce"
        ).fillna(0)
        company_df["P&L Display"] = company_df["CY PNL"] / divisor
        company_df["PY P&L Display"] = company_df["PY PNL"] / divisor
        company_abs_total = company_df["CY PNL"].abs().sum()
        company_df["Contribution %"] = (
            company_df["CY PNL"].abs() / company_abs_total * 100
            if company_abs_total
            else 0
        )
        company_df["Growth %"] = company_df.apply(
            lambda row: pct_change(row["CY PNL"], row["PY PNL"]),
            axis=1,
        )
        company_df = company_df.sort_values(
            "CY PNL", ascending=False
        ).reset_index(drop=True)
        company_chart_df = company_df.head(6).copy()

        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:{COMPANY_TITLE_FONT}px;font-weight:600;'
                f'color:#0f172a;margin:0 0 7px 0;line-height:1.2;">'
                f'P&L by Company (CY)</div>',
                unsafe_allow_html=True,
            )

            if company_chart_df.empty:
                st.info("No company P&L is available for the selected filters.")
            else:
                company_colors = [
                    "#2563eb", "#0f9f8f", "#7c3aed",
                    "#f59e0b", "#ec4899", "#64748b",
                ]
                max_company_value = float(company_chart_df["CY PNL"].abs().max() or 1)
                company_rows = []

                for idx, company_row in company_chart_df.iterrows():
                    company_name = escape(str(company_row["Company"]))
                    raw_value = float(company_row["CY PNL"] or 0)
                    value = float(company_row["P&L Display"] or 0)
                    share = float(company_row["Contribution %"] or 0)
                    py_value = float(company_row["PY P&L Display"] or 0)
                    growth = float(company_row["Growth %"] or 0)
                    width_pct = min(abs(raw_value) / max_company_value * 100, 100)
                    color = company_colors[idx % len(company_colors)]
                    growth_color = "#16a34a" if growth >= 0 else "#dc2626"
                    growth_arrow = "▲" if growth >= 0 else "▼"
                    value_color = "#0f172a" if raw_value >= 0 else "#dc2626"
                    bar_color = color if raw_value >= 0 else "#dc2626"

                    company_rows.append(
                        f'<div title="{company_name} | LY ₹{py_value:.2f} {unit} | {growth_arrow} {abs(growth):.1f}%" '
                        f'style="display:grid;grid-template-columns:minmax(150px,195px) minmax(55px,1fr) '
                        f'minmax(84px,auto) minmax(58px,auto);align-items:center;gap:8px;margin:9px 0;line-height:1.2;">'
                        f'<div style="font-size:{COMPANY_NAME_FONT}px;font-weight:600;color:#334155;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{company_name}</div>'
                        f'<div style="height:9px;background:#e8eef5;border-radius:999px;overflow:hidden;box-shadow:inset 0 1px 2px rgba(15,23,42,.10);">'
                        f'<div style="height:9px;width:{width_pct:.2f}%;background:{bar_color};border-radius:999px;"></div></div>'
                        f'<div style="font-size:{COMPANY_VALUE_FONT}px;font-weight:700;color:{value_color};white-space:nowrap;">₹{value:.2f} {unit}</div>'
                        f'<div style="font-size:{COMPANY_VALUE_FONT}px;font-weight:700;color:#334155;min-width:54px;text-align:right;white-space:nowrap;">{share:.2f}%</div>'
                        f'<div style="grid-column:2/5;margin-top:-3px;font-size:{COMPANY_SUBTEXT_FONT}px;color:#64748b;white-space:nowrap;">'
                        f'LY ₹{py_value:.2f} {unit} · <span style="color:{growth_color};font-weight:700;">'
                        f'{growth_arrow} {abs(growth):.1f}%</span></div></div>'
                    )

                company_html = (
                    '<div style="padding:0 3px 4px 3px;">'
                    + ''.join(company_rows)
                    + '</div>'
                )
                if hasattr(st, "html"):
                    st.html(company_html)
                else:
                    st.markdown(company_html, unsafe_allow_html=True)

    # =====================================================
    # Month-on-Month P&L and Growth
    # =====================================================
    st.markdown("<div aria-hidden='true' style='height:4px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            "<div style='font-size:16px;font-weight:400;color:#0f2744;margin:1px 0 7px 2px;'>"
            "Month on Month P&L & Growth</div>",
            unsafe_allow_html=True,
        )

        mom_df = (
            df.groupby("Month", observed=False, as_index=False)["PNL"]
            .sum()
        )
        mom_df["Month"] = pd.Categorical(
            mom_df["Month"], categories=MONTH_ORDER, ordered=True
        )
        mom_df = mom_df.sort_values("Month").reset_index(drop=True)
        mom_df["P&L Display"] = mom_df["PNL"] / divisor
        mom_df["MoM Growth"] = mom_df["PNL"].pct_change() * 100
        mom_df["Growth Label"] = mom_df["MoM Growth"].apply(
            lambda value: (
                f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"
                if pd.notna(value) else ""
            )
        )

        if mom_df.empty:
            st.info("No monthly P&L data is available for the selected filters.")
        else:
            bar_colors = [
                "#2563eb" if value >= 0 else "#dc2626"
                for value in mom_df["P&L Display"]
            ]
            growth_colors = [
                "#16a34a" if pd.notna(value) and value >= 0 else "#dc2626"
                for value in mom_df["MoM Growth"]
            ]

            fig_mom = go.Figure()
            fig_mom.add_trace(
                go.Bar(
                    x=mom_df["Month"],
                    y=mom_df["P&L Display"],
                    name="P&L",
                    marker=dict(
                        color=bar_colors,
                        line=dict(color="#1e40af", width=1.1),
                    ),
                    text=mom_df["P&L Display"],
                    texttemplate=f"₹%{{text:.2f}} {unit}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>P&L: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )
            fig_mom.add_trace(
                go.Scatter(
                    x=mom_df["Month"],
                    y=mom_df["MoM Growth"],
                    name="MoM Growth",
                    mode="lines+markers+text",
                    yaxis="y2",
                    line=dict(color="#f59e0b", width=3),
                    marker=dict(
                        size=9,
                        color=growth_colors,
                        line=dict(color="#ffffff", width=2),
                    ),
                    text=mom_df["Growth Label"],
                    textposition="top center",
                    textfont=dict(size=11, color="#334155"),
                    connectgaps=False,
                    hovertemplate=(
                        "<b>%{x}</b><br>MoM Growth: %{y:.1f}%<extra></extra>"
                    ),
                )
            )

            pnl_values = mom_df["P&L Display"].dropna()
            pnl_min = float(pnl_values.min()) if not pnl_values.empty else 0.0
            pnl_max = float(pnl_values.max()) if not pnl_values.empty else 0.0
            pnl_span = max(abs(pnl_min), abs(pnl_max), 1.0)

            growth_values = mom_df["MoM Growth"].dropna()
            if growth_values.empty:
                growth_range = [-100, 100]
            else:
                growth_min = float(growth_values.min())
                growth_max = float(growth_values.max())
                growth_padding = max((growth_max - growth_min) * 0.25, 15.0)
                growth_range = [growth_min - growth_padding, growth_max + growth_padding]

            fig_mom.add_hline(y=0, line_color="#94a3b8", line_width=1)
            fig_mom.update_layout(
                height=330,
                margin=dict(l=10, r=12, t=20, b=8),
                plot_bgcolor="#f8fafc",
                paper_bgcolor="rgba(0,0,0,0)",
                bargap=0.34,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    x=0.01,
                    font=dict(size=11),
                ),
                xaxis=dict(
                    title="", showgrid=False, zeroline=False, tickfont=dict(size=11)
                ),
                yaxis=dict(
                    title=dict(text=f"P&L ({unit})", font=dict(size=12)),
                    showgrid=False,
                    zeroline=False,
                    range=[min(pnl_min - pnl_span * 0.18, 0), max(pnl_max + pnl_span * 0.28, 0)],
                    tickfont=dict(size=11),
                ),
                yaxis2=dict(
                    title=dict(text="Growth (%)", font=dict(size=12)),
                    overlaying="y",
                    side="right",
                    showgrid=False,
                    zeroline=False,
                    range=growth_range,
                    ticksuffix="%",
                    tickfont=dict(size=11),
                ),
            )

            st.plotly_chart(
                fig_mom,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )

    st.markdown("<div aria-hidden='true' style='height:4px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("###### P&L by Zone")
        zone_df = df.groupby("zone", as_index=False)["PNL"].sum().sort_values("PNL", ascending=False)
        zone_df["Display"] = zone_df["PNL"] / divisor; zone_df["Pct"] = (zone_df["PNL"].abs()/zone_df["PNL"].abs().sum()*100 if zone_df["PNL"].abs().sum() else 0)
        colors=["#1565C0","#009688","#FB8C00","#7E57C2","#EC407A","#EF5350","#334155"]
        fig_zone=go.Figure(go.Pie(labels=zone_df["zone"], values=zone_df["PNL"].abs(), customdata=zone_df[["Display","Pct"]], hole=.62, sort=False, domain=dict(x=[0,.60],y=[0,1]), marker=dict(colors=colors[:len(zone_df)],line=dict(color="#fff",width=2)), textinfo="none", hovertemplate=f"<b>%{{label}}</b><br>P&L: ₹%{{customdata[0]:.2f}} {unit}<br>Contribution: %{{customdata[1]:.1f}}%<extra></extra>"))
        for idx,row in zone_df.reset_index(drop=True).iterrows():
            y=.91-idx*(.145 if len(zone_df)<=6 else .105); color=colors[idx%len(colors)]
            fig_zone.add_annotation(x=.625,y=y,xref="paper",yref="paper",text="●",showarrow=False,xanchor="left",font=dict(size=16,color=color))
            fig_zone.add_annotation(x=.675,y=y,xref="paper",yref="paper",text=f"<b>{escape(str(row['zone']))}</b><br>₹{row['Display']:.2f} {unit} <span style='color:{color}'>({row['Pct']:.1f}%)</span>",showarrow=False,xanchor="left",align="left")
        fig_zone.add_annotation(x=.30,y=.50,xref="paper",yref="paper",text=f"<b>₹{zone_df['Display'].sum():.2f} {unit}</b><br><span style='font-size:10px'>Net P&L</span>",showarrow=False)
        fig_zone.update_layout(height=310,margin=dict(l=0,r=0,t=4,b=0),showlegend=False,paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_zone,width="stretch",config={"displayModeBar":False,"responsive":True})

    st.markdown("<div aria-hidden='true' style='height:4px'></div>", unsafe_allow_html=True)
    if view_type == "Origin" and "COUNTRY" in df.columns:
        with st.container(border=True):
            st.markdown(
                "<div style='display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 0 8px 2px;'>"
                "<div style='font-size:15px;font-weight:500;color:#0f2744;'>Zone-wise Country P&L</div>"
                "<div style='display:flex;gap:14px;flex-wrap:wrap;font-size:10px;'>"
                "<span style='color:#1d4ed8;'>■ Current Year</span>"
                "<span style='color:#0f766e;'>■ Last Year</span>"
                "<span style='color:#6d28d9;'>■ YoY Comparison</span>"
                "</div></div>",
                unsafe_allow_html=True,
            )

            zone_country_pnl = (
                df.groupby(["zone", "COUNTRY"], dropna=False)["PNL"]
                .sum()
                .reset_index()
            )
            zone_country_pnl["P&L Display"] = zone_country_pnl["PNL"] / divisor
            current_matrix = zone_country_pnl.pivot(
                index="zone", columns="COUNTRY", values="P&L Display"
            ).fillna(0)
            current_matrix["Total"] = current_matrix.sum(axis=1)
            current_matrix = current_matrix.sort_values("Total", ascending=False)
            if (
                prev_df is not None
                and not prev_df.empty
                and {"zone", "COUNTRY", "PNL"}.issubset(prev_df.columns)
            ):
                prev_zone_country_pnl = (
                    prev_df.groupby(["zone", "COUNTRY"], dropna=False)["PNL"]
                    .sum()
                    .reset_index()
                )
                prev_zone_country_pnl["P&L Display"] = prev_zone_country_pnl["PNL"] / divisor
                previous_matrix = prev_zone_country_pnl.pivot(
                    index="zone", columns="COUNTRY", values="P&L Display"
                ).fillna(0)
                previous_matrix["Total"] = previous_matrix.sum(axis=1)
            else:
                previous_matrix = pd.DataFrame()

            zone_colors = {
                "NORTH ZONE": "#1565C0", "WEST ZONE": "#009688",
                "SOUTH ZONE": "#FB8C00", "EAST ZONE": "#7E57C2",
                "NORTH EAST ZONE": "#EC407A", "NEPAL ZONE": "#EF5350",
                "North Zone": "#1565C0", "West Zone": "#009688",
                "South Zone": "#FB8C00", "East Zone": "#7E57C2",
                "North East Zone": "#EC407A", "Nepal Zone": "#EF5350",
            }

            zone_name_map = {
                "NORTH ZONE": "North", "WEST ZONE": "West", "SOUTH ZONE": "South",
                "EAST ZONE": "East", "NORTH EAST ZONE": "NE", "NEPAL ZONE": "Nepal",
            }

            country_cols = sorted(
                set(col for col in current_matrix.columns if col != "Total")
                | set(col for col in previous_matrix.columns if col != "Total")
            )
            zone_order = list(current_matrix.index)
            for zone_key in previous_matrix.index:
                if zone_key not in zone_order:
                    zone_order.append(zone_key)

            current_matrix = current_matrix.reindex(index=zone_order, columns=country_cols + ["Total"], fill_value=0)
            previous_matrix = previous_matrix.reindex(index=zone_order, columns=country_cols + ["Total"], fill_value=0)

            current_grand_total = float(current_matrix[country_cols].to_numpy().sum()) if country_cols else 0.0
            previous_grand_total = float(previous_matrix[country_cols].to_numpy().sum()) if country_cols else 0.0

            def _safe_growth(current_value, previous_value):
                if previous_value:
                    return ((current_value - previous_value) / previous_value) * 100
                return 100.0 if current_value else 0.0

            def _growth_html(growth_value, suffix="%"):
                positive = growth_value >= 0
                color = "#16a34a" if positive else "#dc2626"
                arrow = "▲" if positive else "▼"
                return f'<span style="color:{color};font-weight:600;white-space:nowrap;">{arrow} {abs(growth_value):.2f}{suffix}</span>'

            header_groups = [f'<th class="country-group" colspan="3">{escape(str(country))}</th>' for country in country_cols]
            header_groups.append('<th class="country-group total-group" colspan="3">TOTAL</th>')
            sub_headers = ''.join(
                '<th class="cy-head">CY</th><th class="ly-head">LY</th><th class="yoy-head">YoY %</th>'
                for _ in range(len(country_cols) + 1)
            )

            body_rows = []
            for zone_key in zone_order:
                display_zone = zone_name_map.get(zone_key, str(zone_key).title())
                zone_color = zone_colors.get(zone_key, "#2563eb")
                revenue_cells, share_cells = [], []

                for country in country_cols:
                    cy = float(current_matrix.at[zone_key, country] or 0)
                    ly = float(previous_matrix.at[zone_key, country] or 0)
                    growth = _safe_growth(cy, ly)
                    cy_share = (cy / current_grand_total * 100) if current_grand_total else 0.0
                    ly_share = (ly / previous_grand_total * 100) if previous_grand_total else 0.0
                    share_change = cy_share - ly_share
                    revenue_cells.extend([
                        f'<td class="num cy-cell">{cy:.2f}</td>',
                        f'<td class="num ly-cell">{ly:.2f}</td>',
                        f'<td class="num yoy-cell">{_growth_html(growth)}</td>',
                    ])
                    share_cells.extend([
                        f'<td class="num cy-share">{cy_share:.2f}%</td>',
                        f'<td class="num ly-share">{ly_share:.2f}%</td>',
                        f'<td class="num yoy-cell">{_growth_html(share_change, " pp")}</td>',
                    ])

                zone_cy_total = float(current_matrix.loc[zone_key, country_cols].sum()) if country_cols else 0.0
                zone_ly_total = float(previous_matrix.loc[zone_key, country_cols].sum()) if country_cols else 0.0
                zone_growth = _safe_growth(zone_cy_total, zone_ly_total)
                zone_cy_share = (zone_cy_total / current_grand_total * 100) if current_grand_total else 0.0
                zone_ly_share = (zone_ly_total / previous_grand_total * 100) if previous_grand_total else 0.0
                zone_share_change = zone_cy_share - zone_ly_share
                revenue_cells.extend([
                    f'<td class="num total-cell cy-cell">{zone_cy_total:.2f}</td>',
                    f'<td class="num total-cell ly-cell">{zone_ly_total:.2f}</td>',
                    f'<td class="num total-cell yoy-cell">{_growth_html(zone_growth)}</td>',
                ])
                share_cells.extend([
                    f'<td class="num total-cell cy-share">{zone_cy_share:.2f}%</td>',
                    f'<td class="num total-cell ly-share">{zone_ly_share:.2f}%</td>',
                    f'<td class="num total-cell yoy-cell">{_growth_html(zone_share_change, " pp")}</td>',
                ])
                body_rows.append(
                    '<tr class="zone-revenue-row">'
                    f'<td class="zone-name" rowspan="2" style="border-left:4px solid {zone_color};">{escape(display_zone)}</td>'
                    '<td class="metric-name">P&L</td>' + ''.join(revenue_cells) + '</tr>'
                    '<tr class="zone-share-row"><td class="metric-name">% Share</td>' + ''.join(share_cells) + '</tr>'
                )

            grand_revenue_cells, grand_share_cells = [], []
            for country in country_cols:
                cy = float(current_matrix[country].sum())
                ly = float(previous_matrix[country].sum())
                growth = _safe_growth(cy, ly)
                cy_share = (cy / current_grand_total * 100) if current_grand_total else 0.0
                ly_share = (ly / previous_grand_total * 100) if previous_grand_total else 0.0
                share_change = cy_share - ly_share
                grand_revenue_cells.extend([
                    f'<td class="num cy-cell">{cy:.2f}</td>',
                    f'<td class="num ly-cell">{ly:.2f}</td>',
                    f'<td class="num yoy-cell">{_growth_html(growth)}</td>',
                ])
                grand_share_cells.extend([
                    f'<td class="num cy-share">{cy_share:.2f}%</td>',
                    f'<td class="num ly-share">{ly_share:.2f}%</td>',
                    f'<td class="num yoy-cell">{_growth_html(share_change, " pp")}</td>',
                ])

            grand_growth = _safe_growth(current_grand_total, previous_grand_total)
            grand_revenue_cells.extend([
                f'<td class="num total-cell cy-cell">{current_grand_total:.2f}</td>',
                f'<td class="num total-cell ly-cell">{previous_grand_total:.2f}</td>',
                f'<td class="num total-cell yoy-cell">{_growth_html(grand_growth)}</td>',
            ])
            grand_share_cells.extend([
                '<td class="num total-cell cy-share">100.00%</td>',
                '<td class="num total-cell ly-share">100.00%</td>',
                '<td class="num total-cell yoy-cell">—</td>',
            ])
            total_rows = (
                '<tr class="grand-total-row"><td class="zone-name" rowspan="2">TOTAL</td><td class="metric-name">P&L</td>'
                + ''.join(grand_revenue_cells) + '</tr>'
                '<tr class="grand-total-row"><td class="metric-name">% Share</td>'
                + ''.join(grand_share_cells) + '</tr>'
            )

            dynamic_font = "9px" if len(country_cols) >= 5 else "10px"
            matrix_html = f"""
            <style>
                .compact-zone-matrix-wrap {{width:100%;overflow:visible;border:1px solid #dbe4ef;border-radius:10px;background:#ffffff;}}
                .compact-zone-matrix {{width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;font-family:'Segoe UI',Arial,sans-serif;font-size:{dynamic_font};color:#243b53;}}
                .compact-zone-matrix th,.compact-zone-matrix td {{padding:5px 3px;border-right:1px solid #cbd5e1;border-bottom:1px solid #cbd5e1;text-align:center;line-height:1.15;overflow:hidden;text-overflow:ellipsis;}}
                /* Light separators around every country group (CY / LY / YoY). */
                .compact-zone-matrix .country-group {{border-left:1px solid #94a3b8!important;border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix thead tr:nth-child(2) th:nth-child(3n+1) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix thead tr:nth-child(2) th:nth-child(3n) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-revenue-row td:nth-child(3n+3) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-revenue-row td:nth-child(3n+2) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-share-row td:nth-child(3n+2) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-share-row td:nth-child(3n+1) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:first-of-type td:nth-child(3n+3) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:first-of-type td:nth-child(3n+2) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:last-of-type td:nth-child(3n+2) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:last-of-type td:nth-child(3n+1) {{border-right:1px solid #94a3b8!important;}}
                /* Light horizontal border around each two-row zone block. */
                .compact-zone-matrix .zone-revenue-row td {{border-top:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-revenue-row .zone-name {{border-bottom:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-share-row td {{border-bottom:1px solid #94a3b8!important;}}
                .compact-zone-matrix thead th {{font-weight:500;}}
                .compact-zone-matrix .zone-head {{width:7%;background:#eef4fb;text-align:left;padding-left:8px;}}
                .compact-zone-matrix .metric-head {{width:7%;background:#eef4fb;text-align:left;padding-left:7px;}}
                .compact-zone-matrix .country-group {{background:#eaf2ff;color:#0f2744;font-size:11px;border-top:3px solid #2563eb;}}
                .compact-zone-matrix .total-group {{background:#edf4ff;}}
                .compact-zone-matrix .cy-head {{background:#eff6ff;color:#1d4ed8;}}
                .compact-zone-matrix .ly-head {{background:#ecfdf8;color:#0f766e;}}
                .compact-zone-matrix .yoy-head {{background:#f7f2ff;color:#6d28d9;}}
                .compact-zone-matrix .zone-name {{text-align:left;padding-left:8px;font-size:11px;font-weight:500;background:#f8fbff;white-space:normal;}}
                .compact-zone-matrix .metric-name {{text-align:left;padding-left:7px;color:#475569;font-weight:400;background:#fbfdff;white-space:nowrap;}}
                .compact-zone-matrix .num {{white-space:nowrap;font-weight:400;}}
                .compact-zone-matrix .cy-cell,.compact-zone-matrix .cy-share {{background:#f8fbff;}}
                .compact-zone-matrix .ly-cell,.compact-zone-matrix .ly-share {{background:#f7fcfb;}}
                .compact-zone-matrix .yoy-cell {{background:#fcfaff;}}
                .compact-zone-matrix .total-cell {{font-weight:500;}}
                .compact-zone-matrix .zone-share-row td {{color:#64748b;}}
                .compact-zone-matrix .grand-total-row td {{background:#eaf2ff!important;font-weight:500;color:#0f2744;}}
                .compact-zone-matrix tr:last-child td {{border-bottom:0;}}
                .compact-zone-matrix th:last-child,.compact-zone-matrix td:last-child {{border-right:0;}}
                .zone-matrix-note {{display:flex;gap:18px;flex-wrap:wrap;margin:7px 2px 0;color:#64748b;font-size:10px;}}
                @media (max-width:1200px) {{.compact-zone-matrix {{font-size:8px;}}.compact-zone-matrix th,.compact-zone-matrix td {{padding:4px 2px;}}.compact-zone-matrix .country-group,.compact-zone-matrix .zone-name {{font-size:9px;}}}}
            </style>
            <div class="compact-zone-matrix-wrap">
                <table class="compact-zone-matrix">
                    <thead>
                        <tr><th class="zone-head" rowspan="2">Zone</th><th class="metric-head" rowspan="2">Metric</th>{''.join(header_groups)}</tr>
                        <tr>{sub_headers}</tr>
                    </thead>
                    <tbody>{''.join(body_rows)}{total_rows}</tbody>
                </table>
            </div>
            <div class="zone-matrix-note">
                <span>Values in ₹ {escape(str(unit))}</span>
                <span style="color:#16a34a;">▲ Positive movement</span>
                <span style="color:#dc2626;">▼ Negative movement</span>
                <span>YoY % = (CY − LY) ÷ LY × 100</span>
            </div>
            """
            if hasattr(st, "html"):
                st.html(matrix_html)
            else:
                st.markdown(matrix_html, unsafe_allow_html=True)

    elif view_type == "Origin":
        with st.container(border=True):
            st.info("Zone-wise Country P&L cannot be displayed because COUNTRY is missing from the P&L dataset.")

    st.markdown("<div aria-hidden='true' style='height:4px'></div>", unsafe_allow_html=True)
    customer_col = _find_column(
        df,
        ["Consignor", "consignorname", "customer", "customername"],
    )
    route_col = _find_column(df, ["Route", "routename"])
    customer_layout_col, route_layout_col = st.columns(2, gap="medium")

    with customer_layout_col:
        with st.container(border=True):
            if customer_col:
                render_top_n_pnl_table(
                    df,
                    prev_df,
                    customer_col,
                    "Customers",
                    unit,
                    divisor,
                    "pnl_customer",
                    subtitle=(
                        "Customer basis: Consignor | Current FY P&L, share and YoY movement."
                        if view_type == "Origin"
                        else "Customer basis: Consignee | Current FY P&L, share and YoY movement."
                    ),
                )
            else:
                st.info("Customer column not found.")

    with route_layout_col:
        with st.container(border=True):
            if route_col:
                render_top_n_pnl_table(
                    df,
                    prev_df,
                    route_col,
                    "Routes",
                    unit,
                    divisor,
                    "pnl_route",
                    subtitle=(
                        "Origin → Destination | Current FY P&L, share and YoY movement."
                        if view_type == "Origin"
                        else "Destination → Origin | Current FY P&L, share and YoY movement."
                    ),
                )
            else:
                st.info("Route column not found.")

    st.markdown("<div aria-hidden='true' style='height:4px'></div>", unsafe_allow_html=True)

    # Reusable summaries for the branch section and detail tabs.
    branch_summary = build_group_summary(df, prev_df, "branch")
    monthly = build_monthly_comparison(df, prev_df, divisor)

    with st.container(border=True):
        st.markdown(
            "<div style='font-size:16px;font-weight:400;color:#0f2744;margin:1px 0 7px 2px;'>"
            "Branches by P&amp;L</div>",
            unsafe_allow_html=True,
        )

        branch_options = [
            "All",
            "Loss",
            "₹0–5 Lac",
            "₹5–10 Lac",
            "₹10–15 Lac",
            "₹15–25 Lac",
            "₹25–50 Lac",
            "₹50 Lac & Above",
        ]
        selected_branch_slab = st.segmented_control(
            "Branch P&L slab",
            branch_options,
            default="All",
            key="top_branch_pnl_slab",
            label_visibility="collapsed",
            width="stretch",
        ) or "All"

        slab_ranges = {
            "All": (None, None),
            "Loss": (None, 0),
            "₹0–5 Lac": (0, 500_000),
            "₹5–10 Lac": (500_000, 1_000_000),
            "₹10–15 Lac": (1_000_000, 1_500_000),
            "₹15–25 Lac": (1_500_000, 2_500_000),
            "₹25–50 Lac": (2_500_000, 5_000_000),
            "₹50 Lac & Above": (5_000_000, None),
        }

        all_branch_pnl = (
            df.groupby("branch", dropna=False, as_index=False)["PNL"]
            .sum()
            .sort_values("PNL", ascending=False)
            .reset_index(drop=True)
        )
        all_branch_pnl["branch"] = (
            all_branch_pnl["branch"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
        )

        selected_branch_pnl = all_branch_pnl.copy()
        slab_low, slab_high = slab_ranges[selected_branch_slab]

        if selected_branch_slab == "Loss":
            selected_branch_pnl = selected_branch_pnl[selected_branch_pnl["PNL"] < 0]
        else:
            if slab_low is not None:
                selected_branch_pnl = selected_branch_pnl[selected_branch_pnl["PNL"] >= slab_low]
            if slab_high is not None:
                selected_branch_pnl = selected_branch_pnl[selected_branch_pnl["PNL"] < slab_high]

        selected_branch_pnl = selected_branch_pnl.sort_values(
            "PNL", ascending=False
        ).reset_index(drop=True)

        total_branch_pnl = float(all_branch_pnl["PNL"].sum())
        selected_pnl_total = float(selected_branch_pnl["PNL"].sum())
        selected_share = (
            selected_pnl_total / total_branch_pnl * 100
            if total_branch_pnl
            else 0.0
        )

        st.markdown(
            f'<div style="color:#2563eb;font-size:12px;font-weight:500;'
            f'margin:7px 0 8px 1px;">'
            f'Showing {len(selected_branch_pnl):,} branches in {escape(selected_branch_slab)}. '
            f'Selected P&amp;L: ₹{selected_pnl_total / divisor:,.2f} {escape(unit)} '
            f'({selected_share:.2f}% of total branch P&amp;L). Scroll to view all.'
            f'</div>',
            unsafe_allow_html=True,
        )

        if selected_branch_pnl.empty:
            st.info(f"No branch falls in the {selected_branch_slab} P&L slab.")
        else:
            max_abs_pnl = float(selected_branch_pnl["PNL"].abs().max()) or 1.0
            branch_rows = []

            for index, branch_row in selected_branch_pnl.iterrows():
                branch_value = float(branch_row["PNL"] or 0)
                width_pct = min(abs(branch_value) / max_abs_pnl * 100, 100)
                fill_color = "#22c55e" if branch_value >= 0 else "#dc2626"
                amount_color = "#111827" if branch_value >= 0 else "#dc2626"
                rank = index + 1
                branch_name = escape(str(branch_row["branch"]))

                branch_rows.append(
                    f'<div style="margin-bottom:7px;padding:8px 10px;'
                    f'border:1px solid #dbe4ef;border-radius:12px;background:#f8fbff;">'
                    f'<div style="display:grid;'
                    f'grid-template-columns:34px minmax(190px,310px) minmax(120px,1fr) 115px;'
                    f'align-items:center;gap:10px;">'
                    f'<div style="text-align:center;font-size:13px;color:#334155;">{rank}</div>'
                    f'<div style="font-size:14px;color:#0f2744;white-space:nowrap;'
                    f'overflow:hidden;text-overflow:ellipsis;">{branch_name}</div>'
                    f'<div style="height:7px;background:#e2e8f0;border-radius:999px;'
                    f'overflow:hidden;box-shadow:inset 0 1px 2px rgba(15,23,42,.08);">'
                    f'<div style="width:{width_pct:.1f}%;height:7px;background:{fill_color};'
                    f'border-radius:999px;"></div></div>'
                    f'<div style="text-align:right;color:{amount_color};font-size:13px;'
                    f'font-weight:600;white-space:nowrap;">'
                    f'₹{branch_value / divisor:,.2f} {escape(unit)}</div>'
                    f'</div></div>'
                )

            branch_html = (
                '<div style="max-height:430px;overflow-y:auto;padding-right:3px;">'
                + "".join(branch_rows)
                + "</div>"
            )
            if hasattr(st, "html"):
                st.html(branch_html)
            else:
                st.markdown(branch_html, unsafe_allow_html=True)

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
                "LOADTYPE", "Consignor", "Consignee", "Route", "REVENUE",
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
