import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine


# ============================================================
# NON-FTL KPI DASHBOARD
# FY 2024-25 | Exact calculation logic from the supplied SQL
# ============================================================

_QUERY = text(r"""
SET NOCOUNT ON;

IF OBJECT_ID('tempdb..#DATA') IS NOT NULL
    DROP TABLE #DATA;

;WITH GRDATA AS
(
    SELECT
        T.GRNO,

        MAX(CASE WHEN T.FTL = 'N' THEN 1 ELSE 0 END) AS ISNONFTL,

        SUM(
            CASE
                WHEN T.DOCUMENTTYPE = 'GR'
                THEN ISNULL(T.AWEIGHT,0)
                ELSE 0
            END
        ) AS TOTAWEIGHT,

        SUM(
            CASE
                WHEN T.DOCUMENTTYPE = 'GR'
                THEN ISNULL(T.WEIGHT,0)
                ELSE 0
            END
        ) AS TOTCWEIGHT,

        SUM(ISNULL(T.FREIGHT,0)) AS FREIGHT,

        SUM(ISNULL(T.EXPENSE,0)) AS COSTING,

        SUM(
              ISNULL(T.FREIGHT,0)
            + ISNULL(T.DELIVERYINCOME,0)
            + ISNULL(T.ADDITIONALFREIGHT,0)
            + ISNULL(T.OTHERINCOME,0)
            - ISNULL(T.EXPENSE,0)
        ) AS GP

    FROM DBO.GREENTRANSWEB_GRWISEPNLDETAIL_V7
    (
        '00000',
        '2024-04-01',
        '2025-03-31',
        ''
    ) T

    GROUP BY T.GRNO
)

SELECT
    COUNT(*) AS TOTALGR,
    SUM(TOTAWEIGHT) AS TOTAWEIGHT,
    SUM(TOTCWEIGHT) AS TOTCWEIGHT,
    SUM(FREIGHT) AS FREIGHT,
    SUM(COSTING) AS COSTING,
    SUM(GP) AS GP

INTO #DATA

FROM GRDATA
WHERE ISNONFTL = 1;


SELECT
    V.SORT_ORDER,
    V.PARTICULARS,
    CAST(V.FY2425 AS DECIMAL(18,2)) AS [FY24-25]

FROM #DATA D

CROSS APPLY
(
    VALUES

    (1, 'Load - Actual Weight (tonnes)',
        D.TOTAWEIGHT / 1000.00 / 12.00),

    (2, 'Load - Charge Weight',
        D.TOTCWEIGHT / 1000.00 / 12.00),

    (3, 'Chg Vs Act WT',
        D.TOTCWEIGHT / NULLIF(D.TOTAWEIGHT,0)),

    (4, 'Shipment Count (GRs K)',
        D.TOTALGR / 1000.00 / 12.00),

    (5, 'Revenue (Rs Cr)',
        D.FREIGHT / 10000000.00 / 12.00),

    (6, 'Operating Cost (Rs Cr)',
        D.COSTING / 10000000.00 / 12.00),

    (7, 'GP Amt. (Rs Cr)',
        D.GP / 10000000.00 / 12.00),

    (8, 'Operational GP %',
        D.GP * 100.00 / NULLIF(D.FREIGHT,0)),

    (9, 'CPK - Cost per kg',
        D.COSTING / NULLIF(D.TOTAWEIGHT,0)),

    (10, 'RPK - Revenue per kg (Act WT)',
        D.FREIGHT / NULLIF(D.TOTAWEIGHT,0))

) V
(
    SORT_ORDER,
    PARTICULARS,
    FY2425
)

ORDER BY V.SORT_ORDER;
""")


@st.cache_data(ttl=3600, show_spinner=False)
def load_non_ftl_kpi_data():
    """Run the supplied SQL and return its 10-row KPI result."""
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(_QUERY, conn)

    if df is None or df.empty:
        return pd.DataFrame(columns=["SORT_ORDER", "PARTICULARS", "FY24-25"])

    df.columns = [str(col).strip() for col in df.columns]

    if "FY24-25" in df.columns:
        df["FY24-25"] = pd.to_numeric(
            df["FY24-25"], errors="coerce"
        ).fillna(0.0)

    return df.sort_values("SORT_ORDER").reset_index(drop=True)


