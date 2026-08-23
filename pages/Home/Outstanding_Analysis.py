"""
pages/Home/Outstanding_Analysis.py
==================================

Outstanding Analysis dashboard using the Alloutstanding_BI stored procedure.
RESPONSIVE MERGED VERSION - full analytical insights retained.

Stored procedure call:
    EXEC dbo.Alloutstanding_BI
        '00000',
        'C',
        @FromDate,
        @ToDate,
        @AsOnDate,
        '0000',
        '',
        'SYST'

Only three report parameters are selected by the user:
    1. From Date
    2. To Date
    3. As On Date

The database query runs only when the user clicks Run Report.

Database credentials are handled centrally by services.database.get_engine()
through services.data_outstanding.get_outstanding_data().

Role-based data scope is read from:
    st.session_state["data_scope"]

Supported scope examples:
    {}
    {"zone": "NORTH EAST ZONE"}
    {"circle": "ASSAM - NE"}
    {"branch": "AGARTALA"}

------------------------------------------------------------------------------
CHANGES IN THIS VERSION
------------------------------------------------------------------------------
1. The "Show only pending records" checkbox and its underlying filter have
   been removed entirely. The page now always shows every row returned by
   the stored procedure for the selected date range -- fully settled and
   still-pending invoices alike.

2. A Conversion filter lets the user switch all dashboard-level monetary
   values between ₹ Crore and ₹ Lac. KPI cards, charts and grouped summary
   tables follow the selected unit. The Detailed Records table remains in
   plain ₹ because it shows individual invoice-level rows.

3. Previous-period (PY) growth-arrow comparison has been removed. KPI cards
   now show plain values only, with no ▲/▼ badge and no second stored
   procedure call for the preceding period.

4. "Total Billed" and "Total Received" KPI cards have been replaced with
   "Total Invoices" and "Total Customers" (plain counts), which removes the
   ambiguity those two amount-based cards used to cause.

5. Zone, Circle and Branch now use the same native cascading multiselect
   filters as the Overview page. Customer is also a cascading multiselect,
   allowing several customers to be analysed together.
------------------------------------------------------------------------------
"""

import io
from datetime import date, datetime
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.data_Outstanding import get_outstanding_data


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

ACCENT = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "red": "#dc2626",
    "amber": "#d97706",
    "purple": "#7c3aed",
    "teal": "#0d9488",
}

AGE_BUCKET_ORDER = ["0-30", "31-60", "61-90", "Above 90"]

DOCUMENT_TYPE_MAP = {
    "BILL-GATEPASS CUSTOMER": "BILL",
    "BILL-PAID CUSTOMER": "BILL",
    "OPENING BILL": "BILL",
    "ON A/C RECEIPT": "ON A/C Receipt",
    "ON A/C RECEIPT -GATEPASS CUSTOMER": "ON A/C Receipt",
    "ON A/C RECEIPT -PAID CUSTOMER": "ON A/C Receipt",
    "PAID OUTSTANDING": "UNBILLED",
    "TOPAY": "UNBILLED",
    "UNBILLED GATEPASS": "UNBILLED",
    "UNBILLED GR": "UNBILLED",
}

# Fixed stored-procedure parameters.
SP_BRANCH = "00000"
SP_GRTYPE = "C"
SP_CUSTCODE = "0000"
SP_INVOICENO = ""
SP_USER = "SYST"


# ---------------------------------------------------------------------------
# STYLING
# ---------------------------------------------------------------------------

