"""Operational control-tower dashboard for branch stock."""

from __future__ import annotations

import html
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.stock_data_loader import load_stock_data


PALETTE = {
    "blue": "#2f73d8", "orange": "#ed8b25", "cyan": "#1e91a0",
    "purple": "#7953c6", "green": "#269b54", "red": "#d63f48",
    "brown": "#8a613d", "navy": "#0b3158", "text": "#172238",
}
STOCK_ORDER = ["BOOKING STOCK", "IN-TRANSIT STOCK", "TRANSIT STOCK", "DELIVERY STOCK"]


def _inject_css():
    st.markdown(
        """
        <style>
        .main .block-container{padding:4px 10px 14px!important;max-width:100%!important}
        .stock-title{font:800 18px Inter,sans-serif;color:#102a49;margin:0}.stock-sub{font:500 9px Inter,sans-serif;color:#718096;margin-top:2px}
        .stock-note{padding:7px 10px;border:1px solid #d8e1ec;background:#f8fbff;border-radius:7px;color:#40536b;font-size:9px;margin-bottom:6px}
        div[data-testid="stVerticalBlockBorderWrapper"]{border-color:#dde3ea!important;border-radius:5px!important;box-shadow:0 1px 4px rgba(20,40,65,.05)!important}
        .stock-kpi{height:72px;padding:8px;display:flex;gap:7px;align-items:center;background:#fff;border:1px solid #dde3ea;box-shadow:0 1px 4px rgba(20,40,65,.06)}
        .stock-kpi-icon{width:33px;height:33px;border-radius:50%;display:grid;place-items:center;font-size:15px;flex:none}.stock-kpi-copy{min-width:0}.stock-kpi-label{font-size:8px;font-weight:750;color:#26354a;white-space:nowrap}.stock-kpi-value{font-size:17px;line-height:1.05;font-weight:800;color:#172238;margin:2px 0}.stock-kpi-note{font-size:7px;color:#6d798b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.stock-kpi-red .stock-kpi-value{color:#ce343e}
        .stock-panel-title{display:flex;align-items:center;justify-content:space-between;font-size:11px;font-weight:800;color:#1a283b;margin-bottom:4px}.stock-panel-title span{font-size:8px;color:#788496;font-weight:500}
        .stock-flow{display:flex;align-items:center;justify-content:space-around;padding:9px 3px 5px}.stock-flow-step{text-align:center;position:relative;min-width:75px}.stock-flow-dot{width:39px;height:39px;border-radius:50%;display:grid;place-items:center;margin:auto;border:1px solid currentColor;background:#fff;font-size:16px}.stock-flow-step b{display:block;font-size:8px;margin-top:3px}.stock-flow-step strong{font-size:12px}.stock-flow-arrow{color:#8290a3;font-size:15px}
        .stock-alert-title{font-size:10px;font-weight:800;color:#bf323a;text-transform:uppercase}.stock-view-all{text-align:center;color:#1c5fa8;font-size:8px;font-weight:700;padding-top:3px}.stock-summary{display:grid;grid-template-columns:repeat(7,1fr);background:#fff;border:1px solid #dde3ea;padding:9px}.stock-summary span{text-align:center;border-right:1px dashed #d6dce4;font-size:8px}.stock-summary span:last-child{border:0}.stock-summary strong{display:block;font-size:14px;margin-top:4px}.stock-critical{color:#ce343e!important}.stock-orange{color:#d97918!important}
        div[data-testid="stDataFrame"]{font-size:8px!important}div[data-testid="stDataFrame"] [role="columnheader"]{font-size:8px!important;font-weight:800!important}
        div[data-testid="stSelectbox"] label,div[data-testid="stMultiSelect"] label,div[data-testid="stTextInput"] label,div[data-testid="stDateInput"] label{font-size:8px!important;font-weight:750!important;margin-bottom:1px!important}div[data-baseweb="select"]>div,div[data-testid="stTextInput"] input,div[data-testid="stDateInput"] input{min-height:29px!important;height:29px!important;font-size:8px!important}
        div[data-testid="stDateInput"]{margin-bottom:0!important}.stock-filter-divider{height:1px;background:#edf0f4;margin:2px 0 6px}
        .stPlotlyChart{margin-top:-6px}.stock-footer{text-align:center;color:#718096;font-size:8px;padding-top:6px}
        @media(max-width:900px){.stock-summary{grid-template-columns:repeat(2,1fr);gap:8px}.stock-summary span{border:0}.stock-flow{min-width:500px}.stock-flow-wrap{overflow-x:auto}}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
    title_col, from_col, to_col, as_on_col = st.columns([2.5, .62, .62, .62], gap="small")
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
