import io
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import load_booking_data_pair, get_date_range


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

    start_date, end_date = get_date_range(fy)
    prev_fy = get_previous_fy(fy)
    prev_start, prev_end = get_date_range(prev_fy)

    with st.spinner("Loading P&L data..."):
        raw_df, raw_prev_df = load_booking_data_pair(
            start_date, end_date, prev_start, prev_end, view_type.lower()
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

    # Reconciliation warning only; SP PNL remains source of truth
    calculated_pnl = float(df["REVENUE"].sum() - df["EXPENSE"].sum())
    variance = float(df["PNL"].sum() - calculated_pnl)
    tolerance = max(1.0, abs(df["PNL"].sum()) * 0.000001)
    if abs(variance) > tolerance:
        st.warning(
            f"SP reconciliation difference: PNL column differs from Revenue - Expense by {amount_text(variance, conversion_type)}. "
            "Dashboard is using the SP PNL column as the source of truth."
        )

    # Row 1: monthly P&L trend + revenue/expense
    monthly = build_monthly_comparison(df, prev_df, divisor)
    left, right = st.columns([1.35, 1], gap="small")

    with left:
        with st.container(border=True):
            st.markdown('<div class="section-title">Monthly P&L: Current FY vs LY</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly["Month"], y=monthly["PY_PNL"], name=f"LY ({prev_fy})",
                marker_color="#cbd5e1", text=monthly["PY_PNL"], texttemplate="%{text:.2f}", textposition="outside",
            ))
            fig.add_trace(go.Bar(
                x=monthly["Month"], y=monthly["PNL"], name=f"Current ({fy})",
                marker_color="#16a34a", text=monthly["PNL"], texttemplate="%{text:.2f}", textposition="outside",
            ))
            fig.add_hline(y=0, line_color="#64748b", line_width=1)
            fig.update_layout(
                barmode="group", height=325, margin=dict(l=5, r=5, t=20, b=5),
                plot_bgcolor="#f8fafc", paper_bgcolor="rgba(0,0,0,0)",
                yaxis_title=f"P&L ({unit})", xaxis_title="",
                legend=dict(orientation="h", y=1.08, x=0),
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with right:
        with st.container(border=True):
            st.markdown('<div class="section-title">Monthly Revenue vs Expense</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly["Month"], y=monthly["Revenue"], name="Revenue", marker_color="#2563eb"))
            fig.add_trace(go.Bar(x=monthly["Month"], y=monthly["Expense"], name="Expense", marker_color="#dc2626"))
            fig.add_trace(go.Scatter(
                x=monthly["Month"], y=monthly["PNL"], name="P&L", mode="lines+markers",
                line=dict(color="#16a34a", width=3), marker=dict(size=7),
            ))
            fig.update_layout(
                barmode="group", height=325, margin=dict(l=5, r=5, t=20, b=5),
                plot_bgcolor="#f8fafc", paper_bgcolor="rgba(0,0,0,0)",
                yaxis_title=f"Amount ({unit})", xaxis_title="",
                legend=dict(orientation="h", y=1.08, x=0),
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # Row 2: Company, Zone, Load Type
    c1, c2, c3 = st.columns(3, gap="small")
    summaries = [
        (c1, "COMPNAME", "Company-wise P&L", 10),
        (c2, "zone", "Zone-wise P&L", 10),
        (c3, "LOADTYPE", "Load Type-wise P&L", 10),
    ]
    for container_col, group_col, title, top_n in summaries:
        with container_col:
            with st.container(border=True):
                st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
                summary = build_group_summary(df, prev_df, group_col).nlargest(top_n, "PNL").sort_values("PNL")
                summary["PNL Display"] = summary["PNL"] / divisor
                fig = px.bar(
                    summary, x="PNL Display", y=group_col, orientation="h", text="PNL Display",
                    color="Margin %", color_continuous_scale="RdYlGn",
                    hover_data={"Revenue": ":,.0f", "Expense": ":,.0f", "Margin %": ":.2f", "Growth %": ":.1f"},
                )
                fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
                fig.add_vline(x=0, line_color="#64748b", line_width=1)
                fig.update_layout(
                    height=330, margin=dict(l=5, r=25, t=8, b=5),
                    xaxis_title=f"P&L ({unit})", yaxis_title="",
                    plot_bgcolor="#f8fafc", paper_bgcolor="rgba(0,0,0,0)",
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # Row 3: Branch profitability and loss-making branches
    branch_summary = build_group_summary(df, prev_df, "branch")
    b1, b2 = st.columns([1.25, 1], gap="small")

    with b1:
        with st.container(border=True):
            st.markdown('<div class="section-title">Top 15 Branches by P&L</div>', unsafe_allow_html=True)
            top_branches = branch_summary.nlargest(15, "PNL").sort_values("PNL")
            top_branches["PNL Display"] = top_branches["PNL"] / divisor
            fig = px.bar(
                top_branches, x="PNL Display", y="branch", orientation="h", text="PNL Display",
                color="Margin %", color_continuous_scale="Tealgrn",
            )
            fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
            fig.update_layout(
                height=430, margin=dict(l=5, r=30, t=8, b=5),
                xaxis_title=f"P&L ({unit})", yaxis_title="", coloraxis_showscale=False,
                plot_bgcolor="#f8fafc", paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with b2:
        with st.container(border=True):
            st.markdown('<div class="section-title">Top 15 Loss-Making Branches</div>', unsafe_allow_html=True)
            loss_branches = branch_summary[branch_summary["PNL"] < 0].nsmallest(15, "PNL").copy()
            if loss_branches.empty:
                st.success("No loss-making branch for selected filters.")
            else:
                loss_branches["Loss Display"] = loss_branches["PNL"] / divisor
                fig = px.bar(
                    loss_branches.sort_values("PNL", ascending=False),
                    x="Loss Display", y="branch", orientation="h", text="Loss Display",
                    color_discrete_sequence=["#dc2626"],
                )
                fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
                fig.update_layout(
                    height=430, margin=dict(l=5, r=30, t=8, b=5),
                    xaxis_title=f"P&L ({unit})", yaxis_title="",
                    plot_bgcolor="#f8fafc", paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

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
                "LOADTYPE", "Consignor", "Consignee", "Route", "REVENUE", "EXPENSE", "PNL",
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
                "REVENUE": st.column_config.NumberColumn("Revenue (₹)", format="₹%.0f"),
                "EXPENSE": st.column_config.NumberColumn("Expense (₹)", format="₹%.0f"),
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

