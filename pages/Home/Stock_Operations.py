"""Analytics & Trends page for Sugam Dashboard."""

from __future__ import annotations

import html
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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
        [data-testid="stHeader"]{height:1.65rem!important;background:transparent}
        .main .block-container{
            padding:.15rem .85rem .8rem!important;
            max-width:100%!important;
        }
        [data-testid="stVerticalBlock"]{gap:.45rem!important}
        [data-testid="stHorizontalBlock"]{gap:.65rem!important}

        .stock-title{font:800 17px/1.2 Inter,sans-serif;color:#102a49;margin:1px 0 2px}
        .stock-sub{font:500 9px/1.3 Inter,sans-serif;color:#718096;margin:0}

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
            min-height:30px!important;height:30px!important;
            font-size:8px!important;border-radius:6px!important;
        }
        div[data-testid="stButton"] button{
            min-height:30px!important;height:30px!important;
            padding:0 .65rem!important;border-radius:6px!important;
            font-size:9px!important;font-weight:750!important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]{
            border:1px solid #dde3ea!important;border-radius:7px!important;
            box-shadow:0 1px 3px rgba(20,40,65,.04)!important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]>div{
            padding:.55rem .65rem!important;
        }
        .stock-filter-divider{height:1px;background:#edf0f4;margin:1px 0 3px}

        .stock-kpi{
            min-height:76px;display:flex;align-items:flex-start;gap:7px;
            background:#fff;border:1px solid #e1e7ef;border-radius:7px;
            padding:8px;box-shadow:0 1px 3px rgba(20,40,65,.04);
        }
        .stock-kpi-red{border-color:#f4c9cc;background:#fffafa}
        .stock-kpi-icon{
            width:25px;height:25px;min-width:25px;border-radius:6px;
            display:flex;align-items:center;justify-content:center;
            font-size:12px;font-weight:800;
        }
        .stock-kpi-copy{min-width:0}
        .stock-kpi-label{font:700 8px/1.15 Inter,sans-serif;color:#607086}
        .stock-kpi-value{font:800 15px/1.2 Inter,sans-serif;color:#172238;margin-top:3px}
        .stock-kpi-note{
            font:500 7px/1.2 Inter,sans-serif;color:#718096;
            margin-top:3px;white-space:normal;
        }

        .stock-panel-title,.stock-alert-title{
            display:flex;justify-content:space-between;align-items:center;
            font:800 9px/1.2 Inter,sans-serif;color:#20344e;margin:0 0 4px;
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
            width:29px;height:29px;border:2px solid currentColor;border-radius:50%;
            display:flex;align-items:center;justify-content:center;
            background:#fff;font-size:12px;
        }
        .stock-flow-arrow{color:#a0aaba;font-size:15px;font-weight:800}

        div[data-testid="stDataFrame"]{font-size:8px!important}
        div[data-testid="stDataFrame"] [role="columnheader"]{
            font-size:8px!important;font-weight:800!important;
        }
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


def _apply_scope(df):
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


def _kpi_card(label, value, note, icon, tone, critical=False):
    css = " stock-kpi-red" if critical else ""
    return f"""
    <div class="stock-kpi{css}">
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
    fig.update_traces(textinfo="none", hovertemplate="%{label}<br>%{value:,} GR (%{percent})<extra></extra>")
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


def show_stock_operations():
    _inject_css()
    today = date.today()
    month_start = today.replace(day=1)
    title_col, from_col, to_col, as_on_col, run_col = st.columns(
        [2.3, .62, .62, .62, .55], gap="small"
    )
    with title_col:
        st.markdown('<div class="stock-title">Stock Operations Control Tower</div><div class="stock-sub">Branch stock, ageing exposure and operational action queue</div>', unsafe_allow_html=True)
    with from_col:
        start_date = st.date_input(
            "From Date",
            value=month_start,
            max_value=today,
            key="stock_dashboard_from_date",
        )
    with to_col:
        end_date = st.date_input(
            "To Date",
            value=today,
            max_value=today,
            key="stock_dashboard_to_date",
        )
    with as_on_col:
        as_on_date = st.date_input(
            "As-on Date",
            value=end_date,
            max_value=today,
            key="stock_dashboard_as_on_date",
        )
    with run_col:
        st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
        run_report = st.button(
            "Run Report",
            type="primary",
            use_container_width=True,
            key="stock_dashboard_run_report",
        )

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
            stock_df = _apply_scope(
                load_stock_data(
                    start_date=start_date,
                    end_date=end_date,
                    as_on_date=as_on_date,
                )
            )
    except Exception as exc:
        st.error(f"Stock dashboard data could not be loaded: {exc}")
        return
    if stock_df.empty:
        st.warning("No stock data is available for your assigned scope.")
        return

    with st.container(border=True):
        filter_row_1 = st.columns(5, gap="small")
        with filter_row_1[0]:
            origin_zones = st.multiselect("Origin Zone", _safe_options(stock_df, "origin_zone"), placeholder="All")
        origin_zone_df = stock_df[stock_df["origin_zone"].isin(origin_zones)] if origin_zones else stock_df
        with filter_row_1[1]:
            origin_circles = st.multiselect("Origin Circle", _safe_options(origin_zone_df, "origin_circle"), placeholder="All")
        origin_circle_df = origin_zone_df[origin_zone_df["origin_circle"].isin(origin_circles)] if origin_circles else origin_zone_df
        with filter_row_1[2]:
            branches = st.multiselect("Branch / Location", _safe_options(origin_circle_df, "branch"), placeholder="All")
        branch_df = origin_circle_df[origin_circle_df["branch"].isin(branches)] if branches else origin_circle_df
        with filter_row_1[3]:
            stock_types = st.multiselect("Stock Type", _safe_options(branch_df, "stock_type"), placeholder="All")
        type_df = branch_df[branch_df["stock_type"].isin(stock_types)] if stock_types else branch_df
        with filter_row_1[4]:
            load_types = st.multiselect("PTL / FTL", _safe_options(type_df, "load_type"), placeholder="All")
        load_df = type_df[type_df["load_type"].isin(load_types)] if load_types else type_df

        st.markdown('<div class="stock-filter-divider"></div>', unsafe_allow_html=True)
        filter_row_2 = st.columns([1, 1, 1, 1, 1.15], gap="small")
        with filter_row_2[0]:
            destination_zones = st.multiselect("Destination Zone", _safe_options(load_df, "destination_zone"), placeholder="All")
        destination_zone_df = load_df[load_df["destination_zone"].isin(destination_zones)] if destination_zones else load_df
        with filter_row_2[1]:
            destination_circles = st.multiselect("Destination Circle", _safe_options(destination_zone_df, "destination_circle"), placeholder="All")
        destination_circle_df = destination_zone_df[destination_zone_df["destination_circle"].isin(destination_circles)] if destination_circles else destination_zone_df
        with filter_row_2[2]:
            origins = st.multiselect("Origin", _safe_options(destination_circle_df, "origin"), placeholder="All")
        origin_df = destination_circle_df[destination_circle_df["origin"].isin(origins)] if origins else destination_circle_df
        with filter_row_2[3]:
            destinations = st.multiselect("Destination", _safe_options(origin_df, "destination"), placeholder="All")
        filtered = origin_df[origin_df["destination"].isin(destinations)] if destinations else origin_df
        with filter_row_2[4]:
            search = st.text_input("Search GR / Party", placeholder="GR, origin, destination, party")
        if search:
            needle = search.casefold()
            mask = pd.Series(False, index=filtered.index)
            for column in ["gr_no", "branch", "origin", "destination", "consignor", "consignee"]:
                mask |= filtered[column].astype(str).str.casefold().str.contains(needle, regex=False, na=False)
            filtered = filtered[mask]

    if filtered.empty:
        st.warning("No records match the selected filters.")
        return

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

    flow_col, zone_col, load_col = st.columns([1.8, .9, .9], gap="small")
    with flow_col:
        with st.container(border=True):
            st.markdown(f'<div class="stock-panel-title">Stock Flow (Current Snapshot)<span>{filtered.gr_no.nunique():,} active GR</span></div>', unsafe_allow_html=True)
            _stock_flow(filtered)
    with zone_col:
        with st.container(border=True):
            _donut(filtered, "destination_zone", "Stock by Destination Zone")
    with load_col:
        with st.container(border=True):
            _donut(filtered, "load_type", "PTL / FTL Overview")

    action_col, ageing_col, branch_col = st.columns([1.5, .8, 1.1], gap="small")
    with action_col:
        with st.container(border=True):
            st.markdown('<div class="stock-alert-title">⚠ Action Required</div>', unsafe_allow_html=True)
            action_df = filtered.sort_values(["stock_days", "balance_charge_weight"], ascending=False).head(7).copy()
            action_df["Issue"] = action_df["stock_type"].map({"IN-TRANSIT STOCK":"In-transit ageing", "TRANSIT STOCK":"Transit pending", "DELIVERY STOCK":"Delivery pending", "BOOKING STOCK":"Booking pending"}).fillna("Ageing stock")
            display = action_df[["gr_no", "origin", "destination", "branch", "Issue", "stock_days"]].rename(columns={"gr_no":"GR Number","origin":"Origin","destination":"Destination","branch":"Current Location","stock_days":"Ageing"})
            display["Ageing"] = display["Ageing"].map(lambda value: f"{value:.0f} Days")
            st.dataframe(display, hide_index=True, use_container_width=True, height=225)
            st.markdown('<div class="stock-view-all">Priority based on highest stock days and weight</div>', unsafe_allow_html=True)
    with ageing_col:
        with st.container(border=True):
            age_summary = filtered.groupby("age_band", observed=True)["gr_no"].nunique().reindex(["0-7 Days", "8-14 Days", "15+ Days"], fill_value=0).reset_index(name="GR Count")
            fig = px.bar(age_summary, x="GR Count", y="age_band", orientation="h", color="age_band", color_discrete_map={"0-7 Days":"#48a864","8-14 Days":"#f1bd42","15+ Days":"#df4742"}, text="GR Count")
            fig.update_layout(title=dict(text="Ageing – Stock",font=dict(size=11),x=.01),height=260,margin=dict(l=5,r=8,t=30,b=5),showlegend=False,xaxis=dict(visible=False),yaxis_title=None,paper_bgcolor="white",plot_bgcolor="white",font=dict(size=8))
            fig.update_traces(textposition="outside", hovertemplate="%{y}: %{x:,} GR<extra></extra>")
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    with branch_col:
        with st.container(border=True):
            st.markdown('<div class="stock-panel-title">Branch / Location Pending<span>Top 7</span></div>', unsafe_allow_html=True)
            branch_summary = filtered.groupby("branch").agg(Active_GR=("gr_no","nunique"),In_Transit=("stock_type",lambda s:(s=="IN-TRANSIT STOCK").sum()),Transit=("stock_type",lambda s:(s=="TRANSIT STOCK").sum()),Critical_15d=("is_critical","sum"),Avg_Dwell=("stock_days","mean")).sort_values("Active_GR",ascending=False).head(7).reset_index()
            branch_summary["Avg_Dwell"] = branch_summary["Avg_Dwell"].map(lambda value:f"{value:.1f} d")
            branch_summary=branch_summary.rename(columns={"branch":"Location","Active_GR":"Active","In_Transit":"In-Transit","Transit":"Transit Stock","Critical_15d":"15d+","Avg_Dwell":"Avg Dwell"})
            st.dataframe(branch_summary,hide_index=True,use_container_width=True,height=255)

    route_col, health_col, detail_col = st.columns([.9, 1.05, 1.35], gap="small")
    with route_col:
        with st.container(border=True):
            st.markdown('<div class="stock-panel-title">Top Routes by Active Stock<span>Top 5</span></div>',unsafe_allow_html=True)
            route_summary=filtered.groupby(["origin","destination"]).agg(Active_GR=("gr_no","nunique"),Critical=("is_critical","sum"),Avg_Age=("stock_days","mean")).sort_values("Active_GR",ascending=False).head(5).reset_index()
            route_summary["Route"]=route_summary["origin"]+" → "+route_summary["destination"]
            route_summary["Avg_Age"]=route_summary["Avg_Age"].map(lambda x:f"{x:.1f} d")
            st.dataframe(route_summary[["Route","Active_GR","Critical","Avg_Age"]].rename(columns={"Active_GR":"Active GR","Avg_Age":"Avg Age"}),hide_index=True,use_container_width=True,height=205)
    with health_col:
        with st.container(border=True):
            trend=filtered.groupby("stock_days")["gr_no"].nunique().reset_index(name="GR Count").sort_values("stock_days")
            fig=px.bar(trend,x="stock_days",y="GR Count",color_discrete_sequence=[PALETTE["blue"]])
            fig.update_layout(title=dict(text="Stock Age Distribution",font=dict(size=11),x=.01),height=210,margin=dict(l=8,r=8,t=30,b=25),xaxis_title="Stock Days",yaxis_title=None,paper_bgcolor="white",plot_bgcolor="white",font=dict(size=8))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    with detail_col:
        with st.container(border=True):
            st.markdown('<div class="stock-panel-title">Priority Stock Details<span>Filtered result</span></div>',unsafe_allow_html=True)
            details=filtered.sort_values(["stock_days","stock_topay"],ascending=False).head(6).copy()
            details["Weight"]=details["balance_charge_weight"].map(lambda x:f"{x:,.0f} kg")
            details["To-Pay"]=details["stock_topay"].map(_fmt_money)
            details["Age"]=details["stock_days"].map(lambda x:f"{x:.0f} d")
            st.dataframe(details[["gr_no","branch","stock_type","Weight","To-Pay","Age"]].rename(columns={"gr_no":"GR","branch":"Branch","stock_type":"Status"}),hide_index=True,use_container_width=True,height=205)

    summary_items = [
        ("Booking Stock", type_counts["BOOKING STOCK"], ""),
        ("In-Transit", type_counts["IN-TRANSIT STOCK"], ""),
        ("Transit Stock", type_counts["TRANSIT STOCK"], ""),
        ("Delivery Stock", type_counts["DELIVERY STOCK"], ""),
        ("Critical 15+ Days", critical, "stock-critical"),
        ("Balance Packages", _fmt_number(filtered["balance_packages"].sum()), ""),
        ("Stock To-Pay", _fmt_money(filtered["stock_topay"].sum()), "stock-orange"),
    ]
    summary_html="".join(f'<span>{html.escape(str(label))}<strong class="{css}">{html.escape(str(value))}</strong></span>' for label,value,css in summary_items)
    st.markdown(f'<div class="stock-summary">{summary_html}</div>',unsafe_allow_html=True)
    st.markdown('<div class="stock-note"><b>Stock definition:</b> The dashboard uses the four exact values returned by the ERP stored procedure: Booking Stock, In-Transit Stock, Transit Stock and Delivery Stock. “Hub Stock” is intentionally not inferred until the operational rule is confirmed.</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="stock-footer">Live source: dbo.greentransweb_branchstock_v5_sugam · Period {start_date:%d %b %Y} to {end_date:%d %b %Y} · As on {as_on_date:%d %b %Y}</div>',unsafe_allow_html=True)
