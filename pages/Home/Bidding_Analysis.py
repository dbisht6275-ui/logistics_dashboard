import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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
            COUNT(*) AS BIDDER_COUNT,
            STUFF(
                (
                    SELECT
                        '|||' + CAST(
                            CONCAT(
                                C2.VENDCODE,
                                '::',
                                REPLACE(REPLACE(ISNULL(C2.VENDNAME, ''), '|||', ' '), '::', ' ')
                            ) AS NVARCHAR(MAX)
                        )
                    FROM CTE C2
                    WHERE C2.BIDID = C1.BIDID
                    FOR XML PATH(''), TYPE
                ).value('.', 'NVARCHAR(MAX)'),
                1,
                3,
                ''
            ) AS BIDDER_VENDOR_LIST
        FROM CTE C1
        GROUP BY C1.BIDID
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
        COALESCE(BS.BIDDER_VENDOR_LIST, '') AS BIDDER_VENDOR_LIST,

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

    # --------------------------------------------------------
    # LHC CONTROL / PENDING AGEING
    # --------------------------------------------------------
    is_winner_flag = _clean_text_series(df["ISWINNER"]).str.upper().eq("Y")
    has_winner_name = _clean_text_series(df["WINNER_NAME"]).ne("")
    has_final_rate = df["FINALRATE"].notna()

    df["HAS_WINNER"] = is_winner_flag | has_winner_name | has_final_rate

    lhc_no_text = _clean_text_series(df["LHCNO"])
    approved_y = _clean_text_series(df["APPROVED"]).str.upper().eq("Y")

    df["LHC_STATUS"] = "No Winner"

    # LHC already exists.
    df.loc[
        df["HAS_WINNER"] & lhc_no_text.ne(""),
        "LHC_STATUS"
    ] = "LHC Created"

    # IMPORTANT CONTROL:
    # Count Winner -> LHC Pending only when the BID is approved.
    df.loc[
        df["HAS_WINNER"] & lhc_no_text.eq("") & approved_y,
        "LHC_STATUS"
    ] = "Winner - LHC Pending"

    # Winner exists but approval is still not Y, therefore it is not yet an
    # approved LHC-pending case.
    df.loc[
        df["HAS_WINNER"] & lhc_no_text.eq("") & ~approved_y,
        "LHC_STATUS"
    ] = "Winner - Not Approved"

    # There is no separate Winner Selected Date in the current SQL output.
    # Ageing therefore uses:
    # APPROVEDON -> BIDCLOSEDT -> BIDOPENDT
    ageing_source = (
        df[["APPROVEDON", "BIDCLOSEDT", "BIDOPENDT"]]
        .bfill(axis=1)
        .iloc[:, 0]
    )

    df["LHC_AGEING_FROM"] = pd.to_datetime(ageing_source, errors="coerce")

    today_ts = pd.Timestamp(date.today())
    ageing_days = (
        today_ts - df["LHC_AGEING_FROM"].dt.normalize()
    ).dt.days

    ageing_days = ageing_days.clip(lower=0)

    pending_mask = df["LHC_STATUS"].eq("Winner - LHC Pending")
    df["LHC_PENDING_AGE_DAYS"] = ageing_days.where(pending_mask)

    def lhc_age_bucket(days):
        if pd.isna(days):
            return "Not Pending"

        days = int(days)

        if days == 0:
            return "0 Day"
        if days == 1:
            return "1 Day"
        if days <= 3:
            return "2-3 Days"
        if days <= 7:
            return "4-7 Days"
        if days <= 15:
            return "8-15 Days"
        if days <= 30:
            return "16-30 Days"
        return "31+ Days"

    df["LHC_AGEING_BUCKET"] = df["LHC_PENDING_AGE_DAYS"].apply(lhc_age_bucket)

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
    """Compact collapsible filters. Default state is collapsed."""
    with st.expander("🔎 Filters — click to expand / collapse", expanded=False):
        row1 = st.columns(5, gap="small")

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
            querybid_filter = st.multiselect(
                "Query Bid",
                ["YES", "NO"],
                key="bid_filter_querybid",
                placeholder="YES / NO",
            )

        with row1[3]:
            winner_filter = st.multiselect(
                "Winner Type",
                _sorted_options(df["WINNER_MODE"]),
                key="bid_filter_winner",
                placeholder="All winner types",
            )

        with row1[4]:
            vehicle_filter = st.multiselect(
                "Vehicle Type",
                _sorted_options(df["VEHICLETYPE"]),
                key="bid_filter_vehicle",
                placeholder="All vehicle types",
            )

        row2 = st.columns(5, gap="small")

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

        with row2[4]:
            lhc_status_filter = st.multiselect(
                "LHC Status",
                ["LHC Created", "Winner - LHC Pending", "Winner - Not Approved", "No Winner"],
                key="bid_filter_lhc_status",
                placeholder="All LHC statuses",
            )

    filtered = df.copy()

    if branch_filter:
        filtered = filtered[filtered["BRANCH"].isin(branch_filter)]

    if source_filter:
        filtered = filtered[filtered["SOURCE"].isin(source_filter)]

    if querybid_filter:
        filtered = filtered[filtered["QUERYBID"].isin(querybid_filter)]

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

    if lhc_status_filter:
        filtered = filtered[filtered["LHC_STATUS"].isin(lhc_status_filter)]

    return filtered


# ============================================================
# KPI / CHARTS
# ============================================================

CHART_TEXT_COLOR = "#0f2744"
CHART_MUTED_TEXT_COLOR = "#334155"

def _format_inr(value):
    if value is None or pd.isna(value):
        return "-"
    return f"₹{value:,.0f}"


