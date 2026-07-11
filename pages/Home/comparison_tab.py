import streamlit as st
import pandas as pd
import plotly.express as px
from services.data_loader import load_booking_data_pair, get_date_range


def format_cr(v):
    return f"{v / 10000000:.2f} Cr"


def growth_calc(current, previous):
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100


def growth_label(growth):
    arrow = "▲" if growth >= 0 else "▼"
    return f"{arrow} {abs(growth):.2f}%"

def apply_location_filters(df, key_prefix=""):

    data_scope = st.session_state.get("data_scope", {})

    # Get assigned rights
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    # Branch right -> derive Circle & Zone
    if locked_branch:
        row = df[df["branch"] == locked_branch]
        if not row.empty:
            locked_circle = row["circle"].iloc[0]
            locked_zone = row["zone"].iloc[0]

    # Circle right -> derive Zone
    elif locked_circle:
        row = df[df["circle"] == locked_circle]
        if not row.empty:
            locked_zone = row["zone"].iloc[0]

    c1, c2, c3 = st.columns(3)

    # ---------------- Zone ----------------
    with c1:
        if locked_zone:
            zone = locked_zone
            st.selectbox(
                "Zone",
                [zone],
                disabled=True,
                key=f"{key_prefix}_zone"
            )
        else:
            zone = st.selectbox(
                "Zone",
                ["All"] + sorted(df["zone"].dropna().unique().tolist()),
                key=f"{key_prefix}_zone"
            )

    if zone != "All":
        df = df[df["zone"] == zone]

    # ---------------- Circle ----------------
    with c2:
        if locked_circle:
            circle = locked_circle
            st.selectbox(
                "Circle",
                [circle],
                disabled=True,
                key=f"{key_prefix}_circle"
            )
        else:
            circle = st.selectbox(
                "Circle",
                ["All"] + sorted(df["circle"].dropna().unique().tolist()),
                key=f"{key_prefix}_circle"
            )

    if circle != "All":
        df = df[df["circle"] == circle]

    # ---------------- Branch ----------------
    with c3:
        if locked_branch:
            branch = locked_branch
            st.selectbox(
                "Branch",
                [branch],
                disabled=True,
                key=f"{key_prefix}_branch"
            )
        else:
            branch = st.selectbox(
                "Branch",
                ["All"] + sorted(df["branch"].dropna().unique().tolist()),
                key=f"{key_prefix}_branch"
            )

    if branch != "All":
        df = df[df["branch"] == branch]

    return df

