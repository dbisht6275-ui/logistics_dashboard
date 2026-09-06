"""Professional Stock Operations Control Tower for Sugam Dashboard."""

from __future__ import annotations

import html
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from services.stock_branch_mast import load_stock_branch_mast
from services.stock_data_loader import load_stock_data


PALETTE = {
    "blue": "#2f73d8",
    "blue_dark": "#1456a0",
    "orange": "#ed8b25",
    "cyan": "#1e91a0",
    "purple": "#7953c6",
    "green": "#269b54",
    "red": "#d63f48",
    "brown": "#8a613d",
    "navy": "#0b3158",
    "text": "#172238",
    "muted": "#718096",
    "border": "#dce5ef",
    "page": "#f4f7fb",
}

STOCK_ORDER = [
    "BOOKING STOCK",
    "IN-TRANSIT STOCK",
    "TRANSIT STOCK",
    "DELIVERY STOCK",
]


def _inject_css():
    """Enterprise control-tower styling matching the approved mock-up."""
    st.markdown(
        """
        <style>
        :root{
            --navy:#0b3158;
            --blue:#2f73d8;
            --cyan:#1e91a0;
            --orange:#ed8b25;
            --purple:#7953c6;
            --green:#269b54;
            --red:#d63f48;
            --text:#172238;
            --muted:#718096;
            --border:#dce5ef;
            --page:#f4f7fb;
        }

        html, body, [class*="css"] {font-family: Inter, "Segoe UI", Arial, sans-serif;}
        [data-testid="stHeader"]{height:0!important;background:transparent!important;}
        [data-testid="stAppViewContainer"]{background:var(--page)!important;}
        [data-testid="stMainBlockContainer"], .main .block-container, .block-container{
            padding-top:.45rem!important;
            padding-left:.8rem!important;
            padding-right:.8rem!important;
            padding-bottom:1rem!important;
            width:100%!important;
            max-width:100%!important;
        }
        [data-testid="stVerticalBlock"]{gap:.38rem!important;}
        [data-testid="stHorizontalBlock"]{gap:.55rem!important;align-items:stretch!important;}

        /* Sidebar polish only; navigation itself stays controlled by the main app */
        [data-testid="stSidebar"]{
            background:#ffffff!important;
            border-right:1px solid #e5ebf2!important;
        }
        [data-testid="stSidebar"] .block-container{padding-top:.7rem!important;}

        /* Top control tower header */
        .st-key-stock_header{
            background:linear-gradient(108deg,#082b57 0%,#0d4b83 52%,#0d6d9a 100%);
            border-radius:13px;
            padding:10px 12px 9px;
            box-shadow:0 8px 24px rgba(8,43,87,.18);
            margin-bottom:3px;
        }
        .stock-brand-row{display:flex;align-items:center;gap:14px;min-height:45px;}
        .stock-brand-mark{
            display:flex;align-items:center;gap:8px;padding-right:14px;
            border-right:1px solid rgba(255,255,255,.22);
        }
        .stock-brand-symbol{
            width:27px;height:27px;border-radius:8px;
            background:linear-gradient(145deg,#ff6c2c 0 44%,#49b4f5 45% 100%);
            box-shadow:inset 0 0 0 3px rgba(255,255,255,.12);
            transform:rotate(8deg);
        }
        .stock-brand-name{font:900 15px/1 Inter,sans-serif;color:#fff;letter-spacing:.7px;}
        .stock-brand-tag{font:600 5.8px/1.2 Inter,sans-serif;color:#d4e8fb;margin-top:2px;}
        .stock-heading{min-width:0;}
        .stock-title{font:850 18px/1.1 Inter,sans-serif;color:#fff;margin:0 0 3px;letter-spacing:-.2px;}
        .stock-sub{font:550 8px/1.2 Inter,sans-serif;color:#d8e9f9;margin:0;}
        .stock-header-meta{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap;}
        .stock-live{
            display:inline-flex;align-items:center;gap:6px;border-radius:999px;
            background:#2abf68;color:white;padding:5px 9px;
            font:800 7px Inter,sans-serif;letter-spacing:.35px;
        }
        .stock-live:before{content:"";width:6px;height:6px;border-radius:50%;background:#d9ffe8;}
        .stock-updated{font:600 7px Inter,sans-serif;color:#d9eaff;white-space:nowrap;}

        .st-key-stock_header label,
        .st-key-stock_header label p{color:#eaf4ff!important;font-weight:750!important;}
        .st-key-stock_header div[data-testid="stDateInput"] input{
            background:#fff!important;color:#16314f!important;
        }
        .st-key-stock_header div[data-testid="stButton"] button{
            background:#2680e8!important;color:#fff!important;border:1px solid rgba(255,255,255,.2)!important;
        }
        .st-key-stock_header div[data-testid="stDownloadButton"] button{
            background:#fff!important;color:#175ca8!important;border:1px solid #b9d2ec!important;
        }

        /* Inputs */
        div[data-testid="stDateInput"] label,
        div[data-testid="stSelectbox"] label,
        div[data-testid="stMultiSelect"] label,
        div[data-testid="stTextInput"] label{
            font-size:8px!important;font-weight:750!important;color:#40556f!important;margin-bottom:1px!important;
        }
        div[data-testid="stDateInput"] input,
        div[data-testid="stTextInput"] input,
        div[data-baseweb="select"]>div{
            min-height:31px!important;height:31px!important;font-size:8.5px!important;
            border-radius:7px!important;border-color:#d7e1ec!important;background:#fff!important;
        }
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button{
            min-height:31px!important;height:31px!important;border-radius:7px!important;
            padding:0 .65rem!important;font-size:8.5px!important;font-weight:800!important;
        }
        div[data-testid="stSegmentedControl"]{justify-content:flex-end!important;}
        div[data-testid="stSegmentedControl"] button{
            min-height:25px!important;height:25px!important;min-width:35px!important;
            font-size:8px!important;font-weight:800!important;
        }

        /* Filter surface */
        .stock-filter-shell{
            background:#fff;border:1px solid #e0e7ef;border-radius:10px;
            padding:7px 9px 4px;box-shadow:0 2px 8px rgba(20,40,65,.035);
        }
        .stock-filter-title{
            display:flex;align-items:center;justify-content:space-between;
            font:800 9px Inter,sans-serif;color:#24415f;margin-bottom:4px;
        }
        .stock-filter-hint{font:600 7px Inter,sans-serif;color:#8b98a8;}
        div[data-testid="stExpander"]{
            border:1px solid #e3e9f0!important;border-radius:8px!important;background:#fbfcfe!important;
        }
        div[data-testid="stExpander"] summary{min-height:28px!important;font-size:8px!important;font-weight:750!important;color:#40556f!important;}

        /* KPI cards */
        .stock-kpi{
            position:relative;overflow:hidden;min-height:83px;
            background:#fff;border:1px solid #dfe7f0;border-radius:10px;
            padding:10px 10px 8px;box-shadow:0 4px 13px rgba(20,40,65,.055);
        }
        .stock-kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--tone);}
        .stock-kpi.critical{border-color:#efc8cc;background:linear-gradient(145deg,#fff,#fff5f5);}
        .stock-kpi-top{display:flex;align-items:center;gap:8px;}
        .stock-kpi-icon{
            width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;
            font-size:15px;font-weight:900;background:var(--tone-soft);color:var(--tone);
        }
        .stock-kpi-label{font:800 8px/1.1 Inter,sans-serif;color:#354b65;white-space:nowrap;}
        .stock-kpi-value{font:900 19px/1.05 Inter,sans-serif;color:#153251;margin-top:4px;letter-spacing:-.3px;}
        .stock-kpi-note{font:600 7px/1.25 Inter,sans-serif;color:#748399;margin-top:4px;}

        /* Generic white panels */
        div[data-testid="stVerticalBlockBorderWrapper"]{
            background:#fff!important;border:1px solid #dce5ef!important;border-radius:10px!important;
            box-shadow:0 3px 12px rgba(20,40,65,.045)!important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]>div{padding:.45rem .62rem!important;}
        .stock-panel-title{
            display:flex;align-items:center;justify-content:space-between;gap:12px;
            font:850 10.5px Inter,sans-serif;color:#1f3a59;margin:0 0 5px;
        }
        .stock-panel-title span{font:650 7px Inter,sans-serif;color:#8492a4;}
        .stock-panel-title.alert{color:#b72d36;}

        /* Operational insights row */
        .stock-insights-wrap{
            background:#fff;border:1px solid #dce5ef;border-radius:10px;
            padding:8px 9px 9px;box-shadow:0 3px 12px rgba(20,40,65,.04);
        }
        .stock-insights-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;}
        .stock-insights-title{font:850 10.5px Inter,sans-serif;color:#1f3a59;}
        .stock-insights-sub{font:650 7px Inter,sans-serif;color:#8795a6;}
        .stock-insight-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px;}
        .stock-insight{
            border:1px solid #e3e9f0;border-radius:8px;padding:8px 9px;background:#fff;min-height:72px;
            position:relative;overflow:hidden;
        }
        .stock-insight:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent);}
        .stock-insight-label{font:800 7.5px/1.15 Inter,sans-serif;color:#40556f;}
        .stock-insight-value{font:900 15px/1.1 Inter,sans-serif;color:var(--accent);margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
        .stock-insight-note{font:600 6.8px/1.25 Inter,sans-serif;color:#8190a2;margin-top:4px;}

        /* Plotly */
        .stPlotlyChart{margin:-3px 0 -8px!important;}

        /* AG Grid */
        .stock-grid-toolbar{display:flex;justify-content:flex-end;margin-top:-1px;}
        .ag-theme-streamlit{--ag-font-size:9px;--ag-row-height:30px;}

        .stock-footer{
            display:flex;align-items:center;justify-content:space-between;gap:16px;
            color:#7d8b9c;font:600 7px Inter,sans-serif;padding:5px 3px 2px;
        }

        @media(max-width:1200px){
            .stock-insight-grid{grid-template-columns:repeat(3,1fr);}
            .stock-kpi-label{white-space:normal;}
        }
        @media(max-width:900px){
            .stock-insight-grid{grid-template-columns:repeat(2,1fr);}
            .stock-brand-mark{display:none;}
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
    if "stock_type" not in df.columns or "gr_no" not in df.columns:
        return 0
    return int(df.loc[df["stock_type"].eq(stock_type), "gr_no"].nunique())


def _sum_where(df, stock_type, column):
    if column not in df.columns:
        return 0
    return df.loc[df["stock_type"].eq(stock_type), column].fillna(0).sum()


def _kpi_card(label, value, note, icon, tone, critical=False):
    klass = "stock-kpi critical" if critical else "stock-kpi"
    return f"""
    <div class="{klass}" style="--tone:{tone};--tone-soft:{tone}18">
      <div class="stock-kpi-top">
        <div class="stock-kpi-icon">{icon}</div>
        <div style="min-width:0">
          <div class="stock-kpi-label">{html.escape(str(label))}</div>
          <div class="stock-kpi-value">{html.escape(str(value))}</div>
        </div>
      </div>
      <div class="stock-kpi-note">{html.escape(str(note))}</div>
    </div>
    """


def _base_plot_layout(fig, height=245, margin=None):
    fig.update_layout(
        height=height,
        margin=margin or dict(l=10, r=12, t=36, b=22),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Segoe UI, Arial", size=9, color="#42556d"),
        hoverlabel=dict(font_size=10),
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#edf2f7", zeroline=False)
    return fig


def _zone_bar(df, column, title):
    if column not in df.columns:
        st.info(f"{title}: data unavailable")
        return

    grouped = (
        df.groupby(column, dropna=False)["gr_no"]
        .nunique()
        .reset_index(name="GR Count")
        .sort_values("GR Count", ascending=True)
    )
    grouped[column] = grouped[column].fillna("Unmapped").astype(str).str.strip()
    grouped.loc[grouped[column].eq(""), column] = "Unmapped"
    grouped = grouped.tail(7)

    fig = px.bar(
        grouped,
        x="GR Count",
        y=column,
        orientation="h",
        text="GR Count",
        color_discrete_sequence=[PALETTE["blue"]],
    )
    fig.update_traces(
        marker_line_width=0,
        texttemplate="%{x:,.0f}",
        textposition="outside",
        textfont=dict(size=9, color="#28425f"),
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,} GR<extra></extra>",
    )
    _base_plot_layout(fig, height=245, margin=dict(l=8, r=52, t=34, b=18))
    fig.update_layout(
        title=dict(text=title, font=dict(size=11, color="#1f3a59"), x=.01),
        showlegend=False,
        xaxis=dict(title=None, showgrid=True, gridcolor="#edf2f7", tickfont=dict(size=8)),
        yaxis=dict(title=None, tickfont=dict(size=9, color="#29445f"), automargin=True),
        bargap=.33,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _donut(df, column, title):
    if column not in df.columns:
        st.info(f"{title}: data unavailable")
        return

    grouped = (
        df.groupby(column, dropna=False)["gr_no"]
        .nunique()
        .reset_index(name="GR Count")
        .sort_values("GR Count", ascending=False)
    )
    grouped[column] = grouped[column].fillna("Unknown").astype(str).str.strip()
    grouped.loc[grouped[column].eq(""), column] = "Unknown"

    # Keep PTL and FTL visually consistent when available.
    colour_map = {"PTL": PALETTE["blue_dark"], "FTL": "#11a8ae"}
    fig = px.pie(
        grouped,
        names=column,
        values="GR Count",
        hole=.62,
        color=column,
        color_discrete_map=colour_map,
        color_discrete_sequence=[PALETTE["blue_dark"], "#11a8ae", PALETTE["orange"], PALETTE["purple"]],
    )
    fig.update_traces(
        textinfo="percent",
        textfont_size=10,
        marker=dict(line=dict(color="white", width=1)),
        hovertemplate="%{label}<br>%{value:,} GR (%{percent})<extra></extra>",
    )
    fig.add_annotation(
        text=f"<b>{df['gr_no'].nunique():,}</b><br><span style='font-size:8px'>Total GR</span>",
        showarrow=False,
        font=dict(color="#153251", size=13),
    )
    _base_plot_layout(fig, height=245, margin=dict(l=5, r=5, t=34, b=20))
    fig.update_layout(
        title=dict(text=title, font=dict(size=11, color="#1f3a59"), x=.01),
        legend=dict(
            font=dict(size=8),
            orientation="v",
            x=.82,
            xanchor="left",
            y=.55,
            yanchor="middle",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_table(df, height=250, key="stock_grid"):
    """Compact enterprise grid with download control."""
    if df is None or df.empty:
        st.caption("No records available for the selected filters.")
        return

    _, download_col = st.columns([16, 1])
    with download_col:
        st.download_button(
            "↓",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download table as CSV",
            key=f"{key}_download",
        )

    builder = GridOptionsBuilder.from_dataframe(df)
    builder.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True,
        suppressMovable=False,
    )
    builder.configure_grid_options(
        headerHeight=30,
        rowHeight=29,
        suppressRowClickSelection=True,
        pagination=False,
    )

    AgGrid(
        df,
        gridOptions=builder.build(),
        height=height,
        theme="streamlit",
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=False,
        custom_css={
            ".ag-root-wrapper": {
                "border": "1px solid #e0e7ef !important",
                "border-radius": "8px !important",
                "overflow": "hidden !important",
            },
            ".ag-header": {
                "background-color": "#edf4fb !important",
                "border-bottom": "1px solid #dbe6f0 !important",
            },
            ".ag-header-cell": {
                "background-color": "#edf4fb !important",
                "color": "#28425f !important",
                "font-weight": "700 !important",
                "font-size": "9px !important",
                "border-right": "1px solid #e0e8f1 !important",
            },
            ".ag-header-cell-text": {
                "color": "#28425f !important",
                "font-weight": "700 !important",
            },
            ".ag-icon": {"color": "#58718c !important"},
            ".ag-row-even": {"background-color": "#fbfdff !important"},
            ".ag-row-hover": {"background-color": "#eef6ff !important"},
            ".ag-cell": {
                "font-size": "9px !important",
                "color": "#32485f !important",
                "border-right": "1px solid #edf1f5 !important",
            },
        },
        key=key,
    )


def _operational_insights(df):
    critical_mask = df.get("is_critical", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    overdue_mask = df.get("is_edd_overdue", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    overdue_gr = int(df.loc[overdue_mask, "gr_no"].nunique())

    if "edd" in df.columns:
        missing_edd_gr = int(df.loc[df["edd"].isna(), "gr_no"].nunique())
    else:
        missing_edd_gr = 0

    critical_delivery = int(
        df.loc[critical_mask & df["stock_type"].eq("DELIVERY STOCK"), "gr_no"].nunique()
    )
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
        reason_counts = (
            reason_source.groupby("reason_category")["gr_no"]
            .nunique()
            .sort_values(ascending=False)
        )
    else:
        reason_counts = pd.Series(dtype="int64")

    if reason_counts.empty:
        top_reason, top_reason_gr = "Not recorded", 0
    else:
        top_reason = str(reason_counts.index[0])
        top_reason_gr = int(reason_counts.iloc[0])

    return [
        ("EDD Overdue", f"{overdue_gr:,} GR", "Past committed delivery date", PALETTE["red"]),
        ("Missing EDD", f"{missing_edd_gr:,} GR", "EDD needs update", PALETTE["orange"]),
        ("Critical Delivery", f"{critical_delivery:,} GR", "Delivery stock aged 15+ days", PALETTE["red"]),
        ("Critical Transit", f"{critical_transit:,} GR", "Transit stock aged 15+ days", PALETTE["purple"]),
        ("Highest-Risk Route", risk_route, f"{risk_route_gr:,} critical GR", PALETTE["blue"]),
        ("Top Delay Reason", top_reason, f"{top_reason_gr:,} affected GR", PALETTE["orange"]),
    ]


def _render_operational_insights(df):
    cards = []
    for label, value, note, accent in _operational_insights(df):
        cards.append(
            f"""
            <div class="stock-insight" style="--accent:{accent}">
              <div class="stock-insight-label">{html.escape(str(label))}</div>
              <div class="stock-insight-value" title="{html.escape(str(value))}">{html.escape(str(value))}</div>
              <div class="stock-insight-note">{html.escape(str(note))}</div>
            </div>
            """
        )

    st.markdown(
        f"""
        <div class="stock-insights-wrap">
          <div class="stock-insights-head">
            <div class="stock-insights-title">💡 Operational Insights</div>
            <div class="stock-insights-sub">Key exception highlights requiring attention</div>
          </div>
          <div class="stock-insight-grid">{''.join(cards)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ageing_chart(filtered):
    age_summary = (
        filtered.groupby("age_band", observed=True)["gr_no"]
        .nunique()
        .reindex(["0-7 Days", "8-14 Days", "15+ Days"], fill_value=0)
        .reset_index(name="GR Count")
    )
    fig = px.bar(
        age_summary,
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
    fig.update_traces(
        texttemplate="%{x:,.0f}",
        textposition="outside",
        textfont=dict(size=9, color="#29445f"),
        cliponaxis=False,
    )
    _base_plot_layout(fig, height=235, margin=dict(l=8, r=38, t=34, b=18))
    fig.update_layout(
        title=dict(text="Ageing – Stock", font=dict(size=11, color="#1f3a59"), x=.01),
        showlegend=False,
        xaxis=dict(title=None, gridcolor="#edf2f7"),
        yaxis=dict(title=None, tickfont=dict(size=9), automargin=True),
        bargap=.35,
    )
    return fig


def _stock_date_distribution(filtered, as_on_date, view):
    trend_source = filtered[["gr_no", "stock_days"]].copy()
    trend_source["stock_days"] = trend_source["stock_days"].fillna(0).clip(lower=0)
    trend_source["Stock Date"] = pd.Timestamp(as_on_date) - pd.to_timedelta(
        trend_source["stock_days"], unit="D"
    )

    if view == "D":
        trend_source["Period Key"] = trend_source["Stock Date"].dt.floor("D")
        trend_source["Period"] = trend_source["Stock Date"].dt.strftime("%d %b")
    elif view == "M":
        trend_source["Period Key"] = trend_source["Stock Date"].dt.to_period("M").dt.start_time
        trend_source["Period"] = trend_source["Stock Date"].dt.strftime("%b %Y")
    elif view == "Q":
        trend_source["Period Key"] = trend_source["Stock Date"].dt.to_period("Q").dt.start_time
        trend_source["Period"] = (
            "Q" + trend_source["Stock Date"].dt.quarter.astype(str)
            + " " + trend_source["Stock Date"].dt.year.astype(str)
        )
    else:
        trend_source["Period Key"] = pd.to_datetime(
            trend_source["Stock Date"].dt.year.astype(str) + "-01-01"
        )
        trend_source["Period"] = trend_source["Stock Date"].dt.strftime("%Y")

    trend = (
        trend_source.groupby(["Period Key", "Period"])["gr_no"]
        .nunique()
        .reset_index(name="GR Count")
        .sort_values("Period Key")
    )

    # Keep the lower panel readable instead of rendering hundreds of day bars.
    max_points = 14 if view == "D" else 18
    if len(trend) > max_points:
        trend = trend.tail(max_points)

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
        textfont=dict(size=8, color="#29445f"),
        cliponaxis=False,
    )
    _base_plot_layout(fig, height=225, margin=dict(l=8, r=8, t=34, b=34))
    fig.update_layout(
        title=dict(text="Stock Date Distribution", font=dict(size=11, color="#1f3a59"), x=.01),
        xaxis_title=None,
        yaxis_title=None,
        xaxis=dict(tickangle=-35 if view == "D" else 0, tickfont=dict(size=8)),
        yaxis=dict(gridcolor="#edf2f7", tickfont=dict(size=8)),
        bargap=.28,
    )
    return fig


def _prepare_action_required(filtered, limit=12):
    action_df = filtered.sort_values(
        ["stock_days", "balance_charge_weight"], ascending=False
    ).copy()
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

    display = action_df[
        ["gr_no", "origin", "destination", "branch", "Issue", "stock_days"]
    ].rename(
        columns={
            "gr_no": "GR Number",
            "origin": "Origin",
            "destination": "Destination",
            "branch": "Current Location",
            "stock_days": "Ageing",
        }
    )
    display["Ageing"] = display["Ageing"].map(lambda value: f"{value:.0f} Days")
    return display.head(limit)


def _prepare_branch_pending(filtered, limit=12):
    branch_summary = (
        filtered.groupby("branch")
        .agg(
            Active=("gr_no", "nunique"),
            In_Transit=("stock_type", lambda s: int((s == "IN-TRANSIT STOCK").sum())),
            Transit_Stock=("stock_type", lambda s: int((s == "TRANSIT STOCK").sum())),
            Critical_15d=("is_critical", "sum"),
            Avg_Dwell=("stock_days", "mean"),
        )
        .sort_values("Active", ascending=False)
        .reset_index()
        .head(limit)
    )
    branch_summary["Avg_Dwell"] = branch_summary["Avg_Dwell"].map(lambda v: f"{v:.1f} d")
    return branch_summary.rename(
        columns={
            "branch": "Location",
            "In_Transit": "In-Transit",
            "Transit_Stock": "Transit Stock",
            "Critical_15d": "15d+",
            "Avg_Dwell": "Avg Dwell",
        }
    )


def _prepare_routes(filtered, limit=10):
    routes = (
        filtered.groupby(["origin", "destination"])
        .agg(
            Active_GR=("gr_no", "nunique"),
            Critical=("is_critical", "sum"),
            Avg_Age=("stock_days", "mean"),
        )
        .sort_values("Active_GR", ascending=False)
        .reset_index()
        .head(limit)
    )
    routes["Route"] = routes["origin"].astype(str) + " → " + routes["destination"].astype(str)
    routes["Avg_Age"] = routes["Avg_Age"].map(lambda x: f"{x:.1f} d")
    return routes[["Route", "Active_GR", "Critical", "Avg_Age"]].rename(
        columns={"Active_GR": "Active GR", "Avg_Age": "Avg Age"}
    )


def _prepare_priority_details(filtered, limit=10):
    details = filtered.sort_values(["stock_days", "stock_topay"], ascending=False).copy()
    details["Weight"] = details["balance_charge_weight"].fillna(0).map(lambda x: f"{x:,.0f} kg")
    details["To-Pay"] = details["stock_topay"].fillna(0).map(_fmt_money)
    details["Age"] = details["stock_days"].fillna(0).map(lambda x: f"{x:.0f} d")
    return (
        details[["gr_no", "branch", "stock_type", "Weight", "To-Pay", "Age"]]
        .rename(columns={"gr_no": "GR", "branch": "Branch", "stock_type": "Status"})
        .head(limit)
    )


def show_stock_operations():
    """Render the professional stock control-tower dashboard."""
    _inject_css()

    today = date.today()
    month_start = today.replace(day=1)

    # Header + date controls
    with st.container(key="stock_header"):
        top_left, top_meta = st.columns([3.8, 1.15], gap="small")
        with top_left:
            st.markdown(
                """
                <div class="stock-brand-row">
                  <div class="stock-brand-mark">
                    <div class="stock-brand-symbol"></div>
                    <div>
                      <div class="stock-brand-name">SUGAM</div>
                      <div class="stock-brand-tag">Connects Possibilities</div>
                    </div>
                  </div>
                  <div class="stock-heading">
                    <div class="stock-title">Stock Operations Control Tower</div>
                    <div class="stock-sub">Branch stock · ageing exposure · operational action queue</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with top_meta:
            st.markdown(
                f"""
                <div class="stock-header-meta">
                  <div class="stock-live">LIVE</div>
                  <div class="stock-updated">Data updated {today:%d %b %Y}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        date_cols = st.columns([.8, .8, .8, .7, .78], gap="small")
        with date_cols[0]:
            start_date = st.date_input(
                "From Date",
                value=month_start,
                max_value=today,
                format="DD/MM/YYYY",
                key="stock_dashboard_from_date",
            )
        with date_cols[1]:
            end_date = st.date_input(
                "To Date",
                value=today,
                max_value=today,
                format="DD/MM/YYYY",
                key="stock_dashboard_to_date",
            )
        with date_cols[2]:
            as_on_date = st.date_input(
                "As-on Date",
                value=end_date,
                max_value=today,
                format="DD/MM/YYYY",
                key="stock_dashboard_as_on_date",
            )
        with date_cols[3]:
            run_report = st.button(
                "🔎 Run Report",
                type="primary",
                use_container_width=True,
                key="stock_dashboard_run_report",
            )
        with date_cols[4]:
            download_placeholder = st.empty()

    report_signature = (start_date.isoformat(), end_date.isoformat(), as_on_date.isoformat())
    if run_report:
        st.session_state["stock_dashboard_last_run"] = report_signature

    # First open should render automatically; later date changes require Run Report.
    if "stock_dashboard_last_run" not in st.session_state:
        st.session_state["stock_dashboard_last_run"] = report_signature

    if st.session_state.get("stock_dashboard_last_run") != report_signature:
        st.info("Date filters changed. Click Run Report to refresh the dashboard.")
        return

    if start_date > end_date:
        st.error("From Date cannot be after To Date.")
        return
    if as_on_date < start_date:
        st.error("As-on Date cannot be before From Date.")
        return

    try:
        with st.spinner("Loading live stock data from ERP..."):
            stock_df = _attach_stock_hierarchy(
                load_stock_data(
                    start_date=start_date,
                    end_date=end_date,
                    as_on_date=as_on_date,
                )
            )
            locked_zone, locked_circle, locked_branch = _derive_role_scope(stock_df)
            stock_df = _apply_locked_scope(
                stock_df,
                locked_zone,
                locked_circle,
                locked_branch,
            )
    except Exception as exc:
        st.error(f"Stock dashboard data could not be loaded: {exc}")
        return

    if stock_df.empty:
        st.warning("No stock data is available for your assigned scope.")
        return

    # Top compact operational filters
    st.markdown(
        '<div class="stock-filter-title">STOCK FILTERS <span class="stock-filter-hint">Use filters to drill down without reloading ERP data</span></div>',
        unsafe_allow_html=True,
    )
    primary_filters = st.columns(6, gap="small")
    working_df = stock_df

    with primary_filters[0]:
        if locked_zone:
            selected_zones = st.multiselect(
                "Zone", [locked_zone], default=[locked_zone], disabled=True, key="stock_zone_locked"
            )
        else:
            selected_zones = st.multiselect(
                "Zone", _safe_options(working_df, "zone"), placeholder="All", key="stock_zone_filter"
            )
    if selected_zones:
        working_df = working_df[_match_scope_values(working_df["zone"], selected_zones)]

    with primary_filters[1]:
        if locked_circle:
            selected_circles = st.multiselect(
                "Circle", [locked_circle], default=[locked_circle], disabled=True, key="stock_circle_locked"
            )
        else:
            selected_circles = st.multiselect(
                "Circle", _safe_options(working_df, "circle"), placeholder="All", key="stock_circle_filter"
            )
    if selected_circles:
        working_df = working_df[_match_scope_values(working_df["circle"], selected_circles)]

    with primary_filters[2]:
        branch_options = _safe_options(working_df, "branch")
        if locked_branch:
            branches = st.multiselect(
                "Current Stock Branch",
                branch_options,
                default=branch_options,
                disabled=True,
                key="stock_branch_locked",
            )
        else:
            branches = st.multiselect(
                "Current Stock Branch", branch_options, placeholder="All", key="stock_branch_filter"
            )
    branch_df = working_df[_match_scope_values(working_df["branch"], branches)] if branches else working_df

    with primary_filters[3]:
        stock_types = st.multiselect(
            "Stock Type", _safe_options(branch_df, "stock_type"), placeholder="All", key="stock_type_filter"
        )
    type_df = branch_df[_match_scope_values(branch_df["stock_type"], stock_types)] if stock_types else branch_df

    with primary_filters[4]:
        age_bands = st.multiselect(
            "Ageing Bucket", _safe_options(type_df, "age_band"), placeholder="All", key="stock_age_filter"
        )
    age_df = type_df[_match_scope_values(type_df["age_band"], age_bands)] if age_bands else type_df

    with primary_filters[5]:
        load_types = st.multiselect(
            "Load Type", _safe_options(age_df, "load_type"), placeholder="PTL & FTL", key="stock_load_filter"
        )
    load_df = age_df[_match_scope_values(age_df["load_type"], load_types)] if load_types else age_df

    with st.expander("Advanced Route Filters", expanded=False):
        route_filters = st.columns(3, gap="small")
        with route_filters[0]:
            origins = st.multiselect("GR Origin", _safe_options(load_df, "origin"), placeholder="All origins")
        origin_df = load_df[load_df["origin"].isin(origins)] if origins else load_df

        with route_filters[1]:
            destinations = st.multiselect(
                "GR Destination", _safe_options(origin_df, "destination"), placeholder="All destinations"
            )
        destination_df = origin_df[origin_df["destination"].isin(destinations)] if destinations else origin_df

        with route_filters[2]:
            destination_zones = st.multiselect(
                "Destination Zone",
                _safe_options(destination_df, "destination_zone"),
                placeholder="All zones",
            )
        filtered = (
            destination_df[destination_df["destination_zone"].isin(destination_zones)]
            if destination_zones
            else destination_df
        )

    if filtered.empty:
        st.warning("No records match the selected filters.")
        return

    download_placeholder.download_button(
        "⇩ Download CSV",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"stock_operations_{as_on_date:%d-%m-%Y}.csv",
        mime="text/csv",
        use_container_width=True,
        key="stock_dashboard_download_csv",
    )

    # KPI row
    type_counts = {stock_type: _count_type(filtered, stock_type) for stock_type in STOCK_ORDER}
    critical = int(filtered.get("is_critical", pd.Series(False, index=filtered.index)).fillna(False).sum())
    total_gr = max(int(filtered["gr_no"].nunique()), 1)

    transit_age = filtered.loc[
        filtered["stock_type"].eq("TRANSIT STOCK"), "stock_days"
    ].mean()
    transit_age_note = f"Avg dwell {transit_age:.1f} d" if pd.notna(transit_age) else "Avg dwell -"

    kpis = [
        (
            "Booking Stock",
            f"{type_counts['BOOKING STOCK']:,}",
            f"{_fmt_money(_sum_where(filtered, 'BOOKING STOCK', 'stock_topay'))} exposure",
            "◆",
            PALETTE["blue"],
            False,
        ),
        (
            "In-Transit",
            f"{type_counts['IN-TRANSIT STOCK']:,}",
            f"{_fmt_number(_sum_where(filtered, 'IN-TRANSIT STOCK', 'balance_packages'))} packages",
            "🚚",
            PALETTE["cyan"],
            False,
        ),
        (
            "Transit Stock",
            f"{type_counts['TRANSIT STOCK']:,}",
            transit_age_note,
            "↔",
            PALETTE["purple"],
            False,
        ),
        (
            "Delivery Stock",
            f"{type_counts['DELIVERY STOCK']:,}",
            f"{_fmt_number(_sum_where(filtered, 'DELIVERY STOCK', 'balance_packages'))} packages",
            "✓",
            PALETTE["green"],
            False,
        ),
        (
            "Critical 15+ Days",
            f"{critical:,}",
            f"{critical / total_gr * 100:.1f}% of GR",
            "!",
            PALETTE["red"],
            True,
        ),
        (
            "Balance Packages",
            _fmt_number(filtered["balance_packages"].fillna(0).sum()),
            f"{_fmt_number(filtered['balance_charge_weight'].fillna(0).sum())} kg",
            "▣",
            PALETTE["orange"],
            False,
        ),
        (
            "Stock To-Pay",
            _fmt_money(filtered["stock_topay"].fillna(0).sum()),
            "Collection exposure",
            "₹",
            PALETTE["blue"],
            False,
        ),
    ]

    kpi_cols = st.columns(7, gap="small")
    for column, values in zip(kpi_cols, kpis):
        with column:
            st.markdown(_kpi_card(*values), unsafe_allow_html=True)

    # Primary visual row
    current_zone_col, destination_zone_col, load_col = st.columns([1.05, 1.05, 1], gap="small")
    with current_zone_col:
        with st.container(border=True):
            _zone_bar(filtered, "zone", "Stock by Current Zone")
    with destination_zone_col:
        with st.container(border=True):
            _zone_bar(filtered, "destination_zone", "Stock by Destination Zone")
    with load_col:
        with st.container(border=True):
            _donut(filtered, "load_type", "PTL / FTL Overview")

    # Operational insight cards (not a table)
    _render_operational_insights(filtered)

    # Action + branch pending
    action_col, branch_col = st.columns(2, gap="small")
    with action_col:
        with st.container(border=True):
            st.markdown(
                '<div class="stock-panel-title alert"><span style="font-size:10.5px;color:#b72d36">🎯 Action Required</span><span>Highest ageing first</span></div>',
                unsafe_allow_html=True,
            )
            _render_table(
                _prepare_action_required(filtered),
                height=255,
                key="action_required_grid",
            )

    with branch_col:
        with st.container(border=True):
            st.markdown(
                '<div class="stock-panel-title"><span style="font-size:10.5px;color:#1f3a59">▦ Branch / Location Pending</span><span>All active locations</span></div>',
                unsafe_allow_html=True,
            )
            _render_table(
                _prepare_branch_pending(filtered),
                height=255,
                key="branch_pending_grid",
            )

    # Four lower panels like the approved mock-up
    lower1, lower2, lower3, lower4 = st.columns([1.05, 1.05, .85, 1.1], gap="small")

    with lower1:
        with st.container(border=True):
            fig = _ageing_chart(filtered)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with lower2:
        with st.container(border=True):
            view = st.segmented_control(
                "Distribution period",
                options=["D", "M", "Q", "Y"],
                default="M",
                key="stock_age_distribution_period",
                label_visibility="collapsed",
            )
            fig = _stock_date_distribution(filtered, as_on_date, view)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with lower3:
        with st.container(border=True):
            st.markdown(
                '<div class="stock-panel-title"><span style="font-size:10.5px;color:#1f3a59">↗ Routes by Active Stock</span><span>Top routes</span></div>',
                unsafe_allow_html=True,
            )
            _render_table(_prepare_routes(filtered, limit=8), height=245, key="routes_grid")

    with lower4:
        with st.container(border=True):
            st.markdown(
                '<div class="stock-panel-title"><span style="font-size:10.5px;color:#1f3a59">★ Priority Stock Details</span><span>Critical first</span></div>',
                unsafe_allow_html=True,
            )
            _render_table(
                _prepare_priority_details(filtered, limit=8),
                height=245,
                key="priority_details_grid",
            )

    # Keep mapping exceptions available without cluttering the control tower.
    unmapped_mask = (
        filtered["zone"].isna()
        | filtered["zone"].astype(str).str.strip().str.casefold().isin(
            ["", "unmapped", "unknown", "none", "nan"]
        )
    )
    unmapped_rows = filtered.loc[unmapped_mask].copy()
    if not unmapped_rows.empty:
        unmapped_gr = int(unmapped_rows["gr_no"].nunique())
        with st.expander(f"Data Quality: Unmapped Current-Zone Branches — {unmapped_gr:,} GR"):
            unmapped_summary = (
                unmapped_rows[["gr_no", "branchcode_key", "branch", "origin", "destination"]]
                .drop_duplicates()
                .sort_values(["branch", "gr_no"], ascending=[True, True])
                .rename(
                    columns={
                        "gr_no": "GR Number",
                        "branchcode_key": "Branch Code",
                        "branch": "Current Stock Branch",
                        "origin": "Origin",
                        "destination": "Destination",
                    }
                )
            )
            _render_table(unmapped_summary, height=220, key="unmapped_current_zone_branches_grid")

    st.markdown(
        f"""
        <div class="stock-footer">
          <div>© {today:%Y} Sugam Logistics · Stock Operations</div>
          <div>Data is operational and confidential · As-on {as_on_date:%d %b %Y}</div>
          <div>Built for faster action.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Compatibility with routers that expect show().
def show():
    show_stock_operations()


if __name__ == "__main__":
    show_stock_operations()
