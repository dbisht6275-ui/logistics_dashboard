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
        /* ---------- KPI Card ---------- */
        .kpi-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px 16px;
            min-height: 110px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            position: relative;
            overflow: hidden;
        }
        .kpi-title {
            font-size: 12px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 22px;
            font-weight: 700;
            color: #1e293b;
            line-height: 1.2;
        }
        .kpi-delta {
            font-size: 11px;
            color: #94a3b8;
            margin-top: 4px;
        }
        .kpi-icon {
            position: absolute;
            top: 12px;
            right: 14px;
            font-size: 22px;
            opacity: 0.9;      /* emoji ko clear dikhane ke liye */
        }
        .kpi-accent {
            position: absolute;
            bottom: 0;
            left: 0;
            height: 3px;
            width: 100%;
        }

        /* ---------- Section Headers ---------- */
        .section-header {
            font-size: 14px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 6px;
            padding-bottom: 4px;
            border-bottom: 2px solid #e2e8f0;
        }

        /* ---------- Filter Row ---------- */
        div[data-testid="stHorizontalBlock"] > div {
            align-items: flex-end !important;
        }

        /* ---------- Export Button ---------- */
        div[data-testid="stDownloadButton"] button {
            background-color: #1e40af !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            padding: 8px 14px !important;
            width: 100% !important;
            font-size: 13px !important;
            border: none !important;
            margin-top: 4px;
        }
        div[data-testid="stDownloadButton"] button:hover {
            background-color: #1d4ed8 !important;
        }

        /* ============================================= */
        /*   DATAFRAME COMPACT + SMALL FONT (columns fit) */
        /* ============================================= */
        div[data-testid="stDataFrame"] {
            border-radius: 8px;
            overflow: hidden;
        }
        /* Cell + header font chhota */
        div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] * {
            font-size: 11px !important;
        }
        /* Header thoda bold */
        div[data-testid="stDataFrame"] thead tr th {
            font-size: 11px !important;
            font-weight: 700 !important;
            padding: 4px 6px !important;
        }
        /* Cell padding kam -> zyada columns fit */
        div[data-testid="stDataFrame"] tbody tr td {
            font-size: 11px !important;
            padding: 3px 6px !important;
        }
        /* Glide grid (newer Streamlit) ke liye bhi */
        .glideDataEditor {
            font-size: 11px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



# =====================================================
# Constants
# =====================================================
GREEN  = "#16a34a"
RED    = "#dc2626"
BLUE   = "#2563eb"
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
    df = df.copy()
    rename_map = {
        "zone":         "Zone",
        "circle":       "Circle",
        "branch":       "Branch",
        "consignor":    "Consignor",
        "consignee":    "Consignee",
        "cngecode":     "ConsigneeCode",
        "shipmentcount":"ShipmentCount",
        "actualweight": "ActualWeight",
        "chargeweight": "ChargeWeight",
        "revenue":      "Revenue",
        "avgdelaydays": "AvgDelayDays",
        "maxdelaydays": "MaxDelayDays",
        "loadtype":     "LoadType",
        "fin_month":    "FIN_MONTH",
        "yr":           "YR",
    }
    for col in list(df.columns):
        lower_col = col.lower()
        if lower_col in rename_map and col != rename_map[lower_col]:
            df = df.rename(columns={col: rename_map[lower_col]})
    return df


def clean_booking_data(df: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df)
    numeric_cols = [
        "YR", "FIN_MONTH", "ShipmentCount", "ActualWeight",
        "ChargeWeight", "Revenue", "AvgDelayDays", "MaxDelayDays",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def money_cr(value: float) -> str:
    return f"Rs.{value / 10_000_000:.2f} Cr"


def growth_percentage(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def format_delta(value: float) -> str:
    arrow = "up" if value >= 0 else "dn"
    sign  = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.1f}% vs PY"


def previous_financial_year(fin_year: str, years_back: int = 1) -> str:
    start_year, end_year = fin_year.split("-")
    return f"{int(start_year) - years_back}-{int(end_year) - years_back}"


def get_customer_config(view_type: str) -> dict:
    if view_type == "origin":
        return {"code_col": "cngrcode", "name_col": "Consignor", "label": "Consignor"}
    return {"code_col": "ConsigneeCode", "name_col": "Consignee", "label": "Consignee"}


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
    if zone      != "All" and "Zone"     in filtered.columns: filtered = filtered[filtered["Zone"]     == zone]
    if circle    != "All" and "Circle"   in filtered.columns: filtered = filtered[filtered["Circle"]   == circle]
    if branch    != "All" and "Branch"   in filtered.columns: filtered = filtered[filtered["Branch"]   == branch]
    if load_type != "All" and "LoadType" in filtered.columns: filtered = filtered[filtered["LoadType"] == load_type]
    if customer  != "All" and customer_name_col in filtered.columns:
        filtered = filtered[filtered[customer_name_col] == customer]
    return filtered


# =====================================================
# KPI Card  (accent bar color)
# =====================================================
def kpi_card(title: str, value: str, delta: str, icon: str, color: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-accent" style="background:{color};"></div>
            <div class="kpi-icon">{icon}</div>
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta">{delta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
            "Raw Summary Data":    df,
            "Customer Summary":    customer_summary,
            "Growth Degrowth":     growth_df,
            "Monthly Summary":     monthly_df,
            "Reactivated Customers": reactivated_df,
            "Service Performance": service_df,
        }
        workbook = writer.book
        header_format = workbook.add_format(
            {"bold": True, "bg_color": "#1f2937", "font_color": "white", "border": 1}
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
    summary["prev_revenue"]   = summary["prev_revenue"].fillna(0)
    summary["revenue_change"] = summary["revenue"] - summary["prev_revenue"]
    summary["growth_%"]       = summary.apply(
        lambda row: growth_percentage(row["revenue"], row["prev_revenue"]), axis=1
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


def build_service_summary(df: pd.DataFrame, code_col: str, name_col: str) -> pd.DataFrame:
    service = (
        df.groupby([code_col, name_col], as_index=False)
        .agg(
            shipments=("ShipmentCount", "sum"),
            avg_delay_days=("AvgDelayDays", "mean"),
            max_delay_days=("MaxDelayDays", "max"),
            revenue=("Revenue", "sum"),
        )
    )
    service["Revenue Cr"]     = (service["revenue"] / 10_000_000).round(2)
    service["avg_delay_days"] = service["avg_delay_days"].round(2)
    return service


def add_customer_segments(customer_summary: pd.DataFrame) -> pd.DataFrame:
    segmented = customer_summary.copy()
    if segmented.empty:
        segmented["segment"] = ""
        return segmented
    segmented = segmented.sort_values("revenue", ascending=False)
    total_revenue = segmented["revenue"].sum()
    segmented["revenue_share"]     = segmented["revenue"] / total_revenue
    segmented["cum_revenue_share"] = segmented["revenue_share"].cumsum()

    def segment(cum_share: float) -> str:
        if cum_share <= 0.29: return "Champions"
        elif cum_share <= 0.55: return "Loyal"
        elif cum_share <= 0.80: return "Potential"
        elif cum_share <= 0.92: return "At Risk"
        else: return "Lost"

    segmented["segment"] = segmented["cum_revenue_share"].apply(segment)
    return segmented


# =====================================================
# UI Sections
# =====================================================
def render_main_filters():
    # ---- FY takes 55%, View Type takes 45% ----
    f1, f2 = st.columns([1.2, 1])
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
    data_scope   = st.session_state.get("data_scope", {})
    locked_zone   = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    if locked_branch:
        row = df[df["Branch"] == locked_branch]
        if not row.empty:
            locked_circle = row["Circle"].iloc[0]
            locked_zone   = row["Zone"].iloc[0]
    elif locked_circle:
        row = df[df["Circle"] == locked_circle]
        if not row.empty:
            locked_zone = row["Zone"].iloc[0]

    # Zone | Circle | Branch | LoadType | Consignor | [Export]
    # Equal weight columns; export gets slightly more for button
    f1, f2, f3, f4, f5, f6 = st.columns([1, 1, 1, 1, 1.4, 1.1])

    with f1:
        if locked_zone:
            zone = locked_zone
            st.selectbox("Zone", [zone], disabled=True)
        else:
            zone_list = ["All"] + (sorted(df["Zone"].dropna().unique()) if "Zone" in df.columns else [])
            zone = st.selectbox("Zone", zone_list)
    zone_df = df if zone == "All" else df[df["Zone"] == zone]

    with f2:
        if locked_circle:
            circle = locked_circle
            st.selectbox("Circle", [circle], disabled=True)
        else:
            circle_list = ["All"] + (sorted(zone_df["Circle"].dropna().unique()) if "Circle" in zone_df.columns else [])
            circle = st.selectbox("Circle", circle_list)
    circle_df = zone_df if circle == "All" else zone_df[zone_df["Circle"] == circle]

    with f3:
        if locked_branch:
            branch = locked_branch
            st.selectbox("Branch", [branch], disabled=True)
        else:
            branch_list = ["All"] + (sorted(circle_df["Branch"].dropna().unique()) if "Branch" in circle_df.columns else [])
            branch = st.selectbox("Branch", branch_list)
    branch_df = circle_df if branch == "All" else circle_df[circle_df["Branch"] == branch]

    with f4:
        loadtype_list = ["All"] + (sorted(branch_df["LoadType"].dropna().unique()) if "LoadType" in branch_df.columns else [])
        load_type = st.selectbox("Load Type", loadtype_list)
    loadtype_df = branch_df if load_type == "All" else branch_df[branch_df["LoadType"] == load_type]

    with f5:
        customer_list = ["All"] + (sorted(loadtype_df[customer_name_col].dropna().unique()) if customer_name_col in loadtype_df.columns else [])
        customer = st.selectbox(customer_label, customer_list)

    with f6:
        # Small vertical nudge so button aligns with selectboxes
        st.markdown("<div style='height:27px'></div>", unsafe_allow_html=True)
        export_placeholder = st.empty()

    return zone, circle, branch, load_type, customer, export_placeholder


# =====================================================
# KPI Row  — 7 equal columns
# =====================================================
def render_kpis(metrics: dict, customer_label: str) -> None:
    cols = st.columns(7)

    cards = [
        (
            f"Active {customer_label}s",
            f"{metrics['active_customers']:,}",
            format_delta(metrics["active_growth"]),
            "👥",
            GREEN if metrics["active_growth"] >= 0 else RED,
        ),
        (
            f"New {customer_label}s",
            f"{metrics['new_customers']:,}",
            "Current FY vs Previous FY",
            "🆕",
            GREEN,
        ),
        (
            f"Lost {customer_label}s",
            f"{metrics['lost_customers']:,}",
            "Previous FY not active now",
            "❌",
            RED,
        ),
        (
            "Reactivated Customers",
            f"{metrics['reactivated_customers']:,}",
            "Returned after inactive FY",
            "🔄",
            BLUE,
        ),
        (
            f"At Risk {customer_label}s",
            f"{metrics['at_risk_customers']:,}",
            "Revenue dropped above 25%",
            "⚠️",
            ORANGE,
        ),
        (
            "Total Revenue",
            money_cr(metrics["total_revenue"]),
            format_delta(metrics["revenue_growth"]),
            "₹",
            PURPLE if metrics["revenue_growth"] >= 0 else RED,
        ),
        (
            "Current Yield",
            f"₹{metrics['current_yield']:.2f} /Kg",
            "Revenue / Chg Wt",
            "⚡",
            PURPLE,
        ),
    ]

    for col, (title, value, delta, icon, color) in zip(cols, cards):
        with col:
            kpi_card(title, value, delta, icon, color)



# =====================================================
# Overview Tab
# =====================================================
def render_overview_tab(
    customer_summary: pd.DataFrame,
    monthly: pd.DataFrame,
    code_col: str,
    name_col: str,
    customer_label: str,
    prev_df,
    lost_customer_codes,
) -> None:
    # --- Three equal chart columns ---
    c1, c2, c3 = st.columns(3)

    with c1:
        fig = px.bar(
            monthly, x="FIN_MONTH", y="Revenue Cr",
            text="Revenue Cr", title="Month-wise Revenue (Cr)",
        )
        fig.update_traces(texttemplate="Rs.%{text:.2f} Cr", textposition="outside")
        fig.update_yaxes(title="Revenue Cr")
        fig.update_layout(height=350, margin=dict(t=50, b=30))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        revenue_rank = customer_summary.sort_values("revenue", ascending=False)
        total_revenue = revenue_rank["revenue"].sum()
        rows = []
        for lbl, top_n in [("Top 10", 10), ("Top 20", 20), ("Top 50", 50), ("Top 100", 100)]:
            top_rev = revenue_rank.head(top_n)["revenue"].sum()
            pct     = (top_rev / total_revenue * 100) if total_revenue else 0
            rows.append({"Customer Group": lbl, "% of Total Revenue": round(pct, 1)})
        concentration_df = pd.DataFrame(rows)
        fig = px.bar(
            concentration_df,
            x="% of Total Revenue", y="Customer Group",
            orientation="h", text="% of Total Revenue",
            title="Revenue Concentration",
        )
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(xaxis_title="% of Total Revenue", yaxis_title="", height=350, margin=dict(t=50, b=30))
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        segmented      = add_customer_segments(customer_summary)
        segment_order  = ["Champions", "Loyal", "Potential", "At Risk", "Lost"]
        segment_colors = {
            "Champions": "#14946b",
            "Loyal":     "#0f6ec7",
            "Potential": "#5ab0e8",
            "At Risk":   "#f59e0b",
            "Lost":      "#ef4444",
        }
        segment_df = segmented.groupby("segment", as_index=False).agg(revenue=("revenue", "sum"))
        total_seg_rev = segment_df["revenue"].sum()
        segment_df["Contribution %"] = (segment_df["revenue"] / total_seg_rev * 100).round(1)
        segment_df["Percentage"]     = segment_df["Contribution %"].round(0).astype(int)
        segment_df["Legend Label"]   = segment_df.apply(
            lambda r: f"{r['segment']:<10} {r['Contribution %']:.1f}% ({money_cr(r['revenue'])})", axis=1
        )
        segment_df["segment"] = pd.Categorical(segment_df["segment"], categories=segment_order, ordered=True)
        segment_df = segment_df.sort_values("segment")

        fig = px.pie(
            segment_df, names="Legend Label", values="revenue",
            hole=0.55, title=f"{customer_label} Segmentation",
            color="segment", color_discrete_map=segment_colors,
        )
        fig.update_traces(
            text=segment_df["Percentage"].astype(str) + "%",
            textinfo="text", textposition="inside",
        )
        fig.update_layout(
            height=350,
            margin=dict(t=50, b=10),
            annotations=[dict(
                text=f"Total<br>{money_cr(total_seg_rev)}",
                x=0.5, y=0.5, font_size=13, showarrow=False
            )],
            legend=dict(orientation="v", y=0.95, yanchor="top", x=1.02, xanchor="left", font=dict(size=11)),
            legend_title_text="",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Growing / De-growing / Lost tables — equal 3 columns ---
    # FIX: was /10_000_00 (10 lakh) — corrected to /10_000_000 (1 crore)
    top_growing = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] > customer_summary["prev_revenue"])
    ].copy()
    top_growing["Revenue Cr"]       = (top_growing["revenue"]      / 10_000_000).round(2)
    top_growing["PY Revenue (Cr)"]  = (top_growing["prev_revenue"] / 10_000_000).round(2)
    top_growing["Growth % vs PY"]   = top_growing["growth_%"].round(1)
    top_growing = top_growing.sort_values("Growth % vs PY", ascending=False).head(10)

    top_degrowing = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] < customer_summary["prev_revenue"]) &
        (customer_summary["revenue"] > 0)
    ].copy()
    top_degrowing["Revenue Cr"]      = (top_degrowing["revenue"]      / 10_000_000).round(2)
    top_degrowing["PY Revenue (Cr)"] = (top_degrowing["prev_revenue"] / 10_000_000).round(2)
    top_degrowing["Drop % vs PY"]    = top_degrowing["growth_%"].round(1)
    top_degrowing = top_degrowing.sort_values("Drop % vs PY", ascending=True).head(10)

    lost_summary = (
        prev_df[prev_df[code_col].isin(lost_customer_codes)]
        .groupby([code_col, name_col], as_index=False)
        .agg(lost_revenue=("Revenue", "sum"), last_CN_month=("FIN_MONTH", "max"))
    )
    # FIX: was /100 — corrected to /10_000_000
    lost_summary["Lost Revenue Cr"] = (lost_summary["lost_revenue"] / 10_000_000).round(2)
    top_lost = lost_summary.sort_values("lost_revenue", ascending=False).head(10)

    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown(f"<div class='section-header'>Top 10 Growing {customer_label}s</div>", unsafe_allow_html=True)
        st.dataframe(
            top_growing[[name_col, "Revenue Cr", "PY Revenue (Cr)", "Growth % vs PY"]],
            use_container_width=True, hide_index=True,
        )
    with t2:
        st.markdown(f"<div class='section-header'>Top 10 De-growing {customer_label}s</div>", unsafe_allow_html=True)
        st.dataframe(
            top_degrowing[[name_col, "Revenue Cr", "PY Revenue (Cr)", "Drop % vs PY"]],
            use_container_width=True, hide_index=True,
        )
    with t3:
        st.markdown(f"<div class='section-header'>Top 10 Lost {customer_label}s</div>", unsafe_allow_html=True)
        st.dataframe(
            top_lost[[name_col, "Lost Revenue Cr", "last_CN_month"]],
            use_container_width=True, hide_index=True,
        )


