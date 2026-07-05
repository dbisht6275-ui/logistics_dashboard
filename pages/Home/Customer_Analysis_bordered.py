import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from services.data_CustomerAnalysis import load_booking_data, get_date_range

# =====================================================
# Page Styling
# =====================================================
def apply_dashboard_style() -> None:
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 0.6rem;
                padding-bottom: 1rem;
                max-width: 96%;
            }

            hr {
                margin: 1rem 0 !important;
            }

            label {
                font-size: 12px !important;
                font-weight: 450 !important;
                color: #374151 !important;
            }

            div[data-baseweb="select"] {
                font-size: 13px !important;
            }

            [data-testid="stDataFrame"] table {
                font-size: 11px;
            }

            [data-testid="stDataFrame"] tbody tr {
                height: 24px !important;
            }

            div[data-testid="stDataFrame"] {
                font-size: 12px;
            }

            .kpi-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 15px 16px;
                height: 118px;
                box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
                font-family: Arial, sans-serif;
            }

            .kpi-title {
                font-size: 12px;
                color: #64748b;
                font-weight: 400;
                margin-bottom: 8px;
            }

            .kpi-value {
                font-size: 20px;
                font-weight: 650;
                color: #0f172a;
                line-height: 1.1;
            }

            .kpi-delta {
                font-size: 10px;
                margin-top: 8px;
                line-height: 1.2;
            }

            .kpi-icon {
                width: 35px;
                height: 30px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                flex-shrink: 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# Constants
# =====================================================
GREEN = "#16a34a"
RED = "#dc2626"
BLUE = "#2563eb"
ORANGE = "#f59e0b"
PURPLE = "#7c3aed"

FINANCIAL_YEARS = [
    "Select FY",
    "2026-2027",
    "2025-2026",
    "2024-2025",
    "2023-2024",
    "2022-2023",
    "2021-2022",
    "2020-2021",
]


# =====================================================
# Helper Functions
# =====================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keeps SQL output consistent with dashboard column names.
    Handles minor SQL casing differences safely.
    """
    df = df.copy()

    rename_map = {
        "zone": "Zone",
        "circle": "Circle",
        "branch": "Branch",
        "consignor": "Consignor",
        "consignee": "Consignee",
        "cngecode": "ConsigneeCode",
        "shipmentcount": "ShipmentCount",
        "actualweight": "ActualWeight",
        "chargeweight": "ChargeWeight",
        "revenue": "Revenue",
        "avgdelaydays": "AvgDelayDays",
        "maxdelaydays": "MaxDelayDays",
        "loadtype": "LoadType",
        "fin_month": "FIN_MONTH",
        "yr": "YR",
    }

    for col in list(df.columns):
        lower_col = col.lower()
        if lower_col in rename_map and col != rename_map[lower_col]:
            df = df.rename(columns={col: rename_map[lower_col]})

    return df


def clean_booking_data(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)

    numeric_cols = [
        "YR",
        "FIN_MONTH",
        "ShipmentCount",
        "ActualWeight",
        "ChargeWeight",
        "Revenue",
        "AvgDelayDays",
        "MaxDelayDays",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def money_cr(value: float) -> str:
    return f"₹{value / 10_000_000:.2f} Cr"


def growth_percentage(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def format_delta(value: float) -> str:
    arrow = "↑" if value >= 0 else "↓"
    return f"{arrow} {abs(value):.1f}% vs PY"


def previous_financial_year(fin_year: str, years_back: int = 1) -> str:
    start_year, end_year = fin_year.split("-")
    return f"{int(start_year) - years_back}-{int(end_year) - years_back}"


def get_customer_config(view_type: str) -> dict:
    if view_type == "origin":
        return {
            "code_col": "cngrcode",
            "name_col": "Consignor",
            "label": "Consignor",
        }

    return {
        "code_col": "ConsigneeCode",
        "name_col": "Consignee",
        "label": "Consignee",
    }


def apply_filters(
    df: pd.DataFrame,
    zone: str,
    circle: str,
    branch: str,
    load_type: str,
    customer: str,
    customer_name_col: str,
) -> pd.DataFrame:
    filtered = df.copy()

    if zone != "All" and "Zone" in filtered.columns:
        filtered = filtered[filtered["Zone"] == zone]
    if circle != "All" and "Circle" in filtered.columns:
        filtered = filtered[filtered["Circle"] == circle]
    if branch != "All" and "Branch" in filtered.columns:
        filtered = filtered[filtered["Branch"] == branch]

    if load_type != "All" and "LoadType" in filtered.columns:
        filtered = filtered[filtered["LoadType"] == load_type]

    if customer != "All" and customer_name_col in filtered.columns:
        filtered = filtered[filtered[customer_name_col] == customer]

    return filtered


def kpi_card(title: str, value: str, delta: str, icon: str, color: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div style="display:flex; justify-content:space-between; gap:10px; height:80%;">
                <div>
                    <div class="kpi-title">{title}</div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-delta" style="color:{color};">{delta}</div>
                </div>
                <div class="kpi-icon" style="background:{color}20; color:{color};">
                    {icon}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )




def plotly_card(fig):
    """Render Plotly charts inside a bordered visual card."""
    fig.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=50, b=20),
    )

    try:
        with st.container(border=True):
            st.plotly_chart(fig, use_container_width=True)
    except TypeError:
        st.markdown(
            """
            <div style="
                background:white;
                border:1px solid #d9d9d9;
                border-radius:12px;
                padding:10px;
                box-shadow:0 2px 6px rgba(0,0,0,.06);
                margin-bottom:10px;
            ";>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# Export
# =====================================================
def export_to_excel(
    df: pd.DataFrame,
    customer_summary: pd.DataFrame,
    growth_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    reactivated_df: pd.DataFrame,
    service_df: pd.DataFrame,
) -> BytesIO:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheets = {
            "Raw Summary Data": df,
            "Customer Summary": customer_summary,
            "Growth Degrowth": growth_df,
            "Monthly Summary": monthly_df,
            "Reactivated Customers": reactivated_df,
            "Service Performance": service_df,
        }

        workbook = writer.book
        header_format = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#1f2937",
                "font_color": "white",
                "border": 1,
            }
        )

        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)

            for col_num, col_name in enumerate(sheet_df.columns):
                worksheet.write(0, col_num, col_name, header_format)
                worksheet.set_column(col_num, col_num, 20)

    output.seek(0)
    return output


