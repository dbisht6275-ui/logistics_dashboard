from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.data_loader import get_date_range
from services.net_profit_data_loader import load_net_profit_data_pair
from services.branch_agency_mast import load_stationmast_data


# ============================================================
# NET PROFIT DASHBOARD
#
# Separate dashboard.
# Existing PNL_Analysis.py is not changed.
# ============================================================

FY_OPTIONS = [
    "Select FY",
    "2026-2027",
    "2025-2026",
    "2024-2025",
    "2023-2024",
    "2022-2023",
    "2021-2022",
    "2020-2021",
]

MONTH_ORDER = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]


# ============================================================
# HELPERS
# ============================================================

def get_previous_fy(fy):
    start_year, end_year = map(int, fy.split("-"))
    return f"{start_year - 1}-{end_year - 1}"


def get_conversion(conversion_type):
    if conversion_type == "Lac":
        return 100_000, "Lac"
    return 10_000_000, "Cr"


def amount_text(value, conversion_type):
    divisor, unit = get_conversion(conversion_type)
    return f"₹{float(value or 0) / divisor:,.2f} {unit}"


def pct_change(current, previous):
    current = float(current or 0)
    previous = float(previous or 0)

    if previous == 0:
        return 0.0

    return ((current - previous) / abs(previous)) * 100


def safe_options(df, column):
    if df is None or df.empty or column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[values.ne("")]

    return sorted(
        values.unique().tolist(),
        key=str.casefold,
    )


def apply_multi_filter(df, column, selected):
    if (
        df is None
        or df.empty
        or column not in df.columns
        or not selected
    ):
        return df

    return df[df[column].isin(selected)].copy()


def _normalise_branch_name(value):
    return " ".join(str(value).strip().casefold().split())


def _filter_to_branch_scope(df, branch_names):
    if df is None or df.empty or "BRANCH" not in df.columns or not branch_names:
        return df

    allowed = {_normalise_branch_name(value) for value in branch_names}
    branch_key = df["BRANCH"].fillna("").map(_normalise_branch_name)
    return df[branch_key.isin(allowed)].copy()


