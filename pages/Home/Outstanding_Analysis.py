import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.data_Outstanding import (
    get_engine,
    get_outstanding_data,
    DEFAULT_PARAMS,
)

ACCENT = {
    "blue": "#2563eb",
    "green": "#16a34a",
    "red": "#dc2626",
    "amber": "#d97706",
    "purple": "#7c3aed",
    "teal": "#0d9488",
}


def _inject_css():
    st.markdown(
        """
        <style>
            .oa-kpi-card {
                background: linear-gradient(135deg, #ffffff 0%, #f3f6fb 100%);
                border-radius: 14px;
                padding: 18px 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.06);
                border-left: 6px solid var(--accent, #2563eb);
                text-align: left;
            }
            .oa-kpi-label {
                font-size: 13px; color: #6b7280; font-weight: 600;
                text-transform: uppercase; letter-spacing: .04em; margin-bottom: 4px;
            }
            .oa-kpi-value { font-size: 26px; font-weight: 700; color: #111827; }
            .oa-kpi-sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
            .oa-section-title {
                font-size: 20px; font-weight: 700; color: #111827;
                margin: 18px 0 6px 0; border-bottom: 2px solid #e5e7eb; padding-bottom: 6px;
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


def _inr(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "₹0"
    neg = x < 0
    x = abs(x)
    return f"{'-' if neg else ''}₹{x:,.0f}"


def show_OutstandingAnalysis():
    _inject_css()

    st.markdown(
        "<h2 style='margin-bottom:0;'>📈 Outstanding Analysis</h2>"
        "<p style='color:#6b7280;margin-top:0;'>Zone / Branch / Customer wise receivables &amp; ageing (Alloutstanding_BI)</p>",
        unsafe_allow_html=True,
    )

    # ----------------------------------------------------------------
    # AUTOMATIC DATABASE LOAD
    # ----------------------------------------------------------------
    # Database credentials are read from .streamlit/secrets.toml or
    # Streamlit Cloud > App settings > Secrets. Nothing is entered manually.
    #
    # Expected secrets format:
    # [database]
    # server = "your-server"
    # database = "your-database"
    # username = "your-username"
    # password = "your-password"

    def load_report_data():
        try:
            db = st.secrets["database"]
            engine = get_engine(
                db["server"],
                db["database"],
                db["username"],
                db["password"],
            )

            return get_outstanding_data(
                engine,
                DEFAULT_PARAMS["branch"],
                DEFAULT_PARAMS["grtype"],
                DEFAULT_PARAMS["from_dt"].strftime("%Y-%m-%d"),
                DEFAULT_PARAMS["to_dt"].strftime("%Y-%m-%d"),
                DEFAULT_PARAMS["as_on_dt"].strftime("%Y-%m-%d"),
                DEFAULT_PARAMS["custcode"],
                DEFAULT_PARAMS["invoiceno"],
                DEFAULT_PARAMS["user"],
            )
        except KeyError as exc:
            st.error(f"Missing database secret: {exc}")
            return pd.DataFrame()
        except Exception as exc:
            st.error(f"Unable to load outstanding data: {exc}")
            return pd.DataFrame()

    refresh_col, status_col = st.columns([1, 5])
    with refresh_col:
        refresh_clicked = st.button(
            "🔄 Refresh Data",
            key="oa_refresh_btn",
            use_container_width=True,
        )

    if refresh_clicked or "oa_df" not in st.session_state:
        with st.spinner("Loading outstanding data..."):
            st.session_state["oa_df"] = load_report_data()
            st.session_state["oa_last_refresh"] = datetime.now()

    df = st.session_state.get("oa_df", pd.DataFrame())

    with status_col:
        last_refresh = st.session_state.get("oa_last_refresh")
        if last_refresh and not df.empty:
            st.caption(
                f"Database connected · {len(df):,} records · "
                f"Last refreshed: {last_refresh.strftime('%d-%b-%Y %H:%M')}"
            )

    if df.empty:
        st.warning("No outstanding data was returned from the database.")
        return

    # ----------------------------------------------------------------
    # FILTERS
    # ----------------------------------------------------------------
    f1, f2, f3, f4, f5 = st.columns(5)
    zones = sorted(df["zonename"].dropna().unique()) if "zonename" in df.columns else []
    branches = sorted(df["branchname"].dropna().unique()) if "branchname" in df.columns else []
    customers = sorted(df["custname"].dropna().unique()) if "custname" in df.columns else []
    doctypes = sorted(df["documenttype"].dropna().unique()) if "documenttype" in df.columns else []

    sel_zone = f1.multiselect("Zone", zones, placeholder="All zones", key="oa_f_zone")
    sel_branch = f2.multiselect("Branch", branches, placeholder="All branches", key="oa_f_branch")
    sel_customer = f3.multiselect("Customer", customers, placeholder="All customers", key="oa_f_cust")
    sel_doctype = f4.multiselect("Document Type", doctypes, placeholder="All doc types", key="oa_f_doctype")
    sel_bucket = f5.multiselect("Age Bucket", ["0-30", "31-60", "61-90", "Above 90"], placeholder="All buckets", key="oa_f_bucket")

    fdf = df.copy()
    if sel_zone:
        fdf = fdf[fdf["zonename"].isin(sel_zone)]
    if sel_branch:
        fdf = fdf[fdf["branchname"].isin(sel_branch)]
    if sel_customer:
        fdf = fdf[fdf["custname"].isin(sel_customer)]
    if sel_doctype:
        fdf = fdf[fdf["documenttype"].isin(sel_doctype)]
    if sel_bucket:
        fdf = fdf[fdf["age_bucket"].isin(sel_bucket)]

    # ----------------------------------------------------------------
    # KPI ROW
    # ----------------------------------------------------------------
    total_bill = fdf["billamount"].sum() if "billamount" in fdf else 0
    total_recd = fdf["recdamount"].sum() if "recdamount" in fdf else 0
    total_balance = fdf["balance"].sum() if "balance" in fdf else 0
    total_onacc = fdf["onaccrecd"].sum() if "onaccrecd" in fdf else 0
    total_net = fdf["netbalance"].sum() if "netbalance" in fdf else 0
    overdue_90 = fdf.loc[fdf["age_bucket"] == "Above 90", "netbalance"].sum() if "netbalance" in fdf else 0
    invoice_count = fdf["invoiceno"].nunique() if "invoiceno" in fdf else len(fdf)
    customer_count = fdf["custname"].nunique() if "custname" in fdf else 0

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

    st.write("")

    # ----------------------------------------------------------------
    # CHARTS ROW 1 - Ageing + Zone
    # ----------------------------------------------------------------
    st.markdown("<div class='oa-section-title'>Ageing & Zone-wise Outstanding</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.3])

    with c1:
        bucket_order = ["0-30", "31-60", "61-90", "Above 90"]
        age_df = fdf.groupby("age_bucket")["netbalance"].sum().reindex(bucket_order).fillna(0).reset_index()
        fig_age = px.pie(
            age_df, names="age_bucket", values="netbalance", hole=0.55, color="age_bucket",
            color_discrete_map={"0-30": "#16a34a", "31-60": "#d97706", "61-90": "#ea580c", "Above 90": "#dc2626"},
            title="Net Outstanding by Age Bucket",
        )
        fig_age.update_traces(textinfo="percent+label")
        fig_age.update_layout(height=380, showlegend=False, margin=dict(t=50, b=10, l=10, r=10))
        st.plotly_chart(fig_age, use_container_width=True)

    with c2:
        if "zonename" in fdf.columns:
            zone_df = fdf.groupby("zonename")["netbalance"].sum().sort_values(ascending=True).reset_index()
            fig_zone = px.bar(
                zone_df, x="netbalance", y="zonename", orientation="h", text="netbalance",
                title="Net Outstanding by Zone", color="netbalance", color_continuous_scale="Blues",
            )
            fig_zone.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            fig_zone.update_layout(height=380, coloraxis_showscale=False, margin=dict(t=50, b=10, l=10, r=10),
                                    xaxis_title="Net Outstanding (₹)", yaxis_title="")
            st.plotly_chart(fig_zone, use_container_width=True)

    # ----------------------------------------------------------------
    # CHARTS ROW 2 - Top customers + Branch table
    # ----------------------------------------------------------------
    st.markdown("<div class='oa-section-title'>Top Customers & Branch Performance</div>", unsafe_allow_html=True)
    c3, c4 = st.columns([1.2, 1])

    with c3:
        top_cust = (
            fdf.groupby("custname")["netbalance"].sum().sort_values(ascending=False).head(15).sort_values().reset_index()
        )
        fig_cust = px.bar(
            top_cust, x="netbalance", y="custname", orientation="h",
            title="Top 15 Customers by Net Outstanding", color="netbalance", color_continuous_scale="Reds",
        )
        fig_cust.update_layout(height=440, coloraxis_showscale=False, margin=dict(t=50, b=10, l=10, r=10),
                                xaxis_title="Net Outstanding (₹)", yaxis_title="")
        st.plotly_chart(fig_cust, use_container_width=True)

    with c4:
        if "branchname" in fdf.columns:
            branch_summary = (
                fdf.groupby("branchname")
                .agg(
                    Billed=("billamount", "sum"),
                    Received=("recdamount", "sum"),
                    Net_Outstanding=("netbalance", "sum"),
                    Invoices=("invoiceno", "nunique"),
                )
                .sort_values("Net_Outstanding", ascending=False)
                .reset_index()
            )
            st.dataframe(
                branch_summary.style.format(
                    {"Billed": "₹{:,.0f}", "Received": "₹{:,.0f}", "Net_Outstanding": "₹{:,.0f}", "Invoices": "{:,.0f}"}
                ),
                height=440, use_container_width=True,
            )

    # ----------------------------------------------------------------
    # TREND CHART
    # ----------------------------------------------------------------
    if "invoicedt" in fdf.columns:
        st.markdown("<div class='oa-section-title'>Monthly Billing vs Collection Trend</div>", unsafe_allow_html=True)
        trend_df = fdf.copy()
        trend_df["month"] = trend_df["invoicedt"].dt.to_period("M").dt.to_timestamp()
        trend = trend_df.groupby("month").agg(Billed=("billamount", "sum"), Received=("recdamount", "sum")).reset_index()

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(x=trend["month"], y=trend["Billed"], name="Billed", marker_color="#2563eb"))
        fig_trend.add_trace(go.Scatter(x=trend["month"], y=trend["Received"], name="Received", mode="lines+markers", line=dict(color="#16a34a", width=3)))
        fig_trend.update_layout(height=380, barmode="group", margin=dict(t=30, b=10, l=10, r=10),
                                 yaxis_title="Amount (₹)", legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_trend, use_container_width=True)

    # ----------------------------------------------------------------
    # DETAIL TABLE + EXPORT
    # ----------------------------------------------------------------
    st.markdown("<div class='oa-section-title'>Detailed Records</div>", unsafe_allow_html=True)

    show_cols = [
        c for c in [
            "zonename", "branchname", "custname", "grtype", "documenttype", "invoiceno",
            "invoicedt", "duedt", "billamount", "recdamount", "balance", "onaccrecd",
            "netbalance", "outstandingdays", "age_bucket",
        ] if c in fdf.columns
    ]

    search = st.text_input("🔍 Search (customer, invoice no, branch...)", "", key="oa_search")
    detail_df = fdf[show_cols]
    if search:
        mask = detail_df.apply(lambda r: r.astype(str).str.contains(search, case=False, na=False).any(), axis=1)
        detail_df = detail_df[mask]

    st.dataframe(detail_df, use_container_width=True, height=420)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        detail_df.to_excel(writer, index=False, sheet_name="Outstanding")
    st.download_button(
        "⬇️ Download filtered data (Excel)",
        data=buf.getvalue(),
        file_name=f"outstanding_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="oa_download",
    )

    st.caption(f"Last refreshed: {datetime.now().strftime('%d-%b-%Y %H:%M')} | Total records: {len(fdf):,}")