# =====================================================
# Data Preparation
# =====================================================
def build_customer_summary(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    name_col: str,
) -> pd.DataFrame:
    current_summary = (
        df.groupby([code_col, name_col], as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            shipments=("ShipmentCount", "sum"),
            actual_weight=("ActualWeight", "sum"),
            charge_weight=("ChargeWeight", "sum"),
            avg_delay=("AvgDelayDays", "mean"),
            max_delay=("MaxDelayDays", "max"),
        )
    )

    previous_summary = (
        prev_df.groupby(code_col, as_index=False)
        .agg(prev_revenue=("Revenue", "sum"))
    )

    summary = current_summary.merge(previous_summary, on=code_col, how="left")
    summary["prev_revenue"] = summary["prev_revenue"].fillna(0)
    summary["revenue_change"] = summary["revenue"] - summary["prev_revenue"]
    summary["growth_%"] = summary.apply(
        lambda row: growth_percentage(row["revenue"], row["prev_revenue"]),
        axis=1,
    )

    return summary


def build_monthly_summary(df: pd.DataFrame, code_col: str) -> pd.DataFrame:
    monthly = (
        df.groupby("FIN_MONTH", as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            shipments=("ShipmentCount", "sum"),
            customers=(code_col, "nunique"),
        )
        .sort_values("FIN_MONTH")
    )

    monthly["Revenue Cr"] = (monthly["revenue"] / 10_000_000).round(2)
    return monthly


def build_service_summary(
    df: pd.DataFrame,
    code_col: str,
    name_col: str,
) -> pd.DataFrame:
    service = (
        df.groupby([code_col, name_col], as_index=False)
        .agg(
            shipments=("ShipmentCount", "sum"),
            avg_delay_days=("AvgDelayDays", "mean"),
            max_delay_days=("MaxDelayDays", "max"),
            revenue=("Revenue", "sum"),
        )
    )

    service["Revenue Cr"] = (service["revenue"] / 10_000_000).round(2)
    service["avg_delay_days"] = service["avg_delay_days"].round(2)

    return service


