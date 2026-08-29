"""Analytics & Trends page for Sugam Dashboard."""

from __future__ import annotations

import html
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

from services.stock_branch_mast import load_stock_branch_mast
from services.stock_data_loader import load_stock_data

# Use same palette as main dashboard
PALETTE = {
    "blue": "#2f73d8", "orange": "#ed8b25", "cyan": "#1e91a0",
    "purple": "#7953c6", "green": "#269b54", "red": "#d63f48",
    "brown": "#8a613d", "navy": "#0b3158", "text": "#172238",
}

STOCK_ORDER = [
    "BOOKING STOCK",
    "IN-TRANSIT STOCK",
    "TRANSIT STOCK",
    "DELIVERY STOCK",
]


def _inject_css():
    """Apply compact Stock Operations dashboard styling."""
    st.markdown(
        """
        <style>
        [data-testid="stHeader"]{height:1.8rem!important;background:transparent}
        [data-testid="stAppViewContainer"]{background:#f4f7fb}
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        .main .block-container,
        .block-container{
            padding-top:.1rem!important;
            padding-left:.75rem!important;
            padding-right:.75rem!important;
            width:100%!important;
            max-width:100%!important;
        }
        .main .block-container{
            padding-top:.15rem!important;
            padding-bottom:1rem!important;
            max-width:100%!important;
        }
        section.main,
        section.main>div,
        [data-testid="stAppViewContainer"] .main{
            width:100%!important;
            max-width:100%!important;
        }
        [data-testid="stVerticalBlock"]{gap:.25rem!important}
        [data-testid="stHorizontalBlock"]{gap:.5rem!important}

        .stock-hero{
            display:flex;justify-content:space-between;align-items:center;
            padding:13px 17px;border-radius:12px;
            background:linear-gradient(115deg,#082b57 0%,#10579b 58%,#1587b8 100%);
            box-shadow:none;margin:0;color:#fff;background:transparent;padding:0;
        }
        .st-key-stock_header{
            padding:7px 12px;border-radius:10px;
            background:linear-gradient(115deg,#082b57 0%,#10579b 58%,#1587b8 100%);
            box-shadow:0 7px 18px rgba(8,43,87,.18);margin:0 0 4px;
        }
        .st-key-stock_header label{color:#e9f4ff!important}
        .st-key-stock_header div[data-testid="stDateInput"] label,
        .st-key-stock_header div[data-testid="stDateInput"] label p{
            color:#ffffff!important;font-weight:800!important;
        }
        .st-key-stock_header [data-testid="stHorizontalBlock"]{align-items:end}
        .stock-title{font:800 16px/1.15 Inter,sans-serif;color:#fff;margin:0 0 2px}
        .stock-sub{font:500 7px/1.25 Inter,sans-serif;color:#d9eaff;margin:0}
        .stock-live{
            display:flex;align-items:center;gap:6px;background:rgba(255,255,255,.13);
            border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 10px;
            font:750 8px Inter,sans-serif;letter-spacing:.4px;
        }
        .stock-live:before{content:"";width:7px;height:7px;border-radius:50%;background:#43e594;box-shadow:0 0 0 4px rgba(67,229,148,.15)}
        .stock-filter-title{font:800 10px Inter,sans-serif;color:#193653;margin-bottom:2px}
        div[data-testid="stExpander"]{
            border:1px solid #e1e8f0!important;border-radius:7px!important;
            background:#f8fafc!important;
        }
        div[data-testid="stExpander"] summary{
            min-height:25px!important;height:25px!important;font-size:8px!important;font-weight:750!important;
            color:#38516d!important;
        }

        div[data-testid="stDateInput"] label,
        div[data-testid="stSelectbox"] label,
        div[data-testid="stMultiSelect"] label,
        div[data-testid="stTextInput"] label{
            font-size:8px!important;font-weight:700!important;
            color:#334155!important;margin-bottom:1px!important;
        }
        div[data-testid="stDateInput"] input,
        div[data-testid="stTextInput"] input,
        div[data-baseweb="select"]>div{
            min-height:27px!important;height:27px!important;
            font-size:8px!important;border-radius:6px!important;
        }
        div[data-testid="stButton"] button{
            min-height:27px!important;height:27px!important;
            padding:0 .65rem!important;border-radius:7px!important;border:0!important;
            background:linear-gradient(100deg,#ef4b4f,#e22f45)!important;
            box-shadow:0 4px 10px rgba(226,47,69,.22)!important;
            font-size:9px!important;font-weight:800!important;
        }
        div[data-testid="stDownloadButton"] button{
            min-height:27px!important;height:27px!important;border:0!important;
            border-radius:7px!important;color:#fff!important;
            background:linear-gradient(100deg,#1473c9,#0d9bb5)!important;
            box-shadow:0 4px 10px rgba(20,115,201,.2)!important;
            font-size:9px!important;font-weight:800!important;
        }
        div[data-testid="stSegmentedControl"]{justify-content:flex-end!important}
        div[data-testid="stSegmentedControl"] button{
            min-height:25px!important;height:25px!important;min-width:34px!important;
            padding:0 9px!important;font-size:8px!important;font-weight:800!important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]{
            background:#fff!important;border:1px solid #dce5ef!important;border-radius:10px!important;
            box-shadow:0 3px 10px rgba(20,40,65,.055)!important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]>div{
            padding:.35rem .55rem!important;
        }
        .stock-filter-divider{height:1px;background:#edf0f4;margin:1px 0 3px}

        .stock-kpi{
            position:relative;overflow:hidden;min-height:64px;display:flex;align-items:flex-start;gap:7px;
            background:linear-gradient(145deg,#fff,#f9fbfe);border:1px solid #dfe7f0;border-radius:10px;
            padding:7px 8px;box-shadow:0 4px 12px rgba(20,40,65,.065);
            transition:transform .15s ease,box-shadow .15s ease;
        }
        .stock-kpi:before{content:"";position:absolute;left:0;top:0;right:0;height:3px;background:var(--tone)}
        .stock-kpi:hover{transform:translateY(-2px);box-shadow:0 7px 16px rgba(20,40,65,.11)}
        .stock-kpi-red{border-color:#f4c9cc;background:#fffafa}
        .stock-kpi-icon{
            width:25px;height:25px;min-width:25px;border-radius:7px;
            display:flex;align-items:center;justify-content:center;
            font-size:12px;font-weight:800;
        }
        .stock-kpi-copy{min-width:0}
        .stock-kpi-label{font:750 8px/1.15 Inter,sans-serif;color:#607086;text-transform:uppercase;letter-spacing:.2px}
        .stock-kpi-value{font:850 15px/1.15 Inter,sans-serif;color:#142a44;margin-top:2px}
        .stock-kpi-note{
            font:500 7px/1.2 Inter,sans-serif;color:#718096;
            margin-top:2px;white-space:normal;
        }

        .stock-panel-title,.stock-alert-title{
            display:flex;justify-content:space-between;align-items:center;
            min-height:20px;position:relative;z-index:3;
            font:800 10px/1.25 Inter,sans-serif;color:#20344e;
            margin:0 0 8px;padding:2px 1px 4px;
        }
        .stock-panel-title span{font-size:7px;font-weight:650;color:#8290a2}
        .stock-alert-title{color:#b4232c}

        .stock-flow-wrap{
            width:100%;overflow-x:auto;padding:12px 4px 7px;
        }
        .stock-flow{
            min-width:560px;display:flex;align-items:center;
            justify-content:space-between;gap:5px;
        }
        .stock-flow-step{
            flex:1;text-align:center;display:flex;flex-direction:column;
            align-items:center;gap:3px;font:700 8px/1.1 Inter,sans-serif;
        }
        .stock-flow-step strong{font-size:13px;color:#172238}
        .stock-flow-dot{
            width:36px;height:36px;border:2px solid currentColor;border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            background:#fff;font-size:13px;box-shadow:0 4px 10px rgba(20,40,65,.09);
        }
        .stock-flow-arrow{color:#a0aaba;font-size:15px;font-weight:800}
        .stock-insight-grid{
            display:grid;grid-template-columns:repeat(3,1fr);gap:8px;
            padding:5px 0 2px;
        }
        .stock-insight{
            min-height:62px;padding:9px;border-radius:9px;
            background:linear-gradient(145deg,#f8fbff,#ffffff);
            border:1px solid #e0e8f1;position:relative;overflow:hidden;
        }
        .stock-insight:before{
            content:"";position:absolute;left:0;top:0;bottom:0;width:3px;
            background:var(--accent);
        }
        .stock-insight-label{
            font:750 7px/1.15 Inter,sans-serif;color:#718096;
            text-transform:uppercase;letter-spacing:.25px;
        }
        .stock-insight-value{
            font:850 14px/1.2 Inter,sans-serif;color:#17314f;margin-top:5px;
        }
        .stock-insight-note{font:550 7px/1.2 Inter,sans-serif;color:#8290a2;margin-top:2px}

        div[data-testid="stDataFrame"]{
            font-size:8px!important;margin-top:2px!important;
            position:relative!important;z-index:1!important;
        }
        div[data-testid="stDataFrame"] [role="columnheader"]{
            background:#0b3158!important;color:#fff!important;
            border-color:#274d75!important;font-size:8px!important;font-weight:800!important;
        }
        div[data-testid="stDataFrame"] [role="columnheader"] *{color:#fff!important}
        .stock-table-scroll{
            width:100%;overflow:auto;border:1px solid #d9e2ec;
            border-radius:7px;background:#fff;
        }
        table.stock-html-table{
            width:100%;min-width:720px;border-collapse:separate;border-spacing:0;
            font:500 10px/1.25 Inter,sans-serif;color:#26384f;
        }
        table.stock-html-table thead th{
            position:sticky;top:0;z-index:5;
            padding:9px 10px!important;text-align:left!important;
            background:#0b3158!important;color:#ffffff!important;
            border-right:1px solid #315578!important;
            border-bottom:1px solid #082747!important;
            font-weight:800!important;white-space:nowrap;
        }
        table.stock-html-table thead th:last-child{border-right:0!important}
        table.stock-html-table tbody td{
            padding:8px 10px;border-right:1px solid #e4e9ef;
            border-bottom:1px solid #e4e9ef;white-space:nowrap;
        }
        table.stock-html-table tbody tr:nth-child(even){background:#f7f9fc}
        table.stock-html-table tbody tr:hover{background:#eaf3ff}
        .stPlotlyChart{margin:-5px 0 -8px!important}
        .stock-view-all,.stock-note,.stock-footer{
            font:500 7px/1.35 Inter,sans-serif;color:#718096;
        }
        .stock-view-all{text-align:right;margin-top:2px}
        .stock-note{
            background:#f7f9fc;border:1px solid #e3e8ef;
            border-radius:6px;padding:6px 8px;margin-top:3px;
        }
        .stock-footer{text-align:center;padding-top:4px}
        .stock-summary{
            display:grid;grid-template-columns:repeat(7,1fr);
            border:1px solid #dde3ea;border-radius:7px;background:#fff;
            margin-top:2px;
        }
        .stock-summary span{
            padding:6px 8px;border-right:1px solid #e8edf3;
            font:650 7px/1.2 Inter,sans-serif;color:#718096;
        }
        .stock-summary span:last-child{border-right:0}
        .stock-summary strong{display:block;font-size:11px;color:#172238;margin-top:2px}
        .stock-critical{color:#d63f48!important}.stock-orange{color:#ed8b25!important}

        @media(max-width:1000px){
            .stock-summary{grid-template-columns:repeat(2,1fr)}
            .stock-summary span{border-bottom:1px solid #e8edf3}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _apply_scope(df):
    """Apply branch/circle/zone filters from session state."""
    scope = st.session_state.get("data_scope", {}) or {}
    rules = [
        ("branch", "branch"),
        ("circle", "origin_circle"),
        ("zone", "origin_zone"),
    ]
    scoped = df.copy()
    for scope_key, column in rules:
        value = scope.get(scope_key)
        if value and column in scoped.columns:
            scoped = scoped[scoped[column].astype(str).str.casefold() == str(value).casefold()]
    return scoped


def _fmt_money(value):
    """Format rupees with Cr/L suffix."""
    value = float(value)
    if abs(value) >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if abs(value) >= 100_000:
        return f"₹{value / 100_000:.2f} L"
    return f"₹{value:,.0f}"


def _fmt_number(value):
    """Format large numbers with commas."""
    return f"{float(value):,.0f}"


def show():
    """Main analytics page."""
    _inject_css()
    
    # Page title
    st.markdown('<h1 class="analytics-title">📈 Analytics & Trends</h1>', unsafe_allow_html=True)
    st.markdown('<p class="analytics-subtitle">Historical analysis, trends, and forecasting</p>', unsafe_allow_html=True)
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("Filters")
        
        start_date = st.date_input("From Date", value=date.today().replace(day=1))
        end_date = st.date_input("To Date", value=date.today())
        
        # Load data
        if start_date > end_date:
            st.error("Start date must be before end date")
            return
    
    # Load data with cache
    try:
        raw_data = load_stock_data(start_date, end_date, end_date)
        if raw_data.empty:
            st.warning("No data available for selected date range.")
            return
    except Exception as e:
        st.error(f"Data load error: {str(e)}")
        return
    
    # Apply scope filters
    filtered = _apply_scope(raw_data)
    
    if filtered.empty:
        st.warning("No records match the selected filters.")
        return
    
    # ============ METRIC CARDS ============
    col1, col2, col3, col4 = st.columns(4, gap="small")
    
    with col1:
        total_records = len(filtered)
        avg_age = filtered["stock_days"].mean()
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{total_records:,.0f}</div>
            <div class="metric-label">Total Records</div>
            <div class="metric-label" style="margin-top:6px">Avg Age: {avg_age:.1f} days</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_stock_value = filtered["stock_topay"].sum()
        paid_amount = filtered["paid"].sum()
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{_fmt_money(total_stock_value)}</div>
            <div class="metric-label">Stock Value</div>
            <div class="metric-label" style="margin-top:6px">Paid: {_fmt_money(paid_amount)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        critical_count = len(filtered[filtered["is_critical"]])
        critical_pct = (critical_count / len(filtered) * 100)
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{critical_count:,.0f}</div>
            <div class="metric-label">Critical Items (15+ days)</div>
            <div class="metric-label" style="margin-top:6px">{critical_pct:.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_packages = filtered["balance_packages"].sum()
        total_weight = filtered["balance_charge_weight"].sum()
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{_fmt_number(total_packages)}</div>
            <div class="metric-label">Total Packages</div>
            <div class="metric-label" style="margin-top:6px">{_fmt_number(total_weight)} kg</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # ============ STOCK AGE TREND (30/60/90 days) ============
    col_trend, col_abc = st.columns([1.5, 1], gap="small")
    
    with col_trend:
        with st.container(border=True):
            st.markdown("**📊 Stock Age Trend**")
            
            # Create day-wise trend
            trend_data = filtered.groupby("stock_days")["gr_no"].nunique().reset_index(name="Count")
            trend_data = trend_data.sort_values("stock_days")
            
            fig = px.line(
                trend_data,
                x="stock_days",
                y="Count",
                title="Distribution of Stock by Age (in days)",
                labels={"stock_days": "Days", "Count": "Number of GRs"},
                markers=True,
            )
            fig.update_traces(line=dict(color=PALETTE["blue"], width=2), marker=dict(size=6))
            fig.update_layout(
                height=280,
                margin=dict(l=8, r=8, t=30, b=30),
                hovermode="x unified",
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(size=9),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    with col_abc:
        with st.container(border=True):
            st.markdown("**🎯 ABC Analysis**")
            
            # ABC Analysis: 80-20 rule
            gr_value = filtered.groupby("gr_no")["stock_topay"].sum().sort_values(ascending=False).reset_index(name="value")
            total_value = gr_value["value"].sum()
            gr_value["cumsum"] = gr_value["value"].cumsum() / total_value * 100
            
            gr_value["category"] = pd.cut(
                gr_value["cumsum"],
                bins=[0, 80, 95, 100],
                labels=["A (80%)", "B (15%)", "C (5%)"],
            )
            
            abc_summary = gr_value.groupby("category", observed=True).agg({
                "gr_no": "count",
                "value": "sum",
            }).reset_index().rename(columns={"gr_no": "Items", "value": "Value"})
            
            fig = px.bar(
                abc_summary,
                x="category",
                y=["Items"],
                color="category",
                color_discrete_map={
                    "A (80%)": PALETTE["red"],
                    "B (15%)": PALETTE["orange"],
                    "C (5%)": PALETTE["green"],
                },
                text="Items",
            )
            fig.update_layout(
                height=280,
                margin=dict(l=8, r=8, t=30, b=30),
                showlegend=False,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(size=9),
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    st.divider()
    
    # ============ STOCK TYPE MOVEMENT ============
    col_type, col_dwell = st.columns([1, 1], gap="small")
    
    with col_type:
        with st.container(border=True):
            st.markdown("**🚛 Stock Type Distribution**")
            
            type_dist = filtered.groupby("stock_type")["gr_no"].nunique().reset_index(name="Count")
            
            fig = px.bar(
                type_dist,
                x="stock_type",
                y="Count",
                color="stock_type",
                color_discrete_sequence=[PALETTE["blue"], PALETTE["orange"], PALETTE["green"], PALETTE["purple"]],
                text="Count",
            )
            fig.update_layout(
                height=280,
                margin=dict(l=8, r=8, t=30, b=30),
                showlegend=False,
                xaxis_title=None,
                yaxis_title=None,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(size=9),
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    with col_dwell:
        with st.container(border=True):
            st.markdown("**⏱️ Average Dwell Time by Branch**")
            
            dwell_data = filtered.groupby("branch").agg({
                "stock_days": "mean",
                "gr_no": "count",
            }).reset_index().rename(columns={"stock_days": "Avg Days", "gr_no": "Items"})
            dwell_data = dwell_data.sort_values("Avg Days", ascending=False).head(8)
            
            fig = px.barh(
                dwell_data,
                x="Avg Days",
                y="branch",
                color="Avg Days",
                color_continuous_scale="RdYlGn_r",
                text="Avg Days",
            )
            fig.update_layout(
                height=280,
                margin=dict(l=80, r=8, t=30, b=30),
                yaxis_title=None,
                xaxis_title=None,
                paper_bgcolor="white",
                plot_bgcolor="white",
                font=dict(size=9),
            )
            fig.update_traces(textposition="outside", texttemplate="%.1f d")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    
    st.divider()
    
    # ============ ROUTE PERFORMANCE HEATMAP ============
    with st.container(border=True):
        st.markdown("**🗺️ Route Performance Heatmap (Origin → Destination)**")
        
        route_perf = filtered.groupby(["origin", "destination"]).agg({
            "stock_days": "mean",
            "gr_no": "count",
        }).reset_index().rename(columns={"stock_days": "Avg Age", "gr_no": "Count"})
        
        # Create pivot for heatmap
        heatmap_data = route_perf.pivot_table(
            values="Avg Age",
            index="origin",
            columns="destination",
            aggfunc="mean",
        )
        
        if not heatmap_data.empty and heatmap_data.shape[0] > 1 and heatmap_data.shape[1] > 1:
            fig = px.imshow(
                heatmap_data,
                labels=dict(x="Destination", y="Origin", color="Avg Days"),
                color_continuous_scale="RdYlGn_r",
                aspect="auto",
                text_auto=".1f",
            )
            fig.update_layout(height=400, font=dict(size=9))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Not enough origin-destination combinations for heatmap visualization.")
    
    st.divider()
    
    # ============ DETAILED ANALYTICS TABLE ============
    with st.container(border=True):
        st.markdown("**📋 Detailed Route Analytics**")
        
        route_analytics = filtered.groupby(["origin", "destination"]).agg({
            "gr_no": "nunique",
            "stock_days": ["mean", "max", "min"],
            "is_critical": "sum",
            "balance_packages": "sum",
            "stock_topay": "sum",
        }).reset_index()
        
        route_analytics.columns = ["Origin", "Destination", "GR Count", "Avg Days", "Max Days", "Min Days", "Critical", "Packages", "Value"]
        route_analytics = route_analytics.sort_values("Avg Days", ascending=False).head(15)
        
        # Format columns
        route_analytics["Route"] = route_analytics["Origin"] + " → " + route_analytics["Destination"]
        route_analytics["Value"] = route_analytics["Value"].map(_fmt_money)
        route_analytics["Avg Days"] = route_analytics["Avg Days"].map(lambda x: f"{x:.1f}d")
        route_analytics["Max Days"] = route_analytics["Max Days"].map(lambda x: f"{x:.0f}d")
        
        display_cols = ["Route", "GR Count", "Avg Days", "Max Days", "Critical", "Packages", "Value"]
        st.dataframe(
            route_analytics[display_cols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )
    
    # ============ FOOTER ============
    st.divider()
    st.markdown(
        f'<div style="text-align:center;color:#718096;font-size:8px;padding-top:6px">'
        f'📊 Analytics · Period {start_date:%d %b %Y} to {end_date:%d %b %Y} · Total Records: {len(filtered):,}'
        f'</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    show()


def _fmt_number(value):
    return f"{float(value):,.0f}"


def _fmt_money(value):
    value = float(value)
    if abs(value) >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if abs(value) >= 100_000:
        return f"₹{value / 100_000:.2f} L"
    return f"₹{value:,.0f}"


def _safe_options(df, column):
    if column not in df.columns or df.empty:
        return []
    return sorted(df[column].dropna().astype(str).unique().tolist(), key=str.casefold)


def _render_table(df, height=300, key="stock_grid"):
    toolbar_spacer, download_col = st.columns([12, 1])
    with download_col:
        st.download_button(
            "↓",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{key}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download this table as CSV",
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
        headerHeight=34,
        rowHeight=31,
        suppressRowClickSelection=True,
    )
    AgGrid(
        df,
        gridOptions=builder.build(),
        height=height,
        theme="streamlit",
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=False,
        custom_css={
            ".ag-header": {
                "background-color": "#0b3158 !important",
                "color": "#ffffff !important",
            },
            ".ag-header-cell": {
                "background-color": "#0b3158 !important",
                "color": "#ffffff !important",
                "font-weight": "400 !important",
                "border-right": "1px solid #315578 !important",
            },
            ".ag-header-cell-text": {
                "color": "#ffffff !important",
                "font-weight": "400 !important",
            },
            ".ag-icon": {"color": "#ffffff !important"},
            ".ag-row-even": {"background-color": "#f7f9fc !important"},
        },
        key=key,
    )


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
            "Stock branch hierarchy query is missing required columns: "
            + ", ".join(missing)
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
    enriched["scope_branch"] = enriched["master_branch"].fillna(enriched["branch"])
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
            locked_circle = rows["circle"].dropna().iloc[0] if rows["circle"].notna().any() else locked_circle
            locked_zone = rows["zone"].dropna().iloc[0] if rows["zone"].notna().any() else locked_zone
    elif locked_circle:
        rows = df[_match_scope_value(df["circle"], locked_circle)]
        if not rows.empty:
            locked_circle = rows["circle"].iloc[0]
            locked_zone = rows["zone"].dropna().iloc[0] if rows["zone"].notna().any() else locked_zone
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


def _kpi_card(label, value, note, icon, tone, critical=False):
    css = " stock-kpi-red" if critical else ""
    return f"""
    <div class="stock-kpi{css}" style="--tone:{tone}">
      <div class="stock-kpi-icon" style="background:{tone}18;color:{tone}">{icon}</div>
      <div class="stock-kpi-copy"><div class="stock-kpi-label">{html.escape(label)}</div>
      <div class="stock-kpi-value">{html.escape(str(value))}</div>
      <div class="stock-kpi-note">{html.escape(str(note))}</div></div>
    </div>"""


def _count_type(df, stock_type):
    return int(df.loc[df["stock_type"].eq(stock_type), "gr_no"].nunique())


def _donut(df, column, title):
    grouped = df.groupby(column, dropna=False)["gr_no"].nunique().reset_index(name="GR Count")
    grouped = grouped.sort_values("GR Count", ascending=False)
    fig = px.pie(
        grouped, names=column, values="GR Count", hole=.57,
        color_discrete_sequence=[PALETTE["blue"], PALETTE["green"], PALETTE["orange"], PALETTE["purple"], PALETTE["cyan"]],
    )
    fig.update_traces(
        textinfo="value+percent",
        texttemplate="%{value:,}<br>%{percent}",
        textfont_size=8,
        hovertemplate="%{label}<br>%{value:,} GR (%{percent})<extra></extra>",
    )
    fig.add_annotation(text=f"<b>{df['gr_no'].nunique():,}</b><br><span style='font-size:9px'>Total GR</span>", showarrow=False)
    fig.update_layout(
        title=dict(text=title, font=dict(size=10), x=.01),
        height=215,
        margin=dict(l=4, r=4, t=26, b=46),
        legend=dict(
            font=dict(size=7), orientation="h", x=.5, xanchor="center",
            y=-.08, yanchor="top", entrywidth=86, entrywidthmode="pixels",
        ),
        paper_bgcolor="white",
        uniformtext_minsize=7,
        uniformtext_mode="hide",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _zone_bar(df, column, title):
    grouped = (
        df.groupby(column, dropna=False)["gr_no"]
        .nunique()
        .reset_index(name="GR Count")
        .sort_values("GR Count", ascending=True)
    )
    grouped[column] = grouped[column].fillna("Unmapped").astype(str).str.strip()
    grouped.loc[grouped[column].eq(""), column] = "Unmapped"
    total = max(int(grouped["GR Count"].sum()), 1)
    grouped["Share"] = grouped["GR Count"] / total * 100
    grouped["Label"] = grouped.apply(
        lambda row: (
            f"<b>{int(row['GR Count']):,} GR</b>  ·  "
            f"<span style='color:#1769d2'>{row['Share']:.1f}%</span>"
        ),
        axis=1,
    )

    colours = [
        PALETTE["cyan"], PALETTE["green"], PALETTE["orange"],
        PALETTE["purple"], PALETTE["blue"], PALETTE["brown"],
    ]
    fig = px.bar(
        grouped,
        x="GR Count",
        y=column,
        orientation="h",
        text="Label",
        color=column,
        color_discrete_sequence=colours,
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=10, color="#243b55"),
        cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,} GR<extra></extra>",
    )
    fig.update_layout(
        title=dict(text=title, font=dict(size=11, color="#20344e"), x=.01),
        height=max(245, 42 * len(grouped) + 55),
        margin=dict(l=8, r=95, t=34, b=16),
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(
            title=None,
            tickfont=dict(
                size=9,
                family="Arial Black, Arial, sans-serif",
                color="#20344e",
            ),
            automargin=True,
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        bargap=.30,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _stock_flow(df):
    counts = {stock_type: _count_type(df, stock_type) for stock_type in STOCK_ORDER}
    critical = int(df["is_critical"].sum())
    steps = [
        ("Booking", counts["BOOKING STOCK"], "▤", PALETTE["blue"]),
        ("In-Transit", counts["IN-TRANSIT STOCK"], "🚚", PALETTE["orange"]),
        ("Transit Stock", counts["TRANSIT STOCK"], "⌂", PALETTE["purple"]),
        ("Delivery Stock", counts["DELIVERY STOCK"], "✓", PALETTE["green"]),
        ("Critical 15+", critical, "!", PALETTE["red"]),
    ]
    flow = []
    for index, (label, value, icon, colour) in enumerate(steps):
        flow.append(f'<div class="stock-flow-step" style="color:{colour}"><div class="stock-flow-dot">{icon}</div><b>{label}</b><strong>{value:,}</strong></div>')
        if index < len(steps) - 1:
            flow.append('<div class="stock-flow-arrow">→</div>')
    st.markdown(f'<div class="stock-flow-wrap"><div class="stock-flow">{"".join(flow)}</div></div>', unsafe_allow_html=True)


def _operational_insights(df):
    critical_mask = df["is_critical"].fillna(False).astype(bool)
    overdue_gr = int(df.loc[df["is_edd_overdue"].fillna(False), "gr_no"].nunique())
    missing_edd_gr = int(df.loc[df["edd"].isna(), "gr_no"].nunique())
    critical_delivery = int(
        df.loc[
            critical_mask & df["stock_type"].eq("DELIVERY STOCK"), "gr_no"
        ].nunique()
    )
    critical_transit = int(
        df.loc[
            critical_mask
            & df["stock_type"].isin(["IN-TRANSIT STOCK", "TRANSIT STOCK"]),
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
    if reason_counts.empty:
        top_reason, top_reason_gr = "Not recorded", 0
    else:
        top_reason = str(reason_counts.index[0])
        top_reason_gr = int(reason_counts.iloc[0])

    insights = [
        ("EDD Overdue", f"{overdue_gr:,} GR", "Past committed delivery date", PALETTE["red"]),
        ("Missing EDD", f"{missing_edd_gr:,} GR", "EDD needs to be updated", PALETTE["orange"]),
        ("Critical Delivery", f"{critical_delivery:,} GR", "Delivery stock aged 15+ days", PALETTE["green"]),
        ("Critical Transit", f"{critical_transit:,} GR", "Transit stock aged 15+ days", PALETTE["purple"]),
        ("Highest-Risk Route", risk_route, f"{risk_route_gr:,} critical GR", PALETTE["blue"]),
        ("Top Delay Reason", top_reason, f"{top_reason_gr:,} affected GR", PALETTE["brown"]),
    ]
    return pd.DataFrame(
        [(label, value, note) for label, value, note, _ in insights],
        columns=["Exception", "Current Position", "Action / Meaning"],
    )


def show_stock_operations():
    _inject_css()
    today = date.today()
    month_start = today.replace(day=1)
    with st.container(key="stock_header"):
        title_col, from_col, to_col, as_on_col, run_col, csv_col = st.columns(
            [1.8, .58, .58, .58, .5, .55], gap="small"
        )
        with title_col:
            st.markdown(
                '<div class="stock-hero"><div><div class="stock-title">Stock Operations Control Tower</div>'
                '<div class="stock-sub">Branch stock · ageing exposure · operational action queue</div></div></div>',
                unsafe_allow_html=True,
            )
        with from_col:
            start_date = st.date_input(
                "From Date", value=month_start, max_value=today,
                format="DD/MM/YYYY", key="stock_dashboard_from_date",
            )
        with to_col:
            end_date = st.date_input(
                "To Date", value=today, max_value=today,
                format="DD/MM/YYYY", key="stock_dashboard_to_date",
            )
        with as_on_col:
            as_on_date = st.date_input(
                "As-on Date", value=end_date, max_value=today,
                format="DD/MM/YYYY", key="stock_dashboard_as_on_date",
            )
        with run_col:
            run_report = st.button(
                "Run Report", type="primary", use_container_width=True,
                key="stock_dashboard_run_report",
            )
        with csv_col:
            download_placeholder = st.empty()

    report_signature = (
        start_date.isoformat(),
        end_date.isoformat(),
        as_on_date.isoformat(),
    )
    if run_report:
        st.session_state["stock_dashboard_last_run"] = report_signature

    if st.session_state.get("stock_dashboard_last_run") != report_signature:
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

    with st.container(border=True):
        st.markdown('<div class="stock-filter-title">STOCK FILTERS</div>', unsafe_allow_html=True)
        primary_filters = st.columns(6, gap="small")
        working_df = stock_df

        with primary_filters[0]:
            if locked_zone:
                selected_zones = st.multiselect(
                    "Zone", [locked_zone], default=[locked_zone],
                    disabled=True, key="stock_zone_locked",
                )
            else:
                selected_zones = st.multiselect(
                    "Zone", _safe_options(working_df, "zone"),
                    placeholder="All zones", key="stock_zone_filter",
                )
        if selected_zones:
            working_df = working_df[_match_scope_values(working_df["zone"], selected_zones)]

        with primary_filters[1]:
            if locked_circle:
                selected_circles = st.multiselect(
                    "Circle", [locked_circle], default=[locked_circle],
                    disabled=True, key="stock_circle_locked",
                )
            else:
                selected_circles = st.multiselect(
                    "Circle", _safe_options(working_df, "circle"),
                    placeholder="All circles", key="stock_circle_filter",
                )
        if selected_circles:
            working_df = working_df[_match_scope_values(working_df["circle"], selected_circles)]

        with primary_filters[2]:
            branch_options = _safe_options(working_df, "branch")
            if locked_branch:
                branches = st.multiselect(
                    "Current Stock Branch", branch_options,
                    default=branch_options, disabled=True,
                    key="stock_branch_locked",
                )
            else:
                branches = st.multiselect(
                    "Current Stock Branch", branch_options,
                    placeholder="All branches", key="stock_branch_filter",
                )
        branch_df = working_df[_match_scope_values(working_df["branch"], branches)] if branches else working_df

        with primary_filters[3]:
            stock_types = st.multiselect(
                "Stock Type", _safe_options(branch_df, "stock_type"),
                placeholder="All", key="stock_type_filter",
            )
        type_df = branch_df[_match_scope_values(branch_df["stock_type"], stock_types)] if stock_types else branch_df

        with primary_filters[4]:
            age_bands = st.multiselect(
                "Ageing Bucket",
                _safe_options(type_df, "age_band"),
                placeholder="All ageing",
                key="stock_age_filter",
            )
        age_df = type_df[_match_scope_values(type_df["age_band"], age_bands)] if age_bands else type_df

        with primary_filters[5]:
            load_types = st.multiselect(
                "Load Type", _safe_options(age_df, "load_type"),
                placeholder="PTL & FTL", key="stock_load_filter",
            )
        load_df = age_df[_match_scope_values(age_df["load_type"], load_types)] if load_types else age_df

        with st.expander("GR Route Filters", expanded=False):
            route_filters = st.columns(3, gap="small")
            with route_filters[0]:
                origins = st.multiselect(
                    "GR Origin", _safe_options(load_df, "origin"), placeholder="All origins"
                )
            origin_df = load_df[load_df["origin"].isin(origins)] if origins else load_df

            with route_filters[1]:
                destinations = st.multiselect(
                    "GR Destination",
                    _safe_options(origin_df, "destination"),
                    placeholder="All destinations",
                )
            destination_df = origin_df[origin_df["destination"].isin(destinations)] if destinations else origin_df

            with route_filters[2]:
                destination_zones = st.multiselect(
                    "Destination Zone",
                    _safe_options(destination_df, "destination_zone"),
                    placeholder="All zones",
                )
            zone_df = destination_df[destination_df["destination_zone"].isin(destination_zones)] if destination_zones else destination_df
            filtered = zone_df

    if filtered.empty:
        st.warning("No records match the selected filters.")
        return

    download_placeholder.download_button(
        "Download CSV",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"stock_operations_{as_on_date:%d-%m-%Y}.csv",
        mime="text/csv",
        use_container_width=True,
        key="stock_dashboard_download_csv",
    )

    type_counts = {stock_type: _count_type(filtered, stock_type) for stock_type in STOCK_ORDER}
    critical = int(filtered["is_critical"].sum())
    kpis = [
        ("Booking Stock", type_counts["BOOKING STOCK"], _fmt_money(filtered.loc[filtered.stock_type.eq("BOOKING STOCK"), "stock_topay"].sum()), "▤", PALETTE["blue"], False),
        ("In-Transit", type_counts["IN-TRANSIT STOCK"], f"{_fmt_number(filtered.loc[filtered.stock_type.eq('IN-TRANSIT STOCK'), 'balance_packages'].sum())} packages", "🚚", PALETTE["orange"], False),
        ("Transit Stock", type_counts["TRANSIT STOCK"], "Exact stored-procedure stock type", "⌂", PALETTE["purple"], False),
        ("Delivery Stock", type_counts["DELIVERY STOCK"], f"{_fmt_number(filtered.loc[filtered.stock_type.eq('DELIVERY STOCK'), 'balance_packages'].sum())} packages", "✓", PALETTE["green"], False),
        ("Critical 15+ Days", critical, f"{critical / len(filtered) * 100:.1f}% of records", "!", PALETTE["red"], True),
        ("Balance Packages", _fmt_number(filtered["balance_packages"].sum()), f"{_fmt_number(filtered['balance_charge_weight'].sum())} kg", "▣", PALETTE["cyan"], False),
        ("Stock To-Pay", _fmt_money(filtered["stock_topay"].sum()), "Collection exposure", "₹", PALETTE["brown"], False),
    ]
    columns = st.columns(7, gap="small")
    for column, values in zip(columns, kpis):
        with column:
            st.markdown(_kpi_card(*values), unsafe_allow_html=True)

    current_zone_col, destination_zone_col, load_col = st.columns(3, gap="small")
    with current_zone_col:
        with st.container(border=True):
            _zone_bar(filtered, "zone", "Stock by Current Zone")
    with destination_zone_col:
        with st.container(border=True):
            _zone_bar(filtered, "destination_zone", "Stock by Destination Zone")
    with load_col:
        with st.container(border=True):
            _donut(filtered, "load_type", "PTL / FTL Overview")

    unmapped_mask = (
        filtered["zone"].isna()
        | filtered["zone"].astype(str).str.strip().str.casefold().isin(
            ["", "unmapped", "unknown", "none", "nan"]
        )
    )
    unmapped_rows = filtered.loc[unmapped_mask].copy()
    if not unmapped_rows.empty:
        unmapped_gr = int(unmapped_rows["gr_no"].nunique())
        with st.expander(f"Unmapped Current-Zone Branches — {unmapped_gr:,} GR"):
            unmapped_summary = (
                unmapped_rows[
                    ["gr_no", "branchcode_key", "branch", "origin", "destination"]
                ]
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
            _render_table(
                unmapped_summary,
                height=280,
                key="unmapped_current_zone_branches_grid",
            )

    action_col, branch_col = st.columns(2, gap="small")
    with action_col:
        with st.container(border=True):
            st.markdown('<div class="stock-alert-title">⚠ Action Required</div>', unsafe_allow_html=True)
            action_df = filtered.sort_values(["stock_days", "balance_charge_weight"], ascending=False).copy()
            action_df["Issue"] = action_df["stock_type"].map({"IN-TRANSIT STOCK":"In-transit ageing", "TRANSIT STOCK":"Transit pending", "DELIVERY STOCK":"Delivery pending", "BOOKING STOCK":"Booking pending"}).fillna("Ageing stock")
            display = action_df[["gr_no", "origin", "destination", "branch", "Issue", "stock_days"]].rename(columns={"gr_no":"GR Number","origin":"Origin","destination":"Destination","branch":"Current Location","stock_days":"Ageing"})
            display["Ageing"] = display["Ageing"].map(lambda value: f"{value:.0f} Days")
            _render_table(display, height=300, key="action_required_grid")
    with branch_col:
        with st.container(border=True):
            st.markdown('<div class="stock-panel-title">Branch / Location Pending<span>All branches</span></div>', unsafe_allow_html=True)
            branch_summary = filtered.groupby("branch").agg(Active_GR=("gr_no","nunique"),In_Transit=("stock_type",lambda s:(s=="IN-TRANSIT STOCK").sum()),Transit=("stock_type",lambda s:(s=="TRANSIT STOCK").sum()),Critical_15d=("is_critical","sum"),Avg_Dwell=("stock_days","mean")).sort_values("Active_GR",ascending=False).reset_index()
            branch_summary["Avg_Dwell"] = branch_summary["Avg_Dwell"].map(lambda value:f"{value:.1f} d")
            branch_summary=branch_summary.rename(columns={"branch":"Location","Active_GR":"Active","In_Transit":"In-Transit","Transit":"Transit Stock","Critical_15d":"15d+","Avg_Dwell":"Avg Dwell"})
            _render_table(branch_summary, height=300, key="branch_pending_grid")

    ageing_col, health_col = st.columns(2, gap="small")
    with ageing_col:
        with st.container(border=True):
            age_summary = filtered.groupby("age_band", observed=True)["gr_no"].nunique().reindex(["0-7 Days", "8-14 Days", "15+ Days"], fill_value=0).reset_index(name="GR Count")
            fig = px.bar(age_summary, x="GR Count", y="age_band", orientation="h", color="age_band", color_discrete_map={"0-7 Days":"#48a864","8-14 Days":"#f1bd42","15+ Days":"#df4742"}, text="GR Count")
            fig.update_layout(title=dict(text="Ageing – Stock",font=dict(size=11),x=.01),height=290,margin=dict(l=5,r=28,t=30,b=5),showlegend=False,xaxis=dict(visible=False),yaxis_title=None,paper_bgcolor="white",plot_bgcolor="white",font=dict(size=8))
            fig.update_traces(
                textposition="outside",
                textfont=dict(size=13, color="#20344e"),
                cliponaxis=False,
                hovertemplate="%{y}: %{x:,} GR<extra></extra>",
            )
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    with health_col:
        with st.container(border=True):
            view = st.segmented_control(
                "Distribution period",
                options=["D", "M", "Q", "Y"],
                default="D",
                key="stock_age_distribution_period",
                label_visibility="collapsed",
            )
            trend_source = filtered[["gr_no", "stock_days"]].copy()
            trend_source["stock_days"] = trend_source["stock_days"].fillna(0).clip(lower=0)
            trend_source["Stock Date"] = (
                pd.Timestamp(as_on_date)
                - pd.to_timedelta(trend_source["stock_days"], unit="D")
            )
            if view == "D":
                trend_source["Period Key"] = trend_source["Stock Date"].dt.floor("D")
                trend_source["Period"] = trend_source["Stock Date"].dt.strftime("%d %b %Y")
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
                .nunique().reset_index(name="GR Count").sort_values("Period Key")
            )
            fig=px.bar(trend,x="Period",y="GR Count",text="GR Count",color_discrete_sequence=[PALETTE["blue"]])
            fig.update_traces(
                textposition="outside",cliponaxis=False,
                textfont=dict(size=13, color="#20344e"),
                hovertemplate="%{x}: %{y:,} GR<extra></extra>",
            )
            fig.update_layout(title=dict(text="Stock Date Distribution",font=dict(size=11),x=.01),height=255,margin=dict(l=8,r=8,t=32,b=35),xaxis_title=None,yaxis_title="GR Count",paper_bgcolor="white",plot_bgcolor="white",font=dict(size=9),xaxis=dict(tickangle=-30 if view=="D" else 0))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    with st.container(border=True):
        st.markdown(
            '<div class="stock-panel-title">Exception & Delay Analysis'
            '<span>Action-focused details · not part of KPI</span></div>',
            unsafe_allow_html=True,
        )
        _render_table(
            _operational_insights(filtered),
            height=245,
            key="exception_delay_analysis_grid",
        )

    route_col, detail_col = st.columns(2, gap="small")
    with route_col:
        with st.container(border=True):
            st.markdown('<div class="stock-panel-title">Routes by Active Stock<span>Scrollable</span></div>',unsafe_allow_html=True)
            route_summary=filtered.groupby(["origin","destination"]).agg(Active_GR=("gr_no","nunique"),Critical=("is_critical","sum"),Avg_Age=("stock_days","mean")).sort_values("Active_GR",ascending=False).reset_index()
            route_summary["Route"]=route_summary["origin"]+" → "+route_summary["destination"]
            route_summary["Avg_Age"]=route_summary["Avg_Age"].map(lambda x:f"{x:.1f} d")
            route_display = route_summary[["Route","Active_GR","Critical","Avg_Age"]].rename(columns={"Active_GR":"Active GR","Avg_Age":"Avg Age"})
            _render_table(route_display, height=300, key="routes_grid")
    with detail_col:
        with st.container(border=True):
            st.markdown('<div class="stock-panel-title">Priority Stock Details<span>Filtered result</span></div>',unsafe_allow_html=True)
            details=filtered.sort_values(["stock_days","stock_topay"],ascending=False).copy()
            details["Weight"]=details["balance_charge_weight"].map(lambda x:f"{x:,.0f} kg")
            details["To-Pay"]=details["stock_topay"].map(_fmt_money)
            details["Age"]=details["stock_days"].map(lambda x:f"{x:.0f} d")
            detail_display = details[["gr_no","branch","stock_type","Weight","To-Pay","Age"]].rename(columns={"gr_no":"GR","branch":"Branch","stock_type":"Status"})
            _render_table(detail_display, height=300, key="priority_details_grid")