def _kpi_card(column, label, value, note="", tone="blue"):
    note_text = note if note else "&nbsp;"
    column.markdown(
        f"""
        <div class="bid-kpi-card bid-kpi-{tone}">
            <div class="bid-kpi-label">{label}</div>
            <div class="bid-kpi-value">{value}</div>
            <div class="bid-kpi-note">{note_text}</div>
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
    winner_not_l1 = int(
        df.loc[df["WINNER_VS_L1"].eq("Winner != L1"), "BIDID"].nunique()
    )
    comparable_winner_bids = int(
        df.loc[
            df["WINNER_VS_L1"].isin(["Winner = L1", "Winner != L1"]),
            "BIDID",
        ].nunique()
    )
    manual_bids = int(df.loc[df["WINNER_MODE"].eq("Manual"), "BIDID"].nunique())
    single_bidder = int(df.loc[df["BIDDER_COUNT"].eq(1), "BIDID"].nunique())
    gap_violations = int(df.loc[df["GAP_STATUS"].eq("Violation"), "BIDID"].nunique())
    avg_bidders = df.loc[df["BIDDER_COUNT"].gt(0), "BIDDER_COUNT"].mean()

    approved_pct = (approved_bids / total_bids * 100) if total_bids else 0
    query_pct = (query_bids / total_bids * 100) if total_bids else 0
    l1_pct = (l1_bids / total_bids * 100) if total_bids else 0
    winner_not_l1_pct = (
        winner_not_l1 / comparable_winner_bids * 100
        if comparable_winner_bids else 0
    )
    manual_pct = (manual_bids / total_bids * 100) if total_bids else 0
    single_pct = (single_bidder / total_bids * 100) if total_bids else 0
    gap_pct = (gap_violations / total_bids * 100) if total_bids else 0

    k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9, gap="small")

    _kpi_card(k1, "📦 Total Bids", f"{total_bids:,}", "Filtered unique bids", "blue")
    _kpi_card(k2, "✅ Approved", f"{approved_bids:,}", f"{approved_pct:.1f}% of bids", "green")
    _kpi_card(k3, "💬 Query Bids", f"{query_bids:,}", f"{query_pct:.1f}% of bids", "purple")
    _kpi_card(k4, "🥇 L-1 Selected", f"{l1_bids:,}", f"{l1_pct:.1f}% of bids", "teal")
    _kpi_card(
        k5,
        "🚫 Winner Not L1",
        f"{winner_not_l1:,}",
        f"{winner_not_l1_pct:.1f}% of comparable winners",
        "rose",
    )
    _kpi_card(k6, "✍️ Manual", f"{manual_bids:,}", f"{manual_pct:.1f}% of bids", "orange")
    _kpi_card(k7, "👤 Single Bidder", f"{single_bidder:,}", f"{single_pct:.1f}% of bids", "amber")
    _kpi_card(k8, "⚠️ Gap Violations", f"{gap_violations:,}", f"{gap_pct:.1f}% of bids", "red")
    _kpi_card(
        k9,
        "👥 Avg Bidders",
        "-" if pd.isna(avg_bidders) else f"{avg_bidders:.2f}",
        "Per participating bid",
        "cyan",
    )

    # LHC operational control KPIs
    winner_bids = int(df.loc[df["HAS_WINNER"], "BIDID"].nunique())

    approved_winner_mask = (
        df["HAS_WINNER"]
        & _clean_text_series(df["APPROVED"]).str.upper().eq("Y")
    )
    approved_winner_bids = int(
        df.loc[approved_winner_mask, "BIDID"].nunique()
    )

    lhc_created = int(
        df.loc[df["LHC_STATUS"].eq("LHC Created"), "BIDID"].nunique()
    )
    lhc_pending = int(
        df.loc[df["LHC_STATUS"].eq("Winner - LHC Pending"), "BIDID"].nunique()
    )

    pending_rows = df[df["LHC_STATUS"].eq("Winner - LHC Pending")].copy()

    oldest_pending = (
        int(pending_rows["LHC_PENDING_AGE_DAYS"].max())
        if not pending_rows.empty and pending_rows["LHC_PENDING_AGE_DAYS"].notna().any()
        else 0
    )

    pending_over_7 = int(
        pending_rows.loc[
            pending_rows["LHC_PENDING_AGE_DAYS"].gt(7),
            "BIDID"
        ].nunique()
    )

    lhc_created_pct = (lhc_created / winner_bids * 100) if winner_bids else 0
    lhc_pending_pct = (
        lhc_pending / approved_winner_bids * 100
        if approved_winner_bids else 0
    )

    l1c, l2c, l3c, l4c = st.columns(4, gap="small")

    _kpi_card(
        l1c,
        "🏆 Winner Bids",
        f"{winner_bids:,}",
        "Winner already selected",
        "navy",
    )
    _kpi_card(
        l2c,
        "🚚 LHC Created",
        f"{lhc_created:,}",
        f"{lhc_created_pct:.1f}% of winner bids",
        "green",
    )
    _kpi_card(
        l3c,
        "⏳ LHC Pending",
        f"{lhc_pending:,}",
        f"{lhc_pending_pct:.1f}% of approved winner bids",
        "red",
    )
    _kpi_card(
        l4c,
        "🕒 Oldest Pending",
        f"{oldest_pending:,} days",
        f"{pending_over_7:,} bids pending > 7 days",
        "amber",
    )


def _compact_chart_layout(fig, height=245, bottom_margin=48):
    """Common compact styling for all management charts."""
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=12, b=bottom_margin),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        showlegend=False,
        hoverlabel=dict(
            bgcolor="#0b2447",
            font_size=11,
            font_color="#ffffff",
        ),
        font=dict(
            family="Arial, sans-serif",
            size=10,
            color=CHART_TEXT_COLOR,
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#dbe4ef",
        tickfont=dict(size=9, color=CHART_TEXT_COLOR),
        title=None,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#eef2f7",
        zeroline=False,
        tickfont=dict(size=9, color=CHART_TEXT_COLOR),
        title=None,
        rangemode="tozero",
    )
    return fig


def _bar_chart_with_values(labels, values, height=245, rotate_x=0):
    """Create a compact bar chart with values always visible above bars."""
    labels = [str(x) for x in labels]
    values = [int(v) if pd.notna(v) else 0 for v in values]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            text=[f"{v:,}" for v in values],
            textposition="outside",
            textfont=dict(size=10, color=CHART_TEXT_COLOR),
            cliponaxis=False,
            marker=dict(
                color="#2563eb",
                line=dict(color="#1d4ed8", width=0.5),
            ),
            hovertemplate="<b>%{x}</b><br>Bids: %{y:,}<extra></extra>",
        )
    )

    max_value = max(values) if values else 0
    if max_value > 0:
        fig.update_yaxes(range=[0, max_value * 1.18])

    _compact_chart_layout(fig, height=height, bottom_margin=58 if rotate_x else 42)
    fig.update_xaxes(tickangle=rotate_x)
    return fig


def _horizontal_bar_chart(labels, values, height=270, value_name="Bids"):
    """Ranked horizontal bar chart for long category labels."""
    work = pd.DataFrame({"Label": [str(x) for x in labels], "Value": values})
    work["Value"] = pd.to_numeric(work["Value"], errors="coerce").fillna(0).astype(int)
    work = work.sort_values("Value", ascending=True)

    fig = go.Figure(
        go.Bar(
            x=work["Value"],
            y=work["Label"],
            orientation="h",
            text=[f"{v:,}" for v in work["Value"]],
            textposition="outside",
            textfont=dict(size=9, color=CHART_TEXT_COLOR),
            cliponaxis=False,
            marker=dict(
                color="#2563eb",
                line=dict(color="#1d4ed8", width=0.5),
            ),
            hovertemplate=f"<b>%{{y}}</b><br>{value_name}: %{{x:,}}<extra></extra>",
        )
    )

    max_value = int(work["Value"].max()) if not work.empty else 0
    if max_value > 0:
        fig.update_xaxes(range=[0, max_value * 1.18])

    _compact_chart_layout(fig, height=height, bottom_margin=38)
    fig.update_yaxes(
        showgrid=False,
        autorange=True,
        tickfont=dict(size=9, color=CHART_TEXT_COLOR),
        automargin=True,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f7")
    fig.update_layout(bargap=0.30)
    return fig


def _donut_chart(labels, values, height=245, center_label="Total"):
    """Clean donut for small part-to-whole comparisons."""
    labels = [str(x) for x in labels]
    values = [int(v) if pd.notna(v) else 0 for v in values]
    total = sum(values)

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.64,
            sort=False,
            textinfo="percent",
            textfont=dict(size=10, color=CHART_TEXT_COLOR),
            hovertemplate="<b>%{label}</b><br>Bids: %{value:,}<br>Share: %{percent}<extra></extra>",
            marker=dict(line=dict(color="#ffffff", width=2)),
        )
    )

    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.03,
            xanchor="center",
            x=0.5,
            font=dict(size=9, color=CHART_TEXT_COLOR),
        ),
        font=dict(family="Arial, sans-serif", size=10, color=CHART_TEXT_COLOR),
        annotations=[
            dict(
                text=f"<b>{total:,}</b><br><span style='font-size:9px'>{center_label}</span>",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color=CHART_TEXT_COLOR),
                align="center",
            )
        ],
    )
    return fig


def _lollipop_chart(labels, values, height=270, value_name="Bids"):
    """Compact lollipop ranking to avoid repeating bar charts."""
    work = pd.DataFrame({"Label": [str(x) for x in labels], "Value": values})
    work["Value"] = pd.to_numeric(work["Value"], errors="coerce").fillna(0).astype(int)
    work = work.sort_values("Value", ascending=True)

    line_x, line_y = [], []
    for label, value in zip(work["Label"], work["Value"]):
        line_x.extend([0, value, None])
        line_y.extend([label, label, None])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            line=dict(color="#cbd5e1", width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=work["Value"],
            y=work["Label"],
            mode="markers+text",
            text=[f"{v:,}" for v in work["Value"]],
            textposition="middle right",
            textfont=dict(size=9, color=CHART_TEXT_COLOR),
            marker=dict(
                size=10,
                color="#2563eb",
                line=dict(color="#ffffff", width=1.5),
            ),
            cliponaxis=False,
            hovertemplate=f"<b>%{{y}}</b><br>{value_name}: %{{x:,}}<extra></extra>",
            showlegend=False,
        )
    )

    max_value = int(work["Value"].max()) if not work.empty else 0
    if max_value > 0:
        fig.update_xaxes(range=[0, max_value * 1.22])

    _compact_chart_layout(fig, height=height, bottom_margin=38)
    fig.update_yaxes(showgrid=False, automargin=True, tickfont=dict(size=9, color=CHART_TEXT_COLOR))
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f7", tickfont=dict(size=9, color=CHART_TEXT_COLOR))
    return fig


def _line_chart_with_values(labels, values, height=235):
    """Create daily trend chart with value labels above every point."""
    labels = [str(x) for x in labels]
    values = [int(v) if pd.notna(v) else 0 for v in values]

    fig = go.Figure(
        go.Scatter(
            x=labels,
            y=values,
            mode="lines+markers+text",
            text=[f"{v:,}" for v in values],
            textposition="top center",
            textfont=dict(size=9, color=CHART_TEXT_COLOR),
            line=dict(color="#2563eb", width=2),
            marker=dict(
                size=6,
                color="#ffffff",
                line=dict(color="#2563eb", width=2),
            ),
            hovertemplate="<b>%{x}</b><br>Bids: %{y:,}<extra></extra>",
        )
    )

    max_value = max(values) if values else 0
    if max_value > 0:
        fig.update_yaxes(range=[0, max_value * 1.20])

    _compact_chart_layout(fig, height=height, bottom_margin=44)
    return fig


def _render_chart_card(title, fig):
    """Render every chart inside the same bordered compact card."""
    with st.container(border=True):
        st.markdown(
            f"<div class='bid-chart-title'>{title}</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True,
            },
        )



def _ageing_chart_with_values(ageing_df, height=255):
    """
    Professional ageing chart:
    - Different color by ageing severity
    - Count + % displayed above each bar
    - % is calculated against total Winner -> LHC Pending bids
    """
    work = ageing_df.copy()

    work["Bids"] = pd.to_numeric(work["Bids"], errors="coerce").fillna(0).astype(int)
    total_pending = int(work["Bids"].sum())

    if total_pending > 0:
        work["Percent"] = work["Bids"] / total_pending * 100.0
    else:
        work["Percent"] = 0.0

    # Green -> teal -> blue -> amber -> orange -> red progression.
    ageing_colors = {
        "0 Day": "#16a34a",
        "1 Day": "#22c55e",
        "2-3 Days": "#0d9488",
        "4-7 Days": "#2563eb",
        "8-15 Days": "#d97706",
        "16-30 Days": "#ea580c",
        "31+ Days": "#dc2626",
    }

    colors = [
        ageing_colors.get(str(bucket), "#64748b")
        for bucket in work["LHC_AGEING_BUCKET"]
    ]

    labels = [
        f"{count:,}  |  {pct:.1f}%"
        for count, pct in zip(work["Bids"], work["Percent"])
    ]

    fig = go.Figure(
        go.Bar(
            x=work["LHC_AGEING_BUCKET"].astype(str),
            y=work["Bids"],
            text=labels,
            textposition="outside",
            textfont=dict(
                size=10,
                color=CHART_TEXT_COLOR,
            ),
            cliponaxis=False,
            marker=dict(
                color=colors,
                line=dict(
                    color="#ffffff",
                    width=0.8,
                ),
            ),
            customdata=work["Percent"],
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Pending Bids: %{y:,}<br>"
                "Share: %{customdata:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    max_value = int(work["Bids"].max()) if not work.empty else 0
    if max_value > 0:
        fig.update_yaxes(range=[0, max_value * 1.24])

    _compact_chart_layout(
        fig,
        height=height,
        bottom_margin=55,
    )

    fig.update_layout(
        showlegend=False,
        bargap=0.28,
    )

    fig.update_xaxes(
        tickangle=-18,
        tickfont=dict(size=9, color=CHART_TEXT_COLOR),
    )

    return fig



def _bid_trend_data(df, mode):
    """Aggregate unique BIDIDs by Day / Month / Quarter / Year."""
    trend_df = df.dropna(subset=["BIDOPENDT"]).copy()

    if trend_df.empty:
        return pd.DataFrame(columns=["PERIOD_LABEL", "Bids"])

    trend_df["BIDOPENDT"] = pd.to_datetime(trend_df["BIDOPENDT"], errors="coerce")
    trend_df = trend_df.dropna(subset=["BIDOPENDT"])

    if mode == "D":
        trend_df["PERIOD_KEY"] = trend_df["BIDOPENDT"].dt.date
        grouped = (
            trend_df.groupby("PERIOD_KEY")["BIDID"]
            .nunique()
            .rename("Bids")
            .reset_index()
        )
        grouped["PERIOD_LABEL"] = pd.to_datetime(grouped["PERIOD_KEY"]).dt.strftime("%d %b")

    elif mode == "M":
        trend_df["PERIOD_KEY"] = trend_df["BIDOPENDT"].dt.to_period("M")
        grouped = (
            trend_df.groupby("PERIOD_KEY")["BIDID"]
            .nunique()
            .rename("Bids")
            .reset_index()
        )
        grouped["PERIOD_LABEL"] = grouped["PERIOD_KEY"].dt.strftime("%b %Y")

    elif mode == "Q":
        trend_df["PERIOD_KEY"] = trend_df["BIDOPENDT"].dt.to_period("Q")
        grouped = (
            trend_df.groupby("PERIOD_KEY")["BIDID"]
            .nunique()
            .rename("Bids")
            .reset_index()
        )
        grouped["PERIOD_LABEL"] = grouped["PERIOD_KEY"].apply(
            lambda p: f"Q{p.quarter} {p.year}"
        )

    else:  # Y
        trend_df["PERIOD_KEY"] = trend_df["BIDOPENDT"].dt.year
        grouped = (
            trend_df.groupby("PERIOD_KEY")["BIDID"]
            .nunique()
            .rename("Bids")
            .reset_index()
        )
        grouped["PERIOD_LABEL"] = grouped["PERIOD_KEY"].astype(int).astype(str)

    return grouped[["PERIOD_LABEL", "Bids"]]


def _render_bid_trend_card(df):
    """Bid Trend chart with D / M / Q / Y buttons in the card header."""
    if "bid_trend_mode" not in st.session_state:
        st.session_state["bid_trend_mode"] = "D"

    current_mode = st.session_state["bid_trend_mode"]

    with st.container(border=True):
        # Marker is used by CSS to scope compact button styling to this card only.
        st.markdown("<span class='bid-trend-marker'></span>", unsafe_allow_html=True)

        title_col, d_col, m_col, q_col, y_col = st.columns(
            [5.5, .42, .42, .42, .42],
            gap="small",
            vertical_alignment="center",
        )

        with title_col:
            st.markdown(
                "<div class='bid-chart-title'>Bid Trend</div>",
                unsafe_allow_html=True,
            )

        button_map = [
            ("D", d_col, "bid_trend_d"),
            ("M", m_col, "bid_trend_m"),
            ("Q", q_col, "bid_trend_q"),
            ("Y", y_col, "bid_trend_y"),
        ]

        for mode, col, key in button_map:
            with col:
                if st.button(
                    mode,
                    key=key,
                    type="primary" if current_mode == mode else "secondary",
                    use_container_width=True,
                    help={
                        "D": "Daily",
                        "M": "Monthly",
                        "Q": "Quarterly",
                        "Y": "Yearly",
                    }[mode],
                ):
                    st.session_state["bid_trend_mode"] = mode
                    st.rerun()

        current_mode = st.session_state["bid_trend_mode"]
        trend_data = _bid_trend_data(df, current_mode)

        if trend_data.empty:
            st.info("No bid date data available.")
            return

        subtitle_map = {
            "D": "Daily",
            "M": "Monthly",
            "Q": "Quarterly",
            "Y": "Yearly",
        }

        st.caption(
            f"{subtitle_map[current_mode]} unique bid volume • "
            f"{int(trend_data['Bids'].sum()):,} period-count total"
        )

        trend_fig = _line_chart_with_values(
            trend_data["PERIOD_LABEL"],
            trend_data["Bids"],
            height=245,
        )

        st.plotly_chart(
            trend_fig,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "responsive": True,
            },
        )


def render_charts(df):
    st.markdown("### Management Analysis")

    # --------------------------------------------------------
    # Row 1: primary volume rankings
    # --------------------------------------------------------
    left, right = st.columns(2, gap="small")

    with left:
        branch_data = (
            df.groupby("BRANCH", dropna=False)["BIDID"]
            .nunique()
            .sort_values(ascending=False)
            .head(12)
            .rename("Bids")
            .reset_index()
        )

        if not branch_data.empty:
            branch_fig = _horizontal_bar_chart(
                branch_data["BRANCH"],
                branch_data["Bids"],
                height=300,
                value_name="Bids",
            )
            _render_chart_card("Top Branches by Bid Volume", branch_fig)
        else:
            with st.container(border=True):
                st.markdown("<div class='bid-chart-title'>Top Branches by Bid Volume</div>", unsafe_allow_html=True)
                st.info("No branch data available.")

    with right:
        route_data = (
            df.assign(
                ROUTE_CLEAN=_clean_text_series(df["ROUTE"]).replace("", "Not Available")
            )
            .groupby("ROUTE_CLEAN")["BIDID"]
            .nunique()
            .sort_values(ascending=False)
            .head(12)
            .rename("Bids")
            .reset_index()
        )

        if not route_data.empty:
            route_fig = _horizontal_bar_chart(
                route_data["ROUTE_CLEAN"],
                route_data["Bids"],
                height=300,
                value_name="Bids",
            )
            _render_chart_card("Top Routes by Bid Volume", route_fig)
        else:
            with st.container(border=True):
                st.markdown(
                    "<div class='bid-chart-title'>Top Routes by Bid Volume</div>",
                    unsafe_allow_html=True,
                )
                st.info("No route data available.")

    # --------------------------------------------------------
    # Row 2: all composition donuts in ONE row
    # --------------------------------------------------------
    d1, d2, d3 = st.columns(3, gap="small")

    winner_data = (
        df.groupby("WINNER_MODE")["BIDID"]
        .nunique()
        .reindex(["L-1", "Manual", "Other / Missing"])
        .fillna(0)
        .astype(int)
        .rename("Bids")
        .reset_index()
    )
    winner_data = winner_data[winner_data["Bids"].gt(0)]

    with d1:
        if not winner_data.empty:
            winner_fig = _donut_chart(
                winner_data["WINNER_MODE"],
                winner_data["Bids"],
                height=250,
                center_label="Winner Bids",
            )
            _render_chart_card("Winner Selection Mix", winner_fig)
        else:
            with st.container(border=True):
                st.markdown("<div class='bid-chart-title'>Winner Selection Mix</div>", unsafe_allow_html=True)
                st.info("No winner data available.")

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
        .reset_index()
    )
    participation = participation[participation["Bids"].gt(0)]

    with d2:
        if not participation.empty:
            participation_fig = _donut_chart(
                participation["BIDDER_BUCKET"],
                participation["Bids"],
                height=250,
                center_label="Bids",
            )
            _render_chart_card("Bidder Participation Mix", participation_fig)
        else:
            with st.container(border=True):
                st.markdown("<div class='bid-chart-title'>Bidder Participation Mix</div>", unsafe_allow_html=True)
                st.info("No bidder participation data available.")

    gap_data = (
        df.groupby("GAP_STATUS")["BIDID"]
        .nunique()
        .reindex(["OK", "Violation", "Not Comparable"])
        .fillna(0)
        .astype(int)
        .rename("Bids")
        .reset_index()
    )
    gap_data = gap_data[gap_data["Bids"].gt(0)]

    with d3:
        if not gap_data.empty:
            gap_fig = _donut_chart(
                gap_data["GAP_STATUS"],
                gap_data["Bids"],
                height=250,
                center_label="Checked",
            )
            _render_chart_card("₹500 Gap Compliance Mix", gap_fig)
        else:
            with st.container(border=True):
                st.markdown("<div class='bid-chart-title'>₹500 Gap Compliance Mix</div>", unsafe_allow_html=True)
                st.info("No gap-compliance data available.")

    # --------------------------------------------------------
    # Row 3: operational management views
    # --------------------------------------------------------
    left, right = st.columns(2, gap="small")

    with left:
        approved_user_data = (
            df.assign(
                APPROVEDBYUSER_CLEAN=_clean_text_series(df["APPROVEDBYUSER"]).replace("", "Not Available")
            )
            .groupby("APPROVEDBYUSER_CLEAN")["BIDID"]
            .nunique()
            .sort_values(ascending=False)
            .head(12)
            .rename("Bids")
            .reset_index()
        )

        if not approved_user_data.empty:
            approved_user_fig = _lollipop_chart(
                approved_user_data["APPROVEDBYUSER_CLEAN"],
                approved_user_data["Bids"],
                height=300,
                value_name="Approved Bids",
            )
            _render_chart_card(
                "Approver Workload — Top Users",
                approved_user_fig,
            )
        else:
            with st.container(border=True):
                st.markdown(
                    "<div class='bid-chart-title'>Approver Workload — Top Users</div>",
                    unsafe_allow_html=True,
                )
                st.info("No approver data available.")

    with right:
        pending_df = df[df["LHC_STATUS"].eq("Winner - LHC Pending")].copy()

        ageing_order = [
            "0 Day",
            "1 Day",
            "2-3 Days",
            "4-7 Days",
            "8-15 Days",
            "16-30 Days",
            "31+ Days",
        ]

        if not pending_df.empty:
            ageing_data = (
                pending_df.groupby("LHC_AGEING_BUCKET")["BIDID"]
                .nunique()
                .reindex(ageing_order)
                .fillna(0)
                .astype(int)
                .rename("Bids")
                .reset_index()
            )

            ageing_fig = _ageing_chart_with_values(
                ageing_data,
                height=300,
            )
            _render_chart_card(
                "Approved Winner → LHC Pending Ageing  •  Count + % of Pending",
                ageing_fig,
            )
        else:
            with st.container(border=True):
                st.markdown(
                    "<div class='bid-chart-title'>Winner → LHC Pending Ageing</div>",
                    unsafe_allow_html=True,
                )
                st.info("No winner bids are pending for LHC.")

    # --------------------------------------------------------
    # Row 4: full-width time trend
    # --------------------------------------------------------
    _render_bid_trend_card(df)


# ============================================================
# VENDOR WINNER PERFORMANCE
# ============================================================

def _vendor_participation_rows(df):
    """Build one row per Vendor x Bid for accurate wins/losses."""
    base = (
        df.sort_values(["BIDID", "BIDOPENDT"], na_position="last")
        .drop_duplicates(subset=["BIDID"], keep="last")
        .copy()
    )

    rows = []

    for _, row in base.iterrows():
        bidid = row.get("BIDID")
        winner_value = row.get("WINNER_NAME")
        winner = "" if pd.isna(winner_value) else str(winner_value).strip()
        winner_key = winner.upper()
        seen = set()

        raw_value = row.get("BIDDER_VENDOR_LIST")
        raw_list = "" if pd.isna(raw_value) else str(raw_value).strip()

        if raw_list:
            for token in raw_list.split("|||"):
                token = token.strip()
                if not token:
                    continue

                if "::" in token:
                    vendcode, vendor = token.split("::", 1)
                else:
                    vendcode, vendor = "", token

                vendcode = vendcode.strip()
                vendor = vendor.strip()
                vendor_key = vendor.upper()

                if not vendor or vendor_key in seen:
                    continue

                seen.add(vendor_key)
                rows.append(
                    {
                        "BIDID": bidid,
                        "Vendor Code": vendcode,
                        "Vendor": vendor,
                        "Is Win": int(bool(winner_key) and vendor_key == winner_key),
                    }
                )
        else:
            # Backward-compatible fallback for cached data loaded before the
            # all-bidder SQL field existed. Refreshing the dashboard loads all bidders.
            for col in ["L_1_NAME", "L_2_NAME", "L_3_NAME"]:
                vendor_value = row.get(col)
                vendor = "" if pd.isna(vendor_value) else str(vendor_value).strip()
                vendor_key = vendor.upper()
                if not vendor or vendor_key in seen:
                    continue
                seen.add(vendor_key)
                rows.append(
                    {
                        "BIDID": bidid,
                        "Vendor Code": "",
                        "Vendor": vendor,
                        "Is Win": int(bool(winner_key) and vendor_key == winner_key),
                    }
                )

        # Defensive: keep a selected winner in the vendor table even if the bidder
        # list is incomplete because of source-data issues.
        if winner and winner_key not in seen:
            rows.append(
                {
                    "BIDID": bidid,
                    "Vendor Code": "",
                    "Vendor": winner,
                    "Is Win": 1,
                }
            )

    if not rows:
        return pd.DataFrame(columns=["BIDID", "Vendor Code", "Vendor", "Is Win"])

    participation = pd.DataFrame(rows)
    participation["Vendor Key"] = _clean_text_series(participation["Vendor"]).str.upper()

    # One vendor can appear only once per bid in performance calculations.
    participation = (
        participation.sort_values(["BIDID", "Is Win"], ascending=[True, False])
        .drop_duplicates(subset=["BIDID", "Vendor Key"], keep="first")
        .copy()
    )
    return participation


def _vendor_win_loss_chart(vendor_table, height=330):
    """Top vendor participation split into won and lost bids."""
    work = vendor_table.sort_values(
        ["Bid Participations", "Winner Bids"], ascending=[False, False]
    ).head(12).copy()
    work = work.sort_values("Bid Participations", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=work["Winner Bids"],
            y=work["Vendor"],
            name="Won",
            orientation="h",
            marker=dict(color="#16a34a"),
            hovertemplate="<b>%{y}</b><br>Won: %{x:,}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=work["Lost Bids"],
            y=work["Vendor"],
            name="Lost",
            orientation="h",
            marker=dict(color="#cbd5e1"),
            hovertemplate="<b>%{y}</b><br>Lost: %{x:,}<extra></extra>",
        )
    )

    _compact_chart_layout(fig, height=height, bottom_margin=42)
    fig.update_layout(
        barmode="stack",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            font=dict(size=9, color=CHART_TEXT_COLOR),
        ),
        bargap=0.28,
    )
    fig.update_yaxes(showgrid=False, automargin=True, tickfont=dict(size=9, color=CHART_TEXT_COLOR))
    fig.update_xaxes(showgrid=True, gridcolor="#eef2f7", tickfont=dict(size=9, color=CHART_TEXT_COLOR))
    return fig


def _vendor_win_rate_chart(vendor_table, height=330):
    """Dot plot of vendor win rate, restricted to meaningful participation."""
    work = vendor_table[vendor_table["Bid Participations"].gt(0)].copy()
    work = work.sort_values(
        ["Bid Participations", "Win Rate %"], ascending=[False, False]
    ).head(12)
    work = work.sort_values("Win Rate %", ascending=True)

    fig = go.Figure(
        go.Scatter(
            x=work["Win Rate %"],
            y=work["Vendor"],
            mode="markers+text",
            text=[f"{v:.1f}%" for v in work["Win Rate %"]],
            textposition="middle right",
            textfont=dict(size=9, color=CHART_TEXT_COLOR),
            marker=dict(
                size=10,
                color="#7c3aed",
                line=dict(color="#ffffff", width=1.5),
            ),
            customdata=work[["Bid Participations", "Winner Bids", "Lost Bids"]],
            hovertemplate=(
                "<b>%{y}</b><br>Win Rate: %{x:.1f}%<br>"
                "Participations: %{customdata[0]:,}<br>"
                "Won: %{customdata[1]:,}<br>"
                "Lost: %{customdata[2]:,}<extra></extra>"
            ),
            showlegend=False,
        )
    )

    _compact_chart_layout(fig, height=height, bottom_margin=42)
    fig.update_xaxes(
        range=[0, 108],
        ticksuffix="%",
        dtick=20,
        showgrid=True,
        gridcolor="#eef2f7",
    )
    fig.update_yaxes(showgrid=False, automargin=True, tickfont=dict(size=9, color=CHART_TEXT_COLOR))
    return fig


def render_vendor_performance(df):
    st.markdown("### Vendor Performance — Wins, Losses & Conversion")

    participation = _vendor_participation_rows(df)

    if participation.empty:
        st.info("No vendor participation data available for the selected filters.")
        return

    participation_summary = (
        participation.groupby("Vendor", as_index=False)
        .agg(
            **{
                "Bid Participations": ("BIDID", "nunique"),
                "Winner Bids": ("Is Win", "sum"),
            }
        )
    )
    participation_summary["Lost Bids"] = (
        participation_summary["Bid Participations"] - participation_summary["Winner Bids"]
    ).clip(lower=0)
    participation_summary["Win Rate %"] = (
        participation_summary["Winner Bids"]
        .div(participation_summary["Bid Participations"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
    )
    participation_summary["Loss Rate %"] = 100.0 - participation_summary["Win Rate %"]

    winner_df = df[
        df["HAS_WINNER"]
        & _clean_text_series(df["WINNER_NAME"]).ne("")
    ].copy()

    # Defensive: one BID should contribute only once to winner statistics.
    winner_df = (
        winner_df
        .sort_values(["BIDID", "BIDOPENDT"], na_position="last")
        .drop_duplicates(subset=["BIDID"], keep="last")
        .copy()
    )

    if not winner_df.empty:
        winner_df["APPROVED_WIN_FLAG"] = (
            _clean_text_series(winner_df["APPROVED"]).str.upper().eq("Y")
        ).astype(int)

        winner_df["L1_WIN_FLAG"] = (
            winner_df["WINNER_VS_L1"].eq("Winner = L1")
        ).astype(int)

        winner_df["MANUAL_WIN_FLAG"] = (
            winner_df["WINNER_MODE"].eq("Manual")
        ).astype(int)

        winner_df["LHC_CREATED_FLAG"] = (
            winner_df["LHC_STATUS"].eq("LHC Created")
        ).astype(int)

        winner_df["LHC_PENDING_FLAG"] = (
            winner_df["LHC_STATUS"].eq("Winner - LHC Pending")
        ).astype(int)

        winner_df["SINGLE_BIDDER_WIN_FLAG"] = (
            pd.to_numeric(winner_df["BIDDER_COUNT"], errors="coerce").eq(1)
        ).astype(int)

        winner_metrics = (
            winner_df.groupby("WINNER_NAME", as_index=False)
            .agg(
                **{
                    "L1 Wins": ("L1_WIN_FLAG", "sum"),
                    "Manual Wins": ("MANUAL_WIN_FLAG", "sum"),
                    "Approved Wins": ("APPROVED_WIN_FLAG", "sum"),
                    "LHC Created": ("LHC_CREATED_FLAG", "sum"),
                    "LHC Pending": ("LHC_PENDING_FLAG", "sum"),
                    "Single Bidder Wins": ("SINGLE_BIDDER_WIN_FLAG", "sum"),
                    "Avg Bidders": ("BIDDER_COUNT", "mean"),
                    "Avg Saving vs L1": ("SAVING_VS_L1", "mean"),
                    "Branches": ("BRANCH", "nunique"),
                    "Routes": ("ROUTE", "nunique"),
                    "Last Win": ("BIDOPENDT", "max"),
                    "Oldest Pending Days": ("LHC_PENDING_AGE_DAYS", "max"),
                }
            )
            .rename(columns={"WINNER_NAME": "Vendor"})
        )
    else:
        winner_metrics = pd.DataFrame(columns=["Vendor"])

    vendor_table = participation_summary.merge(
        winner_metrics,
        on="Vendor",
        how="left",
    )

    total_winner_bids = int(winner_df["BIDID"].nunique()) if not winner_df.empty else 0
    vendor_table["Win Share %"] = (
        vendor_table["Winner Bids"] / total_winner_bids * 100.0
        if total_winner_bids else 0.0
    )

    count_cols = [
        "L1 Wins",
        "Manual Wins",
        "Approved Wins",
        "LHC Created",
        "LHC Pending",
        "Single Bidder Wins",
        "Branches",
        "Routes",
    ]
    for col in count_cols:
        if col not in vendor_table.columns:
            vendor_table[col] = 0
        vendor_table[col] = pd.to_numeric(vendor_table[col], errors="coerce").fillna(0).astype(int)

    vendor_table["LHC Pending %"] = (
        vendor_table["LHC Pending"]
        .div(vendor_table["Approved Wins"].replace(0, pd.NA))
        .mul(100.0)
        .fillna(0.0)
    )

    for col in ["Avg Bidders", "Avg Saving vs L1"]:
        if col not in vendor_table.columns:
            vendor_table[col] = pd.NA

    vendor_table["Avg Bidders"] = pd.to_numeric(
        vendor_table["Avg Bidders"], errors="coerce"
    ).round(2)

    vendor_table["Avg Saving vs L1"] = pd.to_numeric(
        vendor_table["Avg Saving vs L1"], errors="coerce"
    ).round(0)

    if "Oldest Pending Days" not in vendor_table.columns:
        vendor_table["Oldest Pending Days"] = 0
    vendor_table["Oldest Pending Days"] = pd.to_numeric(
        vendor_table["Oldest Pending Days"], errors="coerce"
    ).fillna(0).astype(int)

    if "Last Win" not in vendor_table.columns:
        vendor_table["Last Win"] = pd.NaT

    vendor_table = vendor_table.sort_values(
        ["Bid Participations", "Winner Bids", "Win Rate %", "Vendor"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    vendor_table.insert(0, "Rank", range(1, len(vendor_table) + 1))

    total_participations = int(vendor_table["Bid Participations"].sum())
    total_wins = int(vendor_table["Winner Bids"].sum())
    total_losses = int(vendor_table["Lost Bids"].sum())
    overall_win_rate = (total_wins / total_participations * 100.0) if total_participations else 0.0

    v1, v2, v3, v4 = st.columns(4, gap="small")
    _kpi_card(v1, "🤝 Vendor Participations", f"{total_participations:,}", "Vendor × bid attempts", "blue")
    _kpi_card(v2, "🏆 Won Bids", f"{total_wins:,}", f"{overall_win_rate:.1f}% conversion", "green")
    _kpi_card(v3, "❌ Lost Bids", f"{total_losses:,}", "Participated but not selected", "red")
    _kpi_card(v4, "🏢 Active Vendors", f"{vendor_table['Vendor'].nunique():,}", "Participated in selected period", "purple")

    chart_left, chart_right = st.columns(2, gap="small")
    with chart_left:
        _render_chart_card(
            "Top Vendor Participation — Won vs Lost",
            _vendor_win_loss_chart(vendor_table),
        )
    with chart_right:
        _render_chart_card(
            "Vendor Win Rate — Top Participants",
            _vendor_win_rate_chart(vendor_table),
        )

    display_columns = [
        "Rank",
        "Vendor",
        "Bid Participations",
        "Winner Bids",
        "Lost Bids",
        "Win Rate %",
        "Loss Rate %",
        "Win Share %",
        "L1 Wins",
        "Manual Wins",
        "Approved Wins",
        "LHC Created",
        "LHC Pending",
        "LHC Pending %",
        "Single Bidder Wins",
        "Avg Bidders",
        "Avg Saving vs L1",
        "Branches",
        "Routes",
        "Last Win",
        "Oldest Pending Days",
    ]

    vendor_table = vendor_table[display_columns]

    if not vendor_table.empty:
        top_participant = vendor_table.iloc[0]
        top_winner = vendor_table.sort_values(
            ["Winner Bids", "Win Rate %", "Bid Participations"],
            ascending=[False, False, False],
        ).iloc[0]
        st.markdown(
            f"""
            <div class="bid-report-meta">
                📊 Most Active: <b>{top_participant['Vendor']}</b>
                &nbsp;•&nbsp; {int(top_participant['Bid Participations']):,} participations
                &nbsp;•&nbsp; {int(top_participant['Lost Bids']):,} lost
                &nbsp;&nbsp; | &nbsp;&nbsp;
                🏆 Most Wins: <b>{top_winner['Vendor']}</b>
                &nbsp;•&nbsp; {int(top_winner['Winner Bids']):,} wins
                &nbsp;•&nbsp; {float(top_winner['Win Rate %']):.1f}% win rate
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.dataframe(
        vendor_table,
        use_container_width=True,
        hide_index=True,
        height=470,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", format="%d", width="small"),
            "Vendor": st.column_config.TextColumn("Vendor", width="large"),
            "Bid Participations": st.column_config.NumberColumn("Bid Participations", format="%d"),
            "Winner Bids": st.column_config.NumberColumn("Won Bids", format="%d"),
            "Lost Bids": st.column_config.NumberColumn("Lost Bids", format="%d"),
            "Win Rate %": st.column_config.ProgressColumn(
                "Win Rate %",
                min_value=0,
                max_value=100,
                format="%.1f%%",
            ),
            "Loss Rate %": st.column_config.ProgressColumn(
                "Loss Rate %",
                min_value=0,
                max_value=100,
                format="%.1f%%",
            ),
            "Win Share %": st.column_config.ProgressColumn(
                "Win Share %",
                min_value=0,
                max_value=100,
                format="%.1f%%",
            ),
            "L1 Wins": st.column_config.NumberColumn("L1 Wins", format="%d"),
            "Manual Wins": st.column_config.NumberColumn("Manual Wins", format="%d"),
            "Approved Wins": st.column_config.NumberColumn("Approved Wins", format="%d"),
            "LHC Created": st.column_config.NumberColumn("LHC Created", format="%d"),
            "LHC Pending": st.column_config.NumberColumn("LHC Pending", format="%d"),
            "LHC Pending %": st.column_config.ProgressColumn(
                "LHC Pending %",
                min_value=0,
                max_value=100,
                format="%.1f%%",
            ),
            "Single Bidder Wins": st.column_config.NumberColumn(
                "Single Bidder Wins", format="%d"
            ),
            "Avg Bidders": st.column_config.NumberColumn("Avg Bidders", format="%.2f"),
            "Avg Saving vs L1": st.column_config.NumberColumn(
                "Avg Saving vs L1", format="₹ %.0f"
            ),
            "Branches": st.column_config.NumberColumn("Branches", format="%d"),
            "Routes": st.column_config.NumberColumn("Routes", format="%d"),
            "Last Win": st.column_config.DatetimeColumn(
                "Last Win", format="DD/MM/YYYY"
            ),
            "Oldest Pending Days": st.column_config.NumberColumn(
                "Oldest Pending Days", format="%d"
            ),
        },
    )

    csv_data = vendor_table.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "⬇️ Download Vendor Performance",
        data=csv_data,
        file_name="vendor_performance_wins_losses.csv",
        mime="text/csv",
        key="download_vendor_winner_performance",
    )


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
            "LHC_PENDING_AGE_DAYS": st.column_config.NumberColumn(
                "Ageing Days",
                format="%d",
            ),
            "LHC_AGEING_FROM": st.column_config.DatetimeColumn(
                "Ageing From",
                format="DD/MM/YYYY",
            ),
        },
    )


