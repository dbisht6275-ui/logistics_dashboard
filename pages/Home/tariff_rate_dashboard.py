# UPDATED UI BUILD V9: ultra-compact header/filter bar, paged grids, branch scope preserved
from __future__ import annotations

from datetime import date
from html import escape

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


# =============================================================================
# Tariff / Contractual Rate Dashboard
# Filter flow:
#   View Type -> Rate Type -> Zone -> Circle -> Branch -> Rate For -> Customer
#   Empty multiselect = All
#   Child options are rebuilt from the rows allowed by parent selections
#   Stale selections are pruned automatically
#
# Role/data-scope rule is deliberately applied BEFORE dashboard filters:
#   Branch right  -> ORIGIN = branch OR DESTINATION = branch
#   Circle right  -> ORG_CIRCLE = circle OR DEST_CIRCLE = circle
#   Zone right    -> ORG_ZONE = zone OR DEST_ZONE = zone
# This means an Agartala user can see both Agartala -> X and X -> Agartala rates.
# =============================================================================


@st.cache_resource
def get_engine():
    """Build and cache the project's existing SQL Server connection."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
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


QUERY = r"""
SET NOCOUNT ON;

DECLARE @AsOnDate DATE = CAST(:active_on AS DATE);
DECLARE @ScopeType VARCHAR(20) = LOWER(LTRIM(RTRIM(CAST(:scope_type AS VARCHAR(20)))));
DECLARE @ScopeValue VARCHAR(100) = LTRIM(RTRIM(CAST(:scope_value AS VARCHAR(100))));

DECLARE @cols NVARCHAR(MAX);
DECLARE @select_cols NVARCHAR(MAX);
DECLARE @sql NVARCHAR(MAX);

SELECT
    @cols = STRING_AGG(CAST(QUOTENAME(X.CHGNAME) AS NVARCHAR(MAX)), ','),
    @select_cols = STRING_AGG(
        CAST('ISNULL(CHG.' + QUOTENAME(X.CHGNAME) + ',0) AS ' + QUOTENAME(X.CHGNAME) AS NVARCHAR(MAX)),
        ','
    )
FROM
(
    SELECT DISTINCT LTRIM(RTRIM(CM.CHGNAME)) AS CHGNAME
    FROM CUSTCHRG CC WITH (NOLOCK)
    INNER JOIN CNMTCHARGESMAST CM WITH (NOLOCK)
        ON CM.CHGCODE = CC.CHGCODE
    WHERE CM.CHGNAME IS NOT NULL
      AND LTRIM(RTRIM(CM.CHGNAME)) <> ''
) X;

