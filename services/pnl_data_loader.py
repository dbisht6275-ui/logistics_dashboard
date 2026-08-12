import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.data_loader import load_booking_data


# ============================================================
# CACHE
# ============================================================

_CACHE_TTL_SECONDS = 24 * 60 * 60


# ============================================================
# P&L STORED PROCEDURE
# ============================================================

_PNL_QUERY = text("""
    EXEC dbo.GREENTRANSWEB_GRWISEPNLDETAIL_PYTHONDASHBOARD
        @prmbranchcode = :branch_code,
        @prmfromdt     = :from_date,
        @prmtodt       = :to_date,
        @prmgrno       = :grno
""")


# ============================================================
# BRANCH-MONTH OVERHEAD QUERY
#
# Source logic is based on the overhead query provided:
# Salary + Godown Rent + Voucher Overhead + Claim
# ============================================================

_OVERHEAD_QUERY = text("""
DECLARE @FROMDATE DATE = :from_date;
DECLARE @TODATE   DATE = :to_date;

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
# HELPERS
# ============================================================

def _normalise_column_name(value):
    return str(value).strip().replace("_", "").replace(" ", "").casefold()


def _normalise_view_type(view_type):
    value = str(view_type or "origin").strip().upper()

    aliases = {
        "ORIGIN": "ORIGIN",
        "O": "ORIGIN",
        "ORIG": "ORIGIN",
        "DESTINATION": "DESTINATION",
        "DEST": "DESTINATION",
        "D": "DESTINATION",
    }

    normalised = aliases.get(value)

    if normalised is None:
        raise ValueError(
            f"Invalid view type: {view_type!r}. "
            "Allowed values are Origin and Destination."
        )

    return normalised


def _find_column(df, candidates):
    if df is None:
        return None

    column_map = {
        _normalise_column_name(col): col
        for col in df.columns
    }

    for candidate in candidates:
        found = column_map.get(
            _normalise_column_name(candidate)
        )
        if found is not None:
            return found

    return None


def _clean_grno(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _clean_branch_code(series):
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _add_year_month_from_date(df, date_candidates):
    """
    Adds _YEAR and _MONTHNO from the first matching date column.
    """
    date_col = _find_column(df, date_candidates)

    if date_col is None:
        raise ValueError(
            "Could not find a GR/date column required for "
            "Branch-Month P&L aggregation. "
            f"Available columns: {list(df.columns)}"
        )

    dt = pd.to_datetime(df[date_col], errors="coerce")

    df["_YEAR"] = dt.dt.year
    df["_MONTHNO"] = dt.dt.month

    return df


# ============================================================
# FETCH GR-WISE P&L SP DATA
# ============================================================

def _fetch_pnl_sp_data(start_date, end_date):
    started = time.perf_counter()

    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            _PNL_QUERY,
            conn,
            params={
                "branch_code": "00000",
                "from_date": str(start_date),
                "to_date": str(end_date),
                "grno": "",
            },
        )

    print(
        f"[P&L SP Loader] {start_date} to {end_date} | "
        f"rows={len(df):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )

    return df


# ============================================================
# FETCH BRANCH-MONTH OVERHEAD
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
        f"[Overhead Loader] {start_date} to {end_date} | "
        f"rows={len(df):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )

    return df


# ============================================================
# PREPARE REVENUE
# ============================================================

def _prepare_revenue_data(df):
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    gr_col = _find_column(
        out,
        ["GRNO", "grno", "gr_no", "grnumber", "gr_number"]
    )

    revenue_col = _find_column(
        out,
        [
            "REVENUE",
            "revenue",
            "freight",
            "business",
            "totalfreight",
            "total_freight",
        ],
    )

    if gr_col is None or revenue_col is None:
        raise ValueError(
            "Revenue data requires GRNO and REVENUE/FREIGHT columns. "
            f"Available columns: {list(out.columns)}"
        )

    rename_map = {}

    if gr_col != "grno":
        rename_map[gr_col] = "grno"

    if revenue_col != "REVENUE":
        rename_map[revenue_col] = "REVENUE"

    out = out.rename(columns=rename_map)

    out["grno"] = _clean_grno(out["grno"])
    out["REVENUE"] = pd.to_numeric(
        out["REVENUE"],
        errors="coerce"
    ).fillna(0.0)

    out = out[
        out["grno"].notna()
        & out["grno"].ne("")
        & out["grno"].str.lower().ne("nan")
    ].copy()

    return out


# ============================================================
# PREPARE P&L SP
# ============================================================

def _prepare_pnl_sp_data(df):
    aliases = {
        "GRNO": [
            "GRNO",
            "grno",
            "gr_no",
            "grnumber",
            "gr_number",
        ],
        "DELIVERYINCOME": [
            "DELIVERYINCOME",
            "delivery_income",
        ],
        "OTHERCHARGES": [
            "OTHERCHARGES",
            "other_charges",
        ],
        "ADDITIONALFREIGHT": [
            "ADDITIONALFREIGHT",
            "additional_freight",
        ],
        "OTHERINCOME": [
            "OTHERINCOME",
            "other_income",
        ],
        "RAW_EXPENSE": [
            "EXPENSE",
            "expense",
            "raw_expense",
        ],
    }

    output_columns = [
        "grno",
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]

    if df is None or df.empty:
        return pd.DataFrame(columns=output_columns)

    out = df.copy()
    rename_map = {}

    for target, candidates in aliases.items():
        source = _find_column(out, candidates)

        if source is None:
            if target == "OTHERCHARGES":
                out[target] = 0.0
                continue

            raise ValueError(
                f"P&L SP did not return {target}. "
                f"Available columns: {list(out.columns)}"
            )

        rename_map[source] = target

    out = (
        out.rename(columns=rename_map)
        .rename(columns={"GRNO": "grno"})
    )

    out["grno"] = _clean_grno(out["grno"])

    numeric_columns = [
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]

    for column in numeric_columns:
        out[column] = pd.to_numeric(
            out[column],
            errors="coerce"
        ).fillna(0.0)

    out = out[
        out["grno"].notna()
        & out["grno"].ne("")
        & out["grno"].str.lower().ne("nan")
    ].copy()

    return (
        out.groupby(
            "grno",
            as_index=False,
            dropna=False
        )[numeric_columns]
        .sum()
    )


# ============================================================
# MERGE REVENUE + P&L
# ============================================================

def _merge_revenue_and_pnl(revenue_df, pnl_sp_df):
    revenue = _prepare_revenue_data(revenue_df)
    pnl_data = _prepare_pnl_sp_data(pnl_sp_df)

    if revenue.empty:
        return revenue

    revenue = revenue.drop(
        columns=[
            column
            for column in [
                "EXPENSE",
                "PNL",
                "RAW_EXPENSE",
                "DELIVERYINCOME",
                "OTHERCHARGES",
                "ADDITIONALFREIGHT",
                "OTHERINCOME",
            ]
            if column in revenue.columns
        ],
        errors="ignore",
    )

    result = revenue.merge(
        pnl_data,
        on="grno",
        how="left",
        validate="many_to_one",
    )

    numeric_columns = [
        "DELIVERYINCOME",
        "OTHERCHARGES",
        "ADDITIONALFREIGHT",
        "OTHERINCOME",
        "RAW_EXPENSE",
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce"
        ).fillna(0.0)

    # Existing direct-cost logic retained.
    result["EXPENSE"] = (
        result["RAW_EXPENSE"]
        - result["ADDITIONALFREIGHT"]
        - result["DELIVERYINCOME"]
        - result["OTHERINCOME"]
    )

    # Existing P&L logic retained.
    result["PNL"] = (
        result["REVENUE"]
        + result["DELIVERYINCOME"]
        + result["ADDITIONALFREIGHT"]
        + result["OTHERINCOME"]
        - result["RAW_EXPENSE"]
    )

    # Useful reporting metric.
    result["TOTAL_INCOME"] = (
        result["REVENUE"]
        + result["DELIVERYINCOME"]
        + result["ADDITIONALFREIGHT"]
        + result["OTHERINCOME"]
    )

    result["PNL_MARGIN"] = 0.0

    valid_income = result["TOTAL_INCOME"].ne(0)

    result.loc[valid_income, "PNL_MARGIN"] = (
        result.loc[valid_income, "PNL"]
        / result.loc[valid_income, "TOTAL_INCOME"]
        * 100
    )

    return result


# ============================================================
# PREPARE OVERHEAD
# ============================================================

def _prepare_overhead_data(df):
    columns = [
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
        return pd.DataFrame(columns=columns)

    out = df.copy()

    branch_col = _find_column(
        out,
        ["BRANCHCODE", "branchcode", "branch_code"]
    )

    if branch_col is None:
        raise ValueError(
            "Overhead data requires BRANCHCODE. "
            f"Available columns: {list(out.columns)}"
        )

    if branch_col != "BRANCHCODE":
        out = out.rename(
            columns={branch_col: "BRANCHCODE"}
        )

    year_col = _find_column(out, ["YEAR"])
    month_col = _find_column(
        out,
        ["MONTHNO", "MONTH NO", "monthno"]
    )

    total_expense_col = _find_column(
        out,
        ["TOTAL EXPENSE", "TOTAL_EXPENSE", "totalexpense"]
    )

    if year_col is None or month_col is None:
        raise ValueError(
            "Overhead data requires YEAR and MONTHNO. "
            f"Available columns: {list(out.columns)}"
        )

    if total_expense_col is None:
        raise ValueError(
            "Overhead data requires TOTAL EXPENSE. "
            f"Available columns: {list(out.columns)}"
        )

    rename_map = {}

    if year_col != "YEAR":
        rename_map[year_col] = "YEAR"

    if month_col != "MONTHNO":
        rename_map[month_col] = "MONTHNO"

    if total_expense_col != "TOTAL EXPENSE":
        rename_map[total_expense_col] = "TOTAL EXPENSE"

    out = out.rename(columns=rename_map)

    out["BRANCHCODE"] = _clean_branch_code(
        out["BRANCHCODE"]
    )

    out["YEAR"] = pd.to_numeric(
        out["YEAR"],
        errors="coerce"
    )

    out["MONTHNO"] = pd.to_numeric(
        out["MONTHNO"],
        errors="coerce"
    )

    expense_columns = [
        "SALARY",
        "GODOWN RENT",
        "OVERHEAD EXPENSE",
        "CLAIM",
        "TOTAL EXPENSE",
    ]

    for column in expense_columns:
        if column not in out.columns:
            out[column] = 0.0

        out[column] = pd.to_numeric(
            out[column],
            errors="coerce"
        ).fillna(0.0)

    return out


# ============================================================
# FIND BRANCH CODE IN BOOKING DATA
# ============================================================

def _add_branch_month_keys(df):
    out = df.copy()

    branch_col = _find_column(
        out,
        [
            "BRANCHCODE",
            "branchcode",
            "branch_code",
            "originbranchcode",
            "origin_branch_code",
            "destbranchcode",
            "destinationbranchcode",
            "destination_branch_code",
        ],
    )

    if branch_col is None:
        raise ValueError(
            "Could not find Branch Code in booking data. "
            "The GR-wise loader must return a branch-code column "
            "to calculate Branch + Month Net Profit. "
            f"Available columns: {list(out.columns)}"
        )

    out["_BRANCHCODE"] = _clean_branch_code(
        out[branch_col]
    )

    out = _add_year_month_from_date(
        out,
        [
            "GRDT",
            "grdt",
            "GR_DATE",
            "GRDATE",
            "BOOKINGDATE",
            "booking_date",
            "DATE",
        ],
    )

    return out


# ============================================================
# BUILD BRANCH-MONTH SUMMARY
# ============================================================

def _aggregate_branch_month_pnl(df):
    if df is None or df.empty:
        return pd.DataFrame()

    out = _add_branch_month_keys(df)

    group_columns = [
        "_BRANCHCODE",
        "_YEAR",
        "_MONTHNO",
    ]

    summary = (
        out.groupby(
            group_columns,
            as_index=False
        )
        .agg(
            BUSINESS=("REVENUE", "sum"),
            DELIVERY_INCOME=("DELIVERYINCOME", "sum"),
            ADDITIONAL_FREIGHT=("ADDITIONALFREIGHT", "sum"),
            OTHER_INCOME=("OTHERINCOME", "sum"),
            DIRECT_EXPENSE=("EXPENSE", "sum"),
            TOTAL_INCOME=("TOTAL_INCOME", "sum"),
            PNL=("PNL", "sum"),
        )
    )

    summary = summary.rename(
        columns={
            "_BRANCHCODE": "BRANCHCODE",
            "_YEAR": "YEAR",
            "_MONTHNO": "MONTHNO",
        }
    )

    return summary


# ============================================================
# FINAL BRANCH NET PROFIT
#
# IMPORTANT:
# Origin P&L + Destination P&L are combined first.
# Branch-month overhead is deducted only once.
# ============================================================

def _build_branch_net_profit(
    origin_df,
    destination_df,
    overhead_df,
):
    origin = _aggregate_branch_month_pnl(origin_df)
    destination = _aggregate_branch_month_pnl(destination_df)
    overhead = _prepare_overhead_data(overhead_df)

    if origin.empty:
        origin = pd.DataFrame(
            columns=[
                "BRANCHCODE",
                "YEAR",
                "MONTHNO",
                "BUSINESS",
                "DELIVERY_INCOME",
                "ADDITIONAL_FREIGHT",
                "OTHER_INCOME",
                "DIRECT_EXPENSE",
                "TOTAL_INCOME",
                "PNL",
            ]
        )

    if destination.empty:
        destination = pd.DataFrame(
            columns=origin.columns
        )

    # Prefix origin/destination metrics.
    origin = origin.rename(
        columns={
            column: f"ORIGIN_{column}"
            for column in [
                "BUSINESS",
                "DELIVERY_INCOME",
                "ADDITIONAL_FREIGHT",
                "OTHER_INCOME",
                "DIRECT_EXPENSE",
                "TOTAL_INCOME",
                "PNL",
            ]
        }
    )

    destination = destination.rename(
        columns={
            column: f"DESTINATION_{column}"
            for column in [
                "BUSINESS",
                "DELIVERY_INCOME",
                "ADDITIONAL_FREIGHT",
                "OTHER_INCOME",
                "DIRECT_EXPENSE",
                "TOTAL_INCOME",
                "PNL",
            ]
        }
    )

    keys = [
        "BRANCHCODE",
        "YEAR",
        "MONTHNO",
    ]

    combined = origin.merge(
        destination,
        on=keys,
        how="outer",
    )

    numeric_columns = [
        column
        for column in combined.columns
        if column not in keys
    ]

    for column in numeric_columns:
        combined[column] = pd.to_numeric(
            combined[column],
            errors="coerce"
        ).fillna(0.0)

    # Combined branch operational result.
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

    combined["ORIGIN_PNL"] = combined["ORIGIN_PNL"]
    combined["DESTINATION_PNL"] = combined["DESTINATION_PNL"]

    combined["COMBINED_PNL"] = (
        combined["ORIGIN_PNL"]
        + combined["DESTINATION_PNL"]
    )

    # Overhead is Branch + Month and is deducted ONCE.
    overhead_keys = [
        "BRANCHCODE",
        "YEAR",
        "MONTHNO",
    ]

    overhead_merge = overhead[
        [
            "BRANCHCODE",
            "YEAR",
            "MONTHNO",
            "BRANCH",
            "SALARY",
            "GODOWN RENT",
            "OVERHEAD EXPENSE",
            "CLAIM",
            "TOTAL EXPENSE",
        ]
    ].copy()

    overhead_merge["BRANCHCODE"] = _clean_branch_code(
        overhead_merge["BRANCHCODE"]
    )

    combined["BRANCHCODE"] = _clean_branch_code(
        combined["BRANCHCODE"]
    )

    combined["YEAR"] = pd.to_numeric(
        combined["YEAR"],
        errors="coerce"
    )

    combined["MONTHNO"] = pd.to_numeric(
        combined["MONTHNO"],
        errors="coerce"
    )

    final = combined.merge(
        overhead_merge,
        on=overhead_keys,
        how="left",
        validate="one_to_one",
    )

    overhead_numeric = [
        "SALARY",
        "GODOWN RENT",
        "OVERHEAD EXPENSE",
        "CLAIM",
        "TOTAL EXPENSE",
    ]

    for column in overhead_numeric:
        final[column] = pd.to_numeric(
            final[column],
            errors="coerce"
        ).fillna(0.0)

    # Final Net Profit.
    final["NET_PROFIT"] = (
        final["COMBINED_PNL"]
        - final["TOTAL EXPENSE"]
    )

    # Net Profit % against combined income.
    final["NET_PROFIT_MARGIN"] = 0.0

    valid_income = final["TOTAL_INCOME"].ne(0)

    final.loc[valid_income, "NET_PROFIT_MARGIN"] = (
        final.loc[valid_income, "NET_PROFIT"]
        / final.loc[valid_income, "TOTAL_INCOME"]
        * 100
    )

    # Branch display.
    if "BRANCH" not in final.columns:
        final["BRANCH"] = final["BRANCHCODE"]

    final["MONTH"] = final["MONTHNO"].map(
        {
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June",
            7: "July",
            8: "August",
            9: "September",
            10: "October",
            11: "November",
            12: "December",
        }
    )

    return final.sort_values(
        ["BRANCH", "YEAR", "MONTHNO"]
    ).reset_index(drop=True)


# ============================================================
# CURRENT EXISTING API
# ============================================================

def _fetch_complete_period(
    start_date,
    end_date,
    view_type,
):
    normalised_view = _normalise_view_type(
        view_type
    )

    started = time.perf_counter()

    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="pnl-period",
    ) as executor:

        revenue_future = executor.submit(
            load_booking_data,
            start_date,
            end_date,
            normalised_view,
        )

        pnl_future = executor.submit(
            _fetch_pnl_sp_data,
            start_date,
            end_date,
        )

        revenue_df = revenue_future.result()
        pnl_sp_df = pnl_future.result()

    if revenue_df is None or revenue_df.empty:
        return pd.DataFrame()

    result = _merge_revenue_and_pnl(
        revenue_df,
        pnl_sp_df,
    )

    print(
        f"[P&L Period Complete] "
        f"view={normalised_view} | "
        f"merged_rows={len(result):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )

    return result


@st.cache_data(
    ttl=_CACHE_TTL_SECONDS,
    show_spinner=False,
    max_entries=12,
)
def load_pnl_data(
    start_date,
    end_date,
    view_type="origin",
):
    return _fetch_complete_period(
        start_date,
        end_date,
        _normalise_view_type(view_type),
    )


@st.cache_data(
    ttl=_CACHE_TTL_SECONDS,
    show_spinner=False,
    max_entries=8,
)
def load_pnl_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
    view_type="origin",
):
    """
    Existing API:
    Current FY + Previous FY P&L concurrently.
    """
    normalised_view = _normalise_view_type(
        view_type
    )

    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="pnl-pair",
    ) as executor:

        current_future = executor.submit(
            _fetch_complete_period,
            start_date,
            end_date,
            normalised_view,
        )

        previous_future = executor.submit(
            _fetch_complete_period,
            prev_start,
            prev_end,
            normalised_view,
        )

        current_df = current_future.result()
        previous_df = previous_future.result()

    return current_df, previous_df


# ============================================================
# NEW API
#
# Returns:
# Origin P&L + Destination P&L - Branch Month Overhead
# ============================================================

@st.cache_data(
    ttl=_CACHE_TTL_SECONDS,
    show_spinner=False,
    max_entries=8,
)
def load_branch_net_profit_data(
    start_date,
    end_date,
):
    """
    Loads both views and calculates Branch + Month Net Profit.

    Logic:
        Combined P&L
            = Origin P&L + Destination P&L

        Net Profit
            = Combined P&L - Branch Month Total Overhead
    """

    started = time.perf_counter()

    with ThreadPoolExecutor(
        max_workers=3,
        thread_name_prefix="branch-np",
    ) as executor:

        origin_future = executor.submit(
            _fetch_complete_period,
            start_date,
            end_date,
            "ORIGIN",
        )

        destination_future = executor.submit(
            _fetch_complete_period,
            start_date,
            end_date,
            "DESTINATION",
        )

        overhead_future = executor.submit(
            _fetch_overhead_data,
            start_date,
            end_date,
        )

        origin_df = origin_future.result()
        destination_df = destination_future.result()
        overhead_df = overhead_future.result()

    final = _build_branch_net_profit(
        origin_df,
        destination_df,
        overhead_df,
    )

    print(
        f"[Branch NP Complete] "
        f"rows={len(final):,} | "
        f"seconds={time.perf_counter() - started:.2f}"
    )

    return final


@st.cache_data(
    ttl=_CACHE_TTL_SECONDS,
    show_spinner=False,
    max_entries=4,
)
def load_branch_net_profit_data_pair(
    start_date,
    end_date,
    prev_start,
    prev_end,
):
    """
    Current FY + Previous FY Branch Net Profit.
    """

    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="branch-np-pair",
    ) as executor:

        current_future = executor.submit(
            load_branch_net_profit_data,
            start_date,
            end_date,
        )

        previous_future = executor.submit(
            load_branch_net_profit_data,
            prev_start,
            prev_end,
        )

        current_df = current_future.result()
        previous_df = previous_future.result()

    return current_df, previous_df
