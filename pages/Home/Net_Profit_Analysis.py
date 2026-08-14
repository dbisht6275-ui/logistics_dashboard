from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import get_date_range
from services.net_profit_data_loader import load_net_profit_data_pair
from services.pnl_data_loader import load_pnl_sp_revenue_total
from services.net_profit_branch_mast import load_net_profit_branch_mast


# ============================================================
# NET PROFIT DASHBOARD
#
# Separate dashboard.
# Existing PNL_Analysis.py is not changed.
# ============================================================

FY_OPTIONS = [
    "Select FY",
    "2026-2027",
    "2025-2026",
    "2024-2025",
    "2023-2024",
    "2022-2023",
    "2021-2022",
    "2020-2021",
]

MONTH_ORDER = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]


# ============================================================
# HELPERS
# ============================================================

def get_previous_fy(fy):
    start_year, end_year = map(int, fy.split("-"))
    return f"{start_year - 1}-{end_year - 1}"


def get_conversion(conversion_type):
    if conversion_type == "Lac":
        return 100_000, "Lac"
    return 10_000_000, "Cr"


def amount_text(value, conversion_type):
    divisor, unit = get_conversion(conversion_type)
    return f"₹{float(value or 0) / divisor:,.2f} {unit}"


def pct_change(current, previous):
    current = float(current or 0)
    previous = float(previous or 0)

    if previous == 0:
        return 0.0

    return ((current - previous) / abs(previous)) * 100


def safe_options(df, column):
    if df is None or df.empty or column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[values.ne("")]

    return sorted(
        values.unique().tolist(),
        key=str.casefold,
    )


def _normalise_column_name(value):
    """Normalise a column heading so spaces, underscores, hyphens and case do not matter."""
    return "".join(ch for ch in str(value).casefold() if ch.isalnum())


def _find_column(df, *candidates):
    """Return the actual dataframe column matching any candidate using a tolerant header match."""
    if df is None or df.empty:
        return None

    lookup = {_normalise_column_name(col): col for col in df.columns}
    for candidate in candidates:
        found = lookup.get(_normalise_column_name(candidate))
        if found is not None:
            return found
    return None


def _attach_branch_hierarchy(df, branch_master_df):
    """Attach clean Zone/Circle values, preferring Branch Master for missing/Unknown values."""
    if df is None or df.empty:
        return df

    out = df.copy()
    branch_col = _find_column(out, "BRANCH")
    master_branch_col = _find_column(branch_master_df, "BRANCH")

    hierarchy_candidates = {
        "zone": ("zone", "ZONE", "ZONE NAME", "ZONENAME", "ZONE_NAME", "ZONE DESC", "ZONEDESC"),
        "circle": (
            "circle", "CIRCLE", "CIRCLE NAME", "CIRCLENAME", "CIRCLE_NAME",
            "CIRCLE DESC", "CIRCLEDESC", "CIRCLE DESCRIPTION", "CIRCLEDESCRIPTION"
        ),
    }

    invalid_values = {"", "unknown", "none", "nan", "na", "n/a", "null", "-"}

    for canonical, candidates in hierarchy_candidates.items():
        source_col = _find_column(out, *candidates)
        master_col = _find_column(branch_master_df, *candidates)

        # Start with the hierarchy value already present in the P&L data, if any.
        if source_col is not None:
            out[canonical] = out[source_col]
        else:
            out[canonical] = pd.NA

        # Branch Master is the authoritative fallback. This also fixes rows where
        # the source column exists but contains 'Unknown'/blank values.
        if branch_col is not None and master_branch_col is not None and master_col is not None:
            master_clean = branch_master_df[[master_branch_col, master_col]].copy()
            master_clean["_branch_key"] = master_clean[master_branch_col].map(_normalise_branch_name)
            master_clean["_hierarchy_value"] = master_clean[master_col].astype("string").str.strip()
            master_clean = master_clean[
                ~master_clean["_hierarchy_value"].fillna("").str.casefold().isin(invalid_values)
            ]

            hierarchy_map = (
                master_clean.drop_duplicates("_branch_key")
                .set_index("_branch_key")["_hierarchy_value"]
            )
            fallback = out[branch_col].map(_normalise_branch_name).map(hierarchy_map)

            current_text = out[canonical].astype("string").str.strip()
            invalid_mask = current_text.fillna("").str.casefold().isin(invalid_values)
            out.loc[invalid_mask, canonical] = fallback.loc[invalid_mask]

        # Do not expose Unknown/blank pseudo-values in the filter lists.
        current_text = out[canonical].astype("string").str.strip()
        invalid_mask = current_text.fillna("").str.casefold().isin(invalid_values)
        out.loc[invalid_mask, canonical] = pd.NA

    return out