def show_comparison():

    st.subheader("Comparison")

    fy_options = [
        "2026-2027",
        "2025-2026",
        "2024-2025",
        "2023-2024",
        "2022-2023",
        "2021-2022",
        "2020-2021",
    ]

    comparison_type = st.radio(
        "Comparison Type",
        ["Month YoY", "Quarter YoY"],
        horizontal=True
    )
    if "comparison_run" not in st.session_state:
        st.session_state["comparison_run"] = False

    # =========================
    # YoY COMPARISON
    # =========================

    if comparison_type == "Month YoY":

        with st.form("month_yoy_form"):

            col1, col2, col3 = st.columns(3)

            with col1:
                view_type = st.selectbox(
                    "View Type",
                    ["Origin", "Destination"],
                    key="month_view_type"
                )

            with col2:
                fy1 = st.selectbox(
                    "Financial Year 1",
                    fy_options,
                    index=1
                )

            with col3:
                fy2 = st.selectbox(
                    "Financial Year 2",
                    fy_options,
                    index=2
                )

            compare = st.form_submit_button(
                "Run Month YoY Comparison",
                use_container_width=True
            )

        if compare:
            st.session_state["comparison_run"] = True
            st.session_state["month_view_type_value"] = view_type
            st.session_state["month_fy1"] = fy1
            st.session_state["month_fy2"] = fy2

        if not st.session_state.get("comparison_run", False):
            st.info("Select filters and click Run Month YoY Comparison.")
            return

        view_type = st.session_state["month_view_type_value"]
        fy1 = st.session_state["month_fy1"]
        fy2 = st.session_state["month_fy2"]

        
        if fy1 == fy2:
            st.warning("Please select two different financial years.")
            return

    
        start1, end1 = get_date_range(fy1)
        start2, end2 = get_date_range(fy2)

        # Load both selected financial years together in parallel.
        # This uses the same paired-fetch logic as the Overview page.
        with st.spinner("Loading YoY comparison data..."):
            df1, df2 = load_booking_data_pair(
                start1,
                end1,
                start2,
                end2,
                view_type.lower()
            )

            df1["FY"] = fy1
            df2["FY"] = fy2

            df = pd.concat([df1, df2], ignore_index=True)
        st.markdown("##### Location Filters")
        df = apply_location_filters(df, f"month_yoy_{view_type.lower()}")
        val1 = df[df["FY"] == fy1]["REVENUE"].sum()
        val2 = df[df["FY"] == fy2]["REVENUE"].sum()

        growth = growth_calc(val1, val2)
        color = "#198754" if growth >= 0 else "#dc3545"

        st.markdown(
            f"""
            <div style="
                background:#ffffff;
                padding:18px;
                border-radius:14px;
                box-shadow:0 2px 8px rgba(0,0,0,0.12);
                margin-top:10px;
                margin-bottom:20px;
                text-align:center;
            ">
                <div style="font-size:20px;font-weight:700;">
                    {fy1} vs {fy2}
                </div>
                <div style="font-size:34px;font-weight:800;color:{color};margin-top:8px;">
                    {growth_label(growth)}
                </div>
                <div style="font-size:16px;color:#6c757d;margin-top:6px;">
                    {format_cr(val1)} vs {format_cr(val2)}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        month_map = {
            1: "Apr", 2: "May", 3: "Jun", 4: "Jul",
            5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov",
            9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"
        }

        month_order = [
            "Apr", "May", "Jun", "Jul",
            "Aug", "Sep", "Oct", "Nov",
            "Dec", "Jan", "Feb", "Mar"
        ]

        month_df = (
            df.groupby(["FY", "FIN_MONTH"])["REVENUE"]
            .sum()
            .reset_index()
        )

        rows = []

        for m in range(1, 13):
            v1 = month_df[
                (month_df["FY"] == fy1) &
                (month_df["FIN_MONTH"] == m)
            ]["REVENUE"].sum()

            v2 = month_df[
                (month_df["FY"] == fy2) &
                (month_df["FIN_MONTH"] == m)
            ]["REVENUE"].sum()

            g = growth_calc(v1, v2)

            rows.append({
                "Month": month_map[m],
                fy1: round(v1 / 10000000, 2),
                fy2: round(v2 / 10000000, 2),
                "% Change": growth_label(g)
            })

        comparison_df = pd.DataFrame(rows)

        chart_df = comparison_df.melt(
            id_vars="Month",
            value_vars=[fy1, fy2],
            var_name="Financial Year",
            value_name="Revenue Cr"
        )

        chart_df["Month"] = pd.Categorical(
            chart_df["Month"],
            categories=month_order,
            ordered=True
        )

        chart_df = chart_df.sort_values("Month")

        st.markdown("##### Month-wise Revenue Comparison")

        fig = px.bar(
            chart_df,
            x="Month",
            y="Revenue Cr",
            color="Financial Year",
            barmode="group",
            text="Revenue Cr",
            height=320
        )

        fig.update_traces(
            texttemplate="%{text:.2f}",
            textposition="outside"
        )

        fig.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="Revenue Cr",
            xaxis_title="Month",
            legend_title=""
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Month-wise Comparison Table")

        def color_change(val):
            if "▲" in str(val):
                return "color: green; font-weight: bold"
            if "▼" in str(val):
                return "color: red; font-weight: bold"
            return ""

        styled_df = comparison_df.style.map(
            color_change,
            subset=["% Change"]
        ).format({
            fy1: "{:.2f}",
            fy2: "{:.2f}"
        })

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=460
        )

    
    # =========================
    # QoQ COMPARISON
    # =========================

    elif comparison_type == "Quarter YoY":

        with st.form("quarter_yoy_form"):

            col1, col2, col3 = st.columns(3)

            with col1:
                view_type = st.selectbox(
                    "View Type",
                    ["Origin", "Destination"],
                    key="quarter_view_type"
                )

            with col2:
                fy1 = st.selectbox(
                    "Financial Year 1",
                    fy_options,
                    index=1,
                    key="q_fy1"
                )

            with col3:
                fy2 = st.selectbox(
                    "Financial Year 2",
                    fy_options,
                    index=2,
                    key="q_fy2"
                )

            compare = st.form_submit_button(
                "Run Quarter YoY Comparison",
                use_container_width=True
            )

        if compare:
            st.session_state["quarter_run"] = True
            st.session_state["quarter_view_type_value"] = view_type
            st.session_state["quarter_fy1"] = fy1
            st.session_state["quarter_fy2"] = fy2

        if not st.session_state.get("quarter_run", False):
            st.info("Select filters and click Run Quarter YoY Comparison.")
            return

        view_type = st.session_state["quarter_view_type_value"]
        fy1 = st.session_state["quarter_fy1"]
        fy2 = st.session_state["quarter_fy2"]
            
        if fy1 == fy2:
            st.warning("Please select two different financial years.")
            return

 
        start1, end1 = get_date_range(fy1)
        start2, end2 = get_date_range(fy2)

        # Load both selected financial years together in parallel.
        # This uses the same paired-fetch logic as the Overview page.
        with st.spinner("Loading quarter comparison data..."):
            df1, df2 = load_booking_data_pair(
                start1,
                end1,
                start2,
                end2,
                view_type.lower()
            )

            df1["FY"] = fy1
            df2["FY"] = fy2

            df = pd.concat([df1, df2], ignore_index=True)
            
        st.markdown("##### Location Filters")
        df = apply_location_filters(df, f"quater_yoy_{view_type.lower()}")

        def get_quarter(fin_month):
            if fin_month in [1, 2, 3]:
                return "Q1"
            elif fin_month in [4, 5, 6]:
                return "Q2"
            elif fin_month in [7, 8, 9]:
                return "Q3"
            else:
                return "Q4"

        df["Quarter"] = df["FIN_MONTH"].apply(get_quarter)

        quarter_order = ["Q1", "Q2", "Q3", "Q4"]

        quarter_df = (
            df.groupby(["FY", "Quarter"])["REVENUE"]
            .sum()
            .reset_index()
        )

        result_rows = []

        for q in quarter_order:
            v1 = quarter_df[
                (quarter_df["FY"] == fy1) &
                (quarter_df["Quarter"] == q)
            ]["REVENUE"].sum()

            v2 = quarter_df[
                (quarter_df["FY"] == fy2) &
                (quarter_df["Quarter"] == q)
            ]["REVENUE"].sum()

            growth = growth_calc(v1, v2)

            result_rows.append({
                "Quarter": q,
                fy1: round(v1 / 10000000, 2),
                fy2: round(v2 / 10000000, 2),
                "% Change": growth_label(growth)
            })

        comparison_df = pd.DataFrame(result_rows)

        chart_df = comparison_df.melt(
            id_vars="Quarter",
            value_vars=[fy1, fy2],
            var_name="Financial Year",
            value_name="Revenue Cr"
        )

        chart_df["Quarter"] = pd.Categorical(
            chart_df["Quarter"],
            categories=quarter_order,
            ordered=True
        )

        chart_df = chart_df.sort_values("Quarter")

        total1 = comparison_df[fy1].sum()
        total2 = comparison_df[fy2].sum()
        total_growth = growth_calc(total1, total2)
        color = "#198754" if total_growth >= 0 else "#dc3545"

        st.markdown(
            f"""
            <div style="
                background:#ffffff;
                padding:18px;
                border-radius:14px;
                box-shadow:0 2px 8px rgba(0,0,0,0.12);
                margin-top:10px;
                margin-bottom:20px;
                text-align:center;
            ">
                <div style="font-size:20px;font-weight:700;">
                    Quarter YoY: {fy1} vs {fy2}
                </div>
                <div style="font-size:34px;font-weight:800;color:{color};margin-top:8px;">
                    {growth_label(total_growth)}
                </div>
                <div style="font-size:16px;color:#6c757d;margin-top:6px;">
                    {total1:.2f} Cr vs {total2:.2f} Cr
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("##### Quarter-wise YoY Revenue Comparison")

        fig = px.bar(
            chart_df,
            x="Quarter",
            y="Revenue Cr",
            color="Financial Year",
            barmode="group",
            text="Revenue Cr",
            height=320
        )

        fig.update_traces(
            texttemplate="%{text:.2f}",
            textposition="outside"
        )

        fig.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="Revenue Cr",
            xaxis_title="Quarter",
            legend_title=""
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Quarter-wise YoY Comparison Table")

        def color_change(val):
            if "▲" in str(val):
                return "color: green; font-weight: bold"
            if "▼" in str(val):
                return "color: red; font-weight: bold"
            return ""

        styled_df = comparison_df.style.map(
            color_change,
            subset=["% Change"]
        ).format({
            fy1: "{:.2f}",
            fy2: "{:.2f}"
        })

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=220
        )