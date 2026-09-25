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

    # --------------------------------------------------------
    # LHC CONTROL / PENDING AGEING
    # --------------------------------------------------------
    is_winner_flag = _clean_text_series(df["ISWINNER"]).str.upper().eq("Y")
    has_winner_name = _clean_text_series(df["WINNER_NAME"]).ne("")
    has_final_rate = df["FINALRATE"].notna()

    df["HAS_WINNER"] = is_winner_flag | has_winner_name | has_final_rate

    lhc_no_text = _clean_text_series(df["LHCNO"])

    df["LHC_STATUS"] = "No Winner"
    df.loc[df["HAS_WINNER"] & lhc_no_text.ne(""), "LHC_STATUS"] = "LHC Created"
    df.loc[df["HAS_WINNER"] & lhc_no_text.eq(""), "LHC_STATUS"] = "Winner - LHC Pending"

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
                ["LHC Created", "Winner - LHC Pending", "No Winner"],
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
    manual_bids = int(df.loc[df["WINNER_MODE"].eq("Manual"), "BIDID"].nunique())
    single_bidder = int(df.loc[df["BIDDER_COUNT"].eq(1), "BIDID"].nunique())
    gap_violations = int(df.loc[df["GAP_STATUS"].eq("Violation"), "BIDID"].nunique())
    avg_bidders = df.loc[df["BIDDER_COUNT"].gt(0), "BIDDER_COUNT"].mean()

    approved_pct = (approved_bids / total_bids * 100) if total_bids else 0
    query_pct = (query_bids / total_bids * 100) if total_bids else 0
    l1_pct = (l1_bids / total_bids * 100) if total_bids else 0
    manual_pct = (manual_bids / total_bids * 100) if total_bids else 0
    single_pct = (single_bidder / total_bids * 100) if total_bids else 0
    gap_pct = (gap_violations / total_bids * 100) if total_bids else 0

    k1, k2, k3, k4, k5, k6, k7, k8 = st.columns(8, gap="small")

    _kpi_card(k1, "📦 Total Bids", f"{total_bids:,}", "Filtered unique bids", "blue")
    _kpi_card(k2, "✅ Approved", f"{approved_bids:,}", f"{approved_pct:.1f}% of bids", "green")
    _kpi_card(k3, "💬 Query Bids", f"{query_bids:,}", f"{query_pct:.1f}% of bids", "purple")
    _kpi_card(k4, "🥇 L-1 Selected", f"{l1_bids:,}", f"{l1_pct:.1f}% of bids", "teal")
    _kpi_card(k5, "✍️ Manual", f"{manual_bids:,}", f"{manual_pct:.1f}% of bids", "orange")
    _kpi_card(k6, "👤 Single Bidder", f"{single_bidder:,}", f"{single_pct:.1f}% of bids", "amber")
    _kpi_card(k7, "⚠️ Gap Violations", f"{gap_violations:,}", f"{gap_pct:.1f}% of bids", "red")
    _kpi_card(
        k8,
        "👥 Avg Bidders",
        "-" if pd.isna(avg_bidders) else f"{avg_bidders:.2f}",
        "Per participating bid",
        "cyan",
    )

    # LHC operational control KPIs
    winner_bids = int(df.loc[df["HAS_WINNER"], "BIDID"].nunique())
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
    lhc_pending_pct = (lhc_pending / winner_bids * 100) if winner_bids else 0

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
        f"{lhc_pending_pct:.1f}% of winner bids",
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
            color="#334155",
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#dbe4ef",
        tickfont=dict(size=9),
        title=None,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#eef2f7",
        zeroline=False,
        tickfont=dict(size=9),
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
            textfont=dict(size=10, color="#0f172a"),
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
            textfont=dict(size=9, color="#0f172a"),
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
                color="#0f172a",
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
        tickfont=dict(size=9),
    )

    return fig


