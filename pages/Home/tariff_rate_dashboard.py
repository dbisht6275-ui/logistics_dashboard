from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


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
DECLARE @OriginName VARCHAR(100) = CAST(:origin_name AS VARCHAR(100));
DECLARE @DestinationName VARCHAR(100) = CAST(:destination_name AS VARCHAR(100));

SELECT
    COALESCE(RT.CUSTCODE,RT.CNGECODE,RT.CNGRCODE) AS CUSTOMER_CODE,
    CASE
        WHEN RT.CUSTCODE = '0000007565' THEN 'TARIFF RATE'
        ELSE 'CONTRACTUAL RATE'
    END AS RATE_TYPE_GROUP,
    CASE
        WHEN RT.CUSTCODE = '0000007565'
        THEN 'TARIFF RATE'
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
    RT.FROMDT, RT.TODT, RT.FROMWT, RT.TOWT,
    PR.PRODNAME AS PRODUCT_NAME,
    G.ITEMNAME AS GOODS,
    VM.TYPENAME AS VEHICLE_TYPE,
    RT.MINCWEIGHT, RT.RATETYPE,
    VIA.STNNAME AS VIA_BORDER,
    RT.PCKGRATE, RT.SLAB1, RT.RATE1,
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
        SELECT CC.CHGCODE,
               CASE WHEN V.CHGAMT_VALUE > 0
                    THEN V.CHGAMT_VALUE ELSE V.CHGRATE_VALUE END AS VAL
        FROM CUSTCHRG CC
        CROSS APPLY
        (
            SELECT TRY_CONVERT(DECIMAL(18,2),CC.CHGAMT) AS CHGAMT_VALUE,
                   TRY_CONVERT(DECIMAL(18,2),CC.CHGRATE) AS CHGRATE_VALUE
        ) V
        WHERE CC.RATEDATAID=RT.RATEDATAID
          AND CC.CHGCODE IN
          ('A0098','A0120','A0106','A0123','A0107','A0093','A0113','A0103',
           'A0114','A0105','A0110','A0108','A0121','A0104','A0005')
    ) X
) CHG
WHERE RT.TODT > @AsOnDate
  AND ORG.STNNAME = @OriginName
  AND (@DestinationName='' OR DEST.STNNAME=@DestinationName)
ORDER BY RT.FROMDT;
"""

ORIGIN_QUERY = r"""
SELECT DISTINCT ORG.STNNAME AS ORIGIN
FROM RATEMAST RT
INNER JOIN VIEWSTATIONMAST ORG ON ORG.STNCODE=RT.ORGCODE
WHERE RT.TODT > CAST(:active_on AS DATE)
  AND ORG.STNNAME IS NOT NULL
ORDER BY ORG.STNNAME;
"""

DESTINATION_QUERY = r"""
SELECT DISTINCT DEST.STNNAME AS DESTINATION
FROM RATEMAST RT
INNER JOIN VIEWSTATIONMAST ORG ON ORG.STNCODE=RT.ORGCODE
INNER JOIN VIEWSTATIONMAST DEST ON DEST.STNCODE=RT.DESTCODE
WHERE RT.TODT > CAST(:active_on AS DATE)
  AND ORG.STNNAME=:origin_name
  AND DEST.STNNAME IS NOT NULL
