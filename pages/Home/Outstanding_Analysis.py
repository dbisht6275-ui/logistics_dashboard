"""
pages/Home/Outstanding_Analysis.py
====================================
Outstanding Analysis page using the same Financial Year, hierarchy filters,
and role-based data-scope logic used on the Overview page.

Data source: services/data_Outstanding.py -> get_outstanding_data()
Called from main.py as: show_OutstandingAnalysis()
"""

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.data_Outstanding import get_outstanding_data, DEFAULT_PARAMS


ACCENT = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "red": "#dc2626",
    "amber": "#d97706",
    "purple": "#7c3aed",
    "teal": "#0d9488",
}

MONTH_ORDER = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]

CALENDAR_TO_FY_MONTH = {
    4: 1, 5: 2, 6: 3, 7: 4, 8: 5, 9: 6,
    10: 7, 11: 8, 12: 9, 1: 10, 2: 11, 3: 12,
}

FY_MONTH_TO_NAME = {
    1: "Apr", 2: "May", 3: "Jun", 4: "Jul",
    5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov",
    9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar",
}

FY_MONTH_TO_QUARTER = {
    1: "Q1", 2: "Q1", 3: "Q1",
    4: "Q2", 5: "Q2", 6: "Q2",
    7: "Q3", 8: "Q3", 9: "Q3",
    10: "Q4", 11: "Q4", 12: "Q4",
}