def _inject_css():
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 0.5rem;
                padding-bottom: 1rem;
            }

            .oa-kpi-card {
                background: linear-gradient(135deg, #ffffff 0%, #f3f6fb 100%);
                border-radius: 14px;
                padding: 9px 11px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.06);
                border-left: 6px solid var(--accent, #2563eb);
                text-align: left;
                min-height: 78px;
            }

            .oa-kpi-label {
                font-size: 10px;
                color: #64748b;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: .04em;
                margin-bottom: 4px;
            }

            .oa-kpi-value-row {
                display: flex;
                align-items: baseline;
                gap: 8px;
                flex-wrap: wrap;
            }

            .oa-kpi-value {
                font-size: 18px;
                font-weight: 800;
                color: #111827;
            }

            .oa-kpi-sub {
                font-size: 9px;
                color: #94a3b8;
                margin-top: 2px;
            }

            .oa-section-title {
                font-size: 19px;
                font-weight: 700;
                color: #111827;
                margin: 18px 0 6px 0;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 6px;
            }

            /* Outstanding header: title + active filter chips on one line. */
            .oa-header-row {
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 8px;
                width: 100%;
                min-height: 36px;
                padding: 1px 0 1px 2px;
            }

            .oa-header-title {
                color: #102a43;
                font-size: 21px;
                font-weight: 850;
                letter-spacing: -0.3px;
                margin-right: 8px;
                white-space: nowrap;
                line-height: 1.15;
            }

            .oa-filter-chip {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-height: 28px;
                padding: 6px 13px;
                border: 1px solid #b8d1f2;
                border-radius: 999px;
                background: #f5f9ff;
                color: #31557d;
                font-size: 11px;
                font-weight: 500;
                line-height: 1;
                white-space: nowrap;
                box-shadow: inset 0 1px 0 #ffffff;
            }

            /* Keep the bordered dashboard header compact like Business Overview. */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.oa-header-row) {
                border-radius: 14px !important;
                border-color: #d8e3f0 !important;
                background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%) !important;
                box-shadow: 0 4px 12px rgba(15, 42, 67, .06) !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:has(.oa-header-row) > div {
                padding-top: .45rem !important;
                padding-bottom: .45rem !important;
            }

            /* Header Excel action styled like the Overview dashboard action. */
            div[data-testid="stDownloadButton"] > button {
                min-height: 34px !important;
                width: auto !important;
                padding: 5px 11px !important;
                border: 1px solid #2563eb !important;
                border-radius: 8px !important;
                color: #ffffff !important;
                font-size: 11px !important;
                font-weight: 800 !important;
                background: linear-gradient(145deg, #3b82f6 0%, #2563eb 58%, #1d4ed8 100%) !important;
                box-shadow: 0 3px 0 #1e40af, 0 6px 10px rgba(37,99,235,.18) !important;
            }

            /* Overview-style searchable multi-select slicers */
            .checkbox-slicer-label {display:block;height:20px;line-height:20px;margin:0 0 6px 2px;color:#243b53;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
            div[data-testid="stPopover"] {width:100% !important;margin:0 !important;padding:0 !important;}
            div[data-testid="stPopover"] > div {width:100% !important;}
            div[data-testid="stPopover"] > div > button {width:100% !important;min-height:40px !important;height:40px !important;padding:0 9px !important;border:1px solid #cbd9ea !important;border-radius:10px !important;background:linear-gradient(180deg,#ffffff 0%,#f5f8fc 100%) !important;color:#102a43 !important;font-size:11px !important;font-weight:800 !important;justify-content:space-between !important;}
            div[data-testid="stPopoverBody"] {max-height:360px !important;overflow-y:auto !important;}

            /* Business Overview-style dataframe treatment */
            [data-testid="stDataFrame"] {
                border: 1px solid #e2eaf3 !important;
                border-radius: 12px !important;
                overflow: hidden !important;
                background: #fbfdff !important;
                box-shadow: 0 3px 10px rgba(15,42,67,.07) !important;
            }

            [data-testid="stDataFrame"] table {
                font-size: 11px !important;
            }

            [data-testid="stDataFrame"] tbody tr {
                height: 24px !important;
            }

            [data-testid="stDataFrame"] thead tr {
                height: 28px !important;
            }

            [data-testid="stDataFrame"] thead th {
                background: #f8fafc !important;
                color: #64748b !important;
                font-size: 11px !important;
                font-weight: 500 !important;
                border-bottom: 1px solid #e2e8f0 !important;
            }

            [data-testid="stDataFrame"] tbody td {
                color: #334155 !important;
                border-bottom: 1px solid #edf2f7 !important;
            }

            /* Fit the complete date/filter toolbar into one Overview-style row. */
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                min-width: 0 !important;
            }
            div[data-testid="stDateInput"] label,
            div[data-testid="stSelectbox"] label {
                font-size: 10px !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
            div[data-testid="stDateInput"] input,
            div[data-baseweb="select"] span {
                font-size: 11px !important;
            }
            .stButton > button {
                min-height: 40px !important;
                border-radius: 10px !important;
                font-size: 11px !important;
            }


            /* ===== RESPONSIVE / MOBILE ENHANCEMENTS (merged from new version) ===== */
            .block-container {
                padding-left: 0.5rem;
                padding-right: 0.5rem;
                max-width: 100%;
            }

            .oa-kpi-card {
                position: relative;
                overflow: hidden;
            }

            .plotly, .plotly-graph-div {
                width: 100% !important;
            }

            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                min-width: 0 !important;
            }

            @media (max-width: 640px) {
                .block-container {
                    padding-top: 0.3rem;
                    padding-bottom: 0.5rem;
                    padding-left: 0.3rem;
                    padding-right: 0.3rem;
                }

                .oa-kpi-card {
                    padding: 10px 30px 10px 10px;
                    margin-bottom: 0.4rem;
                    min-height: 65px;
                    border-radius: 12px;
                }

                .oa-kpi-value { font-size: 14px; }
                .oa-kpi-label { font-size: 8px; }
                .oa-kpi-sub { font-size: 8px; }

                .oa-section-title {
                    font-size: 14px;
                    margin: 12px 0 6px 0;
                }

                .oa-header-title {
                    font-size: 16px;
                    white-space: normal;
                    min-width: 140px;
                }

                .oa-header-row {
                    gap: 4px;
                    padding: 6px 4px;
                }

                .oa-filter-chip {
                    font-size: 9px;
                    padding: 4px 9px;
                    min-height: 24px;
                }

                div[data-testid="stDateInput"] input,
                div[data-baseweb="select"] span,
                input[type="text"], input[type="date"], select {
                    font-size: 13px !important;
                }

                .stButton > button,
                div[data-testid="stDownloadButton"] > button {
                    min-height: 40px !important;
                    font-size: 12px !important;
                }

                [data-testid="stDataFrame"] table { font-size: 10px !important; }
                [data-testid="stDataFrame"] thead th { font-size: 10px !important; }

                /* Streamlit columns naturally wrap on narrow screens; make each usable. */
                [data-testid="column"] { min-width: 0 !important; }
            }

            @media (min-width: 641px) and (max-width: 1024px) {
                .block-container {
                    padding-top: 0.4rem;
                    padding-bottom: 0.8rem;
                    padding-left: 0.6rem;
                    padding-right: 0.6rem;
                }

                .oa-kpi-card { min-height: 72px; }
                .oa-kpi-value { font-size: 15px; }
                .oa-section-title { font-size: 15px; margin: 14px 0 6px 0; }
                .oa-header-title { font-size: 17px; }
            }

            @media (min-width: 1025px) {
                .block-container {
                    padding-top: 0.5rem;
                    padding-bottom: 1rem;
                    padding-left: 1rem;
                    padding-right: 1rem;
                }
            }


            /* ===== STRUCTURED RESPONSIVE GRIDS ===== */
            .oa-responsive-marker { display:none !important; }
            /* Hide the Streamlit wrapper too. The empty wrapper previously
               pushed only the first date control down by one row. */
            div[data-testid="stElementContainer"]:has(.oa-responsive-marker) {
                display: none !important;
                height: 0 !important;
                min-height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            @media (max-width: 640px) {
                /* Filter toolbar: 2 controls per row, Run Report full width. */
                div[data-testid="stHorizontalBlock"]:has(.oa-filter-grid-marker) {
                    flex-wrap: wrap !important;
                    gap: .45rem !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-filter-grid-marker) > div[data-testid="stColumn"] {
                    flex: 1 1 calc(50% - .45rem) !important;
                    width: calc(50% - .45rem) !important;
                    min-width: calc(50% - .45rem) !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-filter-grid-marker) > div[data-testid="stColumn"]:last-child {
                    flex-basis: 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }

                /* KPI cards: 2 per row on normal phones. */
                div[data-testid="stHorizontalBlock"]:has(.oa-kpi-grid-marker) {
                    flex-wrap: wrap !important;
                    gap: .45rem !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-kpi-grid-marker) > div[data-testid="stColumn"] {
                    flex: 1 1 calc(50% - .45rem) !important;
                    width: calc(50% - .45rem) !important;
                    min-width: calc(50% - .45rem) !important;
                }

                /* Analytical chart/table pairs: one panel per row. */
                div[data-testid="stHorizontalBlock"]:has(.oa-stack-grid-marker) {
                    flex-wrap: wrap !important;
                    gap: .6rem !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-stack-grid-marker) > div[data-testid="stColumn"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }

                /* Header title and Excel action stack cleanly. */
                div[data-testid="stHorizontalBlock"]:has(.oa-header-grid-marker) {
                    flex-wrap: wrap !important;
                    gap: .35rem !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-header-grid-marker) > div[data-testid="stColumn"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-header-grid-marker) div[data-testid="stDownloadButton"] > button {
                    width: 100% !important;
                }

                /* Make popovers/selects and text inputs touch friendly. */
                div[data-testid="stPopover"] > div > button,
                div[data-baseweb="select"] > div,
                div[data-testid="stTextInput"] input,
                div[data-testid="stDateInput"] input {
                    min-height: 42px !important;
                }

                /* Plotly labels get more usable horizontal room. */
                .js-plotly-plot, .plot-container, .svg-container {
                    max-width: 100% !important;
                }

                /* Tables should scroll horizontally rather than squeeze columns. */
                [data-testid="stDataFrame"] {
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch;
                }
                .oa-scale-wrap {
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch;
                }
            }

            @media (max-width: 420px) {
                /* Very narrow phones: use one control/card per row. */
                div[data-testid="stHorizontalBlock"]:has(.oa-filter-grid-marker) > div[data-testid="stColumn"],
                div[data-testid="stHorizontalBlock"]:has(.oa-kpi-grid-marker) > div[data-testid="stColumn"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
                .oa-kpi-card { min-height: 62px; }
                .oa-filter-chip { max-width: 100%; overflow:hidden; text-overflow:ellipsis; }
            }

            @media (min-width: 641px) and (max-width: 1024px) {
                /* Tablet: filters 3 per row and KPI cards 3 per row. */
                div[data-testid="stHorizontalBlock"]:has(.oa-filter-grid-marker),
                div[data-testid="stHorizontalBlock"]:has(.oa-kpi-grid-marker) {
                    flex-wrap: wrap !important;
                    gap: .55rem !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-filter-grid-marker) > div[data-testid="stColumn"],
                div[data-testid="stHorizontalBlock"]:has(.oa-kpi-grid-marker) > div[data-testid="stColumn"] {
                    flex: 1 1 calc(33.333% - .55rem) !important;
                    width: calc(33.333% - .55rem) !important;
                    min-width: calc(33.333% - .55rem) !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-stack-grid-marker) {
                    flex-wrap: wrap !important;
                    gap: .65rem !important;
                }
                div[data-testid="stHorizontalBlock"]:has(.oa-stack-grid-marker) > div[data-testid="stColumn"] {
                    flex: 1 1 100% !important;
                    width: 100% !important;
                    min-width: 100% !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(label, value, sub="", color="blue"):
    """
    Render one KPI card (plain value, no growth badge).
    """
    st.markdown(
        f"""
        <div class="oa-kpi-card" style="--accent:{ACCENT.get(color, '#2563eb')}">
            <div class="oa-kpi-label">{label}</div>
            <div class="oa-kpi-value-row">
                <div class="oa-kpi-value">{value}</div>
            </div>
            <div class="oa-kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_outstanding_header(placeholder, active_filters=None):
    """Render Outstanding Analysis title with active-filter chips beside it."""
    active_filters = active_filters or []

    chip_html = "".join(
        f'<span class="oa-filter-chip">{escape(str(label))}: {escape(str(value))}</span>'
        for label, value in active_filters
        if value not in (None, "", "All", "Not available")
    )

    with placeholder:
        st.markdown(
            f"""
            <div class="oa-header-row">
                <div class="oa-header-title">Outstanding Analysis</div>
                {chip_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _get_conversion(conversion_type):
    """Return the rupee divisor and short display unit for the selected view."""
    return (1_00_000, "Lac") if conversion_type == "Lac" else (1_00_00_000, "Cr")


def _inr_amount(value, conversion_type):
    """Format a rupee value in the selected Crore/Lac display unit."""
    divisor, unit = _get_conversion(conversion_type)
    try:
        value = float(value)
    except (TypeError, ValueError):
        return f"₹0.00 {unit}"

    negative = value < 0
    display_value = abs(value) / divisor
    return f"{'-' if negative else ''}₹{display_value:,.2f} {unit}"


def _find_column(df, candidates):
    """
    Return the first matching column name.

    The function first checks exact lowercase names and then checks normalized
    names so it can handle variations such as:
        zonename / zone_name / zone
        circlename / circle_name / circle
        branchname / branch_name / branch
    """
    if df is None or df.empty:
        return None

    exact_map = {str(col).strip().lower(): col for col in df.columns}

    for candidate in candidates:
        key = candidate.strip().lower()
        if key in exact_map:
            return exact_map[key]

    normalized_map = {
        str(col).strip().lower().replace("_", "").replace(" ", ""): col
        for col in df.columns
    }

    for candidate in candidates:
        key = candidate.strip().lower().replace("_", "").replace(" ", "")
        if key in normalized_map:
            return normalized_map[key]

    return None


def _match_scope_value(series, scope_value):
    """
    Return rows matching a role-scope value.

    Comparison is case-insensitive and ignores leading/trailing spaces.
    """
    if scope_value is None:
        return pd.Series(True, index=series.index)

    target = str(scope_value).strip().casefold()

    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
        .eq(target)
    )


def _match_scope_values(series, scope_values):
    """Return rows matching any selected value, ignoring case and spaces."""
    if not scope_values:
        return pd.Series(True, index=series.index)

    targets = {
        str(value).strip().casefold()
        for value in scope_values
        if value is not None and str(value).strip()
    }
    if not targets:
        return pd.Series(True, index=series.index)

    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
        .isin(targets)
    )


def _derive_role_scope(df, zone_col, circle_col, branch_col):
    """
    Read role rights from session state and derive parent hierarchy.

    If branch is assigned:
        derive its circle and zone from the loaded data.

    If circle is assigned:
        derive its zone from the loaded data.
    """
    data_scope = st.session_state.get("data_scope", {}) or {}

    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    if locked_branch and branch_col:
        branch_rows = df[_match_scope_value(df[branch_col], locked_branch)]

        if not branch_rows.empty:
            # Use the exact value returned by the database.
            locked_branch = branch_rows[branch_col].iloc[0]

            if circle_col and pd.notna(branch_rows[circle_col].iloc[0]):
                locked_circle = branch_rows[circle_col].iloc[0]

            if zone_col and pd.notna(branch_rows[zone_col].iloc[0]):
                locked_zone = branch_rows[zone_col].iloc[0]

    elif locked_circle and circle_col:
        circle_rows = df[_match_scope_value(df[circle_col], locked_circle)]

        if not circle_rows.empty:
            locked_circle = circle_rows[circle_col].iloc[0]

            if zone_col and pd.notna(circle_rows[zone_col].iloc[0]):
                locked_zone = circle_rows[zone_col].iloc[0]

    elif locked_zone and zone_col:
        zone_rows = df[_match_scope_value(df[zone_col], locked_zone)]

        if not zone_rows.empty:
            locked_zone = zone_rows[zone_col].iloc[0]

    return locked_zone, locked_circle, locked_branch


def _apply_locked_scope(
    df,
    zone_col,
    circle_col,
    branch_col,
    locked_zone,
    locked_circle,
    locked_branch,
):
    """
    Restrict the dataframe before normal dashboard filters are created.
    """
    scoped_df = df

    if locked_zone and zone_col:
        scoped_df = scoped_df[
            _match_scope_value(scoped_df[zone_col], locked_zone)
        ]

    if locked_circle and circle_col:
        scoped_df = scoped_df[
            _match_scope_value(scoped_df[circle_col], locked_circle)
        ]

    if locked_branch and branch_col:
        scoped_df = scoped_df[
            _match_scope_value(scoped_df[branch_col], locked_branch)
        ]

    return scoped_df


def _sorted_values(df, column):
    if not column or column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[values.ne("")]

    return sorted(values.unique().tolist(), key=str.casefold)


def _prune_multiselect_state(key, allowed_options):
    """Remove stale selections when a parent cascading filter changes."""
    if key not in st.session_state:
        return

    current = st.session_state.get(key, [])
    if isinstance(current, (list, tuple, set)):
        st.session_state[key] = [
            value for value in current if value in allowed_options
        ]


def _validate_dates(from_date, to_date, as_on_date):
    if from_date > to_date:
        return "From Date cannot be later than To Date."

    if as_on_date < from_date:
        return "As On Date cannot be earlier than From Date."

    return None


@st.cache_data(show_spinner=False, ttl=600, max_entries=1)
def _outstanding_excel_bytes(df: pd.DataFrame) -> bytes:
    """Build the current export once instead of on every widget rerun."""
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Outstanding")
    return excel_buffer.getvalue()


def _safe_selectbox(
    label,
    options,
    key,
    *,
    disabled=False,
    help_text=None,
):
    """
    Render a selectbox safely when its options change between reruns.

    Streamlit keeps widget values in session_state. If a previously selected
    value is no longer present in the new option list, reset it before creating
    the widget. This prevents errors when Zone/Circle/Branch filters cascade.
    """
    clean_options = list(options)

    if not clean_options:
        clean_options = ["Not available"]
        disabled = True

    current_value = st.session_state.get(key)

    if current_value not in clean_options:
        st.session_state[key] = clean_options[0]

    return st.selectbox(
        label,
        clean_options,
        key=key,
        disabled=disabled,
        help=help_text,
    )



def _checkbox_slicer(label, options, key, locked_values=None, searchable=True):
    options = [x for x in options if pd.notna(x)]
    options = list(dict.fromkeys(options))
    st.markdown(f'<div class="checkbox-slicer-label">{escape(str(label))}</div>', unsafe_allow_html=True)
    if locked_values:
        locked_values = [x for x in locked_values if x is not None]
        summary = str(locked_values[0]) if len(locked_values) == 1 else f"{len(locked_values)} selected"
        with st.popover(summary, use_container_width=True):
            for value in locked_values:
                st.checkbox(str(value), value=True, disabled=True, key=f"{key}__locked__{value}")
        return locked_values
    selection_key = f"{key}__instant_selected"
    current = st.session_state.get(selection_key, [])
    st.session_state[selection_key] = [value for value in current if value in options]
    selected_before = st.session_state.get(selection_key, [])
    summary = "All" if not selected_before else (str(selected_before[0]) if len(selected_before) == 1 else f"{len(selected_before)} selected")
    with st.popover(summary, use_container_width=True):
        actions = st.columns(2, gap="small")
        with actions[0]:
            if st.button("Select all", key=f"{key}__select_all"):
                st.session_state[selection_key] = list(options); st.rerun()
        with actions[1]:
            if st.button("Clear", key=f"{key}__clear"):
                st.session_state[selection_key] = []; st.rerun()
        selected_values = st.multiselect(label, options=options, key=selection_key, placeholder="Type to search...", label_visibility="collapsed")
    return selected_values


def _render_scale_table(df, name_col, value_col, value_label, unit, secondary_cols=None, max_rows=50, accent="#7c3aed"):
    secondary_cols = secondary_cols or []
    if df is None or df.empty or name_col not in df.columns or value_col not in df.columns:
        st.info("No table data is available for the selected filters."); return
    view = df.copy().head(max_rows).reset_index(drop=True)
    vals = pd.to_numeric(view[value_col], errors="coerce").fillna(0.0)
    max_abs = max(float(vals.abs().max()), 1.0)
    rows=[]
    for idx,row in view.iterrows():
        raw=float(pd.to_numeric(pd.Series([row[value_col]]),errors="coerce").fillna(0).iloc[0])
        width=min(abs(raw)/max_abs*100,100); name=escape(str(row[name_col])); extras=[]
        for col,label,kind in secondary_cols:
            val=row.get(col,0)
            if kind=="money": extras.append(f'<td class="oa-scale-num">₹{float(val):,.2f} {escape(unit)}</td>')
            elif kind=="int": extras.append(f'<td class="oa-scale-num">{int(val):,}</td>')
            else: extras.append(f'<td class="oa-scale-num">{escape(str(val))}</td>')
        rows.append('<tr>'+f'<td class="oa-scale-rank">{idx+1}</td>'+f'<td class="oa-scale-name" title="{name}">{name}</td>'+f'<td><div class="oa-scale-track"><div class="oa-scale-fill" style="width:{width:.1f}%;background:{accent};"></div></div></td>'+f'<td class="oa-scale-num">₹{raw:,.2f} {escape(unit)}</td>'+''.join(extras)+'</tr>')
    heads=''.join(f'<th style="text-align:right;">{escape(label)}</th>' for _,label,_ in secondary_cols)
    html=("<style>.oa-scale-wrap{width:100%;overflow:auto;border:1px solid #e2e8f0;border-radius:10px;background:#fff}.oa-scale-table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:11px;color:#334155}.oa-scale-table th{padding:7px 6px;background:#f8fafc;color:#64748b;font-weight:500;border-bottom:1px solid #e2e8f0;text-align:left}.oa-scale-table td{padding:7px 6px;border-bottom:1px solid #edf2f7;vertical-align:middle}.oa-scale-table tbody tr:hover{background:#f8fbff}.oa-scale-rank{width:5%;text-align:center;color:#64748b}.oa-scale-name{width:28%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.oa-scale-track{width:100%;height:7px;background:#e8eef8;border-radius:999px;overflow:hidden}.oa-scale-fill{height:7px;border-radius:999px}.oa-scale-num{text-align:right;white-space:nowrap;font-weight:600;color:#0f172a}</style>"+f'<div class="oa-scale-wrap"><table class="oa-scale-table"><thead><tr><th>#</th><th>{escape(str(name_col).replace("_"," ").title())}</th><th>Scale</th><th style="text-align:right;">{escape(value_label)}</th>{heads}</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>')
    if hasattr(st,"html"): st.html(html)
    else: st.markdown(html,unsafe_allow_html=True)


def _clear_old_outstanding_widget_state():
    """
    Remove keys used by older versions of this page.

    Earlier code used 'oa_branch' for the stored-procedure branch text input.
    The current page uses a Branch filter, so stale values such as '00000'
    can conflict with the new selectbox after deployment.
    """
    old_keys = [
        "oa_branch",
        "oa_grtype",
        "oa_fromdt",
        "oa_todt",
        "oa_asondt",
        "oa_custcode",
        "oa_invoiceno",
        "oa_user",
        "oa_f_zone",
        "oa_f_branch",
        "oa_f_cust",
        "oa_f_doctype",
        "oa_f_bucket",
    ]

    if not st.session_state.get("oa_widget_state_migrated_v2"):
        for old_key in old_keys:
            st.session_state.pop(old_key, None)

        st.session_state["oa_widget_state_migrated_v2"] = True


# ---------------------------------------------------------------------------
# PAGE
# ---------------------------------------------------------------------------

def show_OutstandingAnalysis():
    _clear_old_outstanding_widget_state()
    _inject_css()

    # -----------------------------------------------------------------------
    # DASHBOARD HEADER
    # Title and active filter chips follow the Business Overview layout.
    # -----------------------------------------------------------------------

    with st.container(border=True):
        header_left, header_right = st.columns(
            [7, 1],
            gap="small",
            vertical_alignment="center",
        )

        with header_left:
            st.markdown('<span class="oa-responsive-marker oa-header-grid-marker"></span>', unsafe_allow_html=True)
            header_content_placeholder = st.empty()

        with header_right:
            header_action_placeholder = st.empty()

    # Always show the page title, even before the first report is run.
    _render_outstanding_header(header_content_placeholder)

    # -----------------------------------------------------------------------
    # REPORT DATES / INITIAL LOAD
    # -----------------------------------------------------------------------

    default_from_date = date(1980, 1, 1)
    default_to_date = date.today()
    default_as_on_date = date.today()

    # On the very first visit there is no report dataframe yet, so only the
    # three stored-procedure dates and Run Report are shown. After the first
    # successful run, dates + all dashboard filters are rendered in ONE row.
    if "oa_df" not in st.session_state:
        date_col1, date_col2, date_col3, run_col = st.columns(
            [1.25, 1.25, 1.25, 0.9],
            gap="small",
            vertical_alignment="bottom",
        )

        with date_col1:
            st.markdown('<span class="oa-responsive-marker oa-filter-grid-marker"></span>', unsafe_allow_html=True)
            from_date = st.date_input(
                "From Date",
                value=st.session_state.get("oa_from_date", default_from_date),
                format="DD/MM/YYYY",
                key="oa_from_date",
            )

        with date_col2:
            to_date = st.date_input(
                "To Date",
                value=st.session_state.get("oa_to_date", default_to_date),
                format="DD/MM/YYYY",
                key="oa_to_date",
            )

        with date_col3:
            as_on_date = st.date_input(
                "As On Date",
                value=st.session_state.get("oa_as_on_date", default_as_on_date),
                format="DD/MM/YYYY",
                key="oa_as_on_date",
            )

        with run_col:
            run_report = st.button(
                "Run Report",
                type="primary",
                key="oa_run_report_initial",
                width="stretch",
            )

        date_error = _validate_dates(from_date, to_date, as_on_date)
        if date_error:
            st.error(date_error)
            return

        if run_report:
            try:
                loaded_df = get_outstanding_data(
                    branch=SP_BRANCH,
                    grtype=SP_GRTYPE,
                    from_date=from_date,
                    to_date=to_date,
                    as_on_date=as_on_date,
                    custcode=SP_CUSTCODE,
                    invoiceno=SP_INVOICENO,
                    user=SP_USER,
                )
                st.session_state["oa_df"] = loaded_df
                st.session_state["oa_loaded_dates"] = (from_date, to_date, as_on_date)
                st.session_state["oa_last_refreshed"] = datetime.now()
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to load outstanding data: {exc}")
                return

        st.info("Select the three dates and click **Run Report** to load data.")
        return

    # A report is already loaded. The date widgets are rendered later in the
    # same single row as Zone/Circle/Branch/Customer/etc.
    from_date = st.session_state.get("oa_from_date", default_from_date)
    to_date = st.session_state.get("oa_to_date", default_to_date)
    as_on_date = st.session_state.get("oa_as_on_date", default_as_on_date)

    df = st.session_state["oa_df"].copy(deep=False)

    if df.empty:
        st.warning("No outstanding data was found for the selected dates.")
        return

    # -----------------------------------------------------------------------
    # DETECT AVAILABLE HIERARCHY COLUMNS
    # -----------------------------------------------------------------------

    # Exact hierarchy columns now returned by Alloutstanding_BI:
    #   s.zonename AS zone
    #   s.hubname  AS circle
    #   o.branchname
    zone_col = "zone" if "zone" in df.columns else None
    circle_col = "circle" if "circle" in df.columns else None
    branch_col = "branchname" if "branchname" in df.columns else None
    customer_col = _find_column(
        df,
        ["custname", "customername", "customer_name", "customer"],
    )
    document_col = _find_column(
        df,
        ["documenttype", "document_type", "doctype"],
    )
    age_bucket_col = _find_column(
        df,
        ["age_bucket", "agebucket"],
    )

    # Keep the raw document type intact, but use a consolidated dashboard category
    # where known variants map to BILL / ON A/C Receipt / UNBILLED.
    if document_col:
        df["documenttype_dashboard"] = (
            df[document_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .apply(lambda x: DOCUMENT_TYPE_MAP.get(x.upper(), x if x else "Unknown"))
        )
        document_col = "documenttype_dashboard"

    missing_hierarchy = [
        name
        for name, column in {
            "zone": zone_col,
            "circle": circle_col,
            "branchname": branch_col,
        }.items()
        if column is None
    ]

    if missing_hierarchy:
        st.error(
            "Outstanding stored procedure is missing required hierarchy columns: "
            + ", ".join(missing_hierarchy)
        )
        return

    # -----------------------------------------------------------------------
    # ROLE-BASED DATA SCOPE
    # -----------------------------------------------------------------------

    locked_zone, locked_circle, locked_branch = _derive_role_scope(
        df,
        zone_col,
        circle_col,
        branch_col,
    )

    scoped_df = _apply_locked_scope(
        df,
        zone_col,
        circle_col,
        branch_col,
        locked_zone,
        locked_circle,
        locked_branch,
    )

    if scoped_df.empty:
        st.error(
            "No data is available for your assigned Zone, Circle or Branch rights."
        )
        return

    # -----------------------------------------------------------------------
    # DATES + ALL DASHBOARD FILTERS IN ONE ROW (Overview-style)
    # -----------------------------------------------------------------------
    # 11 controls in one compact row:
    # From | To | As On | Zone | Circle | Branch | Customer | Document |
    # Age Bucket | Conversion | Run Report
    filter_columns = st.columns(
        [1.05, 1.05, 1.05, 0.95, 0.95, 0.95, 1.08, 1.00, 0.90, 0.82, 0.82],
        gap="small",
        vertical_alignment="bottom",
    )

    with filter_columns[0]:
        st.markdown('<span class="oa-responsive-marker oa-filter-grid-marker"></span>', unsafe_allow_html=True)
        from_date = st.date_input(
            "From Date",
            value=st.session_state.get("oa_from_date", default_from_date),
            format="DD/MM/YYYY",
            key="oa_from_date",
        )
    with filter_columns[1]:
        to_date = st.date_input(
            "To Date",
            value=st.session_state.get("oa_to_date", default_to_date),
            format="DD/MM/YYYY",
            key="oa_to_date",
        )
    with filter_columns[2]:
        as_on_date = st.date_input(
            "As On Date",
            value=st.session_state.get("oa_as_on_date", default_as_on_date),
            format="DD/MM/YYYY",
            key="oa_as_on_date",
        )

    date_error = _validate_dates(from_date, to_date, as_on_date)
    if date_error:
        st.error(date_error)
        return

    working_df = scoped_df

    zone_options = _sorted_values(working_df, zone_col)
    with filter_columns[3]:
        if locked_zone:
            selected_zones = st.multiselect(
                "◉ Zone",
                [locked_zone],
                default=[locked_zone],
                key="oa_zone_locked_v5",
                disabled=True,
            )
        else:
            _prune_multiselect_state("oa_zone_v5", zone_options)
            selected_zones = st.multiselect(
                "◉ Zone",
                zone_options,
                key="oa_zone_v5",
                placeholder="All zones",
                disabled=not zone_options,
            )
    if selected_zones:
        working_df = working_df[_match_scope_values(working_df[zone_col], selected_zones)]

    circle_options = _sorted_values(working_df, circle_col)
    with filter_columns[4]:
        if locked_circle:
            selected_circles = st.multiselect(
                "◎ Circle",
                [locked_circle],
                default=[locked_circle],
                key="oa_circle_locked_v5",
                disabled=True,
            )
        else:
            _prune_multiselect_state("oa_circle_v5", circle_options)
            selected_circles = st.multiselect(
                "◎ Circle",
                circle_options,
                key="oa_circle_v5",
                placeholder="All circles",
                disabled=not circle_options,
            )
    if selected_circles:
        working_df = working_df[_match_scope_values(working_df[circle_col], selected_circles)]

    branch_options = _sorted_values(working_df, branch_col)
    with filter_columns[5]:
        if locked_branch:
            selected_branches = st.multiselect(
                "⌂ Branch",
                [locked_branch],
                default=[locked_branch],
                key="oa_branch_locked_v5",
                disabled=True,
            )
        else:
            _prune_multiselect_state("oa_branch_v5", branch_options)
            selected_branches = st.multiselect(
                "⌂ Branch",
                branch_options,
                key="oa_branch_v5",
                placeholder="All branches",
                disabled=not branch_options,
            )
    if selected_branches:
        working_df = working_df[_match_scope_values(working_df[branch_col], selected_branches)]

    customer_options = _sorted_values(working_df, customer_col)
    with filter_columns[6]:
        if customer_col:
            _prune_multiselect_state("oa_customer_v5", customer_options)
            selected_customers = st.multiselect(
                "Customer",
                customer_options,
                key="oa_customer_v5",
                placeholder="All customers",
                disabled=not customer_options,
            )
        else:
            selected_customers = []
    if selected_customers and customer_col:
        working_df = working_df[
            _match_scope_values(working_df[customer_col], selected_customers)
        ]

    with filter_columns[7]:
        selected_document = (
            _safe_selectbox(
                "Document Type",
                ["All"] + _sorted_values(working_df, document_col),
                "oa_filter_document_v4",
            )
            if document_col else "All"
        )
    if selected_document != "All" and document_col:
        working_df = working_df[
            _match_scope_value(working_df[document_col], selected_document)
        ]

    with filter_columns[8]:
        available_buckets = [
            b for b in AGE_BUCKET_ORDER
            if age_bucket_col and b in working_df[age_bucket_col].dropna().astype(str).unique()
        ]
        selected_bucket = (
            _safe_selectbox(
                "Age Bucket",
                ["All"] + available_buckets,
                "oa_filter_age_bucket_v4",
            )
            if age_bucket_col else "All"
        )
    if selected_bucket != "All" and age_bucket_col:
        working_df = working_df[
            _match_scope_value(working_df[age_bucket_col], selected_bucket)
        ]

    with filter_columns[9]:
        conversion_type = _safe_selectbox(
            "₹ Conversion",
            ["Crore", "Lac"],
            "oa_conversion_v3",
        )

    with filter_columns[10]:
        run_report = st.button(
            "Run Report",
            type="primary",
            key="oa_run_report",
            width="stretch",
        )

    # Only the Run button refreshes the stored-procedure dataset. Dashboard
    # slicers above operate instantly on the already loaded dataframe.
    if run_report:
        try:
            loaded_df = get_outstanding_data(
                branch=SP_BRANCH,
                grtype=SP_GRTYPE,
                from_date=from_date,
                to_date=to_date,
                as_on_date=as_on_date,
                custcode=SP_CUSTCODE,
                invoiceno=SP_INVOICENO,
                user=SP_USER,
            )
            st.session_state["oa_df"] = loaded_df
            st.session_state["oa_loaded_dates"] = (from_date, to_date, as_on_date)
            st.session_state["oa_last_refreshed"] = datetime.now()
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to load outstanding data: {exc}")
            return

    loaded_dates = st.session_state.get("oa_loaded_dates")
    selected_dates = (from_date, to_date, as_on_date)
    if loaded_dates and loaded_dates != selected_dates:
        st.warning(
            "The date filters have changed. Click **Run Report** to reload the report "
            "for the newly selected dates."
        )

    conversion_divisor, conversion_unit = _get_conversion(conversion_type)
    fdf = working_df
    selected_zone = selected_zones[0] if len(selected_zones) == 1 else "All"
    selected_circle = selected_circles[0] if len(selected_circles) == 1 else "All"
    selected_branch = selected_branches[0] if len(selected_branches) == 1 else "All"

    # -----------------------------------------------------------------------
    # ACTIVE FILTER CHIPS IN DASHBOARD HEADER
    # Only non-All values are shown. Locked role values (Zone/Circle/Branch)
    # remain visible because they explain the user's reporting scope.
    # -----------------------------------------------------------------------

    active_filter_items = [
        ("Zone", ", ".join(map(str, selected_zones)) if selected_zones else "All"),
        ("Circle", ", ".join(map(str, selected_circles)) if selected_circles else "All"),
        ("Branch", ", ".join(map(str, selected_branches)) if selected_branches else "All"),
        ("Customer", ", ".join(map(str, selected_customers)) if selected_customers else "All"),
        ("Document", selected_document),
        ("Age", selected_bucket),
        ("Unit", conversion_type),
    ]

    _render_outstanding_header(
        header_content_placeholder,
        active_filter_items,
    )

    if fdf.empty:
        st.warning("No data found for the selected filters.")
        return

    # -----------------------------------------------------------------------
    # KPI ROW
    # -----------------------------------------------------------------------

    total_balance = (
        pd.to_numeric(fdf["balance"], errors="coerce").fillna(0).sum()
        if "balance" in fdf.columns else 0
    )
    total_on_account = (
        pd.to_numeric(fdf["onaccrecd"], errors="coerce").fillna(0).sum()
        if "onaccrecd" in fdf.columns else 0
    )
    total_net = (
        pd.to_numeric(fdf["netbalance"], errors="coerce").fillna(0).sum()
        if "netbalance" in fdf.columns else 0
    )

    if age_bucket_col and "netbalance" in fdf.columns:
        overdue_90 = pd.to_numeric(
            fdf.loc[
                fdf[age_bucket_col].astype(str).eq("Above 90"),
                "netbalance",
            ],
            errors="coerce",
        ).fillna(0).sum()
    else:
        overdue_90 = 0

    invoice_count = (
        fdf["invoiceno"].nunique()
        if "invoiceno" in fdf.columns
        else len(fdf)
    )

    customer_count = (
        fdf[customer_col].nunique()
        if customer_col
        else 0
    )

    # NOTE: "Total Billed" and "Total Received" KPI cards were removed on
    # request -- they were causing confusion (their totals depended on
    # which rows happened to be settled vs pending). They are replaced
    # with two count-based cards (Total Invoices, Total Customers) that
    # are unambiguous.

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:
        st.markdown('<span class="oa-responsive-marker oa-kpi-grid-marker"></span>', unsafe_allow_html=True)
        _kpi_card(
            "Total Invoices",
            f"{invoice_count:,}",
            "Distinct invoices in selection",
            "blue",
        )

    with k2:
        _kpi_card(
            "Total Customers",
            f"{customer_count:,}",
            "Distinct customers in selection",
            "green",
        )

    with k3:
        _kpi_card(
            "Balance",
            _inr_amount(total_balance, conversion_type),
            "Before on-account adjustment",
            "teal",
        )

    with k4:
        _kpi_card(
            "On-Account Recd",
            _inr_amount(total_on_account, conversion_type),
            "Unadjusted receipts",
            "purple",
        )

    with k5:
        _kpi_card(
            "Net Outstanding",
            _inr_amount(total_net, conversion_type),
            "After on-account adjustment",
            "amber",
        )

    with k6:
        _kpi_card(
            "Overdue > 90 Days",
            _inr_amount(overdue_90, conversion_type),
            "High-risk receivables",
            "red",
        )

    # -----------------------------------------------------------------------
    # AGEING AND ZONE CHARTS
    # -----------------------------------------------------------------------

    st.markdown(
        "<div class='oa-section-title'>Ageing and Zone-wise Outstanding</div>",
        unsafe_allow_html=True,
    )

    chart_col1, chart_col2 = st.columns([1, 1.3])

    with chart_col1:
        st.markdown('<span class="oa-responsive-marker oa-stack-grid-marker"></span>', unsafe_allow_html=True)
        if age_bucket_col and "netbalance" in fdf.columns:
            age_df = (
                fdf.groupby(age_bucket_col, dropna=False)["netbalance"]
                .sum()
                .reindex(AGE_BUCKET_ORDER)
                .fillna(0)
                .reset_index()
            )

            total_age_outstanding = age_df["netbalance"].sum()

            age_colors = {
                "0-30": "#16a34a",
                "31-60": "#d97706",
                "61-90": "#ea580c",
                "Above 90": "#dc2626",
            }

            age_chart_col, age_value_col = st.columns([1.35, 0.65])

            with age_chart_col:
                st.markdown('<span class="oa-responsive-marker oa-stack-grid-marker"></span>', unsafe_allow_html=True)
                fig_age = px.pie(
                    age_df,
                    names=age_bucket_col,
                    values="netbalance",
                    hole=0.55,
                    color=age_bucket_col,
                    color_discrete_map=age_colors,
                    title="Net Outstanding by Age Bucket",
                )

                fig_age.update_traces(
                    textinfo="percent+label",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        f"Outstanding: ₹%{{customdata[0]:,.2f}} {conversion_unit}<br>"
                        "Share: %{percent}<extra></extra>"
                    ),
                    customdata=(age_df[["netbalance"]] / conversion_divisor).values,
                )

                fig_age.update_layout(
                    height=380,
                    showlegend=False,
                    margin=dict(t=50, b=10, l=10, r=10),
                    annotations=[
                        dict(
                            text=(
                                f"<b>{_inr_amount(total_age_outstanding, conversion_type)}</b>"
                                "<br><span style='font-size:11px'>Net Outstanding</span>"
                            ),
                            x=0.5,
                            y=0.5,
                            showarrow=False,
                            align="center",
                            font=dict(size=15, color="#0f172a"),
                        )
                    ],
                )

                st.plotly_chart(fig_age, width='stretch')

            with age_value_col:
                st.markdown(
                    "<div style='height:42px'></div>",
                    unsafe_allow_html=True,
                )

                for _, row in age_df.iterrows():
                    bucket = str(row[age_bucket_col])
                    value = float(row["netbalance"])
                    percentage = (
                        (value / total_age_outstanding) * 100
                        if total_age_outstanding
                        else 0
                    )

                    st.markdown(
                        f"""
                        <div style="
                            display:flex;
                            align-items:flex-start;
                            gap:8px;
                            margin-bottom:14px;
                        ">
                            <div style="
                                width:11px;
                                height:11px;
                                border-radius:50%;
                                background:{age_colors.get(bucket, '#64748b')};
                                margin-top:5px;
                                flex-shrink:0;
                            "></div>
                            <div>
                                <div style="
                                    font-size:12px;
                                    font-weight:700;
                                    color:#334155;
                                ">
                                    {bucket}
                                </div>
                                <div style="
                                    font-size:14px;
                                    font-weight:800;
                                    color:#0f172a;
                                ">
                                    {_inr_amount(value, conversion_type)}
                                </div>
                                <div style="
                                    font-size:11px;
                                    color:#64748b;
                                ">
                                    {percentage:.1f}%
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"""
                    <div style="
                        border-top:1px solid #e5e7eb;
                        padding-top:10px;
                        margin-top:4px;
                    ">
                        <div style="
                            font-size:11px;
                            color:#64748b;
                            font-weight:600;
                        ">
                            Total
                        </div>
                        <div style="
                            font-size:15px;
                            color:#0f172a;
                            font-weight:800;
                        ">
                            {_inr_amount(total_age_outstanding, conversion_type)}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("Age-bucket data is not available.")

    with chart_col2:
        if zone_col and "netbalance" in fdf.columns:
            zone_df = (
                fdf.groupby(zone_col)["netbalance"]
                .sum()
                .sort_values(ascending=True)
                .reset_index()
            )
            zone_df["netbalance_display"] = zone_df["netbalance"] / conversion_divisor

            fig_zone = px.bar(
                zone_df,
                x="netbalance_display",
                y=zone_col,
                orientation="h",
                text="netbalance_display",
                title=f"Net Outstanding by Zone (₹ {conversion_unit})",
                color="netbalance_display",
                color_continuous_scale="Blues",
            )

            fig_zone.update_traces(
                texttemplate=f"₹%{{text:,.2f}} {conversion_unit}",
                textposition="outside",
            )

            max_zone = zone_df["netbalance_display"].max() if not zone_df.empty else 0

            fig_zone.update_layout(
                height=380,
                coloraxis_showscale=False,
                margin=dict(t=50, b=10, l=10, r=30),
                xaxis_title=f"Net Outstanding (₹ {conversion_unit})",
                yaxis_title="",
                xaxis_range=[0, max_zone * 1.18] if max_zone > 0 else None,
            )

            st.plotly_chart(fig_zone, width='stretch')
        else:
            st.info("Zone data is not available.")

    # -----------------------------------------------------------------------
    # DOCUMENT TYPE-WISE OUTSTANDING
    # -----------------------------------------------------------------------

    st.markdown(
        "<div class='oa-section-title'>Document Type-wise Outstanding</div>",
        unsafe_allow_html=True,
    )

    if document_col and "netbalance" in fdf.columns:
        document_summary = (
            fdf.groupby(document_col, dropna=False)
            .agg(
                Net_Outstanding=("netbalance", "sum"),
                Documents=(
                    "invoiceno",
                    "nunique",
                ) if "invoiceno" in fdf.columns else (
                    "netbalance",
                    "size",
                ),
            )
            .reset_index()
        )

        if "billamount" in fdf.columns:
            billed_summary = (
                fdf.groupby(document_col, dropna=False)["billamount"]
                .sum()
                .reset_index(name="Billed")
            )
            document_summary = document_summary.merge(
                billed_summary,
                on=document_col,
                how="left",
            )
        else:
            document_summary["Billed"] = 0

        document_summary[document_col] = (
            document_summary[document_col]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
        )

        document_summary = document_summary.sort_values(
            "Net_Outstanding",
            ascending=True,
        )

        document_summary["Net_Outstanding_Display"] = (
            document_summary["Net_Outstanding"] / conversion_divisor
        )

        doc_chart_col, doc_table_col = st.columns([1.35, 0.85])

        with doc_chart_col:
            st.markdown('<span class="oa-responsive-marker oa-stack-grid-marker"></span>', unsafe_allow_html=True)
            fig_document = px.bar(
                document_summary,
                x="Net_Outstanding_Display",
                y=document_col,
                orientation="h",
                text="Net_Outstanding_Display",
                color="Net_Outstanding_Display",
                color_continuous_scale="Oranges",
                title=f"Net Outstanding by Document Type (₹ {conversion_unit})",
            )

            fig_document.update_traces(
                texttemplate=f"₹%{{text:,.2f}} {conversion_unit}",
                textposition="outside",
            )

            max_document_value = (
                document_summary["Net_Outstanding_Display"].max()
                if not document_summary.empty
                else 0
            )

            fig_document.update_layout(
                height=max(360, 42 * len(document_summary)),
                coloraxis_showscale=False,
                margin=dict(t=50, b=10, l=10, r=45),
                xaxis_title=f"Net Outstanding (₹ {conversion_unit})",
                yaxis_title="",
                xaxis_range=(
                    [0, max_document_value * 1.18]
                    if max_document_value > 0
                    else None
                ),
            )

            st.plotly_chart(
                fig_document,
                width='stretch',
            )

        with doc_table_col:
            document_table = document_summary.sort_values(
                "Net_Outstanding",
                ascending=False,
            ).copy()

            document_table["Net_Outstanding"] = (
                document_table["Net_Outstanding"] / conversion_divisor
            )
            document_table["Billed"] = document_table["Billed"] / conversion_divisor
            document_table = document_table.drop(
                columns=["Net_Outstanding_Display"]
            )
            _render_scale_table(document_table, document_col, "Net_Outstanding", f"Net Outstanding (₹ {conversion_unit})", conversion_unit, secondary_cols=[("Billed", f"Billed (₹ {conversion_unit})", "money"), ("Documents", "Documents", "int")], max_rows=30, accent="#f59e0b")
    else:
        st.info("Document Type or Net Outstanding data is not available.")

    # -----------------------------------------------------------------------
    # CUSTOMER AND BRANCH ANALYSIS
    # -----------------------------------------------------------------------

    st.markdown(
        "<div class='oa-section-title'>Top Customers and Branch Performance</div>",
        unsafe_allow_html=True,
    )

    customer_chart_col, branch_table_col = st.columns([1.2, 1], gap="medium")

    with customer_chart_col:
        st.markdown('<span class="oa-responsive-marker oa-stack-grid-marker"></span>', unsafe_allow_html=True)
        cust_title_col, cust_top_col = st.columns([3.2, 1.0], gap="small", vertical_alignment="center")
        with cust_title_col:
            st.markdown(
                "<div style='font-size:15px;font-weight:600;color:#0f2744;'>Top Customers</div>",
                unsafe_allow_html=True,
            )
        with cust_top_col:
            customer_top_n = st.selectbox(
                "Customers to display",
                [10, 20, 30, 40, 50],
                index=0,
                format_func=lambda value: f"Top {value}",
                key="oa_customer_top_n",
                label_visibility="collapsed",
            )

        if customer_col and "netbalance" in fdf.columns:
            top_customers = (
                fdf.groupby(customer_col, dropna=False)["netbalance"]
                .sum()
                .sort_values(ascending=False)
                .head(customer_top_n)
                .sort_values()
                .reset_index()
            )
            top_customers["netbalance_display"] = (
                top_customers["netbalance"] / conversion_divisor
            )

            fig_customer = px.bar(
                top_customers,
                x="netbalance_display",
                y=customer_col,
                orientation="h",
                color="netbalance_display",
                color_continuous_scale="Reds",
            )
            fig_customer.update_traces(
                texttemplate=f"₹%{{x:,.2f}} {conversion_unit}",
                textposition="outside",
            )
            fig_customer.update_layout(
                height=max(360, min(760, 220 + customer_top_n * 11)),
                coloraxis_showscale=False,
                margin=dict(t=12, b=10, l=10, r=20),
                xaxis_title=f"Net Outstanding (₹ {conversion_unit})",
                yaxis_title="",
            )
            st.plotly_chart(fig_customer, width="stretch")
        else:
            st.info("Customer data is not available.")

    with branch_table_col:
        branch_title_col, branch_top_col = st.columns([3.2, 1.0], gap="small", vertical_alignment="center")
        with branch_title_col:
            st.markdown(
                "<div style='font-size:15px;font-weight:600;color:#0f2744;'>Branch Performance</div>",
                unsafe_allow_html=True,
            )
        with branch_top_col:
            branch_top_n = st.selectbox(
                "Branches to display",
                [10, 20, 30, 40, 50],
                index=0,
                format_func=lambda value: f"Top {value}",
                key="oa_branch_top_n",
                label_visibility="collapsed",
            )

        if branch_col:
            aggregation = {}
            if "billamount" in fdf.columns:
                aggregation["Billed"] = ("billamount", "sum")
            if "recdamount" in fdf.columns:
                aggregation["Received"] = ("recdamount", "sum")
            if "netbalance" in fdf.columns:
                aggregation["Net_Outstanding"] = ("netbalance", "sum")
            if "invoiceno" in fdf.columns:
                aggregation["Invoices"] = ("invoiceno", "nunique")

            if aggregation:
                branch_summary = fdf.groupby(branch_col).agg(**aggregation).reset_index()
                if "Net_Outstanding" in branch_summary.columns:
                    branch_summary = branch_summary.sort_values("Net_Outstanding", ascending=False)
                for column in ["Billed", "Received", "Net_Outstanding"]:
                    if column in branch_summary.columns:
                        branch_summary[column] = branch_summary[column] / conversion_divisor

                _render_scale_table(
                    branch_summary,
                    branch_col,
                    "Net_Outstanding",
                    f"Net Outstanding (₹ {conversion_unit})",
                    conversion_unit,
                    secondary_cols=[
                        ("Billed", f"Billed (₹ {conversion_unit})", "money"),
                        ("Received", f"Received (₹ {conversion_unit})", "money"),
                        ("Invoices", "Invoices", "int"),
                    ],
                    max_rows=branch_top_n,
                    accent="#7c3aed",
                )
            else:
                st.info("Branch amount columns are not available.")
        else:
            st.info("Branch data is not available.")

    # -----------------------------------------------------------------------
    # YEAR-WISE OUTSTANDING INSIGHT
    # -----------------------------------------------------------------------
    # When the report is run from a long historical From Date (for example
    # 01-01-1980), this view shows which invoice years still contribute to the
    # current As-On outstanding. It uses invoice date as the vintage year.
    if "invoicedt" in fdf.columns and "netbalance" in fdf.columns:
        year_source = fdf.copy()
        year_source["invoicedt"] = pd.to_datetime(year_source["invoicedt"], errors="coerce")
        year_source = year_source.dropna(subset=["invoicedt"])

        if not year_source.empty:
            st.markdown(
                "<div class='oa-section-title'>Year-wise Outstanding Insight</div>",
                unsafe_allow_html=True,
            )

            year_source["Invoice Year"] = year_source["invoicedt"].dt.year.astype(int)
            year_agg = {
                "Net_Outstanding": ("netbalance", "sum"),
            }
            if "invoiceno" in year_source.columns:
                year_agg["Invoices"] = ("invoiceno", "nunique")
            if customer_col:
                year_agg["Customers"] = (customer_col, "nunique")
            if "outstandingdays" in year_source.columns:
                year_agg["Avg_Age_Days"] = ("outstandingdays", "mean")

            year_summary = (
                year_source.groupby("Invoice Year", as_index=False)
                .agg(**year_agg)
                .sort_values("Invoice Year")
            )
            year_summary["Outstanding_Display"] = year_summary["Net_Outstanding"] / conversion_divisor

            insight_cols = st.columns(4, gap="small")
            peak_row = year_summary.loc[year_summary["Net_Outstanding"].idxmax()]
            oldest_year = int(year_summary["Invoice Year"].min())
            active_years = int(year_summary["Invoice Year"].nunique())
            three_year_cutoff = pd.Timestamp(as_on_date) - pd.DateOffset(years=3)
            legacy_amount = pd.to_numeric(
                year_source.loc[year_source["invoicedt"] < three_year_cutoff, "netbalance"],
                errors="coerce",
            ).fillna(0).sum()

            with insight_cols[0]:
                st.markdown('<span class="oa-responsive-marker oa-kpi-grid-marker"></span>', unsafe_allow_html=True)
                _kpi_card("Oldest Invoice Year", f"{oldest_year}", "Still contributing to outstanding", "blue")
            with insight_cols[1]:
                _kpi_card("Peak Outstanding Year", f"{int(peak_row['Invoice Year'])}", _inr_amount(peak_row["Net_Outstanding"], conversion_type), "purple")
            with insight_cols[2]:
                _kpi_card("Years Represented", f"{active_years:,}", "Invoice vintage years", "teal")
            with insight_cols[3]:
                _kpi_card("> 3 Years Old", _inr_amount(legacy_amount, conversion_type), "Legacy receivables", "red")

            year_chart_col, year_table_col = st.columns([1.35, 1.0], gap="medium")
            with year_chart_col:
                st.markdown('<span class="oa-responsive-marker oa-stack-grid-marker"></span>', unsafe_allow_html=True)
                fig_year = go.Figure()
                fig_year.add_trace(
                    go.Bar(
                        x=year_summary["Invoice Year"].astype(str),
                        y=year_summary["Outstanding_Display"],
                        name="Net Outstanding",
                        marker_color="#2563eb",
                        text=year_summary["Outstanding_Display"],
                        texttemplate=f"₹%{{text:.2f}} {conversion_unit}",
                        textposition="outside",
                        cliponaxis=False,
                        hovertemplate=(
                            f"<b>Invoice Year %{{x}}</b><br>Net Outstanding: ₹%{{y:.2f}} {conversion_unit}<extra></extra>"
                        ),
                    )
                )
                if "Invoices" in year_summary.columns:
                    fig_year.add_trace(
                        go.Scatter(
                            x=year_summary["Invoice Year"].astype(str),
                            y=year_summary["Invoices"],
                            name="Invoices",
                            mode="lines+markers",
                            yaxis="y2",
                            line=dict(color="#f59e0b", width=2.5),
                            marker=dict(size=7),
                            hovertemplate="<b>Invoice Year %{x}</b><br>Invoices: %{y:,.0f}<extra></extra>",
                        )
                    )
                fig_year.update_layout(
                    height=390,
                    margin=dict(l=8, r=8, t=28, b=8),
                    plot_bgcolor="#fbfdff",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.05, x=0),
                    xaxis=dict(title="Invoice Year", showgrid=False),
                    yaxis=dict(title=f"Outstanding (₹ {conversion_unit})", showgrid=False),
                    yaxis2=dict(title="Invoices", overlaying="y", side="right", showgrid=False),
                )
                st.plotly_chart(fig_year, width="stretch", config={"displayModeBar": False})

            with year_table_col:
                year_table = year_summary.copy().sort_values("Invoice Year", ascending=False)
                year_table["Year"] = year_table["Invoice Year"].astype(str)
                year_table["Net_Outstanding"] = year_table["Net_Outstanding"] / conversion_divisor
                secondary_cols = []
                if "Invoices" in year_table.columns:
                    secondary_cols.append(("Invoices", "Invoices", "int"))
                if "Customers" in year_table.columns:
                    secondary_cols.append(("Customers", "Customers", "int"))
                if "Avg_Age_Days" in year_table.columns:
                    year_table["Avg_Age_Days"] = pd.to_numeric(year_table["Avg_Age_Days"], errors="coerce").fillna(0).round(0).astype(int)
                    secondary_cols.append(("Avg_Age_Days", "Avg Age Days", "int"))

                _render_scale_table(
                    year_table,
                    "Year",
                    "Net_Outstanding",
                    f"Outstanding (₹ {conversion_unit})",
                    conversion_unit,
                    secondary_cols=secondary_cols,
                    max_rows=50,
                    accent="#2563eb",
                )

    # -----------------------------------------------------------------------
    # MONTHLY BILLING VERSUS COLLECTION TREND
    # -----------------------------------------------------------------------

    if "invoicedt" in fdf.columns:
        trend_df = fdf.copy()
        trend_df["invoicedt"] = pd.to_datetime(
            trend_df["invoicedt"],
            errors="coerce",
        )
        trend_df = trend_df.dropna(subset=["invoicedt"])

        if not trend_df.empty:
            st.markdown(
                "<div class='oa-section-title'>Monthly Billing vs Collection Trend</div>",
                unsafe_allow_html=True,
            )

            trend_df["month"] = (
                trend_df["invoicedt"]
                .dt.to_period("M")
                .dt.to_timestamp()
            )

            trend_aggregation = {}

            if "billamount" in trend_df.columns:
                trend_aggregation["Billed"] = ("billamount", "sum")

            if "recdamount" in trend_df.columns:
                trend_aggregation["Received"] = ("recdamount", "sum")

            trend = (
                trend_df.groupby("month")
                .agg(**trend_aggregation)
                .reset_index()
            )

            for column in ["Billed", "Received"]:
                if column in trend.columns:
                    trend[column] = trend[column] / conversion_divisor

            fig_trend = go.Figure()

            if "Billed" in trend.columns:
                fig_trend.add_trace(
                    go.Bar(
                        x=trend["month"],
                        y=trend["Billed"],
                        name="Billed",
                        marker_color="#2563eb",
                    )
                )

            if "Received" in trend.columns:
                fig_trend.add_trace(
                    go.Scatter(
                        x=trend["month"],
                        y=trend["Received"],
                        name="Received",
                        mode="lines+markers",
                        line=dict(color="#16a34a", width=3),
                    )
                )

            fig_trend.update_layout(
                height=380,
                barmode="group",
                margin=dict(t=30, b=10, l=10, r=10),
                yaxis_title=f"Amount (₹ {conversion_unit})",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                ),
            )

            st.plotly_chart(fig_trend, width='stretch')

    # -----------------------------------------------------------------------
    # DETAIL TABLE AND EXPORT
    # -----------------------------------------------------------------------

    st.markdown(
        "<div class='oa-section-title'>Detailed Records</div>",
        unsafe_allow_html=True,
    )

    preferred_columns = [
        zone_col,
        circle_col,
        branch_col,
        customer_col,
        "grtype",
        document_col,
        "invoiceno",
        "invoicedt",
        "duedt",
        "billamount",
        "recdamount",
        "balance",
        "onaccrecd",
        "netbalance",
        "outstandingdays",
        age_bucket_col,
    ]

    show_columns = []

    for column in preferred_columns:
        if column and column in fdf.columns and column not in show_columns:
            show_columns.append(column)

    detail_df = fdf[show_columns].copy() if show_columns else fdf.copy()

    # NOTE: Detail Records is left in plain ₹ (not converted to Crore/Lac) on purpose --
    # this table shows individual invoice-level rows, and converting each
    # row to crore made per-invoice amounts unreadable (values like
    # tiny converted values for small invoices). The selected Conversion unit is
    # used everywhere else (KPI cards, charts and grouped summary tables).
    money_columns = [
        column
        for column in ["billamount", "recdamount", "balance", "onaccrecd", "netbalance"]
        if column in detail_df.columns
    ]

    for column in money_columns:
        detail_df[column] = pd.to_numeric(
            detail_df[column], errors="coerce"
        ).fillna(0)

    search_text = st.text_input(
        "Search customer, invoice number, branch or other details",
        "",
        key="oa_search",
    )

    if search_text:
        search_mask = detail_df.apply(
            lambda row: row.astype(str)
            .str.contains(search_text, case=False, na=False)
            .any(),
            axis=1,
        )

        detail_df = detail_df[search_mask]

    # NOTE: Using pandas Styler (.style.format(...)) on this table used to
    # crash the page on larger date ranges with:
    #   StreamlitAPIException: The dataframe has `N` cells, but the maximum
    #   number of cells allowed to be rendered by Pandas Styler is configured
    #   to `262144`.
    # Styler has a hard render-cell cap that a full detail export can easily
    # exceed. column_config formatting achieves the same "₹" display without
    # going through Styler at all, so there is no cell limit here.
    # Business Overview-style column names, widths and numeric/date formatting.
    column_config = {}

    friendly_text_columns = {
        zone_col: ("Zone", "medium"),
        circle_col: ("Circle", "medium"),
        branch_col: ("Branch", "medium"),
        customer_col: ("Customer", "large"),
        "grtype": ("GR Type", "small"),
        document_col: ("Document Type", "medium"),
        "invoiceno": ("Invoice No.", "medium"),
        age_bucket_col: ("Age Bucket", "small"),
    }

    for column, config in friendly_text_columns.items():
        if column and column in detail_df.columns:
            label, width = config
            column_config[column] = st.column_config.TextColumn(
                label,
                width=width,
            )

    for column, label in [("invoicedt", "Invoice Date"), ("duedt", "Due Date")]:
        if column in detail_df.columns:
            column_config[column] = st.column_config.DateColumn(
                label,
                format="DD/MM/YYYY",
                width="small",
            )

    money_labels = {
        "billamount": "Bill Amount (₹)",
        "recdamount": "Received (₹)",
        "balance": "Balance (₹)",
        "onaccrecd": "On-Account Recd (₹)",
        "netbalance": "Net Outstanding (₹)",
    }

    for column in money_columns:
        column_config[column] = st.column_config.NumberColumn(
            money_labels.get(column, column.replace("_", " ").title() + " (₹)"),
            format="₹%.0f",
            width="medium",
        )

    if "outstandingdays" in detail_df.columns:
        column_config["outstandingdays"] = st.column_config.NumberColumn(
            "Outstanding Days",
            format="%d",
            width="small",
        )

    st.caption(f"Showing {len(detail_df):,} filtered records")

    st.dataframe(
        detail_df,
        width='stretch',
        height=420,
        hide_index=True,
        column_config=column_config,
    )

    excel_data = _outstanding_excel_bytes(detail_df)

    # Put the export action in the top dashboard header, matching Overview.
    with header_action_placeholder:
        st.download_button(
            "⬇ Excel",
            data=excel_data,
            file_name=(
                "outstanding_filtered_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            key="oa_header_download",
            help="Download the currently filtered Outstanding records.",
            width="content",
        )

    last_refreshed = st.session_state.get(
        "oa_last_refreshed",
        datetime.now(),
    )

    st.caption(
        f"Data period: {from_date.strftime('%d-%b-%Y')} to "
        f"{to_date.strftime('%d-%b-%Y')} | "
        f"As on: {as_on_date.strftime('%d-%b-%Y')} | "
        f"Last refreshed: {last_refreshed.strftime('%d-%b-%Y %H:%M')} | "
        f"Records: {len(fdf):,}"
    )

# Compatibility with the responsive/new page entry point.
def main():
    show_OutstandingAnalysis()

if __name__ == "__main__":
    main()
