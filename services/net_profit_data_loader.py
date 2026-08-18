import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.pnl_data_loader import load_pnl_both_views
from services.net_profit_branch_mast import load_net_profit_branch_mast


# ============================================================
# NET PROFIT DATA LOADER
#
# Existing files are NOT modified.
#
# Logic:
#   Branch Operational P&L
#       = Origin P&L + Destination P&L
#
#   Branch Net Profit
#       = Branch Operational P&L - Branch Overhead
#
# Overhead:
#   Salary + Godown Rent + Voucher Overhead + Claim + Booking 6% + Destination 5%
# ============================================================

_CACHE_TTL_SECONDS = 24 * 60 * 60


_OVERHEAD_QUERY = text("""
DECLARE @FROMDATE DATE = :from_date;
DECLARE @TODATE   DATE = :to_date;

/* ================= SALARY ================= */

IF OBJECT_ID('tempdb..#SALARY') IS NOT NULL
    DROP TABLE #SALARY;

SELECT
    SS.BRANCHCODE,
    SS.[YEAR],
    SS.[MONTHNO],
    SUM(SS.NETAMT) AS NETAMT
INTO #SALARY
FROM
(
    SELECT
        SD.BRANCHCODE,
        YEAR(SD.FROMDT) AS [YEAR],
        MONTH(SD.FROMDT) AS [MONTHNO],

        CAST(
            SUM(SD.EAMOUNT)
            +
            IIF(
                ESI.CNTR = 0,
                0,
                SUM(SD.EAMOUNT - SD.PFAMOUNT) * 3.25 / 100
            )
        AS NUMERIC(12,2)) AS NETAMT

    FROM VIEWSALARYFORBRANCHPERFORMANCE SD

    CROSS APPLY
    (
        SELECT COUNT(*) AS CNTR
        FROM VIEWSALARY D
        WHERE D.BRANCHCODE = SD.BRANCHCODE
          AND D.EMPLOYEEID = SD.EMPLOYEEID
          AND D.FROMDT BETWEEN @FROMDATE AND @TODATE
          AND D.SALARYVNO IS NOT NULL
          AND D.SALARYCATEGORY = 'S'
          AND D.SALARYHEADID = 9
    ) ESI

    WHERE SD.FROMDT BETWEEN @FROMDATE AND @TODATE
      AND SD.SALARYVNO IS NOT NULL
      AND SD.SALARYCATEGORY = 'S'

    GROUP BY
        SD.BRANCHCODE,
        YEAR(SD.FROMDT),
        MONTH(SD.FROMDT),
        ESI.CNTR

) SS

GROUP BY
    SS.BRANCHCODE,
    SS.[YEAR],
    SS.[MONTHNO];


/* ================= GODOWN RENT ================= */

IF OBJECT_ID('tempdb..#GODOWN') IS NOT NULL
    DROP TABLE #GODOWN;

SELECT
    H.BRANCHCODE,
    YEAR(H.FROMDT) AS [YEAR],
    MONTH(H.FROMDT) AS [MONTHNO],
    ISNULL(SUM(D.AMOUNT), 0) AS NETAMT
INTO #GODOWN

FROM PURCHASEMRNDETAIL D WITH (NOLOCK)

INNER JOIN PURCHASEMRNHEAD H WITH (NOLOCK)
    ON H.MRNID = D.MRNID

WHERE D.ITEMCODE = '30'
  AND H.CANCEL <> 'Y'
  AND H.VNO IS NOT NULL
  AND H.FROMDT BETWEEN @FROMDATE AND @TODATE
  AND H.TODT BETWEEN @FROMDATE AND @TODATE

GROUP BY
    H.BRANCHCODE,
    YEAR(H.FROMDT),
    MONTH(H.FROMDT);


/* ================= VOUCHER OVERHEAD EXPENSE ================= */

IF OBJECT_ID('tempdb..#VOUCHEREXP') IS NOT NULL
    DROP TABLE #VOUCHEREXP;

SELECT
    VM.BRANCHCODE,
    YEAR(VM.VDATE) AS [YEAR],
    MONTH(VM.VDATE) AS [MONTHNO],
    ISNULL(SUM(VM.DRAMOUNT - VM.CRAMOUNT), 0) AS NETAMT
INTO #VOUCHEREXP

FROM VIEWVOUCHER VM WITH (NOLOCK)

INNER JOIN VIEWLEDGER L
    ON L.LEDCODE = VM.LEDCODE

WHERE VM.VDATE BETWEEN @FROMDATE AND @TODATE
  AND L.MAINGRP = 'AM203'
  AND L.LEDCODE <> '0000001172'

GROUP BY
    VM.BRANCHCODE,
    YEAR(VM.VDATE),
    MONTH(VM.VDATE);


/* ================= CLAIM ================= */

IF OBJECT_ID('tempdb..#CLAIM') IS NOT NULL
    DROP TABLE #CLAIM;

SELECT
    BRANCHCODE,
    YEAR(VDATE) AS [YEAR],
    MONTH(VDATE) AS [MONTHNO],
    ISNULL(SUM(DRAMOUNT - CRAMOUNT), 0) AS NETAMT
INTO #CLAIM

FROM VIEWVOUCHER WITH (NOLOCK)

WHERE VDATE BETWEEN @FROMDATE AND @TODATE
  AND LEDCODE = '0000001289'

GROUP BY
    BRANCHCODE,
    YEAR(VDATE),
    MONTH(VDATE);


/* ================= BOOKING 6% ================= */

IF OBJECT_ID('tempdb..#BOOKING6') IS NOT NULL
    DROP TABLE #BOOKING6;

SELECT
    CN.ORGCODE AS BRANCHCODE,
    YEAR(CN.GRDT) AS [YEAR],
    MONTH(CN.GRDT) AS [MONTHNO],

    ROUND(
        ISNULL(SUM(CN.tamount-cn.servicetax), 0) * 6 / 100,
        2
    ) AS NETAMT

INTO #BOOKING6

FROM CNMT CN WITH (NOLOCK)

WHERE CN.GRDT BETWEEN @FROMDATE AND @TODATE
  AND CN.GRTYPE <> 'N'

GROUP BY
    CN.ORGCODE,
    YEAR(CN.GRDT),
    MONTH(CN.GRDT);


/* ================= DESTINATION 5% ================= */

IF OBJECT_ID('tempdb..#DESTINATION5') IS NOT NULL
    DROP TABLE #DESTINATION5;

SELECT

    CASE
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '704' THEN '602'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '705' THEN '601'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '708' THEN '603'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '712' THEN '171'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '709' THEN '607'
        ELSE COALESCE(MRG.STNCODE, DEST.STNCODE)
    END AS BRANCHCODE,

    YEAR(CN.GRDT) AS [YEAR],
    MONTH(CN.GRDT) AS [MONTHNO],

    ROUND(
        ISNULL(SUM(CN.tamount-cn.servicetax), 0) * 5 / 100,
        2
    ) AS NETAMT

INTO #DESTINATION5

FROM CNMT CN WITH (NOLOCK)

INNER JOIN STATIONMAST DEST
    ON DEST.STNCODE = CN.DESTCODE

LEFT JOIN STATIONMAST MRG
    ON MRG.STNCODE = DEST.MERGESTNCODE

WHERE CN.GRDT BETWEEN @FROMDATE AND @TODATE
  AND CN.GRTYPE <> 'N'

GROUP BY

    CASE
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '704' THEN '602'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '705' THEN '601'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '708' THEN '603'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '712' THEN '171'
        WHEN COALESCE(MRG.STNCODE, DEST.STNCODE) = '709' THEN '607'
        ELSE COALESCE(MRG.STNCODE, DEST.STNCODE)
    END,

    YEAR(CN.GRDT),
    MONTH(CN.GRDT);


/* ================= MONTH / BRANCH LIST ================= */

IF OBJECT_ID('tempdb..#MONTHS') IS NOT NULL
    DROP TABLE #MONTHS;

SELECT DISTINCT
    BRANCHCODE,
    [YEAR],
    [MONTHNO]
INTO #MONTHS

FROM
(
    SELECT BRANCHCODE, [YEAR], [MONTHNO]
    FROM #SALARY

    UNION

    SELECT BRANCHCODE, [YEAR], [MONTHNO]
    FROM #GODOWN

    UNION

    SELECT BRANCHCODE, [YEAR], [MONTHNO]
    FROM #VOUCHEREXP

    UNION

    SELECT BRANCHCODE, [YEAR], [MONTHNO]
    FROM #CLAIM

    UNION

    SELECT BRANCHCODE, [YEAR], [MONTHNO]
    FROM #BOOKING6

    UNION

    SELECT BRANCHCODE, [YEAR], [MONTHNO]
    FROM #DESTINATION5

) M;


/* ================= FINAL OUTPUT ================= */

SELECT
    STN.STNCODE AS BRANCHCODE,
    STN.STNNAME AS BRANCH,
    M.[YEAR],
    M.[MONTHNO] AS [MONTH NO],
    DATENAME(
        MONTH,
        DATEFROMPARTS(M.[YEAR], M.[MONTHNO], 1)
    ) AS [MONTH],

    ROUND(
        ISNULL(SAL.NETAMT, 0),
        2
    ) AS [SALARY],

    ROUND(
        ISNULL(GOD.NETAMT, 0),
        2
    ) AS [GODOWN RENT],

    ROUND(
        ISNULL(VEXP.NETAMT, 0),
        2
    ) AS [OVERHEAD EXPENSE],

    ROUND(
        ISNULL(CL.NETAMT, 0),
        2
    ) AS [CLAIM],

    ROUND(
        ISNULL(BK6.NETAMT, 0),
        2
    ) AS [BOOKING 6%],

    ROUND(
        ISNULL(DEST5.NETAMT, 0),
        2
    ) AS [DESTINATION 5%],

    ROUND(
          ISNULL(SAL.NETAMT, 0)
        + ISNULL(GOD.NETAMT, 0)
        + ISNULL(VEXP.NETAMT, 0)
        + ISNULL(CL.NETAMT, 0)
        + ISNULL(BK6.NETAMT, 0)
        + ISNULL(DEST5.NETAMT, 0),
        2
    ) AS [TOTAL EXPENSE]

FROM #MONTHS M

INNER JOIN STATIONMAST STN
    ON STN.STNCODE = M.BRANCHCODE

LEFT JOIN #SALARY SAL
    ON SAL.BRANCHCODE = M.BRANCHCODE
   AND SAL.[YEAR] = M.[YEAR]
   AND SAL.[MONTHNO] = M.[MONTHNO]

LEFT JOIN #GODOWN GOD
    ON GOD.BRANCHCODE = M.BRANCHCODE
   AND GOD.[YEAR] = M.[YEAR]
   AND GOD.[MONTHNO] = M.[MONTHNO]

LEFT JOIN #VOUCHEREXP VEXP
    ON VEXP.BRANCHCODE = M.BRANCHCODE
   AND VEXP.[YEAR] = M.[YEAR]
   AND VEXP.[MONTHNO] = M.[MONTHNO]

LEFT JOIN #CLAIM CL
    ON CL.BRANCHCODE = M.BRANCHCODE
   AND CL.[YEAR] = M.[YEAR]
   AND CL.[MONTHNO] = M.[MONTHNO]

LEFT JOIN #BOOKING6 BK6
    ON BK6.BRANCHCODE = M.BRANCHCODE
   AND BK6.[YEAR] = M.[YEAR]
   AND BK6.[MONTHNO] = M.[MONTHNO]

LEFT JOIN #DESTINATION5 DEST5
    ON DEST5.BRANCHCODE = M.BRANCHCODE
   AND DEST5.[YEAR] = M.[YEAR]
   AND DEST5.[MONTHNO] = M.[MONTHNO]

ORDER BY
    STN.STNNAME,
    M.[YEAR],
    M.[MONTHNO];
""")


