from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import get_date_range
from services.net_profit_data_loader import load_net_profit_data_pair
from services.pnl_data_loader import load_pnl_sp_revenue_total, load_pnl_data_pair
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
            --np-blue:#2563eb;
            --np-text:#0f172a;
            --np-muted:#64748b;
            --np-border:#e2e8f0;
            --np-soft:#f8fafc;
            --np-green:#15803d;
            --np-red:#dc2626;
            --np-kpi-font: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .block-container {
            max-width:100% !important;
            padding:.35rem .75rem .65rem !important;
        }

        div[data-testid="stVerticalBlock"] { gap:.34rem !important; }
        div[data-testid="stHorizontalBlock"] { row-gap:.28rem !important; }

        /* Executive header */
        .np-header {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:16px;
            padding:7px 12px 8px;
            margin:0 0 2px;
            border:1px solid var(--np-border);
            border-radius:11px;
            background:linear-gradient(90deg,#ffffff 0%,#f8fbff 100%);
        }
        .np-title {
            color:var(--np-text);
            font-family:var(--np-kpi-font);
            font-size:18px;
            font-weight:800;
            line-height:1.1;
            letter-spacing:-.35px;
        }
        .np-subtitle {
            color:var(--np-muted);
            font-family:var(--np-kpi-font);
            font-size:10px;
            margin-top:2px;
        }
        /* Filters */
        div[data-testid="stSelectbox"] label,
        div[data-testid="stMultiSelect"] label {
            font-family:var(--np-kpi-font) !important;
            font-size:10px !important;
            font-weight:650 !important;
            color:#475569 !important;
            margin-bottom:1px !important;
        }
        div[data-baseweb="select"] > div {
            min-height:34px !important;
            border-color:#dce5ef !important;
            border-radius:8px !important;
            background:#fff !important;
            font-size:11px !important;
            box-shadow:none !important;
        }
        div[data-baseweb="select"] span { font-size:11px !important; }
        div[data-baseweb="tag"] {
            height:21px !important;
            border-radius:6px !important;
            font-size:9px !important;
        }

        /* Primary KPI cards */
        .np-card {
            min-height:86px;
            margin:0 2px;
            border:1px solid rgba(148,163,184,.24);
            border-radius:11px;
            padding:11px 54px 9px 12px;
            background:linear-gradient(110deg,var(--np-card-from),var(--np-card-to));
            box-shadow:0 2px 7px rgba(15,23,42,.10);
            position:relative;
            overflow:hidden;
        }
        .np-theme-business {--np-card-from:#fffafb;--np-card-to:#f8ccd7;--np-icon-bg:#22c96b;--np-accent:#07883f;}
        .np-theme-origin {--np-card-from:#f9fdff;--np-card-to:#c6eef9;--np-icon-bg:#ff4148;--np-accent:#05739a;}
        .np-theme-destination {--np-card-from:#fffdfd;--np-card-to:#f7d4d0;--np-icon-bg:#4285ed;--np-accent:#d33124;}
        .np-theme-combined {--np-card-from:#fbfbff;--np-card-to:#d6d4e8;--np-icon-bg:#8b55ef;--np-accent:#4338a8;}
        .np-theme-expense {--np-card-from:#fffdfa;--np-card-to:#ecded3;--np-icon-bg:#ff7110;--np-accent:#b34a00;}
        .np-theme-profit {--np-card-from:#fffdfd;--np-card-to:#decfd2;--np-icon-bg:#a84df2;--np-accent:#7e22ce;}
        .np-theme-margin {--np-card-from:#f9feff;--np-card-to:#c9eaf0;--np-icon-bg:#10abc1;--np-accent:#087f91;}
        .np-card-icon {
            position:absolute;
            right:12px;
            top:11px;
            width:38px;
            height:38px;
            border-radius:50%;
            display:flex;
            align-items:center;
            justify-content:center;
            color:#ffffff;
            background:var(--np-icon-bg);
            font-family:var(--np-kpi-font);
            font-size:19px;
            line-height:1;
            font-weight:800;
            box-shadow:0 2px 5px rgba(15,23,42,.10);
        }
        .np-card-title {
            font-family:var(--np-kpi-font);
            font-size:11px;
            color:#172033;
            font-weight:650;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }
        .np-card-value {
            margin-top:3px;
            font-family:var(--np-kpi-font);
            font-size:17px;
            line-height:1.15;
            color:#050b18;
            font-weight:800;
            white-space:nowrap;
        }
        .np-card-footer {
            margin-top:7px;
            font-family:var(--np-kpi-font);
            font-size:9.5px;
            font-weight:550;
            color:#64748b;
            white-space:nowrap;
        }
        .np-positive { color:var(--np-green); font-weight:700; }
        .np-negative { color:var(--np-red); font-weight:700; }

        /* Secondary expense strip */
        .np-overhead-strip {
            width:100%;
            min-height:58px;
            border:1px solid var(--np-border);
            border-radius:10px;
            background:#fbfdff;
            display:flex;
            align-items:stretch;
            overflow:hidden;
            margin:0 0 2px;
        }
        .np-overhead-item {
            flex:1 1 0;
            min-width:0;
            padding:6px 9px;
            display:flex;
            align-items:center;
            gap:7px;
            position:relative;
        }
        .np-overhead-item:not(:last-child)::after {
            content:"";
            position:absolute;
            right:0;
            top:9px;
            bottom:9px;
            width:1px;
            background:#e5edf5;
        }
        .np-overhead-icon {
            width:25px;
            height:25px;
            min-width:25px;
            border-radius:7px;
            background:#eef6ff;
            display:flex;
            align-items:center;
            justify-content:center;
            color:#2563eb;
            font-size:12px;
        }
        .np-overhead-body { min-width:0; flex:1; }
        .np-overhead-title {
            font-family:var(--np-kpi-font);
            font-size:8.5px;
            color:#64748b;
            font-weight:700;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }
        .np-overhead-value {
            margin-top:1px;
            font-family:var(--np-kpi-font);
            font-size:12.5px;
            color:#0f172a;
            font-weight:750;
            white-space:nowrap;
        }
        .np-overhead-footer {
            margin-top:1px;
            font-family:var(--np-kpi-font);
            font-size:8px;
            color:#94a3b8;
            white-space:nowrap;
        }

        .np-section-title {
            font-family:var(--np-kpi-font);
            font-size:12px;
            color:#0f172a;
            font-weight:750;
            margin:0 0 2px 0;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border:1px solid var(--np-border) !important;
            border-radius:10px !important;
            background:#ffffff !important;
            box-shadow:none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding-top:.45rem !important;
            padding-bottom:.45rem !important;
        }

        [data-testid="stDataFrame"] {
            border:1px solid var(--np-border);
            border-radius:8px;
            overflow:hidden;
        }

        /* Dataframe header: dark navy background with white labels. */
        [data-testid="stDataFrame"] [role="columnheader"] {
            background:#102a43 !important;
            color:#ffffff !important;
            font-weight:700 !important;
        }
        [data-testid="stDataFrame"] [role="columnheader"] * {
            color:#ffffff !important;
        }

        div[data-testid="stDownloadButton"] button {
            min-height:32px !important;
            border-radius:8px !important;
            border:1px solid #dbe4ef !important;
            font-size:10px !important;
            font-weight:650 !important;
            padding:.3rem .7rem !important;
        }

        details[data-testid="stExpander"] {
            border:1px solid var(--np-border) !important;
            border-radius:9px !important;
        }
        details[data-testid="stExpander"] summary p {
            font-size:10px !important;
            font-weight:650 !important;
        }

        /* P&L insight buttons - copied from the P&L dashboard visual language. */
        div[class*="st-key-np_pnl_trend_btn_"] {margin:0 !important;padding:0 !important;}
        div[class*="st-key-np_pnl_trend_btn_"] div[data-testid="stButton"],
        div[class*="st-key-np_pnl_branch_slab_btn_"] div[data-testid="stButton"],
        div[class*="st-key-np_pnl_view_btn_"] div[data-testid="stButton"] {width:100% !important;margin:0 !important;}
        div[class*="st-key-np_pnl_trend_btn_"] button,
        div[class*="st-key-np_pnl_branch_slab_btn_"] button,
        div[class*="st-key-np_pnl_view_btn_"] button {
            width:100% !important;min-height:34px !important;height:34px !important;padding:4px 8px !important;
            margin:0 !important;border:1px solid #d8e2ee !important;border-radius:8px !important;
            background:linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important;color:#334155 !important;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.95),0 1px 2px rgba(15,23,42,.05) !important;
            transform:none !important;font-size:11px !important;font-weight:650 !important;white-space:nowrap !important;
        }
        div[class*="st-key-np_pnl_trend_btn_"] button:hover,
        div[class*="st-key-np_pnl_branch_slab_btn_"] button:hover,
        div[class*="st-key-np_pnl_view_btn_"] button:hover {
            border-color:#9bb7d8 !important;background:linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important;
            color:#174a7e !important;box-shadow:inset 0 1px 0 #ffffff,0 2px 5px rgba(15,42,67,.08) !important;
        }
        div[class*="st-key-np_pnl_trend_btn_"] button[data-testid="stBaseButton-primary"],
        div[class*="st-key-np_pnl_branch_slab_btn_"] button[data-testid="stBaseButton-primary"],
        div[class*="st-key-np_pnl_view_btn_"] button[data-testid="stBaseButton-primary"] {
            border-color:#123f73 !important;background:linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important;
            color:#ffffff !important;box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 2px 5px rgba(15,42,67,.18) !important;
        }
        div[class*="st-key-np_pnl_trend_btn_"] button[data-testid="stBaseButton-primary"] p,
        div[class*="st-key-np_pnl_trend_btn_"] button[data-testid="stBaseButton-primary"] span,
        div[class*="st-key-np_pnl_branch_slab_btn_"] button[data-testid="stBaseButton-primary"] p,
        div[class*="st-key-np_pnl_branch_slab_btn_"] button[data-testid="stBaseButton-primary"] span,
        div[class*="st-key-np_pnl_view_btn_"] button[data-testid="stBaseButton-primary"] p,
        div[class*="st-key-np_pnl_view_btn_"] button[data-testid="stBaseButton-primary"] span {color:#ffffff !important;}
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
    card_styles = {
        "Origin Business": ("np-theme-business", "₹"),
        "Destination Business": ("np-theme-origin", "▤"),
        "Origin P&L": ("np-theme-origin", "↗"),
        "Destination P&L": ("np-theme-destination", "↘"),
        "Gross P&L": ("np-theme-combined", "⇄"),
        "Indirect Exp": ("np-theme-expense", "▰"),
        "Net Profit": ("np-theme-profit", "₹"),
        "Net Profit %": ("np-theme-margin", "%"),
    }
    card_theme, card_icon = card_styles.get(
        title, ("np-theme-origin", "●")
    )

    if disabled:
        st.markdown(
            f"""
            <div class="np-card np-card-disabled {card_theme}">
                <div class="np-card-icon">{escape(card_icon)}</div>
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
        <div class="np-card {card_theme}">
            <div class="np-card-icon">{escape(card_icon)}</div>
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
# P&L INSIGHT HELPERS (ISOLATED FROM NET PROFIT CALCULATIONS)
# ============================================================

def _normalise_insight_pnl(df):
    """Normalise P&L SP output for insight visuals only.

    IMPORTANT: this dataframe is never used by Net Profit KPIs/tables.
    Load-type analysis is intentionally not used in Phase 1.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    aliases = {
        "COMPNAME": ("COMPNAME", "company", "companyname"),
        "zone": ("zone", "zonename", "ZONE"),
        "circle": ("circle", "circlename", "hubname", "CIRCLE"),
        "branch": ("branch", "branchname", "BRANCH"),
        "grno": ("grno", "gr_no", "grnumber", "GRNO"),
        "grdt": ("grdt", "grdate", "bookingdate", "GRDT"),
        "FIN_MONTH": ("FIN_MONTH", "fin_month", "financialmonth"),
        "REVENUE": ("REVENUE", "revenue", "business"),
        "EXPENSE": ("EXPENSE", "expense", "expenses", "cost"),
        "PNL": ("PNL", "pnl", "profitloss", "profit_loss", "profitandloss"),
        "Consignor": ("Consignor", "consignor", "consignorname"),
        "Consignee": ("Consignee", "consignee", "consigneename"),
        "Route": ("Route", "route", "routename"),
    }

    rename_map = {}
    for target, candidates in aliases.items():
        source = _find_column(out, *candidates)
        if source is not None and source != target:
            rename_map[source] = target
    out = out.rename(columns=rename_map)

    for col in ["REVENUE", "EXPENSE", "PNL", "FIN_MONTH"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    if "grdt" in out.columns:
        out["grdt"] = pd.to_datetime(out["grdt"], errors="coerce")

    month_map = {1: "Apr", 2: "May", 3: "Jun", 4: "Jul", 5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov", 9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"}
    quarter_map = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2", 7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"}
    if "FIN_MONTH" in out.columns:
        out["FIN_MONTH"] = pd.to_numeric(out["FIN_MONTH"], errors="coerce").fillna(0).astype(int)
        out["MONTH"] = out["FIN_MONTH"].map(month_map)
        out["QUARTER"] = out["FIN_MONTH"].map(quarter_map)

    return out


def _apply_insight_values(df, column, selected):
    """Case-insensitive multi-value filter for the isolated P&L insight dataset."""
    if df is None or df.empty or column not in df.columns or not selected:
        return df
    selected_keys = {_normalise_branch_name(value) for value in selected}
    keys = df[column].fillna("").astype(str).map(_normalise_branch_name)
    return df[keys.isin(selected_keys)].copy()


def _filter_pnl_insight_scope(df, zones, circles, branches, quarters, months):
    out = df.copy() if df is not None else pd.DataFrame()
    out = _apply_insight_values(out, "zone", zones)
    out = _apply_insight_values(out, "circle", circles)
    out = _apply_insight_values(out, "branch", branches)
    out = _apply_insight_values(out, "QUARTER", quarters)
    out = _apply_insight_values(out, "MONTH", months)
    return out


def _build_pnl_insight_trend(current_df, previous_df, trend_type, start_date, prev_start):
    """Return CY and LY P&L on a comparable financial-period key."""
    if current_df is None or current_df.empty or "PNL" not in current_df.columns:
        return pd.DataFrame(columns=["Period", "PNL", "PY_PNL"])

    cur = current_df.copy()
    prev = previous_df.copy() if previous_df is not None else pd.DataFrame()

    if trend_type in ("Daily", "Weekly") and "grdt" not in cur.columns:
        trend_type = "Monthly"

    if trend_type == "Daily":
        cur = cur[cur["grdt"].notna()].copy()
        cur["Key"] = (cur["grdt"].dt.normalize() - pd.Timestamp(start_date)).dt.days
        cy = cur.groupby("Key", as_index=False)["PNL"].sum()
        cy["Period"] = (pd.Timestamp(start_date) + pd.to_timedelta(cy["Key"], unit="D")).dt.strftime("%d-%b")
        if not prev.empty and "grdt" in prev.columns:
            prev = prev[prev["grdt"].notna()].copy()
            prev["Key"] = (prev["grdt"].dt.normalize() - pd.Timestamp(prev_start)).dt.days
            py = prev.groupby("Key", as_index=False)["PNL"].sum().rename(columns={"PNL": "PY_PNL"})
        else:
            py = pd.DataFrame(columns=["Key", "PY_PNL"])
    elif trend_type == "Weekly":
        cur = cur[cur["grdt"].notna()].copy()
        cur["Key"] = ((cur["grdt"].dt.normalize() - pd.Timestamp(start_date)).dt.days // 7).astype(int)
        cy = cur.groupby("Key", as_index=False)["PNL"].sum()
        cy["Period"] = "W" + (cy["Key"] + 1).astype(str)
        if not prev.empty and "grdt" in prev.columns:
            prev = prev[prev["grdt"].notna()].copy()
            prev["Key"] = ((prev["grdt"].dt.normalize() - pd.Timestamp(prev_start)).dt.days // 7).astype(int)
            py = prev.groupby("Key", as_index=False)["PNL"].sum().rename(columns={"PNL": "PY_PNL"})
        else:
            py = pd.DataFrame(columns=["Key", "PY_PNL"])
    elif trend_type == "Quarterly":
        cy = cur.groupby("QUARTER", as_index=False)["PNL"].sum().rename(columns={"QUARTER": "Period"})
        cy["Period"] = pd.Categorical(cy["Period"], QUARTER_ORDER, ordered=True)
        cy = cy.sort_values("Period")
        cy["Key"] = cy["Period"].astype(str)
        if not prev.empty and "QUARTER" in prev.columns:
            py = prev.groupby("QUARTER", as_index=False)["PNL"].sum().rename(columns={"QUARTER": "Key", "PNL": "PY_PNL"})
        else:
            py = pd.DataFrame(columns=["Key", "PY_PNL"])
    else:
        cy = cur.groupby("MONTH", as_index=False)["PNL"].sum().rename(columns={"MONTH": "Period"})
        cy["Period"] = pd.Categorical(cy["Period"], MONTH_ORDER, ordered=True)
        cy = cy.sort_values("Period")
        cy["Key"] = cy["Period"].astype(str)
        if not prev.empty and "MONTH" in prev.columns:
            py = prev.groupby("MONTH", as_index=False)["PNL"].sum().rename(columns={"MONTH": "Key", "PNL": "PY_PNL"})
        else:
            py = pd.DataFrame(columns=["Key", "PY_PNL"])

    result = cy.merge(py[["Key", "PY_PNL"]], on="Key", how="left")
    result["PY_PNL"] = pd.to_numeric(result["PY_PNL"], errors="coerce").fillna(0.0)
    return result


def _top_pnl_insight_table(df, prev_df, group_col, entity_name, divisor, unit, widget_key, subtitle=""):
    """Original P&L-dashboard style Top-N insight table."""
    if group_col not in df.columns:
        st.info(f"{entity_name.rstrip('s')} column is not available in P&L insight data.")
        return

    title_col, selector_col = st.columns([4.2, 1.0], gap="small", vertical_alignment="center")
    with selector_col:
        top_n = st.selectbox(
            f"{entity_name} to display", [10, 20, 30, 40], index=0,
            format_func=lambda value: f"Top {value}", key=f"{widget_key}_top_n",
            label_visibility="collapsed",
        )
    with title_col:
        st.markdown(
            f"<div style='font-size:18px;font-weight:400;color:#0f2744;margin:1px 0 9px 2px;'>"
            f"Top {top_n} {entity_name} by P&amp;L</div>"
            f"<div style='font-size:12px;font-weight:400;color:#64748b;margin-top:-4px;'>{escape(subtitle)}</div>",
            unsafe_allow_html=True,
        )

    current_data = df[[group_col, "PNL"]].copy()
    current_data[group_col] = current_data[group_col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    current_rank = current_data[current_data[group_col].ne("Unknown")].groupby(group_col, dropna=False)["PNL"].sum().reset_index(name="Current PNL")
    if prev_df is not None and not prev_df.empty and group_col in prev_df.columns and "PNL" in prev_df.columns:
        previous_data = prev_df[[group_col, "PNL"]].copy()
        previous_data[group_col] = previous_data[group_col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
        previous_rank = previous_data[previous_data[group_col].ne("Unknown")].groupby(group_col, dropna=False)["PNL"].sum().reset_index(name="Previous PNL")
    else:
        previous_rank = pd.DataFrame(columns=[group_col, "Previous PNL"])

    ranking = current_rank.merge(previous_rank, on=group_col, how="left")
    ranking["Previous PNL"] = pd.to_numeric(ranking["Previous PNL"], errors="coerce").fillna(0.0)
    ranking["P&L Display"] = (pd.to_numeric(ranking["Current PNL"], errors="coerce").fillna(0.0) / divisor).round(2)
    total_abs_pnl = float(ranking["Current PNL"].abs().sum())
    ranking["Share %"] = ranking["Current PNL"].abs() / total_abs_pnl * 100 if total_abs_pnl else 0.0
    ranking["Growth %"] = ranking.apply(lambda row: pct_change(row["Current PNL"], row["Previous PNL"]) if row["Previous PNL"] != 0 else None, axis=1)
    ranking = ranking.sort_values("Current PNL", ascending=False).head(top_n).reset_index(drop=True)
    if ranking.empty:
        st.info(f"No {entity_name.lower()} P&L is available for the selected filters.")
        return

    max_abs_value = max(float(ranking["P&L Display"].abs().max()), 1.0)
    prefix = "cust" if entity_name == "Customers" else "route"
    bar_gradient = "linear-gradient(90deg,#60a5fa,#2563eb)" if prefix == "cust" else "linear-gradient(90deg,#2dd4bf,#0f766e)"
    singular_name = "Customer" if entity_name == "Customers" else "Route"
    rows=[]
    for idx,row in ranking.iterrows():
        pnl_display=float(row["P&L Display"] or 0); share_pct=float(row["Share %"] or 0)
        bar_width=min((abs(pnl_display)/max_abs_value)*100,100); growth=row["Growth %"]
        if pd.isna(growth): growth_html=f"<span class='{prefix}-growth new'>NEW</span>"
        else:
            positive=growth>=0; growth_class="up" if positive else "down"; growth_arrow="▲" if positive else "▼"
            growth_html=f"<span class='{prefix}-growth {growth_class}'>{growth_arrow} {abs(growth):.1f}%</span>"
        full_name=escape(str(row[group_col])); value_color="#0f172a" if pnl_display>=0 else "#dc2626"
        rows.append("<tr>"+f"<td class='{prefix}-rank'>{idx+1}</td>"+f"<td class='{prefix}-name' title='{full_name}'>{full_name}</td>"+f"<td class='{prefix}-revenue'><div class='{prefix}-value' style='color:{value_color};'>₹{pnl_display:.2f} {escape(str(unit))}</div><div class='{prefix}-bar-track'><div class='{prefix}-bar-fill' style='width:{bar_width:.1f}%'></div></div></td>"+f"<td class='{prefix}-share'>{share_pct:.1f}%</td>"+f"<td class='{prefix}-yoy'>{growth_html}</td></tr>")

    table_html=f"""
    <style>
      .{prefix}-insight-wrap{{width:100%;overflow-x:auto;margin-top:5px;border:1px solid #e2e8f0;border-radius:10px;background:#ffffff;}}
      .{prefix}-insight-table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:12px;color:#334155;}}
      .{prefix}-insight-table th{{padding:7px 6px;background:#f8fafc;color:#64748b;font-size:12px;font-weight:400;text-align:left;border-bottom:1px solid #e2e8f0;white-space:nowrap;}}
      .{prefix}-insight-table td{{padding:8px 6px;border-bottom:1px solid #edf2f7;vertical-align:middle;}}
      .{prefix}-insight-table tr:last-child td{{border-bottom:0;}} .{prefix}-insight-table tbody tr:hover{{background:#f8fbff;}}
      .{prefix}-rank{{width:4%;padding-left:2px!important;padding-right:2px!important;text-align:center;font-weight:400;color:#64748b;}}
      .{prefix}-name{{width:38%;padding-left:3px!important;font-weight:400;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
      .{prefix}-revenue{{width:32%;}} .{prefix}-value{{font-weight:400;margin-bottom:3px;}}
      .{prefix}-bar-track{{width:100%;height:5px;border-radius:999px;background:#e8eef8;overflow:hidden;}}
      .{prefix}-bar-fill{{height:5px;border-radius:999px;background:{bar_gradient};}}
      .{prefix}-share{{width:12%;text-align:right;font-weight:400;color:#475569;}} .{prefix}-yoy{{width:14%;text-align:right;}}
      .{prefix}-growth{{display:inline-block;min-width:50px;text-align:right;font-size:11px;font-weight:400;}}
      .{prefix}-growth.up{{color:#16a34a;}} .{prefix}-growth.down{{color:#dc2626;}} .{prefix}-growth.new{{color:#7c3aed;}}
    </style>
    <div class="{prefix}-insight-wrap"><table class="{prefix}-insight-table"><colgroup><col style="width:4%"><col style="width:38%"><col style="width:32%"><col style="width:12%"><col style="width:14%"></colgroup><thead><tr><th style="text-align:center;">#</th><th>{singular_name}</th><th>P&amp;L ({escape(str(unit))})</th><th style="text-align:right;">% Share</th><th style="text-align:right;">vs LY</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""
    if hasattr(st,"html"): st.html(table_html)
    else: st.markdown(table_html,unsafe_allow_html=True)

def _render_phase1_pnl_insights(
    start_date, end_date, prev_start, prev_end,
    fy, prev_fy,
    zones, circles, branches, quarters, months, valid_branches,
    divisor, unit,
    net_profit_df=None, net_profit_prev_df=None,
):
    """Render isolated P&L insights in the same visual language as Net Profit."""
    st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        title_col, view_col = st.columns([5, 1], gap="small", vertical_alignment="center")
        with title_col:
            st.markdown(
                '<div class="np-section-title" style="margin-bottom:1px;">P&amp;L Insights</div>'
                '<div class="np-subtitle" style="margin:0 0 1px 1px;">'
                'Operational P&amp;L analysis using the active Net Profit filters'
                '</div>',
                unsafe_allow_html=True,
            )
        with view_col:
            view_options = ["Origin", "Destination"]
            insight_view = st.session_state.get("np_pnl_insight_view_value", "Origin")
            if insight_view not in view_options:
                insight_view = "Origin"
                st.session_state["np_pnl_insight_view_value"] = "Origin"

            view_btn_cols = st.columns(2, gap="small")
            for view_index, view_label in enumerate(view_options):
                with view_btn_cols[view_index]:
                    if st.button(
                        view_label,
                        key=f"np_pnl_view_btn_{view_index}",
                        type="primary" if insight_view == view_label else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["np_pnl_insight_view_value"] = view_label
                        st.rerun()

    try:
        with st.spinner(f"Loading {insight_view} P&L insights..."):
            raw_insight_df, raw_insight_prev_df = load_pnl_data_pair(
                start_date, end_date, prev_start, prev_end, insight_view
            )
    except Exception as exc:
        st.warning(f"P&L insights could not be loaded: {exc}")
        return pd.DataFrame(), pd.DataFrame()

    insight_df = _normalise_insight_pnl(raw_insight_df)
    insight_prev_df = _normalise_insight_pnl(raw_insight_prev_df)
    if insight_df.empty or not {"PNL", "FIN_MONTH"}.issubset(insight_df.columns):
        st.info("P&L insight data is not available for the selected financial year.")
        return pd.DataFrame(), pd.DataFrame()

    insight_df = _apply_insight_values(insight_df, "branch", valid_branches)
    if not insight_prev_df.empty:
        insight_prev_df = _apply_insight_values(insight_prev_df, "branch", valid_branches)

    # Same FY / Zone / Circle / Branch / Quarter / Month scope. No LOADTYPE logic.
    insight_df = _filter_pnl_insight_scope(insight_df, zones, circles, branches, quarters, months)
    if not insight_prev_df.empty:
        insight_prev_df = _filter_pnl_insight_scope(
            insight_prev_df, zones, circles, branches, quarters, months
        )

    if insight_df.empty:
        st.info("No P&L insight data found for the selected Net Profit filters.")
        return pd.DataFrame(), pd.DataFrame()

    trend_col, zone_col = st.columns([1, 1], gap="medium")
    with trend_col:
        with st.container(border=True):
            title_left, grain_col = st.columns([2.3, 1.7], gap="small", vertical_alignment="center")
            with title_left:
                st.markdown('<div class="np-section-title">P&amp;L Performance Trend</div>', unsafe_allow_html=True)
            with grain_col:
                trend_options = ["Daily", "Weekly", "Monthly", "Quarterly"]
                trend_type = st.session_state.get("np_pnl_insight_trend_type", "Monthly")
                if trend_type not in trend_options:
                    trend_type = "Monthly"
                    st.session_state["np_pnl_insight_trend_type"] = "Monthly"
                trend_btn_cols = st.columns(len(trend_options), gap="small")
                for trend_index, trend_label in enumerate(trend_options):
                    with trend_btn_cols[trend_index]:
                        if st.button(
                            trend_label, key=f"np_pnl_trend_btn_{trend_index}",
                            type="primary" if trend_type == trend_label else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["np_pnl_insight_trend_type"] = trend_label
                            st.rerun()
            trend_df = _build_pnl_insight_trend(
                insight_df, insight_prev_df, trend_type, start_date, prev_start
            )
            trend_df["CY"] = pd.to_numeric(trend_df["PNL"], errors="coerce").fillna(0.0) / divisor
            trend_df["LY"] = pd.to_numeric(trend_df["PY_PNL"], errors="coerce").fillna(0.0) / divisor
            trend_df["Growth %"] = trend_df.apply(
                lambda row: pct_change(row["CY"], row["LY"]), axis=1
            )
            trend_df["Growth Label"] = trend_df["Growth %"].apply(
                lambda value: f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"
            )

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=trend_df["Period"], y=trend_df["LY"], name=f"LY ({prev_fy})",
                marker=dict(color="#cbd5e1", line=dict(color="#94a3b8", width=1.2)),
                text=trend_df["LY"], texttemplate="%{text:.2f}", textposition="outside",
                textfont=dict(size=10, color="#475569", family="Arial"), cliponaxis=False,
                hovertemplate=f"<b>%{{x}}</b><br>LY P&L: ₹%{{y:.2f}} {unit}<extra></extra>",
            ))
            fig_trend.add_trace(go.Bar(
                x=trend_df["Period"], y=trend_df["CY"], name=f"Current ({fy})",
                marker=dict(color="#2563eb", line=dict(color="#1d4ed8", width=1.2)),
                text=trend_df["CY"], texttemplate="%{text:.2f}", textposition="outside",
                textfont=dict(size=10, color="#2563eb", family="Arial"), cliponaxis=False,
                hovertemplate=f"<b>%{{x}}</b><br>CY P&L: ₹%{{y:.2f}} {unit}<extra></extra>",
            ))

            trend_abs_max = max(
                float(pd.concat([trend_df["CY"].abs(), trend_df["LY"].abs()]).max() or 0),
                1.0,
            )
            if len(trend_df) <= 40:
                for _, trend_row in trend_df.iterrows():
                    growth_value = float(trend_row["Growth %"] or 0)
                    current_value = float(trend_row["CY"] or 0)
                    previous_value = float(trend_row["LY"] or 0)
                    positive_top = max(current_value, previous_value, 0)
                    negative_bottom = min(current_value, previous_value, 0)
                    annotation_gap = trend_abs_max * (0.20 if trend_type == "Monthly" else 0.14)
                    annotation_y = positive_top + annotation_gap if positive_top > 0 else negative_bottom - annotation_gap
                    fig_trend.add_annotation(
                        x=trend_row["Period"], y=annotation_y,
                        text=trend_row["Growth Label"], showarrow=False,
                        font=dict(
                            size=10,
                            color="#166534" if growth_value >= 0 else "#dc2626",
                            family="Arial",
                        ),
                    )

            fig_trend.add_hline(y=0, line_width=1, line_color="#64748b")
            fig_trend.update_layout(
                barmode="group", height=300, margin=dict(l=6, r=6, t=34, b=4),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fbfdff",
                legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0, font=dict(size=10)),
                xaxis_title="", yaxis_title=f"P&L ({unit})", bargap=0.22, bargroupgap=0.08,
            )
            fig_trend.update_xaxes(showgrid=False)
            fig_trend.update_yaxes(showgrid=False)
            st.plotly_chart(fig_trend, width="stretch", config={"displayModeBar": False})

    with zone_col:
        with st.container(border=True):
            title_col, filter_col = st.columns([2, 2], gap="small", vertical_alignment="center")

            np_trend_options = ["Daily", "Weekly", "Monthly", "Quarterly"]
            np_trend_type = st.session_state.get("np_net_profit_performance_trend_value", "Monthly")
            if np_trend_type not in np_trend_options:
                np_trend_type = "Monthly"
                st.session_state["np_net_profit_performance_trend_value"] = "Monthly"

            with title_col:
                st.markdown(
                    '<div style="font-size:14px;font-weight:400;color:#0f172a;">Net Profit Performance Trend</div>',
                    unsafe_allow_html=True,
                )

            with filter_col:
                np_trend_btn_cols = st.columns(len(np_trend_options), gap="small")
                for trend_index, trend_label in enumerate(np_trend_options):
                    with np_trend_btn_cols[trend_index]:
                        if st.button(
                            trend_label,
                            key=f"np_pnl_trend_btn_np_perf_{trend_index}",
                            type="primary" if np_trend_type == trend_label else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["np_net_profit_performance_trend_value"] = trend_label
                            st.rerun()

            def _build_np_trend(current_df, previous_df, trend_type):
                if current_df is None or current_df.empty or "NET_PROFIT" not in current_df.columns:
                    return pd.DataFrame(columns=["Period", "CY", "LY"]), "No Net Profit data available."

                current_df = current_df.copy()
                previous_df = previous_df.copy() if previous_df is not None else pd.DataFrame()

                date_candidates = ["grdt", "GRDT", "grdate", "GRDATE", "bookingdate", "BOOKINGDATE", "date", "DATE"]
                cur_date = next((c for c in date_candidates if c in current_df.columns), None)
                prev_date = next((c for c in date_candidates if c in previous_df.columns), None)

                if trend_type in ("Daily", "Weekly"):
                    if cur_date is None:
                        return pd.DataFrame(columns=["Period", "CY", "LY"]), f"{trend_type} Net Profit cannot be calculated because no date column is available."

                    cur = current_df[[cur_date, "NET_PROFIT"]].copy()
                    cur[cur_date] = pd.to_datetime(cur[cur_date], errors="coerce")
                    cur = cur[cur[cur_date].notna()]
                    if cur.empty:
                        return pd.DataFrame(columns=["Period", "CY", "LY"]), f"No {trend_type.lower()} Net Profit data available."

                    if trend_type == "Daily":
                        cur["Key"] = (cur[cur_date].dt.normalize() - pd.Timestamp(start_date)).dt.days
                        cy = cur.groupby("Key", as_index=False)["NET_PROFIT"].sum().rename(columns={"NET_PROFIT": "CY"})
                        cy["Period"] = (pd.Timestamp(start_date) + pd.to_timedelta(cy["Key"], unit="D")).dt.strftime("%d %b")
                    else:
                        cur["Key"] = ((cur[cur_date].dt.normalize() - pd.Timestamp(start_date)).dt.days // 7)
                        cy = cur.groupby("Key", as_index=False)["NET_PROFIT"].sum().rename(columns={"NET_PROFIT": "CY"})
                        cy["Period"] = "W" + (cy["Key"] + 1).astype(str)

                    if not previous_df.empty and prev_date and "NET_PROFIT" in previous_df.columns:
                        prev = previous_df[[prev_date, "NET_PROFIT"]].copy()
                        prev[prev_date] = pd.to_datetime(prev[prev_date], errors="coerce")
                        prev = prev[prev[prev_date].notna()]
                        if trend_type == "Daily":
                            prev["Key"] = (prev[prev_date].dt.normalize() - pd.Timestamp(prev_start)).dt.days
                        else:
                            prev["Key"] = ((prev[prev_date].dt.normalize() - pd.Timestamp(prev_start)).dt.days // 7)
                        ly = prev.groupby("Key", as_index=False)["NET_PROFIT"].sum().rename(columns={"NET_PROFIT": "LY"})
                    else:
                        ly = pd.DataFrame(columns=["Key", "LY"])

                    result = cy.merge(ly, on="Key", how="left")
                    result["LY"] = pd.to_numeric(result["LY"], errors="coerce").fillna(0.0)
                    return result[["Period", "CY", "LY"]], None

                if trend_type == "Quarterly":
                    if "QUARTER" not in current_df.columns:
                        return pd.DataFrame(columns=["Period", "CY", "LY"]), "Quarter is unavailable in Net Profit data."
                    cy = current_df.groupby("QUARTER", as_index=False)["NET_PROFIT"].sum().rename(columns={"QUARTER": "Period", "NET_PROFIT": "CY"})
                    cy["Period"] = pd.Categorical(cy["Period"], categories=QUARTER_ORDER, ordered=True)
                    cy = cy.sort_values("Period")
                    cy["Key"] = cy["Period"].astype(str)
                    if not previous_df.empty and "QUARTER" in previous_df.columns:
                        ly = previous_df.groupby("QUARTER", as_index=False)["NET_PROFIT"].sum().rename(columns={"QUARTER": "Key", "NET_PROFIT": "LY"})
                    else:
                        ly = pd.DataFrame(columns=["Key", "LY"])
                else:
                    if "MONTH" not in current_df.columns:
                        return pd.DataFrame(columns=["Period", "CY", "LY"]), "Month is unavailable in Net Profit data."
                    cy = current_df.groupby("MONTH", as_index=False)["NET_PROFIT"].sum().rename(columns={"MONTH": "Period", "NET_PROFIT": "CY"})
                    cy["Period"] = pd.Categorical(cy["Period"], categories=MONTH_ORDER, ordered=True)
                    cy = cy.sort_values("Period")
                    cy["Key"] = cy["Period"].astype(str)
                    if not previous_df.empty and "MONTH" in previous_df.columns:
                        ly = previous_df.groupby("MONTH", as_index=False)["NET_PROFIT"].sum().rename(columns={"MONTH": "Key", "NET_PROFIT": "LY"})
                    else:
                        ly = pd.DataFrame(columns=["Key", "LY"])

                result = cy.merge(ly, on="Key", how="left")
                result["LY"] = pd.to_numeric(result["LY"], errors="coerce").fillna(0.0)
                return result[["Period", "CY", "LY"]], None

            np_trend_df, np_trend_error = _build_np_trend(net_profit_df, net_profit_prev_df, np_trend_type)

            if np_trend_error:
                st.info(np_trend_error)
            elif np_trend_df.empty:
                st.info("No Net Profit trend data is available for the selected filters.")
            else:
                np_trend_df["CY Display"] = pd.to_numeric(np_trend_df["CY"], errors="coerce").fillna(0.0) / divisor
                np_trend_df["LY Display"] = pd.to_numeric(np_trend_df["LY"], errors="coerce").fillna(0.0) / divisor
                np_trend_df["Growth %"] = np_trend_df.apply(lambda row: pct_change(row["CY"], row["LY"]), axis=1)
                np_trend_df["Growth Label"] = np_trend_df["Growth %"].apply(
                    lambda value: f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"
                )

                fig_np_trend = go.Figure()
                fig_np_trend.add_trace(go.Bar(
                    x=np_trend_df["Period"], y=np_trend_df["LY Display"],
                    name=f"LY ({prev_fy})",
                    marker=dict(color="#d8dee9", line=dict(color="#94a3b8", width=1.2)),
                    text=np_trend_df["LY Display"], texttemplate="%{text:.2f}", textposition="outside",
                    textfont=dict(size=10, color="#475569", family="Arial"), cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>LY Net Profit: ₹%{{y:.2f}} {unit}<extra></extra>",
                ))
                fig_np_trend.add_trace(go.Bar(
                    x=np_trend_df["Period"], y=np_trend_df["CY Display"],
                    name=f"Current ({fy})",
                    marker=dict(color="#14b8a6", line=dict(color="#0f766e", width=1.3)),
                    text=np_trend_df["CY Display"], texttemplate="%{text:.2f}", textposition="outside",
                    textfont=dict(size=10, color="#0f766e", family="Arial"), cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>Net Profit: ₹%{{y:.2f}} {unit}<extra></extra>",
                ))

                trend_abs_max = max(float(pd.concat([np_trend_df["CY Display"].abs(), np_trend_df["LY Display"].abs()]).max() or 0), 1.0)
                if len(np_trend_df) <= 40:
                    for _, trend_row in np_trend_df.iterrows():
                        growth_value = float(trend_row["Growth %"] or 0)
                        current_value = float(trend_row["CY Display"] or 0)
                        previous_value = float(trend_row["LY Display"] or 0)
                        positive_top = max(current_value, previous_value, 0)
                        negative_bottom = min(current_value, previous_value, 0)
                        gap = trend_abs_max * (0.20 if np_trend_type == "Monthly" else 0.14)
                        annotation_y = positive_top + gap if positive_top > 0 else negative_bottom - gap
                        fig_np_trend.add_annotation(
                            x=trend_row["Period"], y=annotation_y,
                            text=trend_row["Growth Label"], showarrow=False,
                            font=dict(size=10, color="#15803d" if growth_value >= 0 else "#dc2626", family="Arial"),
                        )

                fig_np_trend.add_hline(y=0, line_width=1, line_color="#64748b")
                fig_np_trend.update_layout(
                    barmode="group", height=300, margin=dict(l=6, r=6, t=34, b=4),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#fbfdff",
                    legend=dict(orientation="h", yanchor="bottom", y=1.04, x=0, font=dict(size=10)),
                    xaxis_title="", yaxis_title=f"Net Profit ({unit})",
                    bargap=0.22, bargroupgap=0.08,
                )
                fig_np_trend.update_xaxes(showgrid=False)
                fig_np_trend.update_yaxes(showgrid=False)
                st.plotly_chart(fig_np_trend, width="stretch", config={"displayModeBar": False})


    # P&L and Net Profit period-growth charts above the Branch Monthly Avg insight.
    pnl_period_col, np_period_col = st.columns([1, 1], gap="medium")

    def _period_growth(values):
        result = pd.Series(index=values.index, dtype="float64")
        if len(values):
            result.iloc[0] = float("nan")
        for idx in range(1, len(values)):
            previous_value = float(values.iloc[idx - 1] or 0)
            current_value = float(values.iloc[idx] or 0)
            result.iloc[idx] = (
                ((current_value - previous_value) / abs(previous_value)) * 100
                if previous_value != 0 else float("nan")
            )
        return result

    def _growth_axis_range(values):
        clean = pd.to_numeric(values, errors="coerce").dropna()
        if clean.empty:
            return [-100, 100]
        low = float(clean.min())
        high = float(clean.max())
        pad = max((high - low) * 0.30, 18.0)
        return [min(low - pad, -10), max(high + pad, 10)]

    with pnl_period_col:
        # --------------------------------------------------------
        # P&L W / M / Q
        # --------------------------------------------------------
        with st.container(border=True):
            pnl_period_options = ["W", "M", "Q"]
            pnl_period = st.session_state.get("np_pnl_period_value", "M")
            if pnl_period not in pnl_period_options:
                pnl_period = "M"
                st.session_state["np_pnl_period_value"] = "M"

            pnl_title_col, pnl_btn_col = st.columns(
                [2.4, 1.0], gap="small", vertical_alignment="center"
            )
            pnl_period_name = {
                "W": "Weekly",
                "M": "Monthly",
                "Q": "Quarterly",
            }[pnl_period]

            with pnl_title_col:
                st.markdown(
                    f'<div class="np-section-title">{pnl_period_name} '
                    f'P&amp;L &amp; Growth</div>',
                    unsafe_allow_html=True,
                )

            with pnl_btn_col:
                pnl_btn_cols = st.columns(3, gap="small")
                for period_index, period_label in enumerate(pnl_period_options):
                    with pnl_btn_cols[period_index]:
                        if st.button(
                            period_label,
                            key=f"np_pnl_trend_btn_pnl_period_{period_index}",
                            type="primary" if pnl_period == period_label else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["np_pnl_period_value"] = period_label
                            st.rerun()

            pnl_period_df = pd.DataFrame()
            pnl_period_error = None

            if pnl_period == "W":
                if "grdt" not in insight_df.columns:
                    pnl_period_error = "Weekly P&L is unavailable because GR date is missing."
                else:
                    pnl_week = insight_df[["grdt", "PNL"]].copy()
                    pnl_week["grdt"] = pd.to_datetime(
                        pnl_week["grdt"], errors="coerce"
                    )
                    pnl_week = pnl_week[pnl_week["grdt"].notna()]
                    if pnl_week.empty:
                        pnl_period_error = "Weekly P&L is unavailable for the selected filters."
                    else:
                        pnl_week["Week No"] = (
                            (
                                pnl_week["grdt"].dt.normalize()
                                - pd.Timestamp(start_date)
                            ).dt.days // 7
                        ).astype(int) + 1
                        pnl_period_df = (
                            pnl_week.groupby("Week No", as_index=False)["PNL"]
                            .sum()
                            .sort_values("Week No")
                            .reset_index(drop=True)
                        )
                        pnl_period_df["Period"] = (
                            "W" + pnl_period_df["Week No"].astype(str)
                        )

            elif pnl_period == "Q":
                if "QUARTER" not in insight_df.columns:
                    pnl_period_error = "Quarterly P&L is unavailable."
                else:
                    pnl_period_df = (
                        insight_df.groupby("QUARTER", as_index=False)["PNL"]
                        .sum()
                    )
                    pnl_period_df["QUARTER"] = pd.Categorical(
                        pnl_period_df["QUARTER"],
                        categories=QUARTER_ORDER,
                        ordered=True,
                    )
                    pnl_period_df = (
                        pnl_period_df.sort_values("QUARTER")
                        .reset_index(drop=True)
                    )
                    pnl_period_df["Period"] = pnl_period_df["QUARTER"].astype(str)

            else:
                pnl_period_df = (
                    insight_df.groupby("MONTH", as_index=False)["PNL"]
                    .sum()
                )
                pnl_period_df["MONTH"] = pd.Categorical(
                    pnl_period_df["MONTH"],
                    categories=MONTH_ORDER,
                    ordered=True,
                )
                pnl_period_df = (
                    pnl_period_df.sort_values("MONTH")
                    .reset_index(drop=True)
                )
                pnl_period_df["Period"] = pnl_period_df["MONTH"].astype(str)

            if pnl_period_error:
                st.info(pnl_period_error)
            elif pnl_period_df.empty:
                st.info(f"No {pnl_period_name.lower()} P&L data is available.")
            else:
                pnl_period_df["Display"] = (
                    pd.to_numeric(
                        pnl_period_df["PNL"], errors="coerce"
                    ).fillna(0.0) / divisor
                )
                pnl_period_df["Growth"] = _period_growth(
                    pnl_period_df["PNL"]
                )
                pnl_period_df["Growth Label"] = pnl_period_df["Growth"].apply(
                    lambda value: (
                        f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"
                        if pd.notna(value) else ""
                    )
                )
                pnl_growth_colors = [
                    "#16a34a"
                    if pd.notna(value) and value >= 0
                    else "#dc2626"
                    for value in pnl_period_df["Growth"]
                ]

                fig_period_pnl = go.Figure()
                fig_period_pnl.add_trace(
                    go.Bar(
                        x=pnl_period_df["Period"],
                        y=pnl_period_df["Display"],
                        name="P&L",
                        marker=dict(
                            color="#99f6e4",
                            line=dict(color="#0f766e", width=1.4),
                        ),
                        text=pnl_period_df["Display"],
                        texttemplate="₹%{text:.2f}",
                        textposition="outside",
                        textfont=dict(
                            size=9, color="#0f766e", family="Arial"
                        ),
                        cliponaxis=False,
                        hovertemplate=(
                            f"<b>%{{x}}</b><br>"
                            f"P&L: ₹%{{y:.2f}} {unit}<extra></extra>"
                        ),
                    )
                )
                fig_period_pnl.add_trace(
                    go.Scatter(
                        x=pnl_period_df["Period"],
                        y=pnl_period_df["Growth"],
                        name=f"{pnl_period_name} Growth",
                        mode="lines+markers+text",
                        yaxis="y2",
                        line=dict(color="#7c3aed", width=2.6),
                        marker=dict(
                            size=7,
                            color=pnl_growth_colors,
                            line=dict(color="#ffffff", width=1.5),
                        ),
                        text=pnl_period_df["Growth Label"],
                        textposition="top center",
                        textfont=dict(size=10, color="#6d28d9"),
                        connectgaps=False,
                        hovertemplate=(
                            f"<b>%{{x}}</b><br>{pnl_period_name} "
                            "Growth: %{y:.1f}%<extra></extra>"
                        ),
                    )
                )

                fig_period_pnl.add_hline(
                    y=0, line_color="#94a3b8", line_width=1
                )
                fig_period_pnl.update_layout(
                    height=235,
                    margin=dict(l=4, r=10, t=34, b=2),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="#fbfdff",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.03,
                        x=0,
                        font=dict(size=9),
                    ),
                    bargap=0.30,
                    xaxis=dict(showgrid=False, tickfont=dict(size=9)),
                    yaxis=dict(
                        title=f"P&L ({unit})",
                        showgrid=False,
                        tickfont=dict(size=9),
                        title_font=dict(size=10),
                    ),
                    yaxis2=dict(
                        title="Growth %",
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        ticksuffix="%",
                        tickfont=dict(size=9),
                        title_font=dict(size=10),
                        range=_growth_axis_range(
                            pnl_period_df["Growth"]
                        ),
                    ),
                )
                st.plotly_chart(
                    fig_period_pnl,
                    width="stretch",
                    config={"displayModeBar": False},
                )

    with np_period_col:
        # --------------------------------------------------------
        # NET PROFIT W / M / Q
        # --------------------------------------------------------
        with st.container(border=True):
            np_period_options = ["W", "M", "Q"]
            np_period = st.session_state.get("np_net_profit_period_value", "M")
            if np_period not in np_period_options:
                np_period = "M"
                st.session_state["np_net_profit_period_value"] = "M"

            np_title_col, np_btn_col = st.columns(
                [2.4, 1.0], gap="small", vertical_alignment="center"
            )
            np_period_name = {
                "W": "Weekly",
                "M": "Monthly",
                "Q": "Quarterly",
            }[np_period]

            with np_title_col:
                st.markdown(
                    f'<div class="np-section-title">{np_period_name} '
                    f'Net Profit &amp; Growth</div>',
                    unsafe_allow_html=True,
                )

            with np_btn_col:
                np_btn_cols = st.columns(3, gap="small")
                for period_index, period_label in enumerate(np_period_options):
                    with np_btn_cols[period_index]:
                        if st.button(
                            period_label,
                            key=f"np_pnl_trend_btn_netprofit_period_{period_index}",
                            type="primary" if np_period == period_label else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state[
                                "np_net_profit_period_value"
                            ] = period_label
                            st.rerun()

            if (
                net_profit_df is None
                or net_profit_df.empty
                or "NET_PROFIT" not in net_profit_df.columns
            ):
                st.info("Net Profit trend is not available for the selected filters.")
            else:
                net_period_df = pd.DataFrame()
                net_period_error = None

                if np_period == "W":
                    net_date_col = _find_column(
                        net_profit_df,
                        "grdt",
                        "grdate",
                        "bookingdate",
                        "date",
                    )
                    if net_date_col is None:
                        net_period_error = (
                            "Weekly Net Profit cannot be calculated from the "
                            "current Net Profit dataset because it has no "
                            "transaction/date column."
                        )
                    else:
                        net_week = net_profit_df[
                            [net_date_col, "NET_PROFIT"]
                        ].copy()
                        net_week[net_date_col] = pd.to_datetime(
                            net_week[net_date_col], errors="coerce"
                        )
                        net_week = net_week[
                            net_week[net_date_col].notna()
                        ]
                        if net_week.empty:
                            net_period_error = (
                                "Weekly Net Profit is unavailable for the "
                                "selected filters."
                            )
                        else:
                            net_week["Week No"] = (
                                (
                                    net_week[net_date_col].dt.normalize()
                                    - pd.Timestamp(start_date)
                                ).dt.days // 7
                            ).astype(int) + 1
                            net_period_df = (
                                net_week.groupby(
                                    "Week No", as_index=False
                                )["NET_PROFIT"]
                                .sum()
                                .sort_values("Week No")
                                .reset_index(drop=True)
                            )
                            net_period_df["Period"] = (
                                "W" + net_period_df["Week No"].astype(str)
                            )

                elif np_period == "Q":
                    if "QUARTER" not in net_profit_df.columns:
                        net_period_error = (
                            "Quarterly Net Profit is unavailable."
                        )
                    else:
                        net_period_df = (
                            net_profit_df.groupby(
                                "QUARTER", as_index=False
                            )["NET_PROFIT"]
                            .sum()
                        )
                        net_period_df["QUARTER"] = pd.Categorical(
                            net_period_df["QUARTER"],
                            categories=QUARTER_ORDER,
                            ordered=True,
                        )
                        net_period_df = (
                            net_period_df.sort_values("QUARTER")
                            .reset_index(drop=True)
                        )
                        net_period_df["Period"] = (
                            net_period_df["QUARTER"].astype(str)
                        )

                else:
                    if "MONTH" not in net_profit_df.columns:
                        net_period_error = (
                            "Monthly Net Profit is unavailable."
                        )
                    else:
                        net_period_df = (
                            net_profit_df.groupby(
                                "MONTH", as_index=False
                            )["NET_PROFIT"]
                            .sum()
                        )
                        net_period_df["MONTH"] = pd.Categorical(
                            net_period_df["MONTH"],
                            categories=MONTH_ORDER,
                            ordered=True,
                        )
                        net_period_df = (
                            net_period_df.sort_values("MONTH")
                            .reset_index(drop=True)
                        )
                        net_period_df["Period"] = (
                            net_period_df["MONTH"].astype(str)
                        )

                if net_period_error:
                    st.info(net_period_error)
                elif net_period_df.empty:
                    st.info(
                        f"No {np_period_name.lower()} Net Profit data is available."
                    )
                else:
                    net_period_df["Display"] = (
                        pd.to_numeric(
                            net_period_df["NET_PROFIT"],
                            errors="coerce",
                        ).fillna(0.0) / divisor
                    )
                    net_period_df["Growth"] = _period_growth(
                        net_period_df["NET_PROFIT"]
                    )
                    net_period_df["Growth Label"] = (
                        net_period_df["Growth"].apply(
                            lambda value: (
                                f"{'▲' if value >= 0 else '▼'} "
                                f"{abs(value):.1f}%"
                                if pd.notna(value) else ""
                            )
                        )
                    )
                    net_growth_colors = [
                        "#16a34a"
                        if pd.notna(value) and value >= 0
                        else "#dc2626"
                        for value in net_period_df["Growth"]
                    ]

                    fig_period_np = go.Figure()
                    fig_period_np.add_trace(
                        go.Bar(
                            x=net_period_df["Period"],
                            y=net_period_df["Display"],
                            name="Net Profit",
                            marker=dict(
                                color="#ddd6fe",
                                line=dict(
                                    color="#7c3aed", width=1.4
                                ),
                            ),
                            text=net_period_df["Display"],
                            texttemplate="₹%{text:.2f}",
                            textposition="outside",
                            textfont=dict(
                                size=9,
                                color="#6d28d9",
                                family="Arial",
                            ),
                            cliponaxis=False,
                            hovertemplate=(
                                f"<b>%{{x}}</b><br>"
                                f"Net Profit: ₹%{{y:.2f}} "
                                f"{unit}<extra></extra>"
                            ),
                        )
                    )
                    fig_period_np.add_trace(
                        go.Scatter(
                            x=net_period_df["Period"],
                            y=net_period_df["Growth"],
                            name=f"{np_period_name} Growth",
                            mode="lines+markers+text",
                            yaxis="y2",
                            line=dict(
                                color="#f59e0b", width=2.6
                            ),
                            marker=dict(
                                size=7,
                                color=net_growth_colors,
                                line=dict(
                                    color="#ffffff", width=1.5
                                ),
                            ),
                            text=net_period_df["Growth Label"],
                            textposition="top center",
                            textfont=dict(
                                size=10, color="#b45309"
                            ),
                            connectgaps=False,
                            hovertemplate=(
                                f"<b>%{{x}}</b><br>"
                                f"{np_period_name} Growth: "
                                "%{y:.1f}%<extra></extra>"
                            ),
                        )
                    )

                    fig_period_np.add_hline(
                        y=0, line_color="#94a3b8", line_width=1
                    )
                    fig_period_np.update_layout(
                        height=235,
                        margin=dict(l=4, r=10, t=34, b=2),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="#fbfdff",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.03,
                            x=0,
                            font=dict(size=9),
                        ),
                        bargap=0.30,
                        xaxis=dict(
                            showgrid=False, tickfont=dict(size=9)
                        ),
                        yaxis=dict(
                            title=f"Net Profit ({unit})",
                            showgrid=False,
                            tickfont=dict(size=9),
                            title_font=dict(size=10),
                        ),
                        yaxis2=dict(
                            title="Growth %",
                            overlaying="y",
                            side="right",
                            showgrid=False,
                            ticksuffix="%",
                            tickfont=dict(size=9),
                            title_font=dict(size=10),
                            range=_growth_axis_range(
                                net_period_df["Growth"]
                            ),
                        ),
                    )
                    st.plotly_chart(
                        fig_period_np,
                        width="stretch",
                        config={"displayModeBar": False},
                    )

# Full-width original-style Branch Monthly Avg P&L insight.
    with st.container(border=True):
        st.markdown(
            '<div class="np-section-title" '
            'style="font-size:16px;margin:2px 0 10px 1px;line-height:1.25;">'
            'Branches by Monthly Avg P&amp;L</div>',
            unsafe_allow_html=True,
        )

        if "branch" not in insight_df.columns:
            st.info("Branch is not available in P&L insight data.")
        else:
            current_month_count = max(
                int(insight_df["FIN_MONTH"].dropna().nunique()), 1
            )
            previous_month_count = (
                max(int(insight_prev_df["FIN_MONTH"].dropna().nunique()), 1)
                if (
                    insight_prev_df is not None
                    and not insight_prev_df.empty
                    and "FIN_MONTH" in insight_prev_df.columns
                )
                else current_month_count
            )

            current_branch_avg = (
                insight_df.groupby("branch", dropna=False, as_index=False)["PNL"]
                .sum()
                .rename(columns={"PNL": "CY_PNL"})
            )
            current_branch_avg["branch"] = (
                current_branch_avg["branch"]
                .fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
            )

            if (
                insight_prev_df is not None
                and not insight_prev_df.empty
                and {"branch", "PNL"}.issubset(insight_prev_df.columns)
            ):
                previous_branch_avg = (
                    insight_prev_df.groupby(
                        "branch", dropna=False, as_index=False
                    )["PNL"]
                    .sum()
                    .rename(columns={"PNL": "LY_PNL"})
                )
                previous_branch_avg["branch"] = (
                    previous_branch_avg["branch"]
                    .fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
                )
            else:
                previous_branch_avg = pd.DataFrame(
                    columns=["branch", "LY_PNL"]
                )

            branch_avg = current_branch_avg.merge(
                previous_branch_avg, on="branch", how="left"
            )
            branch_avg["LY_PNL"] = pd.to_numeric(
                branch_avg["LY_PNL"], errors="coerce"
            ).fillna(0.0)
            branch_avg["Monthly Avg P&L"] = (
                branch_avg["CY_PNL"] / current_month_count
            )
            branch_avg["LY Monthly Avg P&L"] = (
                branch_avg["LY_PNL"] / previous_month_count
            )

            slab_options = [
                "All", "Loss", "₹0–5 Lac", "₹5–10 Lac",
                "₹10–15 Lac", "₹15–25 Lac",
                "₹25–50 Lac", "₹50 Lac & Above",
            ]
            selected_slab = st.session_state.get(
                "np_pnl_insight_branch_slab", "All"
            )
            if selected_slab not in slab_options:
                selected_slab = "All"
                st.session_state["np_pnl_insight_branch_slab"] = "All"

            # Full-width panel: all 8 buttons fit in a single row like P&L dashboard.
            slab_button_cols = st.columns(len(slab_options), gap="small")
            for slab_index, slab_label in enumerate(slab_options):
                with slab_button_cols[slab_index]:
                    if st.button(
                        slab_label,
                        key=f"np_pnl_branch_slab_btn_{slab_index}",
                        type=(
                            "primary"
                            if selected_slab == slab_label
                            else "secondary"
                        ),
                        use_container_width=True,
                    ):
                        st.session_state[
                            "np_pnl_insight_branch_slab"
                        ] = slab_label
                        st.rerun()

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

            scoped = branch_avg.copy()
            slab_low, slab_high = slab_ranges[selected_slab]
            if selected_slab == "Loss":
                scoped = scoped[scoped["Monthly Avg P&L"] < 0]
            else:
                if slab_low is not None:
                    scoped = scoped[
                        scoped["Monthly Avg P&L"] >= slab_low
                    ]
                if slab_high is not None:
                    scoped = scoped[
                        scoped["Monthly Avg P&L"] < slab_high
                    ]

            scoped = scoped.sort_values(
                "Monthly Avg P&L", ascending=False
            ).reset_index(drop=True)

            total_abs_branch_pnl = float(
                branch_avg["Monthly Avg P&L"].abs().sum()
            )
            selected_cy_total = float(scoped["Monthly Avg P&L"].sum())
            selected_ly_total = float(scoped["LY Monthly Avg P&L"].sum())
            selected_share = (
                float(scoped["Monthly Avg P&L"].abs().sum())
                / total_abs_branch_pnl * 100
                if total_abs_branch_pnl else 0.0
            )
            selected_growth = (
                (selected_cy_total - selected_ly_total)
                / abs(selected_ly_total) * 100
                if selected_ly_total != 0
                else None
            )

            if selected_growth is None:
                summary_growth_html = (
                    '<span style="color:#7c3aed;font-weight:700;">NEW</span>'
                )
            else:
                summary_growth_color = (
                    "#16a34a" if selected_growth >= 0 else "#dc2626"
                )
                summary_growth_arrow = (
                    "▲" if selected_growth >= 0 else "▼"
                )
                summary_growth_html = (
                    f'<span style="color:{summary_growth_color};'
                    f'font-weight:700;">{summary_growth_arrow} '
                    f'{abs(selected_growth):.1f}%</span>'
                )

            st.markdown(
                f'<div style="color:#31557d;font-size:12px;font-weight:500;'
                f'margin:8px 0 8px 1px;">'
                f'Showing {len(scoped):,} branches in {escape(selected_slab)}. '
                f'CY Avg P&amp;L: <b>₹{selected_cy_total / divisor:,.2f} '
                f'{escape(unit)}</b> · '
                f'LY Avg P&amp;L: <b>₹{selected_ly_total / divisor:,.2f} '
                f'{escape(unit)}</b> · '
                f'Share: <b>{selected_share:.2f}%</b> · '
                f'Growth: {summary_growth_html}. Scroll to view all.'
                f'</div>',
                unsafe_allow_html=True,
            )

            if scoped.empty:
                st.info(
                    f"No branch falls in the {selected_slab} "
                    "monthly-average P&L slab."
                )
            else:
                max_abs_value = max(
                    float(scoped["Monthly Avg P&L"].abs().max()), 1.0
                )
                rows = []

                for idx, row in scoped.iterrows():
                    cy_value = float(row["Monthly Avg P&L"] or 0)
                    ly_value = float(row["LY Monthly Avg P&L"] or 0)
                    width_pct = min(
                        abs(cy_value) / max_abs_value * 100, 100
                    )
                    fill_color = (
                        "#2563eb" if cy_value >= 0 else "#dc2626"
                    )
                    amount_color = (
                        "#111827" if cy_value >= 0 else "#dc2626"
                    )
                    branch_name = escape(str(row["branch"]))
                    share = (
                        abs(cy_value) / total_abs_branch_pnl * 100
                        if total_abs_branch_pnl else 0.0
                    )
                    growth = (
                        (cy_value - ly_value) / abs(ly_value) * 100
                        if ly_value != 0 else None
                    )

                    if growth is None:
                        growth_html = (
                            '<span style="color:#7c3aed;'
                            'font-weight:700;">NEW</span>'
                        )
                    else:
                        growth_color = (
                            "#16a34a" if growth >= 0 else "#dc2626"
                        )
                        growth_arrow = "▲" if growth >= 0 else "▼"
                        growth_html = (
                            f'<span style="color:{growth_color};'
                            f'font-weight:700;">{growth_arrow} '
                            f'{abs(growth):.1f}%</span>'
                        )

                    rows.append(
                        '<div style="margin-bottom:7px;padding:8px 10px;'
                        'border:1px solid #dbe4ef;border-radius:12px;'
                        'background:#fbfdff;">'
                        '<div style="display:grid;'
                        'grid-template-columns:44px minmax(180px,240px) '
                        'minmax(220px,1fr) 115px 105px 78px 92px;'
                        'align-items:center;gap:10px;">'
                        f'<div style="text-align:center;font-size:13px;'
                        f'color:#334155;">{idx + 1}</div>'
                        f'<div style="font-size:14px;color:#0f2744;'
                        f'white-space:nowrap;overflow:hidden;'
                        f'text-overflow:ellipsis;">{branch_name}</div>'
                        '<div style="height:7px;background:#e8eef5;'
                        'border-radius:999px;overflow:hidden;">'
                        f'<div style="width:{width_pct:.1f}%;height:7px;'
                        f'background:{fill_color};border-radius:999px;">'
                        '</div></div>'
                        f'<div style="text-align:right;color:{amount_color};'
                        f'font-size:13px;font-weight:700;white-space:nowrap;">'
                        f'₹{cy_value / divisor:,.2f} {escape(unit)}</div>'
                        f'<div style="text-align:right;color:#64748b;'
                        f'font-size:12px;white-space:nowrap;">'
                        f'₹{ly_value / divisor:,.2f} {escape(unit)}</div>'
                        f'<div style="text-align:right;color:#31557d;'
                        f'font-size:12px;font-weight:600;white-space:nowrap;">'
                        f'{share:.2f}%</div>'
                        f'<div style="text-align:right;font-size:12px;'
                        f'white-space:nowrap;">{growth_html}</div>'
                        '</div></div>'
                    )

                header = (
                    '<div style="display:grid;'
                    'grid-template-columns:44px minmax(180px,240px) '
                    'minmax(220px,1fr) 115px 105px 78px 92px;'
                    'align-items:center;gap:10px;padding:0 10px 6px;'
                    'color:#64748b;font-size:10px;font-weight:700;">'
                    '<div style="text-align:center;">#</div>'
                    '<div>Branch</div>'
                    '<div>P&amp;L Scale</div>'
                    '<div style="text-align:right;">CY Avg</div>'
                    '<div style="text-align:right;">LY Avg</div>'
                    '<div style="text-align:right;">Share</div>'
                    '<div style="text-align:right;">Growth</div>'
                    '</div>'
                )
                branch_html = (
                    header
                    + '<div style="max-height:500px;overflow-y:auto;'
                    'padding-right:3px;">'
                    + "".join(rows)
                    + "</div>"
                )

                if hasattr(st, "html"):
                    st.html(branch_html)
                else:
                    st.markdown(branch_html, unsafe_allow_html=True)


    customer_col, route_col = st.columns(2, gap="medium")
    customer_field = "Consignee" if insight_view == "Destination" else "Consignor"
    with customer_col:
        with st.container(border=True):
            _top_pnl_insight_table(
                insight_df, insight_prev_df, customer_field, "Customers", divisor, unit, "np_pnl_customer",
                subtitle=("Customer basis: Consignee | Current FY P&L, share and YoY movement." if insight_view == "Destination" else "Customer basis: Consignor | Current FY P&L, share and YoY movement."),
            )
    with route_col:
        with st.container(border=True):
            _top_pnl_insight_table(
                insight_df, insight_prev_df, "Route", "Routes", divisor, unit, "np_pnl_route",
                subtitle=("Destination → Origin | Current FY P&L, share and YoY movement." if insight_view == "Destination" else "Origin → Destination | Current FY P&L, share and YoY movement."),
            )


# ============================================================
# DASHBOARD
# ============================================================

    return insight_df, insight_prev_df


def show_net_profit_dashboard():
    _inject_css()

    st.markdown(
        """
        <div class="np-header">
            <div>
                <div class="np-title">Net Profit Analysis</div>
                <div class="np-subtitle">Business, P&L and indirect expense performance by branch</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    # Use whichever hierarchy columns are actually available.
    with filter_cols[1]:
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
    circle_scope = apply_multi_filter(circle_scope, "zone", zones)
    circle_options = safe_options(circle_scope, "circle")

    with filter_cols[2]:
        circles = st.multiselect(
            "Circle",
            circle_options,
            key="np_circle",
            placeholder="All circles",
            disabled=("circle" not in df.columns or not circle_options),
        )

    # Branch choices follow the selected Zone/Circle scope.
    branch_scope = df.copy()
    branch_scope = apply_multi_filter(branch_scope, "zone", zones)
    branch_scope = apply_multi_filter(branch_scope, "circle", circles)
    branch_options = safe_options(branch_scope, "BRANCH")

    with filter_cols[3]:
        branches = st.multiselect(
            "Branch",
            branch_options,
            key="np_branch",
            placeholder="All branches",
        )

    # Quarter choices come only from rows available in the selected FY and
    # current Zone -> Circle -> Branch scope.
    quarter_scope = branch_scope.copy()
    quarter_scope = apply_multi_filter(quarter_scope, "BRANCH", branches)
    available_quarters = set(safe_options(quarter_scope, "QUARTER"))
    quarter_options = [
        quarter for quarter in QUARTER_ORDER
        if quarter in available_quarters
    ]
    if "np_quarter" in st.session_state:
        st.session_state["np_quarter"] = [
            quarter for quarter in st.session_state["np_quarter"]
            if quarter in quarter_options
        ]

    with filter_cols[4]:
        quarters = st.multiselect(
            "Quarter",
            quarter_options,
            key="np_quarter",
            placeholder="All quarters",
            disabled=not quarter_options,
        )

    # Month choices cascade from the selected FY, hierarchy and Quarter.
    month_scope = quarter_scope.copy()
    month_scope = apply_multi_filter(month_scope, "QUARTER", quarters)
    available_months = set(safe_options(month_scope, "MONTH"))
    month_options = [
        month for month in MONTH_ORDER
        if month in available_months
    ]
    if "np_month" in st.session_state:
        st.session_state["np_month"] = [
            month for month in st.session_state["np_month"]
            if month in month_options
        ]

    with filter_cols[5]:
        months = st.multiselect(
            "Month",
            month_options,
            key="np_month",
            placeholder="All months",
            disabled=not month_options,
        )

    with filter_cols[6]:
        conversion_type = st.selectbox(
            "₹ Conversion",
            ["Crore", "Lac"],
            key="np_conversion",
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

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    kpis = [
        ("Origin Business", booking_business_current, booking_business_previous, False, False),
    ]

    # In All Branches mode Delivery Business must not be shown at all.
    if not all_branches:
        kpis.append(
            (
                "Destination Business",
                current["destination_business"],
                previous["destination_business"],
                False,
                False,
            )
        )

    kpis.append(
        ("Origin P&L", current["origin_pnl"], previous["origin_pnl"], False, False)
    )

    # Match the business-card behavior: Destination P&L is relevant only when
    # the user explicitly selects one or more branches.
    if not all_branches:
        kpis.append(
            ("Destination P&L", current["destination_pnl"], previous["destination_pnl"], False, False)
        )

    kpis.extend(
        [
            ("Gross P&L", current["combined_pnl"], previous["combined_pnl"], False, False),
            ("Indirect Exp", current["total_expense"], previous["total_expense"], True, False),
            ("Net Profit", current["net_profit"], previous["net_profit"], False, False),
            ("Net Profit %", current["margin"], previous["margin"], False, False),
        ]
    )

    kpi_cols = st.columns(len(kpis), gap=None)

    for index, (title, cy, ly, reverse_good, disabled) in enumerate(kpis):
        with kpi_cols[index]:
            render_kpi_card(
                title,
                cy,
                ly,
                conversion_type=conversion_type,
                percent=(title == "Net Profit %"),
                reverse_good=reverse_good,
                disabled=disabled,
            )

    # --------------------------------------------------------
    # KPI ROW 2: OVERHEAD BREAKUP
    # --------------------------------------------------------

    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

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
    # BRANCH SUMMARY (feeds Branch Net Profit Detail; no chart rendered)
    # --------------------------------------------------------

    branch_summary = (
        df.groupby(["BRANCHCODE", "BRANCH"], as_index=False, dropna=False)
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
    branch_summary["P&L %"] = 0.0
    valid_business = branch_summary["Revenue"].ne(0)
    branch_summary.loc[valid_business, "P&L %"] = (
        branch_summary.loc[valid_business, "Combined_PNL"]
        / branch_summary.loc[valid_business, "Revenue"] * 100
    )
    branch_summary["Net Profit Margin %"] = 0.0
    valid_income = branch_summary["Total_Income"].ne(0)
    branch_summary.loc[valid_income, "Net Profit Margin %"] = (
        branch_summary.loc[valid_income, "Net_Profit"]
        / branch_summary.loc[valid_income, "Total_Income"] * 100
    )
    branch_summary = branch_summary.sort_values("Net_Profit", ascending=False).reset_index(drop=True)

    # --------------------------------------------------------
    # PHASE 1: P&L INSIGHTS (ISOLATED; EXISTING NET PROFIT KPIs/TABLES UNCHANGED)
    # --------------------------------------------------------

    pnl_detail_df, pnl_detail_prev_df = _render_phase1_pnl_insights(
        start_date=start_date,
        end_date=end_date,
        prev_start=prev_start,
        prev_end=prev_end,
        fy=fy,
        prev_fy=prev_fy,
        zones=zones,
        circles=circles,
        branches=branches,
        quarters=quarters,
        months=months,
        valid_branches=valid_branches,
        divisor=divisor,
        unit=unit,
        net_profit_df=df,
        net_profit_prev_df=prev_df,
    )

    # --------------------------------------------------------
    # DETAIL RENDER TABS - P&L DASHBOARD STYLE
    # --------------------------------------------------------

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        /* Bottom render tabs: four-color matrix style */
        div[class*="st-key-np_bottom_render_tabs"] div[data-baseweb="tab-list"] {
            gap: 10px !important;
            align-items:flex-end !important;
            background:#ffffff !important;
            border-bottom:1px solid #d8e1ea !important;
            padding:0 12px !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"] {
            color:#ffffff !important;
            border:0 !important;
            border-radius:7px 7px 0 0 !important;
            min-height:46px !important;
            padding:10px 20px !important;
            font-size:13px !important;
            font-weight: 700 !important;
            opacity:.88 !important;
            box-shadow:inset 0 -3px 0 rgba(15,23,42,.10) !important;
            transition:transform .15s ease,opacity .15s ease,filter .15s ease !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"] p,
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"] span {
            color:inherit !important;
            font-size:13px !important;
            font-weight:700 !important;
            white-space:nowrap !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"]:nth-of-type(1) {
            background:#8eafbd !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"]:nth-of-type(2) {
            background:#9dbba9 !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"]:nth-of-type(3) {
            background:#ff454d !important;
            color:#111827 !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"]:hover {
            opacity:1 !important;
            filter:saturate(1.08) brightness(.98) !important;
            transform:translateY(-1px) !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] button[data-baseweb="tab"][aria-selected="true"] {
            opacity:1 !important;
            transform:translateY(-2px) !important;
            filter:saturate(1.18) brightness(.94) !important;
            box-shadow:inset 0 -4px 0 rgba(15,23,42,.20),0 4px 9px rgba(15,23,42,.13) !important;
        }
        div[class*="st-key-np_bottom_render_tabs"] div[data-baseweb="tab-highlight"] {
            display: none !important;
        }

        /* Streamlit-version-safe selectors. Some releases render tabs with
           role attributes instead of BaseWeb data attributes. */
        .st-key-np_bottom_render_tabs [role="tablist"],
        div[data-testid="stVerticalBlock"]:has(.np-bottom-tabs-marker) [role="tablist"] {
            gap:10px !important;
            align-items:flex-end !important;
            background:#ffffff !important;
            border-bottom:1px solid #d8e1ea !important;
            padding:0 12px !important;
        }
        .st-key-np_bottom_render_tabs [role="tab"],
        div[data-testid="stVerticalBlock"]:has(.np-bottom-tabs-marker) [role="tab"] {
            color:#ffffff !important;
            border:0 !important;
            border-radius:0 !important;
            min-height:46px !important;
            padding:10px 20px !important;
            font-size:13px !important;
            font-weight:700 !important;
            opacity:.92 !important;
            box-shadow:none !important;
        }
        .st-key-np_bottom_render_tabs [role="tab"]:nth-of-type(1),
        div[data-testid="stVerticalBlock"]:has(.np-bottom-tabs-marker) [role="tab"]:nth-of-type(1) {
            background:#8eafbd !important;
        }
        .st-key-np_bottom_render_tabs [role="tab"]:nth-of-type(2),
        div[data-testid="stVerticalBlock"]:has(.np-bottom-tabs-marker) [role="tab"]:nth-of-type(2) {
            background:#9dbba9 !important;
        }
        .st-key-np_bottom_render_tabs [role="tab"]:nth-of-type(3),
        div[data-testid="stVerticalBlock"]:has(.np-bottom-tabs-marker) [role="tab"]:nth-of-type(3) {
            background:#ff454d !important;
            color:#111827 !important;
        }
        .st-key-np_bottom_render_tabs [role="tab"][aria-selected="true"],
        div[data-testid="stVerticalBlock"]:has(.np-bottom-tabs-marker) [role="tab"][aria-selected="true"] {
            opacity:1 !important;
            filter:saturate(1.18) brightness(.92) !important;
            box-shadow:inset 0 -4px 0 rgba(15,23,42,.24) !important;
        }
        .st-key-np_bottom_render_tabs [data-baseweb="tab-highlight"],
        div[data-testid="stVerticalBlock"]:has(.np-bottom-tabs-marker) [data-baseweb="tab-highlight"] {
            display:none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="np_bottom_render_tabs"):
        st.markdown(
            '<span class="np-bottom-tabs-marker"></span>',
            unsafe_allow_html=True,
        )
        detail_tab, audit_tab, gr_tab = st.tabs(
            [
                "Branch Net Profit Detail",
                "Monthly Calculation Audit",
                "Detailed GR Records",
            ]
        )

    # --------------------------------------------------------
    # TAB 1: BRANCH NET PROFIT DETAIL
    # --------------------------------------------------------
    with detail_tab:
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
                "Revenue": f"Total Business ({unit})",
                "Booking_Business": f"Booking Business ({unit})",
                "Delivery_Business": f"Delivery Business ({unit})",
                "Origin_PNL": f"Origin P&L ({unit})",
                "Destination_PNL": f"Destination P&L ({unit})",
                "Combined_PNL": f"Gross P&L ({unit})",
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

        detail_columns = [
            "Branch Code",
            "Branch",
            f"Booking Business ({unit})",
            f"Delivery Business ({unit})",
            f"Total Business ({unit})",
            f"Origin P&L ({unit})",
            f"Destination P&L ({unit})",
            f"Gross P&L ({unit})",
            "P&L %",
            f"Salary ({unit})",
            f"Godown Rent ({unit})",
            f"Overhead Expense ({unit})",
            f"Claim ({unit})",
            f"Booking 6% ({unit})",
            f"Destination 5% ({unit})",
            f"Total Overhead ({unit})",
            f"Net Profit ({unit})",
            f"Total Income ({unit})",
            "Net Profit Margin %",
        ]
        display = display[
            [column for column in detail_columns if column in display.columns]
        ]

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            column_config={
                "P&L %": st.column_config.NumberColumn(
                    "P&L %",
                    format="%.2f%%",
                ),
                "Net Profit Margin %": st.column_config.NumberColumn(
                    "Net Profit Margin %",
                    format="%.2f%%",
                ),
            },
        )

        csv_data = display.to_csv(index=False).encode("utf-8-sig")

    # --------------------------------------------------------
    # TAB 2: MONTHLY CALCULATION AUDIT
    # --------------------------------------------------------
    with audit_tab:
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
            column for column in audit_columns if column in df.columns
        ]

        audit_display = df[audit_columns].copy()
        audit_sort = [
            column
            for column in ["BRANCH", "YEAR", "MONTHNO"]
            if column in audit_display.columns
        ]
        if audit_sort:
            audit_display = audit_display.sort_values(audit_sort)

        st.dataframe(
            audit_display,
            width="stretch",
            hide_index=True,
        )

    # --------------------------------------------------------
    # TAB 3: GR P&L DETAILED
    # Same filtered P&L insight source; no LOADTYPE filter is applied.
    # --------------------------------------------------------
    with gr_tab:
        if pnl_detail_df is None or pnl_detail_df.empty:
            st.info("No detailed GR records are available for the selected filters.")
        else:
            gr_columns_preferred = [
                "grno",
                "grdt",
                "COMPNAME",
                "zone",
                "circle",
                "branch",
                "GRTYPE",
                "Consignor",
                "Consignee",
                "Route",
                "REVENUE",
                "EXPENSE",
                "PNL",
                "FIN_MONTH",
                "MONTH",
                "QUARTER",
            ]
            gr_columns = [
                column
                for column in gr_columns_preferred
                if column in pnl_detail_df.columns
            ]

            # If the SP returns extra useful columns, keep the table focused on the
            # P&L dashboard's GR-detail dimensions rather than dumping every field.
            gr_display = pnl_detail_df[gr_columns].copy()

            if "grdt" in gr_display.columns:
                gr_display["grdt"] = pd.to_datetime(
                    gr_display["grdt"], errors="coerce"
                ).dt.strftime("%d-%m-%Y")

            for column in ["REVENUE", "EXPENSE", "PNL"]:
                if column in gr_display.columns:
                    gr_display[column] = (
                        pd.to_numeric(
                            gr_display[column], errors="coerce"
                        ).fillna(0.0) / divisor
                    )

            gr_display = gr_display.rename(
                columns={
                    "grno": "GR No",
                    "grdt": "GR Date",
                    "COMPNAME": "Company",
                    "zone": "Zone",
                    "circle": "Circle",
                    "branch": "Branch",
                    "GRTYPE": "GR Type",
                    "Consignor": "Consignor",
                    "Consignee": "Consignee",
                    "Route": "Route",
                    "REVENUE": f"Revenue ({unit})",
                    "EXPENSE": f"Expense ({unit})",
                    "PNL": f"P&L ({unit})",
                    "FIN_MONTH": "Fin Month",
                    "MONTH": "Month",
                    "QUARTER": "Quarter",
                }
            )

            st.dataframe(
                gr_display,
                width="stretch",
                hide_index=True,
                height=520,
            )

    # Keep CSV download as the final dashboard action.
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.download_button(
        "Download Net Profit CSV",
        data=csv_data,
        file_name=f"net_profit_dashboard_{fy}.csv",
        mime="text/csv",
        key="np_download",
    )

# Optional direct-run support.
if __name__ == "__main__":
    show_net_profit_dashboard()
