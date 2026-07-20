import io
import streamlit as st
import pandas as pd
import calendar
import plotly.graph_objects as go
import plotly.express as px
from services.data_loader import load_booking_data_pair, get_date_range
from services.branch_agency_mast import load_stationmast_data

# =========================
# Compact dashboard styling
# =========================

def _inject_overview_css():
    """
    Apply the same top-alignment logic used on the Outstanding page.

    Keeping CSS inside a function prevents Streamlit from rendering separate
    top-level markdown blocks before the page heading.
    """
    st.markdown(
        """
        <style>
            /* Start page content close to the top, same as Outstanding */
            .block-container {
                padding-top: 0.5rem;
                padding-bottom: 1rem;
            }

            /* Remove unnecessary top spacing from the first page elements */
            .block-container > div:first-child {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

            /* Reduce dataframe row height */
            [data-testid="stDataFrame"] table {
                font-size: 11px;
            }

            [data-testid="stDataFrame"] tbody tr {
                height: 24px !important;
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
        """,
        unsafe_allow_html=True,
    )


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



def build_weight_yoy_trend(current_df, previous_df, trend_type, date_col, fy_start, prev_fy_start, month_map):
    """Build Current-FY vs LY weight trend in MT for Daily/Weekly/Monthly/Quarterly views."""
    cur = current_df.copy()
    prev = previous_df.copy() if previous_df is not None and not previous_df.empty else pd.DataFrame()

    cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty and date_col in prev.columns:
        prev[date_col] = pd.to_datetime(prev[date_col], errors="coerce")

    fy_start_ts = pd.to_datetime(fy_start) if fy_start else None
    prev_fy_start_ts = pd.to_datetime(prev_fy_start) if prev_fy_start else None

    if trend_type == "Daily":
        trend_df = cur.groupby(cur[date_col].dt.date)["aweight"].sum().reset_index()
        trend_df.columns = ["Period", "AWEIGHT"]
        trend_df["Key"] = (
            (pd.to_datetime(trend_df["Period"]) - fy_start_ts).dt.days
            if fy_start_ts is not None else range(len(trend_df))
        )

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.date)["aweight"].sum().reset_index()
            prev_trend.columns = ["Period", "PREV_AWEIGHT"]
            prev_trend["Key"] = (pd.to_datetime(prev_trend["Period"]) - prev_fy_start_ts).dt.days
        else:
            prev_trend = pd.DataFrame(columns=["Period", "PREV_AWEIGHT", "Key"])

    elif trend_type == "Weekly":
        trend_df = cur.groupby(cur[date_col].dt.to_period("W"))["aweight"].sum().reset_index()
        trend_df["Period"] = trend_df[date_col].astype(str)
        trend_df["Key"] = (
            ((trend_df[date_col].dt.start_time - fy_start_ts).dt.days // 7)
            if fy_start_ts is not None else range(len(trend_df))
        )
        trend_df = trend_df.rename(columns={"aweight": "AWEIGHT"}).drop(columns=[date_col])

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.to_period("W"))["aweight"].sum().reset_index()
            prev_trend["Key"] = (prev_trend[date_col].dt.start_time - prev_fy_start_ts).dt.days // 7
            prev_trend = prev_trend.rename(columns={"aweight": "PREV_AWEIGHT"}).drop(columns=[date_col])
        else:
            prev_trend = pd.DataFrame(columns=["PREV_AWEIGHT", "Key"])

    elif trend_type == "Quarterly":
        cur["Quarter"] = cur["FIN_MONTH"].map(QUARTER_MAP)
        trend_df = cur.groupby("Quarter")["aweight"].sum().reset_index()
        trend_df["Quarter"] = pd.Categorical(trend_df["Quarter"], categories=QUARTER_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Quarter")
        trend_df.columns = ["Period", "AWEIGHT"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Quarter"] = prev["FIN_MONTH"].map(QUARTER_MAP)
            prev_trend = prev.groupby("Quarter")["aweight"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_AWEIGHT"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_AWEIGHT"])

    else:  # Monthly
        cur["Month"] = cur["FIN_MONTH"].map(month_map)
        trend_df = cur.groupby("Month")["aweight"].sum().reset_index()
        trend_df["Month"] = pd.Categorical(trend_df["Month"], categories=MONTH_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Month")
        trend_df.columns = ["Period", "AWEIGHT"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Month"] = prev["FIN_MONTH"].map(month_map)
            prev_trend = prev.groupby("Month")["aweight"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_AWEIGHT"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_AWEIGHT"])

    trend_df["Weight MT"] = (trend_df["AWEIGHT"] / 1000).round(0)

    if not prev_trend.empty:
        prev_trend["Prev Weight MT"] = (prev_trend["PREV_AWEIGHT"] / 1000).round(0)
        trend_df = trend_df.merge(prev_trend[["Key", "Prev Weight MT"]], on="Key", how="left")
    else:
        trend_df["Prev Weight MT"] = None

    trend_df["Growth %"] = trend_df.apply(
        lambda r: pct_growth(r["Weight MT"], r["Prev Weight MT"])
        if pd.notna(r["Prev Weight MT"]) else None,
        axis=1,
    )
    trend_df["Growth Label"] = trend_df["Growth %"].apply(
        lambda x: growth_label(x) if pd.notna(x) else "N/A"
    )

    return trend_df

def add_revenue_forecast(yoy_df, trend_type, selected_quarter="All", selected_month="All"):
    """
    Add forecast revenue only for the current ongoing financial month.

    Logic:
    - Forecast is shown only in Monthly view.
    - Forecast is shown only for the current calendar month, e.g. July.
    - Future months like Aug-Mar are removed from the chart.
    - Formula: current month actual revenue till today / days passed * total days in month.
    """
    from datetime import datetime

    result = yoy_df.copy()

    if result.empty or "Revenue Cr" not in result.columns:
        result["Forecast Revenue Cr"] = None
        return result

    result["Revenue Cr"] = pd.to_numeric(result["Revenue Cr"], errors="coerce")
    if "Prev Revenue Cr" in result.columns:
        result["Prev Revenue Cr"] = pd.to_numeric(result["Prev Revenue Cr"], errors="coerce")

    # Default: no forecast bar anywhere
    result["Forecast Revenue Cr"] = None

    # Forecast only monthly chart. No forecast for Daily/Weekly/Quarterly.
    if trend_type != "Monthly":
        return result

    today = datetime.today()

    # Convert calendar month into your FY month number: Apr=1, May=2 ... Mar=12
    current_fin_month = ((today.month - 4) % 12) + 1
    current_month_name = MONTH_ORDER[current_fin_month - 1]

    month_to_quarter = {MONTH_ORDER[i]: QUARTER_MAP[i + 1] for i in range(len(MONTH_ORDER))}
    current_quarter = month_to_quarter.get(current_month_name)

    # Remove future months from Monthly chart when Month filter is All.
    # Example in July: show Apr, May, Jun, Jul only. Hide Aug-Mar completely.
    if selected_month == "All":
        if selected_quarter == "All":
            allowed_months = MONTH_ORDER[:current_fin_month]
        elif selected_quarter == current_quarter:
            allowed_months = [
                m for m in MONTH_ORDER
                if month_to_quarter.get(m) == selected_quarter
                and MONTH_ORDER.index(m) <= MONTH_ORDER.index(current_month_name)
            ]
        else:
            allowed_months = [m for m in MONTH_ORDER if month_to_quarter.get(m) == selected_quarter]

        result = result[result["Period"].astype(str).isin(allowed_months)].copy()

    # Respect filters: if user selected a different month/quarter, do not show forecast.
    if selected_month != "All" and selected_month != current_month_name:
        return result

    if selected_quarter != "All" and selected_quarter != current_quarter:
        return result

    # Find current month actual revenue till today
    current_rows = result["Period"].astype(str).eq(current_month_name)
    if not current_rows.any():
        return result

    current_value = result.loc[current_rows, "Revenue Cr"].iloc[0]

    if pd.isna(current_value) or current_value <= 0:
        return result

    days_elapsed = max(today.day, 1)
    total_days = calendar.monthrange(today.year, today.month)[1]

    forecast_value = round((current_value / days_elapsed) * total_days, 2)

    # Forecast bar only for current ongoing month
    result.loc[current_rows, "Forecast Revenue Cr"] = forecast_value

    return result


def create_card(title, value, color, icon, growth_value=0.0):
    """Compact KPI card used in the top KPI row. growth_value is auto-calculated % vs LY."""
    growth_color = "#166534" if growth_value >= 0 else "#dc2626"
    growth_text = growth_label(growth_value)

    html = f"""<div style="background:#ffffff;padding:8px;border-radius:10px;border:1px solid #e5e7eb;border-left:4px solid {color};box-shadow:0 3px 10px rgba(0,0,0,0.08);min-height:70px;">
<div style="display:flex;justify-content:space-between;align-items:center;">
<div style="color:{color};font-size:11px;font-weight:800;">{title}</div>
<div style="font-size:18px;">{icon}</div>
</div>
<div style="font-size:17px;font-weight:900;color:#0f172a;margin-top:1px;">{value}</div>
<div style="font-size:11px;color:{growth_color};font-weight:700;margin-top:1px;">{growth_text} vs LY</div>

</div>"""
    st.markdown(html, unsafe_allow_html=True)


def create_target_card(title, actual, target, unit="", decimals=2, icon="🎯"):
    """Render a compact Target vs Actual card.

    A target of zero means that the target has not yet been configured. Targets
    entered through the dashboard are stored only in the current Streamlit
    session and can later be replaced with database/config values.
    """
    actual = float(actual or 0)
    target = float(target or 0)

    if target > 0:
        achievement = (actual / target) * 100
        gap = actual - target
        progress_width = min(max(achievement, 0), 100)
        status_color = "#16a34a" if achievement >= 100 else "#f59e0b" if achievement >= 80 else "#dc2626"
        gap_label = f"{gap:+,.{decimals}f}{unit} gap"
        target_label = f"Target {target:,.{decimals}f}{unit}"
        achievement_label = f"{achievement:,.1f}% achieved"
    else:
        progress_width = 0
        status_color = "#94a3b8"
        gap_label = "Enter target to calculate gap"
        target_label = "Target not set"
        achievement_label = "Waiting for target"

    html = f"""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;
                padding:10px 11px;box-shadow:0 3px 10px rgba(15,23,42,.06);min-height:112px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <div style="font-size:11px;font-weight:800;color:#334155;">{title}</div>
            <div style="font-size:17px;">{icon}</div>
        </div>
        <div style="font-size:18px;font-weight:900;color:#0f172a;line-height:1.1;">
            {actual:,.{decimals}f}{unit}
        </div>
        <div style="display:flex;justify-content:space-between;gap:6px;margin-top:4px;
                    font-size:10px;color:#64748b;">
            <span>{target_label}</span>
            <span style="font-weight:800;color:{status_color};">{achievement_label}</span>
        </div>
        <div style="height:7px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin-top:7px;">
            <div style="height:7px;width:{progress_width:.1f}%;background:{status_color};border-radius:999px;"></div>
        </div>
        <div style="font-size:10px;font-weight:700;color:{status_color};margin-top:5px;">{gap_label}</div>
    </div>
    """
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

    _inject_overview_css()

    # Direct heading placement, matching the Outstanding page.
    st.markdown(
        """
        <h3 style="margin:0;padding:0;">Revenue Overview</h3>
        <p style="color:#64748b;font-size:12px;margin:0 0 8px 0;">
            Revenue, shipment and branch performance overview
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Bold Filters header
    st.markdown(
        "<div style='font-weight:400;font-size:12px;color:#2563eb;margin-bottom:8px;'>FILTERS</div>",
        unsafe_allow_html=True,
    )

    # Top filter row: view type, FY, zone, circle, branch, quarter, month and load type
    (
        filter_col1, filter_col2, filter_col3, filter_col4,
        filter_col5, filter_col6, filter_col7, filter_col8
    ) = st.columns(8)

    with filter_col1:
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>View Type</div>", unsafe_allow_html=True)
        view_type = st.selectbox("View Type", ["Origin", "Destination"], label_visibility="collapsed")

    with filter_col2:
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>Financial Year</div>", unsafe_allow_html=True)
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
            label_visibility="collapsed"
        )

    if fy == "Select FY":
        st.info("Please select financial year")
        return

    start_date, end_date = get_date_range(fy)

    prev_fy = get_previous_fy(fy)
    prev_start, prev_end = get_date_range(prev_fy)

    # Load current-FY AND last-year data TOGETHER, in parallel,
    # instead of one after another. This roughly halves the wait time
    # compared to two sequential stored-procedure calls.
    with st.spinner("Loading data..."):
        df, prev_df = load_booking_data_pair(
            start_date, end_date, prev_start, prev_end, view_type.lower()
        )

    station_df = load_stationmast_data(start_date, end_date)
    
    # Add FIN_MONTH to station_df if it doesn't exist
    if "FIN_MONTH" not in station_df.columns:
        def get_fin_month(date_str):
            try:
                date = pd.to_datetime(date_str)
                month = date.month
                return ((month - 4) % 12) + 1
            except:
                return None
        
        # Try to add FIN_MONTH from activedate or closedate
        if "activedate" in station_df.columns:
            station_df["FIN_MONTH"] = station_df["activedate"].apply(get_fin_month)
        elif "closedate" in station_df.columns:
            station_df["FIN_MONTH"] = station_df["closedate"].apply(get_fin_month)
        else:
            station_df["FIN_MONTH"] = None

    if df.empty:
        st.warning("No data found")
        return

    month_map = {
        1: "Apr", 2: "May", 3: "Jun", 4: "Jul",
        5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov",
        9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"
    }

    df["Month"] = df["FIN_MONTH"].map(month_map)
    df["Quarter"] = df["FIN_MONTH"].map(QUARTER_MAP)

    if not prev_df.empty:
        prev_df["Month"] = prev_df["FIN_MONTH"].map(month_map)
        prev_df["Quarter"] = prev_df["FIN_MONTH"].map(QUARTER_MAP)

    # Data-scope restriction for this employee (set at login, from config/data_scope.json)
    # e.g. {} = no restriction, {"zone": "Nepal Zone"}, {"circle": "NCR Circle"}, {"branch": "Noida"}
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
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>Zone</div>", unsafe_allow_html=True)
        if locked_zone:
            zone = locked_zone
            st.selectbox("Zone", [zone], disabled=True, help="Locked as per your assigned rights", label_visibility="collapsed")
        else:
            zone = st.selectbox("Zone", ["All"] + sorted(df["zone"].dropna().unique().tolist()), label_visibility="collapsed")

    if zone != "All":
        df = df[df["zone"] == zone]

    with filter_col4:
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>Circle</div>", unsafe_allow_html=True)
        if locked_circle:
            circle = locked_circle
            st.selectbox("Circle", [circle], disabled=True, help="Locked as per your assigned rights", label_visibility="collapsed")
        else:
            circle = st.selectbox("Circle", ["All"] + sorted(df["circle"].dropna().unique().tolist()), label_visibility="collapsed")

    if circle != "All":
        df = df[df["circle"] == circle]

    with filter_col5:
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>Branch</div>", unsafe_allow_html=True)
        if locked_branch:
            branch = locked_branch
            st.selectbox("Branch", [branch], disabled=True, help="Locked as per your assigned rights", label_visibility="collapsed")
        else:
            branch = st.selectbox("Branch", ["All"] + sorted(df["branch"].dropna().unique().tolist()), label_visibility="collapsed")

    if branch != "All":
        df = df[df["branch"] == branch]

    with filter_col6:
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>Quarter</div>", unsafe_allow_html=True)
        available_quarters = [q for q in QUARTER_ORDER if q in df["Quarter"].dropna().unique().tolist()]
        quarter = st.selectbox("Quarter", ["All"] + available_quarters, label_visibility="collapsed")

    if quarter != "All":
        df = df[df["Quarter"] == quarter]

    with filter_col7:
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>Month</div>", unsafe_allow_html=True)
        available_months = [m for m in MONTH_ORDER if m in df["Month"].dropna().unique().tolist()]
        month = st.selectbox("Month", ["All"] + available_months, label_visibility="collapsed")

    if month != "All":
        df = df[df["Month"] == month]

    with filter_col8:
        st.markdown("<div style='font-weight:400;font-size:12px;color:#2563eb;'>Load Type</div>", unsafe_allow_html=True)
        loadtype = st.selectbox("Load Type", ["All"] + sorted(df["LOADTYPE"].dropna().unique().tolist()), label_visibility="collapsed")

    if loadtype != "All":
        df = df[df["LOADTYPE"] == loadtype]

    if df.empty:
        st.warning("No data found for selected filters")
        return

    # =========================
    # Apply the same zone/circle/branch/quarter/month/loadtype filters to the LY data
    # =========================
    if not prev_df.empty:
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
        create_card("LTL Revenue", format_cr(ltl), "#2563eb", "🚚", ltl_growth)

    with k4:
        create_card("Total GR", f"{total_gr:,}", "#2563eb", "📦", gr_growth)

    with k5:
        create_card("Total Weight (MT)", f"{aweight:,.0f}", "#2563eb", "⚓", weight_growth)

    with k6:
        create_card("Topay", format_cr(topay), "#2563eb", "🧾", topay_growth)

    with k7:
        create_card("Paid", format_cr(paid), "#2563eb", "🔗", paid_growth)

    with k8:
        create_card("T.B.B", format_cr(tbb), "#2563eb", "🚚", tbb_growth)

    # =====================================================
    # Actual vs Target (shown only when user clicks the button)
    # =====================================================
    target_toggle_key = "show_actual_vs_target"
    if target_toggle_key not in st.session_state:
        st.session_state[target_toggle_key] = False

    target_button_label = (
        "✕ Hide Actual vs Target"
        if st.session_state[target_toggle_key]
        else "🎯 Actual vs Target"
    )

    if st.button(target_button_label, key="actual_vs_target_button", use_container_width=False):
        st.session_state[target_toggle_key] = not st.session_state[target_toggle_key]
        st.rerun()

    if st.session_state[target_toggle_key]:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:13px;font-weight:900;color:#0f172a;'>Actual vs Target</div>"
                "<div style='font-size:10px;color:#64748b;margin-bottom:8px;'>"
                "Enter temporary targets for the currently selected dashboard filters."
                "</div>",
                unsafe_allow_html=True,
            )

            target_source = st.radio(
                "Target Source",
                ["Manual Entry", "Upload Excel"],
                horizontal=True,
                key=f"target_source_{fy}",
                help="Choose manual entry or upload a target file for the selected hierarchy.",
            )

            revenue_target_cr = 0.0
            ftl_target_cr = 0.0
            ltl_target_cr = 0.0
            gr_target = 0
            weight_target_mt = 0.0

            if target_source == "Manual Entry":
                with st.expander("Enter Target Values", expanded=True):
                    target_input_cols = st.columns(5)

                    with target_input_cols[0]:
                        revenue_target_cr = st.number_input(
                            "Revenue Target (Cr)",
                            min_value=0.0,
                            value=st.session_state.get(f"target_revenue_{fy}", 0.0),
                            step=0.10,
                            key=f"target_revenue_{fy}",
                        )
                    with target_input_cols[1]:
                        ftl_target_cr = st.number_input(
                            "FTL Target (Cr)",
                            min_value=0.0,
                            value=st.session_state.get(f"target_ftl_{fy}", 0.0),
                            step=0.10,
                            key=f"target_ftl_{fy}",
                        )
                    with target_input_cols[2]:
                        ltl_target_cr = st.number_input(
                            "LTL Target (Cr)",
                            min_value=0.0,
                            value=st.session_state.get(f"target_ltl_{fy}", 0.0),
                            step=0.10,
                            key=f"target_ltl_{fy}",
                        )
                    with target_input_cols[3]:
                        gr_target = st.number_input(
                            "GR Target",
                            min_value=0,
                            value=int(st.session_state.get(f"target_gr_{fy}", 0)),
                            step=100,
                            key=f"target_gr_{fy}",
                        )
                    with target_input_cols[4]:
                        weight_target_mt = st.number_input(
                            "Weight Target (MT)",
                            min_value=0.0,
                            value=float(st.session_state.get(f"target_weight_{fy}", 0.0)),
                            step=100.0,
                            key=f"target_weight_{fy}",
                        )
            else:
                st.markdown(
                    "<div style='font-size:10px;color:#64748b;margin:2px 0 7px 0;'>"
                    "Excel columns required: <b>zone, circle, branch, month, ltl, ftl, total</b>. "
                    "Revenue values must be entered in crores. Use <b>All</b> where a target applies to the complete hierarchy."
                    "</div>",
                    unsafe_allow_html=True,
                )

                template_df = pd.DataFrame(
                    [
                        {
                            "zone": "NORTH ZONE",
                            "circle": "NCR CIRCLE",
                            "branch": "NOIDA",
                            "month": "Apr",
                            "ltl": 2.50,
                            "ftl": 4.50,
                            "total": 7.00,
                        },
                        {
                            "zone": "All",
                            "circle": "All",
                            "branch": "All",
                            "month": "May",
                            "ltl": 20.00,
                            "ftl": 35.00,
                            "total": 55.00,
                        },
                    ]
                )
                template_buffer = io.BytesIO()
                with pd.ExcelWriter(template_buffer, engine="openpyxl") as writer:
                    template_df.to_excel(writer, index=False, sheet_name="Targets")
                template_buffer.seek(0)

                upload_col, template_col = st.columns([2.5, 1])
                with upload_col:
                    target_file = st.file_uploader(
                        "Upload Target Excel",
                        type=["xlsx", "xls"],
                        key=f"target_excel_{fy}",
                    )
                with template_col:
                    st.download_button(
                        "Download Template",
                        data=template_buffer.getvalue(),
                        file_name="target_upload_template.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

                if target_file is not None:
                    try:
                        target_df = pd.read_excel(target_file)
                        target_df.columns = [str(col).strip().lower() for col in target_df.columns]
                        required_cols = ["zone", "circle", "branch", "month", "ltl", "ftl", "total"]
                        missing_cols = [col for col in required_cols if col not in target_df.columns]

                        if missing_cols:
                            st.error("Missing required columns: " + ", ".join(missing_cols))
                        else:
                            for col in ["zone", "circle", "branch", "month"]:
                                target_df[col] = target_df[col].fillna("All").astype(str).str.strip()
                            for col in ["ltl", "ftl", "total"]:
                                target_df[col] = pd.to_numeric(target_df[col], errors="coerce").fillna(0)

                            selected_values = {
                                "zone": zone,
                                "circle": circle,
                                "branch": branch,
                                "month": month,
                            }
                            matched_targets = target_df.copy()
                            for col, selected_value in selected_values.items():
                                if matched_targets.empty:
                                    break

                                normalized_values = matched_targets[col].str.casefold()
                                if selected_value != "All":
                                    normalized_selected = str(selected_value).strip().casefold()
                                    exact_rows = normalized_values.eq(normalized_selected)
                                    fallback_rows = normalized_values.eq("all")

                                    # Prefer the exact hierarchy target. Use an All row only
                                    # when no exact target exists at the selected level.
                                    if exact_rows.any():
                                        matched_targets = matched_targets[exact_rows]
                                    else:
                                        matched_targets = matched_targets[fallback_rows]
                                else:
                                    detailed_rows = ~normalized_values.eq("all")

                                    # For an All dashboard selection, aggregate detailed
                                    # rows when available. Otherwise use the All summary row.
                                    if detailed_rows.any():
                                        matched_targets = matched_targets[detailed_rows]
                                    else:
                                        matched_targets = matched_targets[~detailed_rows]

                            revenue_target_cr = float(matched_targets["total"].sum())
                            ftl_target_cr = float(matched_targets["ftl"].sum())
                            ltl_target_cr = float(matched_targets["ltl"].sum())

                            st.success(
                                f"Target loaded: Total ₹{revenue_target_cr:.2f} Cr | "
                                f"FTL ₹{ftl_target_cr:.2f} Cr | LTL ₹{ltl_target_cr:.2f} Cr"
                            )
                            with st.expander("View Matched Target Rows", expanded=False):
                                st.dataframe(
                                    matched_targets[required_cols],
                                    use_container_width=True,
                                    hide_index=True,
                                )
                    except Exception as exc:
                        st.error(f"Unable to read target Excel file: {exc}")

            target_cols = st.columns(5 if target_source == "Manual Entry" else 3)
            with target_cols[0]:
                create_target_card(
                    "Revenue", revenue / 10000000, revenue_target_cr,
                    unit=" Cr", decimals=2, icon="💰",
                )
            with target_cols[1]:
                create_target_card(
                    "FTL Revenue", ftl / 10000000, ftl_target_cr,
                    unit=" Cr", decimals=2, icon="🚛",
                )
            with target_cols[2]:
                create_target_card(
                    "LTL Revenue", ltl / 10000000, ltl_target_cr,
                    unit=" Cr", decimals=2, icon="🚚",
                )
            if target_source == "Manual Entry":
                with target_cols[3]:
                    create_target_card(
                        "Total GR", total_gr, gr_target,
                        unit="", decimals=0, icon="📦",
                    )
                with target_cols[4]:
                    create_target_card(
                        "Weight", aweight, weight_target_mt,
                        unit=" MT", decimals=0, icon="⚓",
                    )

    # Small separator before charts
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Monthly revenue data used for monthly trend and MoM growth
    monthly = (
        df.groupby("Month")["REVENUE"]
        .sum()
        .reset_index()
    )

    monthly["Revenue Cr"] = (monthly["REVENUE"] / 10000000).round(2)

    monthly["Month"] = pd.Categorical(
        monthly["Month"],
        categories=MONTH_ORDER,
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
                _trend_badge_color = "#166534" if revenue_growth >= 0 else "#dc2626"
                st.markdown(
                    f"###### Revenue Trend "
                    f"<span style='font-size:11px;font-weight:700;color:{_trend_badge_color};'>"
                    f"({growth_label(revenue_growth)} vs LY)</span>",
                    unsafe_allow_html=True
                )

            with filter_col:
                trend_type = st.segmented_control(
                    "",
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    default="Monthly",
                    label_visibility="collapsed"
                )

            # Build trend data (Current FY vs LY) for the selected granularity
            DATE_COL = "grdt"   # change if your date column is different

            yoy_df = build_yoy_trend(
                df, prev_df, trend_type, DATE_COL, start_date, prev_start, month_map
            )

            # Add forecast only for the current ongoing month and remove future blank months
            yoy_df = add_revenue_forecast(
                yoy_df,
                trend_type,
                selected_quarter=quarter,
                selected_month=month
            )

            # Revenue trend grouped bar chart — LY vs Current FY vs Forecast
            fig_yoy = go.Figure()

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Prev Revenue Cr"],
                    name=f"LY ({prev_fy})",
                    marker_color="#cbd5e1",
                    text=yoy_df["Prev Revenue Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=9, color="#64748b")
                )
            )

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Revenue Cr"],
                    name=f"Current ({fy})",
                    marker_color="#2563eb",
                    text=yoy_df["Revenue Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=9, color="#2563eb")
                )
            )

            # Forecast bar only for the current ongoing month.
            forecast_df = yoy_df[yoy_df["Forecast Revenue Cr"].notna()].copy()

            if not forecast_df.empty:
                fig_yoy.add_trace(
                    go.Bar(
                        x=forecast_df["Period"],
                        y=forecast_df["Forecast Revenue Cr"],
                        name="Forecast",
                        marker_color="#f97316",
                        text=forecast_df["Forecast Revenue Cr"],
                        texttemplate="%{text:.2f}",
                        textposition="outside",
                        textfont=dict(size=9, color="#f97316")
                    )
                )

            # Growth % annotated above each period's pair of bars
            yoy_max = pd.concat([
                yoy_df["Revenue Cr"],
                yoy_df["Prev Revenue Cr"],
                yoy_df["Forecast Revenue Cr"]
            ]).max()
            yoy_max = yoy_max if pd.notna(yoy_max) and yoy_max > 0 else 1

            # Skip annotation clutter when there are too many bars (Daily/Weekly with long ranges)
            show_annotations = len(yoy_df) <= 40

            if show_annotations:
                for _, r in yoy_df.iterrows():
                    if r["Growth Label"] and r["Growth Label"] not in ["N/A", "Forecast"]:
                        label_color = "#166534" if (r["Growth %"] or 0) >= 0 else "#dc2626"
                        bar_top = max(
                            r["Revenue Cr"] if pd.notna(r["Revenue Cr"]) else 0,
                            r["Prev Revenue Cr"] if pd.notna(r["Prev Revenue Cr"]) else 0,
                            r["Forecast Revenue Cr"] if pd.notna(r["Forecast Revenue Cr"]) else 0
                        )
                        fig_yoy.add_annotation(
                            x=r["Period"],
                            y=bar_top + (yoy_max * 0.16),
                            text=r["Growth Label"],
                            showarrow=False,
                            font=dict(size=10, color=label_color, family="Arial Black")
                        )

            fig_yoy.update_layout(
                barmode="group",
                height=250,
                margin=dict(l=2, r=2, t=30, b=0),
                xaxis_title="",
                yaxis_title="Revenue (Cr)",
                plot_bgcolor="white",
                paper_bgcolor="white",
                legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0, font=dict(size=9)),
                yaxis_range=[0, yoy_max * 1.35]
            )

            fig_yoy.update_xaxes(showgrid=False, zeroline=False)
            fig_yoy.update_yaxes(showgrid=False, zeroline=False)

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
                height=250,
                margin=dict(l=0, r=0, t=5, b=0)
            )

            st.plotly_chart(fig_load, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # =========================
    # Weight trend data is prepared inside the chart based on selected granularity
    # =========================

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

    # =====================================================
    # Weight trend on a separate full-width row
    # =====================================================
    with st.container(border=True):
        weight_title_col, weight_filter_col = st.columns([2, 2])

        with weight_filter_col:
            weight_trend_type = st.segmented_control(
                "",
                ["Daily", "Weekly", "Monthly", "Quarterly"],
                default="Monthly",
                label_visibility="collapsed",
                key="weight_trend_type",
            )

        DATE_COL = "grdt"
        weight_yoy_df = build_weight_yoy_trend(
            df,
            prev_df,
            weight_trend_type,
            DATE_COL,
            start_date,
            prev_start,
            month_map,
        )

        weight_growth_total = pct_growth(
            weight_yoy_df["Weight MT"].sum(),
            weight_yoy_df["Prev Weight MT"].sum(),
        )
        _w_badge_color = "#166534" if weight_growth_total >= 0 else "#dc2626"

        with weight_title_col:
            st.markdown(
                f"###### Weight(MT) Trend "
                f"<span style='font-size:11px;font-weight:700;color:{_w_badge_color};'>"
                f"({growth_label(weight_growth_total)} vs LY)</span>",
                unsafe_allow_html=True,
            )

        fig_weight = go.Figure()

        fig_weight.add_trace(
            go.Bar(
                x=weight_yoy_df["Period"],
                y=weight_yoy_df["Prev Weight MT"],
                name=f"LY ({prev_fy})",
                marker_color="#cbd5e1",
                text=weight_yoy_df["Prev Weight MT"],
                texttemplate="%{text:.0f}",
                textposition="outside",
                textfont=dict(size=9, color="#64748b"),
            )
        )

        fig_weight.add_trace(
            go.Bar(
                x=weight_yoy_df["Period"],
                y=weight_yoy_df["Weight MT"],
                name=f"Current ({fy})",
                marker_color="#0f766e",
                text=weight_yoy_df["Weight MT"],
                texttemplate="%{text:.0f}",
                textposition="outside",
                textfont=dict(size=9, color="#0f766e"),
            )
        )

        weight_max = pd.concat([
            weight_yoy_df["Weight MT"],
            weight_yoy_df["Prev Weight MT"],
        ]).max()
        weight_max = weight_max if pd.notna(weight_max) and weight_max > 0 else 1

        show_weight_annotations = len(weight_yoy_df) <= 40
        if show_weight_annotations:
            for _, r in weight_yoy_df.iterrows():
                if r["Growth Label"] and r["Growth Label"] != "N/A":
                    label_color = "#166534" if (r["Growth %"] or 0) >= 0 else "#dc2626"
                    bar_top = max(
                        r["Weight MT"] if pd.notna(r["Weight MT"]) else 0,
                        r["Prev Weight MT"] if pd.notna(r["Prev Weight MT"]) else 0,
                    )
                    fig_weight.add_annotation(
                        x=r["Period"],
                        y=bar_top + (weight_max * 0.16),
                        text=r["Growth Label"],
                        showarrow=False,
                        font=dict(size=10, color=label_color, family="Arial Black"),
                    )

        fig_weight.update_layout(
            barmode="group",
            height=250,
            margin=dict(l=2, r=2, t=30, b=2),
            plot_bgcolor="white",
            paper_bgcolor="white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                x=0,
                font=dict(size=9),
            ),
            yaxis_title="Weight (MT)",
            yaxis_range=[0, weight_max * 1.35],
        )
        fig_weight.update_xaxes(showgrid=False, zeroline=False)
        fig_weight.update_yaxes(showgrid=False, zeroline=False)

        st.plotly_chart(fig_weight, use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # =====================================================
    # Zone and Country analysis on the next row
    # =====================================================
    if view_type == "Origin":
        zone_col1, zone_col2 = st.columns([1.05, 1.45])
    else:
        zone_col1 = st.container()
        zone_col2 = None

    with zone_col1:
        with st.container(border=True):
            st.markdown("###### Revenue by Zone")

            # Calculate percentage for each zone
            total_zone_revenue = zone_df["Revenue Cr"].sum()
            zone_df["Percentage"] = (zone_df["Revenue Cr"] / total_zone_revenue * 100).round(1)
            # Keep revenue and contribution percentage as separate values.
            # Plotly renders the revenue as the main bar label and the percentage below it.
            zone_df["Revenue Label"] = zone_df["Revenue Cr"].map(lambda value: f"₹{value:.2f} Cr")
            zone_df["Percentage Label"] = zone_df["Percentage"].map(lambda value: f"{value:.1f}%")
            zone_df["Text"] = zone_df.apply(
                lambda row: f"{row['Revenue Label']}<br><span style='font-size:10px'>({row['Percentage Label']})</span>",
                axis=1,
            )

            # Sort for display
            zone_df_sorted = zone_df.sort_values("Revenue Cr", ascending=True).reset_index(drop=True)

            # Use a direct go.Bar trace so every label is generated from the
            # same row as its bar. This avoids Plotly/Pandas text alignment issues.
            fig_zone = go.Figure(
                go.Bar(
                    y=zone_df_sorted["zone_short"].tolist(),
                    x=zone_df_sorted["Revenue Cr"].tolist(),
                    orientation="h",
                    marker_color=[
                        zone_colors.get(zone_name, "#2563eb")
                        for zone_name in zone_df_sorted["zone"].tolist()
                    ],
                    customdata=zone_df_sorted[["Percentage"]].to_numpy(),
                    texttemplate="₹%{x:.2f} Cr<br>(%{customdata[0]:.1f}%)",
                    textposition="outside",
                    textfont=dict(size=10, color="#475569"),
                    cliponaxis=False,
                    hovertemplate=(
                        "<b>%{y}</b><br>Revenue: ₹%{x:.2f} Cr"
                        "<br>Contribution: %{customdata[0]:.1f}%<extra></extra>"
                    ),
                )
            )

            zone_max = zone_df_sorted["Revenue Cr"].max() if not zone_df_sorted.empty else 1
            fig_zone.update_layout(
                height=240,
                margin=dict(l=2, r=80, t=2, b=2),
                xaxis_range=[0, zone_max * 1.30],
                xaxis_title="Revenue (Cr)",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor="white",
                paper_bgcolor="white",
            )

            st.plotly_chart(fig_zone, use_container_width=True)

    if view_type == "Origin" and zone_col2 is not None:
        with zone_col2:
            with st.container(border=True):
                st.markdown("###### Zone vs Country Revenue (%)")

                matrix_display = matrix_df.reset_index().reset_index(drop=True)

                matrix_display["zone"] = matrix_display["zone"].replace({
                    "NORTH ZONE": "North",
                    "WEST ZONE": "West",
                    "SOUTH ZONE": "South",
                    "EAST ZONE": "East",
                    "NORTH EAST ZONE": "NE",
                    "NEPAL ZONE": "Nepal"
                })

                numeric_cols = matrix_display.columns[1:]

                # The pivot already contains a Total column. Exclude it when calculating
                # the grand total, otherwise every value is counted twice.
                country_cols = [col for col in numeric_cols if col != "Total"]
                grand_total = matrix_display[country_cols].to_numpy().sum() if country_cols else 0

                # Show both revenue and contribution percentage in every cell.
                matrix_value_display = matrix_display.copy()
                for col in country_cols:
                    matrix_value_display[col] = matrix_display[col].apply(
                        lambda value: (
                            f"₹{value:.2f} Cr | {(value / grand_total * 100):.1f}%"
                            if grand_total > 0
                            else f"₹{value:.2f} Cr | 0.0%"
                        )
                    )

                matrix_value_display["Total"] = matrix_display["Total"].apply(
                    lambda value: (
                        f"₹{value:.2f} Cr | {(value / grand_total * 100):.1f}%"
                        if grand_total > 0
                        else f"₹{value:.2f} Cr | 0.0%"
                    )
                )

                st.dataframe(
                    matrix_value_display,
                    use_container_width=True,
                    hide_index=True,
                    height=240,
                )

    # =====================================================
    # Management Key Insights
    # =====================================================
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Zone YoY movement used for management commentary.
    current_zone_insights = (
        df.groupby("zone", dropna=False)["REVENUE"]
        .sum()
        .reset_index(name="Current Revenue")
    )
    if prev_df is not None and not prev_df.empty:
        previous_zone_insights = (
            prev_df.groupby("zone", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Previous Revenue")
        )
        zone_insights = current_zone_insights.merge(
            previous_zone_insights, on="zone", how="outer"
        ).fillna(0)
    else:
        zone_insights = current_zone_insights.copy()
        zone_insights["Previous Revenue"] = 0

    zone_insights["Variance"] = (
        zone_insights["Current Revenue"] - zone_insights["Previous Revenue"]
    )
    zone_insights["Growth %"] = zone_insights.apply(
        lambda row: pct_growth(row["Current Revenue"], row["Previous Revenue"]),
        axis=1,
    )

    positive_zones = zone_insights[zone_insights["Variance"] > 0].sort_values(
        "Variance", ascending=False
    )
    declining_zones = zone_insights[zone_insights["Variance"] < 0].sort_values(
        "Variance"
    )

    zone_name_map = {
        "NORTH ZONE": "North",
        "WEST ZONE": "West",
        "SOUTH ZONE": "South",
        "EAST ZONE": "East",
        "NORTH EAST ZONE": "North East",
        "NEPAL ZONE": "Nepal",
    }
    top_driver_names = [
        zone_name_map.get(str(value), str(value).replace(" ZONE", "").title())
        for value in positive_zones["zone"].head(2).tolist()
    ]
    if len(top_driver_names) >= 2:
        driver_text = f"{top_driver_names[0]} and {top_driver_names[1]} zones"
    elif len(top_driver_names) == 1:
        driver_text = f"the {top_driver_names[0]} zone"
    else:
        driver_text = "the selected business segments"

    overall_insight_growth = pct_growth(revenue, prev_kpis["revenue"])
    revenue_direction = "up" if overall_insight_growth >= 0 else "down"

    ftl_insight_growth = pct_growth(ftl, prev_kpis["ftl"])
    ltl_insight_growth = pct_growth(ltl, prev_kpis["ltl"])
    if ftl_insight_growth >= ltl_insight_growth:
        load_growth_text = (
            f"FTL revenue growth ({ftl_insight_growth:.1f}%) is higher than "
            f"LTL revenue growth ({ltl_insight_growth:.1f}%)."
        )
    else:
        load_growth_text = (
            f"LTL revenue growth ({ltl_insight_growth:.1f}%) is higher than "
            f"FTL revenue growth ({ftl_insight_growth:.1f}%)."
        )

    # Number of branches required to reach 80% of filtered revenue.
    branch_contribution = (
        df.groupby("branch", dropna=False)["REVENUE"]
        .sum()
        .sort_values(ascending=False)
    )
    contribution_total = branch_contribution.sum()
    if contribution_total > 0:
        cumulative_share = branch_contribution.cumsum() / contribution_total
        branches_for_80 = int((cumulative_share < 0.80).sum() + 1)
    else:
        branches_for_80 = 0

    if len(declining_zones) == 1:
        decline_zone_name = zone_name_map.get(
            str(declining_zones.iloc[0]["zone"]),
            str(declining_zones.iloc[0]["zone"]).replace(" ZONE", "").title(),
        )
        zone_decline_text = f"{decline_zone_name} Zone is the only zone showing decline for the selected period."
    elif len(declining_zones) > 1:
        decline_names = [
            zone_name_map.get(str(value), str(value).replace(" ZONE", "").title())
            for value in declining_zones["zone"].head(3).tolist()
        ]
        zone_decline_text = (
            f"{len(declining_zones)} zones are showing decline, led by "
            f"{', '.join(decline_names)}."
        )
    else:
        zone_decline_text = "No zone is showing a decline for the selected period."

    # Branches declining more than 20% vs LY.
    current_branch_insights = (
        df.groupby("branch", dropna=False)["REVENUE"]
        .sum()
        .reset_index(name="Current Revenue")
    )
    if prev_df is not None and not prev_df.empty:
        previous_branch_insights = (
            prev_df.groupby("branch", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Previous Revenue")
        )
        branch_yoy_insights = current_branch_insights.merge(
            previous_branch_insights, on="branch", how="outer"
        ).fillna(0)
        branch_yoy_insights["Growth %"] = branch_yoy_insights.apply(
            lambda row: pct_growth(row["Current Revenue"], row["Previous Revenue"]),
            axis=1,
        )
        branch_decline_count = int(
            (branch_yoy_insights["Growth %"] < -20).sum()
        )
    else:
        branch_decline_count = 0

    key_insight_messages = [
        (
            f"Revenue is {revenue_direction} by {abs(overall_insight_growth):.1f}% vs LY, "
            f"driven by strong performance in {driver_text}."
        ),
        load_growth_text,
        f"Top {branches_for_80} branches contribute to 80% of total revenue.",
        zone_decline_text,
        f"{branch_decline_count} branches have declined more than 20% vs LY.",
    ]

    with st.container(border=True):
        st.markdown(
            "<div style='font-size:13px;font-weight:900;color:#0f2747;margin-bottom:7px;'>KEY INSIGHTS</div>",
            unsafe_allow_html=True,
        )
        for message in key_insight_messages:
            st.markdown(
                f"""
                <div style="display:flex;align-items:flex-start;gap:9px;margin:7px 0;">
                    <div style="width:18px;height:18px;border-radius:50%;background:#22c55e;color:white;
                                display:flex;align-items:center;justify-content:center;font-size:11px;
                                font-weight:900;flex:0 0 18px;box-shadow:0 1px 3px rgba(34,197,94,.25);">✓</div>
                    <div style="font-size:11px;line-height:1.45;color:#1e293b;font-weight:650;">{message}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # =====================================================
    # Management visual: Revenue Waterfall
    # =====================================================
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("###### Revenue Waterfall | Last Year to Current Year (Cr)")

        # Compare zone-level revenue between the selected FY and last year.
        current_zone_waterfall = (
            df.groupby("zone", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Current Revenue")
        )

        if prev_df is not None and not prev_df.empty:
            previous_zone_waterfall = (
                prev_df.groupby("zone", dropna=False)["REVENUE"]
                .sum()
                .reset_index(name="Previous Revenue")
            )
            waterfall_source = current_zone_waterfall.merge(
                previous_zone_waterfall,
                on="zone",
                how="outer",
            )
        else:
            waterfall_source = current_zone_waterfall.copy()
            waterfall_source["Previous Revenue"] = 0

        waterfall_source[["Current Revenue", "Previous Revenue"]] = waterfall_source[
            ["Current Revenue", "Previous Revenue"]
        ].fillna(0)
        waterfall_source["Variance"] = (
            waterfall_source["Current Revenue"]
            - waterfall_source["Previous Revenue"]
        )

        zone_short_map = {
            "NORTH ZONE": "North",
            "WEST ZONE": "West",
            "SOUTH ZONE": "South",
            "EAST ZONE": "East",
            "NORTH EAST ZONE": "North East",
            "NEPAL ZONE": "Nepal",
        }
        waterfall_source["Zone Label"] = (
            waterfall_source["zone"]
            .fillna("Unknown")
            .astype(str)
            .map(lambda value: zone_short_map.get(value, value.replace(" ZONE", "").title()))
        )

        # Keep the chart management-friendly: strongest gains first, then declines.
        waterfall_source = waterfall_source.sort_values(
            ["Variance", "Current Revenue"],
            ascending=[False, False],
        ).reset_index(drop=True)

        previous_total_cr = waterfall_source["Previous Revenue"].sum() / 10000000
        current_total_cr = waterfall_source["Current Revenue"].sum() / 10000000
        waterfall_source["Variance Cr"] = waterfall_source["Variance"] / 10000000

        waterfall_x = (
            ["Last Year Revenue"]
            + waterfall_source["Zone Label"].tolist()
            + ["Current Year Revenue"]
        )
        waterfall_y = (
            [previous_total_cr]
            + waterfall_source["Variance Cr"].tolist()
            + [current_total_cr]
        )
        waterfall_measure = (
            ["absolute"]
            + ["relative"] * len(waterfall_source)
            + ["total"]
        )
        waterfall_text = (
            [f"{previous_total_cr:.2f}"]
            + [f"{value:+.2f}" for value in waterfall_source["Variance Cr"]]
            + [f"{current_total_cr:.2f}"]
        )

        fig_waterfall = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=waterfall_measure,
                x=waterfall_x,
                y=waterfall_y,
                text=waterfall_text,
                textposition="outside",
                textfont=dict(size=10, color="#0f172a"),
                connector={"line": {"color": "#94a3b8", "width": 1}},
                increasing={"marker": {"color": "#22c55e"}},
                decreasing={"marker": {"color": "#ef4444"}},
                totals={"marker": {"color": "#0f2747"}},
                hovertemplate=(
                    "<b>%{x}</b><br>Revenue movement: ₹%{y:.2f} Cr<extra></extra>"
                ),
            )
        )

        overall_waterfall_growth = pct_growth(
            current_total_cr,
            previous_total_cr,
        )
        waterfall_growth_color = (
            "#166534" if overall_waterfall_growth >= 0 else "#dc2626"
        )
        waterfall_growth_arrow = "▲" if overall_waterfall_growth >= 0 else "▼"

        fig_waterfall.add_annotation(
            x=0.5,
            y=1.11,
            xref="paper",
            yref="paper",
            text=(
                f"<b>{waterfall_growth_arrow} "
                f"{abs(overall_waterfall_growth):.1f}% Overall Growth</b>"
            ),
            showarrow=False,
            font=dict(size=12, color=waterfall_growth_color),
        )

        chart_max = max(
            previous_total_cr,
            current_total_cr,
            1,
        )
        fig_waterfall.update_layout(
            height=320,
            margin=dict(l=5, r=5, t=45, b=45),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=False,
            yaxis_title="Revenue (Cr)",
            yaxis_range=[0, chart_max * 1.35],
            waterfallgap=0.35,
        )
        fig_waterfall.update_xaxes(
            title="",
            showgrid=False,
            tickangle=-20,
            tickfont=dict(size=10),
        )
        fig_waterfall.update_yaxes(
            showgrid=True,
            gridcolor="#e2e8f0",
            zeroline=False,
        )

        st.plotly_chart(fig_waterfall, use_container_width=True)


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

    b1, b2, b3 = st.columns([1, 1, 0.95])

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

    # =====================================================
    # Branch/Agency Network Changes - NOW FILTERED BY MONTH & QUARTER
    # =====================================================
    
    # Filter station_df based on selected month and quarter
    filtered_station_df = station_df.copy()
    
    # Only filter if FIN_MONTH column exists and has valid values
    if "FIN_MONTH" in filtered_station_df.columns and filtered_station_df["FIN_MONTH"].notna().any():
        if month != "All":
            # Filter by specific month
            fin_month_for_month = [k for k, v in month_map.items() if v == month]
            if fin_month_for_month:
                filtered_station_df = filtered_station_df[filtered_station_df["FIN_MONTH"].isin(fin_month_for_month)]
        elif quarter != "All":
            # Filter by quarter
            quarter_fin_months = [k for k, v in QUARTER_MAP.items() if v == quarter]
            filtered_station_df = filtered_station_df[filtered_station_df["FIN_MONTH"].isin(quarter_fin_months)]
    
    opened_df = filtered_station_df[filtered_station_df["STATUS"] == "OPENED"]
    closed_df = filtered_station_df[filtered_station_df["STATUS"] == "CLOSED"]

    opened_branches = len(opened_df)
    closed_branches = len(closed_df)
    net_increase = opened_branches - closed_branches

    period_label = f"{fy}"
    if month != "All":
        period_label = f"{month} {fy}"
    elif quarter != "All":
        period_label = f"{quarter} {fy}"

    st.markdown(f"""
    ###### 🏢 Branch/Agency Network Changes ({period_label})

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
