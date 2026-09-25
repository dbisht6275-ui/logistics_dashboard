import streamlit as st
import pandas as pd

from datetime import date, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource(show_spinner=False)
def get_bidding_engine():
    """
    Uses the same SQL Server connection pattern requested by the user:
    SQLAlchemy + pymssql + Streamlit secrets.
    """

    def _build_engine():
        connection_url = URL.create(
            "mssql+pymssql",
            username=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            host=st.secrets["DB_SERVER"],
            port=int(st.secrets["DB_PORT"]),
            database=st.secrets["DB_NAME"],
        )

        return create_engine(
            connection_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_size=2,
            max_overflow=1,
        )

    return _build_engine()


# ============================================================
# SQL
# ============================================================

BIDDING_SQL = text(
    r"""
    WITH CTE AS
    (
        SELECT
            BP.BIDID,
            BP.VENDCODE,
            MAX(VD.VENDNAME) AS VENDNAME,
            MAX(
                COALESCE(
                    TRY_CONVERT(DECIMAL(18,2), BP.BIDAMOUNT),
                    0
                )
            ) AS BIDAMOUNT
        FROM BIDAMOUNT BP
        INNER JOIN BIDDETAIL BDD
            ON BDD.BIDID = BP.BIDID
           AND BDD.VENDCODE = BP.VENDCODE
        INNER JOIN VENDMAST VD
            ON VD.VENDCODE = BP.VENDCODE
        WHERE ISNULL(BP.CANCEL,'N') <> 'Y'
        GROUP BY
            BP.BIDID,
            BP.VENDCODE
    ),

    RANKED AS
    (
        SELECT
            *,
            ROW_NUMBER() OVER
            (
                PARTITION BY BIDID
                ORDER BY BIDAMOUNT ASC, VENDCODE ASC
            ) AS RN
        FROM CTE
    ),

    TOP3 AS
    (
        SELECT
            BIDID,

            MAX(CASE WHEN RN = 1 THEN VENDNAME END) AS L_1_NAME,
            MAX(CASE WHEN RN = 1 THEN BIDAMOUNT END) AS L_1_AMOUNT,

            MAX(CASE WHEN RN = 2 THEN VENDNAME END) AS L_2_NAME,
            MAX(CASE WHEN RN = 2 THEN BIDAMOUNT END) AS L_2_AMOUNT,

            MAX(CASE WHEN RN = 3 THEN VENDNAME END) AS L_3_NAME,
            MAX(CASE WHEN RN = 3 THEN BIDAMOUNT END) AS L_3_AMOUNT

        FROM RANKED
        WHERE RN <= 3
        GROUP BY BIDID
    ),

    BIDDER_STATS AS
    (
        SELECT
            BIDID,
            COUNT(*) AS BIDDER_COUNT
        FROM CTE
        GROUP BY BIDID
    )

    SELECT
        BH.BIDID,

        IIF(BH.QUERYBID = 'Y','YES','NO') AS QUERYBID,
        IIF(BH.QUERYTOBID = 'Y','YES','NO') AS QUERYTOBID,

        BH.APPROVED,

        IIF(C.BIDID > 0,'APP','ERP') AS SOURCE,

        BR.STNNAME AS BRANCH,

        N.USERNAME AS GENERATEBYUSER,
        AP.USERNAME AS APPROVEDBYUSER,

        BH.CREATEDON AS GENERATEDDATE,
        BH.BIDAMOUNTUPDATEDON AS REPLYUPDATEON,

        IIF(
            BH.QUERYTOBID = 'Y',
            BH.APPROVEDON,
            NULL
        ) AS APPROVEDON,

        BH.WEIGHT,
        BH.GWEIGHT,

        QUERYAMT.BIDAMOUNT AS [QUERY AMOUNT],

        BH.BIDOPENDT,
        BH.BIDOPENTIME,
        BH.BIDCLOSEDT,
        BH.BIDCLOSETIME,

        BH.ORIGINCITY,
        BH.DESTINATIONCITY,

        VIA.STNNAME AS VIA,

        VT.TYPENAME AS VEHICLETYPE,

        BH.PARTYGODOWN,
        BH.EXACTLOADINGPOINT,
        BH.EXACTDELIVERYPOINT,
        BH.REMARKS,

        /* Winner details - one selected record per BID */
        BD.ISWINNER,
        BD.WINNERLEVEL,
        BD.MANUALBIDREASON,

        WINVEND.VENDNAME AS WINNER_NAME,

        BD.FINALRATE,

        /* Count all winner flags so bad/duplicate master data is visible */
        COALESCE(WCNT.WINNER_COUNT, 0) AS WINNER_COUNT,

        /* LHC */
        LHC.LHCNO,

        HIRE.HIREAMOUNT,

        /* Bidder participation */
        COALESCE(BS.BIDDER_COUNT, 0) AS BIDDER_COUNT,

        /* Top 3 */
        TOP3.L_1_NAME,
        TOP3.L_2_NAME,
        TOP3.L_3_NAME,

        TOP3.L_1_AMOUNT,
        TOP3.L_2_AMOUNT,
        TOP3.L_3_AMOUNT

    FROM BIDHEAD BH

    INNER JOIN STATIONMAST BR
        ON BR.STNCODE = BH.BRANCHCODE

    /* --------------------------------------------------------
       Select only ONE winner row so duplicate ISWINNER='Y'
       records do not duplicate the complete BID in the dashboard.
       Manual row is preferred when both Manual and L-1 are flagged.
       WINNER_COUNT still exposes the data-quality issue.
       -------------------------------------------------------- */
    OUTER APPLY
    (
        SELECT TOP 1
            BDX.VENDCODE,
            BDX.ISWINNER,
            BDX.WINNERLEVEL,
            BDX.MANUALBIDREASON,
            BDX.FINALRATE
        FROM BIDDETAIL BDX WITH (NOLOCK)
        WHERE BDX.BIDID = BH.BIDID
          AND BDX.ISWINNER = 'Y'
        ORDER BY
            CASE
                WHEN LOWER(LTRIM(RTRIM(ISNULL(BDX.WINNERLEVEL,'')))) = 'manual' THEN 0
                WHEN NULLIF(LTRIM(RTRIM(ISNULL(BDX.MANUALBIDREASON,''))), '') IS NOT NULL THEN 1
                WHEN UPPER(LTRIM(RTRIM(ISNULL(BDX.WINNERLEVEL,'')))) = 'L-1' THEN 2
                ELSE 3
            END,
            BDX.VENDCODE
    ) BD

    OUTER APPLY
    (
        SELECT COUNT(*) AS WINNER_COUNT
        FROM BIDDETAIL BDC WITH (NOLOCK)
        WHERE BDC.BIDID = BH.BIDID
          AND BDC.ISWINNER = 'Y'
    ) WCNT

    LEFT JOIN VENDMAST WINVEND
        ON WINVEND.VENDCODE = BD.VENDCODE

    LEFT JOIN VEHICLETYPEMAST VT
        ON VT.TYPECODE = BH.VEHICLETYPECODE

    LEFT JOIN CALLREGISTER C
        ON C.BIDID = BH.BIDID

    LEFT JOIN STATIONMAST VIA
        ON VIA.STNCODE = BH.VIACITY

    LEFT JOIN NAME N
        ON N.CODE = BH.CREATEID

    LEFT JOIN NAME AP
        ON AP.CODE = BH.APPROVEDBY

    OUTER APPLY
    (
        SELECT TOP 1
            BA.BIDAMOUNT
        FROM BIDAMOUNT BA WITH (NOLOCK)
        WHERE BA.BIDID = BH.BIDID
          AND BA.VENDCODE = '0000000000'
          AND BA.BIDAMOUNT > 0
          AND ISNULL(BA.CANCEL,'N') <> 'Y'
    ) QUERYAMT

    OUTER APPLY
    (
        SELECT TOP 1
            LHD.LHCNO
        FROM LHCHEADDETAIL LHD WITH (NOLOCK)
        WHERE LHD.BIDID = BH.BIDID
        ORDER BY LHD.LHCNO DESC
    ) LHC

    OUTER APPLY
    (
        SELECT
            SUM(
                COALESCE(
                    TRY_CONVERT(DECIMAL(18,2), LD.AMOUNT),
                    0
                )
            ) AS HIREAMOUNT
        FROM LHCEXPENSE LD WITH (NOLOCK)
        INNER JOIN MFEXPENSEMAST MCODE
            ON MCODE.MFEXPCODE = LD.MFEXPCODE
        INNER JOIN LHCHEAD LH WITH (NOLOCK)
            ON LH.LHCNO = LD.LHCNO
        WHERE ISNULL(LD.CANCEL,'N') <> 'Y'
          AND MCODE.MFEXPNAME = 'VEHICLE HIRE COST'
          AND LD.LHCNO = LHC.LHCNO
    ) HIRE

    LEFT JOIN TOP3
        ON TOP3.BIDID = BH.BIDID

    LEFT JOIN BIDDER_STATS BS
        ON BS.BIDID = BH.BIDID

    WHERE BH.BIDOPENDT >= :from_date
      AND BH.BIDOPENDT <  :to_date_exclusive
      AND ISNULL(BH.CANCEL,'N') <> 'Y'

    ORDER BY
        BH.BIDOPENDT,
        BH.BIDID;
    """
)