def add_customer_segments(customer_summary: pd.DataFrame) -> pd.DataFrame:
        segmented = customer_summary.copy()

        if segmented.empty:
            segmented["segment"] = ""
            return segmented

        segmented = segmented.sort_values("revenue", ascending=False)
        total_revenue = segmented["revenue"].sum()

        segmented["revenue_share"] = segmented["revenue"] / total_revenue
        segmented["cum_revenue_share"] = segmented["revenue_share"].cumsum()

        def segment(cum_share: float) -> str:
            if cum_share <= 0.29:
                return "Champions"
            elif cum_share <= 0.55:
                return "Loyal"
            elif cum_share <= 0.80:
                return "Potential"
            elif cum_share <= 0.92:
                return "At Risk"
            else:
                return "Lost"

        segmented["segment"] = segmented["cum_revenue_share"].apply(segment)

        return segmented

# =====================================================
# UI Sections
# =====================================================
def render_main_filters():
    f1, f2 = st.columns([1, 1])

    with f1:
        fin_year = st.selectbox("Financial Year", FINANCIAL_YEARS)


    with f2:
        view_type = st.selectbox(
            "View Type",
            ["origin", "destination"],
            format_func=lambda x: "Origin" if x == "origin" else "Destination",
        )

    return fin_year, view_type


def render_data_filters(df: pd.DataFrame, customer_label: str, customer_name_col: str):
    f1, f2, f3, f4, f5, f6 = st.columns([1, 1, 1, 1, 1.3,0.90])

    with f1:
        zone_list = ["All"]
        if "Zone" in df.columns:
            zone_list += sorted(df["Zone"].dropna().unique())
        zone = st.selectbox("Zone", zone_list)

    zone_df = df if zone == "All" else df[df["Zone"] == zone]

    with f2:
        circle_list = ["All"]
        if "Circle" in zone_df.columns:
            circle_list += sorted(zone_df["Circle"].dropna().unique())

        circle = st.selectbox("Circle", circle_list)
    circle_df = zone_df if circle == "All" else zone_df[zone_df["Circle"] == circle]

    with f3:
        branch_list = ["All"]
        if "Branch" in zone_df.columns:
            branch_list += sorted(zone_df["Branch"].dropna().unique())
        branch = st.selectbox("Branch", branch_list)
    branch_df = circle_df if branch == "All" else circle_df[circle_df["Branch"] == branch]

    with f4:
        loadtype_list = ["All"]
        if "LoadType" in zone_df.columns:
            loadtype_list += sorted(zone_df["LoadType"].dropna().unique())
        load_type = st.selectbox("Load Type", loadtype_list)

    loadtype_df = zone_df if load_type == "All" else zone_df[zone_df["LoadType"] == load_type]
        
    with f5:
        customer_list = ["All"]
        if customer_name_col in loadtype_df.columns:
            customer_list += sorted(loadtype_df[customer_name_col].dropna().unique())
        customer = st.selectbox(customer_label, customer_list)


    
    with f6:
        st.markdown("<br>", unsafe_allow_html=True)
        export_placeholder = st.empty()
    


    return zone, circle, branch, load_type, customer, export_placeholder


def render_kpis(metrics: dict, customer_label: str) -> None:
    k1, k2, k3, k4, k5, k6 ,k7= st.columns(7)

    with k1:
        kpi_card(
            f"Active {customer_label}s",
            f"{metrics['active_customers']:,}",
            format_delta(metrics["active_growth"]),
            "👥",
            GREEN if metrics["active_growth"] >= 0 else RED,
        )

    with k2:
        kpi_card(
            f"New {customer_label}s",
            f"{metrics['new_customers']:,}",
            "Current FY vs Previous FY",
            "🆕",
            GREEN,
        )

    with k3:
        kpi_card(
            f"Lost {customer_label}s",
            f"{metrics['lost_customers']:,}",
            "Previous FY not active now",
            "❌",
            RED,
        )

    with k4:
        kpi_card(
            "Reactivated Customers",
            f"{metrics['reactivated_customers']:,}",
            "Returned after inactive FY",
            "🔄",
            BLUE,
        )

    with k5:
        kpi_card(
            f"At Risk {customer_label}s",
            f"{metrics['at_risk_customers']:,}",
            "Revenue dropped above 25%",
            "⚠️",
            ORANGE,
        )

    with k6:
        kpi_card(
            "Total Revenue",
            money_cr(metrics["total_revenue"]),
            format_delta(metrics["revenue_growth"]),
            "₹",
            PURPLE if metrics["revenue_growth"] >= 0 else RED,
        )
    with k7:
        kpi_card(
             "Current Yield",
             f"₹{metrics['current_yield']:.2f} /Kg",
             "Revenue / Charged Weight",
             "⚡",
             PURPLE,
        )

