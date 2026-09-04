from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


# -----------------------------------------------------------------------------
# Database connection
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Main query
#
# Security / role rule:
#   branch scope -> assigned branch can be EITHER origin OR destination
#   circle scope -> assigned circle can be EITHER origin OR destination
#   zone scope   -> assigned zone can be EITHER origin OR destination
#   no scope     -> full network
# -----------------------------------------------------------------------------
QUERY = r"""
DECLARE @AsOnDate DATE = CAST(:active_on AS DATE);
DECLARE @ScopeType VARCHAR(20) = LOWER(CAST(:scope_type AS VARCHAR(20)));
DECLARE @ScopeValue VARCHAR(100) = CAST(:scope_value AS VARCHAR(100));

SELECT
    COALESCE(RT.CUSTCODE,RT.CNGECODE,RT.CNGRCODE) AS CUSTOMER_CODE,
    CASE
        WHEN RT.CUSTCODE = '0000007565' THEN 'TARIFF RATE'
        ELSE 'CONTRACTUAL RATE'
    END AS RATE_TYPE_GROUP,
    CASE
        WHEN RT.CUSTCODE = '0000007565' THEN 'TARIFF RATE'
        ELSE COALESCE(C.CUSTNAME,E.NAME,R.NAME)
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
    RT.RATECATEGORY,
    ISNULL(CHG.BOE,0) AS BOE,
    ISNULL(CHG.CNCHG,0) AS CN_CHARGE,
    ISNULL(CHG.COD,0) AS COD_DOD,
    ISNULL(CHG.DD,0) AS DD,
    ISNULL(CHG.FOV,0) AS FOV,
    ISNULL(CHG.FOD,0) AS FOD,
    ISNULL(CHG.FUEL,0) AS FUEL_SUR,
    ISNULL(CHG.HANDLING,0) AS HANDLING,
    ISNULL(CHG.MISC,0) AS MISC,
    ISNULL(CHG.ODA,0) AS ODA,
    ISNULL(CHG.PICKUP,0) AS PICKUP,
    ISNULL(CHG.ST,0) AS ST,
    ISNULL(CHG.SA,0) AS SA_SF,
    ISNULL(CHG.TPND,0) AS TPND,
    ISNULL(CHG.ICCNCC,0) AS ICC_NCC
FROM RATEMAST RT
INNER JOIN VIEWSTATIONMAST ORG ON ORG.STNCODE=RT.ORGCODE
INNER JOIN VIEWSTATIONMAST DEST ON DEST.STNCODE=RT.DESTCODE
LEFT JOIN VEHICLETYPEMAST VM ON VM.TYPECODE=RT.VEHICLETYPECODE
LEFT JOIN PRODUCTMAST PR ON PR.PRODCODE=RT.PRODUCTCODE
LEFT JOIN STATIONMAST VIA ON VIA.STNCODE=RT.VIABORDERSTNCODE
LEFT JOIN VIEWGOODSMAST G ON G.ITEMCODE=RT.GOODSGROUPCODE
LEFT JOIN CNGRCNGEMAST E ON E.CODE=RT.CNGECODE
LEFT JOIN CNGRCNGEMAST R ON R.CODE=RT.CNGRCODE
LEFT JOIN CUSTMAST C ON C.CUSTCODE=RT.CUSTCODE
OUTER APPLY
(
    SELECT
        MAX(CASE WHEN X.CHGCODE='A0098' THEN X.VAL END) AS BOE,
        MAX(CASE WHEN X.CHGCODE='A0120' THEN X.VAL END) AS CNCHG,
        MAX(CASE WHEN X.CHGCODE='A0106' THEN X.VAL END) AS COD,
        MAX(CASE WHEN X.CHGCODE='A0123' THEN X.VAL END) AS DD,
        MAX(CASE WHEN X.CHGCODE='A0107' THEN X.VAL END) AS FOV,
        MAX(CASE WHEN X.CHGCODE='A0093' THEN X.VAL END) AS FOD,
        MAX(CASE WHEN X.CHGCODE='A0113' THEN X.VAL END) AS FUEL,
        MAX(CASE WHEN X.CHGCODE='A0103' THEN X.VAL END) AS HANDLING,
        MAX(CASE WHEN X.CHGCODE='A0114' THEN X.VAL END) AS MISC,
        MAX(CASE WHEN X.CHGCODE='A0105' THEN X.VAL END) AS ODA,
        MAX(CASE WHEN X.CHGCODE='A0110' THEN X.VAL END) AS PICKUP,
        MAX(CASE WHEN X.CHGCODE='A0108' THEN X.VAL END) AS ST,
        MAX(CASE WHEN X.CHGCODE='A0121' THEN X.VAL END) AS SA,
        MAX(CASE WHEN X.CHGCODE='A0104' THEN X.VAL END) AS TPND,
        MAX(CASE WHEN X.CHGCODE='A0005' THEN X.VAL END) AS ICCNCC
    FROM
    (
        SELECT
            CC.CHGCODE,
            CASE
                WHEN V.CHGAMT_VALUE > 0 THEN V.CHGAMT_VALUE
                ELSE V.CHGRATE_VALUE
            END AS VAL
        FROM CUSTCHRG CC
        CROSS APPLY
        (
            SELECT
                TRY_CONVERT(DECIMAL(18,2),CC.CHGAMT) AS CHGAMT_VALUE,
                TRY_CONVERT(DECIMAL(18,2),CC.CHGRATE) AS CHGRATE_VALUE
        ) V
        WHERE CC.RATEDATAID=RT.RATEDATAID
          AND CC.CHGCODE IN
          ('A0098','A0120','A0106','A0123','A0107','A0093','A0113','A0103',
           'A0114','A0105','A0110','A0108','A0121','A0104','A0005')
    ) X
) CHG
WHERE RT.TODT > @AsOnDate
  AND
  (
      @ScopeType = ''
      OR (@ScopeType = 'branch' AND (ORG.STNNAME = @ScopeValue OR DEST.STNNAME = @ScopeValue))
      OR (@ScopeType = 'circle' AND (ORG.HUBNAME = @ScopeValue OR DEST.HUBNAME = @ScopeValue))
      OR (@ScopeType = 'zone' AND (ORG.ZONENAME = @ScopeValue OR DEST.ZONENAME = @ScopeValue))
  )
ORDER BY RT.FROMDT, ORG.STNNAME, DEST.STNNAME;
"""