ORDER BY DEST.STNNAME;
"""

CHARGES = {
    "BOE": "B.O.E", "CN_CHARGE": "C.N. Charge", "COD_DOD": "COD/DOD",
    "DD": "D/D", "FOV": "F.O.V", "FOD": "FOD",
    "FUEL_SUR": "Fuel Surcharge", "HANDLING": "Handling", "MISC": "Misc",
    "ODA": "O.D.A", "PICKUP": "Pickup", "ST": "S.T", "SA_SF": "SA/SF",
    "TPND": "T.P.N.D", "ICC_NCC": "ICC/NCC",
}


@st.cache_data(ttl=900, show_spinner=False)
def load_rates(
    active_on: date,
    origin_name: str,
    destination_name: str,
) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as cn:
        return pd.read_sql_query(
            text(QUERY),
            cn,
            params={
                "active_on": active_on,
                "origin_name": origin_name,
                "destination_name": destination_name,
            },
        )


@st.cache_data(ttl=3600, show_spinner=False)
def load_origins(active_on: date) -> list[str]:
    engine = get_engine()
    with engine.connect() as cn:
        frame = pd.read_sql_query(
            text(ORIGIN_QUERY),
            cn,
            params={"active_on": active_on},
        )
    return frame["ORIGIN"].dropna().astype(str).tolist()


@st.cache_data(ttl=3600, show_spinner=False)
def load_destinations(active_on: date, origin_name: str) -> list[str]:
    if not origin_name:
        return []
    engine = get_engine()
    with engine.connect() as cn:
        frame = pd.read_sql_query(
            text(DESTINATION_QUERY),
            cn,
            params={"active_on": active_on, "origin_name": origin_name},
        )
    return frame["DESTINATION"].dropna().astype(str).tolist()


def options(frame: pd.DataFrame, column: str) -> list[str]:
    return sorted(frame[column].dropna().astype(str).unique().tolist())


st.title("Rate Dashboard")
st.caption("Tariff and contractual rates by route, weight slabs and additional charges")

st.subheader("Search rates by route")
date_col, origin_col, destination_col = st.columns([1, 1.5, 1.5])
active_date = date_col.date_input("Active on", date.today())

try:
    origin_names = load_origins(active_date)
except Exception as exc:
    st.error("Origin list could not be loaded from the database.")
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()

origin_options = ["Select Origin"] + origin_names
origin_search = origin_col.selectbox("Origin", origin_options)
if origin_search == "Select Origin":
    origin_search = ""

try:
    destination_names = load_destinations(active_date, origin_search)
except Exception as exc:
    st.error("Destination list could not be loaded from the database.")
    with st.expander("Technical details"):
        st.code(str(exc))
    st.stop()

destination_options = ["All Destinations"] + destination_names
destination_search = destination_col.selectbox(
    "Destination (optional)",
    destination_options,
    disabled=not bool(origin_search),
)
if destination_search == "All Destinations":
    destination_search = ""

load = st.button("Load rates", type="primary")

if not origin_search:
    st.info("Select an **Origin**. Destination is optional.")
    st.stop()

key = (active_date, origin_search, destination_search)
if load:
    try:
        with st.spinner("Loading rates..."):
            st.session_state.tariff_data = load_rates(
                active_date,
                origin_search,
                destination_search,
            )
            st.session_state.tariff_key = key
    except Exception as exc:
        st.error("Rate data could not be loaded.")
        with st.expander("Technical details"):
            st.code(str(exc))
        st.stop()

if st.session_state.get("tariff_key") != key:
    st.info("Select the route and click **Load rates**.")
    st.stop()

data = st.session_state.get("tariff_data", pd.DataFrame()).copy()
if data.empty:
    st.warning("No active rates found.")
    st.stop()

for col in ("FROMDT", "TODT"):
    data[col] = pd.to_datetime(data[col], errors="coerce")
for col in ("SLAB1", "RATE1", "FROMWT", "TOWT", "MINCWEIGHT", "FLAT_AMOUNT"):
    data[col] = pd.to_numeric(data[col], errors="coerce")

# Divide records into two categories:
# 1) Tariff Rate      -> CUSTCODE = 0000007565
# 2) Contractual Rate -> every other CUSTCODE
rate_category = st.radio(
    "Rate category",
    ["Tariff Rate", "Contractual Rate"],
    horizontal=True,
)
selected_group = rate_category.upper()
data = data[data["RATE_TYPE_GROUP"] == selected_group].copy()

if data.empty:
    st.warning(f"No active {rate_category.lower()} records found for the selected route.")
    st.stop()

with st.expander("Refine loaded results", expanded=True):
    filter_row1 = st.columns(3)
    rate_for = filter_row1[0].multiselect("Rate applicable to", options(data, "RATEFOR"))
    origins = filter_row1[1].multiselect("Origin", options(data, "ORIGIN"))
    destinations = filter_row1[2].multiselect("Destination", options(data, "DESTINATION"))
    filter_row2 = st.columns(3)
    origin_zone = filter_row2[0].multiselect("Origin zone", options(data, "ORG_ZONE"))
    destination_zone = filter_row2[1].multiselect(
        "Destination zone", options(data, "DEST_ZONE")
    )
    products = filter_row2[2].multiselect("Product", options(data, "PRODUCT_NAME"))

filtered = data
for column, selected in {
    "RATEFOR": rate_for, "ORG_ZONE": origin_zone, "DEST_ZONE": destination_zone,
    "ORIGIN": origins, "DESTINATION": destinations, "PRODUCT_NAME": products,
}.items():
    if selected:
        filtered = filtered[filtered[column].astype(str).isin(selected)]

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

today = pd.Timestamp(date.today())
expiring = filtered[filtered["TODT"].between(today, today + pd.Timedelta(days=30))]
routes = filtered[["ORIGIN", "DESTINATION"]].drop_duplicates().shape[0]
metrics = st.columns(5)
metrics[0].metric("Active records", f"{len(filtered):,}")
metrics[1].metric("Unique routes", f"{routes:,}")
metrics[2].metric("Destinations", f"{filtered['DESTINATION'].nunique():,}")
metrics[3].metric("Average Rate 1", f"{filtered['RATE1'].mean():,.2f}")
metrics[4].metric("Expiring in 30 days", f"{len(expiring):,}")

overview, rate_analysis, charge_analysis, records = st.tabs(
    ["Overview", "Rate analysis", "Additional charges", "Rate records"]
)

with overview:
    left, right = st.columns(2)
    with left:
        summary = filtered["RATEFOR"].fillna("N/A").value_counts().reset_index()
        summary.columns = ["Rate for", "Records"]
        st.plotly_chart(px.bar(summary, x="Rate for", y="Records", text_auto=True,
                               title="Rates by applicability"), use_container_width=True)
    with right:
        summary = filtered["PRODUCT_NAME"].fillna("Not specified").value_counts().reset_index()
        summary.columns = ["Product", "Records"]
        st.plotly_chart(px.bar(summary, x="Product", y="Records", text_auto=True,
                               title="Rates by product"), use_container_width=True)

    top_routes = filtered.assign(
        ROUTE=filtered["ORIGIN"].fillna("N/A") + " → " +
              filtered["DESTINATION"].fillna("N/A")
    )["ROUTE"].value_counts().head(15).sort_values().reset_index()
    top_routes.columns = ["Route", "Records"]
    st.plotly_chart(px.bar(top_routes, x="Records", y="Route", orientation="h",
                           text_auto=True, title="Top 15 routes"),
                    use_container_width=True)

with rate_analysis:
    rates = filtered.groupby(
        ["DESTINATION", "DEST_CIRCLE", "DEST_ZONE"], dropna=False, as_index=False
    ).agg(SLAB1=("SLAB1", "mean"), RATE1=("RATE1", "mean"),
          MIN_WEIGHT=("MINCWEIGHT", "min"), MAX_WEIGHT=("TOWT", "max"),
          RATE_RECORDS=("RATEID", "size"))
    rates["RATE_DIFFERENCE"] = rates["RATE1"] - rates["SLAB1"]
    rank_col, limit_col = st.columns(2)
    ranking = rank_col.radio("Ranking", ["Highest Rate 1", "Lowest Rate 1"],
                             horizontal=True)
    limit = limit_col.slider("Destinations", 5, 30, 15)
    ranked = rates.sort_values("RATE1", ascending=ranking == "Lowest Rate 1").head(limit)
    chart = ranked.melt(id_vars="DESTINATION", value_vars=["SLAB1", "RATE1"],
                        var_name="Rate", value_name="Value")
    st.plotly_chart(px.bar(chart, x="Value", y="DESTINATION", color="Rate",
                           barmode="group", orientation="h",
                           title=f"Destination {rate_category.lower()} comparison"),
                    use_container_width=True)
    st.dataframe(rates.sort_values("RATE1", ascending=False), use_container_width=True,
                 hide_index=True)

with charge_analysis:
    charge_cols = [col for col in CHARGES if col in filtered]
    numeric = filtered[charge_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    charges = pd.DataFrame({
        "Charge": [CHARGES[col] for col in charge_cols],
        "Configured records": [(numeric[col] != 0).sum() for col in charge_cols],
        "Average non-zero value": [
            numeric.loc[numeric[col] != 0, col].mean() if (numeric[col] != 0).any() else 0
            for col in charge_cols
        ],
        "Maximum value": [numeric[col].max() for col in charge_cols],
    })
    st.plotly_chart(px.bar(charges.sort_values("Configured records"),
                           x="Configured records", y="Charge", orientation="h",
                           text_auto=True, title="Additional-charge coverage"),
                    use_container_width=True)
    st.dataframe(charges.sort_values("Configured records", ascending=False),
                 use_container_width=True, hide_index=True)

with records:
    st.dataframe(filtered, use_container_width=True, hide_index=True, height=560,
                 column_config={
                     "FROMDT": st.column_config.DateColumn(format="DD-MM-YYYY"),
                     "TODT": st.column_config.DateColumn(format="DD-MM-YYYY"),
                 })
    st.download_button(
        "Download filtered rates (CSV)",
        filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{rate_category.lower().replace(' ', '_')}_{date.today():%Y%m%d}.csv",
        mime="text/csv",
    )
