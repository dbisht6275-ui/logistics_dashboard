import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from services.data_loader import load_booking_data, get_date_range
from services.branch_agency_mast import load_stationmast_data

# =========================
# Compact dashboard styling
# =========================

st.markdown("""
<style>

/* Reduce dataframe row height */
[data-testid="stDataFrame"] table {
    font-size: 11px;
}

[data-testid="stDataFrame"] tbody tr {
    height: 24px !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Reduce Streamlit default spacing */
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

/* Compact markdown headings inside cards */
h5, h6 {
    margin-top: 0rem !important;
    margin-bottom: 0.35rem !important;
}

/* Compact segmented control */
div[data-testid="stSegmentedControl"] {
    display: flex;
    justify-content: flex-end;
}

div[data-testid="stSegmentedControl"] label {
    padding: 4px 10px !important;
    font-size: 12px !important;
}

/* Reduce dataframe/table vertical spacing */
div[data-testid="stDataFrame"] {
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)


def format_cr(v):
    return f"{v / 10000000:.2f} Cr"


# =========================
# Auto growth-vs-LY helpers
# =========================

def get_previous_fy(fy):
    """Given '2025-2026' returns '2024-2025'."""
    start_year, end_year = map(int, fy.split("-"))
    return f"{start_year - 1}-{end_year - 1}"


def calculate_kpis(data):
    """Compute the same set of KPIs used on the dashboard for any dataframe."""
    if data is None or data.empty:
        return {
            "revenue": 0, "ftl": 0, "ltl": 0, "total_gr": 0,
            "aweight": 0, "topay": 0, "paid": 0, "tbb": 0
        }

    return {
        "revenue": data["REVENUE"].sum(),
        "ftl": data[data["LOADTYPE"] == "FTL"]["REVENUE"].sum(),
        "ltl": data[data["LOADTYPE"] == "LTL"]["REVENUE"].sum(),
        "total_gr": data["grno"].count(),
        "aweight": data["aweight"].sum() / 1000,
        "topay": data[data["GRTYPE"] == "TOPAY"]["REVENUE"].sum(),
        "paid": data[data["GRTYPE"] == "PAID"]["REVENUE"].sum(),
        "tbb": data[data["GRTYPE"] == "TBB"]["REVENUE"].sum(),
    }


def pct_growth(current, previous):
    """% change of current vs previous, safe against zero/NaN previous."""
    if previous in (0, None) or pd.isna(previous):
        return 0.0
    return ((current - previous) / previous) * 100


def growth_label(value):
    arrow = "▲" if value >= 0 else "▼"
    return f"{arrow} {abs(value):.1f}%"


MONTH_ORDER = [
    "Apr", "May", "Jun", "Jul",
    "Aug", "Sep", "Oct", "Nov",
    "Dec", "Jan", "Feb", "Mar"
]

QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]

QUARTER_MAP = {
    1: "Q1", 2: "Q1", 3: "Q1",
    4: "Q2", 5: "Q2", 6: "Q2",
    7: "Q3", 8: "Q3", 9: "Q3",
    10: "Q4", 11: "Q4", 12: "Q4",
}


def build_yoy_trend(current_df, previous_df, trend_type, date_col, fy_start, prev_fy_start, month_map):
    """
    Build a Period-wise Current-FY vs LY revenue comparison dataframe for a chosen granularity.
    trend_type: 'Daily' | 'Weekly' | 'Monthly' | 'Quarterly'
    Returns columns: Period, Revenue Cr, Prev Revenue Cr, Growth %, Growth Label
    """
    cur = current_df.copy()
    prev = previous_df.copy() if previous_df is not None and not previous_df.empty else pd.DataFrame()

    cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty and date_col in prev.columns:
        prev[date_col] = pd.to_datetime(prev[date_col], errors="coerce")

    fy_start_ts = pd.to_datetime(fy_start) if fy_start else None
    prev_fy_start_ts = pd.to_datetime(prev_fy_start) if prev_fy_start else None

    if trend_type == "Daily":
        trend_df = cur.groupby(cur[date_col].dt.date)["REVENUE"].sum().reset_index()
        trend_df.columns = ["Period", "REVENUE"]
        trend_df["Key"] = (
            (pd.to_datetime(trend_df["Period"]) - fy_start_ts).dt.days
            if fy_start_ts is not None else range(len(trend_df))
        )

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.date)["REVENUE"].sum().reset_index()
            prev_trend.columns = ["Period", "PREV_REVENUE"]
            prev_trend["Key"] = (pd.to_datetime(prev_trend["Period"]) - prev_fy_start_ts).dt.days
        else:
            prev_trend = pd.DataFrame(columns=["Period", "PREV_REVENUE", "Key"])

    elif trend_type == "Weekly":
        trend_df = cur.groupby(cur[date_col].dt.to_period("W"))["REVENUE"].sum().reset_index()
        trend_df["Period"] = trend_df[date_col].astype(str)
        trend_df["Key"] = (
            ((trend_df[date_col].dt.start_time - fy_start_ts).dt.days // 7)
            if fy_start_ts is not None else range(len(trend_df))
        )
        trend_df = trend_df.drop(columns=[date_col])

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.to_period("W"))["REVENUE"].sum().reset_index()
            prev_trend["Key"] = (prev_trend[date_col].dt.start_time - prev_fy_start_ts).dt.days // 7
            prev_trend = prev_trend.rename(columns={"REVENUE": "PREV_REVENUE"}).drop(columns=[date_col])
        else:
            prev_trend = pd.DataFrame(columns=["PREV_REVENUE", "Key"])

    elif trend_type == "Quarterly":
        cur["Quarter"] = cur["FIN_MONTH"].map(QUARTER_MAP)
        trend_df = cur.groupby("Quarter")["REVENUE"].sum().reset_index()
        trend_df["Quarter"] = pd.Categorical(trend_df["Quarter"], categories=QUARTER_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Quarter")
        trend_df.columns = ["Period", "REVENUE"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Quarter"] = prev["FIN_MONTH"].map(QUARTER_MAP)
            prev_trend = prev.groupby("Quarter")["REVENUE"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_REVENUE"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_REVENUE"])

    else:  # Monthly
        cur["Month"] = cur["FIN_MONTH"].map(month_map)
        trend_df = cur.groupby("Month")["REVENUE"].sum().reset_index()
        trend_df["Month"] = pd.Categorical(trend_df["Month"], categories=MONTH_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Month")
        trend_df.columns = ["Period", "REVENUE"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Month"] = prev["FIN_MONTH"].map(month_map)
            prev_trend = prev.groupby("Month")["REVENUE"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_REVENUE"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_REVENUE"])

    trend_df["Revenue Cr"] = (trend_df["REVENUE"] / 10000000).round(2)

    if not prev_trend.empty:
        prev_trend["Prev Revenue Cr"] = (prev_trend["PREV_REVENUE"] / 10000000).round(2)
        trend_df = trend_df.merge(prev_trend[["Key", "Prev Revenue Cr"]], on="Key", how="left")
    else:
        trend_df["Prev Revenue Cr"] = None

    trend_df["Growth %"] = trend_df.apply(
        lambda r: pct_growth(r["Revenue Cr"], r["Prev Revenue Cr"]) if pd.notna(r["Prev Revenue Cr"]) else None,
        axis=1
    )
    trend_df["Growth Label"] = trend_df["Growth %"].apply(lambda x: growth_label(x) if pd.notna(x) else "N/A")

    return trend_df


def create_card(title, value, color, icon, growth_value=0.0):
    """Compact KPI card used in the top KPI row. growth_value is auto-calculated % vs LY."""
    growth_color = "#166534" if growth_value >= 0 else "#dc2626"
    growth_text = growth_label(growth_value)

    html = f"""<div style="background:#ffffff;padding:8px;border-radius:10px;border:1px solid #e5e7eb;box-shadow:0 3px 10px rgba(0,0,0,0.08);min-height:70px;">
<div style="display:flex;justify-content:space-between;align-items:center;">
<div style="color:{color};font-size:10px;font-weight:800;">{title}</div>
<div style="font-size:16px;">{icon}</div>
</div>
<div style="font-size:15px;font-weight:900;color:#0f172a;margin-top:1px;">{value}</div>
<div style="font-size:10px;color:{growth_color};font-weight:700;margin-top:1px;">{growth_text} vs LY</div>

</div>"""
    st.markdown(html, unsafe_allow_html=True)


def mini_rank_card(rank, name, value, max_value, color):
    """Compact ranking row for top/bottom branch lists."""
    pct = min((value / max_value * 100), 100) if max_value else 0

    html = f"""<div style="margin-bottom:6px;">
<div style="display:flex;align-items:center;gap:6px;">
<div style="background:#f1f5f9;border-radius:4px;padding:2px 6px;font-size:10px;color:#64748b;">{rank}</div>
<div style="font-size:10px;font-weight:800;color:#0f2747;min-width:95px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
<div style="flex:1;height:5px;background:#e5e7eb;border-radius:20px;overflow:hidden;">
<div style="width:{pct}%;height:5px;background:{color};border-radius:20px;"></div>
</div>
<div style="font-size:10px;font-weight:800;color:#0f2747;min-width:45px;text-align:right;">₹{value:.2f}</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def show_overview():
    """Compact overview dashboard page."""

    header_left, header_right = st.columns([8, 1])

    with header_left:
        st.markdown("""
        <h3 style='margin:0;padding:0;'>Revenue Overview</h3>
        <p style='margin:0;color:#64748b;font-size:12px;'>
         Performance Dashboard
        </p>
        """, unsafe_allow_html=True)

  
    # Top filter row: view type, FY, zone, circle, branch, quarter, month and load type
    (
        filter_col1, filter_col2, filter_col3, filter_col4,
        filter_col5, filter_col6, filter_col7, filter_col8
    ) = st.columns(8)

    with filter_col1:
        view_type = st.selectbox("View Type", ["Origin", "Destination"])

    with filter_col2:
        fy = st.selectbox(
            "Financial Year",
            [
                "Select FY",
                "2026-2027",
                "2025-2026",
                "2024-2025",
                "2023-2024",
                "2022-2023",
                "2021-2022",
                "2020-2021",
            ],
        )

    if fy == "Select FY":
        st.info("Please select financial year")
        return

    start_date, end_date = get_date_range(fy)

    # Load booking and branch network data for selected FY
    with st.spinner("Loading data..."):
        df = load_booking_data(start_date, end_date, view_type.lower())
    station_df = load_stationmast_data(start_date, end_date)

    opened_df = station_df[station_df["STATUS"] == "OPENED"]
    closed_df = station_df[station_df["STATUS"] == "CLOSED"]

    opened_branches = len(opened_df)
    closed_branches = len(closed_df)
    net_increase = opened_branches - closed_branches

    if df.empty:
        st.warning("No data found")
        return

    month_map = {
        1: "Apr", 2: "May", 3: "Jun", 4: "Jul",
        5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov",
        9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"
    }

    df["Month"] = df["FIN_MONTH"].map(month_map)
    # NEW: Quarter column derived from FIN_MONTH, used for the Quarter filter below
    df["Quarter"] = df["FIN_MONTH"].map(QUARTER_MAP)

    # Data-scope restriction for this employee (set at login, from config/data_scope.json)
    # e.g. {} = no restriction, {"zone": "Nepal Zone"}, {"circle": "NCR Circle"}, {"branch": "Noida"}
    # Data-scope restriction for this employee
    data_scope = st.session_state.get("data_scope", {})

    # -----------------------------
    # Auto derive parent hierarchy
    # -----------------------------
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    # If branch right is given, derive its circle and zone
    if locked_branch:
        branch_row = df[df["branch"] == locked_branch]
        if not branch_row.empty:
            locked_circle = branch_row["circle"].iloc[0]
            locked_zone = branch_row["zone"].iloc[0]

    # If circle right is given, derive its zone
    elif locked_circle:
        circle_row = df[df["circle"] == locked_circle]
        if not circle_row.empty:
            locked_zone = circle_row["zone"].iloc[0]


    with filter_col3:
        if locked_zone:
            zone = locked_zone
            st.selectbox("Zone", [zone], disabled=True, help="Locked as per your assigned rights")
        else:
            zone = st.selectbox("Zone", ["All"] + sorted(df["zone"].dropna().unique().tolist()))

    if zone != "All":
        df = df[df["zone"] == zone]


    with filter_col4:
        if locked_circle:
            circle = locked_circle
            st.selectbox("Circle", [circle], disabled=True, help="Locked as per your assigned rights")
        else:
            circle = st.selectbox("Circle", ["All"] + sorted(df["circle"].dropna().unique().tolist()))

    if circle != "All":
        df = df[df["circle"] == circle]


    with filter_col5:
        if locked_branch:
            branch = locked_branch
            st.selectbox("Branch", [branch], disabled=True, help="Locked as per your assigned rights")
        else:
            branch = st.selectbox("Branch", ["All"] + sorted(df["branch"].dropna().unique().tolist()))

    if branch != "All":
        df = df[df["branch"] == branch]

    with filter_col6:
        # NEW: Quarter filter — options always shown in Q1→Q4 order (QUARTER_ORDER),
        # restricted to quarters actually present in the currently filtered data.
        available_quarters = [q for q in QUARTER_ORDER if q in df["Quarter"].dropna().unique().tolist()]
        quarter = st.selectbox("Quarter", ["All"] + available_quarters)

    if quarter != "All":
        df = df[df["Quarter"] == quarter]

    with filter_col7:
        # FIX: Month options now follow financial-year order (Apr..Mar) via MONTH_ORDER,
        # instead of plain alphabetical sort() which broke the sequence.
        available_months = [m for m in MONTH_ORDER if m in df["Month"].dropna().unique().tolist()]
        month = st.selectbox("Month", ["All"] + available_months)

    if month != "All":
        df = df[df["Month"] == month]

    with filter_col8:
        loadtype = st.selectbox("Load Type", ["All"] + sorted(df["LOADTYPE"].dropna().unique().tolist()))

    if loadtype != "All":
        df = df[df["LOADTYPE"] == loadtype]

    if df.empty:
        st.warning("No data found for selected filters")
        return

    # =========================
    # Load previous FY data (same filters) for automatic LY growth %
    # =========================
    prev_fy = get_previous_fy(fy)
    prev_df = pd.DataFrame()
    prev_start, prev_end = None, None

    try:
        prev_start, prev_end = get_date_range(prev_fy)
        with st.spinner("Loading last year data..."):
            prev_df = load_booking_data(prev_start, prev_end, view_type.lower())

        if not prev_df.empty:
            prev_df["Month"] = prev_df["FIN_MONTH"].map(month_map)
            # NEW: Quarter column on previous-year data too, so the Quarter filter
            # also applies correctly to the LY comparison numbers.
            prev_df["Quarter"] = prev_df["FIN_MONTH"].map(QUARTER_MAP)

            if zone != "All":
                prev_df = prev_df[prev_df["zone"] == zone]
            if circle != "All":
                prev_df = prev_df[prev_df["circle"] == circle]
            if branch != "All":
                prev_df = prev_df[prev_df["branch"] == branch]
            if quarter != "All":
                prev_df = prev_df[prev_df["Quarter"] == quarter]
            if month != "All":
                prev_df = prev_df[prev_df["Month"] == month]
            if loadtype != "All":
                prev_df = prev_df[prev_df["LOADTYPE"] == loadtype]
    except Exception:
        prev_df = pd.DataFrame()

    prev_kpis = calculate_kpis(prev_df)

    # KPI calculations after all selected filters are applied
    current_kpis = calculate_kpis(df)

    revenue = current_kpis["revenue"]
    ftl = current_kpis["ftl"]
    ltl = current_kpis["ltl"]
    total_gr = current_kpis["total_gr"]
    aweight = round(current_kpis["aweight"], 1)
    topay = current_kpis["topay"]
    paid = current_kpis["paid"]
    tbb = current_kpis["tbb"]

    # Auto-calculated growth % vs Last Year for each KPI
    revenue_growth = pct_growth(revenue, prev_kpis["revenue"])
    ftl_growth = pct_growth(ftl, prev_kpis["ftl"])
    ltl_growth = pct_growth(ltl, prev_kpis["ltl"])
    gr_growth = pct_growth(total_gr, prev_kpis["total_gr"])
    weight_growth = pct_growth(aweight, prev_kpis["aweight"])
    topay_growth = pct_growth(topay, prev_kpis["topay"])
    paid_growth = pct_growth(paid, prev_kpis["paid"])
    tbb_growth = pct_growth(tbb, prev_kpis["tbb"])

    # KPI Cards
    k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8)

    with k1:
        create_card("Revenue", format_cr(revenue), "#2563eb", "💰", revenue_growth)

    with k2:
        create_card("FTL Revenue", format_cr(ftl), "#2563eb", "🚛", ftl_growth)

    with k3:
        create_card("LTL Revenue", format_cr(ltl), "#f97316", "🚚", ltl_growth)

    with k4:
        create_card("Total GR", f"{total_gr:,}", "#7c3aed", "📦", gr_growth)

    with k5:
        create_card("Total Weight (MT)", f"{aweight:,.0f}", "#0f766e", "⚓", weight_growth)

    with k6:
        create_card("Topay Revenue", format_cr(topay), "#7c3aed", "🧾", topay_growth)

    with k7:
        create_card("Paid Revenue", format_cr(paid), "#06b6d4", "🔗", paid_growth)

    with k8:
        create_card("T.B.B Revenue", format_cr(tbb), "#ef4444", "🚚", tbb_growth)

    # Small separator before charts
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Monthly revenue data used for monthly trend and MoM growth
    monthly = (
        df.groupby("Month")["REVENUE"]
        .sum()
        .reset_index()
    )

    monthly["Revenue Cr"] = (monthly["REVENUE"] / 10000000).round(2)

    month_order = [
        "Apr", "May", "Jun", "Jul",
        "Aug", "Sep", "Oct", "Nov",
        "Dec", "Jan", "Feb", "Mar"
    ]

    monthly["Month"] = pd.Categorical(
        monthly["Month"],
        categories=month_order,
        ordered=True
    )

    monthly = monthly.sort_values("Month")

    ftl_pct = (ftl / revenue * 100) if revenue else 0
    ltl_pct = (ltl / revenue * 100) if revenue else 0

    # Revenue trend and load type charts
    row1, row2 = st.columns([1.4, 0.40])

    with row1:
        with st.container(border=True):

            title_col, filter_col = st.columns([2, 2])

            with title_col:
                st.markdown("###### Revenue Trend — Current FY vs LY")

            with filter_col:
                trend_type = st.segmented_control(
                    "",
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    default="Monthly",
                    label_visibility="collapsed"
                )

            yoy_df = build_yoy_trend(
                df,
                prev_df,
                trend_type,
                "grdt",
                start_date,
                prev_start,
                month_map
            )

            fig_yoy = go.Figure()

            # Last Year
            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Prev Revenue Cr"],
                    name=f"LY ({prev_fy})",
                    marker_color="#cbd5e1",
                    text=yoy_df["Prev Revenue Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside"
                )
            )

            # Current FY
            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Revenue Cr"],
                    name=f"Current ({fy})",
                    marker_color="#2563eb",
                    text=yoy_df["Revenue Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside"
                )
            )

            # Growth labels
            ymax = pd.concat(
                [yoy_df["Revenue Cr"], yoy_df["Prev Revenue Cr"]]
            ).max()

            ymax = ymax if ymax > 0 else 1

            if len(yoy_df) <= 40:
                for _, r in yoy_df.iterrows():

                    if r["Growth Label"] != "N/A":

                        color = "#16a34a" if r["Growth %"] >= 0 else "#dc2626"

                        top = max(
                            r["Revenue Cr"] if pd.notna(r["Revenue Cr"]) else 0,
                            r["Prev Revenue Cr"] if pd.notna(r["Prev Revenue Cr"]) else 0,
                        )

                        fig_yoy.add_annotation(
                            x=r["Period"],
                            y=top + ymax * 0.18,
                            text=r["Growth Label"],
                            showarrow=False,
                            font=dict(
                                size=10,
                                color=color,
                                family="Arial Black"
                            )
                        )

            fig_yoy.update_layout(
                barmode="group",
                height=220,
                margin=dict(l=2, r=2, t=35, b=0),
                xaxis_title="",
                yaxis_title="Revenue (Cr)",
                plot_bgcolor="white",
                paper_bgcolor="white",
                legend=dict(
                    orientation="h",
                    y=1.05,
                    x=0
                ),
                yaxis_range=[0, ymax * 1.50]
            )

            fig_yoy.update_xaxes(showgrid=False)
            fig_yoy.update_yaxes(showgrid=False)

            st.plotly_chart(fig_yoy, use_container_width=True)

    with row2:
        with st.container(border=True):
            st.markdown("###### Revenue by Load Type")

            # Donut chart for FTL/LTL revenue share
            fig_load = go.Figure(
                data=[
                    go.Pie(
                        labels=["FTL", "LTL"],
                        values=[ftl, ltl],
                        hole=0.65,
                        textinfo="percent",
                    )
                ]
            )

            fig_load.update_layout(
                annotations=[
                    dict(
                        text=f"₹{(ftl + ltl)/10000000:.2f} Cr<br>Total",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(size=11)
                    )
                ],
                height=220,
                margin=dict(l=0, r=0, t=5, b=0)
            )

            st.plotly_chart(fig_load, use_container_width=True)
    

    # # =========================
    # # Clear YoY Revenue Trend — Current FY vs LY, grouped bars + growth % labels
    # # =========================
    # with st.container(border=True):
    #     bar_title_col, bar_filter_col = st.columns([2, 2])

    #     with bar_title_col:
    #         st.markdown("###### Revenue Trend — Current FY vs LY")

    #     with bar_filter_col:
    #         bar_trend_type = st.segmented_control(
    #             "",
    #             ["Daily", "Weekly", "Monthly", "Quarterly"],
    #             default="Monthly",
    #             label_visibility="collapsed",
    #             key="bar_trend_type"
    #         )

    #     yoy_df = build_yoy_trend(
    #         df, prev_df, bar_trend_type, "grdt", start_date, prev_start, month_map
    #     )

    #     fig_yoy = go.Figure()

    #     fig_yoy.add_trace(
    #         go.Bar(
    #             x=yoy_df["Period"],
    #             y=yoy_df["Prev Revenue Cr"],
    #             name=f"LY ({prev_fy})",
    #             marker_color="#cbd5e1",
    #             text=yoy_df["Prev Revenue Cr"],
    #             texttemplate="%{text:.2f}",
    #             textposition="outside",
    #             textfont=dict(size=9, color="#64748b")
    #         )
    #     )

    #     fig_yoy.add_trace(
    #         go.Bar(
    #             x=yoy_df["Period"],
    #             y=yoy_df["Revenue Cr"],
    #             name=f"Current ({fy})",
    #             marker_color="#2563eb",
    #             text=yoy_df["Revenue Cr"],
    #             texttemplate="%{text:.2f}",
    #             textposition="outside",
    #             textfont=dict(size=9, color="#2563eb")
    #         )
    #     )

    #     # Growth % annotated above each period's pair of bars
    #     yoy_max = pd.concat([yoy_df["Revenue Cr"], yoy_df["Prev Revenue Cr"]]).max()
    #     yoy_max = yoy_max if pd.notna(yoy_max) and yoy_max > 0 else 1

    #     # Skip annotation clutter when there are too many bars (Daily/Weekly with long ranges)
    #     show_annotations = len(yoy_df) <= 40

    #     if show_annotations:
    #         for _, r in yoy_df.iterrows():
    #             if r["Growth Label"] and r["Growth Label"] != "N/A":
    #                 label_color = "#166534" if (r["Growth %"] or 0) >= 0 else "#dc2626"
    #                 bar_top = max(
    #                     r["Revenue Cr"] if pd.notna(r["Revenue Cr"]) else 0,
    #                     r["Prev Revenue Cr"] if pd.notna(r["Prev Revenue Cr"]) else 0
    #                 )
    #                 fig_yoy.add_annotation(
    #                     x=r["Period"],
    #                     y=bar_top + (yoy_max * 0.16),
    #                     text=r["Growth Label"],
    #                     showarrow=False,
    #                     font=dict(size=10, color=label_color, family="Arial Black")
    #                 )

    #     fig_yoy.update_layout(
    #         barmode="group",
    #         height=260,
    #         margin=dict(l=2, r=2, t=30, b=0),
    #         xaxis_title="",
    #         yaxis_title="Revenue (Cr)",
    #         plot_bgcolor="white",
    #         paper_bgcolor="white",
    #         legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0, font=dict(size=10)),
    #         yaxis_range=[0, yoy_max * 1.35]
    #     )

    #     fig_yoy.update_xaxes(showgrid=False, zeroline=False)
    #     fig_yoy.update_yaxes(showgrid=False, zeroline=False)

    #     st.plotly_chart(fig_yoy, use_container_width=True)

    # st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Monthly weight trend data
    monthly_weight = (
        df.groupby("Month")["aweight"]
        .sum()
        .reset_index()
    )

    monthly_weight["Weight MT"] = (monthly_weight["aweight"] / 1000).round(2)

    monthly_weight["Month"] = pd.Categorical(
        monthly_weight["Month"],
        categories=month_order,
        ordered=True
    )

    monthly_weight = monthly_weight.sort_values("Month")
    # Zone revenue data
    # Zone-wise revenue data
    zone_df = (
        df.groupby("zone")["REVENUE"]
        .sum()
        .reset_index()
    )

    zone_df["Revenue Cr"] = (zone_df["REVENUE"] / 10000000).round(2)
    zone_df["zone_short"] = zone_df["zone"].replace({
        "NORTH ZONE": "North",
        "WEST ZONE": "West",
        "SOUTH ZONE": "South",
        "EAST ZONE": "East",
        "NORTH EAST ZONE": "NE",
        "NEPAL ZONE": "Nepal"
    })

    zone_df = zone_df.sort_values("Revenue Cr", ascending=False)
    zone_df = zone_df.sort_values("Revenue Cr", ascending=False)

    # Zone colors
    zone_colors = {
        "NORTH ZONE": "#1565C0",
        "WEST ZONE": "#009688",
        "SOUTH ZONE": "#FB8C00",
        "EAST ZONE": "#7E57C2",
        "NORTH EAST ZONE": "#EC407A",
        "NEPAL ZONE": "#EF5350",
        "North Zone": "#1565C0",
        "West Zone": "#009688",
        "South Zone": "#FB8C00",
        "East Zone": "#7E57C2",
        "North East Zone": "#EC407A",
        "Nepal Zone": "#EF5350",
    }

    if view_type == "Origin":
        zone_country_rev = (
            df.groupby(["zone", "COUNTRY"])["REVENUE"]
            .sum()
            .reset_index()
        )

        zone_country_rev["Revenue Cr"] = (
            zone_country_rev["REVENUE"] / 10000000
        ).round(2)

        matrix_df = zone_country_rev.pivot(
            index="zone",
            columns="COUNTRY",
            values="Revenue Cr"
        ).fillna(0)

        matrix_df["Total"] = matrix_df.sum(axis=1)
        matrix_df = matrix_df.sort_values("Total", ascending=False)

        zone_order = matrix_df.index.tolist()

        zone_col1, zone_col2, zone_col3 = st.columns([1.25, 1.20, 1.15])

    else:
        zone_col1, zone_col3 = st.columns([1.1, 1.1])
        zone_col2 = None

    with zone_col1:
        with st.container(border=True):
            st.markdown("###### Revenue by Zone")

            fig_zone = px.bar(
                zone_df.sort_values("Revenue Cr", ascending=True),
                y="zone_short",
                x="Revenue Cr",
                orientation="h",
                text="Revenue Cr",
                color="zone",
                color_discrete_map=zone_colors
            )

            fig_zone.update_traces(
                texttemplate="₹%{text:.2f} Cr",
                textposition="outside"
            )

            fig_zone.update_layout(
                height=190,
                margin=dict(l=2, r=30, t=2, b=2),
                xaxis_range=[0, zone_df["Revenue Cr"].max() * 1.15],
                xaxis_title="Revenue (Cr)",
                yaxis_title="",
                showlegend=False
            )

            st.plotly_chart(fig_zone, use_container_width=True)

    if view_type == "Origin":
        with zone_col2:
           
                matrix_display = matrix_df.reset_index()
                matrix_display = matrix_display.reset_index(drop=True)

                matrix_display["zone"] = matrix_display["zone"].replace({
                    "NORTH ZONE": "North",
                    "WEST ZONE": "West",
                    "SOUTH ZONE": "South",
                    "EAST ZONE": "East",
                    "NORTH EAST ZONE": "NE",
                    "NEPAL ZONE": "Nepal"
                })

                numeric_cols = matrix_display.columns[1:]

                # Matrix heatmap: zone versus country revenue
                styled_matrix = (
                    matrix_display.style
                    .format("{:.2f}", subset=numeric_cols)
                    .background_gradient(cmap="Blues", subset=numeric_cols)
                )

                st.dataframe(
                    styled_matrix,
                    use_container_width=True,
                    hide_index=True,
                    height=240
                )

    with zone_col3:
            with st.container(border=True):
                st.markdown("###### Monthly Weight(MT) Trend")

                # Monthly weight bar chart
                fig_weight = go.Figure()

                fig_weight.add_trace(
                    go.Bar(
                        x=monthly_weight["Month"],
                        y=monthly_weight["Weight MT"],
                        text=monthly_weight["Weight MT"],
                        texttemplate="%{text:.2f} MT",
                        textposition="outside",
                        marker_color="#0f766e"
                    )
                )

                fig_weight.update_layout(
                    height=190,
                    margin=dict(l=2, r=2, t=2, b=2)   
                
                )
                fig_weight.update_xaxes(showgrid=False,zeroline=False)
                fig_weight.update_yaxes(showgrid=False,zeroline=False)

                st.plotly_chart(fig_weight, use_container_width=True)
    # Small separator before branch analysis
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Branch summary for top/bottom branches and insights
    branch_summary = (
        df.groupby("branch")
        .agg(
            Revenue=("REVENUE", "sum"),
            GR_Count=("grno", "count"),
            Weight=("aweight", "sum"),
            FTL=("REVENUE", lambda x: x[df.loc[x.index, "LOADTYPE"] == "FTL"].sum()),
            LTL=("REVENUE", lambda x: x[df.loc[x.index, "LOADTYPE"] == "LTL"].sum())
        )
        .reset_index()
    )

    top10_df = branch_summary.sort_values("Revenue", ascending=False).head(10).copy()
    top10_df["Revenue Cr"] = (top10_df["Revenue"] / 10000000).round(2)

    bottom10_df = branch_summary[branch_summary["Revenue"] >= 1000000].copy()
    bottom10_df = bottom10_df.sort_values("Revenue", ascending=True).head(10)
    bottom10_df["Revenue Cr"] = (bottom10_df["Revenue"] / 10000000).round(2)

    monthly["Growth %"] = monthly["Revenue Cr"].pct_change().mul(100).round(2)

    def growth_indicator(x):
        if pd.isna(x):
            return "-"
        elif x >= 0:
            return f"▲ {x:.2f}%"
        else:
            return f"▼ {abs(x):.2f}%"

    monthly["Growth"] = monthly["Growth %"].apply(growth_indicator)

    b1, b2, b3, b4 = st.columns([1, 1, 0.95, 1])

    with b1:
        with st.container(border=True):
            st.markdown("###### Top 10 Branches by Revenue")

            max_top = top10_df["Revenue Cr"].max() if not top10_df.empty else 1

            for i, row in top10_df.reset_index(drop=True).iterrows():
                mini_rank_card(
                    i + 1,
                    row["branch"],
                    row["Revenue Cr"],
                    max_top,
                    "#22c55e"
                )

            

    with b2:
        with st.container(border=True):
            st.markdown("###### Bottom 10 Branches by Revenue")

            max_bottom = 1

            for i, row in bottom10_df.reset_index(drop=True).iterrows():
                mini_rank_card(
                    i + 1,
                    row["branch"],
                    row["Revenue Cr"],
                    max_bottom,
                    "#ef4444"
                )

            

    with b3:
        with st.container(border=True):
            st.markdown("###### Month on Month Growth")

            st.dataframe(
                monthly[["Month", "Revenue Cr", "Growth"]],
                use_container_width=True,
                hide_index=True,
                height=190
            )

    with b4:
        with st.container(border=True):
            st.markdown("##### 💡 Key Insights")

            best_branch = top10_df.iloc[0]["branch"] if not top10_df.empty else "-"
            best_zone = zone_df.iloc[0]["zone"] if not zone_df.empty else "-"

            st.markdown(f"✅ Highest Revenue Branch: **{best_branch}**")
            st.markdown(f"✅ Top Performing Zone: **{best_zone}**")
            st.markdown(f"🚛 Largest Revenue Source: **FTL ({ftl_pct:.1f}%)**")

            if len(monthly["Growth %"].dropna()) > 0:
                last_growth = monthly["Growth %"].dropna().iloc[-1]

                if last_growth < 0:
                    st.markdown(f"⚠️ Revenue at Risk: **Dropped {abs(last_growth):.2f}%**")
                else:
                    st.markdown(f"📈 Revenue Growth: **{last_growth:.2f}%**")

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    ###### 🏢 Branch Network Changes ({fy})

    - **New Branches/Agencies Opened:** {opened_branches}
    - **Branches/Agencies Closed:** {closed_branches}
    - **Net Increase:** {net_increase:+}
    """)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    with st.expander(f"📍 View Opened Branch Details ({opened_branches})"):

        st.dataframe(
            opened_df[
                [
                    "ZONE",
                    "TYPE",
                    "BRANCH",
                    "CODE",
                    "CITY",
                    "STATE",
                    "activedate"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    with st.expander(f"🔒 View Closed Branch Details ({closed_branches})"):

        st.dataframe(
            closed_df[
                [
                    "ZONE",
                    "TYPE",
                    "BRANCH",
                    "CODE",
                    "CITY",
                    "STATE",
                    "closedate"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )                
    # Export currently filtered dataset
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Export CSV",
        data=csv,
        file_name="overview_report.csv",
        mime="text/csv"
    )