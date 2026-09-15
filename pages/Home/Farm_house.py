import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

st.set_page_config(
    page_title="Farmhouse Trip Manager",
    page_icon="🏡",
    layout="wide"
)

# ---------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------

if "booking_cost" not in st.session_state:
    st.session_state.booking_cost = 15000.0

if "members" not in st.session_state:
    st.session_state.members = pd.DataFrame(
        columns=[
            "Member Name",
            "Advance Credit"
        ]
    )

if "expenses" not in st.session_state:
    st.session_state.expenses = pd.DataFrame(
        columns=[
            "Date",
            "Expense Category",
            "Description",
            "Amount",
            "Paid By",
            "Notes"
        ]
    )


# ---------------------------------------------------------
# FUNCTIONS
# ---------------------------------------------------------

def calculate_member_data():

    df = st.session_state.members.copy()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Member Name",
                "Per Member Share",
                "Advance Credit",
                "Pending Balance",
                "Payment Status"
            ]
        )

    total_members = len(df)

    per_member_share = (
        st.session_state.booking_cost / total_members
        if total_members > 0
        else 0
    )

    df["Per Member Share"] = per_member_share

    df["Advance Credit"] = pd.to_numeric(
        df["Advance Credit"],
        errors="coerce"
    ).fillna(0)

    df["Pending Balance"] = (
        df["Per Member Share"] - df["Advance Credit"]
    )

    df["Pending Balance"] = df["Pending Balance"].clip(lower=0)

    def payment_status(row):

        if row["Pending Balance"] <= 0:
            return "Paid"

        elif (
            row["Advance Credit"] > 0
            and row["Pending Balance"] > 0
        ):
            return "Partial"

        else:
            return "Pending"

    df["Payment Status"] = df.apply(
        payment_status,
        axis=1
    )

    return df[
        [
            "Member Name",
            "Per Member Share",
            "Advance Credit",
            "Pending Balance",
            "Payment Status"
        ]
    ]


def rupee(value):
    return f"₹{value:,.2f}"


def create_excel():

    member_df = calculate_member_data()
    expense_df = st.session_state.expenses.copy()

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        member_df.to_excel(
            writer,
            sheet_name="Member Sharing",
            index=False
        )

        expense_df.to_excel(
            writer,
            sheet_name="Expense Tracker",
            index=False
        )

    output.seek(0)

    return output


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.title("🏡 Farmhouse Trip Manager")

st.caption(
    "Manage member sharing, advance collection and trip expenses."
)

# ---------------------------------------------------------
# TOP SUMMARY
# ---------------------------------------------------------

member_calculated = calculate_member_data()

total_members = len(member_calculated)

total_advance = (
    member_calculated["Advance Credit"].sum()
    if not member_calculated.empty
    else 0
)

total_pending = (
    member_calculated["Pending Balance"].sum()
    if not member_calculated.empty
    else 0
)

total_expense = (
    pd.to_numeric(
        st.session_state.expenses["Amount"],
        errors="coerce"
    ).fillna(0).sum()
    if not st.session_state.expenses.empty
    else 0
)

total_spent = (
    st.session_state.booking_cost
    + total_expense
)

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Farmhouse Cost",
    rupee(st.session_state.booking_cost)
)

c2.metric(
    "Total Members",
    total_members
)

c3.metric(
    "Advance Collected",
    rupee(total_advance)
)

c4.metric(
    "Pending Amount",
    rupee(total_pending)
)

c5.metric(
    "Total Expenses",
    rupee(total_expense)
)

st.divider()


# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------

tab1, tab2, tab3 = st.tabs(
    [
        "👥 Member Sharing",
        "💳 Expense Tracker",
        "📊 Dashboard"
    ]
)


# =========================================================
# TAB 1 - MEMBER SHARING
# =========================================================

