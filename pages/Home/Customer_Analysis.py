import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime, timedelta
from functools import lru_cache
from services.data_CustomerAnalysis import load_booking_data, get_date_range

# =====================================================
# Configuration & Constants
# =====================================================
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

COLOR_POSITIVE = "#16a34a"
COLOR_NEGATIVE = "#dc2626"
COLORS = {"positive": COLOR_POSITIVE, "negative": COLOR_NEGATIVE, "neutral": "#2563eb"}

COLUMN_RENAME_MAP = {
    "zone": "Zone", "circle": "Circle", "branch": "Branch",
    "consignor": "Consignor", "consignee": "Consignee", "cngecode": "ConsigneeCode",
    "shipmentcount": "ShipmentCount", "actualweight": "ActualWeight",
    "chargeweight": "ChargeWeight", "revenue": "Revenue",
    "avgdelaydays": "AvgDelayDays", "maxdelaydays": "MaxDelayDays",
    "loadtype": "LoadType", "fin_month": "FIN_MONTH", "yr": "YR",
}

NUMERIC_COLUMNS = [
    "YR", "FIN_MONTH", "ShipmentCount", "ActualWeight",
    "ChargeWeight", "Revenue", "AvgDelayDays", "MaxDelayDays",
]

REQUIRED_COLUMNS = [
    "Zone", "Circle", "Branch", "FIN_MONTH", "Revenue",
    "ShipmentCount", "ActualWeight", "ChargeWeight",
    "AvgDelayDays", "MaxDelayDays",
]


# =====================================================
# Page Styling
# =====================================================
def apply_dashboard_style() -> None:
    """Apply comprehensive dashboard styling with responsive design."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.15rem !important;
            padding-bottom: 2rem !important;
            max-width: 100% !important;
            padding: 0.35rem 0.75rem 0.75rem !important;
        }

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

        .kpi-card {
            border: 1px solid rgba(255,255,255,0.20);
            border-radius: 12px !important;
            padding: 9px 12px !important;
            min-height: 92px !important;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(15,23,42,0.12) !important;
            position: relative;
            overflow: hidden;
            color: #ffffff;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 26px rgba(15,23,42,0.18) !important;
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
            font-size: 9.5px !important;
            font-weight: 700;
            color: rgba(255,255,255,0.88);
            text-transform: uppercase;
            letter-spacing: 0.45px;
            margin-bottom: 3px !important;
            position: relative;
            z-index: 2;
            line-height: 1.15 !important;
        }
        .kpi-value {
            font-size: 18px !important;
            font-weight: 800;
            color: #ffffff;
            line-height: 1.12 !important;
            position: relative;
            z-index: 2;
            white-space: nowrap;
        }
        .kpi-delta {
            font-size: 10px !important;
            color: rgba(255,255,255,0.82);
            margin-top: 3px !important;
            position: relative;
            z-index: 2;
            line-height: 1.15 !important;
        }
        .kpi-icon {
            position: absolute;
            top: 11px !important;
            right: 12px !important;
            font-size: 20px !important;
            opacity: 0.96;
            z-index: 3;
            filter: drop-shadow(0 2px 3px rgba(0,0,0,0.12));
        }

        .section-header {
            font-size: 14px;
            font-weight: 700;
            color: #1e293b;
            margin-bottom: 6px;
            padding-bottom: 4px;
            border-bottom: 2px solid #e2e8f0;
        }

        div[data-testid="stHorizontalBlock"] > div {
            align-items: flex-end !important;
        }

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

        div[data-testid="stDataFrame"] {
            border-radius: 8px;
            overflow: hidden;
        }
        div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] * {
            font-size: 11px !important;
        }
        div[data-testid="stDataFrame"] thead tr th {
            font-size: 11px !important;
            font-weight: 700 !important;
            padding: 4px 6px !important;
        }
        div[data-testid="stDataFrame"] tbody tr td {
            font-size: 11px !important;
            padding: 3px 6px !important;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.35rem !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 0.50rem !important;
            align-items: flex-start !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 11px !important;
            box-shadow: 0 3px 10px rgba(15,42,67,0.07) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.55rem 0.65rem !important;
        }

        hr {
            margin-top: 0.35rem !important;
            margin-bottom: 0.35rem !important;
        }

        [data-testid="stDataFrame"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        [data-testid="stPlotlyChart"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }

        .kpi-row-spacer {
            height: 14px;
            width: 100%;
            clear: both;
        }
        .insight-section-spacer {
            height: 6px;
            width: 100%;
            clear: both;
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
# Helper Functions - Data Processing
# =====================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names with validation."""
    if df.empty:
        return df
    
    df = df.copy()
    for col in list(df.columns):
        lower_col = col.lower()
        if lower_col in COLUMN_RENAME_MAP:
            df = df.rename(columns={col: COLUMN_RENAME_MAP[lower_col]})
    return df


def clean_booking_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate booking data."""
    if df.empty:
        return df
    
    df = normalize_columns(df)
    
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(0)
    
    # Remove negative values for business metrics (except potential revenue adjustments)
    for col in ["ShipmentCount", "ActualWeight", "ChargeWeight"]:
        if col in df.columns:
            df[col] = df[col].clip(lower=0)
    
    return df


def validate_required_columns(df: pd.DataFrame, code_col: str, name_col: str) -> tuple[bool, list]:
    """Validate that all required columns exist in the dataframe."""
    required = REQUIRED_COLUMNS + [code_col, name_col]
    missing = [col for col in required if col not in df.columns]
    return len(missing) == 0, missing


def get_revenue_conversion(conversion_type: str) -> tuple[float, str]:
    """Get revenue conversion divisor and unit."""
    return (100_000, "Lac") if conversion_type == "Lac" else (10_000_000, "Cr")


def money_display(value: float, conversion_type: str) -> str:
    """Format money value with unit."""
    divisor, unit = get_revenue_conversion(conversion_type)
    return f"Rs.{value / divisor:.2f} {unit}"


def growth_percentage(current: float, previous: float) -> float:
    """Calculate growth percentage safely."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def format_delta(value: float) -> str:
    """Format delta as percentage string."""
    arrow = "↑" if value >= 0 else "↓"
    sign = "+" if value >= 0 else ""
    return f"{arrow} {sign}{value:.1f}% vs PY"


