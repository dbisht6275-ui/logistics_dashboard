from __future__ import annotations

from datetime import date

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
DECLARE @AsOnDate DATE = CAST(:active_on AS DATE);
DECLARE @ScopeType VARCHAR(20) = LOWER(LTRIM(RTRIM(CAST(:scope_type AS VARCHAR(20)))));
DECLARE @ScopeValue VARCHAR(100) = LTRIM(RTRIM(CAST(:scope_value AS VARCHAR(100))));

SELECT
    COALESCE(RT.CUSTCODE, RT.CNGECODE, RT.CNGRCODE) AS CUSTOMER_CODE,
    CASE
        WHEN RT.CUSTCODE = '0000007565' THEN 'TARIFF RATE'
        ELSE 'CONTRACTUAL RATE'
    END AS RATE_TYPE_GROUP,
    CASE
        WHEN RT.CUSTCODE = '0000007565' THEN 'TARIFF RATE'
        ELSE COALESCE(C.CUSTNAME, E.NAME, R.NAME)
    END AS CUSTOMER_NAME,
    CASE RT.RATEFOR
        WHEN 'E' THEN 'CONSIGNEE'
        WHEN 'R' THEN 'CONSIGNOR'
        WHEN 'C' THEN 'CREDIT CUSTOMER'
        ELSE 'N/A'
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
    RT.RATECATEGORY
FROM RATEMAST RT
INNER JOIN VIEWSTATIONMAST ORG ON ORG.STNCODE = RT.ORGCODE
INNER JOIN VIEWSTATIONMAST DEST ON DEST.STNCODE = RT.DESTCODE
LEFT JOIN VEHICLETYPEMAST VM ON VM.TYPECODE = RT.VEHICLETYPECODE
LEFT JOIN PRODUCTMAST PR ON PR.PRODCODE = RT.PRODUCTCODE
LEFT JOIN STATIONMAST VIA ON VIA.STNCODE = RT.VIABORDERSTNCODE
LEFT JOIN VIEWGOODSMAST G ON G.ITEMCODE = RT.GOODSGROUPCODE
LEFT JOIN CNGRCNGEMAST E ON E.CODE = RT.CNGECODE
LEFT JOIN CNGRCNGEMAST R ON R.CODE = RT.CNGRCODE
LEFT JOIN CUSTMAST C ON C.CUSTCODE = RT.CUSTCODE
WHERE RT.TODT > @AsOnDate
  AND
  (
      @ScopeType = ''
      OR
      (
          @ScopeType = 'branch'
          AND
          (
              LOWER(LTRIM(RTRIM(ISNULL(ORG.STNNAME, '')))) = LOWER(@ScopeValue)
              OR LOWER(LTRIM(RTRIM(ISNULL(DEST.STNNAME, '')))) = LOWER(@ScopeValue)
          )
      )
      OR
      (
          @ScopeType = 'circle'
          AND
          (
              LOWER(LTRIM(RTRIM(ISNULL(ORG.HUBNAME, '')))) = LOWER(@ScopeValue)
              OR LOWER(LTRIM(RTRIM(ISNULL(DEST.HUBNAME, '')))) = LOWER(@ScopeValue)
          )
      )
      OR
      (
          @ScopeType = 'zone'
          AND
          (
              LOWER(LTRIM(RTRIM(ISNULL(ORG.ZONENAME, '')))) = LOWER(@ScopeValue)
              OR LOWER(LTRIM(RTRIM(ISNULL(DEST.ZONENAME, '')))) = LOWER(@ScopeValue)
          )
      )
  )
ORDER BY RT.FROMDT, ORG.STNNAME, DEST.STNNAME;
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
        .block-container {max-width:100%; padding:.45rem .75rem 1rem !important;}
        div[data-testid="stHorizontalBlock"] {gap:.45rem !important; align-items:flex-start !important;}
        div[data-testid="stSelectbox"] > label,
        div[data-testid="stMultiSelect"] > label,
        div[data-testid="stDateInput"] > label {
            color:#243b53 !important;
            font-size:10px !important;
            font-weight:500 !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
        div[data-testid="stDateInput"] input {
            min-height:38px !important;
            border:1px solid #a9bfd8 !important;
            border-radius:9px !important;
            background:linear-gradient(180deg,#f9fbfe 0%,#eef4fa 58%,#e4edf7 100%) !important;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.95),0 2px 5px rgba(30,64,105,.08) !important;
        }
        div[data-testid="stDataFrame"] {border:1px solid #dbe4ef; border-radius:10px; overflow:hidden;}
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


# =============================================================================
# Page
# =============================================================================
_inject_css()

scope_type, scope_value = _get_login_scope()

st.markdown("## Tariff & Contractual Rate Dashboard")
if scope_type:
    st.caption(
        f"Data access: {scope_type.title()} = {scope_value}. "
        "Permitted rates include the assigned scope on either Origin or Destination side."
    )
else:
    st.caption("Full-network rate visibility. Use the cascading filters below to refine rates.")

header_cols = st.columns([1.0, 1.0, 4.0])
with header_cols[0]:
    active_date = st.date_input("Active on", date.today(), key="rate_active_on_v2")
with header_cols[1]:
    st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)
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

expiry_tab, records_tab = st.tabs(["Expiry Watch", "Rate Records"])


with expiry_tab:
    expiry = filtered[filtered["TODT"].notna()].copy()
    expiry["DAYS_TO_EXPIRY"] = (expiry["TODT"].dt.normalize() - as_on_ts.normalize()).dt.days
    expiry = expiry.sort_values(["DAYS_TO_EXPIRY", "ORIGIN", "DESTINATION"])

    expiry_window = st.selectbox(
        "Expiry Window",
        ["30 days", "60 days", "90 days", "All active"],
        key="rate_expiry_window_v2",
    )
    day_limit = {"30 days": 30, "60 days": 60, "90 days": 90}.get(expiry_window)
    if day_limit is not None:
        expiry = expiry[expiry["DAYS_TO_EXPIRY"].between(0, day_limit)]

    expiry_cols = [
        "RATE_TYPE_GROUP", "CUSTOMER_NAME", "ORIGIN", "DESTINATION",
        "PRODUCT_NAME", "FROMDT", "TODT", "DAYS_TO_EXPIRY",
        "FROMWT", "TOWT", "SLAB1", "RATE1", "FLAT_AMOUNT",
    ]
    expiry_cols = [col for col in expiry_cols if col in expiry.columns]
    display_expiry = expiry[expiry_cols].copy()
    if "RATE_TYPE_GROUP" in display_expiry.columns:
        display_expiry["RATE_TYPE_GROUP"] = display_expiry["RATE_TYPE_GROUP"].map(_rate_type_display)

    st.dataframe(
        display_expiry,
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "FROMDT": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "TODT": st.column_config.DateColumn(format="DD-MM-YYYY"),
        },
    )


with records_tab:
    display_records = filtered.copy()
    display_records["RATE_TYPE_GROUP"] = display_records["RATE_TYPE_GROUP"].map(_rate_type_display)

    st.dataframe(
        display_records,
        use_container_width=True,
        hide_index=True,
        height=580,
        column_config={
            "FROMDT": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "TODT": st.column_config.DateColumn(format="DD-MM-YYYY"),
        },
    )

    st.download_button(
        "Download filtered rates (CSV)",
        display_records.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"rate_dashboard_{active_date:%Y%m%d}.csv",
        mime="text/csv",
        key="rate_download_v2",
    )