def _inject_css():
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 0.3rem;
                padding-bottom: 1rem;
            }
            .oa-kpi-card {
                background: linear-gradient(135deg, #ffffff 0%, #f3f6fb 100%);
                border-radius: 12px;
                padding: 12px 14px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.06);
                border-left: 5px solid var(--accent, #2563eb);
                min-height: 100px;
            }
            .oa-kpi-label {
                font-size: 11px;
                color: #6b7280;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: .03em;
                margin-bottom: 4px;
            }
            .oa-kpi-value {
                font-size: 21px;
                font-weight: 800;
                color: #111827;
            }
            .oa-kpi-sub {
                font-size: 11px;
                color: #9ca3af;
                margin-top: 3px;
            }
            .oa-section-title {
                font-size: 18px;
                font-weight: 700;
                color: #111827;
                margin: 15px 0 6px 0;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 5px;
            }
            [data-testid="stDataFrame"] table {
                font-size: 11px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(label, value, sub="", color="blue"):
    st.markdown(
        f"""
        <div class="oa-kpi-card" style="--accent:{ACCENT.get(color, '#2563eb')}">
            <div class="oa-kpi-label">{label}</div>
            <div class="oa-kpi-value">{value}</div>
            <div class="oa-kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _inr(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "₹0"

    sign = "-" if value < 0 else ""
    return f"{sign}₹{abs(value):,.0f}"


def _get_date_range(fin_year):
    start_year, end_year = map(int, fin_year.split("-"))
    return f"{start_year}-04-01", f"{end_year}-03-31"


def _find_column(df, candidates):
    """Return the first matching dataframe column, case-insensitively."""
    lookup = {str(column).strip().lower(): column for column in df.columns}
    for candidate in candidates:
        match = lookup.get(candidate.lower())
        if match is not None:
            return match
    return None


def _normalise_text(series):
    return series.fillna("").astype(str).str.strip()


def _filter_equals(df, column, selected_value):
    if column and selected_value != "All":
        return df[_normalise_text(df[column]) == str(selected_value).strip()]
    return df


def _derive_period_columns(df, invoice_date_col):
    result = df.copy()

    if invoice_date_col is None:
        result["Month"] = None
        result["Quarter"] = None
        return result

    result[invoice_date_col] = pd.to_datetime(
        result[invoice_date_col], errors="coerce"
    )
    result["_fy_month"] = result[invoice_date_col].dt.month.map(CALENDAR_TO_FY_MONTH)
    result["Month"] = result["_fy_month"].map(FY_MONTH_TO_NAME)
    result["Quarter"] = result["_fy_month"].map(FY_MONTH_TO_QUARTER)
    return result


def _load_outstanding_data(start_date, end_date, force_refresh=False):
    if force_refresh:
        get_outstanding_data.clear()

    return get_outstanding_data(
        branch=DEFAULT_PARAMS.get("branch", "00000"),
        grtype=DEFAULT_PARAMS.get("grtype", "C"),
        from_dt=start_date,
        to_dt=end_date,
        as_on_dt=end_date,
        custcode=DEFAULT_PARAMS.get("custcode", "0000"),
        invoiceno=DEFAULT_PARAMS.get("invoiceno", ""),
        user=DEFAULT_PARAMS.get("user", "SYST"),
    )


def show_OutstandingAnalysis():
    _inject_css()

    header_left, header_right = st.columns([8, 1])

    with header_left:
        st.markdown(
            """
            <h3 style='margin:0;padding:0;'>📈 Outstanding Analysis</h3>
            <p style='margin:0;color:#64748b;font-size:12px;'>
                Zone / Circle / Branch / Customer wise receivables and ageing
            </p>
            """,
            unsafe_allow_html=True,
        )

    with header_right:
        refresh_clicked = st.button(
            "🔄 Refresh",
            key="oa_refresh_btn",
            use_container_width=True,
        )

    # ------------------------------------------------------------------
    # SAME TOP FILTER STYLE AS OVERVIEW
    # ------------------------------------------------------------------
    (
        filter_col1,
        filter_col2,
        filter_col3,
        filter_col4,
        filter_col5,
        filter_col6,
        filter_col7,
        filter_col8,
    ) = st.columns(8)

    with filter_col1:
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
            key="oa_financial_year",
        )

    if fy == "Select FY":
        st.info("Please select financial year")
        return

    start_date, end_date = _get_date_range(fy)

    try:
        with st.spinner("Loading outstanding data..."):
            df = _load_outstanding_data(
                start_date,
                end_date,
                force_refresh=refresh_clicked,
            )
    except Exception as exc:
        st.error(f"Unable to load outstanding data: {exc}")
        return

    if df is None or df.empty:
        st.warning("No outstanding data found for the selected financial year")
        return

    st.session_state["oa_last_refreshed"] = datetime.now()

    # Resolve hierarchy columns flexibly because SP column names may differ.
    zone_col = _find_column(df, ["zonename", "zone"])
    circle_col = _find_column(df, ["circlename", "circle"])
    branch_col = _find_column(df, ["branchname", "branch"])
    customer_col = _find_column(df, ["custname", "customername", "customer"])
    doctype_col = _find_column(df, ["documenttype", "doctype"])
    invoice_date_col = _find_column(df, ["invoicedt", "invoice_date", "invoicedate"])

    df = _derive_period_columns(df, invoice_date_col)

    # ------------------------------------------------------------------
    # ROLE / DATA-SCOPE LOGIC COPIED FROM OVERVIEW
    # ------------------------------------------------------------------
    data_scope = st.session_state.get("data_scope", {}) or {}

    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    # Derive parent hierarchy from branch rights.
    if locked_branch and branch_col:
        branch_rows = df[_normalise_text(df[branch_col]) == str(locked_branch).strip()]
        if not branch_rows.empty:
            if circle_col:
                locked_circle = branch_rows[circle_col].iloc[0]
            if zone_col:
                locked_zone = branch_rows[zone_col].iloc[0]

    # Derive zone from circle rights.
    elif locked_circle and circle_col:
        circle_rows = df[_normalise_text(df[circle_col]) == str(locked_circle).strip()]
        if not circle_rows.empty and zone_col:
            locked_zone = circle_rows[zone_col].iloc[0]

    # Apply locked scope immediately so users cannot access data outside rights.
    scoped_df = df.copy()
    if locked_zone and zone_col:
        scoped_df = _filter_equals(scoped_df, zone_col, locked_zone)
    if locked_circle and circle_col:
        scoped_df = _filter_equals(scoped_df, circle_col, locked_circle)
    if locked_branch and branch_col:
        scoped_df = _filter_equals(scoped_df, branch_col, locked_branch)

    if scoped_df.empty:
        st.warning("No data is available for your assigned data scope")
        return

    # Zone filter
    with filter_col2:
        if locked_zone:
            zone = str(locked_zone)
            st.selectbox(
                "Zone",
                [zone],
                disabled=True,
                help="Locked as per your assigned rights",
                key="oa_zone_locked",
            )
        elif zone_col:
            zone_options = sorted(_normalise_text(scoped_df[zone_col]).replace("", pd.NA).dropna().unique().tolist())
            zone = st.selectbox("Zone", ["All"] + zone_options, key="oa_zone")
        else:
            zone = "All"
            st.selectbox("Zone", ["All"], disabled=True, key="oa_zone_missing")

    filtered_df = _filter_equals(scoped_df, zone_col, zone)

    # Circle filter
    with filter_col3:
        if locked_circle:
            circle = str(locked_circle)
            st.selectbox(
                "Circle",
                [circle],
                disabled=True,
                help="Locked as per your assigned rights",
                key="oa_circle_locked",
            )
        elif circle_col:
            circle_options = sorted(_normalise_text(filtered_df[circle_col]).replace("", pd.NA).dropna().unique().tolist())
            circle = st.selectbox("Circle", ["All"] + circle_options, key="oa_circle")
        else:
            circle = "All"
            st.selectbox("Circle", ["All"], disabled=True, key="oa_circle_missing")

    filtered_df = _filter_equals(filtered_df, circle_col, circle)

    # Branch filter
    with filter_col4:
        if locked_branch:
            branch = str(locked_branch)
            st.selectbox(
                "Branch",
                [branch],
                disabled=True,
                help="Locked as per your assigned rights",
                key="oa_branch_locked",
            )
        elif branch_col:
            branch_options = sorted(_normalise_text(filtered_df[branch_col]).replace("", pd.NA).dropna().unique().tolist())
            branch = st.selectbox("Branch", ["All"] + branch_options, key="oa_branch")
        else:
            branch = "All"
            st.selectbox("Branch", ["All"], disabled=True, key="oa_branch_missing")

    filtered_df = _filter_equals(filtered_df, branch_col, branch)

    # Quarter filter
    with filter_col5:
        available_quarters = [
            q for q in QUARTER_ORDER
            if q in filtered_df["Quarter"].dropna().unique().tolist()
        ]
        quarter = st.selectbox(
            "Quarter",
            ["All"] + available_quarters,
            key="oa_quarter",
        )

    if quarter != "All":
        filtered_df = filtered_df[filtered_df["Quarter"] == quarter]

    # Month filter
    with filter_col6:
        available_months = [
            m for m in MONTH_ORDER
            if m in filtered_df["Month"].dropna().unique().tolist()
        ]
        month = st.selectbox(
            "Month",
            ["All"] + available_months,
            key="oa_month",
        )

    if month != "All":
        filtered_df = filtered_df[filtered_df["Month"] == month]

    # Customer filter
    with filter_col7:
        if customer_col:
            customer_options = sorted(_normalise_text(filtered_df[customer_col]).replace("", pd.NA).dropna().unique().tolist())
            customer = st.selectbox(
                "Customer",
                ["All"] + customer_options,
                key="oa_customer",
            )
        else:
            customer = "All"
            st.selectbox("Customer", ["All"], disabled=True, key="oa_customer_missing")

    filtered_df = _filter_equals(filtered_df, customer_col, customer)

    # Age bucket filter
    with filter_col8:
        available_buckets = [
            bucket for bucket in ["0-30", "31-60", "61-90", "Above 90"]
            if "age_bucket" in filtered_df.columns
            and bucket in filtered_df["age_bucket"].dropna().unique().tolist()
        ]
        age_bucket = st.selectbox(
            "Age Bucket",
            ["All"] + available_buckets,
            key="oa_age_bucket",
        )

    if age_bucket != "All" and "age_bucket" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["age_bucket"] == age_bucket]

    if filtered_df.empty:
        st.warning("No data found for selected filters")
        return

    # Additional document type filter retained below the Overview-style row.
    if doctype_col:
        doc_options = sorted(_normalise_text(filtered_df[doctype_col]).replace("", pd.NA).dropna().unique().tolist())
        document_type = st.selectbox(
            "Document Type",
            ["All"] + doc_options,
            key="oa_document_type",
        )
        filtered_df = _filter_equals(filtered_df, doctype_col, document_type)

    if filtered_df.empty:
        st.warning("No data found for selected document type")
        return

    fdf = filtered_df.copy()

    # ------------------------------------------------------------------
    # KPI ROW
    # ------------------------------------------------------------------
    total_bill = fdf["billamount"].sum() if "billamount" in fdf.columns else 0
    total_recd = fdf["recdamount"].sum() if "recdamount" in fdf.columns else 0
    total_balance = fdf["balance"].sum() if "balance" in fdf.columns else 0
    total_onacc = fdf["onaccrecd"].sum() if "onaccrecd" in fdf.columns else 0
    total_net = fdf["netbalance"].sum() if "netbalance" in fdf.columns else 0

    overdue_90 = 0
    if "age_bucket" in fdf.columns and "netbalance" in fdf.columns:
        overdue_90 = fdf.loc[
            fdf["age_bucket"] == "Above 90", "netbalance"
        ].sum()

    invoice_count = (
        fdf["invoiceno"].nunique()
        if "invoiceno" in fdf.columns
        else len(fdf)
    )
    customer_count = (
        fdf[customer_col].nunique()
        if customer_col and customer_col in fdf.columns
        else 0
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        _kpi_card("Total Billed", _inr(total_bill), f"{invoice_count:,} invoices", "blue")
    with k2:
        _kpi_card("Total Received", _inr(total_recd), "incl. on-account", "green")
    with k3:
        _kpi_card("Balance", _inr(total_balance), "before on-account adj.", "teal")
    with k4:
        _kpi_card("On-Account Recd", _inr(total_onacc), "", "purple")
    with k5:
        _kpi_card("Net Outstanding", _inr(total_net), f"{customer_count:,} customers", "amber")
    with k6:
        _kpi_card("Overdue > 90 Days", _inr(overdue_90), "high risk", "red")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # CHARTS ROW 1
    # ------------------------------------------------------------------
    st.markdown(
        "<div class='oa-section-title'>Ageing & Zone-wise Outstanding</div>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 1.3])

    with c1:
        if "age_bucket" in fdf.columns and "netbalance" in fdf.columns:
            bucket_order = ["0-30", "31-60", "61-90", "Above 90"]
            age_df = (
                fdf.groupby("age_bucket")["netbalance"]
                .sum()
                .reindex(bucket_order)
                .fillna(0)
                .reset_index()
            )
            fig_age = px.pie(
                age_df,
                names="age_bucket",
                values="netbalance",
                hole=0.55,
                color="age_bucket",
                color_discrete_map={
                    "0-30": "#16a34a",
                    "31-60": "#d97706",
                    "61-90": "#ea580c",
                    "Above 90": "#dc2626",
                },
                title="Net Outstanding by Age Bucket",
            )
            fig_age.update_traces(textinfo="percent+label")
            fig_age.update_layout(
                height=340,
                showlegend=False,
                margin=dict(t=50, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_age, use_container_width=True)
        else:
            st.info("Age bucket data is not available")

    with c2:
        if zone_col and "netbalance" in fdf.columns:
            zone_df = (
                fdf.groupby(zone_col)["netbalance"]
                .sum()
                .sort_values(ascending=True)
                .reset_index()
            )
            fig_zone = px.bar(
                zone_df,
                x="netbalance",
                y=zone_col,
                orientation="h",
                text="netbalance",
                title="Net Outstanding by Zone",
                color="netbalance",
                color_continuous_scale="Blues",
            )
            fig_zone.update_traces(
                texttemplate="₹%{text:,.0f}",
                textposition="outside",
            )
            fig_zone.update_layout(
                height=340,
                coloraxis_showscale=False,
                margin=dict(t=50, b=10, l=10, r=30),
                xaxis_title="Net Outstanding (₹)",
                yaxis_title="",
            )
            st.plotly_chart(fig_zone, use_container_width=True)
        else:
            st.info("Zone data is not available")

    # ------------------------------------------------------------------
    # CHARTS ROW 2
    # ------------------------------------------------------------------
    st.markdown(
        "<div class='oa-section-title'>Top Customers & Branch Performance</div>",
        unsafe_allow_html=True,
    )
    c3, c4 = st.columns([1.2, 1])

    with c3:
        if customer_col and "netbalance" in fdf.columns:
            top_cust = (
                fdf.groupby(customer_col)["netbalance"]
                .sum()
                .sort_values(ascending=False)
                .head(15)
                .sort_values()
                .reset_index()
            )
            fig_cust = px.bar(
                top_cust,
                x="netbalance",
                y=customer_col,
                orientation="h",
                title="Top 15 Customers by Net Outstanding",
                color="netbalance",
                color_continuous_scale="Reds",
            )
            fig_cust.update_layout(
                height=420,
                coloraxis_showscale=False,
                margin=dict(t=50, b=10, l=10, r=20),
                xaxis_title="Net Outstanding (₹)",
                yaxis_title="",
            )
            st.plotly_chart(fig_cust, use_container_width=True)
        else:
            st.info("Customer data is not available")

    with c4:
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
                        "Net_Outstanding", ascending=False
                    )

                money_columns = [
                    column for column in ["Billed", "Received", "Net_Outstanding"]
                    if column in branch_summary.columns
                ]
                format_map = {column: "₹{:,.0f}" for column in money_columns}
                if "Invoices" in branch_summary.columns:
                    format_map["Invoices"] = "{:,.0f}"

                st.dataframe(
                    branch_summary.style.format(format_map),
                    height=420,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Branch summary fields are not available")
        else:
            st.info("Branch data is not available")

    # ------------------------------------------------------------------
    # MONTHLY TREND
    # ------------------------------------------------------------------
    if invoice_date_col and "billamount" in fdf.columns:
        st.markdown(
            "<div class='oa-section-title'>Monthly Billing vs Collection Trend</div>",
            unsafe_allow_html=True,
        )

        trend_df = fdf.copy()
        trend_df[invoice_date_col] = pd.to_datetime(
            trend_df[invoice_date_col], errors="coerce"
        )
        trend_df["month_start"] = (
            trend_df[invoice_date_col].dt.to_period("M").dt.to_timestamp()
        )

        agg_map = {"Billed": ("billamount", "sum")}
        if "recdamount" in trend_df.columns:
            agg_map["Received"] = ("recdamount", "sum")

        trend = trend_df.groupby("month_start").agg(**agg_map).reset_index()

        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Bar(
                x=trend["month_start"],
                y=trend["Billed"],
                name="Billed",
                marker_color="#2563eb",
            )
        )

        if "Received" in trend.columns:
            fig_trend.add_trace(
                go.Scatter(
                    x=trend["month_start"],
                    y=trend["Received"],
                    name="Received",
                    mode="lines+markers",
                    line=dict(color="#16a34a", width=3),
                )
            )

        fig_trend.update_layout(
            height=350,
            barmode="group",
            margin=dict(t=30, b=10, l=10, r=10),
            yaxis_title="Amount (₹)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
            ),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    # ------------------------------------------------------------------
    # DETAIL TABLE + EXPORT
    # ------------------------------------------------------------------
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
        doctype_col,
        "invoiceno",
        invoice_date_col,
        "duedt",
        "billamount",
        "recdamount",
        "balance",
        "onaccrecd",
        "netbalance",
        "outstandingdays",
        "age_bucket",
    ]

    show_cols = []
    for column in preferred_columns:
        if column and column in fdf.columns and column not in show_cols:
            show_cols.append(column)

    search = st.text_input(
        "🔍 Search customer, invoice number, branch...",
        "",
        key="oa_search",
    )

    detail_df = fdf[show_cols].copy() if show_cols else fdf.copy()

    if search:
        search_mask = detail_df.apply(
            lambda row: row.astype(str)
            .str.contains(search, case=False, na=False)
            .any(),
            axis=1,
        )
        detail_df = detail_df[search_mask]

    st.dataframe(
        detail_df,
        use_container_width=True,
        height=420,
        hide_index=True,
    )

    export_buffer = io.BytesIO()
    with pd.ExcelWriter(export_buffer, engine="openpyxl") as writer:
        detail_df.to_excel(writer, index=False, sheet_name="Outstanding")

    st.download_button(
        "⬇️ Download filtered data (Excel)",
        data=export_buffer.getvalue(),
        file_name=f"outstanding_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="oa_download",
    )

    last_refreshed = st.session_state.get("oa_last_refreshed", datetime.now())
    st.caption(
        f"Last refreshed: {last_refreshed.strftime('%d-%b-%Y %H:%M')} "
        f"| Total records: {len(fdf):,}"
    )