# ============================================================
# GENERIC HELPERS
# ============================================================

def _normalise_name(value):
    return str(value).strip().replace("_", "").replace(" ", "").casefold()


def _find_column(df, candidates):
    if df is None:
        return None

    mapping = {
        _normalise_name(column): column
        for column in df.columns
    }

    for candidate in candidates:
        found = mapping.get(_normalise_name(candidate))
        if found is not None:
            return found

    return None


def _clean_code(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _first_existing_metadata(df):
    """
    Return available organisation metadata.
    This is intentionally optional so the Net Profit loader does not fail
    merely because a stored procedure returns fewer hierarchy columns.
    """
    aliases = {
        "COMPNAME": ["COMPNAME", "company", "companyname"],
        "zone": ["zone", "zonename"],
        "circle": ["circle", "circlename", "hubname"],
    }

    result = {}

    for target, candidates in aliases.items():
        column = _find_column(df, candidates)
        if column is not None:
            result[target] = column

    return result


# ============================================================
# VIEW-SPECIFIC BRANCH IDENTIFICATION
# ============================================================

def _get_branch_identity_column(df, view_type):
    """
    The current booking stored procedure returns a display branch column
    ('branch') rather than a dedicated ORIGINBRANCHCODE / DESTBRANCHCODE.

    For Net Profit we therefore use the branch represented by the selected
    view as the operational branch identity:

      ViewType=ORIGIN      -> df['branch'] is the booking/origin branch
      ViewType=DESTINATION -> df['branch'] is the delivery/destination branch

    Dedicated branch-code columns are still preferred if the SP starts
    returning them in future.
    """
    view = str(view_type).strip().upper()

    if view == "ORIGIN":
        candidates = [
            "ORIGINBRANCHCODE",
            "origin_branch_code",
            "BOOKINGBRANCHCODE",
            "booking_branch_code",
            "branch",
            "BRANCH",
            "branchname",
            "BRANCHCODE",
            "branch_code",
        ]
    elif view == "DESTINATION":
        candidates = [
            "DESTBRANCHCODE",
            "DESTINATIONBRANCHCODE",
            "destination_branch_code",
            "DELIVERYBRANCHCODE",
            "delivery_branch_code",
            "branch",
            "BRANCH",
            "branchname",
            "BRANCHCODE",
            "branch_code",
        ]
    else:
        raise ValueError(f"Unsupported view type: {view_type!r}")

    branch_col = _find_column(df, candidates)

    if branch_col is None:
        raise ValueError(
            f"Could not identify {view.title()} branch. "
            f"Expected one of {candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    return branch_col


def _normalise_branch_key(series):
    """Normalised branch-name/code key used only for joins."""
    return (
        series.astype(str)
        .str.strip()
        .str.casefold()
        .str.replace(r"\s+", " ", regex=True)
    )

def _get_date_column(df):
    date_col = _find_column(
        df,
        [
            "GRDT",
            "grdt",
            "GRDATE",
            "GR_DATE",
            "BOOKINGDATE",
            "booking_date",
            "DATE",
        ],
    )

    if date_col is None:
        raise ValueError(
            "Could not identify GR/booking date required for month-wise "
            f"Net Profit. Available columns: {list(df.columns)}"
        )

    return date_col


# ============================================================
# PREPARE ORIGIN / DESTINATION BRANCH-MONTH P&L
# ============================================================

def _aggregate_view_pnl(df, view_type):
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "BRANCH_KEY",
                "BRANCH",
                "YEAR",
                "MONTHNO",
                "BUSINESS",
                "TOTAL_INCOME",
                "DIRECT_EXPENSE",
                "PNL",
            ]
        )

    out = df.copy()

    branch_col = _get_branch_identity_column(out, view_type)
    date_col = _get_date_column(out)

    required_metrics = {
        "REVENUE": ["REVENUE", "revenue", "business"],
        "EXPENSE": ["EXPENSE", "expense", "cost"],
        "PNL": ["PNL", "pnl", "profitloss", "profit_loss"],
    }

    rename_map = {}

    for target, candidates in required_metrics.items():
        source = _find_column(out, candidates)
        if source is None:
            raise ValueError(
                f"{view_type} P&L data is missing {target}. "
                f"Available columns: {list(out.columns)}"
            )
        if source != target:
            rename_map[source] = target

    out = out.rename(columns=rename_map)

    out["_BRANCH"] = (
        out[branch_col]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
    )
    out["_BRANCH_KEY"] = _normalise_branch_key(out["_BRANCH"])

    dt = pd.to_datetime(out[date_col], errors="coerce")
    out["_YEAR"] = dt.dt.year
    out["_MONTHNO"] = dt.dt.month

    for column in ["REVENUE", "EXPENSE", "PNL"]:
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)

    # Business rule for this Net Profit dashboard:
    # TOTAL_INCOME is the P&L amount itself.
    out["TOTAL_INCOME"] = out["PNL"]

    out = out[
        out["_BRANCH_KEY"].notna()
        & out["_BRANCH_KEY"].ne("")
        & out["_BRANCH_KEY"].ne("nan")
        & out["_YEAR"].notna()
        & out["_MONTHNO"].notna()
    ].copy()

    # Keep optional hierarchy metadata.
    metadata = _first_existing_metadata(out)

    agg_spec = {
        "BUSINESS": ("REVENUE", "sum"),
        "TOTAL_INCOME": ("TOTAL_INCOME", "sum"),
        "DIRECT_EXPENSE": ("EXPENSE", "sum"),
        "PNL": ("PNL", "sum"),
    }

    for target, source in metadata.items():
        agg_spec[target] = (source, "first")

    summary = (
        out.groupby(
            ["_BRANCH_KEY", "_BRANCH", "_YEAR", "_MONTHNO"],
            as_index=False,
            dropna=False,
        )
        .agg(**agg_spec)
        .rename(
            columns={
                "_BRANCH_KEY": "BRANCH_KEY",
                "_BRANCH": "BRANCH",
                "_YEAR": "YEAR",
                "_MONTHNO": "MONTHNO",
            }
        )
    )

    summary["YEAR"] = pd.to_numeric(summary["YEAR"], errors="coerce")
    summary["MONTHNO"] = pd.to_numeric(summary["MONTHNO"], errors="coerce")

    return summary