def render_charts(df):
    st.markdown("### Management Analysis")

    left, right = st.columns(2, gap="small")

    with left:
        branch_data = (
            df.groupby("BRANCH", dropna=False)["BIDID"]
            .nunique()
            .sort_values(ascending=False)
            .head(15)
            .rename("Bids")
            .reset_index()
        )

        if not branch_data.empty:
            branch_fig = _bar_chart_with_values(
                branch_data["BRANCH"],
                branch_data["Bids"],
                height=270,
                rotate_x=-35,
            )
            _render_chart_card("Bids by Branch", branch_fig)
        else:
            with st.container(border=True):
                st.markdown("<div class='bid-chart-title'>Bids by Branch</div>", unsafe_allow_html=True)
                st.info("No branch data available.")

    with right:
        winner_data = (
            df.groupby("WINNER_MODE")["BIDID"]
            .nunique()
            .sort_values(ascending=False)
            .rename("Bids")
            .reset_index()
        )

        if not winner_data.empty:
            winner_fig = _bar_chart_with_values(
                winner_data["WINNER_MODE"],
                winner_data["Bids"],
                height=270,
            )
            _render_chart_card("Winner Selection", winner_fig)
        else:
            with st.container(border=True):
                st.markdown("<div class='bid-chart-title'>Winner Selection</div>", unsafe_allow_html=True)
                st.info("No winner data available.")

    left, right = st.columns(2, gap="small")

    with left:
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

        participation_fig = _bar_chart_with_values(
            participation["BIDDER_BUCKET"],
            participation["Bids"],
            height=245,
        )
        _render_chart_card("Bidder Participation", participation_fig)

    with right:
        gap_data = (
            df.groupby("GAP_STATUS")["BIDID"]
            .nunique()
            .reindex(["OK", "Violation", "Not Comparable"])
            .fillna(0)
            .astype(int)
            .rename("Bids")
            .reset_index()
        )

        gap_fig = _bar_chart_with_values(
            gap_data["GAP_STATUS"],
            gap_data["Bids"],
            height=245,
        )
        _render_chart_card("₹500 Gap Compliance", gap_fig)

    left, right = st.columns(2, gap="small")

    with left:
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
                height=255,
            )
            _render_chart_card(
                "Winner → LHC Pending Ageing  •  Count + % of Pending",
                ageing_fig,
            )
        else:
            with st.container(border=True):
                st.markdown(
                    "<div class='bid-chart-title'>Winner → LHC Pending Ageing</div>",
                    unsafe_allow_html=True,
                )
                st.info("No winner bids are pending for LHC.")

    with right:
        trend_df = df.dropna(subset=["BIDOPENDT"]).copy()

        if not trend_df.empty:
            trend_df["BID_DATE"] = trend_df["BIDOPENDT"].dt.date
            daily = (
                trend_df.groupby("BID_DATE")["BIDID"]
                .nunique()
                .rename("Bids")
                .reset_index()
            )

            daily["DATE_LABEL"] = pd.to_datetime(daily["BID_DATE"]).dt.strftime("%d %b")

            daily_fig = _line_chart_with_values(
                daily["DATE_LABEL"],
                daily["Bids"],
                height=245,
            )
            _render_chart_card("Daily Bid Trend", daily_fig)
        else:
            with st.container(border=True):
                st.markdown(
                    "<div class='bid-chart-title'>Daily Bid Trend</div>",
                    unsafe_allow_html=True,
                )
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
            "⏳ Winner → LHC Pending",
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

        /* Compact header date labels */
        .bid-header-anchor + div label[data-testid="stWidgetLabel"] p,
        div[data-testid="stHorizontalBlock"]:has(.bid-header-anchor)
        label[data-testid="stWidgetLabel"] p {
            font-size:9px !important;
            margin-bottom:1px !important;
            line-height:1.05 !important;
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

        div[data-testid="stDataFrame"] {
            border:1px solid #cbd5e1 !important;
            border-radius:9px !important;
            overflow:hidden !important;
            box-shadow:0 3px 10px rgba(15,23,42,.06) !important;
        }
        div[data-testid="stDataFrame"] * { font-size:10.5px !important; }

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
        title_col, d1, d2, run_col = st.columns(
            [4.4, 0.95, 0.95, 1.35],
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

        with d1:
            from_date = st.date_input(
                "From",
                value=st.session_state["bidding_from_date"],
                format="DD/MM/YYYY",
                key="bidding_from_date_input",
            )

        with d2:
            to_date = st.date_input(
                "To",
                value=st.session_state["bidding_to_date"],
                format="DD/MM/YYYY",
                key="bidding_to_date_input",
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
    render_exceptions(filtered_df)
    render_detail_table(filtered_df)

