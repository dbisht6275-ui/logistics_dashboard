import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from services.data_loader import load_booking_data, get_date_range

# =========================
# Compact dashboard styling
# =========================

st.markdown("""
<style>
[data-testid="stDataFrame"] table {
    font-size: 11px;
}
[data-testid="stDataFrame"] tbody tr {
    height: 24px !important;
}
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
h5, h6 {
    margin-top: 0rem !important;
    margin-bottom: 0.35rem !important;
}
div[data-testid="stSegmentedControl"] {
    display: flex;
    justify-content: flex-end;
}
div[data-testid="stSegmentedControl"] label {
    padding: 4px 10px !important;
    font-size: 12px !important;
}
div[data-testid="stDataFrame"] {
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# Helpers
# =========================

def format_cr(v):
    return f"{v / 10000000:.2f} Cr"


def get_previous_fy(fy):
    start_year, end_year = map(int, fy.split("-"))
    return f"{start_year - 1}-{end_year - 1}"


def pct_growth(current, previous):
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

FIN_MONTH_MAP = {
    1: "Apr", 2: "May", 3: "Jun", 4: "Jul",
    5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov",
    9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"
}


def create_card(title, value, color, icon, growth_value=None):
    """Compact KPI card. growth_value=None hides the vs-PY line (for % metrics without a clean PY compare)."""
    html = f"""<div style="background:#ffffff;padding:8px;border-radius:10px;border:1px solid #e5e7eb;box-shadow:0 3px 10px rgba(0,0,0,0.08);min-height:70px;">
<div style="display:flex;justify-content:space-between;align-items:center;">
<div style="color:{color};font-size:10px;font-weight:800;">{title}</div>
<div style="font-size:16px;">{icon}</div>
</div>
<div style="font-size:15px;font-weight:900;color:#0f172a;margin-top:1px;">{value}</div>"""

    if growth_value is not None:
        growth_color = "#166534" if growth_value >= 0 else "#dc2626"
        growth_text = growth_label(growth_value)
        html += f"""<div style="font-size:10px;color:{growth_color};font-weight:700;margin-top:1px;">{growth_text} vs LY</div>"""

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def mini_rank_card(rank, name, value, max_value, color, suffix="%"):
    pct = min((value / max_value * 100), 100) if max_value else 0
    html = f"""<div style="margin-bottom:6px;">
<div style="display:flex;align-items:center;gap:6px;">
<div style="background:#f1f5f9;border-radius:4px;padding:2px 6px;font-size:10px;color:#64748b;">{rank}</div>
<div style="font-size:10px;font-weight:800;color:#0f2747;min-width:95px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
<div style="flex:1;height:5px;background:#e5e7eb;border-radius:20px;overflow:hidden;">
<div style="width:{pct}%;height:5px;background:{color};border-radius:20px;"></div>
</div>
<div style="font-size:10px;font-weight:800;color:#0f2747;min-width:45px;text-align:right;">{value:.1f}{suffix}</div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def calculate_service_kpis(data):
    """KPIs used across the Service Level page. Safe against empty/None input."""
    if data is None or data.empty:
        return {
            "bookings": 0, "revenue": 0, "delivered": 0,
            "on_time_pct": 0, "sla_pct": 0, "avg_transit": 0
        }

    delivered_df = data[data["ShipmentStatus"] == "Delivered"]
    delivered = len(delivered_df)
    bookings = data["grno"].count()
    revenue = data["REVENUE"].sum()

    on_time_pct = (
        delivered_df["IsWithinSLA"].sum() / delivered * 100
        if delivered else 0
    )
    sla_pct = (
        data["IsWithinSLA"].sum() / bookings * 100
        if bookings else 0
    )
    avg_transit = (
        delivered_df["TransitDays"].mean()
        if delivered else 0
    )

    return {
        "bookings": bookings,
        "revenue": revenue,
        "delivered": delivered,
        "on_time_pct": on_time_pct,
        "sla_pct": sla_pct,
        "avg_transit": avg_transit if pd.notna(avg_transit) else 0
    }


def show_service_level():
    """Service Level analysis page."""

    st.markdown("""
    <h3 style='margin:0;padding:0;'>Service Level</h3>
    <p style='margin:0;color:#64748b;font-size:12px;'>
    Delivery Performance & SLA Dashboard
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # -----------------------------
    # Filter row
    # -----------------------------
    f1, f2, f3, f4, f5 = st.columns(5)

    with f1:
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

    with st.spinner("Loading service level data..."):
        df = load_booking_data(start_date, end_date, "origin")

    if df.empty:
        st.warning("No data found")
        return

    df["Month"] = df["FIN_MONTH"].map(FIN_MONTH_MAP)

    data_scope = st.session_state.get("data_scope", {})
    locked_zone = data_scope.get("zone")
    locked_branch = data_scope.get("branch")

    if locked_branch:
        branch_row = df[df["branch"] == locked_branch]
        if not branch_row.empty:
            locked_zone = branch_row["zone"].iloc[0]

    with f2:
        if locked_zone:
            zone = locked_zone
            st.selectbox("Zone", [zone], disabled=True, help="Locked as per your assigned rights")
        else:
            zone = st.selectbox("Zone", ["All"] + sorted(df["zone"].dropna().unique().tolist()))

    if zone != "All":
        df = df[df["zone"] == zone]

    with f3:
        if locked_branch:
            origin_branch = locked_branch
            st.selectbox("Origin Branch", [origin_branch], disabled=True, help="Locked as per your assigned rights")
        else:
            origin_branch = st.selectbox("Origin Branch", ["All"] + sorted(df["branch"].dropna().unique().tolist()))

    if origin_branch != "All":
        df = df[df["branch"] == origin_branch]

    with f4:
        dest_branch = st.selectbox("Destination Branch", ["All"] + sorted(df["destination"].dropna().unique().tolist()))

    if dest_branch != "All":
        df = df[df["destination"] == dest_branch]

    with f5:
        month = st.selectbox("Month", ["All"] + sorted(df["Month"].dropna().unique().tolist()))

    if month != "All":
        df = df[df["Month"] == month]

    if df.empty:
        st.warning("No data found for selected filters")
        return

    # -----------------------------
    # Previous FY (same filters) for growth %
    # -----------------------------
    prev_fy = get_previous_fy(fy)
    prev_df = pd.DataFrame()

    try:
        prev_start, prev_end = get_date_range(prev_fy)
        with st.spinner("Loading last year data..."):
            prev_df = load_booking_data(prev_start, prev_end, "origin")

        if not prev_df.empty:
            prev_df["Month"] = prev_df["FIN_MONTH"].map(FIN_MONTH_MAP)
            if zone != "All":
                prev_df = prev_df[prev_df["zone"] == zone]
            if origin_branch != "All":
                prev_df = prev_df[prev_df["branch"] == origin_branch]
            if dest_branch != "All":
                prev_df = prev_df[prev_df["destination"] == dest_branch]
            if month != "All":
                prev_df = prev_df[prev_df["Month"] == month]
    except Exception:
        prev_df = pd.DataFrame()

    kpi = calculate_service_kpis(df)
    prev_kpi = calculate_service_kpis(prev_df)

    bookings_growth = pct_growth(kpi["bookings"], prev_kpi["bookings"])
    revenue_growth = pct_growth(kpi["revenue"], prev_kpi["revenue"])
    delivered_growth = pct_growth(kpi["delivered"], prev_kpi["delivered"])
    on_time_growth = pct_growth(kpi["on_time_pct"], prev_kpi["on_time_pct"])
    sla_growth = pct_growth(kpi["sla_pct"], prev_kpi["sla_pct"])
    transit_growth = pct_growth(kpi["avg_transit"], prev_kpi["avg_transit"])

    # -----------------------------
    # KPI cards
    # -----------------------------
    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        create_card("Total Bookings", f"{kpi['bookings']:,}", "#2563eb", "📦", bookings_growth)
    with k2:
        create_card("Total Revenue", format_cr(kpi["revenue"]), "#16a34a", "💰", revenue_growth)
    with k3:
        create_card("Delivered Shipments", f"{kpi['delivered']:,}", "#0f766e", "✅", delivered_growth)
    with k4:
        create_card("On-Time Delivery %", f"{kpi['on_time_pct']:.2f}%", "#2563eb", "⏱️", on_time_growth)
    with k5:
        create_card("SLA Achievement %", f"{kpi['sla_pct']:.2f}%", "#7c3aed", "🛡️", sla_growth)
    with k6:
        # for transit days, a "growth" going up is bad, so invert the color logic via -transit_growth
        create_card("Avg Transit Time (Days)", f"{kpi['avg_transit']:.2f}", "#f97316", "🚛", -transit_growth)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # -----------------------------
    # Shipment status donut + Service level mix + SLA trend
    # -----------------------------
    row1a, row1b, row1c = st.columns([0.9, 1.3, 1.6])

    status_counts = df["ShipmentStatus"].value_counts()
    total_shipments = status_counts.sum()

    with row1a:
        with st.container(border=True):
            st.markdown("###### Shipment Status")

            fig_status = go.Figure(
                data=[
                    go.Pie(
                        labels=status_counts.index,
                        values=status_counts.values,
                        hole=0.65,
                        textinfo="percent",
                        marker=dict(colors=["#2563eb", "#f97316", "#94a3b8", "#dc2626"])
                    )
                ]
            )
            fig_status.update_layout(
                annotations=[
                    dict(
                        text=f"{total_shipments:,}<br>Total",
                        x=0.5, y=0.5, showarrow=False, font=dict(size=11)
                    )
                ],
                height=210,
                margin=dict(l=0, r=0, t=5, b=0),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, font=dict(size=8))
            )
            st.plotly_chart(fig_status, use_container_width=True)

    with row1b:
        with st.container(border=True):
            st.markdown("###### Service Level Mix")

            delivered_df = df[df["ShipmentStatus"] == "Delivered"]
            same_day = (delivered_df["TransitDays"] == 0).sum()
            next_day = (delivered_df["TransitDays"] == 1).sum()
            within_sla = df["IsWithinSLA"].sum()
            late = df["IsLate"].sum()
            late_df = df[df["IsLate"] == 1]
            avg_delay = late_df["DelayDays"].mean() if not late_df.empty else 0

            m1, m2 = st.columns(2)
            with m1:
                create_card("Same Day Delivery", f"{same_day:,}", "#2563eb", "⚡")
                create_card("Within SLA", f"{within_sla:,}", "#16a34a", "✔️")
            with m2:
                create_card("Next Day Delivery", f"{next_day:,}", "#7c3aed", "📅")
                create_card("Late Delivery", f"{late:,}", "#dc2626", "⚠️")

            create_card("Average Delay (Days)", f"{avg_delay:.2f}", "#0f172a", "⏳")

    with row1c:
        with st.container(border=True):
            st.markdown("###### SLA Performance (Monthly Trend)")

            monthly_sla = df.groupby("Month").agg(
                Delivered=("ShipmentStatus", lambda x: (x == "Delivered").sum()),
                WithinSLA=("IsWithinSLA", "sum"),
                Bookings=("grno", "count")
            ).reset_index()

            monthly_sla["Month"] = pd.Categorical(monthly_sla["Month"], categories=MONTH_ORDER, ordered=True)
            monthly_sla = monthly_sla.sort_values("Month")
            monthly_sla["SLA %"] = (monthly_sla["WithinSLA"] / monthly_sla["Bookings"] * 100).round(1)

            fig_trend = go.Figure()
            fig_trend.add_trace(
                go.Scatter(
                    x=monthly_sla["Month"],
                    y=monthly_sla["SLA %"],
                    mode="lines+markers+text",
                    text=monthly_sla["SLA %"],
                    texttemplate="%{text:.0f}%",
                    textposition="top center",
                    textfont=dict(size=9),
                    line=dict(width=2.5, color="#2563eb"),
                    marker=dict(size=6, color="#2563eb", line=dict(color="white", width=1.5))
                )
            )
            fig_trend.update_layout(
                height=210,
                margin=dict(l=2, r=2, t=10, b=0),
                plot_bgcolor="white",
                paper_bgcolor="white",
                yaxis_title="SLA %",
                yaxis_range=[0, 105]
            )
            fig_trend.update_xaxes(showgrid=False, zeroline=False)
            fig_trend.update_yaxes(showgrid=False, zeroline=False)
            st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # -----------------------------
    # Top branches / routes / delay distribution / zone table
    # -----------------------------
    row2a, row2b, row2c, row2d = st.columns([1, 1.1, 0.9, 1.3])

    branch_stats = df.groupby("branch").agg(
        Bookings=("grno", "count"),
        WithinSLA=("IsWithinSLA", "sum")
    ).reset_index()
    branch_stats = branch_stats[branch_stats["Bookings"] >= 10]
    branch_stats["SLA %"] = (branch_stats["WithinSLA"] / branch_stats["Bookings"] * 100).round(1)
    top_branches = branch_stats.sort_values("SLA %", ascending=False).head(5)

    with row2a:
        with st.container(border=True):
            st.markdown("###### Top 5 Branches by SLA %")
            max_val = top_branches["SLA %"].max() if not top_branches.empty else 1
            for i, r in top_branches.reset_index(drop=True).iterrows():
                mini_rank_card(i + 1, r["branch"], r["SLA %"], max_val, "#22c55e")

    route_stats = df.groupby("Route").agg(
        Bookings=("grno", "count"),
        WithinSLA=("IsWithinSLA", "sum")
    ).reset_index()
    route_stats = route_stats[route_stats["Bookings"] >= 10]
    route_stats["On-Time %"] = (route_stats["WithinSLA"] / route_stats["Bookings"] * 100).round(1)
    top_routes = route_stats.sort_values("On-Time %", ascending=False).head(5)

    with row2b:
        with st.container(border=True):
            st.markdown("###### Top 5 Routes by On-Time Delivery %")
            max_val = top_routes["On-Time %"].max() if not top_routes.empty else 1
            for i, r in top_routes.reset_index(drop=True).iterrows():
                mini_rank_card(i + 1, r["Route"], r["On-Time %"], max_val, "#2563eb")

    with row2c:
        with st.container(border=True):
            st.markdown("###### Delay Days Distribution")
            st.caption("Note: source data has no delay-reason field; showing delay-day buckets instead.")

            delayed = df[df["DelayDays"] > 0].copy()
            if not delayed.empty:
                bins = [0, 1, 2, 5, 10, float("inf")]
                labels = ["1 Day", "2 Days", "3-5 Days", "6-10 Days", "10+ Days"]
                delayed["Bucket"] = pd.cut(delayed["DelayDays"], bins=bins, labels=labels)
                bucket_counts = delayed["Bucket"].value_counts().reindex(labels).fillna(0)

                fig_delay = go.Figure(
                    data=[
                        go.Pie(
                            labels=bucket_counts.index,
                            values=bucket_counts.values,
                            hole=0.65,
                            textinfo="percent"
                        )
                    ]
                )
                fig_delay.update_layout(
                    annotations=[dict(text=f"{int(bucket_counts.sum())}<br>Delayed", x=0.5, y=0.5, showarrow=False, font=dict(size=10))],
                    height=200,
                    margin=dict(l=0, r=0, t=5, b=0),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.35, font=dict(size=7))
                )
                st.plotly_chart(fig_delay, use_container_width=True)
            else:
                st.info("No delayed shipments in selection")

    zone_stats = df.groupby("zone").agg(
        Bookings=("grno", "count"),
        WithinSLA=("IsWithinSLA", "sum"),
        AvgTransit=("TransitDays", "mean")
    ).reset_index()
    delivered_by_zone = df[df["ShipmentStatus"] == "Delivered"].groupby("zone").apply(
        lambda x: (x["IsWithinSLA"].sum() / len(x) * 100) if len(x) else 0
    ).reset_index(name="On-Time %")

    zone_table = zone_stats.merge(delivered_by_zone, on="zone", how="left")
    zone_table["SLA %"] = (zone_table["WithinSLA"] / zone_table["Bookings"] * 100).round(2)
    zone_table["On-Time %"] = zone_table["On-Time %"].round(2)
    zone_table["Avg Transit (Days)"] = zone_table["AvgTransit"].round(2)
    zone_table = zone_table[["zone", "SLA %", "On-Time %", "Avg Transit (Days)"]].sort_values("SLA %", ascending=False)
    zone_table.columns = ["Zone", "SLA %", "On-Time %", "Avg Transit (Days)"]

    with row2d:
        with st.container(border=True):
            st.markdown("###### Delivery Performance by Zone")
            st.dataframe(
                zone_table,
                use_container_width=True,
                hide_index=True,
                height=200
            )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # -----------------------------
    # Insights, alerts, top customers, overdue routes
    # -----------------------------
    b1, b2, b3, b4 = st.columns([1, 1.1, 1.1, 1.1])

    overdue_df = df[df["ShipmentStatus"] == "Overdue"]
    sla_breach_df = df[df["IsLate"] == 1]
    in_transit_df = df[df["ShipmentStatus"] == "In Transit"]

    with b1:
        with st.container(border=True):
            st.markdown("##### 💡 AI Insights")

            best_branch = top_branches.iloc[0]["branch"] if not top_branches.empty else "-"
            best_branch_sla = top_branches.iloc[0]["SLA %"] if not top_branches.empty else 0
            worst_zone = zone_table.iloc[-1]["Zone"] if not zone_table.empty else "-"
            top_delay_bucket = (
                delayed["Bucket"].value_counts().idxmax()
                if not delayed.empty else "-"
            )

            sla_trend_change = 0
            if len(monthly_sla) >= 2:
                sla_trend_change = monthly_sla["SLA %"].iloc[-1] - monthly_sla["SLA %"].iloc[-2]

            st.markdown(
                f"{'✅' if sla_trend_change >= 0 else '⚠️'} SLA achievement "
                f"{'improved' if sla_trend_change >= 0 else 'dropped'} by "
                f"**{abs(sla_trend_change):.1f}%** vs previous month."
            )
            st.markdown(f"🔴 **{worst_zone}** zone has the lowest SLA performance. Needs attention.")
            st.markdown(f"⏳ **{top_delay_bucket}** delay bucket has the most late deliveries.")
            st.markdown(f"🏆 **{best_branch}** is the top performer with **{best_branch_sla:.1f}%** SLA.")

    with b2:
        with st.container(border=True):
            st.markdown("##### 🔔 Alerts & Notifications")
            st.markdown(f"🟠 Overdue Shipments: **{len(overdue_df):,}**")
            st.markdown(f"🔴 SLA Breach Shipments: **{len(sla_breach_df):,}**")
            st.markdown(f"🔵 In Transit: **{len(in_transit_df):,}**")

    top_customers = (
        df.groupby("consignor")
        .agg(Revenue=("REVENUE", "sum"), Bookings=("grno", "count"), WithinSLA=("IsWithinSLA", "sum"))
        .reset_index()
    )
    top_customers["SLA %"] = (top_customers["WithinSLA"] / top_customers["Bookings"] * 100).round(1)
    top_customers["Revenue Cr"] = (top_customers["Revenue"] / 10000000).round(2)
    top_customers = top_customers.sort_values("Revenue", ascending=False).head(5)

    with b3:
        with st.container(border=True):
            st.markdown("##### 👤 Top 5 Customers by Revenue")
            st.dataframe(
                top_customers[["consignor", "Revenue Cr", "Bookings", "SLA %"]].rename(
                    columns={"consignor": "Customer"}
                ),
                use_container_width=True,
                hide_index=True,
                height=190
            )

    overdue_routes = (
        overdue_df.groupby("Route")
        .agg(Overdue_Shipments=("grno", "count"), Avg_Delay=("DelayDays", "mean"))
        .reset_index()
        .sort_values("Overdue_Shipments", ascending=False)
        .head(5)
    )
    overdue_routes["Avg_Delay"] = overdue_routes["Avg_Delay"].round(2)
    overdue_routes.columns = ["Route", "Overdue Shipments", "Avg Delay (Days)"]

    with b4:
        with st.container(border=True):
            st.markdown("##### 🚩 Top 5 Overdue Routes")
            if not overdue_routes.empty:
                st.dataframe(
                    overdue_routes,
                    use_container_width=True,
                    hide_index=True,
                    height=190
                )
            else:
                st.info("No overdue routes in selection")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.caption("All metrics are based on selected filters. Click on any chart or card to view detailed analysis.")

    # Export
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Export CSV",
        data=csv,
        file_name="service_level_report.csv",
        mime="text/csv"
    )