def previous_financial_year(fin_year: str, years_back: int = 1) -> str:
    """Calculate previous financial year."""
    try:
        start_year, end_year = map(int, fin_year.split("-"))
        return f"{start_year - years_back}-{end_year - years_back}"
    except ValueError:
        return fin_year


def get_customer_config(view_type: str) -> dict:
    """Get configuration based on view type."""
    configs = {
        "origin": {"code_col": "ConsignorCode", "name_col": "Consignor", "label": "Consignor"},
        "destination": {"code_col": "ConsigneeCode", "name_col": "Consignee", "label": "Consignee"},
    }
    return configs.get(view_type, configs["destination"])


def apply_filters(
    df: pd.DataFrame,
    zone: str = "All",
    circle: str = "All",
    branch: str = "All",
    quarter: str = "All",
    month: str = "All",
    load_type: str = "All",
    customer: str = "All",
    customer_name_col: str = "Consignee",
) -> pd.DataFrame:
    """Apply multiple filters to dataframe."""
    filtered = df.copy()
    
    filters = {
        "Zone": zone,
        "Circle": circle,
        "Branch": branch,
        "Quarter": quarter,
        "Month": month,
        "LoadType": load_type,
    }
    
    for col, filter_val in filters.items():
        if filter_val != "All" and col in filtered.columns:
            filtered = filtered[filtered[col] == filter_val]
    
    if customer != "All" and customer_name_col in filtered.columns:
        filtered = filtered[filtered[customer_name_col] == customer]
    
    return filtered


# =====================================================
# KPI Card Component
# =====================================================
def kpi_card(title: str, value: str, delta: str, icon: str, gradient: str) -> None:
    """Render a styled KPI card."""
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
# Data Export
# =====================================================
def export_to_excel(
    df: pd.DataFrame,
    customer_summary: pd.DataFrame,
    growth_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
    reactivated_df: pd.DataFrame,
    service_df: pd.DataFrame,
) -> BytesIO:
    """Export multiple dataframes to Excel with formatting."""
    output = BytesIO()
    
    try:
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
                {"bold": True, "bg_color": "#1f2937", "font_color": "white", "border": 1}
            )
            number_format = workbook.add_format({"num_format": "#,##0.00"})
            
            for sheet_name, sheet_df in sheets.items():
                sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                worksheet = writer.sheets[sheet_name]
                worksheet.freeze_panes(1, 0)
                
                for col_num, col_name in enumerate(sheet_df.columns):
                    worksheet.write(0, col_num, col_name, header_format)
                    worksheet.set_column(col_num, col_num, 20)
        
        output.seek(0)
        return output
    except Exception as e:
        st.error(f"Excel export failed: {str(e)}")
        return None


# =====================================================
# Data Aggregation Functions
# =====================================================
def build_customer_summary(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    name_col: str,
) -> pd.DataFrame:
    """Build comprehensive customer summary with growth metrics."""
    if df.empty:
        return pd.DataFrame()
    
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
        .reset_index(drop=True)
    )
    
    if prev_df.empty:
        current_summary["prev_revenue"] = 0
    else:
        previous_summary = (
            prev_df.groupby(code_col, as_index=False)
            .agg(prev_revenue=("Revenue", "sum"))
        )
        current_summary = current_summary.merge(previous_summary, on=code_col, how="left")
        current_summary["prev_revenue"] = current_summary["prev_revenue"].fillna(0)
    
    current_summary["revenue_change"] = current_summary["revenue"] - current_summary.get("prev_revenue", 0)
    current_summary["growth_%"] = current_summary.apply(
        lambda row: growth_percentage(row["revenue"], row.get("prev_revenue", 0)), axis=1
    )
    
    return current_summary


def build_monthly_summary(df: pd.DataFrame, code_col: str, conversion_type: str) -> pd.DataFrame:
    """Build monthly aggregation with revenue conversion."""
    if df.empty:
        return pd.DataFrame()
    
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
    """Build service performance summary."""
    if df.empty:
        return pd.DataFrame()
    
    service = (
        df.groupby([code_col, name_col], as_index=False)
        .agg(
            shipments=("ShipmentCount", "sum"),
            avg_delay_days=("AvgDelayDays", "mean"),
            max_delay_days=("MaxDelayDays", "max"),
            revenue=("Revenue", "sum"),
        )
        .reset_index(drop=True)
    )
    
    service["avg_delay_days"] = service["avg_delay_days"].round(2)
    service["max_delay_days"] = service["max_delay_days"].round(2)
    
    return service


def add_customer_segments(customer_summary: pd.DataFrame) -> pd.DataFrame:
    """Add ABC/RFM style customer segmentation."""
    if customer_summary.empty:
        customer_summary["segment"] = ""
        return customer_summary
    
    segmented = customer_summary.copy().sort_values("revenue", ascending=False)
    total_revenue = segmented["revenue"].sum()
    
    if total_revenue == 0:
        segmented["segment"] = "No Revenue"
        return segmented
    
    segmented["revenue_share"] = segmented["revenue"] / total_revenue
    segmented["cum_revenue_share"] = segmented["revenue_share"].cumsum()

    def assign_segment(cum_share: float) -> str:
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

    segmented["segment"] = segmented["cum_revenue_share"].apply(assign_segment)
    return segmented


# =====================================================
# UI Components
# =====================================================
def render_dashboard_header() -> object:
    """Render header with export placeholder."""
    with st.container(border=True):
        header_left, header_right = st.columns([7, 1], gap="small", vertical_alignment="center")

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


