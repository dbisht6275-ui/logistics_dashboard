from html import escape

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine
from services.data_loader import get_date_range


# =====================================================
# NON-FTL KPI DASHBOARD
# UI pattern intentionally follows PNL_Analysis.py.
# Existing PNL_Analysis.py is not imported or modified.
# =====================================================

FY_OPTIONS = [
    "Select FY",
    "2026-2027",
    "2025-2026",
    "2024-2025",
    "2023-2024",
    "2022-2023",
]

_CACHE_TTL_SECONDS = 24 * 60 * 60


def _inject_non_ftl_css() -> None:
    """P&L-dashboard style header/cards, isolated under Non-FTL widget keys."""
    st.markdown(
        """
        <style>
        :root {
            --dash-navy:#102a43;
            --dash-blue:#2563eb;
            --dash-muted:#64748b;
            --dash-border:#dbe4ef;
        }

        .stApp { background:#ffffff !important; }
        .block-container {
            max-width:100% !important;
            padding:.35rem .75rem .75rem !important;
        }
        div[data-testid="stVerticalBlock"] { gap:.55rem !important; }
        div[data-testid="stHorizontalBlock"] {
            gap:.5rem !important;
            align-items:flex-start !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width:0 !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            margin-top:4px !important;
            margin-bottom:10px !important;
            border:1px solid #dce5ef !important;
            border-radius:14px !important;
            background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%) !important;
            box-shadow:0 7px 18px rgba(15,42,67,.075), inset 0 1px 0 #ffffff !important;
            box-sizing:border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding:.55rem .65rem !important;
        }

        .nonftl-header-marker {
            display:flex;
            align-items:center;
            min-height:36px;
            color:var(--dash-navy);
            font-size:19px;
            font-weight:850;
            white-space:nowrap;
        }

        .nonftl-inline-label {
            display:flex;
            align-items:center;
            justify-content:flex-end;
            min-height:34px;
            color:#334155;
            font-size:10px;
            font-weight:700;
            line-height:1;
            white-space:nowrap;
        }

        .st-key-nonftl_header_bar div[data-testid="stVerticalBlockBorderWrapper"] {
            padding:8px 12px !important;
            margin-top:0 !important;
            margin-bottom:4px !important;
            border-radius:10px !important;
            transform:none !important;
            overflow:visible !important;
        }
        .st-key-nonftl_header_bar div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding:0 !important;
        }
        .st-key-nonftl_header_bar div[data-testid="stVerticalBlock"] {
            gap:0 !important;
        }

        .st-key-nonftl_fy div[data-testid="stSelectbox"] > label,
        .st-key-nonftl_fy div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
            display:none !important;
            height:0 !important;
            min-height:0 !important;
            margin:0 !important;
            padding:0 !important;
        }

        .st-key-nonftl_fy div[data-testid="stSelectbox"] {
            gap:0 !important;
            margin:0 !important;
        }

        .st-key-nonftl_fy div[data-baseweb="select"] > div,
        .st-key-nonftl_run_report button {
            min-height:34px !important;
            height:34px !important;
            border-radius:8px !important;
        }

        .st-key-nonftl_run_report button {
            margin:0 !important;
            padding:0 12px !important;
            border:1px solid #174ea6 !important;
            background:linear-gradient(180deg,#2468c9 0%,#174ea6 100%) !important;
            color:#fff !important;
            font-size:11px !important;
            font-weight:800 !important;
            white-space:nowrap !important;
            box-shadow:0 3px 7px rgba(23,78,166,.24) !important;
        }
        .st-key-nonftl_run_report button p,
        .st-key-nonftl_run_report button span {
            color:#fff !important;
            font-weight:800 !important;
        }

        .nonftl-report-caption {
            color:#64748b;
            font-size:10px;
            margin:5px 1px 0 1px;
        }

        .kpi-3d-card {
            position:relative;
            overflow:hidden;
            min-height:78px;
            padding:8px 9px;
            border:1px solid #cbd5e1;
            border-radius:14px;
            background:linear-gradient(145deg,#ffffff 0%,#f8fafc 45%,#e7edf5 100%);
            box-shadow:0 3px 8px rgba(15,23,42,.10),
                       inset 1px 1px 0 rgba(255,255,255,.98);
            transform:none;
            transition:transform .15s ease,box-shadow .15s ease;
        }

        .kpi-3d-card:hover {
            transform:translateY(-2px);
            box-shadow:0 7px 14px rgba(15,23,42,.13),
                       inset 1px 1px 0 rgba(255,255,255,.98);
        }

        .kpi-3d-gloss {
            position:absolute;
            inset:1px 1px auto 1px;
            height:38%;
            border-radius:13px 13px 50% 50%;
            background:linear-gradient(180deg,rgba(255,255,255,.78),rgba(255,255,255,0));
            pointer-events:none;
        }

        .kpi-3d-head {
            position:relative;
            z-index:1;
            display:grid;
            grid-template-columns:minmax(0,1fr) 27px;
            align-items:center;
            gap:6px;
        }

        .kpi-3d-title {
            color:var(--kpi-accent);
            font-size:11px;
            font-family:"Segoe UI",Arial,sans-serif;
            font-weight:400;
            letter-spacing:.15px;
            text-align:left;
            white-space:nowrap;
            overflow:hidden;
            text-overflow:ellipsis;
        }

        .kpi-3d-icon {
            width:27px;
            height:27px;
            border-radius:9px;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:15px;
            background:linear-gradient(145deg,#ffffff,#dfe7f1);
            border:1px solid #d7e1ec;
            box-shadow:0 2px 4px rgba(15,23,42,.10),
                       inset 1px 1px 0 rgba(255,255,255,.95);
        }

        .kpi-3d-value {
            position:relative;
            z-index:1;
            margin-top:6px;
            color:#102a43;
            font-size:16px;
            font-weight:950;
            line-height:1.08;
            white-space:nowrap;
        }

        .nonftl-section-title {
            font-size:14px;
            font-weight:600;
            color:#0f2744;
            margin:4px 0 7px 1px;
        }

        [data-testid="stDataFrame"] {
            border:1px solid #e2eaf3;
            border-radius:10px;
            overflow:hidden;
            box-shadow:none !important;
            background:#fbfdff;
        }

        @media (max-width:768px) {
            div[data-testid="stHorizontalBlock"] {
                flex-direction:column !important;
                flex-wrap:nowrap !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                width:100% !important;
                min-width:100% !important;
            }
            .kpi-3d-card { min-height:82px !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _fy_label(fy: str) -> str:
    """2024-2025 -> FY24-25"""
    start_year, end_year = fy.split("-")
    return f"FY{start_year[-2:]}-{end_year[-2:]}"


def _build_query() -> text:
    # Accounting/calculation logic is the same as the SQL supplied by the user.
    return text(
        r"""
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
                :from_date,
                :to_date,
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
            CAST(V.FY_VALUE AS DECIMAL(18,2)) AS FY_VALUE

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
            FY_VALUE
        )

        ORDER BY V.SORT_ORDER;
        """
    )


@st.cache_data(
    ttl=_CACHE_TTL_SECONDS,
    show_spinner=False,
    max_entries=8,
)
def load_non_ftl_kpis(start_date, end_date) -> pd.DataFrame:
    engine = get_engine()

    with engine.connect() as conn:
        df = pd.read_sql_query(
            _build_query(),
            conn,
            params={
                "from_date": str(start_date),
                "to_date": str(end_date),
            },
        )

    if df is None or df.empty:
        return pd.DataFrame(
            columns=["SORT_ORDER", "PARTICULARS", "FY_VALUE"]
        )

    df.columns = [str(col).strip() for col in df.columns]

    df["SORT_ORDER"] = pd.to_numeric(
        df["SORT_ORDER"], errors="coerce"
    ).fillna(0).astype(int)

    df["FY_VALUE"] = pd.to_numeric(
        df["FY_VALUE"], errors="coerce"
    ).fillna(0.0)

    return df.sort_values("SORT_ORDER").reset_index(drop=True)


def _format_kpi_value(particular: str, value: float) -> str:
    value = float(value or 0.0)

    if particular == "Operational GP %":
        return f"{value:,.2f}%"

    if particular == "Chg Vs Act WT":
        return f"{value:,.2f}x"

    if particular == "Shipment Count (GRs K)":
        return f"{value:,.2f} K"

    if particular in {
        "Revenue (Rs Cr)",
        "Operating Cost (Rs Cr)",
        "GP Amt. (Rs Cr)",
    }:
        return f"₹{value:,.2f} Cr"

    if particular in {
        "CPK - Cost per kg",
        "RPK - Revenue per kg (Act WT)",
    }:
        return f"₹{value:,.2f}"

    return f"{value:,.2f}"


def _kpi_icon(sort_order: int) -> str:
    return {
        1: "⚖️",
        2: "📦",
        3: "↔️",
        4: "🚚",
        5: "💰",
        6: "🧾",
        7: "📈",
        8: "🎯",
        9: "🏷️",
        10: "₹",
    }.get(sort_order, "•")


def _render_kpi_card(title: str, value: str, icon: str) -> None:
    html = (
        '<div class="kpi-3d-card" style="--kpi-accent:#2563eb;">'
        '<div class="kpi-3d-gloss"></div>'
        '<div class="kpi-3d-head">'
        f'<div class="kpi-3d-title">{escape(title)}</div>'
        f'<div class="kpi-3d-icon">{escape(icon)}</div>'
        '</div>'
        f'<div class="kpi-3d-value">{escape(value)}</div>'
        '</div>'
    )

    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def _render_header():
    with st.container(border=True, key="nonftl_header_bar"):
        title_col, fy_label_col, fy_col, run_col, spacer_col = st.columns(
            [1.85, .28, .86, .86, 4.15],
            gap="small",
            vertical_alignment="center",
        )

        with title_col:
            st.markdown(
                '<div class="nonftl-header-marker">'
                'Non-FTL KPI Dashboard'
                '</div>',
                unsafe_allow_html=True,
            )

        with fy_label_col:
            st.markdown(
                '<div class="nonftl-inline-label">F.Y.</div>',
                unsafe_allow_html=True,
            )

        with fy_col:
            fy = st.selectbox(
                "Financial Year",
                FY_OPTIONS,
                key="nonftl_fy",
                label_visibility="collapsed",
            )

        with run_col:
            run_report = st.button(
                "▶ Run Report",
                key="nonftl_run_report",
                type="primary",
                width="stretch",
            )

        with spacer_col:
            st.markdown(
                '<div aria-hidden="true" style="height:1px"></div>',
                unsafe_allow_html=True,
            )

    return fy, run_report


def show_non_ftl_kpi_dashboard() -> None:
    """
    Separate Non-FTL dashboard.
    Uses the visual/report-loading pattern of the existing P&L dashboard,
    but executes only the supplied Non-FTL KPI query.
    """
    _inject_non_ftl_css()

    if "nonftl_report_ready" not in st.session_state:
        st.session_state["nonftl_report_ready"] = False

    pending_fy, run_report = _render_header()

    if pending_fy == "Select FY":
        if run_report:
            st.warning(
                "Please select a financial year before running the report."
            )
        else:
            st.info(
                "Select a financial year, then click ▶ Run Report."
            )
        return

    if run_report:
        start_date, end_date = get_date_range(pending_fy)

        try:
            with st.spinner("Loading Non-FTL KPI data..."):
                raw_df = load_non_ftl_kpis(start_date, end_date)
        except Exception as exc:
            st.error(f"Unable to load Non-FTL KPI data: {exc}")
            return

        st.session_state["nonftl_report_df"] = raw_df
        st.session_state["nonftl_active_fy"] = pending_fy
        st.session_state["nonftl_report_ready"] = True

    if not st.session_state.get("nonftl_report_ready", False):
        st.info("Select a financial year, then click ▶ Run Report.")
        return

    active_fy = st.session_state.get("nonftl_active_fy")

    if pending_fy != active_fy:
        st.info(
            "Financial year changed. Click ▶ Run Report to refresh the dashboard."
        )
        return

    stored_df = st.session_state.get("nonftl_report_df")

    if stored_df is None or stored_df.empty:
        st.warning(
            "No Non-FTL data found for the selected financial year."
        )
        return

    df = stored_df.copy()

    required = {"SORT_ORDER", "PARTICULARS", "FY_VALUE"}
    missing = required.difference(df.columns)

    if missing:
        st.error(
            f"Missing SQL output columns: {sorted(missing)}"
        )
        st.write("Available columns:", list(df.columns))
        return

    fy_column = _fy_label(active_fy)

    start_date, end_date = get_date_range(active_fy)
    st.markdown(
        f'<div class="nonftl-report-caption">'
        f'{escape(active_fy)} · {escape(str(start_date))} to '
        f'{escape(str(end_date))} · Non-FTL GRs only'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 10 cards exactly from the SQL output.
    # Same dense P&L-dashboard visual language; two rows of five.
    records = df.to_dict("records")

    for start_idx in (0, 5):
        card_cols = st.columns(5, gap="small")

        for col, row in zip(
            card_cols,
            records[start_idx:start_idx + 5],
        ):
            with col:
                _render_kpi_card(
                    title=str(row["PARTICULARS"]),
                    value=_format_kpi_value(
                        str(row["PARTICULARS"]),
                        row["FY_VALUE"],
                    ),
                    icon=_kpi_icon(int(row["SORT_ORDER"])),
                )

    st.markdown(
        '<div class="nonftl-section-title">'
        'KPI Summary'
        '</div>',
        unsafe_allow_html=True,
    )

    summary = df[
        ["SORT_ORDER", "PARTICULARS", "FY_VALUE"]
    ].copy()

    summary[fy_column] = summary.apply(
        lambda row: _format_kpi_value(
            str(row["PARTICULARS"]),
            row["FY_VALUE"],
        ),
        axis=1,
    )

    summary = summary[
        ["SORT_ORDER", "PARTICULARS", fy_column]
    ].rename(
        columns={
            "SORT_ORDER": "#",
            "PARTICULARS": "Particulars",
        }
    )

    st.dataframe(
        summary,
        width="stretch",
        hide_index=True,
        height=390,
    )


# Optional short alias.
def show_non_ftl_dashboard() -> None:
    show_non_ftl_kpi_dashboard()