CHARGES = {
    "BOE": "B.O.E",
    "CN_CHARGE": "C.N. Charge",
    "COD_DOD": "COD/DOD",
    "DD": "D/D",
    "FOV": "F.O.V",
    "FOD": "FOD",
    "FUEL_SUR": "Fuel Surcharge",
    "HANDLING": "Handling",
    "MISC": "Misc",
    "ODA": "O.D.A",
    "PICKUP": "Pickup",
    "ST": "S.T",
    "SA_SF": "SA/SF",
    "TPND": "T.P.N.D",
    "ICC_NCC": "ICC/NCC",
}


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------
@st.cache_data(ttl=900, show_spinner=False)
def load_rates_v3(
    active_on: date,
    scope_type: str,
    scope_value: str,
) -> pd.DataFrame:
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


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _canon(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).casefold()


def _options(frame: pd.DataFrame, column: str) -> list[str]:
    if frame is None or frame.empty or column not in frame.columns:
        return []
    values = frame[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return sorted(values.unique().tolist(), key=str.casefold)


def _select_all(label: str, values: list[str], key: str, help_text: str | None = None) -> str:
    options = ["All"] + list(values)
    existing = st.session_state.get(key)
    if existing not in options:
        st.session_state[key] = "All"
    return st.selectbox(label, options, key=key, help=help_text)


def _apply_single(frame: pd.DataFrame, column: str, selected: str) -> pd.DataFrame:
    if selected == "All" or column not in frame.columns:
        return frame
    return frame[frame[column].fillna("").astype(str).eq(str(selected))]


def _get_login_scope() -> tuple[str, str]:
    """Return one configured employee data scope, using the existing login data_scope."""
    data_scope = st.session_state.get("data_scope", {}) or {}

    # Most specific scope wins if malformed config ever contains more than one key.
    for scope_type in ("branch", "circle", "zone"):
        value = data_scope.get(scope_type)
        if value is not None and str(value).strip():
            return scope_type, str(value).strip()

    return "", ""


def _scope_masks(frame: pd.DataFrame, scope_type: str, scope_value: str) -> tuple[pd.Series, pd.Series]:
    """Return masks showing whether the logged-in scope appears on origin/destination side."""
    false_mask = pd.Series(False, index=frame.index)
    if not scope_type or not scope_value or frame.empty:
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


def _add_scope_direction(frame: pd.DataFrame, scope_type: str, scope_value: str) -> pd.DataFrame:
    result = frame.copy()
    if not scope_type:
        result["SCOPE_DIRECTION"] = "Network"
        return result

    org_mask, dest_mask = _scope_masks(result, scope_type, scope_value)
    result["SCOPE_DIRECTION"] = ""
    result.loc[org_mask & ~dest_mask, "SCOPE_DIRECTION"] = "Outbound"
    result.loc[~org_mask & dest_mask, "SCOPE_DIRECTION"] = "Inbound"
    result.loc[org_mask & dest_mask, "SCOPE_DIRECTION"] = "Within scope"
    result.loc[result["SCOPE_DIRECTION"].eq(""), "SCOPE_DIRECTION"] = "Other"
    return result


def _route_count(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    return frame[["ORIGIN", "DESTINATION"]].drop_duplicates().shape[0]


def _rate_type_label(value: str) -> str:
    mapping = {
        "TARIFF RATE": "Tariff Rate",
        "CONTRACTUAL RATE": "Contractual Rate",
    }
    return mapping.get(value, value.title())


# -----------------------------------------------------------------------------
# Page header + role context
# -----------------------------------------------------------------------------
st.title("Rate Dashboard")
st.caption("Role-aware tariff and contractual rate coverage across the network")

scope_type, scope_value = _get_login_scope()
role_name = st.session_state.get("role", "viewer")
employee_name = st.session_state.get("employee_name") or st.session_state.get("username", "User")

if scope_type:
    st.info(
        f"**{scope_type.title()} access: {scope_value}**  |  "
        f"Showing every active rate where **{scope_value} is on either the Origin side or the Destination side**."
    )
else:
    st.info("**Full network access**  |  No Zone / Circle / Branch data restriction is assigned to this login.")

header_cols = st.columns([1.0, 1.2, 2.8, 1.0])
active_date = header_cols[0].date_input("Active on", date.today(), key="rate_active_date_v3")
header_cols[1].text_input("Login", value=str(employee_name), disabled=True, key="rate_login_name_v3")
header_cols[2].text_input(
    "Data scope",
    value=(f"{scope_type.title()}: {scope_value}" if scope_type else "Full Network"),
    disabled=True,
    key="rate_scope_display_v3",
)
load = header_cols[3].button("Load Dashboard", type="primary", use_container_width=True)

load_key = (active_date, scope_type, scope_value)
if load:
    try:
        with st.spinner("Loading permitted rate data..."):
            loaded = load_rates_v3(active_date, scope_type, scope_value)
            st.session_state["rate_dashboard_data_v3"] = loaded
            st.session_state["rate_dashboard_key_v3"] = load_key
    except Exception as exc:
        st.error("Rate data could not be loaded.")
        with st.expander("Technical details"):
            st.code(str(exc))
        st.stop()

if st.session_state.get("rate_dashboard_key_v3") != load_key:
    st.info("Click **Load Dashboard** to load rates for the selected date and your assigned data rights.")
    st.stop()

data = st.session_state.get("rate_dashboard_data_v3", pd.DataFrame()).copy()
if data.empty:
    if scope_type:
        st.warning(
            f"No active rates were found where {scope_value} appears on the origin or destination side."
        )
    else:
        st.warning("No active rates were found for the selected date.")
    st.stop()

required_columns = {
    "RATE_TYPE_GROUP",
    "ORG_ZONE",
    "ORG_CIRCLE",
    "ORIGIN",
    "DEST_ZONE",
    "DEST_CIRCLE",
    "DESTINATION",
}
missing_columns = sorted(required_columns.difference(data.columns))
if missing_columns:
    load_rates_v3.clear()
    st.error(
        "The deployed SQL result is missing required columns: " + ", ".join(missing_columns)
    )
    st.stop()

for col in ("FROMDT", "TODT"):
    data[col] = pd.to_datetime(data[col], errors="coerce")

for col in (
    "SLAB1",
    "RATE1",
    "FROMWT",
    "TOWT",
    "MINCWEIGHT",
    "FLAT_AMOUNT",
    "PCKGRATE",
):
    if col in data.columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

# Rate groups are based ONLY on RT.CUSTCODE.
data["RATE_TYPE_GROUP"] = data["RATE_TYPE_GROUP"].fillna("").astype(str).str.upper().str.strip()
data = _add_scope_direction(data, scope_type, scope_value)

# Defensive security check in Python too. SQL already applies the same rule.
if scope_type:
    org_scope_mask, dest_scope_mask = _scope_masks(data, scope_type, scope_value)
    data = data[org_scope_mask | dest_scope_mask].copy()
    if data.empty:
        st.warning("No records remain inside your assigned data scope.")
        st.stop()


# -----------------------------------------------------------------------------
# Filters
# -----------------------------------------------------------------------------
st.markdown("### Filters")

primary_filters = st.columns([1.15, 1.15, 1.25, 1.35])
with primary_filters[0]:
    rate_type_filter = st.selectbox(
        "Rate Type",
        ["All", "Tariff Rate", "Contractual Rate"],
        key="rate_type_filter_v3",
    )

working = data.copy()
if rate_type_filter != "All":
    working = working[
        working["RATE_TYPE_GROUP"].eq(rate_type_filter.upper())
    ]

with primary_filters[1]:
    if scope_type:
        direction_values = [
            x for x in ["Outbound", "Inbound", "Within scope"]
            if x in working["SCOPE_DIRECTION"].dropna().unique().tolist()
        ]
        direction_filter = _select_all(
            "Scope Direction",
            direction_values,
            "rate_direction_filter_v3",
            help_text=(
                "Outbound = assigned scope is on Origin side; Inbound = assigned scope is on Destination side."
            ),
        )
    else:
        direction_filter = "All"
        st.selectbox(
            "Scope Direction",
            ["Full Network"],
            disabled=True,
            key="rate_direction_full_v3",
        )

if scope_type and direction_filter != "All":
    working = working[working["SCOPE_DIRECTION"].eq(direction_filter)]

with primary_filters[2]:
    product_filter = _select_all(
        "Product",
        _options(working, "PRODUCT_NAME"),
        "rate_product_filter_v3",
    )
working = _apply_single(working, "PRODUCT_NAME", product_filter)

with primary_filters[3]:
    rate_for_filter = _select_all(
        "Rate Applicable To",
        _options(working, "RATEFOR"),
        "rate_for_filter_v3",
    )
working = _apply_single(working, "RATEFOR", rate_for_filter)

# Origin hierarchy
st.caption("Origin hierarchy")
origin_filters = st.columns(3)
with origin_filters[0]:
    org_zone = _select_all("Origin Zone", _options(working, "ORG_ZONE"), "rate_org_zone_v3")
working = _apply_single(working, "ORG_ZONE", org_zone)

with origin_filters[1]:
    org_circle = _select_all("Origin Circle", _options(working, "ORG_CIRCLE"), "rate_org_circle_v3")
working = _apply_single(working, "ORG_CIRCLE", org_circle)

with origin_filters[2]:
    origin = _select_all("Origin Branch", _options(working, "ORIGIN"), "rate_origin_v3")
working = _apply_single(working, "ORIGIN", origin)

# Destination hierarchy
st.caption("Destination hierarchy")
destination_filters = st.columns(3)
with destination_filters[0]:
    dest_zone = _select_all("Destination Zone", _options(working, "DEST_ZONE"), "rate_dest_zone_v3")
working = _apply_single(working, "DEST_ZONE", dest_zone)

with destination_filters[1]:
    dest_circle = _select_all("Destination Circle", _options(working, "DEST_CIRCLE"), "rate_dest_circle_v3")
working = _apply_single(working, "DEST_CIRCLE", dest_circle)

with destination_filters[2]:
    destination = _select_all("Destination Branch", _options(working, "DESTINATION"), "rate_destination_v3")
working = _apply_single(working, "DESTINATION", destination)

filtered = working.copy()
if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()


# -----------------------------------------------------------------------------
# KPI layer
# -----------------------------------------------------------------------------
as_on_ts = pd.Timestamp(active_date)
expiry_end = as_on_ts + pd.Timedelta(days=30)
expiring = filtered[
    filtered["TODT"].notna() & filtered["TODT"].between(as_on_ts, expiry_end)
]

unique_routes = _route_count(filtered)
tariff_routes = _route_count(filtered[filtered["RATE_TYPE_GROUP"].eq("TARIFF RATE")])
contractual_routes = _route_count(filtered[filtered["RATE_TYPE_GROUP"].eq("CONTRACTUAL RATE")])
all_branches = set(_options(filtered, "ORIGIN")) | set(_options(filtered, "DESTINATION"))
if scope_type == "branch":
    all_branches = {b for b in all_branches if _canon(b) != _canon(scope_value)}
connected_branches = len(all_branches)

metrics = st.columns(6)
metrics[0].metric("Active Rate Records", f"{len(filtered):,}")
metrics[1].metric("Unique Routes", f"{unique_routes:,}")
metrics[2].metric("Tariff Routes", f"{tariff_routes:,}")
metrics[3].metric("Contractual Routes", f"{contractual_routes:,}")
metrics[4].metric("Connected Branches", f"{connected_branches:,}")
metrics[5].metric("Expiring in 30 Days", f"{len(expiring):,}")


# -----------------------------------------------------------------------------
# Dashboard tabs
# -----------------------------------------------------------------------------
overview_tab, route_tab, charge_tab, expiry_tab, records_tab = st.tabs(
    [
        "Overview",
        "Route & Rate Analysis",
        "Additional Charges",
        "Expiry Watch",
        "Rate Records",
    ]
)


with overview_tab:
    # Rate-type coverage: route count is more useful than a raw average rate because
    # RATE1 can represent different products / slabs / rate structures.
    type_records = (
        filtered.groupby("RATE_TYPE_GROUP", dropna=False)
        .agg(RECORDS=("RATEID", "size"))
        .reset_index()
    )
    type_routes = (
        filtered[["RATE_TYPE_GROUP", "ORIGIN", "DESTINATION"]]
        .drop_duplicates()
        .groupby("RATE_TYPE_GROUP", dropna=False)
        .size()
        .reset_index(name="ROUTES")
    )
    type_summary = type_records.merge(type_routes, on="RATE_TYPE_GROUP", how="left")
    type_summary["Rate Type"] = type_summary["RATE_TYPE_GROUP"].map(_rate_type_label)

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(
            px.bar(
                type_summary,
                x="Rate Type",
                y="ROUTES",
                text_auto=True,
                title="Route Coverage by Rate Type",
                labels={"ROUTES": "Unique Routes"},
            ),
            use_container_width=True,
        )

    with chart_right:
        if scope_type:
            direction_summary = (
                filtered[["SCOPE_DIRECTION", "ORIGIN", "DESTINATION"]]
                .drop_duplicates()
                .groupby("SCOPE_DIRECTION")
                .size()
                .reset_index(name="ROUTES")
            )
            direction_order = ["Outbound", "Inbound", "Within scope"]
            direction_summary["_order"] = direction_summary["SCOPE_DIRECTION"].map(
                {name: i for i, name in enumerate(direction_order)}
            )
            direction_summary = direction_summary.sort_values("_order")
            st.plotly_chart(
                px.bar(
                    direction_summary,
                    x="SCOPE_DIRECTION",
                    y="ROUTES",
                    text_auto=True,
                    title=f"{scope_value}: Inbound / Outbound Route Coverage",
                    labels={"SCOPE_DIRECTION": "Direction", "ROUTES": "Unique Routes"},
                ),
                use_container_width=True,
            )
        else:
            zone_summary = (
                filtered[["ORG_ZONE", "ORIGIN", "DESTINATION"]]
                .drop_duplicates()
                .groupby("ORG_ZONE", dropna=False)
                .size()
                .reset_index(name="ROUTES")
                .sort_values("ROUTES", ascending=False)
                .head(15)
            )
            st.plotly_chart(
                px.bar(
                    zone_summary,
                    x="ROUTES",
                    y="ORG_ZONE",
                    orientation="h",
                    text_auto=True,
                    title="Top Origin Zones by Route Coverage",
                    labels={"ORG_ZONE": "Origin Zone", "ROUTES": "Unique Routes"},
                ),
                use_container_width=True,
            )

    # Zone-to-zone network flow matrix.
    route_level = filtered[["ORG_ZONE", "DEST_ZONE", "ORIGIN", "DESTINATION"]].drop_duplicates()
    zone_flow = (
        route_level.groupby(["ORG_ZONE", "DEST_ZONE"], dropna=False)
        .size()
        .reset_index(name="ROUTES")
    )
    if not zone_flow.empty:
        st.plotly_chart(
            px.density_heatmap(
                zone_flow,
                x="DEST_ZONE",
                y="ORG_ZONE",
                z="ROUTES",
                histfunc="sum",
                text_auto=True,
                title="Origin Zone to Destination Zone Route Matrix",
                labels={"ORG_ZONE": "Origin Zone", "DEST_ZONE": "Destination Zone", "ROUTES": "Routes"},
            ),
            use_container_width=True,
        )

    # Most connected routes under current filters.
    top_routes = (
        filtered.assign(
            ROUTE=filtered["ORIGIN"].fillna("N/A") + " -> " + filtered["DESTINATION"].fillna("N/A")
        )
        .groupby("ROUTE")
        .agg(RECORDS=("RATEID", "size"))
        .reset_index()
        .sort_values("RECORDS", ascending=False)
        .head(15)
        .sort_values("RECORDS")
    )
    if not top_routes.empty:
        st.plotly_chart(
            px.bar(
                top_routes,
                x="RECORDS",
                y="ROUTE",
                orientation="h",
                text_auto=True,
                title="Top 15 Route Definitions",
                labels={"RECORDS": "Rate Records", "ROUTE": "Route"},
            ),
            use_container_width=True,
        )


with route_tab:
    route_summary = (
        filtered.groupby(
            ["RATE_TYPE_GROUP", "ORG_ZONE", "ORG_CIRCLE", "ORIGIN", "DEST_ZONE", "DEST_CIRCLE", "DESTINATION", "PRODUCT_NAME"],
            dropna=False,
            as_index=False,
        )
        .agg(
            RATE_RECORDS=("RATEID", "size"),
            MIN_RATE1=("RATE1", "min"),
            AVG_RATE1=("RATE1", "mean"),
            MAX_RATE1=("RATE1", "max"),
            MIN_FROM_WEIGHT=("FROMWT", "min"),
            MAX_TO_WEIGHT=("TOWT", "max"),
            EARLIEST_EXPIRY=("TODT", "min"),
        )
    )
    route_summary["Rate Type"] = route_summary["RATE_TYPE_GROUP"].map(_rate_type_label)

    ranking_cols = st.columns([1.2, 1.0, 2.0])
    with ranking_cols[0]:
        rank_mode = st.selectbox(
            "Rate1 Ranking",
            ["Highest Rate1", "Lowest Rate1"],
            key="rate_rank_mode_v3",
        )
    with ranking_cols[1]:
        rank_limit = st.slider("Routes to show", 5, 30, 15, key="rate_rank_limit_v3")
    with ranking_cols[2]:
        st.caption(
            "Rate1 ranking is shown only after your current Product / Route / Rate Type filters. "
            "Avoid comparing Rate1 across unlike products or rate structures."
        )

    rank_source = route_summary.dropna(subset=["AVG_RATE1"]).copy()
    if not rank_source.empty:
        rank_source["ROUTE"] = rank_source["ORIGIN"].fillna("N/A") + " -> " + rank_source["DESTINATION"].fillna("N/A")
        rank_source = rank_source.sort_values(
            "AVG_RATE1",
            ascending=(rank_mode == "Lowest Rate1"),
        ).head(rank_limit)
        rank_source = rank_source.sort_values("AVG_RATE1")
        st.plotly_chart(
            px.bar(
                rank_source,
                x="AVG_RATE1",
                y="ROUTE",
                orientation="h",
                text_auto=".2f",
                hover_data=["PRODUCT_NAME", "Rate Type"],
                title="Filtered Route Rate1 Comparison",
                labels={"AVG_RATE1": "Average Rate1", "ROUTE": "Route"},
            ),
            use_container_width=True,
        )

    display_route_summary = route_summary.rename(
        columns={
            "RATE_TYPE_GROUP": "RATE TYPE CODE",
            "PRODUCT_NAME": "PRODUCT",
        }
    )
    st.dataframe(
        display_route_summary.sort_values(["ORIGIN", "DESTINATION", "PRODUCT"], na_position="last"),
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "EARLIEST_EXPIRY": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "AVG_RATE1": st.column_config.NumberColumn(format="%.2f"),
            "MIN_RATE1": st.column_config.NumberColumn(format="%.2f"),
            "MAX_RATE1": st.column_config.NumberColumn(format="%.2f"),
        },
    )


with charge_tab:
    charge_cols = [col for col in CHARGES if col in filtered.columns]
    if not charge_cols:
        st.info("No additional-charge columns are available in the query result.")
    else:
        numeric = filtered[charge_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        charges = pd.DataFrame(
            {
                "Charge": [CHARGES[col] for col in charge_cols],
                "Configured Records": [(numeric[col] != 0).sum() for col in charge_cols],
                "Coverage %": [
                    round(((numeric[col] != 0).sum() / len(numeric)) * 100, 1)
                    if len(numeric) else 0
                    for col in charge_cols
                ],
                "Average Non-Zero Value": [
                    numeric.loc[numeric[col] != 0, col].mean()
                    if (numeric[col] != 0).any()
                    else 0
                    for col in charge_cols
                ],
                "Maximum Value": [numeric[col].max() for col in charge_cols],
            }
        )

        st.plotly_chart(
            px.bar(
                charges.sort_values("Configured Records"),
                x="Configured Records",
                y="Charge",
                orientation="h",
                text_auto=True,
                title="Additional Charge Coverage",
            ),
            use_container_width=True,
        )
        st.dataframe(
            charges.sort_values("Configured Records", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


with expiry_tab:
    future_expiry = filtered[
        filtered["TODT"].notna() & filtered["TODT"].ge(as_on_ts)
    ].copy()
    future_expiry["DAYS_TO_EXPIRY"] = (future_expiry["TODT"] - as_on_ts).dt.days

    expiry_metrics = st.columns(4)
    expiry_metrics[0].metric("0-7 Days", f"{len(future_expiry[future_expiry['DAYS_TO_EXPIRY'].between(0, 7)]):,}")
    expiry_metrics[1].metric("8-30 Days", f"{len(future_expiry[future_expiry['DAYS_TO_EXPIRY'].between(8, 30)]):,}")
    expiry_metrics[2].metric("31-60 Days", f"{len(future_expiry[future_expiry['DAYS_TO_EXPIRY'].between(31, 60)]):,}")
    expiry_metrics[3].metric("61+ Days", f"{len(future_expiry[future_expiry['DAYS_TO_EXPIRY'].ge(61)]):,}")

    expiry_table = future_expiry.sort_values(["TODT", "ORIGIN", "DESTINATION"]).copy()
    expiry_columns = [
        "RATE_TYPE_GROUP",
        "CUSTOMER_NAME",
        "ORG_ZONE",
        "ORG_CIRCLE",
        "ORIGIN",
        "DEST_ZONE",
        "DEST_CIRCLE",
        "DESTINATION",
        "PRODUCT_NAME",
        "TODT",
        "DAYS_TO_EXPIRY",
        "RATE1",
    ]
    expiry_columns = [c for c in expiry_columns if c in expiry_table.columns]
    st.dataframe(
        expiry_table[expiry_columns].head(500),
        use_container_width=True,
        hide_index=True,
        height=560,
        column_config={
            "TODT": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "DAYS_TO_EXPIRY": st.column_config.NumberColumn("Days to Expiry", format="%d"),
        },
    )


with records_tab:
    preferred_order = [
        "RATE_TYPE_GROUP",
        "SCOPE_DIRECTION",
        "CUSTOMER_CODE",
        "CUSTOMER_NAME",
        "RATEFOR",
        "ORG_ZONE",
        "ORG_CIRCLE",
        "ORIGIN",
        "DEST_ZONE",
        "DEST_CIRCLE",
        "DESTINATION",
        "FROMDT",
        "TODT",
        "PRODUCT_NAME",
        "GOODS",
        "VEHICLE_TYPE",
        "FROMWT",
        "TOWT",
        "MINCWEIGHT",
        "RATETYPE",
        "PCKGRATE",
        "SLAB1",
        "RATE1",
        "FLAT_AMOUNT",
        "RATECATEGORY",
        "VIA_BORDER",
    ]
    preferred_order += [c for c in CHARGES if c in filtered.columns]
    remaining = [c for c in filtered.columns if c not in preferred_order]
    display_columns = [c for c in preferred_order if c in filtered.columns] + remaining

    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
        height=620,
        column_config={
            "FROMDT": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "TODT": st.column_config.DateColumn(format="DD-MM-YYYY"),
        },
    )

    scope_slug = f"{scope_type}_{scope_value}" if scope_type else "full_network"
    safe_scope_slug = "_".join(scope_slug.lower().split())
    st.download_button(
        "Download filtered rates (CSV)",
        filtered[display_columns].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"rate_dashboard_{safe_scope_slug}_{date.today():%Y%m%d}.csv",
        mime="text/csv",
    )