def render_filter_row_start() -> tuple:
    """Create filter layout and return columns with FY and view type."""
    filter_columns = st.columns(
        [1.10, 1.00, 0.82, 0.92, 1.00, 0.72, 0.82, 0.92, 1.25, 0.82],
        gap="small",
    )

    with filter_columns[0]:
        fin_year = st.selectbox(
            "Financial Year",
            FINANCIAL_YEARS,
            key="customer_financial_year",
        )

    with filter_columns[1]:
        view_type = st.selectbox(
            "View Type",
            ["destination", "origin"],
            format_func=lambda x: "Destination" if x == "destination" else "Origin",
            key="customer_view_type",
        )

    return filter_columns, fin_year, view_type


def render_data_filters(
    df: pd.DataFrame,
    customer_label: str,
    customer_name_col: str,
    filter_columns,
) -> tuple:
    """Render cascading filters with proper data isolation."""
    data_scope = st.session_state.get("data_scope", {})
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    # Resolve locked values to their parent hierarchy
    if locked_branch and locked_branch in df.get("Branch", []):
        branch_data = df[df["Branch"] == locked_branch]
        if not branch_data.empty:
            locked_circle = branch_data["Circle"].iloc[0]
            locked_zone = branch_data["Zone"].iloc[0]
    elif locked_circle and locked_circle in df.get("Circle", []):
        circle_data = df[df["Circle"] == locked_circle]
        if not circle_data.empty:
            locked_zone = circle_data["Zone"].iloc[0]

    f1, f2, f3, f4, f5, f6, f7, f8 = filter_columns[2:]

    # Zone Filter
    with f1:
        if locked_zone:
            zone = locked_zone
            st.selectbox("Zone", [zone], disabled=True, key="customer_zone_locked")
        else:
            zone_list = ["All"] + sorted(df["Zone"].dropna().unique().tolist())
            zone = st.selectbox("Zone", zone_list, key="customer_zone")
    
    zone_df = df if zone == "All" else df[df["Zone"] == zone]

    # Circle Filter
    with f2:
        if locked_circle:
            circle = locked_circle
            st.selectbox("Circle", [circle], disabled=True, key="customer_circle_locked")
        else:
            circle_list = ["All"] + sorted(zone_df["Circle"].dropna().unique().tolist())
            circle = st.selectbox("Circle", circle_list, key="customer_circle")
    
    circle_df = zone_df if circle == "All" else zone_df[zone_df["Circle"] == circle]

    # Branch Filter
    with f3:
        if locked_branch:
            branch = locked_branch
            st.selectbox("Branch", [branch], disabled=True, key="customer_branch_locked")
        else:
            branch_list = ["All"] + sorted(circle_df["Branch"].dropna().unique().tolist())
            branch = st.selectbox("Branch", branch_list, key="customer_branch")
    
    branch_df = circle_df if branch == "All" else circle_df[circle_df["Branch"] == branch]

    # Quarter Filter
    with f4:
        available_quarters = sorted([q for q in QUARTER_ORDER if q in branch_df["Quarter"].dropna().unique().tolist()])
        quarter = st.selectbox("Quarter", ["All"] + available_quarters, key="customer_quarter")
    
    quarter_df = branch_df if quarter == "All" else branch_df[branch_df["Quarter"] == quarter]

    # Month Filter
    with f5:
        available_months = sorted([m for m in MONTH_ORDER if m in quarter_df["Month"].dropna().unique().tolist()])
        month = st.selectbox("Month", ["All"] + available_months, key="customer_month")
    
    month_df = quarter_df if month == "All" else quarter_df[quarter_df["Month"] == month]

    # Load Type Filter
    with f6:
        loadtype_list = ["All"] + sorted(month_df["LoadType"].dropna().unique().tolist())
        load_type = st.selectbox("Load Type", loadtype_list, key="customer_loadtype")
    
    loadtype_df = month_df if load_type == "All" else month_df[month_df["LoadType"] == load_type]

    # Customer Filter
    with f7:
        customer_list = ["All"] + sorted(loadtype_df[customer_name_col].dropna().unique().tolist())
        customer = st.selectbox(customer_label, customer_list, key="customer_name_filter")

    # Conversion Type Filter
    with f8:
        conversion_type = st.selectbox("Conversion", ["Crore", "Lac"], key="customer_conversion_type")

    return zone, circle, branch, quarter, month, load_type, customer, conversion_type


# =====================================================
# KPI Rendering
# =====================================================
def render_kpis(metrics: dict, customer_label: str, conversion_type: str) -> None:
    """Render KPI cards with gradient backgrounds based on performance."""
    cols = st.columns(7, gap="small")

    kpi_data = [
        {
            "title": f"Active {customer_label}s",
            "value": f"{metrics['active_customers']:,}",
            "delta": format_delta(metrics["active_growth"]),
            "icon": "👥",
            "gradient": "linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)" if metrics["active_growth"] >= 0
                        else "linear-gradient(135deg, #b91c1c 0%, #ef4444 100%)",
        },
        {
            "title": f"New {customer_label}s",
            "value": f"{metrics['new_customers']:,}",
            "delta": "Current FY vs Previous FY",
            "icon": "🆕",
            "gradient": "linear-gradient(135deg, #047857 0%, #22c55e 100%)",
        },
        {
            "title": f"Lost {customer_label}s",
            "value": f"{metrics['lost_customers']:,}",
            "delta": "Previous FY not active now",
            "icon": "❌",
            "gradient": "linear-gradient(135deg, #be123c 0%, #f43f5e 100%)",
        },
        {
            "title": "Reactivated Customers",
            "value": f"{metrics['reactivated_customers']:,}",
            "delta": "Returned after inactive FY",
            "icon": "🔄",
            "gradient": "linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%)",
        },
        {
            "title": f"At Risk {customer_label}s",
            "value": f"{metrics['at_risk_customers']:,}",
            "delta": "Revenue dropped above 25%",
            "icon": "⚠️",
            "gradient": "linear-gradient(135deg, #c2410c 0%, #f59e0b 100%)",
        },
        {
            "title": "Total Revenue",
            "value": money_display(metrics["total_revenue"], conversion_type),
            "delta": format_delta(metrics["revenue_growth"]),
            "icon": "₹",
            "gradient": "linear-gradient(135deg, #6d28d9 0%, #a855f7 100%)" if metrics["revenue_growth"] >= 0
                        else "linear-gradient(135deg, #b91c1c 0%, #ef4444 100%)",
        },
        {
            "title": "Current Yield",
            "value": f"₹{metrics['current_yield']:.2f} /Kg",
            "delta": "Revenue / Chg Wt",
            "icon": "⚡",
            "gradient": "linear-gradient(135deg, #7e22ce 0%, #ec4899 100%)",
        },
    ]

    for col, kpi in zip(cols, kpi_data):
        with col:
            kpi_card(kpi["title"], kpi["value"], kpi["delta"], kpi["icon"], kpi["gradient"])

    st.markdown("<div class='kpi-row-spacer'></div>", unsafe_allow_html=True)