# =====================================================
# Growth Tab
# =====================================================
def render_growth_tab(growth_df: pd.DataFrame, name_col: str, customer_label: str) -> None:
    st.subheader(f"{customer_label} Growth / Degrowth")
    display_df = growth_df.copy()
    display_df["Revenue Cr"]          = (display_df["revenue"]      / 10_000_000).round(2)
    display_df["Previous Revenue Cr"] = (display_df["prev_revenue"] / 10_000_000).round(2)
    st.dataframe(
        display_df[[
            name_col, "Revenue Cr", "Previous Revenue Cr", "growth_%",
            "Customer Status", "shipments", "actual_weight", "charge_weight",
            "avg_delay", "max_delay",
        ]].sort_values("growth_%", ascending=True),
        use_container_width=True, hide_index=True,
    )


# =====================================================
# Service Tab
# =====================================================
def render_service_tab(service_df: pd.DataFrame, customer_label: str) -> None:
    st.subheader(f"{customer_label} Service Performance")
    st.dataframe(
        service_df.sort_values("avg_delay_days", ascending=False),
        use_container_width=True, hide_index=True,
    )


# =====================================================
# Revenue Bridge
# =====================================================
def render_revenue_bridge(metrics: dict, customer_label: str) -> None:
    bridge_df = pd.DataFrame({
        "Metric": [
            "Revenue PY",
            f"New {customer_label}s",
            "Reactivated",
            "Lost Revenue",
            "Revenue CY",
        ],
        "Value": [
            metrics["prev_revenue"],
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
    fig.update_traces(texttemplate="Rs. %{text:.2f} Cr", textposition="outside")
    fig.update_yaxes(title="Revenue Cr")
    fig.update_xaxes(title="")
    fig.update_layout(height=370, margin=dict(t=50, b=30))
    st.plotly_chart(fig, use_container_width=True)


# =====================================================
# Zone Summary Table
# =====================================================
def render_zone_summary_table(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    customer_label: str,
) -> None:
    current_zone = df.groupby("Zone", as_index=False).agg(
        Active_Customers=(code_col, "nunique"),
        Revenue=("Revenue", "sum"),
    )
    prev_zone = prev_df.groupby("Zone", as_index=False).agg(
        Prev_Customers=(code_col, "nunique"),
        Prev_Revenue=("Revenue", "sum"),
    )
    new_df   = df[~df[code_col].isin(prev_df[code_col].dropna().unique())]
    lost_df  = prev_df[~prev_df[code_col].isin(df[code_col].dropna().unique())]
    new_zone  = new_df.groupby("Zone",  as_index=False).agg(New=(code_col,  "nunique"))
    lost_zone = lost_df.groupby("Zone", as_index=False).agg(Lost=(code_col, "nunique"))

    zone_summary = (
        current_zone
        .merge(prev_zone,  on="Zone", how="left")
        .merge(new_zone,   on="Zone", how="left")
        .merge(lost_zone,  on="Zone", how="left")
        .fillna(0)
    )
    zone_summary["Revenue (Cr)"] = (zone_summary["Revenue"] / 10_000_000).round(2)
    zone_summary["Growth %"]     = zone_summary.apply(
        lambda r: growth_percentage(r["Revenue"], r["Prev_Revenue"]), axis=1
    )
    zone_summary = zone_summary.rename(columns={"Active_Customers": f"Active {customer_label}s"})

    display_df = zone_summary[["Zone", f"Active {customer_label}s", "New", "Lost", "Revenue (Cr)", "Growth %"]].copy()
    total_row = {
        "Zone":                       "Total",
        f"Active {customer_label}s":  int(display_df[f"Active {customer_label}s"].sum()),
        "New":                        int(display_df["New"].sum()),
        "Lost":                       int(display_df["Lost"].sum()),
        "Revenue (Cr)":               round(display_df["Revenue (Cr)"].sum(), 2),
        "Growth %":                   growth_percentage(zone_summary["Revenue"].sum(), zone_summary["Prev_Revenue"].sum()),
    }
    display_df = pd.concat([display_df, pd.DataFrame([total_row])], ignore_index=True)

    st.markdown(f"<div class='section-header'>Zone-wise {customer_label} Summary</div>", unsafe_allow_html=True)
    st.dataframe(
        display_df.style.format({
            f"Active {customer_label}s": "{:,.0f}",
            "New":          "{:,.0f}",
            "Lost":         "{:,.0f}",
            "Revenue (Cr)": "{:,.2f}",
            "Growth %":     "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


# =====================================================
# Branch Summary Table
# =====================================================
def render_branch_summary_table(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    customer_label: str,
) -> None:
    current    = df.groupby("Branch", as_index=False).agg(Revenue=("Revenue", "sum"), Customers=(code_col, "nunique"))
    previous   = prev_df.groupby("Branch", as_index=False).agg(PrevRevenue=("Revenue", "sum"))
    new_df     = df[~df[code_col].isin(prev_df[code_col].unique())]
    new_branch = new_df.groupby("Branch", as_index=False).agg(NewCustomers=(code_col, "nunique"))

    summary = (
        current
        .merge(previous,   on="Branch", how="left")
        .merge(new_branch, on="Branch", how="left")
        .fillna(0)
    )
    summary["Revenue (Cr)"] = (summary["Revenue"] / 10_000_000).round(2)
    summary["Growth %"]     = summary.apply(lambda r: growth_percentage(r["Revenue"], r["PrevRevenue"]), axis=1)
    summary = summary.sort_values("Revenue", ascending=False).head(10)
    summary = summary.rename(columns={
        "Customers":    customer_label + "s",
        "NewCustomers": f"New {customer_label}s",
    })

    st.markdown("<div class='section-header'>Top 10 Branch Performance</div>", unsafe_allow_html=True)
    styled = (
        summary[["Branch", "Revenue (Cr)", customer_label + "s", f"New {customer_label}s", "Growth %"]]
        .style
        .format({
            "Revenue (Cr)":             "{:.2f}",
            customer_label + "s":       "{:,.0f}",
            f"New {customer_label}s":   "{:,.0f}",
            "Growth %":                 "{:.1f}%",
        })
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{
            "selector": "th",
            "props": [("text-align", "center"), ("font-weight", "bold"), ("background-color", "#F8FAFC")],
        }])
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)


# =====================================================
# Drilldown Tab
# =====================================================
def render_drilldown_tab(df: pd.DataFrame, name_col: str, customer_label: str) -> None:
    st.subheader(f"{customer_label} Drill Down")
    customers = sorted(df[name_col].dropna().unique())
    if not customers:
        st.info(f"No {customer_label.lower()} available for drill down.")
        return

    selected_customer = st.selectbox(f"Select {customer_label} for Detail", customers)
    customer_df = df[df[name_col] == selected_customer]

    total_shipments          = customer_df["ShipmentCount"].sum()
    total_revenue            = customer_df["Revenue"].sum()
    total_weight             = customer_df["ChargeWeight"].sum()
    avg_revenue_per_shipment = total_revenue / total_shipments if total_shipments > 0 else 0

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Total Shipments",        f"{total_shipments:,.0f}")
    d2.metric("Revenue",                money_cr(total_revenue))
    d3.metric("Charge Weight",          f"{total_weight:,.0f}")
    d4.metric("Avg Revenue / Shipment", f"Rs.{avg_revenue_per_shipment:,.0f}")
    st.dataframe(customer_df, use_container_width=True, hide_index=True)


# =====================================================
# Main Dashboard
# =====================================================
def show_CustomerAnalysis() -> None:
    apply_dashboard_style()

    fin_year, view_type = render_main_filters()
    if fin_year == "Select FY":
        st.info("Please select a Financial Year to continue.")
        return

    config         = get_customer_config(view_type)
    code_col       = config["code_col"]
    name_col       = config["name_col"]
    customer_label = config["label"]

    start_date, end_date = get_date_range(fin_year)
    prev_start, prev_end = get_date_range(previous_financial_year(fin_year, 1))
    old_start,  old_end  = get_date_range(previous_financial_year(fin_year, 2))

    with st.spinner("Loading customer summary data..."):
        all_df = clean_booking_data(load_booking_data(old_start, end_date, view_type))

    df      = all_df[all_df["YR"].astype(int) == int(fin_year.split("-")[0])].copy()
    prev_df = all_df[all_df["YR"].astype(int) == int(previous_financial_year(fin_year, 1).split("-")[0])].copy()
    old_df  = all_df[all_df["YR"].astype(int) == int(previous_financial_year(fin_year, 2).split("-")[0])].copy()

    if df.empty:
        st.warning("No customer data found.")
        return

    required_cols = [code_col, name_col, "Zone", "Branch", "FIN_MONTH",
                     "Revenue", "ShipmentCount", "ActualWeight", "ChargeWeight",
                     "AvgDelayDays", "MaxDelayDays"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        st.error(f"Missing columns: {missing_cols}")
        st.write("Available columns:", list(df.columns))
        return

    zone, circle, branch, load_type, customer, export_placeholder = render_data_filters(
        df, customer_label, name_col
    )

    df      = apply_filters(df,      zone, circle, branch, load_type, customer, name_col)
    prev_df = apply_filters(prev_df, zone, circle, branch, load_type, customer, name_col)
    old_df  = apply_filters(old_df,  zone, circle, branch, load_type, customer, name_col)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    st.divider()

    # --- Customer sets ---
    current_customers    = set(df[code_col].dropna().unique())
    previous_customers   = set(prev_df[code_col].dropna().unique())
    older_customers      = set(old_df[code_col].dropna().unique())
    new_customer_codes         = current_customers - previous_customers
    lost_customer_codes        = previous_customers - current_customers
    reactivated_customer_codes = (current_customers & older_customers) - previous_customers

    active_customers      = len(current_customers)
    prev_active_customers = len(previous_customers)
    new_customers         = len(new_customer_codes)
    lost_customers        = len(lost_customer_codes)
    reactivated_customers = len(reactivated_customer_codes)
    total_revenue         = df["Revenue"].sum()
    prev_revenue          = prev_df["Revenue"].sum()

    customer_summary = build_customer_summary(df, prev_df, code_col, name_col)
    monthly          = build_monthly_summary(df, code_col)
    service_df       = build_service_summary(df, code_col, name_col)

    reactivated_df = customer_summary[customer_summary[code_col].isin(reactivated_customer_codes)].copy()
    if not reactivated_df.empty:
        reactivated_df["Revenue Cr"]          = (reactivated_df["revenue"]      / 10_000_000).round(2)
        reactivated_df["Previous Revenue Cr"] = (reactivated_df["prev_revenue"] / 10_000_000).round(2)

    growth_df = customer_summary.copy()
    growth_df["Customer Status"] = "Existing"
    growth_df.loc[growth_df[code_col].isin(new_customer_codes),         "Customer Status"] = "New"
    growth_df.loc[growth_df[code_col].isin(reactivated_customer_codes), "Customer Status"] = "Reactivated"

    at_risk_customers = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] < customer_summary["prev_revenue"] * 0.75)
    ][code_col].nunique()

    revenue_from_new_customers = df[df[code_col].isin(new_customer_codes)]["Revenue"].sum()
    lost_revenue               = prev_df[prev_df[code_col].isin(lost_customer_codes)]["Revenue"].sum()
    reactivated_revenue        = df[df[code_col].isin(reactivated_customer_codes)]["Revenue"].sum()
    charged_weight             = df["ChargeWeight"].sum()
    current_yield              = total_revenue / charged_weight if charged_weight > 0 else 0
    retention_percent          = (
        ((active_customers - new_customers) / prev_active_customers) * 100
        if prev_active_customers > 0 else 0
    )

    metrics = {
        "active_customers":           active_customers,
        "new_customers":              new_customers,
        "lost_customers":             lost_customers,
        "reactivated_customers":      reactivated_customers,
        "at_risk_customers":          at_risk_customers,
        "total_revenue":              total_revenue,
        "prev_revenue":               prev_revenue,
        "active_growth":              growth_percentage(active_customers, prev_active_customers),
        "revenue_growth":             growth_percentage(total_revenue, prev_revenue),
        "retention_percent":          retention_percent,
        "revenue_from_new_customers": revenue_from_new_customers,
        "lost_revenue":               lost_revenue,
        "reactivated_revenue":        reactivated_revenue,
        "current_yield":              current_yield,
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
            label="Export to Excel",
            data=excel_file,
            file_name=f"customer_analysis_{view_type}_{fin_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # --- KPIs ---
    render_kpis(metrics, customer_label)

    st.divider()

    # --- Main 3-column layout: Zone | Revenue Bridge | Branch ---
    # Equal width [1, 1, 1] so all three sections align perfectly
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        render_zone_summary_table(df, prev_df, code_col, customer_label)
    with c2:
        render_revenue_bridge(metrics, customer_label)
    with c3:
        render_branch_summary_table(df, prev_df, code_col, customer_label)

    st.divider()

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs([
        f"{customer_label} Overview",
        "Growth & Retention",
        "Service Performance",
        f"{customer_label} Drill Down",
    ])
    with tab1:
        render_overview_tab(customer_summary, monthly, code_col, name_col, customer_label, prev_df, lost_customer_codes)
    with tab2:
        render_growth_tab(growth_df, name_col, customer_label)
    with tab3:
        render_service_tab(service_df, customer_label)
    with tab4:
        render_drilldown_tab(df, name_col, customer_label)