def _apply_pnl_business_rule(df, all_branches):
    """
    All branches  -> Origin view P&L only.
    Explicit branch selection -> Origin P&L + Destination P&L.
    Overhead is deducted once in both cases.
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    for column in [
        "ORIGIN_PNL",
        "DESTINATION_PNL",
        "ORIGIN_BUSINESS",
        "DESTINATION_BUSINESS",
        "ORIGIN_TOTAL_INCOME",
        "DESTINATION_TOTAL_INCOME",
        "ORIGIN_DIRECT_EXPENSE",
        "DESTINATION_DIRECT_EXPENSE",
        "TOTAL EXPENSE",
    ]:
        if column not in out.columns:
            out[column] = 0.0
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)

    if all_branches:
        # Consolidated dashboard must not count the same GR-level P&L twice.
        out["DESTINATION_PNL"] = 0.0
        out["DESTINATION_BUSINESS"] = 0.0
        out["DESTINATION_TOTAL_INCOME"] = 0.0
        out["DESTINATION_DIRECT_EXPENSE"] = 0.0

    out["BUSINESS"] = out["ORIGIN_BUSINESS"] + out["DESTINATION_BUSINESS"]
    out["TOTAL_INCOME"] = out["ORIGIN_TOTAL_INCOME"] + out["DESTINATION_TOTAL_INCOME"]
    out["DIRECT_EXPENSE"] = out["ORIGIN_DIRECT_EXPENSE"] + out["DESTINATION_DIRECT_EXPENSE"]
    out["COMBINED_PNL"] = out["ORIGIN_PNL"] + out["DESTINATION_PNL"]
    out["NET_PROFIT"] = out["COMBINED_PNL"] - out["TOTAL EXPENSE"]

    out["NET_PROFIT_MARGIN"] = 0.0
    valid_income = out["TOTAL_INCOME"].ne(0)
    out.loc[valid_income, "NET_PROFIT_MARGIN"] = (
        out.loc[valid_income, "NET_PROFIT"]
        / out.loc[valid_income, "TOTAL_INCOME"]
        * 100
    )

    return out


def calculate_kpis(df):
    if df is None or df.empty:
        return {
            "origin_pnl": 0.0,
            "destination_pnl": 0.0,
            "combined_pnl": 0.0,
            "salary": 0.0,
            "godown": 0.0,
            "overhead": 0.0,
            "claim": 0.0,
            "total_expense": 0.0,
            "net_profit": 0.0,
            "total_income": 0.0,
            "margin": 0.0,
        }

    values = {
        "origin_pnl": float(df["ORIGIN_PNL"].sum()),
        "destination_pnl": float(df["DESTINATION_PNL"].sum()),
        "combined_pnl": float(df["COMBINED_PNL"].sum()),
        "salary": float(df["SALARY"].sum()),
        "godown": float(df["GODOWN RENT"].sum()),
        "overhead": float(df["OVERHEAD EXPENSE"].sum()),
        "claim": float(df["CLAIM"].sum()),
        "total_expense": float(df["TOTAL EXPENSE"].sum()),
        "net_profit": float(df["NET_PROFIT"].sum()),
        "total_income": float(df["TOTAL_INCOME"].sum()),
    }

    values["margin"] = (
        values["net_profit"] / values["total_income"] * 100
        if values["total_income"]
        else 0.0
    )

    return values


def _inject_css():
    st.markdown(
        """
        <style>
        :root {
            --np-navy:#102a43;
            --np-blue:#2563eb;
            --np-muted:#64748b;
            --np-border:#dbe4ef;
        }

        .block-container {
            max-width:100% !important;
            padding:.45rem .8rem .9rem !important;
        }

        .np-title {
            color:var(--np-navy);
            font-size:20px;
            font-weight:850;
            letter-spacing:-.3px;
        }

        .np-subtitle {
            color:var(--np-muted);
            font-size:11px;
            margin-top:2px;
        }

        .np-card {
            min-height:92px;
            border:1px solid #dbe4ef;
            border-radius:14px;
            padding:10px 11px;
            background:linear-gradient(145deg,#ffffff,#f7faff);
            box-shadow:0 5px 14px rgba(15,42,67,.07);
        }

        .np-card-title {
            font-size:10px;
            color:#64748b;
            font-weight:650;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .np-card-value {
            margin-top:5px;
            font-size:17px;
            color:#102a43;
            font-weight:850;
            white-space:nowrap;
        }

        .np-card-footer {
            margin-top:6px;
            font-size:9px;
            color:#64748b;
        }

        .np-positive { color:#15803d; }
        .np-negative { color:#dc2626; }

        .np-section-title {
            font-size:15px;
            color:#0f2744;
            font-weight:700;
            margin:2px 0 8px 1px;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border:1px solid #dce5ef !important;
            border-radius:14px !important;
            background:#ffffff !important;
            box-shadow:0 6px 16px rgba(15,42,67,.06) !important;
        }

        [data-testid="stDataFrame"] {
            border:1px solid #e2e8f0;
            border-radius:10px;
            overflow:hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(title, current, previous, conversion_type=None, percent=False, reverse_good=False):
    if percent:
        current_text = f"{current:,.2f}%"
        previous_text = f"{previous:,.2f}%"
        growth = current - previous
        growth_label = f"{growth:+.2f} pp"
        good = growth <= 0 if reverse_good else growth >= 0
    else:
        current_text = amount_text(current, conversion_type)
        previous_text = amount_text(previous, conversion_type)
        growth = pct_change(current, previous)
        growth_label = f"{growth:+.1f}%"
        good = growth <= 0 if reverse_good else growth >= 0

    class_name = "np-positive" if good else "np-negative"

    st.markdown(
        f"""
        <div class="np-card">
            <div class="np-card-title">{escape(title)}</div>
            <div class="np-card-value">{escape(current_text)}</div>
            <div class="np-card-footer">
                LY: {escape(previous_text)}
                &nbsp;·&nbsp;
                <span class="{class_name}">{escape(growth_label)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_same_filters(df, filters):
    out = df.copy()

    for column, selected in filters.items():
        out = apply_multi_filter(out, column, selected)

    return out


# ============================================================
# DASHBOARD
# ============================================================

def show_net_profit_dashboard():
    _inject_css()

    st.markdown(
        """
        <div class="np-title">Net Profit Dashboard</div>
        <div class="np-subtitle">
            Origin P&L + Destination P&L − Branch overhead
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # --------------------------------------------------------
    # PRIMARY FILTERS
    # --------------------------------------------------------

    filter_cols = st.columns([1.15, 1, 1.35, 1.2, 1.2, 1.1, 1.0], gap="small")

    with filter_cols[0]:
        fy = st.selectbox(
            "Financial Year",
            FY_OPTIONS,
            key="np_fy",
        )

    if fy == "Select FY":
        st.info("Please select financial year.")
        return

    start_date, end_date = get_date_range(fy)
    prev_fy = get_previous_fy(fy)
    prev_start, prev_end = get_date_range(prev_fy)

    # Branch/Agency master is loaded first and becomes the dashboard branch scope.
    branch_master_df = load_stationmast_data(start_date, end_date)
    valid_branches = safe_options(branch_master_df, "BRANCH")

    if not valid_branches:
        st.warning("No valid branches found in Branch/Agency Master for selected financial year.")
        return

    with st.spinner("Loading Origin, Destination and branch overhead..."):
        raw_df, raw_prev_df = load_net_profit_data_pair(
            start_date,
            end_date,
            prev_start,
            prev_end,
        )

    if raw_df is None or raw_df.empty:
        st.warning("No Net Profit data found for selected financial year.")
        return

    # Restrict P&L/overhead to branches returned by Branch/Agency Master.
    df = _filter_to_branch_scope(raw_df.copy(), valid_branches)
    prev_df = (
        _filter_to_branch_scope(raw_prev_df.copy(), valid_branches)
        if raw_prev_df is not None
        else pd.DataFrame()
    )

    with filter_cols[1]:
        conversion_type = st.selectbox(
            "₹ Conversion",
            ["Crore", "Lac"],
            key="np_conversion",
        )

    # Use whichever hierarchy columns are actually available.
    with filter_cols[2]:
        branches = st.multiselect(
            "Branch",
            valid_branches,
            key="np_branch",
            placeholder="All branches",
        )

    with filter_cols[3]:
        zones = st.multiselect(
            "Zone",
            safe_options(df, "zone"),
            key="np_zone",
            placeholder="All zones",
            disabled="zone" not in df.columns,
        )

    with filter_cols[4]:
        circles = st.multiselect(
            "Circle",
            safe_options(df, "circle"),
            key="np_circle",
            placeholder="All circles",
            disabled="circle" not in df.columns,
        )

    with filter_cols[5]:
        quarters = st.multiselect(
            "Quarter",
            QUARTER_ORDER,
            key="np_quarter",
            placeholder="All quarters",
        )

    with filter_cols[6]:
        months = st.multiselect(
            "Month",
            MONTH_ORDER,
            key="np_month",
            placeholder="All months",
        )

    filters = {
        "BRANCH": branches,
        "zone": zones,
        "circle": circles,
        "QUARTER": quarters,
        "MONTH": months,
    }

    df = _apply_same_filters(df, filters)
    prev_df = _apply_same_filters(prev_df, filters) if not prev_df.empty else prev_df

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    # No explicit branch selection means consolidated All Branches mode.
    # In this mode only Origin-view P&L is used.
    all_branches = len(branches) == 0
    df = _apply_pnl_business_rule(df, all_branches=all_branches)
    prev_df = (
        _apply_pnl_business_rule(prev_df, all_branches=all_branches)
        if not prev_df.empty
        else prev_df
    )

    divisor, unit = get_conversion(conversion_type)

    current = calculate_kpis(df)
    previous = calculate_kpis(prev_df)

    # --------------------------------------------------------
    # KPI ROW 1
    # --------------------------------------------------------

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    kpi_cols = st.columns(6, gap="small")

    kpis = [
        ("Origin P&L", current["origin_pnl"], previous["origin_pnl"], False),
        ("Destination P&L", current["destination_pnl"], previous["destination_pnl"], False),
        ("Combined P&L", current["combined_pnl"], previous["combined_pnl"], False),
        ("Total Overhead", current["total_expense"], previous["total_expense"], True),
        ("Net Profit", current["net_profit"], previous["net_profit"], False),
        ("Net Profit Margin", current["margin"], previous["margin"], False),
    ]

    for index, (title, cy, ly, reverse_good) in enumerate(kpis):
        with kpi_cols[index]:
            render_kpi_card(
                title,
                cy,
                ly,
                conversion_type=conversion_type,
                percent=(title == "Net Profit Margin"),
                reverse_good=reverse_good,
            )

    # --------------------------------------------------------
    # KPI ROW 2: OVERHEAD BREAKUP
    # --------------------------------------------------------

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    overhead_cols = st.columns(4, gap="small")

    overhead_kpis = [
        ("Salary", current["salary"], previous["salary"]),
        ("Godown Rent", current["godown"], previous["godown"]),
        ("Overhead Expense", current["overhead"], previous["overhead"]),
        ("Claim", current["claim"], previous["claim"]),
    ]

    for index, (title, cy, ly) in enumerate(overhead_kpis):
        with overhead_cols[index]:
            render_kpi_card(
                title,
                cy,
                ly,
                conversion_type=conversion_type,
                reverse_good=True,
            )

    # --------------------------------------------------------
    # MONTHLY TREND + OVERHEAD BREAKUP
    # --------------------------------------------------------

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.55, 0.85], gap="medium")

    with left:
        with st.container(border=True):
            st.markdown(
                '<div class="np-section-title">Monthly Net Profit Trend</div>',
                unsafe_allow_html=True,
            )

            monthly = (
                df.groupby(["FIN_MONTH", "MONTH"], as_index=False)
                .agg(
                    Origin_PNL=("ORIGIN_PNL", "sum"),
                    Destination_PNL=("DESTINATION_PNL", "sum"),
                    Combined_PNL=("COMBINED_PNL", "sum"),
                    Overhead=("TOTAL EXPENSE", "sum"),
                    Net_Profit=("NET_PROFIT", "sum"),
                )
                .sort_values("FIN_MONTH")
            )

            prev_monthly = (
                prev_df.groupby(["FIN_MONTH", "MONTH"], as_index=False)
                .agg(LY_Net_Profit=("NET_PROFIT", "sum"))
                if prev_df is not None and not prev_df.empty
                else pd.DataFrame(columns=["FIN_MONTH", "MONTH", "LY_Net_Profit"])
            )

            monthly = monthly.merge(
                prev_monthly[["FIN_MONTH", "LY_Net_Profit"]],
                on="FIN_MONTH",
                how="left",
            )

            monthly["LY_Net_Profit"] = pd.to_numeric(
                monthly["LY_Net_Profit"],
                errors="coerce",
            ).fillna(0.0)

            monthly["Net Profit"] = monthly["Net_Profit"] / divisor
            monthly["LY Net Profit"] = monthly["LY_Net_Profit"] / divisor

            fig = go.Figure()

            fig.add_trace(
                go.Bar(
                    x=monthly["MONTH"],
                    y=monthly["LY Net Profit"],
                    name=f"LY ({prev_fy})",
                    marker_color="#cbd5e1",
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>"
                        f"LY Net Profit: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )

            fig.add_trace(
                go.Bar(
                    x=monthly["MONTH"],
                    y=monthly["Net Profit"],
                    name=f"Current ({fy})",
                    marker_color="#2563eb",
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>"
                        f"Net Profit: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )

            fig.add_hline(y=0, line_width=1, line_color="#64748b")

            fig.update_layout(
                barmode="group",
                height=340,
                margin=dict(l=10, r=10, t=20, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#fbfdff",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    x=0,
                ),
                xaxis_title="",
                yaxis_title=f"Net Profit ({unit})",
            )

            fig.update_xaxes(
                categoryorder="array",
                categoryarray=MONTH_ORDER,
                showgrid=False,
            )

            fig.update_yaxes(showgrid=False)

            st.plotly_chart(
                fig,
                width="stretch",
                config={"displayModeBar": False},
            )

    with right:
        with st.container(border=True):
            st.markdown(
                '<div class="np-section-title">Overhead Composition</div>',
                unsafe_allow_html=True,
            )

            overhead_values = pd.DataFrame(
                {
                    "Expense": [
                        "Salary",
                        "Godown Rent",
                        "Overhead Expense",
                        "Claim",
                    ],
                    "Amount": [
                        current["salary"],
                        current["godown"],
                        current["overhead"],
                        current["claim"],
                    ],
                }
            )

            overhead_values = overhead_values[
                overhead_values["Amount"].abs() > 0
            ].copy()

            if overhead_values.empty:
                st.info("No overhead found for selected filters.")
            else:
                fig_overhead = px.pie(
                    overhead_values,
                    names="Expense",
                    values="Amount",
                    hole=0.62,
                )

                fig_overhead.update_traces(
                    textposition="outside",
                    textinfo="percent+label",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Amount: ₹%{value:,.2f}<br>"
                        "Share: %{percent}<extra></extra>"
                    ),
                )

                fig_overhead.update_layout(
                    height=340,
                    margin=dict(l=5, r=5, t=10, b=5),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    annotations=[
                        dict(
                            text=amount_text(
                                current["total_expense"],
                                conversion_type,
                            ),
                            x=0.5,
                            y=0.53,
                            font_size=16,
                            showarrow=False,
                        ),
                        dict(
                            text="Total Overhead",
                            x=0.5,
                            y=0.43,
                            font_size=10,
                            showarrow=False,
                        ),
                    ],
                )

                st.plotly_chart(
                    fig_overhead,
                    width="stretch",
                    config={"displayModeBar": False},
                )

    # --------------------------------------------------------
    # BRANCH PROFITABILITY
    # --------------------------------------------------------

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        top_left, top_right = st.columns([5, 1], gap="small")

        with top_left:
            st.markdown(
                '<div class="np-section-title">Branch-wise Net Profit</div>',
                unsafe_allow_html=True,
            )

        with top_right:
            top_n = st.selectbox(
                "Top branches",
                [10, 20, 30, 50],
                key="np_top_n",
                label_visibility="collapsed",
            )

        branch_summary = (
            df.groupby(
                ["BRANCHCODE", "BRANCH"],
                as_index=False,
                dropna=False,
            )
            .agg(
                Origin_PNL=("ORIGIN_PNL", "sum"),
                Destination_PNL=("DESTINATION_PNL", "sum"),
                Combined_PNL=("COMBINED_PNL", "sum"),
                Salary=("SALARY", "sum"),
                Godown_Rent=("GODOWN RENT", "sum"),
                Overhead_Expense=("OVERHEAD EXPENSE", "sum"),
                Claim=("CLAIM", "sum"),
                Total_Overhead=("TOTAL EXPENSE", "sum"),
                Net_Profit=("NET_PROFIT", "sum"),
                Total_Income=("TOTAL_INCOME", "sum"),
            )
        )

        branch_summary["Net Profit Margin %"] = 0.0
        valid_income = branch_summary["Total_Income"].ne(0)

        branch_summary.loc[valid_income, "Net Profit Margin %"] = (
            branch_summary.loc[valid_income, "Net_Profit"]
            / branch_summary.loc[valid_income, "Total_Income"]
            * 100
        )

        branch_summary = branch_summary.sort_values(
            "Net_Profit",
            ascending=False,
        ).reset_index(drop=True)

        chart_df = branch_summary.head(top_n).copy()
        chart_df["Net Profit Display"] = chart_df["Net_Profit"] / divisor

        fig_branch = px.bar(
            chart_df,
            x="Net Profit Display",
            y="BRANCH",
            orientation="h",
            labels={
                "Net Profit Display": f"Net Profit ({unit})",
                "BRANCH": "Branch",
            },
            hover_data={
                "BRANCHCODE": True,
                "Origin_PNL": ":,.2f",
                "Destination_PNL": ":,.2f",
                "Combined_PNL": ":,.2f",
                "Total_Overhead": ":,.2f",
                "Net Profit Display": ":.2f",
            },
        )

        fig_branch.update_layout(
            height=max(360, min(850, 45 * len(chart_df) + 100)),
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#fbfdff",
            yaxis=dict(autorange="reversed"),
            showlegend=False,
        )

        fig_branch.update_xaxes(showgrid=False)
        fig_branch.update_yaxes(showgrid=False)

        st.plotly_chart(
            fig_branch,
            width="stretch",
            config={"displayModeBar": False},
        )

    # --------------------------------------------------------
    # DETAIL TABLE
    # --------------------------------------------------------

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(
            '<div class="np-section-title">Branch Net Profit Detail</div>',
            unsafe_allow_html=True,
        )

        display = branch_summary.copy()

        money_columns = [
            "Origin_PNL",
            "Destination_PNL",
            "Combined_PNL",
            "Salary",
            "Godown_Rent",
            "Overhead_Expense",
            "Claim",
            "Total_Overhead",
            "Net_Profit",
            "Total_Income",
        ]

        for column in money_columns:
            display[column] = (
                pd.to_numeric(display[column], errors="coerce")
                .fillna(0.0)
                / divisor
            )

        display = display.rename(
            columns={
                "BRANCHCODE": "Branch Code",
                "BRANCH": "Branch",
                "Origin_PNL": f"Origin P&L ({unit})",
                "Destination_PNL": f"Destination P&L ({unit})",
                "Combined_PNL": f"Combined P&L ({unit})",
                "Salary": f"Salary ({unit})",
                "Godown_Rent": f"Godown Rent ({unit})",
                "Overhead_Expense": f"Overhead Expense ({unit})",
                "Claim": f"Claim ({unit})",
                "Total_Overhead": f"Total Overhead ({unit})",
                "Net_Profit": f"Net Profit ({unit})",
                "Total_Income": f"Total Income ({unit})",
            }
        )

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            column_config={
                "Net Profit Margin %": st.column_config.NumberColumn(
                    "Net Profit Margin %",
                    format="%.2f%%",
                ),
            },
        )

        csv_data = display.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            "Download Net Profit CSV",
            data=csv_data,
            file_name=f"net_profit_dashboard_{fy}.csv",
            mime="text/csv",
            key="np_download",
        )

    # --------------------------------------------------------
    # MONTH-WISE AUDIT TABLE
    # --------------------------------------------------------

    with st.expander("Monthly calculation audit"):
        audit_columns = [
            "BRANCHCODE",
            "BRANCH",
            "YEAR",
            "MONTHNO",
            "MONTH",
            "ORIGIN_PNL",
            "DESTINATION_PNL",
            "COMBINED_PNL",
            "SALARY",
            "GODOWN RENT",
            "OVERHEAD EXPENSE",
            "CLAIM",
            "TOTAL EXPENSE",
            "NET_PROFIT",
            "NET_PROFIT_MARGIN",
        ]

        audit_columns = [
            column
            for column in audit_columns
            if column in df.columns
        ]

        st.dataframe(
            df[audit_columns].sort_values(
                ["BRANCH", "YEAR", "MONTHNO"]
            ),
            width="stretch",
            hide_index=True,
        )


# Optional direct-run support.
if __name__ == "__main__":
    show_net_profit_dashboard()