# =====================================================
# Chart Rendering Functions
# =====================================================
def render_overview_tab(
    customer_summary: pd.DataFrame,
    monthly: pd.DataFrame,
    code_col: str,
    name_col: str,
    customer_label: str,
    prev_df: pd.DataFrame,
    lost_customer_codes: set,
    conversion_type: str,
) -> None:
    """Render overview tab with revenue charts and customer analysis."""
    if customer_summary.empty or monthly.empty:
        st.warning("Insufficient data for overview analysis.")
        return

    c1, c2, c3 = st.columns(3, gap="small")

    # Monthly Revenue Chart
    with c1:
        with st.container(border=True):
            _, revenue_unit = get_revenue_conversion(conversion_type)
            fig = px.bar(
                monthly, x="FIN_MONTH", y="Revenue Display",
                text="Revenue Display", title=f"Month-wise Revenue ({revenue_unit})",
                color_discrete_sequence=["#2563eb"],
            )
            fig.update_traces(
                texttemplate=f"Rs.%{{text:.2f}} {revenue_unit}",
                textposition="outside",
            )
            fig.update_yaxes(title=f"Revenue ({revenue_unit})")
            fig.update_xaxes(title="Month")
            fig.update_layout(
                height=330, margin=dict(t=45, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Revenue Concentration Chart
    with c2:
        with st.container(border=True):
            revenue_rank = customer_summary.sort_values("revenue", ascending=False)
            total_revenue = revenue_rank["revenue"].sum()
            
            if total_revenue > 0:
                concentration_data = []
                for label, top_n in [("Top 10", 10), ("Top 20", 20), ("Top 50", 50), ("Top 100", 100)]:
                    top_rev = revenue_rank.head(top_n)["revenue"].sum()
                    pct = (top_rev / total_revenue * 100)
                    concentration_data.append({"Customer Group": label, "% of Total Revenue": pct})
                
                concentration_df = pd.DataFrame(concentration_data)
                fig = px.bar(
                    concentration_df,
                    x="% of Total Revenue", y="Customer Group",
                    orientation="h", text="% of Total Revenue",
                    title="Revenue Concentration",
                    color_discrete_sequence=["#059669"],
                )
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig.update_layout(
                    xaxis_title="% of Total Revenue", yaxis_title="",
                    height=330, margin=dict(t=45, b=20),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Customer Segmentation Chart
    with c3:
        with st.container(border=True):
            segmented = add_customer_segments(customer_summary)
            segment_order = ["Champions", "Loyal", "Potential", "At Risk", "Lost"]
            segment_colors = {
                "Champions": "#14946b", "Loyal": "#0f6ec7", "Potential": "#5ab0e8",
                "At Risk": "#f59e0b", "Lost": "#ef4444",
            }
            
            segment_df = segmented.groupby("segment", as_index=False).agg(revenue=("revenue", "sum"))
            total_seg_rev = segment_df["revenue"].sum()
            
            if total_seg_rev > 0:
                segment_df["Contribution %"] = (segment_df["revenue"] / total_seg_rev * 100).round(1)
                segment_df["Legend Label"] = segment_df.apply(
                    lambda r: f"{r['segment']} {r['Contribution %']:.1f}%", axis=1
                )
                segment_df["segment"] = pd.Categorical(
                    segment_df["segment"], categories=segment_order, ordered=True
                )
                segment_df = segment_df.sort_values("segment")
                
                fig = px.pie(
                    segment_df, names="Legend Label", values="revenue", hole=0.55,
                    title=f"{customer_label} Segmentation",
                    color="segment",
                    color_discrete_map=segment_colors,
                )
                fig.update_traces(textinfo="percent", textposition="inside")
                fig.update_layout(
                    height=330, margin=dict(t=45, b=5),
                    annotations=[dict(
                        text=f"Total<br>{money_display(total_seg_rev, conversion_type)}",
                        x=0.5, y=0.5, font_size=12, showarrow=False,
                    )],
                    legend=dict(
                        orientation="v", y=0.95, yanchor="top",
                        x=1.0, xanchor="left", font=dict(size=10)
                    ),
                    legend_title_text="",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div class='insight-section-spacer'></div>", unsafe_allow_html=True)

    # Top Growing/De-growing/Lost Customers
    top_growing = customer_summary[
        (customer_summary.get("prev_revenue", 0) > 0) &
        (customer_summary["revenue"] > customer_summary.get("prev_revenue", 0))
    ].copy().nlargest(10, "growth_%")

    top_degrowing = customer_summary[
        (customer_summary.get("prev_revenue", 0) > 0) &
        (customer_summary["revenue"] < customer_summary.get("prev_revenue", 0)) &
        (customer_summary["revenue"] > 0)
    ].copy().nsmallest(10, "growth_%")

    lost_summary = pd.DataFrame()
    if not prev_df.empty and lost_customer_codes:
        lost_summary = (
            prev_df[prev_df[code_col].isin(lost_customer_codes)]
            .groupby([code_col, name_col], as_index=False)
            .agg(lost_revenue=("Revenue", "sum"), last_CN_month=("FIN_MONTH", "max"))
            .nlargest(10, "lost_revenue")
        )

    divisor, unit = get_revenue_conversion(conversion_type)
    v1, v2, v3 = st.columns(3, gap="small")

    with v1:
        with st.container(border=True):
            st.markdown(f"<div class='section-header'>Top Growing {customer_label}s</div>", unsafe_allow_html=True)
            if top_growing.empty:
                st.info("No growing customers for selected filters.")
            else:
                chart_df = top_growing.sort_values("growth_%", ascending=True)
                fig = px.bar(chart_df, x="growth_%", y=name_col, orientation="h", text="growth_%",
                            color_discrete_sequence=["#059669"])
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig.update_layout(
                    height=310, margin=dict(l=5, r=30, t=5, b=15),
                    xaxis_title="Growth %", yaxis_title="",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with v2:
        with st.container(border=True):
            st.markdown(f"<div class='section-header'>Top De-growing {customer_label}s</div>", unsafe_allow_html=True)
            if top_degrowing.empty:
                st.info("No de-growing customers for selected filters.")
            else:
                chart_df = top_degrowing.sort_values("growth_%", ascending=False)
                fig = px.bar(chart_df, x="growth_%", y=name_col, orientation="h", text="growth_%",
                            color_discrete_sequence=["#dc2626"])
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig.update_layout(
                    height=310, margin=dict(l=5, r=30, t=5, b=15),
                    xaxis_title="Drop %", yaxis_title="",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with v3:
        with st.container(border=True):
            st.markdown(f"<div class='section-header'>Top Lost {customer_label}s</div>", unsafe_allow_html=True)
            if lost_summary.empty:
                st.info("No lost customers for selected filters.")
            else:
                lost_summary["Lost Revenue Display"] = lost_summary["lost_revenue"] / divisor
                chart_df = lost_summary.sort_values("lost_revenue", ascending=True)
                fig = px.bar(chart_df, x="Lost Revenue Display", y=name_col, orientation="h",
                            text="Lost Revenue Display", color_discrete_sequence=["#ef4444"])
                fig.update_traces(texttemplate=f"%{{text:.2f}} {unit}", textposition="outside")
                fig.update_layout(
                    height=310, margin=dict(l=5, r=30, t=5, b=15),
                    xaxis_title=f"Lost Revenue ({unit})", yaxis_title="",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_growth_tab(growth_df: pd.DataFrame, name_col: str, customer_label: str, conversion_type: str) -> None:
    """Render growth analysis tab."""
    st.markdown(f"<div class='section-header'>{customer_label} Growth / Degrowth Analysis</div>", unsafe_allow_html=True)
    
    if growth_df.empty:
        st.info("No growth data available for selected filters.")
        return

    display_df = growth_df.copy()
    divisor, unit = get_revenue_conversion(conversion_type)
    display_df["Revenue Display"] = display_df["revenue"] / divisor
    display_df["Previous Revenue Display"] = display_df.get("prev_revenue", 0) / divisor
    display_df["Bubble Size"] = display_df["shipments"].clip(lower=1)

    fig = px.scatter(
        display_df,
        x="Previous Revenue Display",
        y="Revenue Display",
        size="Bubble Size",
        color="Customer Status",
        hover_name=name_col,
        hover_data={"growth_%": ":.1f", "shipments": ":,.0f", "Bubble Size": False},
        size_max=34,
        title="Current Revenue vs Previous Revenue",
        color_discrete_map={
            "New": "#22c55e",
            "Existing": "#2563eb",
            "Reactivated": "#f59e0b",
        }
    )
    
    max_val = max(
        display_df["Revenue Display"].max(),
        display_df["Previous Revenue Display"].max(),
        1
    )
    fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(dash="dash", color="#64748b", width=1))
    
    fig.update_layout(
        height=430, margin=dict(t=45, b=25),
        xaxis_title=f"Previous Revenue ({unit})",
        yaxis_title=f"Current Revenue ({unit})",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("View detailed growth table", expanded=False):
        revenue_col = f"Revenue ({unit})"
        previous_col = f"Previous Revenue ({unit})"
        display_df[revenue_col] = display_df["Revenue Display"].round(2)
        display_df[previous_col] = display_df["Previous Revenue Display"].round(2)
        
        display_cols = [
            name_col, revenue_col, previous_col, "growth_%",
            "Customer Status", "shipments", "avg_delay", "max_delay",
        ]
        display_cols = [c for c in display_cols if c in display_df.columns]
        
        st.dataframe(
            display_df[display_cols].sort_values("growth_%", ascending=True),
            use_container_width=True, hide_index=True,
        )


def render_service_tab(service_df: pd.DataFrame, customer_label: str, conversion_type: str) -> None:
    """Render service performance tab."""
    st.markdown(f"<div class='section-header'>{customer_label} Service Performance</div>", unsafe_allow_html=True)
    
    if service_df.empty:
        st.info("No service performance data available.")
        return

    display_df = service_df.copy()
    divisor, unit = get_revenue_conversion(conversion_type)
    display_df["Revenue Display"] = display_df["revenue"] / divisor
    display_df["Bubble Size"] = display_df["shipments"].clip(lower=1)

    left, right = st.columns([1.35, 1], gap="small")
    
    with left:
        with st.container(border=True):
            fig = px.scatter(
                display_df,
                x="avg_delay_days",
                y="Revenue Display",
                size="Bubble Size",
                color="max_delay_days",
                hover_name=display_df.columns[1] if len(display_df.columns) > 1 else None,
                hover_data={"Bubble Size": False},
                color_continuous_scale="YlOrRd",
                size_max=38,
                title="Revenue vs Average Delay",
            )
            fig.update_layout(
                height=390, margin=dict(t=45, b=25),
                xaxis_title="Average Delay (Days)",
                yaxis_title=f"Revenue ({unit})",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with right:
        with st.container(border=True):
            delayed = display_df.nlargest(12, "avg_delay_days").sort_values("avg_delay_days")
            y_col = display_df.columns[1] if len(display_df.columns) > 1 else "Index"
            
            fig = px.bar(
                delayed, x="avg_delay_days", y=y_col, orientation="h",
                text="avg_delay_days", title="Highest Average Delay",
                color_discrete_sequence=["#f97316"],
            )
            fig.update_traces(texttemplate="%{text:.1f} d", textposition="outside")
            fig.update_layout(
                height=390, margin=dict(l=5, r=25, t=45, b=25),
                xaxis_title="Average Delay (Days)",
                yaxis_title="",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("View detailed service table", expanded=False):
        display_df[f"Revenue ({unit})"] = display_df["Revenue Display"].round(2)
        st.dataframe(
            display_df.drop(columns=["Revenue Display", "Bubble Size"], errors="ignore")
            .sort_values("avg_delay_days", ascending=False),
            use_container_width=True, hide_index=True,
        )


def render_revenue_bridge(metrics: dict, customer_label: str, conversion_type: str) -> None:
    """Render revenue bridge waterfall chart."""
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
        color_discrete_sequence=["#3b82f6"],
    )
    fig.update_traces(texttemplate=f"Rs. %{{text:.2f}} {revenue_unit}", textposition="outside")
    fig.update_yaxes(title=f"Revenue ({revenue_unit})")
    fig.update_xaxes(title="")
    fig.update_layout(
        height=330,
        margin=dict(l=5, r=5, t=12, b=5),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_zone_summary_table(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    customer_label: str,
    conversion_type: str,
) -> None:
    """Render zone-wise comparison."""
    if df.empty:
        st.info("No zone data available.")
        return

    current_zone = df.groupby("Zone", as_index=False).agg(
        Active_Customers=(code_col, "nunique"),
        Revenue=("Revenue", "sum"),
    )
    
    prev_zone = pd.DataFrame()
    if not prev_df.empty:
        prev_zone = prev_df.groupby("Zone", as_index=False).agg(
            Prev_Customers=(code_col, "nunique"),
            Prev_Revenue=("Revenue", "sum"),
        )

    current_codes = set(df[code_col].dropna().unique())
    previous_codes = set(prev_df[code_col].dropna().unique()) if not prev_df.empty else set()
    
    new_df = df[df[code_col].isin(current_codes - previous_codes)]
    new_zone = new_df.groupby("Zone", as_index=False).agg(New=(code_col, "nunique"))
    
    lost_df = prev_df[prev_df[code_col].isin(previous_codes - current_codes)] if not prev_df.empty else pd.DataFrame()
    lost_zone = lost_df.groupby("Zone", as_index=False).agg(Lost=(code_col, "nunique")) if not lost_df.empty else pd.DataFrame()

    summary = current_zone.copy()
    if not prev_zone.empty:
        summary = summary.merge(prev_zone, on="Zone", how="left")
    else:
        summary["Prev_Customers"] = 0
        summary["Prev_Revenue"] = 0
    
    if not new_zone.empty:
        summary = summary.merge(new_zone, on="Zone", how="left")
    else:
        summary["New"] = 0
    
    if not lost_zone.empty:
        summary = summary.merge(lost_zone, on="Zone", how="left")
    else:
        summary["Lost"] = 0
    
    summary = summary.fillna(0)

    if summary.empty:
        st.info("No zone performance data available.")
        return

    divisor, unit = get_revenue_conversion(conversion_type)
    cy_col = f"CY Revenue ({unit})"
    py_col = f"PY Revenue ({unit})"
    summary[cy_col] = (summary["Revenue"] / divisor).round(2)
    summary[py_col] = (summary["Prev_Revenue"] / divisor).round(2)
    summary["Growth %"] = summary.apply(
        lambda row: growth_percentage(row["Revenue"], row["Prev_Revenue"]), axis=1
    )
    summary = summary.sort_values("Revenue", ascending=True)

    chart_df = summary[["Zone", cy_col, py_col]].melt(
        id_vars="Zone",
        var_name="Period",
        value_name="Revenue Display",
    )
    
    st.markdown(
        f"<div class='section-header'>Zone Revenue: CY vs PY</div>",
        unsafe_allow_html=True,
    )
    
    fig = px.bar(
        chart_df,
        x="Revenue Display",
        y="Zone",
        color="Period",
        barmode="group",
        orientation="h",
        text="Revenue Display",
        category_orders={"Period": [py_col, cy_col]},
        color_discrete_map={py_col: "#94a3b8", cy_col: "#3b82f6"},
    )
    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_layout(
        height=310,
        margin=dict(l=5, r=30, t=8, b=5),
        xaxis_title=f"Revenue ({unit})",
        yaxis_title="",
        legend_title_text="",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("View zone figures (CY and PY)", expanded=False):
        table_df = summary.rename(columns={
            "Active_Customers": f"Active {customer_label}s CY",
            "Prev_Customers": f"Active {customer_label}s PY",
        })[[
            "Zone",
            f"Active {customer_label}s CY",
            f"Active {customer_label}s PY",
            "New",
            "Lost",
            cy_col,
            py_col,
            "Growth %",
        ]].sort_values(cy_col, ascending=False)

        st.dataframe(
            table_df.style.format({
                f"Active {customer_label}s CY": "{:,.0f}",
                f"Active {customer_label}s PY": "{:,.0f}",
                "New": "{:,.0f}",
                "Lost": "{:,.0f}",
                cy_col: "{:,.2f}",
                py_col: "{:,.2f}",
                "Growth %": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )


def render_branch_summary_table(
    df: pd.DataFrame,
    prev_df: pd.DataFrame,
    code_col: str,
    customer_label: str,
    conversion_type: str,
) -> None:
    """Render top branches comparison."""
    if df.empty:
        st.info("No branch data available.")
        return

    current = df.groupby("Branch", as_index=False).agg(
        Revenue=("Revenue", "sum"),
        Customers=(code_col, "nunique"),
    )
    
    previous = pd.DataFrame()
    if not prev_df.empty:
        previous = prev_df.groupby("Branch", as_index=False).agg(
            PrevRevenue=("Revenue", "sum"),
            PrevCustomers=(code_col, "nunique"),
        )

    current_codes = set(df[code_col].dropna().unique())
    previous_codes = set(prev_df[code_col].dropna().unique()) if not prev_df.empty else set()
    
    new_df = df[df[code_col].isin(current_codes - previous_codes)]
    new_branch = new_df.groupby("Branch", as_index=False).agg(NewCustomers=(code_col, "nunique"))

    summary = current.copy()
    if not previous.empty:
        summary = summary.merge(previous, on="Branch", how="left")
    else:
        summary["PrevRevenue"] = 0
        summary["PrevCustomers"] = 0
    
    if not new_branch.empty:
        summary = summary.merge(new_branch, on="Branch", how="left")
    else:
        summary["NewCustomers"] = 0
    
    summary = summary.fillna(0)

    if summary.empty:
        st.info("No branch performance data available.")
        return

    divisor, unit = get_revenue_conversion(conversion_type)
    cy_col = f"CY Revenue ({unit})"
    py_col = f"PY Revenue ({unit})"
    summary[cy_col] = (summary["Revenue"] / divisor).round(2)
    summary[py_col] = (summary["PrevRevenue"] / divisor).round(2)
    summary["Growth %"] = summary.apply(
        lambda row: growth_percentage(row["Revenue"], row["PrevRevenue"]), axis=1
    )
    summary = summary.nlargest(10, "Revenue").sort_values("Revenue", ascending=True)

    chart_df = summary[["Branch", cy_col, py_col]].melt(
        id_vars="Branch",
        var_name="Period",
        value_name="Revenue Display",
    )
    
    st.markdown(
        "<div class='section-header'>Top 10 Branches: CY vs PY</div>",
        unsafe_allow_html=True,
    )
    
    fig = px.bar(
        chart_df,
        x="Revenue Display",
        y="Branch",
        color="Period",
        barmode="group",
        orientation="h",
        text="Revenue Display",
        category_orders={"Period": [py_col, cy_col]},
        color_discrete_map={py_col: "#94a3b8", cy_col: "#10b981"},
    )
    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside",
        cliponaxis=False,
    )
    fig.update_layout(
        height=310,
        margin=dict(l=5, r=30, t=8, b=5),
        xaxis_title=f"Revenue ({unit})",
        yaxis_title="",
        legend_title_text="",
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with st.expander("View branch figures (CY and PY)", expanded=False):
        table_df = summary.rename(columns={
            "Customers": f"{customer_label}s CY",
            "PrevCustomers": f"{customer_label}s PY",
        })[[
            "Branch",
            cy_col,
            py_col,
            f"{customer_label}s CY",
            f"{customer_label}s PY",
            "NewCustomers",
            "Growth %",
        ]].sort_values(cy_col, ascending=False)

        st.dataframe(
            table_df.style.format({
                cy_col: "{:,.2f}",
                py_col: "{:,.2f}",
                f"{customer_label}s CY": "{:,.0f}",
                f"{customer_label}s PY": "{:,.0f}",
                "NewCustomers": "{:,.0f}",
                "Growth %": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )


def render_drilldown_tab(df: pd.DataFrame, code_col: str, name_col: str, customer_label: str, conversion_type: str) -> None:
    """Render customer drill-down tab."""
    st.subheader(f"{customer_label} Drill Down")
    
    customers = sorted(df[name_col].dropna().unique())
    if not customers:
        st.info(f"No {customer_label.lower()} available for drill down.")
        return

    selected_customer = st.selectbox(f"Select {customer_label} for Detail", customers, key="drilldown_customer")
    customer_df = df[df[name_col] == selected_customer]

    if customer_df.empty:
        st.warning(f"No data found for {selected_customer}")
        return

    total_shipments = customer_df["ShipmentCount"].sum()
    total_revenue = customer_df["Revenue"].sum()
    total_weight = customer_df["ChargeWeight"].sum()
    avg_revenue_per_shipment = total_revenue / total_shipments if total_shipments > 0 else 0

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Total Shipments", f"{total_shipments:,.0f}")
    d2.metric("Revenue", money_display(total_revenue, conversion_type))
    d3.metric("Charge Weight", f"{total_weight:,.0f}")
    d4.metric("Avg Revenue / Shipment", f"Rs.{avg_revenue_per_shipment:,.0f}")
    
    st.dataframe(customer_df, use_container_width=True, hide_index=True)


# =====================================================
# Main Dashboard Function
# =====================================================
def show_CustomerAnalysis() -> None:
    """Main dashboard orchestration function."""
    apply_dashboard_style()
    export_placeholder = render_dashboard_header()

    filter_columns, fin_year, view_type = render_filter_row_start()
    
    if fin_year == "Select FY":
        st.info("📊 Please select a Financial Year to continue.")
        return

    # Get configuration based on view type
    config = get_customer_config(view_type)
    code_col = config["code_col"]
    name_col = config["name_col"]
    customer_label = config["label"]

    # Load data
    start_date, end_date = get_date_range(fin_year)
    prev_start, prev_end = get_date_range(previous_financial_year(fin_year, 1))
    old_start, old_end = get_date_range(previous_financial_year(fin_year, 2))

    try:
        with st.spinner("📥 Loading customer summary data..."):
            all_df = clean_booking_data(load_booking_data(old_start, end_date, view_type))
    except Exception as e:
        st.error(f"❌ Data loading failed: {str(e)}")
        return

    if all_df.empty:
        st.warning("⚠️ No booking data found for selected period.")
        return

    # Split by financial year
    current_year = int(fin_year.split("-")[0])
    prev_year = current_year - 1
    old_year = current_year - 2

    df = all_df[all_df["YR"].astype(int) == current_year].copy()
    prev_df = all_df[all_df["YR"].astype(int) == prev_year].copy()
    old_df = all_df[all_df["YR"].astype(int) == old_year].copy()

    if df.empty:
        st.warning(f"⚠️ No data found for FY {fin_year}.")
        return

    # Add display columns
    for period_df in (df, prev_df, old_df):
        period_df["Month"] = period_df["FIN_MONTH"].map(MONTH_MAP)
        period_df["Quarter"] = period_df["FIN_MONTH"].map(QUARTER_MAP)

    # Validate required columns
    valid, missing_cols = validate_required_columns(df, code_col, name_col)
    if not valid:
        st.error(f"❌ Missing required columns: {missing_cols}")
        return

    # Render filters
    zone, circle, branch, quarter, month, load_type, customer, conversion_type = render_data_filters(
        df,
        customer_label,
        name_col,
        filter_columns,
    )

    # Apply filters
    df = apply_filters(df, zone, circle, branch, quarter, month, load_type, customer, name_col)
    prev_df = apply_filters(prev_df, zone, circle, branch, quarter, month, load_type, customer, name_col)
    old_df = apply_filters(old_df, zone, circle, branch, quarter, month, load_type, customer, name_col)

    if df.empty:
        st.warning(f"⚠️ No data found for selected filters.")
        return

    st.divider()

    # Calculate customer sets
    current_customers = set(df[code_col].dropna().unique())
    previous_customers = set(prev_df[code_col].dropna().unique())
    older_customers = set(old_df[code_col].dropna().unique())

    new_customer_codes = current_customers - previous_customers
    lost_customer_codes = previous_customers - current_customers
    reactivated_customer_codes = (current_customers & older_customers) - previous_customers

    # Calculate metrics
    active_customers = len(current_customers)
    prev_active_customers = len(previous_customers)
    new_customers = len(new_customer_codes)
    lost_customers = len(lost_customer_codes)
    reactivated_customers = len(reactivated_customer_codes)
    total_revenue = df["Revenue"].sum()
    prev_revenue = prev_df["Revenue"].sum()

    # Build analysis dataframes
    customer_summary = build_customer_summary(df, prev_df, code_col, name_col)
    monthly = build_monthly_summary(df, code_col, conversion_type)
    service_df = build_service_summary(df, code_col, name_col)

    # Reactivated customers
    reactivated_df = customer_summary[customer_summary[code_col].isin(reactivated_customer_codes)].copy()
    if not reactivated_df.empty:
        revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)
        reactivated_df[f"Revenue ({revenue_unit})"] = (reactivated_df["revenue"] / revenue_divisor).round(2)
        reactivated_df[f"Previous Revenue ({revenue_unit})"] = (reactivated_df.get("prev_revenue", 0) / revenue_divisor).round(2)

    # Growth dataframe
    growth_df = customer_summary.copy()
    growth_df["Customer Status"] = "Existing"
    growth_df.loc[growth_df[code_col].isin(new_customer_codes), "Customer Status"] = "New"
    growth_df.loc[growth_df[code_col].isin(reactivated_customer_codes), "Customer Status"] = "Reactivated"

    # At risk customers
    at_risk_customers = customer_summary[
        (customer_summary.get("prev_revenue", 0) > 0) &
        (customer_summary["revenue"] < customer_summary.get("prev_revenue", 0) * 0.75)
    ][code_col].nunique()

    # Revenue calculations
    revenue_from_new = df[df[code_col].isin(new_customer_codes)]["Revenue"].sum()
    lost_revenue = prev_df[prev_df[code_col].isin(lost_customer_codes)]["Revenue"].sum()
    reactivated_revenue = df[df[code_col].isin(reactivated_customer_codes)]["Revenue"].sum()
    charged_weight = df["ChargeWeight"].sum()
    current_yield = total_revenue / charged_weight if charged_weight > 0 else 0

    retention_percent = (
        ((active_customers - new_customers) / prev_active_customers) * 100
        if prev_active_customers > 0 else 0
    )

    # Metrics dictionary
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
        "revenue_from_new_customers": revenue_from_new,
        "lost_revenue": lost_revenue,
        "reactivated_revenue": reactivated_revenue,
        "current_yield": current_yield,
    }

    # Export functionality
    excel_file = export_to_excel(
        df=df,
        customer_summary=customer_summary,
        growth_df=growth_df,
        monthly_df=monthly,
        reactivated_df=reactivated_df,
        service_df=service_df,
    )
    
    with export_placeholder:
        if excel_file:
            st.download_button(
                label="📥 Export to Excel",
                data=excel_file,
                file_name=f"customer_analysis_{view_type}_{fin_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="customer_analysis_export_excel",
                help="Download filtered customer analysis data as Excel workbook",
                use_container_width=True,
            )

    # Render KPIs
    render_kpis(metrics, customer_label, conversion_type)

    # Render summary charts
    c1, c2, c3 = st.columns([1, 1, 1], gap="small", vertical_alignment="top")
    
    with c1:
        with st.container(border=True):
            render_zone_summary_table(df, prev_df, code_col, customer_label, conversion_type)
    
    with c2:
        with st.container(border=True):
            st.markdown("<div class='section-header'>Revenue Bridge</div>", unsafe_allow_html=True)
            render_revenue_bridge(metrics, customer_label, conversion_type)
    
    with c3:
        with st.container(border=True):
            render_branch_summary_table(df, prev_df, code_col, customer_label, conversion_type)

    st.markdown("<div class='insight-section-spacer'></div>", unsafe_allow_html=True)

    # Tabs
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
        render_drilldown_tab(df, code_col, name_col, customer_label, conversion_type)


# =====================================================
# Entry Point
# =====================================================
if __name__ == "__main__":
    show_CustomerAnalysis()