# ============================================================
# OVERHEAD
# ============================================================

def _fetch_overhead_data(start_date, end_date):
    started = time.perf_counter()
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            _OVERHEAD_QUERY,
            conn,
            params={
                "from_date": str(start_date),
                "to_date": str(end_date),
            },
        )

    print(
        f"[Net Profit Overhead] {start_date} to {end_date} | "
        f"rows={len(df):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )

    return df


def _prepare_overhead(df):
    expected = [
        "BRANCHCODE",
        "BRANCH",
        "YEAR",
        "MONTHNO",
        "MONTH",
        "SALARY",
        "GODOWN RENT",
        "OVERHEAD EXPENSE",
        "CLAIM",
        "BOOKING 6%",
        "DESTINATION 5%",
        "TOTAL EXPENSE",
    ]

    if df is None or df.empty:
        return pd.DataFrame(columns=expected)

    out = df.copy()

    aliases = {
        "BRANCHCODE": ["BRANCHCODE", "branch_code"],
        "BRANCH": ["BRANCH", "branch", "branchname"],
        "YEAR": ["YEAR"],
        "MONTHNO": ["MONTHNO", "MONTH NO"],
        "MONTH": ["MONTH"],
        "SALARY": ["SALARY"],
        "GODOWN RENT": ["GODOWN RENT", "GODOWN_RENT"],
        "OVERHEAD EXPENSE": ["OVERHEAD EXPENSE", "OVERHEAD_EXPENSE"],
        "CLAIM": ["CLAIM"],
        "BOOKING 6%": ["BOOKING 6%", "BOOKING_6", "BOOKING6"],
        "DESTINATION 5%": ["DESTINATION 5%", "DESTINATION_5", "DESTINATION5"],
        "TOTAL EXPENSE": ["TOTAL EXPENSE", "TOTAL_EXPENSE"],
    }

    rename_map = {}

    for target, candidates in aliases.items():
        source = _find_column(out, candidates)
        if source is not None and source != target:
            rename_map[source] = target

    out = out.rename(columns=rename_map)

    required = ["BRANCHCODE", "YEAR", "MONTHNO", "TOTAL EXPENSE"]
    missing = [column for column in required if column not in out.columns]

    if missing:
        raise ValueError(
            f"Overhead query is missing columns: {missing}. "
            f"Available columns: {list(out.columns)}"
        )

    if "BRANCH" not in out.columns:
        out["BRANCH"] = out["BRANCHCODE"]

    if "MONTH" not in out.columns:
        out["MONTH"] = ""

    out["BRANCHCODE"] = _clean_code(out["BRANCHCODE"])
    out["BRANCH"] = (
        out["BRANCH"]
        .fillna(out["BRANCHCODE"])
        .astype(str)
        .str.strip()
    )
    out["BRANCH_KEY"] = _normalise_branch_key(out["BRANCH"])
    out["YEAR"] = pd.to_numeric(out["YEAR"], errors="coerce")
    out["MONTHNO"] = pd.to_numeric(out["MONTHNO"], errors="coerce")

    for column in [
        "SALARY",
        "GODOWN RENT",
        "OVERHEAD EXPENSE",
        "CLAIM",
        "BOOKING 6%",
        "DESTINATION 5%",
        "TOTAL EXPENSE",
    ]:
        if column not in out.columns:
            out[column] = 0.0

        out[column] = pd.to_numeric(
            out[column],
            errors="coerce",
        ).fillna(0.0)

    return out[["BRANCH_KEY"] + expected].copy()


# ============================================================
# COMBINE ORIGIN + DESTINATION + OVERHEAD
# ============================================================

def _prefix_metrics(df, prefix):
    keys = {"BRANCH_KEY", "BRANCH", "YEAR", "MONTHNO"}
    rename_map = {
        column: f"{prefix}_{column}"
        for column in df.columns
        if column not in keys
    }
    return df.rename(columns=rename_map)


def _coalesce_metadata(final, field):
    left = f"ORIGIN_{field}"
    right = f"DESTINATION_{field}"

    if left in final.columns and right in final.columns:
        return (
            final[left]
            .replace("", pd.NA)
            .fillna(final[right])
            .fillna("Unknown")
        )

    if left in final.columns:
        return final[left].fillna("Unknown")

    if right in final.columns:
        return final[right].fillna("Unknown")

    return pd.Series("Unknown", index=final.index)


def _build_net_profit(origin_df, destination_df, overhead_df):
    origin = _aggregate_view_pnl(origin_df, "ORIGIN")
    destination = _aggregate_view_pnl(destination_df, "DESTINATION")
    overhead = _prepare_overhead(overhead_df)

    # Branch Master is the source of truth. Every branch/agency must remain
    # available even when it has no Origin P&L, no Destination P&L, or no overhead.
    branch_master = load_net_profit_branch_mast()
    if branch_master is None or branch_master.empty:
        return pd.DataFrame()

    master = branch_master.copy()
    branch_col = _find_column(master, ["BRANCH", "branch", "branchname"])
    code_col = _find_column(master, ["CODE", "BRANCHCODE", "branch_code"])
    zone_col = _find_column(master, ["ZONE", "zone", "zonename"])
    circle_col = _find_column(master, ["CIRCLE", "circle", "circlename", "hubname"])
    company_col = _find_column(master, ["COMPNAME", "company", "companyname"])

    if branch_col is None:
        raise ValueError(
            f"Net Profit Branch Master must contain BRANCH. Available columns: {list(master.columns)}"
        )

    master["BRANCH"] = master[branch_col].fillna("").astype(str).str.strip()
    master["BRANCH_KEY"] = _normalise_branch_key(master["BRANCH"])
    master["BRANCHCODE"] = (
        _clean_code(master[code_col]) if code_col is not None else ""
    )
    master["zone"] = master[zone_col].fillna("Unknown") if zone_col is not None else "Unknown"
    master["circle"] = master[circle_col].fillna("Unknown") if circle_col is not None else "Unknown"
    master["COMPNAME"] = master[company_col].fillna("Unknown") if company_col is not None else "Unknown"
    master = master[
        master["BRANCH_KEY"].notna()
        & master["BRANCH_KEY"].ne("")
        & master["BRANCH_KEY"].ne("nan")
    ][["BRANCH_KEY", "BRANCHCODE", "BRANCH", "zone", "circle", "COMPNAME"]].drop_duplicates("BRANCH_KEY")

    # Build branch-month skeleton from the selected reporting period present in
    # Origin, Destination, or Overhead. If a month has only overhead, it still survives.
    month_parts = []
    for source in [origin, destination, overhead]:
        if source is not None and not source.empty and {"YEAR", "MONTHNO"}.issubset(source.columns):
            month_parts.append(source[["YEAR", "MONTHNO"]])

    if not month_parts:
        return pd.DataFrame()

    months = (
        pd.concat(month_parts, ignore_index=True)
        .dropna(subset=["YEAR", "MONTHNO"])
        .drop_duplicates()
    )
    months["YEAR"] = pd.to_numeric(months["YEAR"], errors="coerce")
    months["MONTHNO"] = pd.to_numeric(months["MONTHNO"], errors="coerce")
    months = months.dropna(subset=["YEAR", "MONTHNO"])

    master["_K"] = 1
    months["_K"] = 1
    base = master.merge(months, on="_K", how="inner").drop(columns="_K")

    keys = ["BRANCH_KEY", "YEAR", "MONTHNO"]

    origin = origin.rename(columns={"BRANCH": "ORIGIN_BRANCH"})
    destination = destination.rename(columns={"BRANCH": "DESTINATION_BRANCH"})

    origin = _prefix_metrics(origin, "ORIGIN")
    destination = _prefix_metrics(destination, "DESTINATION")

    combined = base.merge(
        origin,
        on=keys,
        how="left",
        validate="one_to_one",
    ).merge(
        destination,
        on=keys,
        how="left",
        validate="one_to_one",
    )

    for column in combined.columns:
        if column in keys:
            continue
        if any(
            column.endswith(suffix)
            for suffix in [
                "_BUSINESS",
                "_TOTAL_INCOME",
                "_DIRECT_EXPENSE",
                "_PNL",
            ]
        ):
            combined[column] = pd.to_numeric(
                combined[column],
                errors="coerce",
            ).fillna(0.0)

    for prefix in ["ORIGIN", "DESTINATION"]:
        for metric in ["BUSINESS", "TOTAL_INCOME", "DIRECT_EXPENSE", "PNL"]:
            column = f"{prefix}_{metric}"
            if column not in combined.columns:
                combined[column] = 0.0

    # Keep organisation metadata from Branch Master as the primary source.
    for field in ["COMPNAME", "zone", "circle"]:
        if field not in combined.columns:
            combined[field] = _coalesce_metadata(combined, field)
        else:
            fallback = _coalesce_metadata(combined, field)
            combined[field] = (
                combined[field]
                .replace("", pd.NA)
                .fillna(fallback)
                .fillna("Unknown")
            )

    combined["BUSINESS"] = (
        combined["ORIGIN_BUSINESS"]
        + combined["DESTINATION_BUSINESS"]
    )

    combined["TOTAL_INCOME"] = (
        combined["ORIGIN_TOTAL_INCOME"]
        + combined["DESTINATION_TOTAL_INCOME"]
    )

    combined["DIRECT_EXPENSE"] = (
        combined["ORIGIN_DIRECT_EXPENSE"]
        + combined["DESTINATION_DIRECT_EXPENSE"]
    )

    combined["COMBINED_PNL"] = (
        combined["ORIGIN_PNL"]
        + combined["DESTINATION_PNL"]
    )

    overhead_merge = overhead[
        [
            "BRANCH_KEY",
            "BRANCHCODE",
            "BRANCH",
            "YEAR",
            "MONTHNO",
            "SALARY",
            "GODOWN RENT",
            "OVERHEAD EXPENSE",
            "CLAIM",
            "BOOKING 6%",
            "DESTINATION 5%",
            "TOTAL EXPENSE",
        ]
    ].copy()

    final = combined.merge(
        overhead_merge.drop(columns=["BRANCHCODE", "BRANCH"], errors="ignore"),
        on=keys,
        how="left",
        validate="one_to_one",
    )

    # Branch display/code come from Branch Master. Origin/Destination names
    # are only fallback metadata when needed.
    origin_branch_col = next(
        (
            c for c in [
                "ORIGIN_ORIGIN_BRANCH",
                "ORIGIN_BRANCH",
            ]
            if c in final.columns
        ),
        None,
    )
    destination_branch_col = next(
        (
            c for c in [
                "DESTINATION_DESTINATION_BRANCH",
                "DESTINATION_BRANCH",
            ]
            if c in final.columns
        ),
        None,
    )

    if "BRANCH" not in final.columns:
        final["BRANCH"] = pd.NA

    if origin_branch_col is not None:
        final["BRANCH"] = final["BRANCH"].fillna(final[origin_branch_col])

    if destination_branch_col is not None:
        final["BRANCH"] = final["BRANCH"].fillna(final[destination_branch_col])

    final["BRANCH"] = (
        final["BRANCH"]
        .fillna(final["BRANCH_KEY"])
        .astype(str)
        .str.strip()
    )

    if "BRANCHCODE" not in final.columns:
        final["BRANCHCODE"] = ""
    final["BRANCHCODE"] = final["BRANCHCODE"].fillna("").astype(str).str.strip()

    for column in [
        "SALARY",
        "GODOWN RENT",
        "OVERHEAD EXPENSE",
        "CLAIM",
        "BOOKING 6%",
        "DESTINATION 5%",
        "TOTAL EXPENSE",
    ]:
        final[column] = pd.to_numeric(
            final[column],
            errors="coerce",
        ).fillna(0.0)

    # FINAL ACCOUNTING LOGIC:
    # Origin P&L + Destination P&L - branch overhead (once).
    final["NET_PROFIT"] = (
        final["COMBINED_PNL"]
        - final["TOTAL EXPENSE"]
    )

    final["NET_PROFIT_MARGIN"] = 0.0
    valid_income = final["TOTAL_INCOME"].ne(0)

    final.loc[valid_income, "NET_PROFIT_MARGIN"] = (
        final.loc[valid_income, "NET_PROFIT"]
        / final.loc[valid_income, "TOTAL_INCOME"]
        * 100
    )

    final["MONTH"] = final["MONTHNO"].map(
        {
            1: "Jan",
            2: "Feb",
            3: "Mar",
            4: "Apr",
            5: "May",
            6: "Jun",
            7: "Jul",
            8: "Aug",
            9: "Sep",
            10: "Oct",
            11: "Nov",
            12: "Dec",
        }
    )

    final["FIN_MONTH"] = final["MONTHNO"].map(
        {
            4: 1,
            5: 2,
            6: 3,
            7: 4,
            8: 5,
            9: 6,
            10: 7,
            11: 8,
            12: 9,
            1: 10,
            2: 11,
            3: 12,
        }
    )

    final["QUARTER"] = final["FIN_MONTH"].map(
        {
            1: "Q1",
            2: "Q1",
            3: "Q1",
            4: "Q2",
            5: "Q2",
            6: "Q2",
            7: "Q3",
            8: "Q3",
            9: "Q3",
            10: "Q4",
            11: "Q4",
            12: "Q4",
        }
    )

    return final.sort_values(
        ["BRANCH", "YEAR", "MONTHNO"]
    ).reset_index(drop=True)


# ============================================================
# PUBLIC API
# ============================================================

def _fetch_complete_net_profit_period(start_date, end_date):
    """
    For one period:
      1. Existing Origin P&L
      2. Existing Destination P&L
      3. Branch overhead
      4. Combine by Branch + Year + Month
    """
    started = time.perf_counter()

    # Origin and Destination share the same heavy P&L stored-procedure output.
    # Fetch both views together so that SP executes only once for this period.
    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="net-profit",
    ) as executor:

        pnl_views_future = executor.submit(
            load_pnl_both_views,
            start_date,
            end_date,
        )

        overhead_future = executor.submit(
            _fetch_overhead_data,
            start_date,
            end_date,
        )

        origin_df, destination_df = pnl_views_future.result()
        overhead_df = overhead_future.result()

    final = _build_net_profit(
        origin_df,
        destination_df,
        overhead_df,
    )

    print(
        f"[Net Profit Complete] {start_date} to {end_date} | "
        f"rows={len(final):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )

    return final


@st.cache_data(
    ttl=_CACHE_TTL_SECONDS,
    show_spinner=False,
    max_entries=8,
)
def load_net_profit_data(start_date, end_date):
    return _fetch_complete_net_profit_period(
        start_date,
        end_date,
    )


@st.cache_data(
    ttl=_CACHE_TTL_SECONDS,
    show_spinner=False,
    max_entries=4,
)
def load_net_profit_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
):
    """
    Memory-safe Current FY + Previous FY loader.

    IMPORTANT:
    Current FY and Previous FY are loaded SEQUENTIALLY
    to reduce peak memory usage on Streamlit Cloud.

    Inside each period, Origin + Destination + Overhead
    are still fetched in parallel for reasonable speed.
    """

    print(
        f"[Net Profit Pair] Loading CURRENT FY first: "
        f"{start_date} to {end_date}"
    )

    current_df = load_net_profit_data(
        start_date,
        end_date,
    )

    print(
        f"[Net Profit Pair] CURRENT FY complete | "
        f"rows={len(current_df):,}"
    )

    print(
        f"[Net Profit Pair] Loading PREVIOUS FY next: "
        f"{prev_start} to {prev_end}"
    )

    previous_df = load_net_profit_data(
        prev_start,
        prev_end,
    )

    print(
        f"[Net Profit Pair] PREVIOUS FY complete | "
        f"rows={len(previous_df):,}"
    )

    return current_df, previous_df