def _format_value(particular, value):
    value = float(value or 0.0)

    if particular == "Operational GP %":
        return f"{value:,.2f}%"

    if particular in {
        "Revenue (Rs Cr)",
        "Operating Cost (Rs Cr)",
        "GP Amt. (Rs Cr)",
    }:
        return f"Rs {value:,.2f} Cr"

    if particular in {
        "CPK - Cost per kg",
        "RPK - Revenue per kg (Act WT)",
    }:
        return f"Rs {value:,.2f}"

    if particular == "Shipment Count (GRs K)":
        return f"{value:,.2f} K"

    if particular == "Chg Vs Act WT":
        return f"{value:,.2f}x"

    return f"{value:,.2f}"


def _inject_css():
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 100% !important;
            padding-top: .65rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        .nonftl-title {
            color: #102a43;
            font-size: 23px;
            font-weight: 850;
            letter-spacing: -.3px;
            margin: 0;
        }

        .nonftl-subtitle {
            color: #64748b;
            font-size: 11px;
            margin: 2px 0 14px 0;
        }

        .nonftl-card {
            min-height: 103px;
            padding: 12px 13px;
            border: 1px solid #dbe4ef;
            border-radius: 14px;
            background: linear-gradient(180deg,#ffffff 0%,#f8fbff 100%);
            box-shadow: 0 5px 13px rgba(15,42,67,.08);
        }

        .nonftl-card-title {
            min-height: 31px;
            color: #64748b;
            font-size: 11px;
            font-weight: 650;
            line-height: 1.25;
        }

        .nonftl-card-value {
            margin-top: 10px;
            color: #102a43;
            font-size: 20px;
            font-weight: 850;
            line-height: 1.05;
            white-space: nowrap;
        }

        .nonftl-section-title {
            color: #102a43;
            font-size: 15px;
            font-weight: 750;
            margin: 18px 0 7px 1px;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_non_ftl_kpi_dashboard():
    _inject_css()

    header_left, header_right = st.columns([5.5, 1.0], vertical_alignment="center")

    with header_left:
        st.markdown(
            '<div class="nonftl-title">Non-FTL KPI Dashboard</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="nonftl-subtitle">'
            'FY 2024-25 | Non-FTL GRs only | Values as per supplied SQL'
            '</div>',
            unsafe_allow_html=True,
        )

    with header_right:
        if st.button("Refresh", key="nonftl_refresh", use_container_width=True):
            load_non_ftl_kpi_data.clear()
            st.rerun()

    try:
        with st.spinner("Loading Non-FTL KPI data..."):
            df = load_non_ftl_kpi_data()
    except Exception as exc:
        st.error(f"Unable to load Non-FTL KPI data: {exc}")
        return

    if df.empty:
        st.warning("No Non-FTL data found for FY 2024-25.")
        return

    required = {"SORT_ORDER", "PARTICULARS", "FY24-25"}
    missing = required.difference(df.columns)
    if missing:
        st.error(
            f"SQL output is missing columns: {sorted(missing)}. "
            f"Available columns: {list(df.columns)}"
        )
        return

    # 10 KPIs in two clean rows of five cards.
    records = df.to_dict("records")

    for start in (0, 5):
        row = records[start:start + 5]
        cols = st.columns(5, gap="small")

        for col, item in zip(cols, row):
            particular = str(item["PARTICULARS"])
            value = _format_value(particular, item["FY24-25"])

            with col:
                st.markdown(
                    f"""
                    <div class="nonftl-card">
                        <div class="nonftl-card-title">{particular}</div>
                        <div class="nonftl-card-value">{value}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown(
        '<div class="nonftl-section-title">KPI Summary</div>',
        unsafe_allow_html=True,
    )

    output_df = df[["PARTICULARS", "FY24-25"]].copy()
    output_df["FY24-25"] = output_df.apply(
        lambda row: _format_value(row["PARTICULARS"], row["FY24-25"]),
        axis=1,
    )
    output_df.columns = ["Particulars", "FY24-25"]

    st.dataframe(
        output_df,
        use_container_width=True,
        hide_index=True,
        height=390,
    )