def render_overview_tab(
    customer_summary: pd.DataFrame,
    monthly: pd.DataFrame,
    code_col: str,
    name_col: str,
    customer_label: str,
    prev_df,
    lost_customer_codes,
) -> None:
    c1, c2, c3 = st.columns([1, 1, 0.95])

    with c1:
        fig = px.bar(
            monthly,
            x="FIN_MONTH",
            y="Revenue Cr",
            text="Revenue Cr",
            title="Month-wise Revenue Cr",
        )
        fig.update_traces(texttemplate="<b>₹%{text:.2f} Cr</b>", textposition="outside")
        fig.update_yaxes(title="Revenue Cr")
        fig.update_layout(height=350)
        plotly_card(fig)

    with c2:
        revenue_rank = customer_summary.sort_values("revenue", ascending=False)
        total_revenue = revenue_rank["revenue"].sum()

        rows = []
        for label, top_n in [
            ("Top 10 Customers", 10),
            ("Top 20 Customers", 20),
            ("Top 50 Customers", 50),
            ("Top 100 Customers", 100),
        ]:
            top_revenue = revenue_rank.head(top_n)["revenue"].sum()
            percentage = (top_revenue / total_revenue * 100) if total_revenue else 0
            rows.append(
                {
                    "Customer Group": label,
                    "% of Total Revenue": round(percentage, 1),
                }
            )

        concentration_df = pd.DataFrame(rows)

        fig = px.bar(
            concentration_df,
            x="% of Total Revenue",
            y="Customer Group",
            orientation="h",
            text="% of Total Revenue",
            title="Revenue Concentration",
        )
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(xaxis_title="% of Total Revenue", yaxis_title="", height=350)
        plotly_card(fig)

    with c3:
        segmented = add_customer_segments(customer_summary)

        segment_order = ["Champions", "Loyal", "Potential", "At Risk", "Lost"]
        segment_colors = {
            "Champions": "#14946b",
            "Loyal": "#0f6ec7",
            "Potential": "#5ab0e8",
            "At Risk": "#f59e0b",
            "Lost": "#ef4444",
        }

        segment_df = (
            segmented.groupby("segment", as_index=False)
            .agg(revenue=("revenue", "sum"))
        )

        total_segment_revenue = segment_df["revenue"].sum()

        segment_df["Revenue Cr"] = segment_df["revenue"] / 10_000_000
        segment_df["Revenue Label"] = segment_df["Revenue Cr"].apply(
            lambda x: f"₹{x:.2f} Cr"
        )
        segment_df["Contribution %"] = (
            segment_df["revenue"] / total_segment_revenue * 100
        ).round(1)

        segment_df["Percentage"] = segment_df["Contribution %"].round(0).astype(int)

        segment_df["Legend Label"] = segment_df.apply(
            lambda r: "{:<10} {:>5}% ({})".format(
                r["segment"],
                f"{r['Contribution %']:.1f}",
                money_cr(r["revenue"])
            ),
            axis=1,
        )
        segment_df["segment"] = pd.Categorical(
            segment_df["segment"],
            categories=segment_order,
            ordered=True,
        )

        segment_df = segment_df.sort_values("segment")

        fig = px.pie(
            segment_df,
            names="Legend Label",
            values="revenue",
            hole=0.55,
            title=f"{customer_label} Segmentation (By Revenue)",
            color="segment",
            color_discrete_map=segment_colors,
            
        )

        fig.update_traces(
            text=segment_df["Percentage"].astype(str) + "%",
            textinfo="text",
            textposition="inside",
        )

        fig.update_layout(
            height=350,

            annotations=[
                dict(
                    text=f"Total Revenue<br><b>{money_cr(total_segment_revenue)}</b>",
                    x=0.5,
                    y=0.5,
                    font_size=14,
                    showarrow=False,
                )
            ],

            legend=dict(
                orientation="v",
                y=0.95,
                yanchor="top",
                x=1.02,
                xanchor="left",
                font=dict(size=13),
                itemsizing="constant",
            ),

            legend_title_text="",
        )

        plotly_card(fig)

    top_growing = customer_summary[
        (customer_summary["prev_revenue"] > 0)
        & (customer_summary["revenue"] > customer_summary["prev_revenue"])
    ].copy()

    top_growing["Revenue Cr"] = (top_growing["revenue"] / 10_000_00).round(2)
    top_growing["PY Revenue (Cr)"] = (top_growing["prev_revenue"] / 10_000_00).round(2)
    top_growing["Growth % vs PY"] = top_growing["growth_%"].round(1)

    top_growing = top_growing.sort_values(
        "Growth % vs PY", ascending=False
    ).head(10)

    top_degrowing = customer_summary[
        (customer_summary["prev_revenue"] > 0)
        & (customer_summary["revenue"] < customer_summary["prev_revenue"])
        & (customer_summary["revenue"] > 0)
    ].copy()

    top_degrowing["Revenue Cr"] = (top_degrowing["revenue"] /10_000_00).round(2)
    top_degrowing["PY Revenue (Cr)"] = (top_degrowing["prev_revenue"] / 10_000_00).round(2)
    top_degrowing["Drop % vs PY"] = top_degrowing["growth_%"].round(1)

    top_degrowing = top_degrowing.sort_values(
        "Drop % vs PY", ascending=True
    ).head(10)

    lost_summary = (
        prev_df[prev_df[code_col].isin(lost_customer_codes)]
        .groupby([code_col, name_col], as_index=False)
        .agg(
            lost_revenue=("Revenue", "sum"),
            last_CN_month=("FIN_MONTH", "max"),
        )
    )

    lost_summary["Lost Revenue Cr"] = (
        lost_summary["lost_revenue"] / 100
    ).round(2)

    top_lost = lost_summary.sort_values(
        "lost_revenue", ascending=False
    ).head(10)

    t1, t2, t3 = st.columns([1.2,1.2, 1.0])

    with t1:
        st.markdown(f"##### Top 10 Growing {customer_label}s")
        st.dataframe(
            top_growing[
                [name_col, "Revenue Cr", "PY Revenue (Cr)", "Growth % vs PY"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with t2:
        st.markdown(f"##### Top 10 De-growing {customer_label}s")
        st.dataframe(
            top_degrowing[
                [name_col, "Revenue Cr", "PY Revenue (Cr)", "Drop % vs PY"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    with t3:
        st.markdown(f"##### Top 10 Lost {customer_label}s")
        st.dataframe(
            top_lost[
                [name_col, "Lost Revenue Cr", "last_CN_month"]
            ],
            use_container_width=True,
            hide_index=True,
        )


def render_growth_tab(
    growth_df: pd.DataFrame,
    name_col: str,
    customer_label: str,
) -> None:
    st.subheader(f"{customer_label} Growth / Degrowth")

    display_df = growth_df.copy()
    display_df["Revenue Cr"] = (display_df["revenue"] / 10_000_000).round(2)
    display_df["Previous Revenue Cr"] = (
        display_df["prev_revenue"] / 10_000_000
    ).round(2)

    st.dataframe(
        display_df[
            [
                name_col,
                "Revenue Cr",
                "Previous Revenue Cr",
                "growth_%",
                "Customer Status",
                "shipments",
                "actual_weight",
                "charge_weight",
                "avg_delay",
                "max_delay",
            ]
        ].sort_values("growth_%", ascending=True),
        use_container_width=True,
        hide_index=True,
    )


def render_service_tab(service_df: pd.DataFrame, customer_label: str) -> None:
    st.subheader(f"{customer_label} Service Performance")

    st.dataframe(
        service_df.sort_values("avg_delay_days", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


def render_revenue_bridge(metrics: dict, customer_label: str) -> None:
    bridge_df = pd.DataFrame({
        "Metric": [
            "Revenue<br>PY",
            f"Revenue from New<br>{customer_label}s",
            "Reactivated<br>Revenue",
            "Lost<br>Revenue",
            "Revenue<br>CY",
        ],
        "Value": [
            metrics["prev_revenue"] ,
            metrics["revenue_from_new_customers"],
            metrics["reactivated_revenue"],
            -metrics["lost_revenue"],
            metrics["total_revenue"],
        ],
    })

    fig = px.bar(
        bridge_df,
        x="Metric",
        y=bridge_df["Value"] / 10_000_000,
        text=(bridge_df["Value"] / 10_000_000).round(2),
        title="Revenue Bridge",
    )

    fig.update_traces(texttemplate="<b>₹ %{text:.2f} Cr</b>", textposition="outside")
    fig.update_yaxes(title="Revenue Cr")
    fig.update_xaxes(title="")
    fig.update_layout(height=360)

    plotly_card(fig)

def render_drilldown_tab(df: pd.DataFrame, name_col: str, customer_label: str) -> None:
    st.subheader(f"{customer_label} Drill Down")

    customers = sorted(df[name_col].dropna().unique())

    if not customers:
        st.info(f"No {customer_label.lower()} available for drill down.")
        return

    selected_customer = st.selectbox(f"Select {customer_label} for Detail", customers)
    customer_df = df[df[name_col] == selected_customer]

    total_shipments = customer_df["ShipmentCount"].sum()
    total_revenue = customer_df["Revenue"].sum()
    total_weight = customer_df["ChargeWeight"].sum()
    avg_revenue_per_shipment = (
        total_revenue / total_shipments if total_shipments > 0 else 0
    )

    d1, d2, d3, d4 = st.columns(4)

    d1.metric("Total Shipments", f"{total_shipments:,.0f}")
    d2.metric("Revenue", money_cr(total_revenue))
    d3.metric("Charge Weight", f"{total_weight:,.0f}")
    d4.metric("Avg Revenue / Shipment", f"₹{avg_revenue_per_shipment:,.0f}")

    st.dataframe(customer_df, use_container_width=True, hide_index=True)


# =====================================================
# Main Dashboard
# =====================================================
def show_CustomerAnalysis() -> None:
    apply_dashboard_style()

    fin_year, view_type = render_main_filters()

    if fin_year == "Select FY":
        st.info("Please select financial year")
        return

    
    config = get_customer_config(view_type)
    code_col = config["code_col"]
    name_col = config["name_col"]
    customer_label = config["label"]

    start_date, end_date = get_date_range(fin_year)
    prev_start, prev_end = get_date_range(previous_financial_year(fin_year, 1))
    old_start, old_end = get_date_range(previous_financial_year(fin_year, 2))

    with st.spinner("Loading customer summary data..."):
        all_df = clean_booking_data(load_booking_data(old_start, end_date, view_type))

    df = all_df[
        (all_df["YR"].astype(int) == int(fin_year.split("-")[0]))
    ].copy()

    prev_df = all_df[
        (all_df["YR"].astype(int) == int(previous_financial_year(fin_year, 1).split("-")[0]))
    ].copy()

    old_df = all_df[
        (all_df["YR"].astype(int) == int(previous_financial_year(fin_year, 2).split("-")[0]))
    ].copy()

    if df.empty:
        st.warning("No customer data found.")
        return

    required_cols = [
        code_col,
        name_col,
        "Zone",
        "Branch",
        "FIN_MONTH",
        "Revenue",
        "ShipmentCount",
        "ActualWeight",
        "ChargeWeight",
        "AvgDelayDays",
        "MaxDelayDays",
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        st.error(f"Missing columns in data: {missing_cols}")
        st.write("Available columns:", list(df.columns))
        return

    zone, circle, branch, load_type, customer, export_placeholder = render_data_filters(
        df,
        customer_label,
        name_col,
    )

    df = apply_filters(df, zone, circle, branch,load_type, customer, name_col)
    prev_df = apply_filters(prev_df, zone, circle, branch,load_type, customer, name_col)
    old_df = apply_filters(old_df, zone, circle, branch, load_type, customer, name_col)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    st.divider()

    current_customers = set(df[code_col].dropna().unique())
    previous_customers = set(prev_df[code_col].dropna().unique())
    older_customers = set(old_df[code_col].dropna().unique())

    new_customer_codes = current_customers - previous_customers
    lost_customer_codes = previous_customers - current_customers
    reactivated_customer_codes = (current_customers & older_customers) - previous_customers

    active_customers = len(current_customers)
    prev_active_customers = len(previous_customers)
    new_customers = len(new_customer_codes)
    lost_customers = len(lost_customer_codes)
    reactivated_customers = len(reactivated_customer_codes)

    total_revenue = df["Revenue"].sum()
    prev_revenue = prev_df["Revenue"].sum()

    customer_summary = build_customer_summary(df, prev_df, code_col, name_col)
    monthly = build_monthly_summary(df, code_col)
    service_df = build_service_summary(df, code_col, name_col)

    reactivated_df = customer_summary[
        customer_summary[code_col].isin(reactivated_customer_codes)
    ].copy()

    if not reactivated_df.empty:
        reactivated_df["Revenue Cr"] = (
            reactivated_df["revenue"] / 10_000_000
        ).round(2)
        reactivated_df["Previous Revenue Cr"] = (
            reactivated_df["prev_revenue"] / 10_000_000
        ).round(2)

    growth_df = customer_summary.copy()
    growth_df["Customer Status"] = "Existing"

    growth_df.loc[
        growth_df[code_col].isin(new_customer_codes),
        "Customer Status",
    ] = "New"

    growth_df.loc[
        growth_df[code_col].isin(reactivated_customer_codes),
        "Customer Status",
    ] = "Reactivated"

    at_risk_customers = customer_summary[
        (customer_summary["prev_revenue"] > 0)
        & (customer_summary["revenue"] < customer_summary["prev_revenue"] * 0.75)
    ][code_col].nunique()

    revenue_from_new_customers = df[
        df[code_col].isin(new_customer_codes)
    ]["Revenue"].sum()

    lost_revenue = prev_df[
        prev_df[code_col].isin(lost_customer_codes)
    ]["Revenue"].sum()

    reactivated_revenue = df[
        df[code_col].isin(reactivated_customer_codes)
    ]["Revenue"].sum()

    charged_weight = df["ChargeWeight"].sum()
    current_yield = total_revenue / charged_weight if charged_weight > 0 else 0

    retention_percent = (
        ((active_customers - new_customers) / prev_active_customers) * 100
        if prev_active_customers > 0
        else 0
    )

    metrics = {
        "active_customers": active_customers,
        "new_customers": new_customers,
        "lost_customers": lost_customers,
        "reactivated_customers": reactivated_customers,
        "at_risk_customers": at_risk_customers,
        "total_revenue": total_revenue,
        "prev_revenue": prev_revenue, 
        "active_growth": growth_percentage(active_customers, prev_active_customers),
        "revenue_growth": growth_percentage(total_revenue, prev_revenue),
        "retention_percent": retention_percent,
        "revenue_from_new_customers": revenue_from_new_customers,
        "lost_revenue": lost_revenue,
        "reactivated_revenue": reactivated_revenue,
        "current_yield": current_yield,
    }

    excel_file = export_to_excel(
        df=df,
        customer_summary=customer_summary,
        growth_df=growth_df,
        monthly_df=monthly,
        reactivated_df=reactivated_df,
        service_df=service_df,
    )

    with export_placeholder:
        st.download_button(
            label="⬇️ Export to Excel",
            data=excel_file,
            file_name=f"customer_analysis_{view_type}_{fin_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.markdown(
        """
        <style>
        div.stDownloadButton > button {
            background-color: #06245c;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 9px 18px;
            font-size: 13px;
            font-weight: 600;
        }

        div.stDownloadButton > button:hover {
            background-color: #0b3a8f;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_kpis(metrics, customer_label)

    c1, c2 = st.columns([1, 1])

    with c1:
        render_revenue_bridge(metrics, customer_label)

    with c2:
        st.empty()
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            f"{customer_label} Overview",
            "Growth & Retention",
            "Service Performance",
            f"{customer_label} Drill Down",
        ]
    )

    with tab1:
        render_overview_tab(
            customer_summary,
            monthly,
            code_col,
            name_col,
            customer_label,
            prev_df,
            lost_customer_codes,
        )

    with tab2:
        render_growth_tab(growth_df, name_col, customer_label)

    with tab3:
        render_service_tab(service_df, customer_label)

    with tab4:
        render_drilldown_tab(df, name_col, customer_label)