with tab1:

    st.subheader(
        "Farmhouse Booking & Member Sharing"
    )

    cost_col1, cost_col2 = st.columns(
        [1, 2]
    )

    with cost_col1:

        booking_cost = st.number_input(
            "Total Farmhouse Booking Cost",
            min_value=0.0,
            value=float(
                st.session_state.booking_cost
            ),
            step=500.0,
            format="%.2f"
        )

        st.session_state.booking_cost = booking_cost

    with cost_col2:

        if total_members > 0:

            per_member = (
                st.session_state.booking_cost
                / total_members
            )

            st.info(
                f"Per Member Share: "
                f"₹{per_member:,.2f}"
            )

        else:

            st.info(
                "Add members to calculate "
                "per-member share."
            )

    st.markdown("### Add Member")

    col1, col2, col3 = st.columns(
        [2, 1, 1]
    )

    with col1:

        new_member = st.text_input(
            "Member Name"
        )

    with col2:

        advance = st.number_input(
            "Advance Credit",
            min_value=0.0,
            value=0.0,
            step=500.0
        )

    with col3:

        st.write("")
        st.write("")

        if st.button(
            "➕ Add Member",
            use_container_width=True
        ):

            if new_member.strip():

                existing_names = (
                    st.session_state.members[
                        "Member Name"
                    ]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .tolist()
                )

                if (
                    new_member.strip().lower()
                    in existing_names
                ):

                    st.warning(
                        "This member already exists."
                    )

                else:

                    new_row = pd.DataFrame(
                        {
                            "Member Name": [
                                new_member.strip()
                            ],
                            "Advance Credit": [
                                advance
                            ]
                        }
                    )

                    st.session_state.members = (
                        pd.concat(
                            [
                                st.session_state.members,
                                new_row
                            ],
                            ignore_index=True
                        )
                    )

                    st.rerun()

            else:

                st.warning(
                    "Enter member name."
                )

    st.markdown("### Member List")

    member_calculated = calculate_member_data()

    if member_calculated.empty:

        st.info(
            "No members added yet."
        )

    else:

        display_df = member_calculated.copy()

        display_df[
            "Per Member Share"
        ] = display_df[
            "Per Member Share"
        ].map(
            lambda x: f"₹{x:,.2f}"
        )

        display_df[
            "Advance Credit"
        ] = display_df[
            "Advance Credit"
        ].map(
            lambda x: f"₹{x:,.2f}"
        )

        display_df[
            "Pending Balance"
        ] = display_df[
            "Pending Balance"
        ].map(
            lambda x: f"₹{x:,.2f}"
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown(
            "### Update Member Advance"
        )

        u1, u2, u3 = st.columns(
            [2, 1, 1]
        )

        with u1:

            selected_member = st.selectbox(
                "Select Member",
                st.session_state.members[
                    "Member Name"
                ].tolist()
            )

        current_advance = float(
            st.session_state.members.loc[
                st.session_state.members[
                    "Member Name"
                ] == selected_member,
                "Advance Credit"
            ].iloc[0]
        )

        with u2:

            updated_advance = (
                st.number_input(
                    "New Advance",
                    min_value=0.0,
                    value=current_advance,
                    step=500.0
                )
            )

        with u3:

            st.write("")
            st.write("")

            if st.button(
                "Update Advance",
                use_container_width=True
            ):

                st.session_state.members.loc[
                    st.session_state.members[
                        "Member Name"
                    ] == selected_member,
                    "Advance Credit"
                ] = updated_advance

                st.rerun()

        st.markdown(
            "### Remove Member"
        )

        r1, r2 = st.columns(
            [3, 1]
        )

        with r1:

            delete_member = st.selectbox(
                "Member to Remove",
                st.session_state.members[
                    "Member Name"
                ].tolist(),
                key="delete_member"
            )

        with r2:

            st.write("")
            st.write("")

            if st.button(
                "🗑 Remove",
                type="secondary",
                use_container_width=True
            ):

                st.session_state.members = (
                    st.session_state.members[
                        st.session_state.members[
                            "Member Name"
                        ] != delete_member
                    ].reset_index(drop=True)
                )

                st.rerun()

        st.markdown("### Member Totals")

        t1, t2, t3 = st.columns(3)

        t1.metric(
            "Total Member Share",
            rupee(
                member_calculated[
                    "Per Member Share"
                ].sum()
            )
        )

        t2.metric(
            "Total Advance",
            rupee(
                member_calculated[
                    "Advance Credit"
                ].sum()
            )
        )

        t3.metric(
            "Total Pending",
            rupee(
                member_calculated[
                    "Pending Balance"
                ].sum()
            )
        )


# =========================================================
# TAB 2 - EXPENSE TRACKER
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
        "Other"
    ]

    with st.form(
        "expense_form",
        clear_on_submit=True
    ):

        col1, col2, col3 = st.columns(3)

        with col1:

            expense_date = st.date_input(
                "Date",
                value=date.today()
            )

        with col2:

            expense_category = st.selectbox(
                "Expense Category",
                categories
            )

        with col3:

            amount = st.number_input(
                "Amount",
                min_value=0.0,
                step=100.0
            )

        col4, col5 = st.columns(2)

        with col4:

            description = st.text_input(
                "Description"
            )

        with col5:

            member_names = (
                st.session_state.members[
                    "Member Name"
                ].tolist()
            )

            paid_by_options = (
                member_names
                if member_names
                else ["Not Assigned"]
            )

            paid_by = st.selectbox(
                "Paid By",
                paid_by_options
            )

        notes = st.text_area(
            "Notes"
        )

        submit_expense = st.form_submit_button(
            "➕ Add Expense",
            use_container_width=True
        )

        if submit_expense:

            if amount <= 0:

                st.warning(
                    "Expense amount must "
                    "be greater than zero."
                )

            else:

                new_expense = pd.DataFrame(
                    {
                        "Date": [
                            expense_date
                        ],
                        "Expense Category": [
                            expense_category
                        ],
                        "Description": [
                            description
                        ],
                        "Amount": [
                            amount
                        ],
                        "Paid By": [
                            paid_by
                        ],
                        "Notes": [
                            notes
                        ]
                    }
                )

                st.session_state.expenses = (
                    pd.concat(
                        [
                            st.session_state.expenses,
                            new_expense
                        ],
                        ignore_index=True
                    )
                )

                st.rerun()

    st.markdown("### Expense Register")

    if st.session_state.expenses.empty:

        st.info(
            "No expenses added yet."
        )

    else:

        expense_display = (
            st.session_state.expenses.copy()
        )

        expense_display[
            "Amount"
        ] = pd.to_numeric(
            expense_display[
                "Amount"
            ],
            errors="coerce"
        ).fillna(0)

        expense_display[
            "Amount"
        ] = expense_display[
            "Amount"
        ].map(
            lambda x: f"₹{x:,.2f}"
        )

        st.dataframe(
            expense_display,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Remove Expense")

        expense_index = st.selectbox(
            "Select Expense",
            options=range(
                len(
                    st.session_state.expenses
                )
            ),
            format_func=lambda i:
                f"{st.session_state.expenses.iloc[i]['Date']} | "
                f"{st.session_state.expenses.iloc[i]['Expense Category']} | "
                f"{st.session_state.expenses.iloc[i]['Description']} | "
                f"₹{float(st.session_state.expenses.iloc[i]['Amount']):,.2f}"
        )

        if st.button(
            "🗑 Delete Expense"
        ):

            st.session_state.expenses = (
                st.session_state.expenses.drop(
                    index=expense_index
                ).reset_index(drop=True)
            )

            st.rerun()


# =========================================================
# TAB 3 - DASHBOARD
# =========================================================

with tab3:

    st.subheader(
        "Farmhouse Trip Summary"
    )

    member_calculated = calculate_member_data()

    total_advance = (
        member_calculated[
            "Advance Credit"
        ].sum()
        if not member_calculated.empty
        else 0
    )

    total_pending = (
        member_calculated[
            "Pending Balance"
        ].sum()
        if not member_calculated.empty
        else 0
    )

    if (
        not st.session_state.expenses.empty
    ):

        expense_numeric = (
            st.session_state.expenses.copy()
        )

        expense_numeric[
            "Amount"
        ] = pd.to_numeric(
            expense_numeric[
                "Amount"
            ],
            errors="coerce"
        ).fillna(0)

        total_expenses = expense_numeric[
            "Amount"
        ].sum()

    else:

        expense_numeric = pd.DataFrame()
        total_expenses = 0

    total_amount_spent = (
        st.session_state.booking_cost
        + total_expenses
    )

    a1, a2, a3 = st.columns(3)

    a1.metric(
        "Total Farmhouse Cost",
        rupee(
            st.session_state.booking_cost
        )
    )

    a2.metric(
        "Total Expenses",
        rupee(total_expenses)
    )

    a3.metric(
        "Total Amount Spent",
        rupee(total_amount_spent)
    )

    a4, a5, a6 = st.columns(3)

    a4.metric(
        "Total Advance Collected",
        rupee(total_advance)
    )

    a5.metric(
        "Total Pending Amount",
        rupee(total_pending)
    )

    a6.metric(
        "Total Members",
        len(member_calculated)
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            "### Category-wise Expenses"
        )

        if not expense_numeric.empty:

            category_summary = (
                expense_numeric
                .groupby(
                    "Expense Category",
                    as_index=False
                )["Amount"]
                .sum()
            )

            st.dataframe(
                category_summary.style.format(
                    {
                        "Amount":
                        "₹{:,.2f}"
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

            chart_data = (
                category_summary.set_index(
                    "Expense Category"
                )
            )

            st.bar_chart(
                chart_data
            )

        else:

            st.info(
                "No expense data available."
            )

    with col2:

        st.markdown(
            "### Member-wise Expenses Paid"
        )

        if not expense_numeric.empty:

            member_paid = (
                expense_numeric
                .groupby(
                    "Paid By",
                    as_index=False
                )["Amount"]
                .sum()
            )

            st.dataframe(
                member_paid.style.format(
                    {
                        "Amount":
                        "₹{:,.2f}"
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "No payment data available."
            )

    st.divider()

    st.markdown(
        "### Payment Status Summary"
    )

    if not member_calculated.empty:

        status_summary = (
            member_calculated[
                "Payment Status"
            ]
            .value_counts()
            .reset_index()
        )

        status_summary.columns = [
            "Payment Status",
            "Members"
        ]

        st.dataframe(
            status_summary,
            use_container_width=True,
            hide_index=True
        )


# ---------------------------------------------------------
# EXCEL DOWNLOAD
# ---------------------------------------------------------

st.divider()

st.subheader(
    "📥 Export Data"
)

excel_file = create_excel()

st.download_button(
    label="Download Excel Report",
    data=excel_file,
    file_name="Farmhouse_Trip_Report.xlsx",
    mime=(
        "application/vnd.openxmlformats-"
        "officedocument.spreadsheetml.sheet"
    ),
    use_container_width=True
)
