"""Stock Operations Control Tower - page-only UI for Sugam Dashboard.

This module intentionally styles only the Stock Operations page container.
It does not modify the application's sidebar, navigation, or global menu.
"""

from __future__ import annotations

import html
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.stock_branch_mast import load_stock_branch_mast
from services.stock_data_loader import load_stock_data


PALETTE = {
    "blue": "#2477df",
    "blue_dark": "#0b5aa7",
    "navy": "#0b3158",
    "cyan": "#11a8ae",
    "orange": "#f08a22",
    "purple": "#7b55df",
    "green": "#2caf67",
    "red": "#df3f4a",
    "text": "#17324f",
    "muted": "#718096",
    "border": "#dce6f0",
    "page": "#f4f8fc",
}

STOCK_ORDER = [
    "BOOKING STOCK",
    "IN-TRANSIT STOCK",
    "TRANSIT STOCK",
    "DELIVERY STOCK",
]


ZONE_COLOURS = {
    "NORTH EAST ZONE": "#2477df",
    "EAST ZONE": "#11a8ae",
    "NEPAL ZONE": "#7b55df",
    "NORTH ZONE": "#2caf67",
    "WEST ZONE": "#f08a22",
    "SOUTH ZONE": "#df3f4a",
    "CENTRAL ZONE": "#8a613d",
    "UNMAPPED": "#64748b",
}

ZONE_FALLBACK = [
    "#2477df", "#11a8ae", "#7b55df", "#2caf67",
    "#f08a22", "#df3f4a", "#8a613d", "#64748b",
]


LOAD_COLOURS = {
    "PTL": "#145fb3",
    "LTL": "#145fb3",
    "FTL": "#18b7bd",
    "UNKNOWN": "#94a3b8",
}