def apply_multi_filter(df, column, selected):
    if (
        df is None
        or df.empty
        or column not in df.columns
        or not selected
    ):
        return df

    return df[df[column].isin(selected)].copy()


def _normalise_branch_name(value):
    return " ".join(str(value).strip().casefold().split())


def _filter_to_branch_scope(df, branch_names):
    if df is None or df.empty or "BRANCH" not in df.columns or not branch_names:
        return df

    allowed = {_normalise_branch_name(value) for value in branch_names}
    branch_key = df["BRANCH"].fillna("").map(_normalise_branch_name)
    return df[branch_key.isin(allowed)].copy()


def _apply_pnl_business_rule(df, all_branches):
    """
    P&L rule:
    - All branches -> Origin-view P&L only, to avoid double-counting GR-level P&L.
    - Explicit branch selection -> Origin P&L + Destination P&L.

    Business / Revenue rule:
    - Always Booking + Delivery (Origin Business + Destination Business),
      including All Branches / Select All cases.

    Overhead is deducted once in both P&L cases.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    for column in [
        "ORIGIN_PNL",
        "DESTINATION_PNL",
        "ORIGIN_BUSINESS",
        "DESTINATION_BUSINESS",
        "ORIGIN_TOTAL_INCOME",
        "DESTINATION_TOTAL_INCOME",
        "ORIGIN_DIRECT_EXPENSE",
        "DESTINATION_DIRECT_EXPENSE",
        "TOTAL EXPENSE",
    ]:
        if column not in out.columns:
            out[column] = 0.0
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)

    if all_branches:
        # Consolidated P&L must not count the same GR-level P&L twice.
        # IMPORTANT: Destination Business is intentionally retained because
        # Business / Revenue must always show Booking + Delivery.
        out["DESTINATION_PNL"] = 0.0
        out["DESTINATION_TOTAL_INCOME"] = 0.0
        out["DESTINATION_DIRECT_EXPENSE"] = 0.0

    out["BUSINESS"] = out["ORIGIN_BUSINESS"] + out["DESTINATION_BUSINESS"]
    out["TOTAL_INCOME"] = out["ORIGIN_TOTAL_INCOME"] + out["DESTINATION_TOTAL_INCOME"]
    out["DIRECT_EXPENSE"] = out["ORIGIN_DIRECT_EXPENSE"] + out["DESTINATION_DIRECT_EXPENSE"]
    out["COMBINED_PNL"] = out["ORIGIN_PNL"] + out["DESTINATION_PNL"]
    out["NET_PROFIT"] = out["COMBINED_PNL"] - out["TOTAL EXPENSE"]

    out["NET_PROFIT_MARGIN"] = 0.0
    valid_income = out["TOTAL_INCOME"].ne(0)
    out.loc[valid_income, "NET_PROFIT_MARGIN"] = (
        out.loc[valid_income, "NET_PROFIT"]
        / out.loc[valid_income, "TOTAL_INCOME"]
        * 100
    )

    return out


def calculate_kpis(df):
    if df is None or df.empty:
        return {
            "origin_pnl": 0.0,
            "destination_pnl": 0.0,
            "combined_pnl": 0.0,
            "salary": 0.0,
            "godown": 0.0,
            "overhead": 0.0,
            "claim": 0.0,
            "booking_6": 0.0,
            "destination_5": 0.0,
            "total_expense": 0.0,
            "net_profit": 0.0,
            "total_income": 0.0,
            "origin_business": 0.0,
            "destination_business": 0.0,
            "business": 0.0,
            "margin": 0.0,
        }

    values = {
        "origin_pnl": float(df["ORIGIN_PNL"].sum()),
        "destination_pnl": float(df["DESTINATION_PNL"].sum()),
        "combined_pnl": float(df["COMBINED_PNL"].sum()),
        "salary": float(df["SALARY"].sum()),
        "godown": float(df["GODOWN RENT"].sum()),
        "overhead": float(df["OVERHEAD EXPENSE"].sum()),
        "claim": float(df["CLAIM"].sum()),
        "booking_6": float(df["BOOKING 6%"].sum()) if "BOOKING 6%" in df.columns else 0.0,
        "destination_5": float(df["DESTINATION 5%"].sum()) if "DESTINATION 5%" in df.columns else 0.0,
        "total_expense": float(df["TOTAL EXPENSE"].sum()),
        "net_profit": float(df["NET_PROFIT"].sum()),
        "total_income": float(df["TOTAL_INCOME"].sum()),
        "origin_business": float(df["ORIGIN_BUSINESS"].sum()) if "ORIGIN_BUSINESS" in df.columns else 0.0,
        "destination_business": float(df["DESTINATION_BUSINESS"].sum()) if "DESTINATION_BUSINESS" in df.columns else 0.0,
        "business": float(df["BUSINESS"].sum()) if "BUSINESS" in df.columns else 0.0,
    }

    values["margin"] = (
        values["net_profit"] / values["total_income"] * 100
        if values["total_income"]
        else 0.0
    )

    return values


def _inject_css():
    st.markdown(
        """
        <style>
        :root {
            --np-navy:#102a43;
            --np-kpi-font: Arial, Helvetica, sans-serif;
            --np-blue:#2563eb;
            --np-muted:#64748b;
            --np-border:#dbe4ef;
        }

        .block-container {
            max-width:100% !important;
            padding:.45rem .8rem .9rem !important;
        }

        .np-title {
            color:var(--np-navy);
            font-size:20px;
            font-weight:850;
            letter-spacing:-.3px;
        }

        .np-subtitle {
            color:var(--np-muted);
            font-size:11px;
            margin-top:2px;
        }

        .np-card {
            min-height:92px;
            border:1px solid #dbe4ef;
            border-radius:14px;
            padding:10px 11px;
            background:linear-gradient(145deg,#ffffff,#f7faff);
            box-shadow:0 5px 14px rgba(15,42,67,.07);
        }

        .np-card-disabled {
            opacity:.52;
            background:#f1f5f9;
            box-shadow:none;
        }

        .np-card-disabled .np-card-value,
        .np-card-disabled .np-card-title,
        .np-card-disabled .np-card-footer {
            color:#94a3b8 !important;
        }

        .np-card-title {
            font-family:var(--np-kpi-font);
            font-size:11px;
            color:#334155;
            font-weight:700;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .np-card-value {
            margin-top:5px;
            font-family:var(--np-kpi-font);
            font-size:18px;
            color:#0f2744;
            font-weight:700;
            letter-spacing:0;
            white-space:nowrap;
        }

        .np-card-footer {
            margin-top:6px;
            font-family:var(--np-kpi-font);
            font-size:10px;
            font-weight:500;
            color:#64748b;
        }

        .np-overhead-strip {
            width:100%;
            min-height:72px;
            border:1px solid #e6edf5;
            border-radius:12px;
            background:#ffffff;
            box-shadow:0 4px 12px rgba(15,42,67,.06);
            display:flex;
            align-items:stretch;
            overflow:hidden;
        }

        .np-overhead-item {
            flex:1 1 0;
            min-width:0;
            padding:8px 12px;
            display:flex;
            align-items:center;
            gap:9px;
            position:relative;
        }

        .np-overhead-item:not(:last-child)::after {
            content:"";
            position:absolute;
            right:0;
            top:12px;
            bottom:12px;
            width:1px;
            background:#dfe7f0;
        }

        .np-overhead-icon {
            width:34px;
            height:34px;
            min-width:34px;
            border-radius:50%;
            background:#eaf4ff;
            display:flex;
            align-items:center;
            justify-content:center;
            color:#1677e8;
            font-size:17px;
            line-height:1;
        }

        .np-overhead-body { min-width:0; flex:1; }
        .np-overhead-title {
            font-family:var(--np-kpi-font);
            font-size:10px;
            color:#334155;
            font-weight:700;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }
        .np-overhead-value {
            margin-top:2px;
            font-family:var(--np-kpi-font);
            font-size:15px;
            color:#0f2744;
            font-weight:700;
            white-space:nowrap;
        }
        .np-overhead-footer {
            margin-top:3px;
            font-family:var(--np-kpi-font);
            font-size:9px;
            font-weight:500;
            color:#64748b;
            white-space:nowrap;
        }

        .np-positive { color:#15803d; }
        .np-negative { color:#dc2626; }

        .np-section-title {
            font-size:15px;
            color:#0f2744;
            font-weight:700;
            margin:2px 0 8px 1px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border:1px solid #dce5ef !important;
            border-radius:14px !important;
            background:#ffffff !important;
            box-shadow:0 6px 16px rgba(15,42,67,.06) !important;
        }

        [data-testid="stDataFrame"] {
            border:1px solid #e2e8f0;
            border-radius:10px;
            overflow:hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(
    title,
    current,
    previous,
    conversion_type=None,
    percent=False,
    reverse_good=False,
    disabled=False,
):
    if disabled:
        st.markdown(
            f"""
            <div class="np-card np-card-disabled">
                <div class="np-card-title">{escape(title)}</div>
                <div class="np-card-value">--</div>
                <div class="np-card-footer">Select a branch to view</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if percent:
        current_text = f"{current:,.2f}%"
        previous_text = f"{previous:,.2f}%"
        growth = current - previous
        growth_label = f"{growth:+.2f} pp"
        good = growth <= 0 if reverse_good else growth >= 0
    else:
        current_text = amount_text(current, conversion_type)
        previous_text = amount_text(previous, conversion_type)
        growth = pct_change(current, previous)
        growth_label = f"{growth:+.1f}%"
        good = growth <= 0 if reverse_good else growth >= 0

    class_name = "np-positive" if good else "np-negative"

    st.markdown(
        f"""
        <div class="np-card">
            <div class="np-card-title">{escape(title)}</div>
            <div class="np-card-value">{escape(current_text)}</div>
            <div class="np-card-footer">
                LY: {escape(previous_text)}
                &nbsp;·&nbsp;
                <span class="{class_name}">{escape(growth_label)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def overhead_kpi_item_html(title, current, previous, conversion_type, icon):
    current_text = amount_text(current, conversion_type)
    previous_text = amount_text(previous, conversion_type)
    growth = pct_change(current, previous)
    growth_label = f"{growth:+.2f}%"

    # Lower overhead is favourable; higher overhead is adverse.
    class_name = "np-positive" if growth <= 0 else "np-negative"
    arrow = "▼" if growth < 0 else "▲" if growth > 0 else "–"

    # Keep the HTML left-aligned. Leading 4+ spaces are interpreted by Markdown
    # as a code block, which causes the raw <div> markup to appear on screen.
    return (
        f'<div class="np-overhead-item">'
        f'<div class="np-overhead-icon">{escape(icon)}</div>'
        f'<div class="np-overhead-body">'
        f'<div class="np-overhead-title">{escape(title)}</div>'
        f'<div class="np-overhead-value">{escape(current_text)}</div>'
        f'<div class="np-overhead-footer">'
        f'LY: {escape(previous_text)}&nbsp;|&nbsp;'
        f'<span class="{class_name}">{escape(arrow)} {escape(growth_label)}</span>'
        f'</div></div></div>'
    )

def _apply_same_filters(df, filters):
    out = df.copy()

    for column, selected in filters.items():
        out = apply_multi_filter(out, column, selected)

    return out


# ============================================================
# DASHBOARD
# ============================================================

def show_net_profit_dashboard():
    _inject_css()

    st.markdown(
        """
        <div class="np-title">Net Profit Dashboard</div>
        <div class="np-subtitle">
            Origin P&L + Destination P&L − Branch overhead
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # PRIMARY FILTERS
    # --------------------------------------------------------

    filter_cols = st.columns([1.15, 1, 1.35, 1.2, 1.2, 1.1, 1.0], gap="small")

    with filter_cols[0]:
        fy = st.selectbox(
            "Financial Year",
            FY_OPTIONS,
            key="np_fy",
        )

    if fy == "Select FY":
        st.info("Please select financial year.")
        return

    start_date, end_date = get_date_range(fy)
    prev_fy = get_previous_fy(fy)
    prev_start, prev_end = get_date_range(prev_fy)

    # Branch/Agency master is loaded first and becomes the dashboard branch scope.
    branch_master_df = load_net_profit_branch_mast()
    valid_branches = safe_options(branch_master_df, "BRANCH")

    if not valid_branches:
        st.warning("No valid branches found in Branch/Agency Master for selected financial year.")
        return

    with st.spinner("Loading Origin, Destination and branch overhead..."):
        raw_df, raw_prev_df = load_net_profit_data_pair(
            start_date,
            end_date,
            prev_start,
            prev_end,
        )

        # Consolidated All-Branches booking/origin revenue must come directly
        # from the P&L revenue stored procedure. Summing the branch-joined
        # ORIGIN_BUSINESS rows can understate revenue because some booking
        # records may be lost/repeated by branch mapping joins.
        sp_revenue_total = load_pnl_sp_revenue_total(start_date, end_date)
        sp_prev_revenue_total = load_pnl_sp_revenue_total(prev_start, prev_end)

    if raw_df is None or raw_df.empty:
        st.warning("No Net Profit data found for selected financial year.")
        return

    # Restrict P&L/overhead to branches returned by Branch/Agency Master.
    # Also backfill Zone/Circle from Branch Master when the raw P&L data does not carry them.
    df = _attach_branch_hierarchy(
        _filter_to_branch_scope(raw_df.copy(), valid_branches),
        branch_master_df,
    )
    prev_df = (
        _attach_branch_hierarchy(
            _filter_to_branch_scope(raw_prev_df.copy(), valid_branches),
            branch_master_df,
        )
        if raw_prev_df is not None
        else pd.DataFrame()
    )

    with filter_cols[1]:
        conversion_type = st.selectbox(
            "₹ Conversion",
            ["Crore", "Lac"],
            key="np_conversion",
        )

    # Use whichever hierarchy columns are actually available.
    with filter_cols[2]:
        branches = st.multiselect(
            "Branch",
            safe_options(branch_master_df, "BRANCH"),
            key="np_branch",
            placeholder="All branches",
        )

    with filter_cols[3]:
        zones = st.multiselect(
            "Zone",
            safe_options(df, "zone"),
            key="np_zone",
            placeholder="All zones",
            disabled="zone" not in df.columns,
        )

    # Circle choices must follow the current Branch/Zone scope.  Building the
    # option list from the unscoped dataframe can leave the widget empty when
    # hierarchy values are populated from Branch Master.
    circle_scope = df.copy()
    circle_scope = apply_multi_filter(circle_scope, "BRANCH", branches)
    circle_scope = apply_multi_filter(circle_scope, "zone", zones)
    circle_options = safe_options(circle_scope, "circle")

    with filter_cols[4]:
        circles = st.multiselect(
            "Circle",
            circle_options,
            key="np_circle",
            placeholder="All circles",
            disabled=("circle" not in df.columns or not circle_options),
        )

    with filter_cols[5]:
        quarters = st.multiselect(
            "Quarter",
            QUARTER_ORDER,
            key="np_quarter",
            placeholder="All quarters",
        )

    with filter_cols[6]:
        months = st.multiselect(
            "Month",
            MONTH_ORDER,
            key="np_month",
            placeholder="All months",
        )

    filters = {
        "BRANCH": branches,
        "zone": zones,
        "circle": circles,
        "QUARTER": quarters,
        "MONTH": months,
    }

    df = _apply_same_filters(df, filters)
    prev_df = _apply_same_filters(prev_df, filters) if not prev_df.empty else prev_df

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    # No explicit branch selection means consolidated All Branches mode.
    # In this mode only Origin-view P&L is used.
    all_branches = len(branches) == 0
    df = _apply_pnl_business_rule(df, all_branches=all_branches)
    prev_df = (
        _apply_pnl_business_rule(prev_df, all_branches=all_branches)
        if not prev_df.empty
        else prev_df
    )

    divisor, unit = get_conversion(conversion_type)

    current = calculate_kpis(df)
    previous = calculate_kpis(prev_df)

    # Business KPI display rule:
    # - Fully consolidated All Branches (no Branch/Zone/Circle/Quarter/Month filter):
    #   show the exact P&L SP revenue total in the Booking/Origin KPI. This is the
    #   authoritative origin-basis consolidated revenue and avoids understatement
    #   caused by branch joins. Destination KPI stays disabled.
    # - All Branches with hierarchy/time filters: use filtered ORIGIN_BUSINESS only.
    # - Explicit branch selection: show Booking and Destination revenue separately.
    no_business_scope_filters = not (branches or zones or circles or quarters or months)

    if all_branches and no_business_scope_filters:
        booking_business_current = float(sp_revenue_total or 0.0)
        booking_business_previous = float(sp_prev_revenue_total or 0.0)
    else:
        booking_business_current = current["origin_business"]
        booking_business_previous = previous["origin_business"]

    # --------------------------------------------------------
    # KPI ROW 1
    # --------------------------------------------------------

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    kpi_cols = st.columns(7, gap="small")

    kpis = [
        ("Origin P&L", current["origin_pnl"], previous["origin_pnl"], False, False),
        ("Destination P&L", current["destination_pnl"], previous["destination_pnl"], False, False),
        ("Combined P&L", current["combined_pnl"], previous["combined_pnl"], False, False),
        ("Origin Business / Booking", booking_business_current, booking_business_previous, False, False),
        (
            "Destination Business / Delivery",
            current["destination_business"],
            previous["destination_business"],
            False,
            all_branches,
        ),
        ("Net Profit", current["net_profit"], previous["net_profit"], False, False),
        ("Net Profit Margin", current["margin"], previous["margin"], False, False),
    ]

    for index, (title, cy, ly, reverse_good, disabled) in enumerate(kpis):
        with kpi_cols[index]:
            render_kpi_card(
                title,
                cy,
                ly,
                conversion_type=conversion_type,
                percent=(title == "Net Profit Margin"),
                reverse_good=reverse_good,
                disabled=disabled,
            )

    # --------------------------------------------------------
    # KPI ROW 2: OVERHEAD BREAKUP
    # --------------------------------------------------------

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    overhead_kpis = [
        ("Salary", current["salary"], previous["salary"], "●"),
        ("Overhead Expense", current["overhead"], previous["overhead"], "▦"),
        ("Claim", current["claim"], previous["claim"], "◆"),
        ("Booking (Freight)", current["booking_6"], previous["booking_6"], "▣"),
        ("Destination (Freight)", current["destination_5"], previous["destination_5"], "●"),
        ("Godown Rent", current["godown"], previous["godown"], "▥"),
    ]

    overhead_items_html = "".join(
        overhead_kpi_item_html(title, cy, ly, conversion_type, icon)
        for title, cy, ly, icon in overhead_kpis
    )
    st.markdown(
        f'<div class="np-overhead-strip">{overhead_items_html}</div>',
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # MONTHLY TREND + OVERHEAD BREAKUP
    # --------------------------------------------------------

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.55, 0.85], gap="medium")

    with left:
        with st.container(border=True):
            st.markdown(
                '<div class="np-section-title">Monthly Net Profit Trend</div>',
                unsafe_allow_html=True,
            )

            monthly = (
                df.groupby(["FIN_MONTH", "MONTH"], as_index=False)
                .agg(
                    Origin_PNL=("ORIGIN_PNL", "sum"),
                    Destination_PNL=("DESTINATION_PNL", "sum"),
                    Combined_PNL=("COMBINED_PNL", "sum"),
                    Overhead=("TOTAL EXPENSE", "sum"),
                    Net_Profit=("NET_PROFIT", "sum"),
                )
                .sort_values("FIN_MONTH")
            )

            prev_monthly = (
                prev_df.groupby(["FIN_MONTH", "MONTH"], as_index=False)
                .agg(LY_Net_Profit=("NET_PROFIT", "sum"))
                if prev_df is not None and not prev_df.empty
                else pd.DataFrame(columns=["FIN_MONTH", "MONTH", "LY_Net_Profit"])
            )

            monthly = monthly.merge(
                prev_monthly[["FIN_MONTH", "LY_Net_Profit"]],
                on="FIN_MONTH",
                how="left",
            )

            monthly["LY_Net_Profit"] = pd.to_numeric(
                monthly["LY_Net_Profit"],
                errors="coerce",
            ).fillna(0.0)

            monthly["Net Profit"] = monthly["Net_Profit"] / divisor
            monthly["LY Net Profit"] = monthly["LY_Net_Profit"] / divisor

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=monthly["MONTH"],
                    y=monthly["LY Net Profit"],
                    name=f"LY ({prev_fy})",
                    marker_color="#cbd5e1",
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>"
                        f"LY Net Profit: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )

            fig.add_trace(
                go.Bar(
                    x=monthly["MONTH"],
                    y=monthly["Net Profit"],
                    name=f"Current ({fy})",
                    marker_color="#2563eb",
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>"
                        f"Net Profit: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )

            fig.add_hline(y=0, line_width=1, line_color="#64748b")

            fig.update_layout(
                barmode="group",
                height=340,
                margin=dict(l=10, r=10, t=20, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#fbfdff",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    x=0,
                ),
                xaxis_title="",
                yaxis_title=f"Net Profit ({unit})",
            )

            fig.update_xaxes(
                categoryorder="array",
                categoryarray=MONTH_ORDER,
                showgrid=False,
            )

            fig.update_yaxes(showgrid=False)

            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )

    with right:
        with st.container(border=True):
            st.markdown(
                '<div class="np-section-title">Overhead Composition</div>',
                unsafe_allow_html=True,
            )

            overhead_values = pd.DataFrame(
                {
                    "Expense": [
                        "Salary",
                        "Godown Rent",
                        "Overhead Expense",
                        "Claim",
                        "Booking 6%",
                        "Destination 5%",
                    ],
                    "Amount": [
                        current["salary"],
                        current["godown"],
                        current["overhead"],
                        current["claim"],
                        current["booking_6"],
                        current["destination_5"],
                    ],
                }
            )

            overhead_values = overhead_values[
                overhead_values["Amount"].abs() > 0
            ].copy()

            if overhead_values.empty:
                st.info("No overhead found for selected filters.")
            else:
                fig_overhead = px.pie(
                    overhead_values,
                    names="Expense",
                    values="Amount",
                    hole=0.62,
                )

                fig_overhead.update_traces(
                    textposition="outside",
                    textinfo="percent+label",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Amount: ₹%{value:,.2f}<br>"
                        "Share: %{percent}<extra></extra>"
                    ),
                )

                fig_overhead.update_layout(
                    height=340,
                    margin=dict(l=5, r=5, t=10, b=5),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    annotations=[
                        dict(
                            text=amount_text(
                                current["total_expense"],
                                conversion_type,
                            ),
                            x=0.5,
                            y=0.53,
                            font_size=16,
                            showarrow=False,
                        ),
                        dict(
                            text="Total Overhead",
                            x=0.5,
                            y=0.43,
                            font_size=10,
                            showarrow=False,
                        ),
                    ],
                )

                st.plotly_chart(
                    fig_overhead,
                    width="stretch",
                    config={"displayModeBar": False},
                )

                overhead_change = pct_change(
                    current["total_expense"],
                    previous["total_expense"],
                )
                st.caption(
                    f"Total Overhead insight: {amount_text(current['total_expense'], conversion_type)} "
                    f"vs LY {amount_text(previous['total_expense'], conversion_type)} "
                    f"({overhead_change:+.1f}%)."
                )

    # --------------------------------------------------------
    # BRANCH PROFITABILITY
    # --------------------------------------------------------

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        top_left, top_right = st.columns([5, 1], gap="small")

        with top_left:
            st.markdown(
                '<div class="np-section-title">Branch-wise Net Profit</div>',
                unsafe_allow_html=True,
            )

        with top_right:
            top_n = st.selectbox(
                "Top branches",
                [10, 20, 30, 50],
                key="np_top_n",
                label_visibility="collapsed",
            )

        branch_summary = (
            df.groupby(
                ["BRANCHCODE", "BRANCH"],
                as_index=False,
                dropna=False,
            )
            .agg(
                Revenue=("BUSINESS", "sum"),
                Booking_Business=("ORIGIN_BUSINESS", "sum"),
                Delivery_Business=("DESTINATION_BUSINESS", "sum"),
                Origin_PNL=("ORIGIN_PNL", "sum"),
                Destination_PNL=("DESTINATION_PNL", "sum"),
                Combined_PNL=("COMBINED_PNL", "sum"),
                Salary=("SALARY", "sum"),
                Godown_Rent=("GODOWN RENT", "sum"),
                Overhead_Expense=("OVERHEAD EXPENSE", "sum"),
                Claim=("CLAIM", "sum"),
                Booking_6=("BOOKING 6%", "sum"),
                Destination_5=("DESTINATION 5%", "sum"),
                Total_Overhead=("TOTAL EXPENSE", "sum"),
                Net_Profit=("NET_PROFIT", "sum"),
                Total_Income=("TOTAL_INCOME", "sum"),
            )
        )

        branch_summary["Net Profit Margin %"] = 0.0
        valid_income = branch_summary["Total_Income"].ne(0)

        branch_summary.loc[valid_income, "Net Profit Margin %"] = (
            branch_summary.loc[valid_income, "Net_Profit"]
            / branch_summary.loc[valid_income, "Total_Income"]
            * 100
        )

        branch_summary = branch_summary.sort_values(
            "Net_Profit",
            ascending=False,
        ).reset_index(drop=True)

        chart_df = branch_summary.head(top_n).copy()
        chart_df["Net Profit Display"] = chart_df["Net_Profit"] / divisor

        fig_branch = px.bar(
            chart_df,
            x="Net Profit Display",
            y="BRANCH",
            orientation="h",
            labels={
                "Net Profit Display": f"Net Profit ({unit})",
                "BRANCH": "Branch",
            },
            hover_data={
                "BRANCHCODE": True,
                "Origin_PNL": ":,.2f",
                "Destination_PNL": ":,.2f",
                "Combined_PNL": ":,.2f",
                "Total_Overhead": ":,.2f",
                "Net Profit Display": ":.2f",
            },
        )

        fig_branch.update_layout(
            height=max(360, min(850, 45 * len(chart_df) + 100)),
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#fbfdff",
            yaxis=dict(autorange="reversed"),
            showlegend=False,
        )

        fig_branch.update_xaxes(showgrid=False)
        fig_branch.update_yaxes(showgrid=False)

        st.plotly_chart(
            fig_branch,
            width="stretch",
            config={"displayModeBar": False},
        )

    # --------------------------------------------------------
    # DETAIL TABLE
    # --------------------------------------------------------

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            '<div class="np-section-title">Branch Net Profit Detail</div>',
            unsafe_allow_html=True,
        )

        display = branch_summary.copy()

        money_columns = [
            "Revenue",
            "Booking_Business",
            "Delivery_Business",
            "Origin_PNL",
            "Destination_PNL",
            "Combined_PNL",
            "Salary",
            "Godown_Rent",
            "Overhead_Expense",
            "Claim",
            "Booking_6",
            "Destination_5",
            "Total_Overhead",
            "Net_Profit",
            "Total_Income",
        ]

        for column in money_columns:
            display[column] = (
                pd.to_numeric(display[column], errors="coerce")
                .fillna(0.0)
                / divisor
            )

        display = display.rename(
            columns={
                "BRANCHCODE": "Branch Code",
                "BRANCH": "Branch",
                "Revenue": f"Revenue ({unit})",
                "Booking_Business": f"Booking Business ({unit})",
                "Delivery_Business": f"Delivery Business ({unit})",
                "Origin_PNL": f"Origin P&L ({unit})",
                "Destination_PNL": f"Destination P&L ({unit})",
                "Combined_PNL": f"Combined P&L ({unit})",
                "Salary": f"Salary ({unit})",
                "Godown_Rent": f"Godown Rent ({unit})",
                "Overhead_Expense": f"Overhead Expense ({unit})",
                "Claim": f"Claim ({unit})",
                "Booking_6": f"Booking 6% ({unit})",
                "Destination_5": f"Destination 5% ({unit})",
                "Total_Overhead": f"Total Overhead ({unit})",
                "Net_Profit": f"Net Profit ({unit})",
                "Total_Income": f"Total Income ({unit})",
            }
        )

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            column_config={
                "Net Profit Margin %": st.column_config.NumberColumn(
                    "Net Profit Margin %",
                    format="%.2f%%",
                ),
            },
        )

        csv_data = display.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "Download Net Profit CSV",
            data=csv_data,
            file_name=f"net_profit_dashboard_{fy}.csv",
            mime="text/csv",
            key="np_download",
        )

    # --------------------------------------------------------
    # MONTH-WISE AUDIT TABLE
    # --------------------------------------------------------

    with st.expander("Monthly calculation audit"):
        audit_columns = [
            "BRANCHCODE",
            "BRANCH",
            "YEAR",
            "MONTHNO",
            "MONTH",
            "BUSINESS",
            "ORIGIN_BUSINESS",
            "DESTINATION_BUSINESS",
            "ORIGIN_PNL",
            "DESTINATION_PNL",
            "COMBINED_PNL",
            "SALARY",
            "GODOWN RENT",
            "OVERHEAD EXPENSE",
            "CLAIM",
            "BOOKING 6%",
            "DESTINATION 5%",
            "TOTAL EXPENSE",
            "NET_PROFIT",
            "NET_PROFIT_MARGIN",
        ]

        audit_columns = [
            column
            for column in audit_columns
            if column in df.columns
        ]

        st.dataframe(
            df[audit_columns].sort_values(
                ["BRANCH", "YEAR", "MONTHNO"]
            ),
            width="stretch",
            hide_index=True,
        )


# Optional direct-run support.
if __name__ == "__main__":
    show_net_profit_dashboard()