def render_exceptions(df):
    st.markdown("### Exceptions & Control Checks")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [
            "⏳ Approved Winner → LHC Pending",
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
        pending_df = df[df["LHC_STATUS"].eq("Winner - LHC Pending")].copy()

        ageing_order = [
            "0 Day",
            "1 Day",
            "2-3 Days",
            "4-7 Days",
            "8-15 Days",
            "16-30 Days",
            "31+ Days",
        ]

        age_filter = st.multiselect(
            "Pending Ageing",
            ageing_order,
            key="bid_lhc_pending_age_filter",
            placeholder="All ageing buckets",
        )

        if age_filter:
            pending_df = pending_df[
                pending_df["LHC_AGEING_BUCKET"].isin(age_filter)
            ]

        pending_df = pending_df.sort_values(
            ["LHC_PENDING_AGE_DAYS", "BIDID"],
            ascending=[False, False],
            na_position="last",
        )

        _exception_table(
            pending_df,
            [
                "BIDID",
                "BIDOPENDT",
                "BIDCLOSEDT",
                "APPROVEDON",
                "BRANCH",
                "ROUTE",
                "VEHICLETYPE",
                "QUERYBID",
                "APPROVED",
                "WINNER_NAME",
                "WINNER_MODE",
                "FINALRATE",
                "LHC_STATUS",
                "LHC_AGEING_FROM",
                "LHC_PENDING_AGE_DAYS",
                "LHC_AGEING_BUCKET",
                "GENERATEBYUSER",
                "APPROVEDBYUSER",
                "MANUALBIDREASON",
            ],
        )

    with tab2:
        violation_df = df[df["GAP_STATUS"].eq("Violation")].copy()
        _exception_table(violation_df, base_cols)

    with tab3:
        manual_df = df[df["WINNER_MODE"].eq("Manual")].copy()
        _exception_table(
            manual_df,
            base_cols + ["WINNER_VS_L1", "QUERY_AMOUNT"],
        )

    with tab4:
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

    with tab5:
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

    with tab6:
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
        "LHC_STATUS",
        "LHCNO",
        "LHC_AGEING_FROM",
        "LHC_PENDING_AGE_DAYS",
        "LHC_AGEING_BUCKET",
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
            "LHC_PENDING_AGE_DAYS": st.column_config.NumberColumn(
                "Ageing Days",
                format="%d",
            ),
            "LHC_AGEING_FROM": st.column_config.DatetimeColumn(
                "Ageing From",
                format="DD/MM/YYYY",
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
           COMPACT BIDDING DASHBOARD - NBD STYLE
           ===================================================== */
        .block-container {
            max-width:100% !important;
            padding:.35rem .65rem .9rem !important;
        }

        div[data-testid="stVerticalBlock"] { gap:.55rem !important; }
        div[data-testid="stHorizontalBlock"] { gap:.45rem !important; }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius:9px !important;
            border:1px solid #dbe4ef !important;
            box-shadow:0 2px 7px rgba(15,42,67,.05) !important;
            background:#fff !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding:.50rem .65rem !important;
        }

        /* Chart cards need a few pixels of safe top space so headings never clip. */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.bid-chart-title) > div {
            padding-top:.42rem !important;
        }

        label[data-testid="stWidgetLabel"] p {
            font-size:10.5px !important;
            line-height:1.25 !important;
            margin-bottom:3px !important;
        }
        div[data-baseweb="select"] > div {
            min-height:38px !important;
            font-size:11px !important;
        }
        div[data-testid="stDateInput"] input {
            min-height:32px !important;
            height:32px !important;
            font-size:10px !important;
            padding-top:2px !important;
            padding-bottom:2px !important;
        }

        div[data-testid="stDateInput"] div[data-baseweb="input"] {
            min-height:32px !important;
        }

        /* Header date labels are rendered inline, to the LEFT of each date box. */
        .bid-inline-date-label {
            display:flex;
            align-items:center;
            justify-content:flex-end;
            min-height:32px;
            height:32px;
            color:#334155;
            font-size:9.5px;
            font-weight:800;
            line-height:1;
            white-space:nowrap;
            padding-right:2px;
        }

        /* Remove any extra vertical space around collapsed date labels in header. */
        div[data-testid="stHorizontalBlock"]:has(.bid-header-anchor)
        div[data-testid="stDateInput"] {
            margin-top:0 !important;
            margin-bottom:0 !important;
        }

        /* Collapsible filters */
        div[data-testid="stExpander"] {
            border:1px solid #dbe4ef !important;
            border-radius:9px !important;
            background:#ffffff !important;
            box-shadow:0 2px 7px rgba(15,42,67,.04) !important;
        }
        div[data-testid="stExpander"] summary {
            min-height:32px !important;
            padding:.25rem .55rem !important;
        }
        div[data-testid="stExpander"] summary p {
            font-size:10.5px !important;
            font-weight:800 !important;
            color:#0f2744 !important;
        }
        div[data-testid="stExpander"] details > div {
            padding:.15rem .55rem .45rem !important;
        }

        .bid-title {
            color:#102a43;
            font-size:18px;
            font-weight:850;
            line-height:1.18;
            margin:0;
        }
        .bid-subtitle {
            color:#64748b;
            font-size:9.5px;
            line-height:1.25;
            margin-top:2px;
        }
        .bid-period-badge {
            display:inline-block;
            padding:3px 7px;
            border-radius:999px;
            background:#eff6ff;
            color:#1d4f91;
            border:1px solid #bfdbfe;
            font-size:8.5px;
            font-weight:800;
            letter-spacing:.1px;
        }
        .bid-period-line {
            display:block;
            width:100%;
            box-sizing:border-box;
            background:#0b2447;
            color:#ffffff;
            border:1px solid #17365D;
            border-radius:7px;
            padding:6px 10px;
            margin:2px 0 4px 0;
            font-size:9.5px;
            font-weight:700;
            line-height:1.25;
            box-shadow:0 2px 6px rgba(11,36,71,.14);
        }

        .bid-filter-inline-title {
            color:#0f2744;
            font-size:13px;
            font-weight:850;
            line-height:1.1;
            padding-top:24px;
            white-space:nowrap;
        }

        .bid-kpi-card {
            box-sizing:border-box;
            background:linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
            border:1px solid #dbe4ef;
            border-left:3px solid var(--accent,#2563eb);
            border-radius:9px;
            padding:6px 8px;
            height:64px;
            min-height:64px;
            box-shadow:0 2px 7px rgba(15,23,42,.055);
            transition:box-shadow .15s ease, transform .15s ease;
        }
        .bid-kpi-card:hover {
            box-shadow:0 5px 14px rgba(15,23,42,.10);
            transform:translateY(-1px);
        }
        div[data-testid="stElementContainer"]:has(.bid-kpi-card) {
            min-height:64px !important;
        }
        .bid-kpi-label {
            font-size:9px;
            color:#64748b;
            font-weight:750;
            line-height:1.15;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }
        .bid-kpi-value {
            font-size:15px;
            color:#0f172a;
            font-weight:900;
            margin-top:2px;
            line-height:1.15;
            white-space:nowrap;
        }
        .bid-kpi-note {
            font-size:8.5px;
            color:#64748b;
            margin-top:2px;
            line-height:1.15;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .bid-kpi-blue   { --accent:#2563eb; }
        .bid-kpi-green  { --accent:#16a34a; }
        .bid-kpi-purple { --accent:#7c3aed; }
        .bid-kpi-teal   { --accent:#0f9f8f; }
        .bid-kpi-orange { --accent:#ea580c; }
        .bid-kpi-amber  { --accent:#d97706; }
        .bid-kpi-red    { --accent:#dc2626; }
        .bid-kpi-cyan   { --accent:#0891b2; }
        .bid-kpi-rose   { --accent:#e11d48; }
        .bid-kpi-navy   { --accent:#0f2f63; }

        .bid-trend-mode-label {
            display:flex;
            align-items:center;
            justify-content:flex-end;
            gap:4px;
            min-height:24px;
        }

        /* Compact D / M / Q / Y buttons used only in Bid Trend card */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.bid-trend-marker)
        div[data-testid="stButton"] button {
            min-height:26px !important;
            height:26px !important;
            padding:0 .42rem !important;
            border-radius:6px !important;
            font-size:9.5px !important;
            font-weight:850 !important;
            line-height:1 !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.bid-trend-marker)
        div[data-testid="stButton"] button[kind="primary"] {
            box-shadow:0 2px 6px rgba(37,99,235,.18) !important;
        }

        .bid-report-meta {
            display:block;
            width:100%;
            box-sizing:border-box;
            background:#f8fafc;
            border:1px solid #dbe4ef;
            border-left:3px solid #7c3aed;
            border-radius:7px;
            padding:6px 9px;
            margin:4px 0 6px 0;
            color:#334155;
            font-size:9.5px;
            line-height:1.35;
        }

        .bid-chart-title {
            box-sizing:border-box;
            display:block;
            min-height:22px;
            font-size:11px;
            font-weight:850;
            color:#0f2744;
            line-height:1.35;
            margin:0 0 4px 0;
            padding:3px 0 3px 7px;
            border-left:3px solid #2563eb;
            overflow:visible;
            white-space:nowrap;
        }
        div[data-testid="stPlotlyChart"] {
            border-radius:7px !important;
            overflow:hidden !important;
        }
        div[data-testid="stElementContainer"]:has(.bid-chart-title) {
            min-height:22px !important;
            margin-bottom:0 !important;
            overflow:visible !important;
        }

        h3 {
            font-size:12.5px !important;
            font-weight:850 !important;
            color:#0f2744 !important;
            margin:1px 0 5px 0 !important;
            line-height:1.2 !important;
            border-left:3px solid #17365D;
            padding-left:6px;
        }
        h4 {
            font-size:11px !important;
            font-weight:800 !important;
            color:#334155 !important;
            margin:2px 0 4px 0 !important;
        }
        hr { margin:.35rem 0 !important; }

        /* Data tables: dark-blue outer frame + white header text. */
        div[data-testid="stDataFrame"] {
            border:2px solid #0b2447 !important;
            border-radius:9px !important;
            overflow:hidden !important;
            box-shadow:0 3px 10px rgba(11,36,71,.12) !important;
            --gdg-bg-header:#0b2447;
            --gdg-bg-header-has-focus:#17365D;
            --gdg-text-header:#ffffff;
        }
        div[data-testid="stDataFrame"] * { font-size:10.5px !important; }

        /* Works on Streamlit versions exposing dataframe headers as DOM elements. */
        div[data-testid="stDataFrame"] [role="columnheader"],
        div[data-testid="stDataFrame"] [data-testid="stDataFrameHeaderCell"] {
            background:#0b2447 !important;
            color:#ffffff !important;
            border-color:#17365D !important;
        }
        div[data-testid="stDataFrame"] [role="columnheader"] *,
        div[data-testid="stDataFrame"] [data-testid="stDataFrameHeaderCell"] * {
            color:#ffffff !important;
            fill:#ffffff !important;
        }

        div[data-testid="stDownloadButton"] button,
        div[data-testid="stButton"] button {
            min-height:32px !important;
            padding:.15rem .5rem !important;
            border-radius:7px !important;
            font-size:10px !important;
            font-weight:750 !important;
        }

        @media (max-width: 1000px) {
            div[data-testid="stHorizontalBlock"] {
                flex-wrap:wrap !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    today = date.today()

    if "bidding_from_date" not in st.session_state:
        st.session_state["bidding_from_date"] = today - timedelta(days=7)

    if "bidding_to_date" not in st.session_state:
        st.session_state["bidding_to_date"] = today

    with st.container(border=True):
        title_col, dates_col, run_col = st.columns(
            [4.65, 2.45, 1.35],
            gap="small",
            vertical_alignment="bottom",
        )

        with title_col:
            st.markdown(
                "<div class='bid-header-anchor'></div>"
                "<div class='bid-title'>🚚 Bidding Analysis</div>"
                "<div class='bid-subtitle'>Competition, winner selection, ₹500 gap compliance and LHC hire validation.</div>",
                unsafe_allow_html=True,
            )

        # Keep From / To labels on the LEFT of the date boxes so the header uses
        # horizontal space instead of adding an extra label row above the inputs.
        with dates_col:
            from_lbl, from_box, to_lbl, to_box = st.columns(
                [0.30, 1.00, 0.20, 1.00],
                gap="small",
                vertical_alignment="center",
            )

            with from_lbl:
                st.markdown(
                    "<div class='bid-inline-date-label'>From</div>",
                    unsafe_allow_html=True,
                )

            with from_box:
                from_date = st.date_input(
                    "From",
                    value=st.session_state["bidding_from_date"],
                    format="DD/MM/YYYY",
                    key="bidding_from_date_input",
                    label_visibility="collapsed",
                )

            with to_lbl:
                st.markdown(
                    "<div class='bid-inline-date-label'>To</div>",
                    unsafe_allow_html=True,
                )

            with to_box:
                to_date = st.date_input(
                    "To",
                    value=st.session_state["bidding_to_date"],
                    format="DD/MM/YYYY",
                    key="bidding_to_date_input",
                    label_visibility="collapsed",
                )

        with run_col:
            load_clicked = st.button(
                "↻ Load / Refresh",
                type="primary",
                use_container_width=True,
                key="bidding_load_refresh",
            )

    if from_date > to_date:
        st.error("From Date cannot be greater than To Date.")
        return

    cached_raw = st.session_state.get("bidding_raw_data")
    needs_schema_refresh = (
        isinstance(cached_raw, pd.DataFrame)
        and not cached_raw.empty
        and "BIDDER_VENDOR_LIST" not in cached_raw.columns
    )

    should_load = (
        load_clicked
        or "bidding_raw_data" not in st.session_state
        or needs_schema_refresh
    )

    if should_load:
        st.session_state["bidding_from_date"] = from_date
        st.session_state["bidding_to_date"] = to_date

        try:
            with st.spinner("Loading bidding data..."):
                if load_clicked or needs_schema_refresh:
                    load_bidding_data.clear()

                raw_df = load_bidding_data(from_date, to_date)
                st.session_state["bidding_raw_data"] = raw_df

        except Exception as exc:
            st.error("Unable to load bidding data from SQL Server.")
            st.exception(exc)
            return

    raw_df = st.session_state.get("bidding_raw_data", pd.DataFrame())

    # Re-run lightweight derived calculations on cached data as well.
    # This ensures newly added control fields are available immediately
    # after a code deployment without forcing users to reload SQL first.
    if raw_df is not None and not raw_df.empty:
        raw_df = prepare_bidding_data(raw_df)
        st.session_state["bidding_raw_data"] = raw_df

    if raw_df is None or raw_df.empty:
        st.warning("No bidding data found for the selected date range.")
        return

    st.markdown(
        f"""
        <div class="bid-period-line">
            Loaded Period: {st.session_state['bidding_from_date'].strftime('%d/%m/%Y')}
            to {st.session_state['bidding_to_date'].strftime('%d/%m/%Y')}
            &nbsp;|&nbsp; {raw_df['BIDID'].nunique():,} unique bids
        </div>
        """,
        unsafe_allow_html=True,
    )

    filtered_df = apply_dashboard_filters(raw_df)

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    render_kpis(filtered_df)
    render_charts(filtered_df)
    render_vendor_performance(filtered_df)
    render_exceptions(filtered_df)
    render_detail_table(filtered_df)