# ============================================================
# DATA LOAD
# ============================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_bidding_data(from_date, to_date):
    """
    to_date is inclusive in the UI.
    SQL receives next day as exclusive upper bound.
    """
    engine = get_bidding_engine()

    to_date_exclusive = to_date + timedelta(days=1)

    with engine.connect() as conn:
        df = pd.read_sql(
            BIDDING_SQL,
            conn,
            params={
                "from_date": from_date,
                "to_date_exclusive": to_date_exclusive,
            },
        )

    return prepare_bidding_data(df)


# ============================================================
# DATA PREPARATION
# ============================================================

def _clean_text_series(series):
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
    )


def prepare_bidding_data(df):
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df

    df = df.copy()

    # Make Python-friendly name.
    if "QUERY AMOUNT" in df.columns:
        df = df.rename(columns={"QUERY AMOUNT": "QUERY_AMOUNT"})

    numeric_columns = [
        "WEIGHT",
        "GWEIGHT",
        "QUERY_AMOUNT",
        "FINALRATE",
        "HIREAMOUNT",
        "L_1_AMOUNT",
        "L_2_AMOUNT",
        "L_3_AMOUNT",
        "BIDDER_COUNT",
        "WINNER_COUNT",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    date_columns = [
        "GENERATEDDATE",
        "REPLYUPDATEON",
        "APPROVEDON",
        "BIDOPENDT",
        "BIDCLOSEDT",
    ]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # --------------------------------------------------------
    # Derived management metrics
    # --------------------------------------------------------
    df["L1_L2_GAP"] = df["L_2_AMOUNT"] - df["L_1_AMOUNT"]
    df["L2_L3_GAP"] = df["L_3_AMOUNT"] - df["L_2_AMOUNT"]

    def gap_status(row):
        if pd.isna(row.get("L_1_AMOUNT")) or pd.isna(row.get("L_2_AMOUNT")):
            return "Not Comparable"
        if row["L1_L2_GAP"] < 500:
            return "Violation"
        return "OK"

    df["GAP_STATUS"] = df.apply(gap_status, axis=1)

    # Positive value = final awarded rate is lower than original L1 amount.
    df["SAVING_VS_L1"] = df["L_1_AMOUNT"] - df["FINALRATE"]

    # Positive value = query amount was higher than final rate.
    df["SAVING_VS_QUERY"] = df["QUERY_AMOUNT"] - df["FINALRATE"]

    # Final rate and booked vehicle hire validation.
    df["FINAL_HIRE_DIFF"] = df["FINALRATE"] - df["HIREAMOUNT"]

    def rate_match_status(row):
        if pd.isna(row.get("FINALRATE")) or pd.isna(row.get("HIREAMOUNT")):
            return "Not Available"
        if abs(row["FINAL_HIRE_DIFF"]) <= 0.01:
            return "Matched"
        return "Mismatch"

    df["FINAL_HIRE_STATUS"] = df.apply(rate_match_status, axis=1)

    winner_level = _clean_text_series(df["WINNERLEVEL"]).str.lower()

    df["WINNER_MODE"] = "Other / Missing"
    df.loc[winner_level.eq("l-1"), "WINNER_MODE"] = "L-1"
    df.loc[winner_level.eq("manual"), "WINNER_MODE"] = "Manual"

    # Some records may contain manual reason even when WINNERLEVEL is inconsistent.
    manual_reason = _clean_text_series(df["MANUALBIDREASON"])
    df.loc[
        manual_reason.ne("") & ~winner_level.eq("l-1"),
        "WINNER_MODE"
    ] = "Manual"

    l1_name = _clean_text_series(df["L_1_NAME"]).str.upper()
    winner_name = _clean_text_series(df["WINNER_NAME"]).str.upper()

    df["WINNER_VS_L1"] = "Not Comparable"
    comparable = l1_name.ne("") & winner_name.ne("")
    df.loc[comparable & l1_name.eq(winner_name), "WINNER_VS_L1"] = "Winner = L1"
    df.loc[comparable & ~l1_name.eq(winner_name), "WINNER_VS_L1"] = "Winner != L1"

    # Participation bucket for charts.
    def bidder_bucket(value):
        if pd.isna(value) or value <= 0:
            return "No Bidder"
        value = int(value)
        if value == 1:
            return "1 Bidder"
        if value == 2:
            return "2 Bidders"
        if value == 3:
            return "3 Bidders"
        return "4+ Bidders"

    df["BIDDER_BUCKET"] = df["BIDDER_COUNT"].apply(bidder_bucket)

    df["ROUTE"] = (
        _clean_text_series(df["ORIGINCITY"]).replace("", "-")
        + " → "
        + _clean_text_series(df["DESTINATIONCITY"]).replace("", "-")
    )

    return df


# ============================================================
# FILTER HELPERS
# ============================================================

def _sorted_options(series):
    values = (
        series.dropna()
        .astype(str)
        .str.strip()
    )
    values = values[values.ne("")]
    return sorted(values.unique().tolist())


def apply_dashboard_filters(df):
    # Filters are kept inside a compact expander so the dashboard opens with
    # management KPIs visible immediately. The selected filters remain active
    # even when the expander is collapsed.
    with st.expander("🔎 Filters", expanded=False):
        row1 = st.columns(4, gap="small")

        with row1[0]:
            branch_filter = st.multiselect(
                "Branch",
                _sorted_options(df["BRANCH"]),
                key="bid_filter_branch",
                placeholder="All branches",
            )

        with row1[1]:
            source_filter = st.multiselect(
                "Source",
                _sorted_options(df["SOURCE"]),
                key="bid_filter_source",
                placeholder="All sources",
            )

        with row1[2]:
            winner_filter = st.multiselect(
                "Winner Type",
                _sorted_options(df["WINNER_MODE"]),
                key="bid_filter_winner",
                placeholder="All winner types",
            )

        with row1[3]:
            vehicle_filter = st.multiselect(
                "Vehicle Type",
                _sorted_options(df["VEHICLETYPE"]),
                key="bid_filter_vehicle",
                placeholder="All vehicle types",
            )

        row2 = st.columns(4, gap="small")

        with row2[0]:
            origin_filter = st.multiselect(
                "Origin",
                _sorted_options(df["ORIGINCITY"]),
                key="bid_filter_origin",
                placeholder="All origins",
            )

        with row2[1]:
            destination_filter = st.multiselect(
                "Destination",
                _sorted_options(df["DESTINATIONCITY"]),
                key="bid_filter_destination",
                placeholder="All destinations",
            )

        with row2[2]:
            gap_filter = st.multiselect(
                "₹500 Gap Status",
                ["OK", "Violation", "Not Comparable"],
                key="bid_filter_gap",
                placeholder="All statuses",
            )

        with row2[3]:
            approved_filter = st.multiselect(
                "Approved",
                _sorted_options(df["APPROVED"]),
                key="bid_filter_approved",
                placeholder="All",
            )

    filtered = df.copy()

    if branch_filter:
        filtered = filtered[filtered["BRANCH"].isin(branch_filter)]

    if source_filter:
        filtered = filtered[filtered["SOURCE"].isin(source_filter)]

    if winner_filter:
        filtered = filtered[filtered["WINNER_MODE"].isin(winner_filter)]

    if vehicle_filter:
        filtered = filtered[filtered["VEHICLETYPE"].isin(vehicle_filter)]

    if origin_filter:
        filtered = filtered[filtered["ORIGINCITY"].isin(origin_filter)]

    if destination_filter:
        filtered = filtered[filtered["DESTINATIONCITY"].isin(destination_filter)]

    if gap_filter:
        filtered = filtered[filtered["GAP_STATUS"].isin(gap_filter)]

    if approved_filter:
        filtered = filtered[filtered["APPROVED"].isin(approved_filter)]

    return filtered


# ============================================================
# KPI / CHARTS
# ============================================================

def _format_inr(value):
    if value is None or pd.isna(value):
        return "-"
    return f"₹{value:,.0f}"


def _kpi_card(column, icon, label, value, note="", tone="blue"):
    note_html = f'<div class="bid-kpi-note">{note}</div>' if note else '<div class="bid-kpi-note">&nbsp;</div>'
    column.markdown(
        f"""
        <div class="bid-kpi-card bid-kpi-{tone}">
            <div class="bid-kpi-top">
                <span class="bid-kpi-icon">{icon}</span>
                <span class="bid-kpi-label">{label}</span>
            </div>
            <div class="bid-kpi-value">{value}</div>
            {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpis(df):
    total_bids = int(df["BIDID"].nunique())

    approved_bids = int(
        df.loc[
            _clean_text_series(df["APPROVED"]).str.upper().eq("Y"),
            "BIDID"
        ].nunique()
    )

    query_bids = int(
        df.loc[
            _clean_text_series(df["QUERYBID"]).str.upper().eq("YES"),
            "BIDID"
        ].nunique()
    )

    l1_bids = int(df.loc[df["WINNER_MODE"].eq("L-1"), "BIDID"].nunique())
    manual_bids = int(df.loc[df["WINNER_MODE"].eq("Manual"), "BIDID"].nunique())
    single_bidder = int(df.loc[df["BIDDER_COUNT"].eq(1), "BIDID"].nunique())
    gap_violations = int(df.loc[df["GAP_STATUS"].eq("Violation"), "BIDID"].nunique())

    avg_bidders = df.loc[df["BIDDER_COUNT"].gt(0), "BIDDER_COUNT"].mean()
    duplicate_winner_flags = int(
        df.loc[df["WINNER_COUNT"].gt(1), "BIDID"].nunique()
    )

    final_rate_total = df["FINALRATE"].sum(min_count=1)
    saving_vs_l1 = df["SAVING_VS_L1"].sum(min_count=1)

    approved_pct = (approved_bids / total_bids * 100) if total_bids else 0
    l1_pct = (l1_bids / total_bids * 100) if total_bids else 0
    manual_pct = (manual_bids / total_bids * 100) if total_bids else 0
    single_pct = (single_bidder / total_bids * 100) if total_bids else 0

    r1 = st.columns(5, gap="small")
    _kpi_card(r1[0], "📦", "Total Bids", f"{total_bids:,}", "Filtered unique bids", "blue")
    _kpi_card(r1[1], "✅", "Approved", f"{approved_bids:,}", f"{approved_pct:.1f}% of bids", "green")
    _kpi_card(r1[2], "💬", "Query Bids", f"{query_bids:,}", "Rate query raised", "purple")
    _kpi_card(r1[3], "🥇", "L-1 Selected", f"{l1_bids:,}", f"{l1_pct:.1f}% of bids", "teal")
    _kpi_card(r1[4], "✍️", "Manual Selected", f"{manual_bids:,}", f"{manual_pct:.1f}% of bids", "orange")

    r2 = st.columns(5, gap="small")
    _kpi_card(r2[0], "👤", "Single Bidder", f"{single_bidder:,}", f"{single_pct:.1f}% of bids", "amber")
    _kpi_card(r2[1], "⚠️", "Gap Violations", f"{gap_violations:,}", "L1-L2 gap below ₹500", "red")
    _kpi_card(
        r2[2], "👥", "Avg Bidders / Bid",
        "-" if pd.isna(avg_bidders) else f"{avg_bidders:.2f}",
        "Competitive participation", "cyan"
    )
    _kpi_card(r2[3], "🚩", "Duplicate Winners", f"{duplicate_winner_flags:,}", "Multiple winner flags", "rose")
    _kpi_card(
        r2[4], "₹", "Total Final Rate", _format_inr(final_rate_total),
        (f"Saving {_format_inr(saving_vs_l1)} vs L1" if not pd.isna(saving_vs_l1) else "No saving data"),
        "navy"
    )


def render_charts(df):
    st.markdown("### Management Analysis")

    left, right = st.columns(2)

    with left:
        st.markdown("#### Bids by Branch")
        branch_data = (
            df.groupby("BRANCH", dropna=False)["BIDID"]
            .nunique()
            .sort_values(ascending=False)
            .head(15)
            .rename("Bids")
            .to_frame()
        )
        if not branch_data.empty:
            st.bar_chart(branch_data, use_container_width=True)
        else:
            st.info("No branch data available.")

    with right:
        st.markdown("#### Winner Selection")
        winner_data = (
            df.groupby("WINNER_MODE")["BIDID"]
            .nunique()
            .sort_values(ascending=False)
            .rename("Bids")
            .to_frame()
        )
        if not winner_data.empty:
            st.bar_chart(winner_data, use_container_width=True)
        else:
            st.info("No winner data available.")

    left, right = st.columns(2)

    with left:
        st.markdown("#### Bidder Participation")
        participation_order = [
            "No Bidder",
            "1 Bidder",
            "2 Bidders",
            "3 Bidders",
            "4+ Bidders",
        ]

        participation = (
            df.groupby("BIDDER_BUCKET")["BIDID"]
            .nunique()
            .reindex(participation_order)
            .fillna(0)
            .astype(int)
            .rename("Bids")
            .to_frame()
        )
        st.bar_chart(participation, use_container_width=True)

    with right:
        st.markdown("#### ₹500 Gap Compliance")
        gap_data = (
            df.groupby("GAP_STATUS")["BIDID"]
            .nunique()
            .reindex(["OK", "Violation", "Not Comparable"])
            .fillna(0)
            .astype(int)
            .rename("Bids")
            .to_frame()
        )
        st.bar_chart(gap_data, use_container_width=True)

    st.markdown("#### Daily Bid Trend")

    trend_df = df.dropna(subset=["BIDOPENDT"]).copy()
    if not trend_df.empty:
        trend_df["BID_DATE"] = trend_df["BIDOPENDT"].dt.date
        daily = (
            trend_df.groupby("BID_DATE")["BIDID"]
            .nunique()
            .rename("Bids")
            .to_frame()
        )
        st.line_chart(daily, use_container_width=True)
    else:
        st.info("No bid date data available.")


# ============================================================
# EXCEPTIONS
# ============================================================

def _exception_table(df, columns):
    available = [col for col in columns if col in df.columns]
    if df.empty:
        st.info("No records.")
        return

    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        column_config={
            "QUERY_AMOUNT": st.column_config.NumberColumn(
                "Query Amount",
                format="₹ %.2f",
            ),
            "L_1_AMOUNT": st.column_config.NumberColumn(
                "L1 Amount",
                format="₹ %.2f",
            ),
            "L_2_AMOUNT": st.column_config.NumberColumn(
                "L2 Amount",
                format="₹ %.2f",
            ),
            "L_3_AMOUNT": st.column_config.NumberColumn(
                "L3 Amount",
                format="₹ %.2f",
            ),
            "L1_L2_GAP": st.column_config.NumberColumn(
                "L1-L2 Gap",
                format="₹ %.2f",
            ),
            "FINALRATE": st.column_config.NumberColumn(
                "Final Rate",
                format="₹ %.2f",
            ),
            "HIREAMOUNT": st.column_config.NumberColumn(
                "Hire Amount",
                format="₹ %.2f",
            ),
            "SAVING_VS_L1": st.column_config.NumberColumn(
                "Saving vs L1",
                format="₹ %.2f",
            ),
            "FINAL_HIRE_DIFF": st.column_config.NumberColumn(
                "Final-Hire Diff",
                format="₹ %.2f",
            ),
        },
    )


def render_exceptions(df):
    st.markdown("### Exceptions & Control Checks")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "₹500 Gap Violations",
            "Manual Winners",
            "Duplicate Winner Flags",
            "Single Bidder",
            "Final vs Hire",
        ]
    )

    base_cols = [
        "BIDID",
        "BIDOPENDT",
        "BRANCH",
        "ROUTE",
        "VEHICLETYPE",
        "BIDDER_COUNT",
        "L_1_NAME",
        "L_1_AMOUNT",
        "L_2_NAME",
        "L_2_AMOUNT",
        "L1_L2_GAP",
        "WINNER_NAME",
        "WINNER_MODE",
        "FINALRATE",
        "SAVING_VS_L1",
        "MANUALBIDREASON",
        "LHCNO",
        "HIREAMOUNT",
    ]

    with tab1:
        violation_df = df[df["GAP_STATUS"].eq("Violation")].copy()
        _exception_table(violation_df, base_cols)

    with tab2:
        manual_df = df[df["WINNER_MODE"].eq("Manual")].copy()
        _exception_table(
            manual_df,
            base_cols + ["WINNER_VS_L1", "QUERY_AMOUNT"],
        )

    with tab3:
        duplicate_df = df[df["WINNER_COUNT"].gt(1)].copy()
        _exception_table(
            duplicate_df,
            [
                "BIDID",
                "BIDOPENDT",
                "BRANCH",
                "ROUTE",
                "WINNER_COUNT",
                "WINNER_NAME",
                "WINNERLEVEL",
                "MANUALBIDREASON",
                "FINALRATE",
                "L_1_NAME",
                "L_1_AMOUNT",
            ],
        )

    with tab4:
        single_df = df[df["BIDDER_COUNT"].eq(1)].copy()
        _exception_table(
            single_df,
            [
                "BIDID",
                "BIDOPENDT",
                "BRANCH",
                "ROUTE",
                "VEHICLETYPE",
                "BIDDER_COUNT",
                "L_1_NAME",
                "L_1_AMOUNT",
                "WINNER_NAME",
                "WINNER_MODE",
                "FINALRATE",
                "MANUALBIDREASON",
            ],
        )

    with tab5:
        mismatch_df = df[df["FINAL_HIRE_STATUS"].eq("Mismatch")].copy()
        _exception_table(
            mismatch_df,
            [
                "BIDID",
                "BIDOPENDT",
                "BRANCH",
                "ROUTE",
                "WINNER_NAME",
                "FINALRATE",
                "LHCNO",
                "HIREAMOUNT",
                "FINAL_HIRE_DIFF",
            ],
        )


# ============================================================
# DETAIL TABLE
# ============================================================

def render_detail_table(df):
    st.markdown("### Bid-wise Detail")

    detail_columns = [
        "BIDID",
        "BIDOPENDT",
        "BRANCH",
        "SOURCE",
        "QUERYBID",
        "APPROVED",
        "ROUTE",
        "VIA",
        "VEHICLETYPE",
        "WEIGHT",
        "GWEIGHT",
        "BIDDER_COUNT",
        "QUERY_AMOUNT",
        "L_1_NAME",
        "L_1_AMOUNT",
        "L_2_NAME",
        "L_2_AMOUNT",
        "L_3_NAME",
        "L_3_AMOUNT",
        "L1_L2_GAP",
        "GAP_STATUS",
        "WINNER_NAME",
        "WINNER_MODE",
        "WINNERLEVEL",
        "FINALRATE",
        "SAVING_VS_L1",
        "WINNER_VS_L1",
        "MANUALBIDREASON",
        "LHCNO",
        "HIREAMOUNT",
        "FINAL_HIRE_STATUS",
        "FINAL_HIRE_DIFF",
        "WINNER_COUNT",
        "GENERATEBYUSER",
        "APPROVEDBYUSER",
        "PARTYGODOWN",
        "EXACTLOADINGPOINT",
        "EXACTDELIVERYPOINT",
        "REMARKS",
    ]

    available = [c for c in detail_columns if c in df.columns]

    display_df = df[available].sort_values(
        by=["BIDOPENDT", "BIDID"],
        ascending=[False, False],
        na_position="last",
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "BIDID": st.column_config.NumberColumn("Bid ID", format="%d"),
            "QUERY_AMOUNT": st.column_config.NumberColumn(
                "Query Amount",
                format="₹ %.2f",
            ),
            "L_1_AMOUNT": st.column_config.NumberColumn(
                "L1 Amount",
                format="₹ %.2f",
            ),
            "L_2_AMOUNT": st.column_config.NumberColumn(
                "L2 Amount",
                format="₹ %.2f",
            ),
            "L_3_AMOUNT": st.column_config.NumberColumn(
                "L3 Amount",
                format="₹ %.2f",
            ),
            "L1_L2_GAP": st.column_config.NumberColumn(
                "L1-L2 Gap",
                format="₹ %.2f",
            ),
            "FINALRATE": st.column_config.NumberColumn(
                "Final Rate",
                format="₹ %.2f",
            ),
            "SAVING_VS_L1": st.column_config.NumberColumn(
                "Saving vs L1",
                format="₹ %.2f",
            ),
            "HIREAMOUNT": st.column_config.NumberColumn(
                "Hire Amount",
                format="₹ %.2f",
            ),
            "FINAL_HIRE_DIFF": st.column_config.NumberColumn(
                "Final-Hire Diff",
                format="₹ %.2f",
            ),
        },
    )

    csv_data = display_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "⬇️ Download Filtered Data",
        data=csv_data,
        file_name="bidding_dashboard_filtered.csv",
        mime="text/csv",
        key="download_bidding_dashboard_csv",
    )


# ============================================================
# MAIN PAGE
# ============================================================

def show_bidding_analysis():
    st.markdown(
        """
        <style>
        /* =====================================================
           COMPACT BIDDING DASHBOARD
           ===================================================== */
        .main .block-container {
            padding-top: .35rem !important;
            padding-bottom: 1rem !important;
        }

        .bid-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin: 0 0 .45rem 0;
            padding: .62rem .82rem;
            border: 1px solid #dfe7f1;
            border-radius: 12px;
            background: linear-gradient(135deg, #ffffff 0%, #f5f9ff 100%);
            box-shadow: 0 2px 8px rgba(15,47,99,.05);
        }
        .bid-title-wrap { min-width: 0; }
        .bid-title {
            margin: 0;
            color: #0f2f63;
            font-size: 1.42rem;
            line-height: 1.1;
            font-weight: 800;
            letter-spacing: -.02em;
        }
        .bid-subtitle {
            margin-top: .18rem;
            color: #64748b;
            font-size: .78rem;
            line-height: 1.25;
        }
        .bid-header-badge {
            flex: 0 0 auto;
            padding: .28rem .55rem;
            border-radius: 999px;
            background: #eaf2ff;
            color: #1d5aa6;
            font-size: .70rem;
            font-weight: 700;
            border: 1px solid #d3e4fb;
        }

        /* Compact date form */
        div[data-testid="stForm"] {
            padding: .48rem .65rem .38rem !important;
            margin-bottom: .25rem !important;
            border: 1px solid #e1e7ef !important;
            border-radius: 10px !important;
            background: #ffffff !important;
        }
        div[data-testid="stForm"] [data-testid="stWidgetLabel"] p {
            font-size: .72rem !important;
            font-weight: 650 !important;
            margin-bottom: .10rem !important;
        }
        div[data-testid="stForm"] [data-testid="stDateInput"] input {
            min-height: 34px !important;
            height: 34px !important;
            font-size: .78rem !important;
        }
        div[data-testid="stForm"] .stButton > button,
        div[data-testid="stForm"] [data-testid="stFormSubmitButton"] > button {
            min-height: 34px !important;
            height: 34px !important;
            margin-top: 0 !important;
            border-radius: 8px !important;
            font-size: .78rem !important;
            font-weight: 700 !important;
            color: #ffffff !important;
            background: linear-gradient(135deg,#1769d2,#0f4f9d) !important;
            border: 0 !important;
            box-shadow: 0 3px 8px rgba(23,105,210,.18) !important;
        }

        .bid-period-line {
            display: flex;
            align-items: center;
            gap: 7px;
            margin: .14rem 0 .32rem;
            color: #6b7280;
            font-size: .72rem;
        }
        .bid-period-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #22c55e;
            box-shadow: 0 0 0 3px rgba(34,197,94,.11);
        }

        /* Compact expander / filters */
        [data-testid="stExpander"] {
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
            background: #fff !important;
            margin-bottom: .45rem !important;
        }
        [data-testid="stExpander"] summary {
            min-height: 36px !important;
            padding-top: .25rem !important;
            padding-bottom: .25rem !important;
        }
        [data-testid="stExpander"] summary p {
            font-size: .80rem !important;
            font-weight: 700 !important;
            color: #27466f !important;
        }
        [data-testid="stExpander"] [data-testid="stWidgetLabel"] p {
            font-size: .69rem !important;
            font-weight: 650 !important;
        }
        [data-testid="stExpander"] [data-baseweb="select"] > div {
            min-height: 34px !important;
            font-size: .75rem !important;
        }

        /* KPI cards */
        .bid-kpi-card {
            min-height: 91px;
            padding: .58rem .65rem .50rem;
            margin-bottom: .34rem;
            border-radius: 11px;
            border: 1px solid #e3eaf3;
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(15,47,99,.055);
            position: relative;
            overflow: hidden;
        }
        .bid-kpi-card::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: var(--accent);
        }
        .bid-kpi-top {
            display: flex;
            align-items: center;
            gap: 6px;
            min-width: 0;
        }
        .bid-kpi-icon {
            width: 25px;
            height: 25px;
            flex: 0 0 25px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 7px;
            background: var(--soft);
            font-size: .78rem;
        }
        .bid-kpi-label {
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            color: #53657d;
            font-size: .69rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: .025em;
        }
        .bid-kpi-value {
            margin-top: .34rem;
            color: #12233f;
            font-size: 1.38rem;
            line-height: 1;
            font-weight: 850;
            letter-spacing: -.025em;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .bid-kpi-note {
            margin-top: .26rem;
            color: #7a8799;
            font-size: .61rem;
            line-height: 1.05;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .bid-kpi-blue   { --accent:#2563eb; --soft:#eff6ff; }
        .bid-kpi-green  { --accent:#16a34a; --soft:#f0fdf4; }
        .bid-kpi-purple { --accent:#7c3aed; --soft:#f5f3ff; }
        .bid-kpi-teal   { --accent:#0f9f8f; --soft:#f0fdfa; }
        .bid-kpi-orange { --accent:#ea580c; --soft:#fff7ed; }
        .bid-kpi-amber  { --accent:#d97706; --soft:#fffbeb; }
        .bid-kpi-red    { --accent:#dc2626; --soft:#fef2f2; }
        .bid-kpi-cyan   { --accent:#0891b2; --soft:#ecfeff; }
        .bid-kpi-rose   { --accent:#e11d48; --soft:#fff1f2; }
        .bid-kpi-navy   { --accent:#0f2f63; --soft:#eef4fb; }

        /* Less vertical whitespace around headings/dividers/charts */
        h3 {
            margin-top: .55rem !important;
            margin-bottom: .35rem !important;
            font-size: 1.02rem !important;
        }
        h4 {
            margin-top: .35rem !important;
            margin-bottom: .25rem !important;
            font-size: .84rem !important;
        }
        hr {
            margin: .52rem 0 !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: .48rem;
        }

        @media (max-width: 900px) {
            .bid-header-badge { display:none; }
            .bid-kpi-value { font-size: 1.18rem; }
        }
        </style>

        <div class="bid-header">
            <div class="bid-title-wrap">
                <div class="bid-title">🚚 Bidding Analysis</div>
                <div class="bid-subtitle">Competition • winner selection • ₹500 gap compliance • final rate • LHC validation</div>
            </div>
            <div class="bid-header-badge">Management Dashboard</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    today = date.today()

    if "bidding_from_date" not in st.session_state:
        st.session_state["bidding_from_date"] = today - timedelta(days=7)

    if "bidding_to_date" not in st.session_state:
        st.session_state["bidding_to_date"] = today

    with st.form("bidding_period_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([1, 1, .85], gap="small")

        with c1:
            from_date = st.date_input(
                "From Date",
                value=st.session_state["bidding_from_date"],
            )

        with c2:
            to_date = st.date_input(
                "To Date",
                value=st.session_state["bidding_to_date"],
            )

        with c3:
            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
            load_clicked = st.form_submit_button(
                "↻ Load / Refresh",
                use_container_width=True,
            )

    if from_date > to_date:
        st.error("From Date cannot be greater than To Date.")
        return

    should_load = load_clicked or "bidding_raw_data" not in st.session_state

    if should_load:
        st.session_state["bidding_from_date"] = from_date
        st.session_state["bidding_to_date"] = to_date

        try:
            with st.spinner("Loading bidding data..."):
                if load_clicked:
                    load_bidding_data.clear()

                raw_df = load_bidding_data(from_date, to_date)
                st.session_state["bidding_raw_data"] = raw_df

        except Exception as exc:
            st.error("Unable to load bidding data from SQL Server.")
            st.exception(exc)
            return

    raw_df = st.session_state.get("bidding_raw_data", pd.DataFrame())

    if raw_df is None or raw_df.empty:
        st.warning("No bidding data found for the selected date range.")
        return

    st.markdown(
        f"""
        <div class="bid-period-line">
            <span class="bid-period-dot"></span>
            <span>
                Loaded <b>{st.session_state['bidding_from_date'].strftime('%d %b %Y')}</b>
                to <b>{st.session_state['bidding_to_date'].strftime('%d %b %Y')}</b>
                &nbsp;•&nbsp; <b>{raw_df['BIDID'].nunique():,}</b> unique bids
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    filtered_df = apply_dashboard_filters(raw_df)

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    render_kpis(filtered_df)

    st.markdown("---")
    render_charts(filtered_df)

    st.markdown("---")
    render_exceptions(filtered_df)

    st.markdown("---")
    render_detail_table(filtered_df)

