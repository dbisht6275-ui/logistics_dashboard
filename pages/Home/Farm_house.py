import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO


def show_farmhouse():

    # ---------------------------------------------------------
    # SESSION STATE
    # ---------------------------------------------------------
    if "farmhouse_booking_cost" not in st.session_state:
        st.session_state.farmhouse_booking_cost = 15000.0

    if "farmhouse_members" not in st.session_state:
        st.session_state.farmhouse_members = pd.DataFrame(
            columns=["Member Name", "Advance Credit"]
        )

    if "farmhouse_expenses" not in st.session_state:
        st.session_state.farmhouse_expenses = pd.DataFrame(
            columns=[
                "Date",
                "Expense Category",
                "Description",
                "Amount",
                "Paid By",
                "Notes",
            ]
        )

    # ---------------------------------------------------------
    # FUNCTIONS
    # ---------------------------------------------------------
    def calculate_member_data():

        df = st.session_state.farmhouse_members.copy()

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "Member Name",
                    "Per Member Share",
                    "Advance Credit",
                    "Pending Balance",
                    "Payment Status",
                ]
            )

        total_members = len(df)

        per_member_share = (
            st.session_state.farmhouse_booking_cost / total_members
            if total_members > 0
            else 0
        )

        df["Advance Credit"] = pd.to_numeric(
            df["Advance Credit"],
            errors="coerce",
        ).fillna(0)

        df["Per Member Share"] = per_member_share

        df["Pending Balance"] = (
            df["Per Member Share"] - df["Advance Credit"]
        ).clip(lower=0)

        def get_status(row):

            if row["Pending Balance"] <= 0:
                return "Paid"

            elif row["Advance Credit"] > 0:
                return "Partial"

            return "Pending"

        df["Payment Status"] = df.apply(
            get_status,
            axis=1,
        )

        return df[
            [
                "Member Name",
                "Per Member Share",
                "Advance Credit",
                "Pending Balance",
                "Payment Status",
            ]
        ]

    def rupee(value):
        return f"₹{float(value):,.2f}"

    def create_excel():

        member_df = calculate_member_data()
        expense_df = st.session_state.farmhouse_expenses.copy()

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl",
        ) as writer:

            member_df.to_excel(
                writer,
                sheet_name="Member Sharing",
                index=False,
            )

            expense_df.to_excel(
                writer,
                sheet_name="Expense Tracker",
                index=False,
            )

        output.seek(0)

        return output

    # ---------------------------------------------------------
    # PAGE HEADER
    # ---------------------------------------------------------
    st.markdown(
        """
        <div style="
            padding:15px 18px;
            background:linear-gradient(90deg,#0f2f63,#1761d2);
            border-radius:12px;
            margin-bottom:18px;
        ">
            <div style="
                color:white;
                font-size:26px;
                font-weight:800;
            ">
                🏡 Farmhouse Trip Manager
            </div>

            <div style="
                color:#dbeafe;
                font-size:13px;
                margin-top:4px;
            ">
                Manage member contribution, advance collection and trip expenses
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # CURRENT CALCULATIONS
    # ---------------------------------------------------------
    member_data = calculate_member_data()

    total_members = len(member_data)

    total_advance = (
        member_data["Advance Credit"].sum()
        if not member_data.empty
        else 0
    )

    total_pending = (
        member_data["Pending Balance"].sum()
        if not member_data.empty
        else 0
    )

    expense_df = st.session_state.farmhouse_expenses.copy()

    if not expense_df.empty:

        expense_df["Amount"] = pd.to_numeric(
            expense_df["Amount"],
            errors="coerce",
        ).fillna(0)

        total_expense = expense_df["Amount"].sum()

    else:
        total_expense = 0

    total_spent = (
        st.session_state.farmhouse_booking_cost
        + total_expense
    )

    # ---------------------------------------------------------
    # KPI SUMMARY
    # ---------------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Farmhouse Cost",
        rupee(st.session_state.farmhouse_booking_cost),
    )

    c2.metric(
        "Members",
        total_members,
    )

    c3.metric(
        "Advance Collected",
        rupee(total_advance),
    )

    c4.metric(
        "Pending",
        rupee(total_pending),
    )

    c5.metric(
        "Other Expenses",
        rupee(total_expense),
    )

    st.divider()

    # ---------------------------------------------------------
    # TABS
    # ---------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(
        [
            "👥 Member Sharing",
            "💳 Expense Tracker",
            "📊 Summary",
        ]
    )

    # =========================================================
    # TAB 1
    # =========================================================
    with tab1:

        st.subheader(
            "Farmhouse Booking & Member Sharing"
        )

        col1, col2 = st.columns([1, 2])

        with col1:

            booking_cost = st.number_input(
                "Total Farmhouse Booking Cost",
                min_value=0.0,
                value=float(
                    st.session_state.farmhouse_booking_cost
                ),
                step=500.0,
                key="farmhouse_booking_cost_input",
            )

            if (
                booking_cost
                != st.session_state.farmhouse_booking_cost
            ):

                st.session_state.farmhouse_booking_cost = booking_cost

        with col2:

            if total_members > 0:

                share = (
                    st.session_state.farmhouse_booking_cost
                    / total_members
                )

                st.success(
                    f"Per Member Share: {rupee(share)}"
                )

            else:

                st.info(
                    "Add members to calculate per member share."
                )

        st.markdown("### Add Member")

        m1, m2, m3 = st.columns([2, 1, 1])

        with m1:

            member_name = st.text_input(
                "Member Name",
                key="farmhouse_new_member",
            )

        with m2:

            advance_credit = st.number_input(
                "Advance Credit",
                min_value=0.0,
                value=0.0,
                step=500.0,
                key="farmhouse_new_advance",
            )

        with m3:

            st.write("")
            st.write("")

            if st.button(
                "➕ Add Member",
                use_container_width=True,
                key="farmhouse_add_member",
            ):

                member_name_clean = member_name.strip()

                if not member_name_clean:

                    st.warning(
                        "Please enter member name."
                    )

                else:

                    existing_names = (
                        st.session_state.farmhouse_members[
                            "Member Name"
                        ]
                        .astype(str)
                        .str.strip()
                        .str.lower()
                        .tolist()
                    )

                    if (
                        member_name_clean.lower()
                        in existing_names
                    ):

                        st.warning(
                            "Member already exists."
                        )

                    else:

                        new_row = pd.DataFrame(
                            {
                                "Member Name": [
                                    member_name_clean
                                ],
                                "Advance Credit": [
                                    advance_credit
                                ],
                            }
                        )

                        st.session_state.farmhouse_members = (
                            pd.concat(
                                [
                                    st.session_state.farmhouse_members,
                                    new_row,
                                ],
                                ignore_index=True,
                            )
                        )

                        st.rerun()

        st.markdown("### Member List")

        member_data = calculate_member_data()

        if member_data.empty:

            st.info(
                "No members added yet."
            )

        else:

            display_df = member_data.copy()

            for col in [
                "Per Member Share",
                "Advance Credit",
                "Pending Balance",
            ]:

                display_df[col] = display_df[col].map(
                    lambda x: f"₹{x:,.2f}"
                )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown(
                "### Update Member Advance"
            )

            u1, u2, u3 = st.columns([2, 1, 1])

            member_list = (
                st.session_state.farmhouse_members[
                    "Member Name"
                ].tolist()
            )

            with u1:

                selected_member = st.selectbox(
                    "Select Member",
                    member_list,
                    key="farmhouse_update_member",
                )

            current_advance = float(
                st.session_state.farmhouse_members.loc[
                    st.session_state.farmhouse_members[
                        "Member Name"
                    ]
                    == selected_member,
                    "Advance Credit",
                ].iloc[0]
            )

            with u2:

                updated_advance = st.number_input(
                    "Advance Amount",
                    min_value=0.0,
                    value=current_advance,
                    step=500.0,
                    key=f"farmhouse_update_advance_{selected_member}",
                )

            with u3:

                st.write("")
                st.write("")

                if st.button(
                    "Update",
                    use_container_width=True,
                    key="farmhouse_update_button",
                ):

                    st.session_state.farmhouse_members.loc[
                        st.session_state.farmhouse_members[
                            "Member Name"
                        ]
                        == selected_member,
                        "Advance Credit",
                    ] = updated_advance

                    st.rerun()

            st.markdown("### Remove Member")

            d1, d2 = st.columns([3, 1])

            with d1:

                delete_member = st.selectbox(
                    "Select Member",
                    member_list,
                    key="farmhouse_delete_member",
                )

            with d2:

                st.write("")
                st.write("")

                if st.button(
                    "🗑 Remove",
                    use_container_width=True,
                    key="farmhouse_delete_button",
                ):

                    st.session_state.farmhouse_members = (
                        st.session_state.farmhouse_members[
                            st.session_state.farmhouse_members[
                                "Member Name"
                            ]
                            != delete_member
                        ].reset_index(drop=True)
                    )

                    st.rerun()

    # =========================================================
    # TAB 2
    # =========================================================
    with tab2:

        st.subheader(
            "Expense Tracker"
        )

        categories = [
            "Food",
            "Beverages",
            "Snacks",
            "Travel",
            "Decoration",
            "Other",
        ]

        with st.form(
            "farmhouse_expense_form",
            clear_on_submit=True,
        ):

            e1, e2, e3 = st.columns(3)

            with e1:

                expense_date = st.date_input(
                    "Date",
                    value=date.today(),
                )

            with e2:

                category = st.selectbox(
                    "Expense Category",
                    categories,
                )

            with e3:

                amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    step=100.0,
                )

            e4, e5 = st.columns(2)

            with e4:

                description = st.text_input(
                    "Description"
                )

            with e5:

                members = (
                    st.session_state.farmhouse_members[
                        "Member Name"
                    ].tolist()
                )

                paid_by = st.selectbox(
                    "Paid By",
                    members
                    if members
                    else ["Not Assigned"],
                )

            notes = st.text_area(
                "Notes"
            )

            submitted = st.form_submit_button(
                "➕ Add Expense",
                use_container_width=True,
            )

            if submitted:

                if amount <= 0:

                    st.warning(
                        "Amount must be greater than zero."
                    )

                else:

                    new_expense = pd.DataFrame(
                        {
                            "Date": [expense_date],
                            "Expense Category": [
                                category
                            ],
                            "Description": [
                                description
                            ],
                            "Amount": [amount],
                            "Paid By": [paid_by],
                            "Notes": [notes],
                        }
                    )

                    st.session_state.farmhouse_expenses = (
                        pd.concat(
                            [
                                st.session_state.farmhouse_expenses,
                                new_expense,
                            ],
                            ignore_index=True,
                        )
                    )

                    st.rerun()

        st.markdown(
            "### Expense Register"
        )

        expenses = (
            st.session_state.farmhouse_expenses.copy()
        )

        if expenses.empty:

            st.info(
                "No expenses added yet."
            )

        else:

            expenses["Amount"] = pd.to_numeric(
                expenses["Amount"],
                errors="coerce",
            ).fillna(0)

            display_expenses = expenses.copy()

            display_expenses["Amount"] = (
                display_expenses["Amount"].map(
                    lambda x: f"₹{x:,.2f}"
                )
            )

            st.dataframe(
                display_expenses,
                use_container_width=True,
                hide_index=True,
            )

            st.markdown(
                "### Delete Expense"
            )

            expense_index = st.selectbox(
                "Select Expense",
                range(len(expenses)),
                format_func=lambda i: (
                    f"{expenses.iloc[i]['Date']} | "
                    f"{expenses.iloc[i]['Expense Category']} | "
                    f"{expenses.iloc[i]['Description']} | "
                    f"₹{float(expenses.iloc[i]['Amount']):,.2f}"
                ),
                key="farmhouse_expense_delete_select",
            )

            if st.button(
                "🗑 Delete Expense",
                key="farmhouse_delete_expense",
            ):

                st.session_state.farmhouse_expenses = (
                    st.session_state.farmhouse_expenses.drop(
                        index=expense_index
                    ).reset_index(drop=True)
                )

                st.rerun()

    # =========================================================
    # TAB 3
    # =========================================================
    with tab3:

        st.subheader(
            "Farmhouse Trip Summary"
        )

        member_data = calculate_member_data()

        expenses = (
            st.session_state.farmhouse_expenses.copy()
        )

        if not expenses.empty:

            expenses["Amount"] = pd.to_numeric(
                expenses["Amount"],
                errors="coerce",
            ).fillna(0)

            total_expenses = expenses[
                "Amount"
            ].sum()

        else:
            total_expenses = 0

        total_advance = (
            member_data["Advance Credit"].sum()
            if not member_data.empty
            else 0
        )

        total_pending = (
            member_data["Pending Balance"].sum()
            if not member_data.empty
            else 0
        )

        total_amount_spent = (
            st.session_state.farmhouse_booking_cost
            + total_expenses
        )

        s1, s2, s3 = st.columns(3)

        s1.metric(
            "Farmhouse Cost",
            rupee(
                st.session_state.farmhouse_booking_cost
            ),
        )

        s2.metric(
            "Other Expenses",
            rupee(total_expenses),
        )

        s3.metric(
            "Total Amount Spent",
            rupee(total_amount_spent),
        )

        s4, s5, s6 = st.columns(3)

        s4.metric(
            "Advance Collected",
            rupee(total_advance),
        )

        s5.metric(
            "Pending Amount",
            rupee(total_pending),
        )

        s6.metric(
            "Total Members",
            len(member_data),
        )

        st.divider()

        left, right = st.columns(2)

        with left:

            st.markdown(
                "### Category-wise Expenses"
            )

            if not expenses.empty:

                category_summary = (
                    expenses.groupby(
                        "Expense Category",
                        as_index=False,
                    )["Amount"].sum()
                )

                st.dataframe(
                    category_summary,
                    use_container_width=True,
                    hide_index=True,
                )

                st.bar_chart(
                    category_summary.set_index(
                        "Expense Category"
                    )
                )

            else:

                st.info(
                    "No expense data."
                )

        with right:

            st.markdown(
                "### Member-wise Amount Paid"
            )

            if not expenses.empty:

                member_summary = (
                    expenses.groupby(
                        "Paid By",
                        as_index=False,
                    )["Amount"].sum()
                )

                st.dataframe(
                    member_summary,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "No expense data."
                )

        st.divider()

        if not member_data.empty:

            st.markdown(
                "### Payment Status"
            )

            status_summary = (
                member_data[
                    "Payment Status"
                ]
                .value_counts()
                .reset_index()
            )

            status_summary.columns = [
                "Payment Status",
                "Members",
            ]

            st.dataframe(
                status_summary,
                use_container_width=True,
                hide_index=True,
            )

    # ---------------------------------------------------------
    # EXPORT
    # ---------------------------------------------------------
    st.divider()

    excel_data = create_excel()

    st.download_button(
        "📥 Download Excel Report",
        data=excel_data,
        file_name="Farmhouse_Trip_Report.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
        key="farmhouse_excel_download",
    )