SET @sql = N'
;WITH RATE_DATA AS
(
    SELECT
        RT.RATEDATAID,
        RT.CUSTCODE,
        RT.CNGECODE,
        RT.CNGRCODE,
        RT.RATEFOR,
        RT.RATEID,
        RT.ORGCODE,
        RT.DESTCODE,
        RT.FROMDT,
        RT.TODT,
        RT.FROMWT,
        RT.TOWT,
        RT.PRODUCTCODE,
        RT.GOODSGROUPCODE,
        RT.VEHICLETYPECODE,
        RT.MINCWEIGHT,
        RT.RATETYPE,
        RT.VIABORDERSTNCODE,
        RT.PCKGRATE,
        RT.SLAB1,
        RT.RATE1,
        RT.AMOUNT,
        RT.RATECATEGORY
    FROM RATEMAST RT WITH (NOLOCK)
    INNER JOIN VIEWSTATIONMAST ORG WITH (NOLOCK)
        ON ORG.STNCODE = RT.ORGCODE
    INNER JOIN VIEWSTATIONMAST DEST WITH (NOLOCK)
        ON DEST.STNCODE = RT.DESTCODE
    WHERE RT.TODT > @P_AsOnDate
      AND
      (
          @P_ScopeType = ''''
          OR
          (
              @P_ScopeType = ''branch''
              AND
              (
                  LOWER(LTRIM(RTRIM(ISNULL(ORG.STNNAME, '''')))) = LOWER(@P_ScopeValue)
                  OR LOWER(LTRIM(RTRIM(ISNULL(DEST.STNNAME, '''')))) = LOWER(@P_ScopeValue)
              )
          )
          OR
          (
              @P_ScopeType = ''circle''
              AND
              (
                  LOWER(LTRIM(RTRIM(ISNULL(ORG.HUBNAME, '''')))) = LOWER(@P_ScopeValue)
                  OR LOWER(LTRIM(RTRIM(ISNULL(DEST.HUBNAME, '''')))) = LOWER(@P_ScopeValue)
              )
          )
          OR
          (
              @P_ScopeType = ''zone''
              AND
              (
                  LOWER(LTRIM(RTRIM(ISNULL(ORG.ZONENAME, '''')))) = LOWER(@P_ScopeValue)
                  OR LOWER(LTRIM(RTRIM(ISNULL(DEST.ZONENAME, '''')))) = LOWER(@P_ScopeValue)
              )
          )
      )
),
CHARGE_SOURCE AS
(
    SELECT
        CC.RATEDATAID,
        LTRIM(RTRIM(CM.CHGNAME)) AS CHGNAME,
        CASE
            WHEN TRY_CONVERT(DECIMAL(18,2), CC.CHGAMT) > 0
                THEN TRY_CONVERT(DECIMAL(18,2), CC.CHGAMT)
            ELSE TRY_CONVERT(DECIMAL(18,2), CC.CHGRATE)
        END AS VAL
    FROM CUSTCHRG CC WITH (NOLOCK)
    INNER JOIN RATE_DATA RD
        ON RD.RATEDATAID = CC.RATEDATAID
    INNER JOIN CNMTCHARGESMAST CM WITH (NOLOCK)
        ON CM.CHGCODE = CC.CHGCODE
    WHERE CM.CHGNAME IS NOT NULL
      AND LTRIM(RTRIM(CM.CHGNAME)) <> ''''
),
CHARGE_PIVOT AS
(
    SELECT RATEDATAID, ' + @cols + '
    FROM
    (
        SELECT RATEDATAID, CHGNAME, VAL
        FROM CHARGE_SOURCE
    ) SRC
    PIVOT
    (
        MAX(VAL)
        FOR CHGNAME IN (' + @cols + ')
    ) PVT
)
SELECT
    COALESCE(RT.CUSTCODE, RT.CNGECODE, RT.CNGRCODE) AS CUSTOMER_CODE,
    CASE
        WHEN RT.CUSTCODE = ''0000007565'' THEN ''TARIFF RATE''
        ELSE ''CONTRACTUAL RATE''
    END AS RATE_TYPE_GROUP,
    CASE
        WHEN RT.CUSTCODE = ''0000007565'' THEN ''TARIFF RATE''
        ELSE COALESCE(C.CUSTNAME, E.NAME, R.NAME)
    END AS CUSTOMER_NAME,
    CASE RT.RATEFOR
        WHEN ''E'' THEN ''CONSIGNEE''
        WHEN ''R'' THEN ''CONSIGNOR''
        WHEN ''C'' THEN ''CREDIT CUSTOMER''
        ELSE ''N/A''
    END AS RATEFOR,
    RT.RATEID,
    ORG.ZONENAME AS ORG_ZONE,
    ORG.HUBNAME AS ORG_CIRCLE,
    ORG.STNNAME AS ORIGIN,
    DEST.ZONENAME AS DEST_ZONE,
    DEST.HUBNAME AS DEST_CIRCLE,
    DEST.STNNAME AS DESTINATION,
    RT.FROMDT,
    RT.TODT,
    RT.FROMWT,
    RT.TOWT,
    PR.PRODNAME AS PRODUCT_NAME,
    G.ITEMNAME AS GOODS,
    VM.TYPENAME AS VEHICLE_TYPE,
    RT.MINCWEIGHT,
    RT.RATETYPE,
    VIA.STNNAME AS VIA_BORDER,
    RT.PCKGRATE,
    RT.SLAB1,
    RT.RATE1,
    RT.AMOUNT AS FLAT_AMOUNT,
    RT.RATECATEGORY,
    ' + @select_cols + '
FROM RATE_DATA RT
INNER JOIN VIEWSTATIONMAST ORG WITH (NOLOCK)
    ON ORG.STNCODE = RT.ORGCODE
INNER JOIN VIEWSTATIONMAST DEST WITH (NOLOCK)
    ON DEST.STNCODE = RT.DESTCODE
LEFT JOIN VEHICLETYPEMAST VM WITH (NOLOCK)
    ON VM.TYPECODE = RT.VEHICLETYPECODE
LEFT JOIN PRODUCTMAST PR WITH (NOLOCK)
    ON PR.PRODCODE = RT.PRODUCTCODE
LEFT JOIN STATIONMAST VIA WITH (NOLOCK)
    ON VIA.STNCODE = RT.VIABORDERSTNCODE
LEFT JOIN VIEWGOODSMAST G WITH (NOLOCK)
    ON G.ITEMCODE = RT.GOODSGROUPCODE
LEFT JOIN CNGRCNGEMAST E WITH (NOLOCK)
    ON E.CODE = RT.CNGECODE
LEFT JOIN CNGRCNGEMAST R WITH (NOLOCK)
    ON R.CODE = RT.CNGRCODE
LEFT JOIN CUSTMAST C WITH (NOLOCK)
    ON C.CUSTCODE = RT.CUSTCODE
LEFT JOIN CHARGE_PIVOT CHG
    ON CHG.RATEDATAID = RT.RATEDATAID
ORDER BY RT.FROMDT, ORG.STNNAME, DEST.STNNAME;
';

IF @cols IS NULL
BEGIN
    SELECT TOP (0)
        CAST(NULL AS VARCHAR(20)) AS CUSTOMER_CODE,
        CAST(NULL AS VARCHAR(20)) AS RATE_TYPE_GROUP,
        CAST(NULL AS VARCHAR(200)) AS CUSTOMER_NAME,
        CAST(NULL AS VARCHAR(30)) AS RATEFOR,
        RT.RATEID,
        ORG.ZONENAME AS ORG_ZONE,
        ORG.HUBNAME AS ORG_CIRCLE,
        ORG.STNNAME AS ORIGIN,
        DEST.ZONENAME AS DEST_ZONE,
        DEST.HUBNAME AS DEST_CIRCLE,
        DEST.STNNAME AS DESTINATION,
        RT.FROMDT, RT.TODT, RT.FROMWT, RT.TOWT,
        CAST(NULL AS VARCHAR(200)) AS PRODUCT_NAME,
        CAST(NULL AS VARCHAR(200)) AS GOODS,
        CAST(NULL AS VARCHAR(200)) AS VEHICLE_TYPE,
        RT.MINCWEIGHT, RT.RATETYPE,
        CAST(NULL AS VARCHAR(200)) AS VIA_BORDER,
        RT.PCKGRATE, RT.SLAB1, RT.RATE1,
        RT.AMOUNT AS FLAT_AMOUNT, RT.RATECATEGORY
    FROM RATEMAST RT
    INNER JOIN VIEWSTATIONMAST ORG ON ORG.STNCODE = RT.ORGCODE
    INNER JOIN VIEWSTATIONMAST DEST ON DEST.STNCODE = RT.DESTCODE;
END
ELSE
BEGIN
    EXEC sys.sp_executesql
        @sql,
        N'@P_AsOnDate DATE, @P_ScopeType VARCHAR(20), @P_ScopeValue VARCHAR(100)',
        @P_AsOnDate = @AsOnDate,
        @P_ScopeType = @ScopeType,
        @P_ScopeValue = @ScopeValue;
END;
"""


@st.cache_data(ttl=900, show_spinner=False)
def load_rates_role_v2(active_on: date, scope_type: str, scope_value: str) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as cn:
        return pd.read_sql_query(
            text(QUERY),
            cn,
            params={
                "active_on": active_on,
                "scope_type": scope_type,
                "scope_value": scope_value,
            },
        )


def _canon(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).casefold()


def _safe_options(source_df: pd.DataFrame, column: str) -> list[str]:
    """Return clean, sorted values for the current parent scope."""
    if source_df is None or source_df.empty or column not in source_df.columns:
        return []
    values = source_df[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return sorted(values.unique().tolist(), key=str.casefold)


def _apply_multi_filter(source_df: pd.DataFrame, column: str, selected: list[str]) -> pd.DataFrame:
    """Empty multiselect means All."""
    if (
        source_df is None
        or source_df.empty
        or column not in source_df.columns
        or not selected
    ):
        return source_df
    return source_df[source_df[column].isin(selected)].copy()


def _prune_multiselect_state(key: str, allowed_options: list[str]) -> None:
    """Remove stale selections when a parent filter changes."""
    if key in st.session_state:
        current = st.session_state.get(key, [])
        if isinstance(current, (list, tuple, set)):
            st.session_state[key] = [
                value for value in current if value in allowed_options
            ]


def _get_login_scope() -> tuple[str, str]:
    data_scope = st.session_state.get("data_scope", {}) or {}
    # User Management is expected to save one scope key. If bad data contains
    # more than one, the most specific right wins.
    for scope_type in ("branch", "circle", "zone"):
        value = data_scope.get(scope_type)
        if value is not None and str(value).strip():
            return scope_type, str(value).strip()
    return "", ""


def _scope_masks(frame: pd.DataFrame, scope_type: str, scope_value: str) -> tuple[pd.Series, pd.Series]:
    false_mask = pd.Series(False, index=frame.index)
    if frame is None or frame.empty or not scope_type or not scope_value:
        return false_mask, false_mask

    column_map = {
        "branch": ("ORIGIN", "DESTINATION"),
        "circle": ("ORG_CIRCLE", "DEST_CIRCLE"),
        "zone": ("ORG_ZONE", "DEST_ZONE"),
    }
    org_col, dest_col = column_map.get(scope_type, (None, None))
    if not org_col or org_col not in frame.columns or dest_col not in frame.columns:
        return false_mask, false_mask

    target = _canon(scope_value)
    org_mask = frame[org_col].fillna("").astype(str).map(_canon).eq(target)
    dest_mask = frame[dest_col].fillna("").astype(str).map(_canon).eq(target)
    return org_mask, dest_mask


def _apply_python_role_scope(frame: pd.DataFrame, scope_type: str, scope_value: str) -> pd.DataFrame:
    """Defensive second security layer. SQL already applies the same OR rule."""
    if not scope_type or frame is None or frame.empty:
        return frame
    org_mask, dest_mask = _scope_masks(frame, scope_type, scope_value)
    return frame[org_mask | dest_mask].copy()


def _inject_css():
    """Compact controls for the rate dashboard."""
    st.markdown(
        """
        <style>
        .block-container {max-width:100%; padding:.12rem .42rem .55rem !important;}
        div[data-testid="stHorizontalBlock"] {gap:.22rem !important; align-items:flex-start !important;}
        div[data-testid="stWidgetLabel"] {min-height:12px !important; margin-bottom:0 !important;}
        div[data-testid="stWidgetLabel"] p {line-height:1.0 !important; margin:0 !important;}
        div[data-testid="stSelectbox"],
        div[data-testid="stMultiSelect"],
        div[data-testid="stDateInput"] {margin-bottom:0 !important;}
        div[data-testid="stSelectbox"] > label,
        div[data-testid="stMultiSelect"] > label,
        div[data-testid="stTextInput"] > label,
        div[data-testid="stNumberInput"] > label,
        div[data-testid="stDateInput"] > label {
            color:#243b53 !important;
            font-size:9px !important;
            line-height:1 !important;
            font-weight:600 !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stDateInput"] input {
            min-height:28px !important;
            height:28px !important;
            border:1px solid #b6c6d7 !important;
            border-radius:7px !important;
            background:linear-gradient(180deg,#f9fbfe 0%,#eef4fa 58%,#e4edf7 100%) !important;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.95),0 2px 5px rgba(30,64,105,.08) !important;
        }
        /* Compact bordered page header */
        .rate-dashboard-title {
            margin:0 !important;
            padding:0 !important;
            color:#17365d;
            font-size:.88rem !important;
            line-height:1.05 !important;
            font-weight:700 !important;
        }
        .rate-dashboard-scope {
            margin:.08rem 0 0 0 !important;
            color:#607286;
            font-size:.60rem !important;
            line-height:1.05 !important;
        }
        .login-scope-value {
            color:#0b3f75 !important;
            font-weight:800 !important;
            font-size:.76rem !important;
            letter-spacing:.01em;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color:#c2cfdb !important;
            border-radius:8px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding:.28rem .48rem !important;
        }
        .active-on-label {
            font-size:9px !important;
            font-weight:700 !important;
            color:#243b53 !important;
            line-height:28px !important;
            white-space:nowrap !important;
            text-align:right !important;
        }
        div[data-testid="stDateInput"] {max-width:138px !important;}
        div[data-testid="stDateInput"] input {
            font-size:10px !important;
            padding:.15rem .45rem !important;
        }
        div[data-testid="stButton"] button {
            min-height:28px !important;
            height:28px !important;
            padding:.15rem .55rem !important;
            border-radius:7px !important;
            font-size:10px !important;
            line-height:1 !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] span {
            font-size:10px !important;
        }

        /* Reliable HTML grid styling. Streamlit st.dataframe uses a canvas in
           recent versions, so its header cannot be recolored reliably with CSS. */
        .rate-grid-wrap {
            width:100%;
            overflow:auto;
            border:1px solid #8ea8c2;
            border-radius:8px;
            background:#ffffff;
        }
        table.rate-grid-table {
            width:max-content;
            min-width:100%;
            border-collapse:separate;
            border-spacing:0;
            font-size:12px;
            color:#1f2937;
        }
        table.rate-grid-table thead th {
            position:sticky;
            top:0;
            z-index:3;
            background:#123b66 !important;
            color:#ffffff !important;
            font-weight:700 !important;
            text-align:left;
            white-space:nowrap;
            padding:8px 10px;
            border-right:1px solid #31597f;
            border-bottom:1px solid #0b2d4e;
        }
        table.rate-grid-table tbody td {
            white-space:nowrap;
            padding:6px 10px;
            border-right:1px solid #e3eaf1;
            border-bottom:1px solid #e8eef4;
            background:#ffffff;
        }
        table.rate-grid-table tbody tr:nth-child(even) td { background:#f7f9fc; }
        table.rate-grid-table tbody tr:hover td { background:#edf4fb; }

        /* Ultra-compact top header card. */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding-top:.10rem !important;
            padding-bottom:.10rem !important;
        }
        div[data-testid="stButton"] button {
            min-height:28px !important;
            height:28px !important;
            padding:.10rem .45rem !important;
            font-size:.66rem !important;
            font-weight:700 !important;
            background:#123b66 !important;
            color:#ffffff !important;
            border:1px solid #0b2d4e !important;
            box-shadow:0 1px 2px rgba(18,59,102,.18) !important;
        }
        div[data-testid="stButton"] button:hover {
            background:#0b2d4e !important;
            color:#ffffff !important;
            border-color:#081f36 !important;
        }
        .active-on-label {
            font-size:.56rem !important;
            font-weight:700 !important;
            color:#243b53 !important;
            white-space:nowrap !important;
            line-height:28px !important;
            padding-top:0 !important;
            text-align:right !important;
        }

        /* Compact view selector used instead of st.tabs so only one heavy grid renders. */
        div[role="radiogroup"] {gap:.25rem !important;}
        div[role="radiogroup"] label {
            background:#eef3f8 !important;
            border:1px solid #c4d2df !important;
            border-radius:6px !important;
            padding:.20rem .55rem !important;
            min-height:30px !important;
        }
        div[role="radiogroup"] label:has(input:checked) {
            background:#123b66 !important;
            color:#ffffff !important;
            border-color:#0b2d4e !important;
        }
        /* Streamlit applies its own text color to nested elements; force selected button text white. */
        div[role="radiogroup"] label:has(input:checked) * {
            color:#ffffff !important;
        }
        .grid-summary {
            font-size:.70rem;
            color:#52667a;
            margin:.02rem 0 .18rem 0;
        }
        .rate-grid-table tbody tr.tariff-row td {
            background:#fff3cd !important;
            color:#5f4300 !important;
            font-weight:600 !important;
        }
        .rate-grid-table tbody tr.tariff-row:hover td {
            background:#ffe69c !important;
        }
        .quick-finder-title {
            font-size:1.05rem;
            font-weight:700;
            color:#123b66;
            margin:.15rem 0 .05rem 0;
        }
        .quick-finder-note {
            font-size:.72rem;
            color:#6a7685;
            margin:0 0 .28rem 0;
        }
        .quick-kpi-wrap {
            display:grid;
            grid-template-columns:repeat(4,minmax(120px,1fr));
            gap:8px;
            margin:.28rem 0 .35rem 0;
        }
        .quick-kpi {
            border:1px solid #d5dfeb;
            border-radius:8px;
            background:#f8fbff;
            padding:6px 10px;
            min-height:48px;
        }
        .quick-kpi .kpi-label {font-size:.67rem;color:#52667a;margin-bottom:1px;}
        .quick-kpi .kpi-value {font-size:1.18rem;font-weight:700;color:#123b66;line-height:1.1;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _rate_type_display(value: str) -> str:
    value = str(value or "").upper().strip()
    if value == "TARIFF RATE":
        return "Tariff Rate"
    if value == "CONTRACTUAL RATE":
        return "Contractual Rate"
    return value.title()


def _render_rate_grid(frame: pd.DataFrame, height: int = 520) -> None:
    """Render a compact scrollable grid; blanks for missing values and highlight Tariff rows."""
    if frame is None or frame.empty:
        st.info("No records to display.")
        return

    show = frame.copy()
    for col in ("FROMDT", "TODT"):
        if col in show.columns:
            dt = pd.to_datetime(show[col], errors="coerce")
            show[col] = dt.dt.strftime("%d-%m-%Y").where(dt.notna(), "")

    # Display missing values as blank instead of NaN / NaT / <NA>.
    show = show.astype(object).where(pd.notna(show), "")

    headers = "".join(f"<th>{escape(str(col))}</th>" for col in show.columns)
    body_rows = []
    rate_idx = show.columns.get_loc("RATE_TYPE_GROUP") if "RATE_TYPE_GROUP" in show.columns else None
    for row in show.itertuples(index=False, name=None):
        is_tariff = False
        if rate_idx is not None:
            is_tariff = str(row[rate_idx]).strip().casefold() == "tariff rate"
        row_class = ' class="tariff-row"' if is_tariff else ""
        cells = "".join(f"<td>{escape(str(value)) if value != '' else ''}</td>" for value in row)
        body_rows.append(f"<tr{row_class}>{cells}</tr>")

    table_html = (
        '<table class="rate-grid-table">'
        f'<thead><tr>{headers}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
    )
    st.markdown(
        f'<div class="rate-grid-wrap" style="max-height:{int(height)}px;">{table_html}</div>',
        unsafe_allow_html=True,
    )


def _paged_frame(frame: pd.DataFrame, key: str, default_size: int = 100) -> pd.DataFrame:
    """Return only one page so the browser never renders thousands of HTML rows."""
    if frame is None or frame.empty:
        return frame

    total = len(frame)
    size_options = [50, 100, 250, 500]
    default_index = size_options.index(default_size) if default_size in size_options else 1

    ctl = st.columns([1.15, 1.0, 4.5], gap="small")
    with ctl[0]:
        page_size = st.selectbox(
            "Rows per page",
            size_options,
            index=default_index,
            key=f"{key}_page_size",
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    current = int(st.session_state.get(f"{key}_page", 1) or 1)
    current = max(1, min(current, total_pages))

    with ctl[1]:
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=current,
            step=1,
            key=f"{key}_page_input",
        )
    st.session_state[f"{key}_page"] = int(page)

    start = (int(page) - 1) * page_size
    stop = min(start + page_size, total)
    with ctl[2]:
        st.markdown(
            f'<div class="grid-summary">Showing {start + 1:,}-{stop:,} of {total:,} records · Page {int(page):,} of {total_pages:,}</div>',
            unsafe_allow_html=True,
        )
    return frame.iloc[start:stop].copy()


# =============================================================================
# Page
# =============================================================================
_inject_css()

scope_type, scope_value = _get_login_scope()

# Keep title, date and load action in one compact single-row header.
with st.container(border=True):
    header_cols = st.columns([7.2, 0.48, 0.92, 1.08], gap="small")

    with header_cols[0]:
        st.markdown(
            '<div class="rate-dashboard-title">Tariff &amp; Contractual Rate Dashboard</div>',
            unsafe_allow_html=True,
        )
        if scope_type:
            st.markdown(
                f'<div class="rate-dashboard-scope">Data access: {escape(scope_type.title())} = '
                f'<span class="login-scope-value">{escape(str(scope_value))}</span> · '
                'Origin or Destination permitted.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="rate-dashboard-scope">Full-network visibility · use filters to refine rates.</div>',
                unsafe_allow_html=True,
            )

    with header_cols[1]:
        st.markdown('<div class="active-on-label">Active on</div>', unsafe_allow_html=True)

    with header_cols[2]:
        active_date = st.date_input(
            "Active on",
            date.today(),
            key="rate_active_on_v2",
            label_visibility="collapsed",
        )

    with header_cols[3]:
        load_clicked = st.button(
            "Load Dashboard",
            type="primary",
            use_container_width=True,
            key="rate_load_v2",
        )

load_key = (active_date, scope_type, scope_value)
if load_clicked:
    try:
        with st.spinner("Loading rate data..."):
            loaded = load_rates_role_v2(active_date, scope_type, scope_value)
            st.session_state["rate_data_v2"] = loaded
            st.session_state["rate_key_v2"] = load_key
    except Exception as exc:
        st.error("Rate data could not be loaded.")
        with st.expander("Technical details"):
            st.code(str(exc))
        st.stop()

if st.session_state.get("rate_key_v2") != load_key:
    st.info("Choose the active date and click **Load Dashboard**.")
    st.stop()

data = st.session_state.get("rate_data_v2", pd.DataFrame()).copy()
if data.empty:
    if scope_type:
        st.warning(f"No active rates found for your assigned {scope_type}: {scope_value}.")
    else:
        st.warning("No active rates found for the selected date.")
    st.stop()

required_columns = {
    "RATE_TYPE_GROUP",
    "ORG_ZONE", "ORG_CIRCLE", "ORIGIN",
    "DEST_ZONE", "DEST_CIRCLE", "DESTINATION",
}
missing = sorted(required_columns.difference(data.columns))
if missing:
    load_rates_role_v2.clear()
    st.error("SQL result is missing required columns: " + ", ".join(missing))
    st.stop()

# Normalize values used by filters and calculations.
for col in ("FROMDT", "TODT"):
    if col in data.columns:
        data[col] = pd.to_datetime(data[col], errors="coerce")

for col in ("SLAB1", "RATE1", "FROMWT", "TOWT", "MINCWEIGHT", "FLAT_AMOUNT", "PCKGRATE"):
    if col in data.columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

data["RATE_TYPE_GROUP"] = data["RATE_TYPE_GROUP"].fillna("").astype(str).str.upper().str.strip()
data["CUSTOMER_NAME"] = data.get("CUSTOMER_NAME", "").fillna("Not specified").astype(str).str.strip().replace("", "Not specified")
data["PRODUCT_NAME"] = data.get("PRODUCT_NAME", "").fillna("Not specified").astype(str).str.strip().replace("", "Not specified")
data["RATEFOR"] = data.get("RATEFOR", "").fillna("N/A").astype(str).str.strip().replace("", "N/A")

# Defensive access control in Python as well as SQL.
data = _apply_python_role_scope(data, scope_type, scope_value)
if data.empty:
    st.warning("No records remain inside your assigned data scope.")
    st.stop()



# =============================================================================
# FILTER ROW
# =============================================================================
filter_cols = st.columns(7, gap="small")

with filter_cols[0]:
    view_type = st.selectbox(
        "⇄ View Type",
        ["Origin", "Destination"],
        key="rate_view_type_v2",
        help="Changes which side Zone / Circle / Branch filters are based on.",
    )

with filter_cols[1]:
    rate_type = st.selectbox(
        "▥ Rate Type",
        ["All", "Tariff Rate", "Contractual Rate"],
        key="rate_type_v2",
    )

working = data.copy()
if rate_type != "All":
    working = working[working["RATE_TYPE_GROUP"].eq(rate_type.upper())].copy()

# View Type chooses which route side supplies Zone / Circle / Branch.
if view_type == "Origin":
    zone_col, circle_col, branch_col = "ORG_ZONE", "ORG_CIRCLE", "ORIGIN"
else:
    zone_col, circle_col, branch_col = "DEST_ZONE", "DEST_CIRCLE", "DESTINATION"

filter_source_df = working.copy()

# ZONE
zone_options = _safe_options(filter_source_df, zone_col)
_prune_multiselect_state("rate_zone_v2", zone_options)
with filter_cols[2]:
    selected_zones = st.multiselect(
        "◉ Zone",
        zone_options,
        key="rate_zone_v2",
        placeholder="All zones",
        disabled=not zone_options,
    )

# CIRCLE follows Zone
circle_scope = _apply_multi_filter(filter_source_df.copy(), zone_col, selected_zones)
circle_options = _safe_options(circle_scope, circle_col)
_prune_multiselect_state("rate_circle_v2", circle_options)
with filter_cols[3]:
    selected_circles = st.multiselect(
        "◎ Circle",
        circle_options,
        key="rate_circle_v2",
        placeholder="All circles",
        disabled=not circle_options,
    )

# BRANCH follows Zone + Circle
branch_scope = _apply_multi_filter(circle_scope.copy(), circle_col, selected_circles)
branch_options = _safe_options(branch_scope, branch_col)
_prune_multiselect_state("rate_branch_v2", branch_options)
with filter_cols[4]:
    selected_branches = st.multiselect(
        "⌂ Branch",
        branch_options,
        key="rate_branch_v2",
        placeholder="All branches",
        disabled=not branch_options,
    )

# RATE FOR follows the selected hierarchy
ratefor_scope = _apply_multi_filter(branch_scope.copy(), branch_col, selected_branches)
ratefor_options = _safe_options(ratefor_scope, "RATEFOR")
_prune_multiselect_state("rate_ratefor_v2", ratefor_options)
with filter_cols[5]:
    selected_ratefor = st.multiselect(
        "◫ Rate For",
        ratefor_options,
        key="rate_ratefor_v2",
        placeholder="All",
        disabled=not ratefor_options,
    )

# CUSTOMER follows all filters above
customer_scope = _apply_multi_filter(ratefor_scope.copy(), "RATEFOR", selected_ratefor)
customer_options = _safe_options(customer_scope, "CUSTOMER_NAME")
_prune_multiselect_state("rate_customer_v2", customer_options)
with filter_cols[6]:
    selected_customers = st.multiselect(
        "♙ Customer",
        customer_options,
        key="rate_customer_v2",
        placeholder="All customers",
        disabled=not customer_options,
    )

# Apply active filters to final dataframe.
filtered = working.copy()
for column, selected in (
    (zone_col, selected_zones),
    (circle_col, selected_circles),
    (branch_col, selected_branches),
    ("RATEFOR", selected_ratefor),
    ("CUSTOMER_NAME", selected_customers),
):
    filtered = _apply_multi_filter(filtered, column, selected)

if filtered.empty:
    st.warning("No rate records match the selected filters.")
    st.stop()


# =============================================================================
# RESULTS
# =============================================================================
as_on_ts = pd.Timestamp(active_date)

# Columns not in the fixed rate schema are dynamic charge-name columns.
base_rate_columns = {
    "CUSTOMER_CODE", "RATE_TYPE_GROUP", "CUSTOMER_NAME", "RATEFOR", "RATEID",
    "ORG_ZONE", "ORG_CIRCLE", "ORIGIN", "DEST_ZONE", "DEST_CIRCLE", "DESTINATION",
    "FROMDT", "TODT", "FROMWT", "TOWT", "PRODUCT_NAME", "GOODS", "VEHICLE_TYPE",
    "MINCWEIGHT", "RATETYPE", "VIA_BORDER", "PCKGRATE", "SLAB1", "RATE1",
    "FLAT_AMOUNT", "RATECATEGORY",
}
charge_columns = [col for col in data.columns if col not in base_rate_columns]

view_mode = st.radio(
    "Result view",
    ["Expiry Watch", "Rate Records", "Quick Rate Finder"],
    horizontal=True,
    label_visibility="collapsed",
    key="rate_result_view_v4",
)


if view_mode == "Expiry Watch":
    expiry = filtered[filtered["TODT"].notna()].copy()
    expiry["DAYS_TO_EXPIRY"] = (expiry["TODT"].dt.normalize() - as_on_ts.normalize()).dt.days
    expiry = expiry.sort_values(["DAYS_TO_EXPIRY", "ORIGIN", "DESTINATION"])

    expiry_window = st.selectbox(
        "Expiry Window",
        ["7 days", "15 days", "30 days", "60 days", "90 days", "All active"],
        key="rate_expiry_window_v2",
    )
    day_limit = {"7 days": 7, "15 days": 15, "30 days": 30, "60 days": 60, "90 days": 90}.get(expiry_window)
    if day_limit is not None:
        expiry = expiry[expiry["DAYS_TO_EXPIRY"].between(0, day_limit)]

    expiry_cols = [
        "RATE_TYPE_GROUP", "CUSTOMER_NAME", "ORIGIN", "DESTINATION",
        "FROMDT", "TODT", "DAYS_TO_EXPIRY",
        "FROMWT", "TOWT", "RATE1", "FLAT_AMOUNT",
    ]
    expiry_cols = [col for col in expiry_cols if col in expiry.columns]
    display_expiry = expiry[expiry_cols].copy()
    if "RATE_TYPE_GROUP" in display_expiry.columns:
        display_expiry["RATE_TYPE_GROUP"] = display_expiry["RATE_TYPE_GROUP"].map(_rate_type_display)

    page_expiry = _paged_frame(display_expiry, "expiry_grid", default_size=100)
    _render_rate_grid(page_expiry, height=500)


elif view_mode == "Rate Records":
    # Important: render only one page. Rendering the complete HTML table was the main browser-freeze cause.
    display_records = filtered.copy()
    display_records = display_records.drop(columns=[c for c in ["SLAB1", "PRODUCT_NAME"] if c in display_records.columns])
    display_records["RATE_TYPE_GROUP"] = display_records["RATE_TYPE_GROUP"].map(_rate_type_display)

    page_records = _paged_frame(display_records, "records_grid", default_size=100)
    _render_rate_grid(page_records, height=540)

    st.caption(
        "For performance, only the selected page is rendered. Filters still apply to the complete loaded dataset."
    )
    prepare_download = st.checkbox(
        "Prepare full filtered CSV download",
        value=False,
        key="rate_prepare_download_v3",
        help="Enable only when you need the export. This avoids rebuilding a large CSV on every dashboard refresh.",
    )
    if prepare_download:
        st.download_button(
            "Download all filtered rates (CSV)",
            display_records.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"rate_dashboard_{active_date:%Y%m%d}.csv",
            mime="text/csv",
            key="rate_download_v3",
        )


else:
    st.markdown('<div class="quick-finder-title">Quick Rate Finder</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="quick-finder-note">Select at least one route condition: Origin or Destination. Other fields are optional.</div>',
        unsafe_allow_html=True,
    )

    finder_source = data
    finder_cols = st.columns([1.25, 1.25, 1.0, 1.6, 0.9], gap="small")

    origin_options = _safe_options(finder_source, "ORIGIN")
    with finder_cols[0]:
        finder_origin = st.selectbox(
            "Origin",
            [""] + origin_options,
            index=0,
            key="rate_finder_origin_v2",
            format_func=lambda x: "Select origin" if x == "" else x,
        )

    # Destination remains independently searchable so Origin-only, Destination-only,
    # and Origin+Destination queries all work.
    destination_options = _safe_options(finder_source, "DESTINATION")
    with finder_cols[1]:
        finder_destination = st.selectbox(
            "Destination",
            [""] + destination_options,
            index=0,
            key="rate_finder_destination_v2",
            format_func=lambda x: "Select destination" if x == "" else x,
        )

    with finder_cols[2]:
        finder_rate_type = st.selectbox(
            "Rate Type",
            ["All", "Tariff Rate", "Contractual Rate"],
            key="rate_finder_type_v2",
        )

    customer_source = finder_source
    if finder_origin:
        customer_source = customer_source[customer_source["ORIGIN"].eq(finder_origin)]
    if finder_destination:
        customer_source = customer_source[customer_source["DESTINATION"].eq(finder_destination)]
    if finder_rate_type != "All":
        customer_source = customer_source[
            customer_source["RATE_TYPE_GROUP"].eq(finder_rate_type.upper())
        ]
    customer_options = _safe_options(customer_source, "CUSTOMER_NAME")
    with finder_cols[3]:
        finder_customer = st.selectbox(
            "Customer (optional)",
            [""] + customer_options,
            index=0,
            key="rate_finder_customer_v2",
            format_func=lambda x: "All customers" if x == "" else x,
        )

    with finder_cols[4]:
        finder_weight = st.number_input(
            "Weight (optional)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="rate_finder_weight_v2",
            help="If entered, only rate slabs covering this weight are shown.",
        )

    finder_results = finder_source
    if finder_origin:
        finder_results = finder_results[finder_results["ORIGIN"].eq(finder_origin)]
    if finder_destination:
        finder_results = finder_results[finder_results["DESTINATION"].eq(finder_destination)]
    if finder_rate_type != "All":
        finder_results = finder_results[
            finder_results["RATE_TYPE_GROUP"].eq(finder_rate_type.upper())
        ]
    if finder_customer:
        finder_results = finder_results[finder_results["CUSTOMER_NAME"].eq(finder_customer)]

    if finder_weight > 0 and not finder_results.empty:
        from_wt = pd.to_numeric(finder_results["FROMWT"], errors="coerce")
        to_wt = pd.to_numeric(finder_results["TOWT"], errors="coerce")
        weight_mask = (
            (from_wt.isna() | from_wt.le(finder_weight))
            & (to_wt.isna() | to_wt.eq(0) | to_wt.ge(finder_weight))
        )
        finder_results = finder_results[weight_mask]

    if not finder_origin and not finder_destination:
        st.info("Select at least **Origin** or **Destination** to query the applicable rate.")
    elif finder_results.empty:
        st.warning("No active rate found for the selected route and criteria.")
    else:
        finder_results = finder_results.sort_values(
            ["RATE_TYPE_GROUP", "CUSTOMER_NAME", "FROMWT", "TOWT", "FROMDT"],
            na_position="last",
        ).copy()
        finder_results["RATE_TYPE_GROUP"] = finder_results["RATE_TYPE_GROUP"].map(_rate_type_display)

        tariff_count = int(finder_results["RATE_TYPE_GROUP"].eq("Tariff Rate").sum())
        contractual_count = int(finder_results["RATE_TYPE_GROUP"].eq("Contractual Rate").sum())
        active_charge_count = sum(
            pd.to_numeric(finder_results[col], errors="coerce").fillna(0).ne(0).any()
            for col in charge_columns
            if col in finder_results.columns
        )
        kpi_html = f"""
        <div class="quick-kpi-wrap">
            <div class="quick-kpi"><div class="kpi-label">Matching Rates</div><div class="kpi-value">{len(finder_results):,}</div></div>
            <div class="quick-kpi"><div class="kpi-label">Tariff</div><div class="kpi-value">{tariff_count:,}</div></div>
            <div class="quick-kpi"><div class="kpi-label">Contractual</div><div class="kpi-value">{contractual_count:,}</div></div>
            <div class="quick-kpi"><div class="kpi-label">Active Charge Types</div><div class="kpi-value">{active_charge_count:,}</div></div>
        </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)

        finder_display_cols = [
            "RATE_TYPE_GROUP", "CUSTOMER_NAME", "RATEFOR", "RATEID",
            "ORIGIN", "DESTINATION", "FROMDT", "TODT",
            "FROMWT", "TOWT", "MINCWEIGHT", "RATETYPE",
            "GOODS", "VEHICLE_TYPE", "VIA_BORDER",
            "PCKGRATE", "RATE1", "FLAT_AMOUNT", "RATECATEGORY",
        ] + charge_columns
        finder_display_cols = [col for col in finder_display_cols if col in finder_results.columns]

        finder_page = _paged_frame(
            finder_results[finder_display_cols],
            "finder_grid",
            default_size=100,
        )
        _render_rate_grid(finder_page, height=500)

        prepare_finder_download = st.checkbox(
            "Prepare rate finder CSV download",
            value=False,
            key="rate_finder_prepare_download_v3",
        )
        if prepare_finder_download:
            st.download_button(
                "Download complete rate finder result (CSV)",
                finder_results[finder_display_cols].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"rate_finder_{active_date:%Y%m%d}.csv",
                mime="text/csv",
                key="rate_finder_download_v3",
            )

