"""
pages/Home/Outstanding_Analysis.py
==================================

Outstanding Analysis dashboard using the Alloutstanding_BI stored procedure.

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

2. All monetary values are displayed in ₹ Crore (2 decimal places) across
   KPI cards, charts and grouped summary tables. The Detailed Records table
   is the one exception -- it stays in plain ₹ since it shows individual
   invoice-level rows, where crore formatting made small amounts unreadable.

3. Previous-period (PY) growth-arrow comparison has been removed. KPI cards
   now show plain values only, with no ▲/▼ badge and no second stored
   procedure call for the preceding period.

4. "Total Billed" and "Total Received" KPI cards have been replaced with
   "Total Invoices" and "Total Customers" (plain counts), which removes the
   ambiguity those two amount-based cards used to cause.
------------------------------------------------------------------------------
"""

import io
from datetime import date, datetime, timedelta

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
                padding: 16px 18px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.06);
                border-left: 6px solid var(--accent, #2563eb);
                text-align: left;
                min-height: 108px;
            }

            .oa-kpi-label {
                font-size: 12px;
                color: #6b7280;
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
                font-size: 23px;
                font-weight: 800;
                color: #111827;
            }

            .oa-kpi-sub {
                font-size: 11px;
                color: #9ca3af;
                margin-top: 3px;
            }

            .oa-section-title {
                font-size: 19px;
                font-weight: 700;
                color: #111827;
                margin: 18px 0 6px 0;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 6px;
            }

            [data-testid="stDataFrame"] table {
                font-size: 11px;
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


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _inr_cr(value):
    """
    Format a rupee value in ₹ Crore, 2 decimal places.

    1 Crore = 1,00,00,000 (10,000,000)
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "₹0.00 Cr"

    negative = value < 0
    value = abs(value)

    crore_value = value / 1_00_00_000

    return f"{'-' if negative else ''}₹{crore_value:,.2f} Cr"


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
    scoped_df = df.copy()

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


def _validate_dates(from_date, to_date, as_on_date):
    if from_date > to_date:
        return "From Date cannot be later than To Date."

    if as_on_date < from_date:
        return "As On Date cannot be earlier than From Date."

    return None


def _load_as_on_trend(from_date, to_date, as_on_date, days=7):
    """Load recent outstanding snapshots by varying only the As On Date.

    The stored procedure returns one snapshot for one As On Date, so a real
    trend requires one procedure call per snapshot date. The selected From/To
    dates remain unchanged.
    """
    trend_rows = []

    first_snapshot = max(from_date, as_on_date - timedelta(days=days - 1))
    snapshot_dates = pd.date_range(first_snapshot, as_on_date, freq="D").date

    for snapshot_date in snapshot_dates:
        snapshot_df = get_outstanding_data(
            branch=SP_BRANCH,
            grtype=SP_GRTYPE,
            from_dt=from_date,
            to_dt=to_date,
            as_on_dt=snapshot_date,
            custcode=SP_CUSTCODE,
            invoiceno=SP_INVOICENO,
            user=SP_USER,
        )

        if snapshot_df is None or snapshot_df.empty:
            snapshot_total = 0.0
        elif "netbalance" in snapshot_df.columns:
            snapshot_total = pd.to_numeric(
                snapshot_df["netbalance"], errors="coerce"
            ).fillna(0).sum()
        elif "balance" in snapshot_df.columns:
            snapshot_total = pd.to_numeric(
                snapshot_df["balance"], errors="coerce"
            ).fillna(0).sum()
        else:
            snapshot_total = 0.0

        trend_rows.append(
            {
                "as_on_date": pd.Timestamp(snapshot_date),
                "net_outstanding": float(snapshot_total),
                "net_outstanding_cr": float(snapshot_total) / 1_00_00_000,
            }
        )

    return pd.DataFrame(trend_rows)


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

    st.markdown(
        """
        <h3 style="margin:0;padding:0;">Outstanding Analysis</h3>
        <p style="color:#64748b;font-size:12px;margin:0 0 8px 0;">
            Zone / Circle / Branch / Customer-wise receivables and ageing
            (values shown in ₹ Crore)
        </p>
        """,
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # THREE STORED-PROCEDURE DATE PARAMETERS
    # -----------------------------------------------------------------------

    default_from_date = date(1980, 1, 1)
    default_to_date = date(2026, 6, 30)
    default_as_on_date = date(2026, 6, 30)

    date_col1, date_col2, date_col3, run_col = st.columns(
        [1.25, 1.25, 1.25, 0.9]
    )

    with date_col1:
        from_date = st.date_input(
            "From Date",
            value=st.session_state.get("oa_from_date", default_from_date),
            key="oa_from_date",
        )

    with date_col2:
        to_date = st.date_input(
            "To Date",
            value=st.session_state.get("oa_to_date", default_to_date),
            key="oa_to_date",
        )

    with date_col3:
        as_on_date = st.date_input(
            "As On Date",
            value=st.session_state.get("oa_as_on_date", default_as_on_date),
            key="oa_as_on_date",
        )

    with run_col:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_report = st.button(
            "Run Report",
            type="primary",
            key="oa_run_report",
            width='stretch',
        )

    date_error = _validate_dates(from_date, to_date, as_on_date)

    if date_error:
        st.error(date_error)
        return

    # Load data only after the user presses Run Report.
    if run_report:
        try:
            loaded_df = get_outstanding_data(
                branch=SP_BRANCH,
                grtype=SP_GRTYPE,
                from_dt=from_date,
                to_dt=to_date,
                as_on_dt=as_on_date,
                custcode=SP_CUSTCODE,
                invoiceno=SP_INVOICENO,
                user=SP_USER,
            )

            st.session_state["oa_df"] = loaded_df
            st.session_state["oa_loaded_dates"] = (
                from_date,
                to_date,
                as_on_date,
            )
            # Load recent snapshots for the As On Date trend.
            # This performs one stored-procedure call per day.
            st.session_state["oa_as_on_trend"] = _load_as_on_trend(
                from_date=from_date,
                to_date=to_date,
                as_on_date=as_on_date,
                days=7,
            )

            st.session_state["oa_last_refreshed"] = datetime.now()

        except Exception as exc:
            st.error(f"Unable to load outstanding data: {exc}")
            return

    # Do not query the database automatically on first page load.
    if "oa_df" not in st.session_state:
        st.info("Select the three dates and click **Run Report** to load data.")
        return

    df = st.session_state["oa_df"].copy()

    if df.empty:
        st.warning("No outstanding data was found for the selected dates.")
        return

    loaded_dates = st.session_state.get("oa_loaded_dates")
    selected_dates = (from_date, to_date, as_on_date)

    if loaded_dates and loaded_dates != selected_dates:
        st.warning(
            "The date filters have changed. Click **Run Report** to load data "
            "for the newly selected dates."
        )

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
    # DASHBOARD FILTERS
    # -----------------------------------------------------------------------

    filter_columns = st.columns(6)

    with filter_columns[0]:
        if zone_col:
            if locked_zone:
                selected_zone = locked_zone
                _safe_selectbox(
                    "Zone",
                    [selected_zone],
                    "oa_filter_zone_locked_v2",
                    disabled=True,
                    help_text="Locked as per your assigned rights",
                )
            else:
                selected_zone = _safe_selectbox(
                    "Zone",
                    ["All"] + _sorted_values(scoped_df, zone_col),
                    "oa_filter_zone_v2",
                )
        else:
            selected_zone = "All"
            _safe_selectbox(
                "Zone",
                ["Not available"],
                "oa_filter_zone_missing_v2",
                disabled=True,
            )

    working_df = scoped_df.copy()

    if selected_zone != "All" and zone_col:
        working_df = working_df[
            _match_scope_value(working_df[zone_col], selected_zone)
        ]

    with filter_columns[1]:
        if circle_col:
            if locked_circle:
                selected_circle = locked_circle
                _safe_selectbox(
                    "Circle",
                    [selected_circle],
                    "oa_filter_circle_locked_v2",
                    disabled=True,
                    help_text="Locked as per your assigned rights",
                )
            else:
                selected_circle = _safe_selectbox(
                    "Circle",
                    ["All"] + _sorted_values(working_df, circle_col),
                    "oa_filter_circle_v2",
                )
        else:
            selected_circle = "All"
            _safe_selectbox(
                "Circle",
                ["Not available"],
                "oa_filter_circle_missing_v2",
                disabled=True,
            )

    if selected_circle != "All" and circle_col:
        working_df = working_df[
            _match_scope_value(working_df[circle_col], selected_circle)
        ]

    with filter_columns[2]:
        if branch_col:
            if locked_branch:
                selected_branch = locked_branch
                _safe_selectbox(
                    "Branch",
                    [selected_branch],
                    "oa_filter_branch_locked_v2",
                    disabled=True,
                    help_text="Locked as per your assigned rights",
                )
            else:
                selected_branch = _safe_selectbox(
                    "Branch",
                    ["All"] + _sorted_values(working_df, branch_col),
                    "oa_filter_branch_v2",
                )
        else:
            selected_branch = "All"
            _safe_selectbox(
                "Branch",
                ["Not available"],
                "oa_filter_branch_missing_v2",
                disabled=True,
            )

    if selected_branch != "All" and branch_col:
        working_df = working_df[
            _match_scope_value(working_df[branch_col], selected_branch)
        ]

    with filter_columns[3]:
        if customer_col:
            selected_customer = _safe_selectbox(
                "Customer",
                ["All"] + _sorted_values(working_df, customer_col),
                "oa_filter_customer_v2",
            )
        else:
            selected_customer = "All"
            _safe_selectbox(
                "Customer",
                ["Not available"],
                "oa_filter_customer_missing_v2",
                disabled=True,
            )

    if selected_customer != "All" and customer_col:
        working_df = working_df[
            _match_scope_value(working_df[customer_col], selected_customer)
        ]

    with filter_columns[4]:
        if document_col:
            selected_document = _safe_selectbox(
                "Document Type",
                ["All"] + _sorted_values(working_df, document_col),
                "oa_filter_document_v2",
            )
        else:
            selected_document = "All"
            _safe_selectbox(
                "Document Type",
                ["Not available"],
                "oa_filter_document_missing_v2",
                disabled=True,
            )

    if selected_document != "All" and document_col:
        working_df = working_df[
            _match_scope_value(working_df[document_col], selected_document)
        ]

    with filter_columns[5]:
        if age_bucket_col:
            available_buckets = [
                bucket
                for bucket in AGE_BUCKET_ORDER
                if bucket in working_df[age_bucket_col].dropna().astype(str).unique()
            ]

            selected_bucket = _safe_selectbox(
                "Age Bucket",
                ["All"] + available_buckets,
                "oa_filter_age_bucket_v2",
            )
        else:
            selected_bucket = "All"
            _safe_selectbox(
                "Age Bucket",
                ["Not available"],
                "oa_filter_age_bucket_missing_v2",
                disabled=True,
            )

    if selected_bucket != "All" and age_bucket_col:
        working_df = working_df[
            _match_scope_value(working_df[age_bucket_col], selected_bucket)
        ]

    fdf = working_df.copy()

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
            _inr_cr(total_balance),
            "Before on-account adjustment",
            "teal",
        )

    with k4:
        _kpi_card(
            "On-Account Recd",
            _inr_cr(total_on_account),
            "Unadjusted receipts",
            "purple",
        )

    with k5:
        _kpi_card(
            "Net Outstanding",
            _inr_cr(total_net),
            "After on-account adjustment",
            "amber",
        )

    with k6:
        _kpi_card(
            "Overdue > 90 Days",
            _inr_cr(overdue_90),
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
                        "Outstanding: ₹%{customdata[0]:,.2f} Cr<br>"
                        "Share: %{percent}<extra></extra>"
                    ),
                    customdata=(age_df[["netbalance"]] / 1_00_00_000).values,
                )

                fig_age.update_layout(
                    height=380,
                    showlegend=False,
                    margin=dict(t=50, b=10, l=10, r=10),
                    annotations=[
                        dict(
                            text=(
                                f"<b>{_inr_cr(total_age_outstanding)}</b>"
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
                                    {_inr_cr(value)}
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
                            {_inr_cr(total_age_outstanding)}
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
            zone_df["netbalance_cr"] = zone_df["netbalance"] / 1_00_00_000

            fig_zone = px.bar(
                zone_df,
                x="netbalance_cr",
                y=zone_col,
                orientation="h",
                text="netbalance_cr",
                title="Net Outstanding by Zone (₹ Cr)",
                color="netbalance_cr",
                color_continuous_scale="Blues",
            )

            fig_zone.update_traces(
                texttemplate="₹%{text:,.2f} Cr",
                textposition="outside",
            )

            max_zone = zone_df["netbalance_cr"].max() if not zone_df.empty else 0

            fig_zone.update_layout(
                height=380,
                coloraxis_showscale=False,
                margin=dict(t=50, b=10, l=10, r=30),
                xaxis_title="Net Outstanding (₹ Cr)",
                yaxis_title="",
                xaxis_range=[0, max_zone * 1.18] if max_zone > 0 else None,
            )

            st.plotly_chart(fig_zone, width='stretch')
        else:
            st.info("Zone data is not available.")

    # -----------------------------------------------------------------------
    # OUTSTANDING TREND BY AS ON DATE
    # -----------------------------------------------------------------------

    as_on_trend = st.session_state.get("oa_as_on_trend", pd.DataFrame()).copy()

    if not as_on_trend.empty:
        st.markdown(
            "<div class='oa-section-title'>Outstanding Trend by As On Date</div>",
            unsafe_allow_html=True,
        )

        as_on_trend["as_on_date"] = pd.to_datetime(
            as_on_trend["as_on_date"], errors="coerce"
        )
        as_on_trend = as_on_trend.dropna(subset=["as_on_date"]).sort_values(
            "as_on_date"
        )

        fig_as_on = go.Figure()
        fig_as_on.add_trace(
            go.Scatter(
                x=as_on_trend["as_on_date"],
                y=as_on_trend["net_outstanding_cr"],
                mode="lines+markers+text",
                name="Net Outstanding",
                line=dict(color="#2563eb", width=3),
                marker=dict(size=8, color="#2563eb"),
                text=as_on_trend["net_outstanding_cr"],
                texttemplate="₹%{text:,.2f} Cr",
                textposition="top center",
                hovertemplate=(
                    "<b>%{x|%d-%b-%Y}</b><br>"
                    "Net Outstanding: ₹%{y:,.2f} Cr<extra></extra>"
                ),
            )
        )

        trend_max = as_on_trend["net_outstanding_cr"].max()
        trend_min = as_on_trend["net_outstanding_cr"].min()
        trend_padding = max((trend_max - trend_min) * 0.35, trend_max * 0.08, 0.10)

        fig_as_on.update_layout(
            height=360,
            margin=dict(t=45, b=10, l=10, r=10),
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis_title="As On Date",
            yaxis_title="Net Outstanding (₹ Cr)",
            showlegend=False,
            yaxis_range=[
                max(0, trend_min - trend_padding),
                trend_max + trend_padding,
            ],
        )
        fig_as_on.update_xaxes(showgrid=False, tickformat="%d-%b")
        fig_as_on.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)

        st.plotly_chart(fig_as_on, width="stretch")

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

        document_summary["Net_Outstanding_Cr"] = (
            document_summary["Net_Outstanding"] / 1_00_00_000
        )

        doc_chart_col, doc_table_col = st.columns([1.35, 0.85])

        with doc_chart_col:
            fig_document = px.bar(
                document_summary,
                x="Net_Outstanding_Cr",
                y=document_col,
                orientation="h",
                text="Net_Outstanding_Cr",
                color="Net_Outstanding_Cr",
                color_continuous_scale="Oranges",
                title="Net Outstanding by Document Type (₹ Cr)",
            )

            fig_document.update_traces(
                texttemplate="₹%{text:,.2f} Cr",
                textposition="outside",
            )

            max_document_value = (
                document_summary["Net_Outstanding_Cr"].max()
                if not document_summary.empty
                else 0
            )

            fig_document.update_layout(
                height=max(360, 42 * len(document_summary)),
                coloraxis_showscale=False,
                margin=dict(t=50, b=10, l=10, r=45),
                xaxis_title="Net Outstanding (₹ Cr)",
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
                document_table["Net_Outstanding"] / 1_00_00_000
            )
            document_table["Billed"] = document_table["Billed"] / 1_00_00_000
            document_table = document_table.drop(
                columns=["Net_Outstanding_Cr"]
            )

            st.dataframe(
                document_table,
                width='stretch',
                hide_index=True,
                height=max(360, 42 * len(document_table)),
                column_config={
                    "Net_Outstanding": st.column_config.NumberColumn(
                        "Net Outstanding (₹ Cr)", format="₹%.2f Cr",
                    ),
                    "Billed": st.column_config.NumberColumn(
                        "Billed (₹ Cr)", format="₹%.2f Cr",
                    ),
                    "Documents": st.column_config.NumberColumn(
                        "Documents", format="%d",
                    ),
                },
            )
    else:
        st.info("Document Type or Net Outstanding data is not available.")

    # -----------------------------------------------------------------------
    # CUSTOMER AND BRANCH ANALYSIS
    # -----------------------------------------------------------------------

    st.markdown(
        "<div class='oa-section-title'>Top Customers and Branch Performance</div>",
        unsafe_allow_html=True,
    )

    customer_chart_col, branch_table_col = st.columns([1.2, 1])

    with customer_chart_col:
        if customer_col and "netbalance" in fdf.columns:
            top_customers = (
                fdf.groupby(customer_col)["netbalance"]
                .sum()
                .sort_values(ascending=False)
                .head(15)
                .sort_values()
                .reset_index()
            )
            top_customers["netbalance_cr"] = (
                top_customers["netbalance"] / 1_00_00_000
            )

            fig_customer = px.bar(
                top_customers,
                x="netbalance_cr",
                y=customer_col,
                orientation="h",
                title="Top 15 Customers by Net Outstanding (₹ Cr)",
                color="netbalance_cr",
                color_continuous_scale="Reds",
            )

            fig_customer.update_traces(
                texttemplate="₹%{x:,.2f} Cr",
                textposition="outside",
            )

            fig_customer.update_layout(
                height=440,
                coloraxis_showscale=False,
                margin=dict(t=50, b=10, l=10, r=20),
                xaxis_title="Net Outstanding (₹ Cr)",
                yaxis_title="",
            )

            st.plotly_chart(fig_customer, width='stretch')
        else:
            st.info("Customer data is not available.")

    with branch_table_col:
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
                branch_summary = (
                    fdf.groupby(branch_col)
                    .agg(**aggregation)
                    .reset_index()
                )

                if "Net_Outstanding" in branch_summary.columns:
                    branch_summary = branch_summary.sort_values(
                        "Net_Outstanding",
                        ascending=False,
                    )

                branch_column_config = {}

                for column in ["Billed", "Received", "Net_Outstanding"]:
                    if column in branch_summary.columns:
                        branch_summary[column] = (
                            branch_summary[column] / 1_00_00_000
                        )
                        branch_column_config[column] = st.column_config.NumberColumn(
                            column.replace("_", " ") + " (₹ Cr)",
                            format="₹%.2f Cr",
                        )

                if "Invoices" in branch_summary.columns:
                    branch_column_config["Invoices"] = st.column_config.NumberColumn(
                        "Invoices",
                        format="%d",
                    )

                st.dataframe(
                    branch_summary,
                    height=440,
                    width='stretch',
                    hide_index=True,
                    column_config=branch_column_config,
                )
            else:
                st.info("Branch amount columns are not available.")
        else:
            st.info("Branch data is not available.")

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
                    trend[column] = trend[column] / 1_00_00_000

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
                yaxis_title="Amount (₹ Cr)",
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

    # NOTE: Detail Records is left in plain ₹ (not ₹ Cr) on purpose --
    # this table shows individual invoice-level rows, and converting each
    # row to crore made per-invoice amounts unreadable (values like
    # ₹0.00 Cr for small invoices). Crore formatting is still used
    # everywhere else (KPI cards, charts, grouped summary tables).
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
    column_config = {
        column: st.column_config.NumberColumn(
            column.replace("_", " ").title() + " (₹)",
            format="₹%.0f",
        )
        for column in money_columns
    }

    st.dataframe(
        detail_df,
        width='stretch',
        height=420,
        hide_index=True,
        column_config=column_config,
    )

    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        detail_df.to_excel(
            writer,
            index=False,
            sheet_name="Outstanding",
        )

    st.download_button(
        "Download filtered data (Excel)",
        data=excel_buffer.getvalue(),
        file_name=(
            "outstanding_filtered_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key="oa_download",
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
