import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.pnl_data_loader import load_pnl_data


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
#   Salary + Godown Rent + Voucher Overhead + Claim
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
    SELECT BRANCHCODE, [YEAR], [MONTHNO] FROM #SALARY
    UNION
    SELECT BRANCHCODE, [YEAR], [MONTHNO] FROM #GODOWN
    UNION
    SELECT BRANCHCODE, [YEAR], [MONTHNO] FROM #VOUCHEREXP
    UNION
    SELECT BRANCHCODE, [YEAR], [MONTHNO] FROM #CLAIM
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

    ROUND(ISNULL(SAL.NETAMT, 0), 2) AS [SALARY],
    ROUND(ISNULL(GOD.NETAMT, 0), 2) AS [GODOWN RENT],
    ROUND(ISNULL(VEXP.NETAMT, 0), 2) AS [OVERHEAD EXPENSE],
    ROUND(ISNULL(CL.NETAMT, 0), 2) AS [CLAIM],

    ROUND(
          ISNULL(SAL.NETAMT, 0)
        + ISNULL(GOD.NETAMT, 0)
        + ISNULL(VEXP.NETAMT, 0)
        + ISNULL(CL.NETAMT, 0),
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

def _get_branch_code_column(df, view_type):
    """
    IMPORTANT:
    Origin and Destination can have different branch-code fields.

    Prefer the view-specific field first.
    Only fall back to generic BRANCHCODE when a dedicated field is absent.
    """
    view = str(view_type).strip().upper()

    if view == "ORIGIN":
        candidates = [
            "ORIGINBRANCHCODE",
            "origin_branch_code",
            "BOOKINGBRANCHCODE",
            "booking_branch_code",
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
            "BRANCHCODE",
            "branch_code",
        ]
    else:
        raise ValueError(f"Unsupported view type: {view_type!r}")

    branch_col = _find_column(df, candidates)

    if branch_col is None:
        raise ValueError(
            f"Could not identify {view.title()} Branch Code. "
            f"Expected one of {candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    return branch_col


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
                "BRANCHCODE",
                "YEAR",
                "MONTHNO",
                "BUSINESS",
                "TOTAL_INCOME",
                "DIRECT_EXPENSE",
                "PNL",
            ]
        )

    out = df.copy()

    branch_col = _get_branch_code_column(out, view_type)
    date_col = _get_date_column(out)

    required_metrics = {
        "REVENUE": ["REVENUE", "revenue", "business"],
        "TOTAL_INCOME": ["TOTAL_INCOME", "totalincome"],
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

    out["_BRANCHCODE"] = _clean_code(out[branch_col])

    dt = pd.to_datetime(out[date_col], errors="coerce")
    out["_YEAR"] = dt.dt.year
    out["_MONTHNO"] = dt.dt.month

    for column in ["REVENUE", "TOTAL_INCOME", "EXPENSE", "PNL"]:
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)

    out = out[
        out["_BRANCHCODE"].notna()
        & out["_BRANCHCODE"].ne("")
        & out["_BRANCHCODE"].str.casefold().ne("nan")
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
            ["_BRANCHCODE", "_YEAR", "_MONTHNO"],
            as_index=False,
            dropna=False,
        )
        .agg(**agg_spec)
        .rename(
            columns={
                "_BRANCHCODE": "BRANCHCODE",
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
    out["YEAR"] = pd.to_numeric(out["YEAR"], errors="coerce")
    out["MONTHNO"] = pd.to_numeric(out["MONTHNO"], errors="coerce")

    for column in [
        "SALARY",
        "GODOWN RENT",
        "OVERHEAD EXPENSE",
        "CLAIM",
        "TOTAL EXPENSE",
    ]:
        if column not in out.columns:
            out[column] = 0.0

        out[column] = pd.to_numeric(
            out[column],
            errors="coerce",
        ).fillna(0.0)

    return out[expected].copy()


# ============================================================
# COMBINE ORIGIN + DESTINATION + OVERHEAD
# ============================================================

def _prefix_metrics(df, prefix):
    keys = {"BRANCHCODE", "YEAR", "MONTHNO"}
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

    keys = ["BRANCHCODE", "YEAR", "MONTHNO"]

    origin = _prefix_metrics(origin, "ORIGIN")
    destination = _prefix_metrics(destination, "DESTINATION")

    combined = origin.merge(
        destination,
        on=keys,
        how="outer",
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

    # Ensure required origin/destination metrics exist even when one side is empty.
    for prefix in ["ORIGIN", "DESTINATION"]:
        for metric in ["BUSINESS", "TOTAL_INCOME", "DIRECT_EXPENSE", "PNL"]:
            column = f"{prefix}_{metric}"
            if column not in combined.columns:
                combined[column] = 0.0

    # Organisational metadata, if present.
    for field in ["COMPNAME", "zone", "circle"]:
        combined[field] = _coalesce_metadata(combined, field)

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

    final = combined.merge(
        overhead,
        on=keys,
        how="left",
        validate="one_to_one",
    )

    for column in [
        "SALARY",
        "GODOWN RENT",
        "OVERHEAD EXPENSE",
        "CLAIM",
        "TOTAL EXPENSE",
    ]:
        final[column] = pd.to_numeric(
            final[column],
            errors="coerce",
        ).fillna(0.0)

    if "BRANCH" not in final.columns:
        final["BRANCH"] = final["BRANCHCODE"]
    else:
        final["BRANCH"] = (
            final["BRANCH"]
            .replace("", pd.NA)
            .fillna(final["BRANCHCODE"])
        )

    # THE FINAL ACCOUNTING LOGIC.
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

    # Calendar labels.
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

    # Financial year month number: Apr=1 ... Mar=12.
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

    with ThreadPoolExecutor(
        max_workers=3,
        thread_name_prefix="net-profit",
    ) as executor:

        origin_future = executor.submit(
            load_pnl_data,
            start_date,
            end_date,
            "origin",
        )

        destination_future = executor.submit(
            load_pnl_data,
            start_date,
            end_date,
            "destination",
        )

        overhead_future = executor.submit(
            _fetch_overhead_data,
            start_date,
            end_date,
        )

        origin_df = origin_future.result()
        destination_df = destination_future.result()
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
    Current FY + Previous FY Net Profit concurrently.
    """
    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="net-profit-pair",
    ) as executor:

        current_future = executor.submit(
            _fetch_complete_net_profit_period,
            start_date,
            end_date,
        )

        previous_future = executor.submit(
            _fetch_complete_net_profit_period,
            prev_start,
            prev_end,
        )

        current_df = current_future.result()
        previous_df = previous_future.result()

    return current_df, previous_df
