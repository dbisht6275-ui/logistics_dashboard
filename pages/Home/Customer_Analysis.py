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
        /* ---------- Page spacing ---------- */
        .block-container {
            padding-top: 1.15rem !important;
            padding-bottom: 2rem !important;
        }

        /* ---------- Dashboard Heading ---------- */
        .dashboard-header {
            margin: 0 0 1rem 0;
            padding: 0;
        }
        .dashboard-title {
            margin: 0;
            color: #0f172a;
            font-size: 30px;
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.4px;
        }
        .dashboard-subtitle {
            margin-top: 6px;
            color: #64748b;
            font-size: 14px;
            font-weight: 400;
        }

        /* ---------- Gradient KPI Cards ---------- */
        .kpi-card {
            border: 1px solid rgba(255,255,255,0.20);
            border-radius: 14px;
            padding: 16px 17px;
            min-height: 118px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 8px 20px rgba(15,23,42,0.14);
            position: relative;
            overflow: hidden;
            color: #ffffff;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 26px rgba(15,23,42,0.18);
        }
        .kpi-card::before {
            content: "";
            position: absolute;
            width: 90px;
            height: 90px;
            border-radius: 50%;
            right: -28px;
            top: -34px;
            background: rgba(255,255,255,0.12);
        }
        .kpi-card::after {
            content: "";
            position: absolute;
            width: 62px;
            height: 62px;
            border-radius: 50%;
            right: 18px;
            bottom: -34px;
            background: rgba(255,255,255,0.08);
        }
        .kpi-title {
            font-size: 11px;
            font-weight: 700;
            color: rgba(255,255,255,0.88);
            text-transform: uppercase;
            letter-spacing: 0.45px;
            margin-bottom: 8px;
            position: relative;
            z-index: 2;
            padding-right: 28px;
        }
        .kpi-value {
            font-size: 22px;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.2;
            position: relative;
            z-index: 2;
            white-space: nowrap;
        }
        .kpi-delta {
            font-size: 11px;
            color: rgba(255,255,255,0.82);
            margin-top: 6px;
            position: relative;
            z-index: 2;
        }
        .kpi-icon {
            position: absolute;
            top: 14px;
            right: 15px;
            font-size: 22px;
            opacity: 0.96;
            z-index: 3;
            filter: drop-shadow(0 2px 3px rgba(0,0,0,0.12));
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
        

        /* ---------- Compact layout overrides: aligned with Overview ---------- */
        .block-container {
            max-width: 100% !important;
            padding: 0.35rem 0.75rem 0.75rem !important;
        }
        .block-container > div:first-child {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        div[data-testid="stVerticalBlock"] {
            gap: 0.35rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.50rem !important;
            align-items: flex-start !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 11px !important;
            box-shadow: 0 3px 10px rgba(15,42,67,0.07) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.55rem 0.65rem !important;
        }

        /* ---------- Compact heading card ---------- */
        .dashboard-header {
            margin: 0 !important;
            padding: 2px 0 3px 4px !important;
        }
        .dashboard-title {
            margin: 0 !important;
            color: #102a43 !important;
            font-size: 19px !important;
            font-weight: 850 !important;
            line-height: 1.15 !important;
            letter-spacing: -0.3px !important;
        }
        .dashboard-subtitle {
            margin-top: 2px !important;
            color: #64748b !important;
            font-size: 11px !important;
            font-weight: 400 !important;
        }

        /* ---------- Compact filters and controls ---------- */
        div[data-testid="stSelectbox"] {
            padding: 2px 3px 4px !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            overflow: visible !important;
        }
        div[data-baseweb="select"] > div {
            min-height: 34px !important;
        }
        .stDownloadButton > button {
            min-height: 34px !important;
            border-radius: 9px !important;
            font-size: 12px !important;
            font-weight: 750 !important;
            white-space: nowrap !important;
        }

        /* ---------- Compact KPI row ---------- */
        .kpi-card {
            min-height: 104px !important;
            padding: 12px 14px !important;
            border-radius: 13px !important;
            box-shadow: 0 5px 14px rgba(15,23,42,0.13) !important;
        }
        .kpi-title {
            margin-bottom: 5px !important;
            font-size: 10px !important;
        }
        .kpi-value {
            font-size: 20px !important;
        }
        .kpi-delta {
            margin-top: 4px !important;
            font-size: 10px !important;
        }
        .kpi-icon {
            top: 11px !important;
            right: 12px !important;
            font-size: 20px !important;
        }

        /* ---------- Compact insight sections ---------- */
        hr {
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
        }
        .section-header {
            margin-top: 0 !important;
            margin-bottom: 0.25rem !important;
        }
        [data-testid="stDataFrame"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        [data-testid="stPlotlyChart"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        div[data-testid="stTabs"] {
            margin-top: 0 !important;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.35rem !important;
        }
        h1, h2, h3, h4, h5, h6 {
            margin-top: 0.10rem !important;
            margin-bottom: 0.25rem !important;
        }

        @media (max-width: 1500px) {
            .block-container {
                padding-left: 0.45rem !important;
                padding-right: 0.45rem !important;
            }
            div[data-testid="stHorizontalBlock"] {
                gap: 0.35rem !important;
            }
            .dashboard-title {
                font-size: 18px !important;
            }
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

MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
MONTH_MAP = {1: "Apr", 2: "May", 3: "Jun", 4: "Jul", 5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov", 9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"}
QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]
QUARTER_MAP = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2", 7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"}

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


def get_revenue_conversion(conversion_type: str):
    """Display-only conversion. All business calculations remain in rupees."""
    return (100_000, "Lac") if conversion_type == "Lac" else (10_000_000, "Cr")


def money_display(value: float, conversion_type: str) -> str:
    divisor, unit = get_revenue_conversion(conversion_type)
    return f"Rs.{value / divisor:.2f} {unit}"


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
    quarter: str,
    month: str,
    load_type: str,
    customer: str,
    customer_name_col: str,
) -> pd.DataFrame:
    filtered = df.copy()
    if zone      != "All" and "Zone"     in filtered.columns: filtered = filtered[filtered["Zone"]     == zone]
    if circle    != "All" and "Circle"   in filtered.columns: filtered = filtered[filtered["Circle"]   == circle]
    if branch    != "All" and "Branch"   in filtered.columns: filtered = filtered[filtered["Branch"]   == branch]
    if quarter   != "All" and "Quarter"  in filtered.columns: filtered = filtered[filtered["Quarter"]  == quarter]
    if month     != "All" and "Month"    in filtered.columns: filtered = filtered[filtered["Month"]    == month]
    if load_type != "All" and "LoadType" in filtered.columns: filtered = filtered[filtered["LoadType"] == load_type]
    if customer  != "All" and customer_name_col in filtered.columns:
        filtered = filtered[filtered[customer_name_col] == customer]
    return filtered


# =====================================================
# KPI Card  (accent bar color)
# =====================================================
def kpi_card(title: str, value: str, delta: str, icon: str, gradient: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card" style="background:{gradient};">
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


def build_monthly_summary(df: pd.DataFrame, code_col: str, conversion_type: str) -> pd.DataFrame:
    monthly = (
        df.groupby("FIN_MONTH", as_index=False)
        .agg(
            revenue=("Revenue", "sum"),
            shipments=("ShipmentCount", "sum"),
            customers=(code_col, "nunique"),
        )
        .sort_values("FIN_MONTH")
    )
    divisor, unit = get_revenue_conversion(conversion_type)
    monthly["Revenue Display"] = (monthly["revenue"] / divisor).round(2)
    monthly["Revenue Unit"] = unit
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
def render_dashboard_header():
    """Render the compact Overview-style heading and return the export placeholder."""
    with st.container(border=True):
        header_left, header_right = st.columns(
            [7, 1],
            gap="small",
            vertical_alignment="center",
        )

        with header_left:
            st.markdown(
                """
                <div class="dashboard-header">
                    <div class="dashboard-title">Customer Analysis</div>
                    <div class="dashboard-subtitle">
                        Analyze customer acquisition, retention, revenue and branch performance.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with header_right:
            export_placeholder = st.empty()

    return export_placeholder


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
    data_scope    = st.session_state.get("data_scope", {})
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

    # Same filter sequence used in Overview: geography -> period -> load -> customer -> conversion.
    f1, f2, f3, f4, f5, f6, f7, f8 = st.columns(
        [1, 1, 1, .85, .95, 1, 1.35, .9],
        gap="small",
    )

    with f1:
        if locked_zone:
            zone = locked_zone
            st.selectbox("Zone", [zone], disabled=True, key="customer_zone_locked")
        else:
            zone_list = ["All"] + (sorted(df["Zone"].dropna().unique()) if "Zone" in df.columns else [])
            zone = st.selectbox("Zone", zone_list, key="customer_zone")
    zone_df = df if zone == "All" else df[df["Zone"] == zone]

    with f2:
        if locked_circle:
            circle = locked_circle
            st.selectbox("Circle", [circle], disabled=True, key="customer_circle_locked")
        else:
            circle_list = ["All"] + (sorted(zone_df["Circle"].dropna().unique()) if "Circle" in zone_df.columns else [])
            circle = st.selectbox("Circle", circle_list, key="customer_circle")
    circle_df = zone_df if circle == "All" else zone_df[zone_df["Circle"] == circle]

    with f3:
        if locked_branch:
            branch = locked_branch
            st.selectbox("Branch", [branch], disabled=True, key="customer_branch_locked")
        else:
            branch_list = ["All"] + (sorted(circle_df["Branch"].dropna().unique()) if "Branch" in circle_df.columns else [])
            branch = st.selectbox("Branch", branch_list, key="customer_branch")
    branch_df = circle_df if branch == "All" else circle_df[circle_df["Branch"] == branch]

    with f4:
        available_quarters = [q for q in QUARTER_ORDER if q in branch_df["Quarter"].dropna().unique().tolist()]
        quarter = st.selectbox("Quarter", ["All"] + available_quarters, key="customer_quarter")
    quarter_df = branch_df if quarter == "All" else branch_df[branch_df["Quarter"] == quarter]

    with f5:
        available_months = [m for m in MONTH_ORDER if m in quarter_df["Month"].dropna().unique().tolist()]
        month = st.selectbox("Month", ["All"] + available_months, key="customer_month")
    month_df = quarter_df if month == "All" else quarter_df[quarter_df["Month"] == month]

    with f6:
        loadtype_list = ["All"] + (sorted(month_df["LoadType"].dropna().unique()) if "LoadType" in month_df.columns else [])
        load_type = st.selectbox("Load Type", loadtype_list, key="customer_loadtype")
    loadtype_df = month_df if load_type == "All" else month_df[month_df["LoadType"] == load_type]

    with f7:
        customer_list = ["All"] + (sorted(loadtype_df[customer_name_col].dropna().unique()) if customer_name_col in loadtype_df.columns else [])
        customer = st.selectbox(customer_label, customer_list, key="customer_name_filter")

    with f8:
        conversion_type = st.selectbox("Conversion", ["Crore", "Lac"], key="customer_conversion_type")

    return zone, circle, branch, quarter, month, load_type, customer, conversion_type


# =====================================================
# KPI Row  — 7 equal columns
# =====================================================
def render_kpis(metrics: dict, customer_label: str, conversion_type: str) -> None:
    cols = st.columns(7)

    cards = [
        (
            f"Active {customer_label}s",
            f"{metrics['active_customers']:,}",
            format_delta(metrics["active_growth"]),
            "👥",
            "linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)" if metrics["active_growth"] >= 0
            else "linear-gradient(135deg, #b91c1c 0%, #ef4444 100%)",
        ),
        (
            f"New {customer_label}s",
            f"{metrics['new_customers']:,}",
            "Current FY vs Previous FY",
            "🆕",
            "linear-gradient(135deg, #047857 0%, #22c55e 100%)",
        ),
        (
            f"Lost {customer_label}s",
            f"{metrics['lost_customers']:,}",
            "Previous FY not active now",
            "❌",
            "linear-gradient(135deg, #b91c1c 0%, #f43f5e 100%)",
        ),
        (
            "Reactivated Customers",
            f"{metrics['reactivated_customers']:,}",
            "Returned after inactive FY",
            "🔄",
            "linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%)",
        ),
        (
            f"At Risk {customer_label}s",
            f"{metrics['at_risk_customers']:,}",
            "Revenue dropped above 25%",
            "⚠️",
            "linear-gradient(135deg, #c2410c 0%, #f59e0b 100%)",
        ),
        (
            "Total Revenue",
            money_display(metrics["total_revenue"], conversion_type),
            format_delta(metrics["revenue_growth"]),
            "₹",
            "linear-gradient(135deg, #6d28d9 0%, #a855f7 100%)" if metrics["revenue_growth"] >= 0
            else "linear-gradient(135deg, #b91c1c 0%, #ef4444 100%)",
        ),
        (
            "Current Yield",
            f"₹{metrics['current_yield']:.2f} /Kg",
            "Revenue / Chg Wt",
            "⚡",
            "linear-gradient(135deg, #7e22ce 0%, #ec4899 100%)",
        ),
    ]

    for col, (title, value, delta, icon, gradient) in zip(cols, cards):
        with col:
            kpi_card(title, value, delta, icon, gradient)



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
    conversion_type: str,
) -> None:
    # --- Three equal chart columns ---
    c1, c2, c3 = st.columns(3)

    with c1:
        _, revenue_unit = get_revenue_conversion(conversion_type)
        fig = px.bar(
            monthly, x="FIN_MONTH", y="Revenue Display",
            text="Revenue Display", title=f"Month-wise Revenue ({revenue_unit})",
        )
        fig.update_traces(texttemplate=f"Rs.%{{text:.2f}} {revenue_unit}", textposition="outside")
        fig.update_yaxes(title=f"Revenue ({revenue_unit})")
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
            lambda r: f"{r['segment']:<10} {r['Contribution %']:.1f}% ({money_display(r['revenue'], conversion_type)})", axis=1
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
                text=f"Total<br>{money_display(total_seg_rev, conversion_type)}",
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
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
    current_revenue_col = f"Revenue ({revenue_unit})"
    previous_revenue_col = f"PY Revenue ({revenue_unit})"
    lost_revenue_col = f"Lost Revenue ({revenue_unit})"
    top_growing[current_revenue_col] = (top_growing["revenue"] / revenue_divisor).round(2)
    top_growing[previous_revenue_col] = (top_growing["prev_revenue"] / revenue_divisor).round(2)
    top_growing["Growth % vs PY"]   = top_growing["growth_%"].round(1)
    top_growing = top_growing.sort_values("Growth % vs PY", ascending=False).head(10)

    top_degrowing = customer_summary[
        (customer_summary["prev_revenue"] > 0) &
        (customer_summary["revenue"] < customer_summary["prev_revenue"]) &
        (customer_summary["revenue"] > 0)
    ].copy()
    top_degrowing[current_revenue_col] = (top_degrowing["revenue"] / revenue_divisor).round(2)
    top_degrowing[previous_revenue_col] = (top_degrowing["prev_revenue"] / revenue_divisor).round(2)
    top_degrowing["Drop % vs PY"]    = top_degrowing["growth_%"].round(1)
    top_degrowing = top_degrowing.sort_values("Drop % vs PY", ascending=True).head(10)

    lost_summary = (
        prev_df[prev_df[code_col].isin(lost_customer_codes)]
        .groupby([code_col, name_col], as_index=False)
        .agg(lost_revenue=("Revenue", "sum"), last_CN_month=("FIN_MONTH", "max"))
    )
    # FIX: was /100 — corrected to /10_000_000
    lost_summary[lost_revenue_col] = (lost_summary["lost_revenue"] / revenue_divisor).round(2)
    top_lost = lost_summary.sort_values("lost_revenue", ascending=False).head(10)

    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown(f"<div class='section-header'>Top 10 Growing {customer_label}s</div>", unsafe_allow_html=True)
        st.dataframe(
            top_growing[[name_col, current_revenue_col, previous_revenue_col, "Growth % vs PY"]],
            use_container_width=True, hide_index=True,
        )
    with t2:
        st.markdown(f"<div class='section-header'>Top 10 De-growing {customer_label}s</div>", unsafe_allow_html=True)
        st.dataframe(
            top_degrowing[[name_col, current_revenue_col, previous_revenue_col, "Drop % vs PY"]],
            use_container_width=True, hide_index=True,
        )
    with t3:
        st.markdown(f"<div class='section-header'>Top 10 Lost {customer_label}s</div>", unsafe_allow_html=True)
        st.dataframe(
            top_lost[[name_col, lost_revenue_col, "last_CN_month"]],
            use_container_width=True, hide_index=True,
        )


# =====================================================
# Growth Tab
# =====================================================
def render_growth_tab(growth_df: pd.DataFrame, name_col: str, customer_label: str, conversion_type: str) -> None:
    st.subheader(f"{customer_label} Growth / Degrowth")
    display_df = growth_df.copy()
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
    revenue_col = f"Revenue ({revenue_unit})"
    previous_col = f"Previous Revenue ({revenue_unit})"
    display_df[revenue_col] = (display_df["revenue"] / revenue_divisor).round(2)
    display_df[previous_col] = (display_df["prev_revenue"] / revenue_divisor).round(2)
    st.dataframe(
        display_df[[
            name_col, revenue_col, previous_col, "growth_%",
            "Customer Status", "shipments", "actual_weight", "charge_weight",
            "avg_delay", "max_delay",
        ]].sort_values("growth_%", ascending=True),
        use_container_width=True, hide_index=True,
    )


# =====================================================
# Service Tab
# =====================================================
def render_service_tab(service_df: pd.DataFrame, customer_label: str, conversion_type: str) -> None:
    st.subheader(f"{customer_label} Service Performance")
    display_df = service_df.copy()
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
    display_df[f"Revenue ({revenue_unit})"] = (display_df["revenue"] / revenue_divisor).round(2)
    st.dataframe(
        display_df.sort_values("avg_delay_days", ascending=False),
        use_container_width=True, hide_index=True,
    )


# =====================================================
# Revenue Bridge
# =====================================================
def render_revenue_bridge(metrics: dict, customer_label: str, conversion_type: str) -> None:
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
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
    fig = px.bar(
        bridge_df,
        x="Metric",
        y=bridge_df["Value"] / revenue_divisor,
        text=(bridge_df["Value"] / revenue_divisor).round(2),
        title="Revenue Bridge",
    )
    fig.update_traces(texttemplate=f"Rs. %{{text:.2f}} {revenue_unit}", textposition="outside")
    fig.update_yaxes(title=f"Revenue ({revenue_unit})")
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
    conversion_type: str,
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
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
    revenue_col = f"Revenue ({revenue_unit})"
    zone_summary[revenue_col] = (zone_summary["Revenue"] / revenue_divisor).round(2)
    zone_summary["Growth %"]     = zone_summary.apply(
        lambda r: growth_percentage(r["Revenue"], r["Prev_Revenue"]), axis=1
    )
    zone_summary = zone_summary.rename(columns={"Active_Customers": f"Active {customer_label}s"})

    display_df = zone_summary[["Zone", f"Active {customer_label}s", "New", "Lost", revenue_col, "Growth %"]].copy()
    total_row = {
        "Zone":                       "Total",
        f"Active {customer_label}s":  int(display_df[f"Active {customer_label}s"].sum()),
        "New":                        int(display_df["New"].sum()),
        "Lost":                       int(display_df["Lost"].sum()),
        revenue_col:                   round(display_df[revenue_col].sum(), 2),
        "Growth %":                   growth_percentage(zone_summary["Revenue"].sum(), zone_summary["Prev_Revenue"].sum()),
    }
    display_df = pd.concat([display_df, pd.DataFrame([total_row])], ignore_index=True)

    st.markdown(f"<div class='section-header'>Zone-wise {customer_label} Summary</div>", unsafe_allow_html=True)
    st.dataframe(
        display_df.style.format({
            f"Active {customer_label}s": "{:,.0f}",
            "New":          "{:,.0f}",
            "Lost":         "{:,.0f}",
            revenue_col:   "{:,.2f}",
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
    conversion_type: str,
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
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
    revenue_col = f"Revenue ({revenue_unit})"
    summary[revenue_col] = (summary["Revenue"] / revenue_divisor).round(2)
    summary["Growth %"]     = summary.apply(lambda r: growth_percentage(r["Revenue"], r["PrevRevenue"]), axis=1)
    summary = summary.sort_values("Revenue", ascending=False).head(10)
    summary = summary.rename(columns={
        "Customers":    customer_label + "s",
        "NewCustomers": f"New {customer_label}s",
    })

    st.markdown("<div class='section-header'>Top 10 Branch Performance</div>", unsafe_allow_html=True)
    styled = (
        summary[["Branch", revenue_col, customer_label + "s", f"New {customer_label}s", "Growth %"]]
        .style
        .format({
            revenue_col:                 "{:.2f}",
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
def render_drilldown_tab(df: pd.DataFrame, name_col: str, customer_label: str, conversion_type: str) -> None:
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
    d2.metric("Revenue",                money_display(total_revenue, conversion_type))
    d3.metric("Charge Weight",          f"{total_weight:,.0f}")
    d4.metric("Avg Revenue / Shipment", f"Rs.{avg_revenue_per_shipment:,.0f}")
    st.dataframe(customer_df, use_container_width=True, hide_index=True)


# =====================================================
# Main Dashboard
# =====================================================
def show_CustomerAnalysis() -> None:
    apply_dashboard_style()
    export_placeholder = render_dashboard_header()

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

    # Display/filter helper columns. FIN_MONTH remains the source of truth.
    for period_df in (df, prev_df, old_df):
        period_df["Month"] = period_df["FIN_MONTH"].map(MONTH_MAP)
        period_df["Quarter"] = period_df["FIN_MONTH"].map(QUARTER_MAP)

    required_cols = [code_col, name_col, "Zone", "Branch", "FIN_MONTH",
                     "Revenue", "ShipmentCount", "ActualWeight", "ChargeWeight",
                     "AvgDelayDays", "MaxDelayDays"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        st.error(f"Missing columns: {missing_cols}")
        st.write("Available columns:", list(df.columns))
        return

    zone, circle, branch, quarter, month, load_type, customer, conversion_type = render_data_filters(
        df, customer_label, name_col
    )

    df      = apply_filters(df,      zone, circle, branch, quarter, month, load_type, customer, name_col)
    prev_df = apply_filters(prev_df, zone, circle, branch, quarter, month, load_type, customer, name_col)
    old_df  = apply_filters(old_df,  zone, circle, branch, quarter, month, load_type, customer, name_col)

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
    monthly          = build_monthly_summary(df, code_col, conversion_type)
    service_df       = build_service_summary(df, code_col, name_col)

    reactivated_df = customer_summary[customer_summary[code_col].isin(reactivated_customer_codes)].copy()
    if not reactivated_df.empty:
        revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
        reactivated_df[f"Revenue ({revenue_unit})"] = (reactivated_df["revenue"] / revenue_divisor).round(2)
        reactivated_df[f"Previous Revenue ({revenue_unit})"] = (reactivated_df["prev_revenue"] / revenue_divisor).round(2)

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
            key="customer_analysis_export_excel",
            help="Download the filtered customer analysis data.",
            use_container_width=True,
        )

    # --- KPIs ---
    render_kpis(metrics, customer_label, conversion_type)

    st.divider()

    # --- Main 3-column layout: Zone | Revenue Bridge | Branch ---
    # Equal width [1, 1, 1] so all three sections align perfectly
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        render_zone_summary_table(df, prev_df, code_col, customer_label, conversion_type)
    with c2:
        render_revenue_bridge(metrics, customer_label, conversion_type)
    with c3:
        render_branch_summary_table(df, prev_df, code_col, customer_label, conversion_type)

    st.divider()

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs([
        f"{customer_label} Overview",
        "Growth & Retention",
        "Service Performance",
        f"{customer_label} Drill Down",
    ])
    with tab1:
        render_overview_tab(customer_summary, monthly, code_col, name_col, customer_label, prev_df, lost_customer_codes, conversion_type)
    with tab2:
        render_growth_tab(growth_df, name_col, customer_label, conversion_type)
    with tab3:
        render_service_tab(service_df, customer_label, conversion_type)
    with tab4:
        render_drilldown_tab(df, name_col, customer_label, conversion_type)