def _inject_css():
    """Apply styles only inside the Stock Operations page."""
    st.markdown(
        """
        <style>
        /* use full page width for this page only */
        .main .block-container, [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"]{max-width:100%!important;width:100%!important;padding-left:.65rem!important;padding-right:.65rem!important;padding-top:.2rem!important;}
        /* IMPORTANT: everything below is scoped to this page only. */
        .st-key-stock_page{
            background:#f4f8fc;
            border-radius:12px;
            padding:0 7px 8px 7px;
        }
        .st-key-stock_page [data-testid="stVerticalBlock"]{gap:.42rem!important}
        .st-key-stock_page [data-testid="stHorizontalBlock"]{gap:.52rem!important;align-items:stretch!important}

        /* dark page header */
        .st-key-stock_topbar{
            background:linear-gradient(90deg,#0a315a 0%,#0d4e82 58%,#0b3158 100%);
            border-radius:0 0 10px 10px;
            padding:10px 13px 8px 13px;
            box-shadow:0 5px 16px rgba(8,45,82,.15);
            margin-bottom:2px;
        }
        .stock-title-wrap{display:flex;align-items:center;gap:12px;height:44px}
        .stock-title-mark{
            width:7px;height:36px;border-radius:7px;
            background:linear-gradient(180deg,#34a9ff,#60d7ff);
            box-shadow:0 0 0 3px rgba(255,255,255,.08)
        }
        .stock-title{font:800 19px/1.08 "Segoe UI",Arial,sans-serif;color:#fff;letter-spacing:-.25px}
        .stock-subtitle{font:500 8.5px/1.2 "Segoe UI",Arial,sans-serif;color:#d8e9f8;margin-top:3px}
        .stock-live-wrap{height:44px;display:flex;align-items:center;justify-content:flex-end;gap:8px}
        .stock-live{
            display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;
            background:#2fbf69;color:#fff;font:800 7.5px "Segoe UI",Arial,sans-serif;letter-spacing:.3px
        }
        .stock-live:before{content:"";width:6px;height:6px;border-radius:50%;background:#d8ffe8}
        .stock-updated{font:600 7.5px "Segoe UI",Arial,sans-serif;color:#d5e6f7;white-space:nowrap}

        .st-key-stock_topbar div[data-testid="stTextInput"]{margin-top:5px}
        .st-key-stock_topbar div[data-testid="stTextInput"] input{
            min-height:31px!important;height:31px!important;
            background:#ffffff!important;
            border:1px solid #c9d7e6!important;
            color:#111827!important;border-radius:8px!important;
            font-size:9px!important;font-weight:800!important;
            -webkit-text-fill-color:#111827!important;
            caret-color:#111827!important;
        }
        .st-key-stock_topbar input, .st-key-stock_topbar textarea{color:#111827!important;font-weight:800!important;-webkit-text-fill-color:#111827!important;}
        .st-key-stock_topbar div[data-testid="stTextInput"] input::placeholder{
            color:#6b7280!important;opacity:1!important;font-weight:600!important;
            -webkit-text-fill-color:#6b7280!important;
        }

        /* filter row */
        .st-key-stock_filters{
            background:#fff;border:1px solid #dfe8f1;border-radius:10px;
            padding:6px 8px 7px 8px;box-shadow:0 2px 8px rgba(20,40,65,.04)
        }
        .st-key-stock_filters label,
        .st-key-stock_filters label p{
            font:700 7.4px/1.1 "Segoe UI",Arial,sans-serif!important;color:#4d6680!important;
            margin-bottom:2px!important
        }
        .st-key-stock_filters div[data-testid="stDateInput"] input,
        .st-key-stock_filters div[data-baseweb="select"]>div{
            min-height:31px!important;height:31px!important;border-radius:7px!important;
            border-color:#d7e2ee!important;background:#fff!important;font-size:8px!important
        }
        .st-key-stock_filters div[data-testid="stButton"] button{
            min-height:31px!important;height:31px!important;margin-top:15px!important;
            background:#2477df!important;border:0!important;border-radius:7px!important;color:white!important;
            font-size:8px!important;font-weight:800!important;box-shadow:0 4px 9px rgba(36,119,223,.18)!important
        }
        .st-key-stock_filters div[data-testid="stDownloadButton"] button{
            min-height:31px!important;height:31px!important;margin-top:15px!important;
            background:#fff!important;border:1px solid #b9d2ec!important;border-radius:7px!important;
            color:#165da9!important;font-size:8px!important;font-weight:800!important
        }

        /* KPI row */
        .stock-kpi{
            position:relative;min-height:78px;background:#fff;border:1px solid #dfe7f0;border-radius:10px;
            padding:9px 9px 7px 9px;box-shadow:0 3px 10px rgba(20,40,65,.045);overflow:hidden
        }
        .stock-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--tone)}
        .stock-kpi.critical{background:#fff7f7;border-color:#f2c8cc}
        .stock-kpi-row{display:flex;align-items:center;gap:8px}
        .stock-kpi-icon{
            width:31px;height:31px;min-width:31px;border-radius:9px;display:flex;align-items:center;justify-content:center;
            background:var(--soft);color:var(--tone);font-size:16px;font-weight:900;line-height:1
        }
        .stock-kpi-label{font:700 8.2px/1.12 "Segoe UI",Arial,sans-serif;color:#29445f;white-space:nowrap}
        .stock-kpi-value{font:850 18px/1.03 "Segoe UI",Arial,sans-serif;color:#153a66;margin-top:4px;letter-spacing:-.25px}
        .stock-kpi-note{font:600 7.1px/1.2 "Segoe UI",Arial,sans-serif;color:#74869a;margin-top:5px;padding-left:39px}
        .stock-kpi.critical .stock-kpi-value,.stock-kpi.critical .stock-kpi-note{color:#d9333f}

        /* cards */
        .st-key-stock_page div[data-testid="stVerticalBlockBorderWrapper"]{
            background:#fff!important;border:1px solid #dce6f0!important;border-radius:10px!important;
            box-shadow:0 3px 10px rgba(20,40,65,.035)!important
        }
        .st-key-stock_page div[data-testid="stVerticalBlockBorderWrapper"]>div{padding:.52rem .62rem .58rem!important}
        .st-key-stock_page .stPlotlyChart{margin:-4px 0 -8px!important}

        .stock-panel-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 7px 0;padding:3px 2px 2px;min-height:26px}
        .stock-panel-name{display:flex;align-items:center;gap:6px;font:800 11.5px "Segoe UI",Arial,sans-serif;color:#173c68}
        .stock-panel-name .ico{font-size:12px;color:#1a70ce}
        .stock-panel-meta{font:900 8.4px "Segoe UI",Arial,sans-serif;color:#173c68;letter-spacing:.05px}
        .stock-view{color:#1c78dd;font-weight:700}
        .st-key-insights_view_all button,
        .st-key-action_view_all button,
        .st-key-branch_view_all button{
            min-height:24px!important;height:24px!important;padding:0 7px!important;
            background:transparent!important;border:0!important;box-shadow:none!important;
            color:#1c78dd!important;font-size:7.4px!important;font-weight:800!important;
        }
        .st-key-insights_view_all button:hover,
        .st-key-action_view_all button:hover,
        .st-key-branch_view_all button:hover{
            background:#edf6ff!important;color:#0b5aa7!important;border-radius:6px!important;
        }

        /* insight strip */
        .stock-insights{
            background:#fff;border:1px solid #dce6f0;border-radius:10px;padding:10px 10px 9px;
            box-shadow:0 3px 10px rgba(20,40,65,.035)
        }
        .stock-insights-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;padding:2px 1px 1px;min-height:25px}
        .stock-insights-title{font:800 10.5px "Segoe UI",Arial,sans-serif;color:#173c68}
        .stock-insights-note{font:600 7px "Segoe UI",Arial,sans-serif;color:#7d8da0}
        .stock-insight-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px;width:100%}
        .stock-insight{
            min-height:70px;background:#fff;border:1px solid #e0e8f1;border-radius:8px;padding:9px 9px 8px;
            display:grid;grid-template-columns:28px 1fr;column-gap:7px;align-items:center;overflow:hidden
        }
        .stock-insight-icon{
            width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
            background:var(--soft);color:var(--accent);font:900 12px "Segoe UI Symbol","Segoe UI",Arial,sans-serif
        }
        .stock-insight-label{font:750 8.1px/1.18 "Segoe UI",Arial,sans-serif;color:#344d67;margin-bottom:1px}
        .stock-insight-value{font:850 13px/1.12 "Segoe UI",Arial,sans-serif;color:var(--accent);margin-top:3px;white-space:normal;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
        .stock-insight-sub{grid-column:2;font:600 6.8px/1.15 "Segoe UI",Arial,sans-serif;color:#798a9d;margin-top:-5px}

        /* HTML tables */
        .stock-table-wrap{width:100%;max-width:100%;overflow-x:auto;overflow-y:hidden;border:1px solid #e0e8f0;border-radius:7px;background:#fff}
        table.stock-table{width:100%;min-width:100%;border-collapse:collapse;table-layout:auto;font:650 8.8px/1.22 "Segoe UI",Arial,sans-serif;color:#2e4761}
        table.stock-table th{
            background:#eef5fb;color:#38516c;padding:7px 7px;text-align:left;border-right:1px solid #dfe8f0;
            border-bottom:1px solid #d9e4ee;font-weight:800;white-space:nowrap
        }
        table.stock-table td{
            padding:7px 7px;border-right:1px solid #e7edf3;border-bottom:1px solid #e7edf3;
            white-space:nowrap;background:#fff
        }
        table.stock-table tbody tr:nth-child(even) td{background:#fbfdff}
        table.stock-table th:last-child,table.stock-table td:last-child{border-right:0}
        table.stock-table tbody tr:last-child td{border-bottom:0}
        .pill-red{display:inline-block;background:#ffe3e5;color:#d73440;border-radius:5px;padding:2px 5px;font-weight:800}
        .pill-blue{display:inline-block;background:#e7f2ff;color:#176bc0;border-radius:5px;padding:2px 5px;font-weight:800}
        .pill-green{display:inline-block;background:#e8f7ee;color:#22854c;border-radius:5px;padding:2px 5px;font-weight:800}
        .pill-orange{display:inline-block;background:#fff0df;color:#cc6a13;border-radius:5px;padding:2px 5px;font-weight:800}
        .stock-table-wrap::-webkit-scrollbar{height:7px}
        .stock-table-wrap::-webkit-scrollbar-thumb{background:#c8d6e5;border-radius:999px}
        .stock-table-wrap::-webkit-scrollbar-track{background:#eef4f9}

        /* bottom charts */
        .stock-mini-note{font:600 6.8px "Segoe UI",Arial,sans-serif;color:#7d8ea1}
        .stock-footer{display:flex;justify-content:space-between;align-items:center;padding:3px 5px 0;color:#7f8fa1;font:600 6.8px "Segoe UI",Arial,sans-serif}

        .st-key-stock_page div[data-testid="stExpander"]{
            border:1px solid #e0e8f0!important;border-radius:8px!important;background:#fff!important
        }
        .st-key-stock_page div[data-testid="stExpander"] summary{font-size:8px!important;font-weight:700!important;color:#526a82!important}

        @media(max-width:1350px){
            .stock-insight-grid{grid-template-columns:repeat(3,1fr)}
            .stock-kpi-label{white-space:normal}
        }
        @media(max-width:1180px){
            .stock-table-wrap{overflow-x:auto}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fmt_number(value):
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return "0"


def _fmt_money(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    if abs(value) >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if abs(value) >= 100_000:
        return f"₹{value / 100_000:.2f} L"
    return f"₹{value:,.0f}"


def _safe_options(df, column):
    if column not in df.columns or df.empty:
        return []
    values = df[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return sorted(values.unique().tolist(), key=str.casefold)


def _find_column(df, candidates):
    normalized = {
        str(column).strip().casefold().replace("_", "").replace(" ", ""): column
        for column in df.columns
    }
    for candidate in candidates:
        key = candidate.strip().casefold().replace("_", "").replace(" ", "")
        if key in normalized:
            return normalized[key]
    return None


def _normalise_branch_code(series):
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(3)
    )


def _match_scope_value(series, value):
    if value is None or not str(value).strip():
        return pd.Series(True, index=series.index)
    target = str(value).strip().casefold()
    return series.fillna("").astype(str).str.strip().str.casefold().eq(target)


def _match_scope_values(series, values):
    targets = {
        str(value).strip().casefold()
        for value in (values or [])
        if value is not None and str(value).strip()
    }
    if not targets:
        return pd.Series(True, index=series.index)
    return series.fillna("").astype(str).str.strip().str.casefold().isin(targets)


def _attach_stock_hierarchy(stock_df):
    code_column = _find_column(
        stock_df,
        ["branchcode", "branch_code", "branch code", "stncode", "code"],
    )
    if not code_column:
        raise ValueError(
            "Stock data does not contain branchcode, so Zone/Circle rights cannot be mapped."
        )

    hierarchy = load_stock_branch_mast().copy()
    zone_column = _find_column(hierarchy, ["zone", "zonename"])
    circle_column = _find_column(hierarchy, ["circle", "hubname"])
    branch_column = _find_column(hierarchy, ["branch", "branchname", "stnname"])
    master_code_column = _find_column(
        hierarchy, ["code", "branchcode", "branch_code", "stncode"]
    )

    missing = [
        name
        for name, column in {
            "zone": zone_column,
            "circle": circle_column,
            "branch": branch_column,
            "code": master_code_column,
        }.items()
        if not column
    ]
    if missing:
        raise ValueError(
            "Stock branch hierarchy query is missing required columns: " + ", ".join(missing)
        )

    hierarchy = hierarchy.rename(
        columns={
            zone_column: "zone",
            circle_column: "circle",
            branch_column: "master_branch",
            master_code_column: "branchcode",
        }
    )
    hierarchy["branchcode_key"] = _normalise_branch_code(hierarchy["branchcode"])

    enriched = stock_df.copy()
    enriched["branchcode_key"] = _normalise_branch_code(enriched[code_column])
    enriched = enriched.merge(
        hierarchy[["branchcode_key", "zone", "circle", "master_branch"]],
        on="branchcode_key",
        how="left",
        validate="m:1",
    )
    enriched["scope_branch"] = enriched["master_branch"].fillna(enriched.get("branch"))
    return enriched


def _derive_role_scope(df):
    data_scope = st.session_state.get("data_scope", {}) or {}
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    if locked_branch:
        branch_mask = (
            _match_scope_value(df["scope_branch"], locked_branch)
            | _match_scope_value(df["branch"], locked_branch)
            | _match_scope_value(df["branchcode_key"], locked_branch)
        )
        rows = df[branch_mask]
        if not rows.empty:
            locked_branch = rows["scope_branch"].iloc[0]
            if rows["circle"].notna().any():
                locked_circle = rows["circle"].dropna().iloc[0]
            if rows["zone"].notna().any():
                locked_zone = rows["zone"].dropna().iloc[0]
    elif locked_circle:
        rows = df[_match_scope_value(df["circle"], locked_circle)]
        if not rows.empty:
            locked_circle = rows["circle"].iloc[0]
            if rows["zone"].notna().any():
                locked_zone = rows["zone"].dropna().iloc[0]
    elif locked_zone:
        rows = df[_match_scope_value(df["zone"], locked_zone)]
        if not rows.empty:
            locked_zone = rows["zone"].iloc[0]

    return locked_zone, locked_circle, locked_branch


def _apply_locked_scope(df, locked_zone, locked_circle, locked_branch):
    scoped = df
    if locked_zone:
        scoped = scoped[_match_scope_value(scoped["zone"], locked_zone)]
    if locked_circle:
        scoped = scoped[_match_scope_value(scoped["circle"], locked_circle)]
    if locked_branch:
        scoped = scoped[_match_scope_value(scoped["scope_branch"], locked_branch)]
    return scoped


def _count_type(df, stock_type):
    return int(df.loc[df["stock_type"].eq(stock_type), "gr_no"].nunique())


def _sum_where(df, stock_type, column):
    if column not in df.columns:
        return 0
    return df.loc[df["stock_type"].eq(stock_type), column].fillna(0).sum()


def _kpi_card(label, value, note, icon, tone, critical=False):
    klass = "stock-kpi critical" if critical else "stock-kpi"
    return f"""
    <div class="{klass}" style="--tone:{tone};--soft:{tone}18">
      <div class="stock-kpi-row">
        <div class="stock-kpi-icon">{html.escape(str(icon))}</div>
        <div style="min-width:0">
          <div class="stock-kpi-label">{html.escape(str(label))}</div>
          <div class="stock-kpi-value">{html.escape(str(value))}</div>
        </div>
      </div>
      <div class="stock-kpi-note">{html.escape(str(note))}</div>
    </div>
    """


def _base_chart(fig, height, margins):
    fig.update_layout(
        height=height,
        margin=margins,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial", size=8, color="#405873"),
        hoverlabel=dict(font_size=9),
    )
    return fig


def _zone_bar(df, column, title):
    grouped = (
        df.groupby(column, dropna=False)["gr_no"]
        .nunique()
        .reset_index(name="GR Count")
    )
    grouped[column] = grouped[column].fillna("Unmapped").astype(str).str.strip()
    grouped.loc[grouped[column].eq(""), column] = "Unmapped"
    grouped = grouped.sort_values("GR Count", ascending=False).head(8)

    # Keep the same colour for the same zone in both Current and Destination charts.
    dynamic_map = {}
    fallback_index = 0
    for zone in grouped[column].tolist():
        key = str(zone).strip().upper()
        if key in ZONE_COLOURS:
            dynamic_map[zone] = ZONE_COLOURS[key]
        else:
            dynamic_map[zone] = ZONE_FALLBACK[fallback_index % len(ZONE_FALLBACK)]
            fallback_index += 1

    fig = px.bar(
        grouped,
        x="GR Count",
        y=column,
        orientation="h",
        text="GR Count",
        color=column,
        color_discrete_map=dynamic_map,
    )
    fig.update_traces(
        texttemplate="<b>%{x:,.0f}</b>",
        textposition="outside",
        textfont=dict(size=8, color="#173c68", family="Arial Black, Segoe UI, Arial"),
        marker=dict(line=dict(width=0)),
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:,} GR<extra></extra>",
    )
    _base_chart(fig, 185, dict(l=8, r=46, t=8, b=22))
    fig.update_layout(
        showlegend=False,
        xaxis=dict(
            title=None,
            showgrid=True,
            gridcolor="#edf2f7",
            tickfont=dict(size=7, color="#64748b"),
        ),
        yaxis=dict(
            title=None,
            tickfont=dict(size=8, color="#334155", family="Arial Black, Segoe UI, Arial"),
            autorange="reversed",
            automargin=True,
        ),
        bargap=.34,
    )
    return fig


def _prepare_load_mix(df):
    grouped = (
        df.groupby("load_type", dropna=False)["gr_no"]
        .nunique()
        .reset_index(name="GR Count")
    )
    grouped["load_type"] = grouped["load_type"].fillna("Unknown").astype(str).str.strip().str.upper()
    grouped.loc[grouped["load_type"].isin(["", "UNKNOWN", "NAN", "NONE"]), "load_type"] = "UNKNOWN"
    grouped["Display"] = grouped["load_type"].replace({"LTL": "PTL"})
    grouped = grouped.groupby("Display", as_index=False)["GR Count"].sum().sort_values("GR Count", ascending=False)
    total = int(grouped["GR Count"].sum())
    grouped["Share"] = grouped["GR Count"] / max(total, 1) * 100
    grouped["Colour"] = grouped["Display"].map(lambda x: LOAD_COLOURS.get(str(x).upper(), LOAD_COLOURS["UNKNOWN"]))
    return grouped, total


def _donut(df):
    grouped, total = _prepare_load_mix(df)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=grouped["Display"],
                values=grouped["GR Count"],
                hole=.62,
                domain=dict(x=[0.00, 0.62], y=[0.02, 0.98]),
                sort=False,
                direction="clockwise",
                marker=dict(
                    colors=grouped["Colour"].tolist(),
                    line=dict(color="white", width=2),
                ),
                text=grouped["Share"].map(lambda x: f"{x:.0f}%"),
                textinfo="text",
                textposition="inside",
                insidetextorientation="auto",
                textfont=dict(
                    size=10,
                    color="white",
                    family="Arial Black, Segoe UI, Arial",
                ),
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "%{value:,} GR<br>"
                    "%{percent}<extra></extra>"
                ),
                showlegend=False,
            )
        ]
    )

    # Center total exactly inside the donut hole.
    center_x = (0.00 + 0.62) / 2
    fig.add_annotation(
        x=center_x,
        y=.535,
        xref="paper",
        yref="paper",
        text=f"<b>{total:,}</b>",
        showarrow=False,
        xanchor="center",
        yanchor="middle",
        align="center",
        font=dict(
            size=18,
            color="#153a66",
            family="Arial Black, Segoe UI, Arial",
        ),
    )
    fig.add_annotation(
        x=center_x,
        y=.425,
        xref="paper",
        yref="paper",
        text="<b>Total GR</b>",
        showarrow=False,
        xanchor="center",
        yanchor="middle",
        align="center",
        font=dict(
            size=10,
            color="#153a66",
            family="Arial Black, Segoe UI, Arial",
        ),
    )

    # Reference-style legend built inside Plotly, avoiding Streamlit HTML rendering issues.
    legend_y = .63
    row_gap = .24
    for idx, row in grouped.reset_index(drop=True).iterrows():
        y = legend_y - idx * row_gap
        label = str(row["Display"]).upper()
        colour = str(row["Colour"])
        value = int(row["GR Count"])
        share = float(row["Share"])

        fig.add_annotation(
            x=.69, y=y, xref="paper", yref="paper",
            text="●", showarrow=False, xanchor="center", yanchor="middle",
            font=dict(size=19, color=colour, family="Arial"),
        )
        fig.add_annotation(
            x=.735, y=y, xref="paper", yref="paper",
            text=(
                f"<b>{label}</b><br>"
                f"<span style='font-size:9px'>{value:,} GR ({share:.0f}%)</span>"
            ),
            showarrow=False,
            xanchor="left",
            yanchor="middle",
            align="left",
            font=dict(size=10, color="#173c68", family="Segoe UI, Arial"),
        )

    _base_chart(fig, 185, dict(l=0, r=2, t=0, b=0))
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=2, t=0, b=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


def _panel_header(title, icon, meta=""):
    meta_html = f'<div class="stock-panel-meta">{html.escape(str(meta))}</div>' if meta else ""
    return f"""
    <div class="stock-panel-head">
      <div class="stock-panel-name"><span class="ico">{icon}</span>{html.escape(str(title))}</div>
      {meta_html}
    </div>
    """


def _operational_insights(df):
    critical_mask = df.get("is_critical", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    overdue_mask = df.get("is_edd_overdue", pd.Series(False, index=df.index)).fillna(False).astype(bool)

    overdue_gr = int(df.loc[overdue_mask, "gr_no"].nunique())
    missing_edd_gr = int(df.loc[df["edd"].isna(), "gr_no"].nunique()) if "edd" in df.columns else 0
    critical_delivery = int(df.loc[critical_mask & df["stock_type"].eq("DELIVERY STOCK"), "gr_no"].nunique())
    critical_transit = int(
        df.loc[
            critical_mask & df["stock_type"].isin(["IN-TRANSIT STOCK", "TRANSIT STOCK"]),
            "gr_no",
        ].nunique()
    )

    route_risk = (
        df.loc[critical_mask]
        .groupby(["origin", "destination"])["gr_no"]
        .nunique()
        .sort_values(ascending=False)
    )
    if route_risk.empty:
        risk_route, risk_route_gr = "-", 0
    else:
        origin, destination = route_risk.index[0]
        risk_route = f"{origin} → {destination}"
        risk_route_gr = int(route_risk.iloc[0])

    if "reason_category" in df.columns:
        reason_source = df[
            ~df["reason_category"].astype(str).str.strip().str.casefold().isin(
                ["", "unknown", "none", "nan"]
            )
        ]
        reason_counts = reason_source.groupby("reason_category")["gr_no"].nunique().sort_values(ascending=False)
    else:
        reason_counts = pd.Series(dtype="int64")

    if reason_counts.empty:
        top_reason, top_reason_gr = "Not recorded", 0
    else:
        top_reason = str(reason_counts.index[0])
        top_reason_gr = int(reason_counts.iloc[0])

    return [
        ("◷", "EDD Overdue", f"{overdue_gr:,} GR", "Past committed delivery date", PALETTE["red"]),
        ("▤", "Missing EDD", f"{missing_edd_gr:,} GR", "EDD needs update", PALETTE["orange"]),
        ("!", "Critical Delivery", f"{critical_delivery:,} GR", "Delivery stock aged 15+ days", PALETTE["red"]),
        ("⇆", "Critical Transit", f"{critical_transit:,} GR", "Transit stock aged 15+ days", PALETTE["purple"]),
        ("⌖", "Highest-Risk Route", risk_route, f"{risk_route_gr:,} critical GR", PALETTE["blue"]),
        ("!", "Top Delay Reason", top_reason, f"{top_reason_gr:,} affected GR", PALETTE["orange"]),
    ]


def _render_insights(df):
    insights = _operational_insights(df)

    with st.container():
        title_col, note_col, action_col = st.columns([5.6, 2.7, .8], gap="small")
        with title_col:
            st.markdown(
                '<div class="stock-insights" style="padding:8px 10px">'
                '<div class="stock-insights-title" style="padding-top:2px">💡 Operational Insights</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        with note_col:
            st.markdown(
                '<div style="padding-top:11px;text-align:right;font:650 7px Segoe UI,Arial,sans-serif;color:#7d8da0">'
                'Key exception highlights requiring attention</div>',
                unsafe_allow_html=True,
            )
        with action_col:
            expanded = _view_all_toggle("stock_insights_expanded", "insights_view_all")

    cols = st.columns(6, gap="small")
    for col, (icon, label, value, note, accent) in zip(cols, insights):
        with col:
            st.markdown(
                f"""
                <div class="stock-insight" style="--accent:{accent};--soft:{accent}18">
                  <div class="stock-insight-icon">{html.escape(str(icon))}</div>
                  <div>
                    <div class="stock-insight-label">{html.escape(str(label))}</div>
                    <div class="stock-insight-value" title="{html.escape(str(value))}">{html.escape(str(value))}</div>
                  </div>
                  <div class="stock-insight-sub">{html.escape(str(note))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if expanded:
        st.markdown(
            _html_table(_insights_table(df), ["28%", "24%", "48%"]),
            unsafe_allow_html=True,
        )


def _insights_table(df):
    rows = []
    for _icon, label, value, note, _accent in _operational_insights(df):
        rows.append({
            "Exception": label,
            "Current Position": value,
            "Action / Meaning": note,
        })
    return pd.DataFrame(rows)


def _view_all_toggle(state_key, button_key):
    expanded = bool(st.session_state.get(state_key, False))
    label = "Show Less ↑" if expanded else "View All →"
    if st.button(label, key=button_key):
        st.session_state[state_key] = not expanded
        st.rerun()
    return expanded


def _render_dynamic_heading(title, icon, state_key, button_key, note=None):
    """Render a panel heading with a working View All / Show Less control."""
    left_col, note_col, button_col = st.columns([5.8, 2.2, 1.0], gap="small")
    with left_col:
        st.markdown(
            f'<div class="stock-panel-head" style="margin-bottom:0">'
            f'<div class="stock-panel-name"><span class="ico">{icon}</span>{html.escape(str(title))}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with note_col:
        if note:
            st.markdown(
                f'<div style="padding-top:7px;text-align:right;font:650 7px Segoe UI,Arial,sans-serif;color:#7d8da0">{html.escape(str(note))}</div>',
                unsafe_allow_html=True,
            )
    with button_col:
        expanded = _view_all_toggle(state_key, button_key)
    return expanded


def _prepare_action_required(filtered, limit=10):
    sort_cols = [c for c in ["stock_days", "balance_charge_weight"] if c in filtered.columns]
    action_df = filtered.sort_values(sort_cols, ascending=False).copy() if sort_cols else filtered.copy()
    action_df["Issue"] = action_df["stock_type"].map(
        {
            "IN-TRANSIT STOCK": "In Transit (15+)",
            "TRANSIT STOCK": "Transit Pending",
            "DELIVERY STOCK": "Delivery Pending",
            "BOOKING STOCK": "Booking Pending",
        }
    ).fillna("Ageing Stock")
    if "is_edd_overdue" in action_df.columns:
        action_df.loc[action_df["is_edd_overdue"].fillna(False), "Issue"] = "EDD Overdue"
    if "edd" in action_df.columns:
        action_df.loc[action_df["edd"].isna(), "Issue"] = "Missing EDD"

    grdt_col = _find_column(
        action_df,
        ["grdt", "gr_dt", "gr date", "gr_date", "grdate", "booking_date", "booking date"],
    )
    action_df["GR Date"] = action_df[grdt_col] if grdt_col else pd.NaT

    display = action_df[["gr_no", "GR Date", "origin", "destination", "branch", "Issue", "stock_days"]].copy()
    display.columns = ["GR Number", "GR Date", "Origin", "Destination", "Current Location", "Issue", "Ageing"]
    return display if limit is None else display.head(limit)


def _prepare_branch_pending(filtered, limit=10):
    rows = []
    for branch, group in filtered.groupby("branch", dropna=False):
        critical_series = group.get("is_critical", pd.Series(False, index=group.index))
        if not isinstance(critical_series, pd.Series):
            critical_series = pd.Series(False, index=group.index)
        rows.append(
            {
                "Location": branch,
                "Active": group["gr_no"].nunique(),
                "In-Transit": group.loc[group["stock_type"].eq("IN-TRANSIT STOCK"), "gr_no"].nunique(),
                "Transit Stock": group.loc[group["stock_type"].eq("TRANSIT STOCK"), "gr_no"].nunique(),
                "15d+": group.loc[critical_series.fillna(False).astype(bool), "gr_no"].nunique(),
                "Weight": group.get("balance_charge_weight", pd.Series(0, index=group.index)).fillna(0).sum(),
                "Avg Dwell": group["stock_days"].mean(),
            }
        )
    result = pd.DataFrame(rows).sort_values("Active", ascending=False)
    return result if limit is None else result.head(limit)


def _prepare_routes(filtered, limit=10):
    route_source = filtered.copy()
    if "balance_charge_weight" not in route_source.columns:
        route_source["balance_charge_weight"] = 0

    routes = (
        route_source.groupby(["origin", "destination"], dropna=False)
        .agg(
            Active_GR=("gr_no", "nunique"),
            Weight=("balance_charge_weight", "sum"),
        )
        .reset_index()
        .sort_values(["Active_GR", "Weight"], ascending=[False, False])
    )
    if limit is not None:
        routes = routes.head(limit)
    routes["Route"] = routes["origin"].astype(str) + " → " + routes["destination"].astype(str)
    routes.insert(0, "#", range(1, len(routes) + 1))
    return routes[["#", "Route", "Active_GR", "Weight"]].rename(columns={"Active_GR": "Active GR"})


def _prepare_priority(filtered, limit=10):
    details = filtered.sort_values(["stock_days", "stock_topay"], ascending=False).copy()
    details["Weight"] = details["balance_charge_weight"].fillna(0)
    details["To-Pay"] = details["stock_topay"].fillna(0)
    details["Age"] = details["stock_days"].fillna(0)
    result = details[["gr_no", "branch", "stock_type", "Weight", "To-Pay", "Age"]].rename(
        columns={"gr_no": "GR", "branch": "Branch", "stock_type": "Status"}
    )
    return result if limit is None else result.head(limit)


def _cell(value, column):
    if pd.isna(value):
        return "-"
    if column == "Ageing":
        try:
            return f'<span class="pill-red">{float(value):.0f} Days</span>'
        except Exception:
            return html.escape(str(value))
    if column == "GR Date":
        try:
            dt = pd.to_datetime(value, errors="coerce")
            return "-" if pd.isna(dt) else dt.strftime("%d-%m-%Y")
        except Exception:
            return html.escape(str(value))
    if column == "Avg Dwell":
        return f"{float(value):.1f} d"
    if column == "Weight":
        return f"{float(value):,.0f} kg"
    if column == "To-Pay":
        return _fmt_money(value)
    if column == "Age":
        return f'<span class="pill-red">{float(value):.0f} d</span>'
    if column == "Status":
        text = str(value)
        key = text.strip().upper()
        if "DELIVERY" in key:
            klass = "pill-green"
        elif "TRANSIT" in key:
            klass = "pill-blue"
        elif "BOOKING" in key or "HOLD" in key:
            klass = "pill-orange"
        else:
            klass = "pill-blue"
        return f'<span class="{klass}">{html.escape(text.title())}</span>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:,.0f}"
    return html.escape(str(value))


def _html_table(df, widths=None):
    if df is None or df.empty:
        return '<div class="stock-mini-note">No data available for selected filters.</div>'
    widths = widths or []
    head = []
    for i, col in enumerate(df.columns):
        style = f' style="width:{widths[i]}"' if i < len(widths) and widths[i] else ""
        head.append(f"<th{style}>{html.escape(str(col))}</th>")
    body = []
    for _, row in df.iterrows():
        cells = [f"<td>{_cell(row[col], col)}</td>" for col in df.columns]
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f'<div class="stock-table-wrap"><table class="stock-table"><thead><tr>{"".join(head)}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _ageing_chart(filtered):
    order = ["0-7 Days", "8-14 Days", "15+ Days"]
    summary = (
        filtered.groupby("age_band", observed=True)["gr_no"]
        .nunique()
        .reindex(order, fill_value=0)
        .reset_index(name="GR Count")
    )
    fig = px.bar(
        summary,
        x="GR Count",
        y="age_band",
        orientation="h",
        color="age_band",
        color_discrete_map={
            "0-7 Days": "#38b86a",
            "8-14 Days": "#f0a629",
            "15+ Days": "#e4474f",
        },
        text="GR Count",
    )
    fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside", textfont=dict(size=8), cliponaxis=False)
    _base_chart(fig, 155, dict(l=6, r=36, t=0, b=22))
    fig.update_layout(
        showlegend=False,
        xaxis=dict(title=None, gridcolor="#edf2f7", tickfont=dict(size=7)),
        yaxis=dict(title=None, tickfont=dict(size=8), categoryorder="array", categoryarray=order[::-1]),
        bargap=.34,
    )
    return fig


def _stock_date_chart(filtered, as_on_date, period="M"):
    src = filtered[["gr_no", "stock_days"]].copy()
    src["stock_days"] = src["stock_days"].fillna(0).clip(lower=0)
    src["Stock Date"] = pd.Timestamp(as_on_date) - pd.to_timedelta(src["stock_days"], unit="D")

    period = (period or "M").upper()
    if period == "D":
        src["Period Key"] = src["Stock Date"].dt.floor("D")
        src["Period"] = src["Stock Date"].dt.strftime("%d %b")
        tail_n = 14
    elif period == "W":
        src["Period Key"] = src["Stock Date"].dt.to_period("W-SUN").dt.start_time
        src["Period"] = src["Period Key"].dt.strftime("%d %b")
        tail_n = 12
    elif period == "Q":
        src["Period Key"] = src["Stock Date"].dt.to_period("Q").dt.start_time
        q = src["Stock Date"].dt.quarter.astype(str)
        y = src["Stock Date"].dt.year.astype(str)
        src["Period"] = "Q" + q + " " + y
        tail_n = 8
    elif period == "Y":
        src["Period Key"] = pd.to_datetime(src["Stock Date"].dt.year.astype(str) + "-01-01")
        src["Period"] = src["Stock Date"].dt.strftime("%Y")
        tail_n = 6
    else:  # M
        src["Period Key"] = src["Stock Date"].dt.to_period("M").dt.start_time
        src["Period"] = src["Stock Date"].dt.strftime("%b %Y")
        tail_n = 12

    trend = (
        src.groupby(["Period Key", "Period"])["gr_no"]
        .nunique()
        .reset_index(name="GR Count")
        .sort_values("Period Key")
        .tail(tail_n)
    )

    fig = px.bar(
        trend,
        x="Period",
        y="GR Count",
        text="GR Count",
        color_discrete_sequence=[PALETTE["blue"]],
    )
    fig.update_traces(
        texttemplate="%{y:,.0f}",
        textposition="outside",
        textfont=dict(size=8, color="#173c68"),
        cliponaxis=False,
        hovertemplate="%{x}<br>%{y:,} GR<extra></extra>",
    )
    _base_chart(fig, 220, dict(l=8, r=8, t=8, b=35))
    fig.update_layout(
        xaxis=dict(title=None, tickfont=dict(size=8), tickangle=-30 if period in {"D", "W"} else 0),
        yaxis=dict(title=None, gridcolor="#edf2f7", tickfont=dict(size=8)),
        bargap=.25,
        showlegend=False,
    )
    return fig


def _apply_search(df, search_text):
    search = (search_text or "").strip()
    if not search:
        return df
    target = search.casefold()
    columns = [c for c in ["gr_no", "branch", "origin", "destination", "zone", "destination_zone"] if c in df.columns]
    mask = pd.Series(False, index=df.index)
    for col in columns:
        mask = mask | df[col].fillna("").astype(str).str.casefold().str.contains(target, regex=False)
    return df[mask]


def show_stock_operations():
    """Render the Stock Operations page without altering the app sidebar."""
    _inject_css()

    today = date.today()
    month_start = today.replace(day=1)

    with st.container(key="stock_page"):
        # PAGE HEADER - no sidebar/navigation code here.
        with st.container(key="stock_topbar"):
            title_col, live_col, search_col = st.columns([3.5, 1.15, 1.7], gap="small")
            with title_col:
                st.markdown(
                    """
                    <div class="stock-title-wrap">
                      <div class="stock-title-mark"></div>
                      <div>
                        <div class="stock-title">Stock Operations Control Tower</div>
                        <div class="stock-subtitle">Branch stock · ageing exposure · operational action queue</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with live_col:
                st.markdown(
                    f'<div class="stock-live-wrap"><span class="stock-live">LIVE</span><span class="stock-updated">As-on {today:%d %b %Y}</span></div>',
                    unsafe_allow_html=True,
                )
            with search_col:
                search_text = st.text_input(
                    "Search",
                    placeholder="Search GR / Branch / Route...",
                    label_visibility="collapsed",
                    key="stock_page_search",
                )

        # FILTER BAR. Date inputs are rendered first because ERP data depends on them.
        with st.container(key="stock_filters"):
            cols = st.columns([.88,.88,.88,.72,.72,1.02,.78,.86,.72,.78,.86], gap="small")
            with cols[0]:
                start_date = st.date_input("From Date", value=month_start, max_value=today, format="DD/MM/YYYY", key="stock_dashboard_from_date")
            with cols[1]:
                end_date = st.date_input("To Date", value=today, max_value=today, format="DD/MM/YYYY", key="stock_dashboard_to_date")
            with cols[2]:
                as_on_date = st.date_input("As-on Date", value=end_date, max_value=today, format="DD/MM/YYYY", key="stock_dashboard_as_on_date")

            if start_date > end_date:
                st.error("From Date cannot be after To Date.")
                return
            if as_on_date < start_date:
                st.error("As-on Date cannot be before From Date.")
                return

            try:
                stock_df = _attach_stock_hierarchy(
                    load_stock_data(start_date=start_date, end_date=end_date, as_on_date=as_on_date)
                )
                locked_zone, locked_circle, locked_branch = _derive_role_scope(stock_df)
                stock_df = _apply_locked_scope(stock_df, locked_zone, locked_circle, locked_branch)
            except Exception as exc:
                st.error(f"Stock dashboard data could not be loaded: {exc}")
                return

            if stock_df.empty:
                st.warning("No stock data is available for your assigned scope.")
                return

            working = stock_df
            with cols[3]:
                if locked_zone:
                    selected_zones = st.multiselect("Zone", [locked_zone], default=[locked_zone], disabled=True, key="stock_zone_locked")
                else:
                    selected_zones = st.multiselect("Zone", _safe_options(working, "zone"), placeholder="All", key="stock_zone_filter")
            if selected_zones:
                working = working[_match_scope_values(working["zone"], selected_zones)]

            with cols[4]:
                if locked_circle:
                    selected_circles = st.multiselect("Circle", [locked_circle], default=[locked_circle], disabled=True, key="stock_circle_locked")
                else:
                    selected_circles = st.multiselect("Circle", _safe_options(working, "circle"), placeholder="All", key="stock_circle_filter")
            if selected_circles:
                working = working[_match_scope_values(working["circle"], selected_circles)]

            with cols[5]:
                branch_options = _safe_options(working, "branch")
                if locked_branch:
                    branches = st.multiselect("Current Stock Branch", branch_options, default=branch_options, disabled=True, key="stock_branch_locked")
                else:
                    branches = st.multiselect("Current Stock Branch", branch_options, placeholder="All", key="stock_branch_filter")
            if branches:
                working = working[_match_scope_values(working["branch"], branches)]

            with cols[6]:
                stock_types = st.multiselect("Stock Type", _safe_options(working, "stock_type"), placeholder="All", key="stock_type_filter")
            if stock_types:
                working = working[_match_scope_values(working["stock_type"], stock_types)]

            with cols[7]:
                age_bands = st.multiselect("Ageing Bucket", _safe_options(working, "age_band"), placeholder="All", key="stock_age_filter")
            if age_bands:
                working = working[_match_scope_values(working["age_band"], age_bands)]

            with cols[8]:
                load_types = st.multiselect("Load Type", _safe_options(working, "load_type"), placeholder="All", key="stock_load_filter")
            if load_types:
                working = working[_match_scope_values(working["load_type"], load_types)]

            filtered = _apply_search(working, search_text)

            with cols[9]:
                st.button("⌕ Run Report", type="primary", use_container_width=True, key="stock_dashboard_run_report")
            with cols[10]:
                st.download_button(
                    "⇩ Download CSV",
                    data=filtered.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"stock_operations_{as_on_date:%d-%m-%Y}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="stock_dashboard_download_csv",
                )

        if filtered.empty:
            st.warning("No records match the selected filters/search.")
            return

        # KPI ROW
        type_counts = {stock_type: _count_type(filtered, stock_type) for stock_type in STOCK_ORDER}
        critical_mask = filtered.get("is_critical", pd.Series(False, index=filtered.index)).fillna(False).astype(bool)
        critical = int(filtered.loc[critical_mask, "gr_no"].nunique())
        total_gr = max(int(filtered["gr_no"].nunique()), 1)
        transit_age = filtered.loc[filtered["stock_type"].eq("TRANSIT STOCK"), "stock_days"].mean()
        transit_note = f"Avg dwell {transit_age:.1f} d" if pd.notna(transit_age) else "Avg dwell -"

        kpis = [
            ("Booking Stock", f"{type_counts['BOOKING STOCK']:,}", f"{_fmt_money(_sum_where(filtered, 'BOOKING STOCK', 'stock_topay'))} exposure", "📦", PALETTE["blue"], False),
            ("In-Transit", f"{type_counts['IN-TRANSIT STOCK']:,}", f"{_fmt_number(_sum_where(filtered, 'IN-TRANSIT STOCK', 'balance_packages'))} packages", "🚚", PALETTE["cyan"], False),
            ("Transit Stock", f"{type_counts['TRANSIT STOCK']:,}", transit_note, "↔️", PALETTE["purple"], False),
            ("Delivery Stock", f"{type_counts['DELIVERY STOCK']:,}", f"{_fmt_number(_sum_where(filtered, 'DELIVERY STOCK', 'balance_packages'))} packages", "✅", PALETTE["green"], False),
            ("Critical 15+ Days", f"{critical:,}", f"{critical / total_gr * 100:.1f}% of GR", "⚠️", PALETTE["red"], True),
            ("Balance Packages", _fmt_number(filtered["balance_packages"].fillna(0).sum()), f"{_fmt_number(filtered['balance_charge_weight'].fillna(0).sum())} kg", "📦", PALETTE["orange"], False),
            ("Stock To-Pay", _fmt_money(filtered["stock_topay"].fillna(0).sum()), "Collection exposure", "₹", PALETTE["blue"], False),
        ]
        kpi_cols = st.columns(7, gap="small")
        for column, card in zip(kpi_cols, kpis):
            with column:
                st.markdown(_kpi_card(*card), unsafe_allow_html=True)

        # PRIMARY CHART ROW
        c1, c2, c3 = st.columns([1.03, 1.03, 1], gap="small")
        with c1:
            with st.container(border=True):
                st.markdown(_panel_header("Stock by Current Zone", "◆", f"Total {total_gr:,} GR"), unsafe_allow_html=True)
                st.plotly_chart(_zone_bar(filtered, "zone", ""), use_container_width=True, config={"displayModeBar": False})
        with c2:
            with st.container(border=True):
                st.markdown(_panel_header("Stock by Destination Zone", "⇆", f"Total {total_gr:,} GR"), unsafe_allow_html=True)
                st.plotly_chart(_zone_bar(filtered, "destination_zone", ""), use_container_width=True, config={"displayModeBar": False})
        with c3:
            with st.container(border=True):
                st.markdown(_panel_header("PTL / FTL Overview", "◉", ""), unsafe_allow_html=True)
                st.plotly_chart(_donut(filtered), use_container_width=True, config={"displayModeBar": False})

        # OPERATIONAL INSIGHTS
        _render_insights(filtered)

        # ACTION + BRANCH TABLES - default 10 rows; View All expands to full results.
        left, right = st.columns(2, gap="small")
        with left:
            with st.container(border=True):
                action_expanded = _render_dynamic_heading(
                    "Action Required", "◎",
                    "stock_action_expanded", "action_view_all"
                )
                action_limit = None if action_expanded else 10
                st.markdown(
                    _html_table(
                        _prepare_action_required(filtered, action_limit),
                        ["14%","12%","11%","13%","19%","18%","13%"],
                    ),
                    unsafe_allow_html=True,
                )
        with right:
            with st.container(border=True):
                branch_expanded = _render_dynamic_heading(
                    "Branch / Location Pending", "▦",
                    "stock_branch_expanded", "branch_view_all"
                )
                branch_limit = None if branch_expanded else 10
                st.markdown(
                    _html_table(
                        _prepare_branch_pending(filtered, branch_limit),
                        ["20%","11%","13%","14%","10%","16%","16%"],
                    ),
                    unsafe_allow_html=True,
                )

        # Bottom row 1: only Ageing + Stock Date Distribution
        b1, b2 = st.columns(2, gap="small")
        with b1:
            with st.container(border=True):
                st.markdown(_panel_header("Ageing – Stock", "⌛", ""), unsafe_allow_html=True)
                st.plotly_chart(_ageing_chart(filtered), use_container_width=True, config={"displayModeBar": False})
        with b2:
            with st.container(border=True):
                title_col, period_col = st.columns([4.2, 1.8], gap="small")
                with title_col:
                    st.markdown(_panel_header("Stock Date Distribution", "▥", ""), unsafe_allow_html=True)
                with period_col:
                    stock_period = st.segmented_control(
                        "Stock Date Period",
                        options=["D", "M", "W", "Q", "Y"],
                        default="M",
                        key="stock_date_distribution_period",
                        label_visibility="collapsed",
                    )
                st.plotly_chart(
                    _stock_date_chart(filtered, as_on_date, stock_period),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

        # Bottom row 2: Routes + Priority Details
        b3, b4 = st.columns(2, gap="small")
        with b3:
            with st.container(border=True):
                routes_expanded = _render_dynamic_heading(
                    "Routes by Active Stock", "↗",
                    "stock_routes_expanded", "routes_view_all"
                )
                routes_limit = None if routes_expanded else 10
                st.markdown(
                    _html_table(
                        _prepare_routes(filtered, routes_limit),
                        ["9%", "51%", "18%", "22%"],
                    ),
                    unsafe_allow_html=True,
                )
        with b4:
            with st.container(border=True):
                priority_expanded = _render_dynamic_heading(
                    "Priority Stock Details", "★",
                    "stock_priority_expanded", "priority_view_all"
                )
                priority_limit = None if priority_expanded else 10
                st.markdown(
                    _html_table(
                        _prepare_priority(filtered, priority_limit),
                        ["18%","16%","22%","14%","18%","12%"],
                    ),
                    unsafe_allow_html=True,
                )

        # Keep mapping exceptions accessible without changing the approved visible layout.
        unmapped_mask = (
            filtered["zone"].isna()
            | filtered["zone"].astype(str).str.strip().str.casefold().isin(["", "unmapped", "unknown", "none", "nan"])
        )
        unmapped_rows = filtered.loc[unmapped_mask].copy()
        if not unmapped_rows.empty:
            with st.expander(f"Data Quality · Unmapped Current-Zone Branches ({unmapped_rows['gr_no'].nunique():,} GR)", expanded=False):
                cols_show = [c for c in ["gr_no", "branchcode_key", "branch", "origin", "destination"] if c in unmapped_rows.columns]
                st.dataframe(unmapped_rows[cols_show].drop_duplicates().head(100), use_container_width=True, hide_index=True)

        st.markdown(
            f"""
            <div class="stock-footer">
              <span>© {today:%Y} Sugam Logistics</span>
              <span>Data is operational and confidential &nbsp; | &nbsp; As-on {as_on_date:%d %b %Y}</span>
              <span>Built for faster operational action.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def show():
    """Compatibility entry point used by routers."""
    show_stock_operations()


if __name__ == "__main__":
    show_stock_operations()
