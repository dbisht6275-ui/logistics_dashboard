import io
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services.pnl_data_loader import load_pnl_data_pair
from services.data_loader import get_date_range

# =====================================================
# Constants
# =====================================================
MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
MONTH_MAP = {1: "Apr", 2: "May", 3: "Jun", 4: "Jul", 5: "Aug", 6: "Sep", 7: "Oct", 8: "Nov", 9: "Dec", 10: "Jan", 11: "Feb", 12: "Mar"}
QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]
TOP_N_OPTIONS = [10, 20, 30, 40]
QUARTER_MAP = {1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2", 7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"}
FY_OPTIONS = [
    "Select FY", "2026-2027", "2025-2026", "2024-2025",
    "2023-2024", "2022-2023", "2021-2022", "2020-2021",
]


# =====================================================
# Styling
# =====================================================
ROW_GAP_HEIGHT = 12

def compact_spacer(height=ROW_GAP_HEIGHT):
    """Render a reliable small vertical gap between major dashboard rows."""
    st.markdown(
        f"<div class='dashboard-row-spacer' style='height:{int(height)}px;min-height:{int(height)}px;line-height:{int(height)}px;'>&nbsp;</div>",
        unsafe_allow_html=True,
    )

def _inject_pnl_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --dash-navy:#102a43;
            --dash-blue:#2563eb;
            --dash-teal:#0f766e;
            --dash-muted:#64748b;
            --dash-border:#dbe4ef;
        }

        .stApp { background:#ffffff !important; }
        .block-container { max-width:100% !important; padding:.35rem .75rem .75rem !important; }
        div[data-testid="stVerticalBlock"] { gap:.55rem !important; }
        .dashboard-row-spacer { display:block !important; width:100% !important; margin:0 !important; padding:0 !important; }
        div[data-testid="stHorizontalBlock"] { gap:.5rem !important; align-items:flex-start !important; }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] { min-width:0 !important; }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            margin-top:4px !important;
            margin-bottom:10px !important;
            border:1px solid #dce5ef !important;
            border-radius:14px !important;
            background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%) !important;
            box-shadow:0 7px 18px rgba(15,42,67,.075), inset 0 1px 0 #ffffff !important;
            box-sizing:border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div { padding:.55rem .65rem !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform:translateY(-1px);
            box-shadow:0 10px 22px rgba(15,42,67,.10), inset 0 1px 0 #ffffff !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"]) {
            gap:14px !important; column-gap:14px !important; margin-top:3px !important; margin-bottom:6px !important;
        }

        .pnl-title, .executive-title {
            color:var(--dash-navy); font-size:19px; font-weight:850; letter-spacing:-.3px; margin:0;
        }
        .pnl-header-marker { display:flex; align-items:center; min-height:36px; color:var(--dash-navy); font-size:19px; font-weight:850; white-space:nowrap; }
        .pnl-inline-label { display:flex; align-items:center; justify-content:flex-end; min-height:34px; color:#334155; font-size:10px; font-weight:700; line-height:1; white-space:nowrap; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pnl-header-marker) { padding:8px 12px !important; margin-top:0 !important; margin-bottom:4px !important; border-radius:10px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pnl-header-marker) > div { padding:0 !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pnl-header-marker) div[data-testid="stVerticalBlock"] { gap:0 !important; }
        .st-key-pnl_view_type div[data-testid="stSelectbox"] > label,
        .st-key-pnl_view_type div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
        .st-key-pnl_fy div[data-testid="stSelectbox"] > label,
        .st-key-pnl_fy div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] { display:none !important; height:0 !important; min-height:0 !important; margin:0 !important; padding:0 !important; }
        .st-key-pnl_view_type div[data-testid="stSelectbox"], .st-key-pnl_fy div[data-testid="stSelectbox"] { gap:0 !important; margin:0 !important; }
        .st-key-pnl_view_type div[data-baseweb="select"] > div,
        .st-key-pnl_fy div[data-baseweb="select"] > div,
        .st-key-pnl_run_report button { min-height:34px !important; height:34px !important; border-radius:8px !important; }
        .st-key-pnl_run_report button { margin:0 !important; padding:0 12px !important; border:1px solid #174ea6 !important; background:linear-gradient(180deg,#2468c9 0%,#174ea6 100%) !important; color:#fff !important; font-size:11px !important; font-weight:800 !important; white-space:nowrap !important; box-shadow:0 3px 7px rgba(23,78,166,.24) !important; }
        .st-key-pnl_run_report button p, .st-key-pnl_run_report button span { color:#fff !important; font-weight:800 !important; }
        .pnl-subtitle, .executive-subtitle { color:var(--dash-muted); font-size:11px; margin-top:2px; }
        .section-title { font-size:14px; font-weight:600; color:#0f2744; margin:1px 0 7px 1px; }

        div[data-testid="stElementContainer"]:has(.filter-summary) {
            position:relative !important; z-index:5 !important; margin-top:0 !important; margin-bottom:0 !important;
        }
        .filter-summary {
            display:flex; flex-wrap:wrap; justify-content:flex-start; align-items:center; width:100%;
            min-height:28px; gap:6px; margin:0; padding:0; line-height:1; position:relative; z-index:5;
        }
        .filter-chip {
            display:inline-flex; align-items:center; justify-content:center; min-height:26px; padding:5px 11px;
            border:1px solid #b8d1f2; border-radius:999px; background:#f5f9ff; color:#31557d;
            font-size:10px; font-weight:500; line-height:1; box-shadow:inset 0 1px 0 #ffffff; white-space:nowrap;
        }

        div[data-testid="stSelectbox"] {
            display:flex !important; flex-direction:column !important; gap:7px !important;
            padding:0 !important; margin:0 0 2px 0 !important; border:0 !important;
            background:transparent !important; box-shadow:none !important; overflow:visible !important;
        }
        div[data-testid="stSelectbox"] > label,
        div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
            display:block !important; position:static !important; min-height:22px !important;
            margin:0 0 2px 2px !important; padding:0 !important; line-height:22px !important;
            color:#243b53 !important; font-size:10px !important; font-family:"Segoe UI",Arial,sans-serif !important;
            font-weight:400 !important; white-space:nowrap !important; overflow:hidden !important; text-overflow:ellipsis !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            min-height:40px !important; height:40px !important; padding:0 8px !important;
            border:1px solid #cbd9ea !important; border-radius:10px !important;
            background:linear-gradient(180deg,#ffffff 0%,#f5f8fc 100%) !important;
            box-shadow:inset 0 1px 2px rgba(15,23,42,.06) !important;
        }
        div[data-baseweb="select"] span { color:#102a43 !important; font-weight:800 !important; font-size:11px !important; }
        div[data-baseweb="select"] svg { color:#1d4ed8 !important; }

        .kpi-3d-card {
            position:relative; overflow:hidden; min-height:70px; padding:8px 9px;
            border:1px solid #cbd5e1; border-radius:14px;
            background:linear-gradient(145deg,#ffffff 0%,#f8fafc 45%,#e7edf5 100%);
            box-shadow:0 3px 8px rgba(15,23,42,.10), inset 1px 1px 0 rgba(255,255,255,.98);
            transform:none; transition:transform .15s ease,box-shadow .15s ease;
        }
        .kpi-3d-card:hover { transform:translateY(-2px); box-shadow:0 7px 14px rgba(15,23,42,.13), inset 1px 1px 0 rgba(255,255,255,.98); }
        .kpi-3d-topline { display:none !important; }
        .kpi-3d-gloss { position:absolute; inset:1px 1px auto 1px; height:38%; border-radius:13px 13px 50% 50%; background:linear-gradient(180deg,rgba(255,255,255,.78),rgba(255,255,255,0)); pointer-events:none; }
        .kpi-3d-head { position:relative; z-index:1; display:grid; grid-template-columns:minmax(0,1fr) 27px; align-items:center; gap:6px; }
        .kpi-3d-title { color:var(--kpi-accent); font-size:11px; font-family:"Segoe UI",Arial,sans-serif; font-weight:400; letter-spacing:.15px; text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .kpi-3d-icon { width:27px; height:27px; border-radius:9px; display:flex; align-items:center; justify-content:center; font-size:15px; background:linear-gradient(145deg,#ffffff,#dfe7f1); border:1px solid #d7e1ec; box-shadow:0 2px 4px rgba(15,23,42,.10), inset 1px 1px 0 rgba(255,255,255,.95); }
        .kpi-3d-value { position:relative; z-index:1; margin-top:2px; color:#102a43; font-size:16px; font-weight:950; line-height:1.08; white-space:nowrap; }
        .kpi-3d-footer { position:relative; z-index:1; margin-top:4px; display:flex; align-items:center; justify-content:space-between; gap:6px; }
        .kpi-3d-ly { min-width:0; color:#64748b; font-size:9px; font-weight:600; line-height:1.1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .kpi-3d-growth { display:inline-block; padding:2px 7px; border:1px solid; border-radius:999px; font-size:9px; font-weight:400; white-space:nowrap; box-shadow:inset 0 1px 0 rgba(255,255,255,.9),0 2px 3px rgba(15,23,42,.10); }

        div[data-testid="stSegmentedControl"] { display:flex !important; justify-content:flex-end !important; width:100% !important; margin-top:1px !important; }
        div[data-testid="stSegmentedControl"] > div,
        div[data-testid="stSegmentedControl"] [role="radiogroup"] {
            display:flex !important; gap:6px !important; width:100% !important; padding:0 !important;
            border:0 !important; background:transparent !important; box-shadow:none !important;
        }
        div[data-testid="stSegmentedControl"] label,
        div[data-testid="stSegmentedControl"] button {
            position:relative !important; display:flex !important; align-items:center !important; justify-content:center !important;
            min-height:32px !important; height:32px !important; padding:4px 10px !important; margin:0 !important;
            border:1px solid #d8e2ee !important; border-radius:8px !important;
            background:linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important; color:#334155 !important;
            box-shadow:inset 0 1px 0 #ffffff,0 1px 2px rgba(15,23,42,.05) !important; transform:none !important;
            font-size:10px !important; font-weight:650 !important; white-space:nowrap !important;
        }
        div[data-testid="stSegmentedControl"] label:hover,
        div[data-testid="stSegmentedControl"] button:hover {
            border-color:#9bb7d8 !important; background:linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important; color:#174a7e !important;
        }
        div[data-testid="stSegmentedControl"] label:has(input:checked),
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            border-color:#123f73 !important; background:linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important;
            color:#ffffff !important; box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 2px 5px rgba(15,42,67,.18) !important;
        }
        div[data-testid="stSegmentedControl"] label:has(input:checked) p,
        div[data-testid="stSegmentedControl"] label:has(input:checked) span,
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] p,
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] span { color:#ffffff !important; }

        .stButton > button {
            position:relative !important; overflow:hidden !important; min-height:34px !important; padding:5px 13px !important;
            border:1px solid #d8e2ee !important; border-radius:8px !important; background:linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important;
            color:#334155 !important; box-shadow:inset 0 1px 0 rgba(255,255,255,.95),0 1px 2px rgba(15,23,42,.05) !important;
            transform:none !important; font-size:11px !important; font-weight:650 !important;
        }
        .stButton > button:hover { border-color:#9bb7d8 !important; background:linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important; color:#174a7e !important; }
        .stButton > button[data-testid="stBaseButton-primary"] { border-color:#123f73 !important; background:linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important; color:#ffffff !important; }

        div[data-testid="stDownloadButton"] > button {
            min-height:34px !important; width:auto !important; padding:5px 10px !important; border:1px solid #2563eb !important;
            border-radius:8px !important; color:#ffffff !important; font-size:10px !important; font-weight:850 !important;
            background:linear-gradient(145deg,#3b82f6 0%,#2563eb 58%,#1d4ed8 100%) !important;
            box-shadow:0 3px 0 #1e40af,0 6px 10px rgba(37,99,235,.20) !important;
        }
        div[data-testid="stDownloadButton"] > button p { color:#ffffff !important; }

        [data-testid="stDataFrame"] { border:1px solid #e2eaf3; border-radius:10px; overflow:hidden; box-shadow:none !important; background:#fbfdff; }
        [data-testid="stDataFrame"] table { font-size:11px; }
        [data-testid="stDataFrame"] tbody tr { height:22px !important; }

        @media (max-width:1500px) {
            .block-container { padding-left:.45rem !important; padding-right:.45rem !important; }
            div[data-testid="stHorizontalBlock"] { gap:.4rem !important; }
            div[data-testid="stSelectbox"] > label, div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] { font-size:9px !important; }
            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div { min-height:38px !important; height:38px !important; }
        }

        /* Phone layout: allow Streamlit's desktop rows to become readable cards. */
        @media (max-width:768px) {
            .block-container {
                max-width:100% !important;
                padding:.25rem .45rem .7rem !important;
                overflow-x:hidden !important;
            }

            div[data-testid="stHorizontalBlock"] {
                flex-direction:column !important;
                flex-wrap:nowrap !important;
                gap:.55rem !important;
                width:100% !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                flex:1 1 100% !important;
                width:100% !important;
                min-width:100% !important;
            }

            .executive-title { font-size:18px !important; }
            .filter-summary {
                width:100% !important;
                flex-wrap:wrap !important;
                gap:4px !important;
            }
            .filter-chip {
                max-width:100% !important;
                white-space:normal !important;
                overflow-wrap:anywhere !important;
            }

            div[data-testid="stSelectbox"],
            div[data-testid="stPopover"],
            div[data-testid="stButton"],
            div[data-testid="stDownloadButton"] { width:100% !important; }

            div[data-testid="stButton"] > button,
            div[data-testid="stDownloadButton"] > button,
            div[data-testid="stPopover"] > div,
            div[data-testid="stPopover"] > div > button {
                width:100% !important;
                max-width:none !important;
            }

            .kpi-3d-card { min-height:82px !important; }

            /* Keep dense analytical tables usable without widening the page. */
            .compact-zone-matrix-wrap,
            [class$="-insight-wrap"] {
                width:100% !important;
                max-width:100% !important;
                overflow-x:auto !important;
                -webkit-overflow-scrolling:touch;
            }
            .compact-zone-matrix { min-width:760px !important; }

            /* Inline desktop grids used by company and branch ranking panels. */
            div[style*="grid-template-columns:minmax(150px,195px)"],
            div[style*="grid-template-columns:34px minmax(175px,280px)"] {
                min-width:720px !important;
            }
            div:has(> div[style*="grid-template-columns:34px minmax(175px,280px)"]) {
                max-width:100% !important;
                overflow-x:auto !important;
                -webkit-overflow-scrolling:touch;
            }

            [data-testid="stPlotlyChart"] { width:100% !important; }
            [data-testid="stPlotlyChart"] > div { width:100% !important; }
        }


        /* Overview-style checkbox slicers */
        .checkbox-slicer-label {
            display:block;height:22px;min-height:22px;margin:0 0 9px 2px;
            padding:0;line-height:22px;color:#243b53;font-size:10px;
            font-family:"Segoe UI",Arial,sans-serif;font-weight:400;
            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
        }
        div[data-testid="stVerticalBlock"]:has(.checkbox-slicer-label) {gap:0 !important;}
        div[data-testid="stElementContainer"]:has(.checkbox-slicer-label) {
            min-height:31px !important;height:31px !important;margin:0 !important;
            padding:0 !important;overflow:visible !important;
        }
        div[data-testid="stPopover"] {width:100% !important;margin:0 !important;padding:0 !important;}
        div[data-testid="stPopover"] > div {width:100% !important;}
        div[data-testid="stPopover"] > div > button {
            width:100% !important;min-height:40px !important;height:40px !important;
            padding:0 9px !important;margin:0 !important;border:1px solid #cbd9ea !important;
            border-radius:10px !important;background:linear-gradient(180deg,#ffffff 0%,#f5f8fc 100%) !important;
            box-shadow:inset 0 1px 2px rgba(15,23,42,.06) !important;color:#102a43 !important;
            font-size:11px !important;font-weight:800 !important;justify-content:space-between !important;
            transform:none !important;
        }
        div[data-testid="stPopover"] > div > button:hover,
        div[data-testid="stPopover"] > div > button:focus {
            border-color:#cbd9ea !important;background:linear-gradient(180deg,#ffffff 0%,#f5f8fc 100%) !important;
            box-shadow:inset 0 1px 2px rgba(15,23,42,.06) !important;transform:none !important;
        }
        div[data-testid="stPopoverBody"] {max-height:360px !important;overflow-y:auto !important;}
        div[data-testid="stPopoverBody"] div[data-testid="stButton"] {width:auto !important;margin:0 !important;padding:0 !important;}
        div[data-testid="stPopoverBody"] div[data-testid="stButton"] > button {
            width:auto !important;min-width:0 !important;min-height:26px !important;height:26px !important;
            padding:2px 8px !important;margin:0 !important;border:1px solid #dbe4ef !important;
            border-radius:6px !important;background:#ffffff !important;color:#2563eb !important;
            box-shadow:none !important;transform:none !important;font-size:10px !important;font-weight:600 !important;
        }
        div[data-testid="stPopoverBody"] div[data-testid="stButton"] > button:hover {
            border-color:#93c5fd !important;background:#eff6ff !important;color:#1d4ed8 !important;
            box-shadow:none !important;transform:none !important;
        }

        /* Branch slab buttons - same design as Business Overview */
        div[class*="st-key-pnl_branch_slab_btn_"] {margin:0 !important;padding:0 !important;}
        div[class*="st-key-pnl_branch_slab_btn_"] div[data-testid="stButton"] {width:100% !important;margin:0 !important;}
        div[class*="st-key-pnl_branch_slab_btn_"] button {
            width:100% !important;min-height:34px !important;height:34px !important;padding:4px 8px !important;
            margin:0 !important;border:1px solid #d8e2ee !important;border-radius:8px !important;
            background:linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important;color:#334155 !important;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.95),0 1px 2px rgba(15,23,42,.05) !important;
            transform:none !important;font-size:11px !important;font-weight:650 !important;white-space:nowrap !important;
        }
        div[class*="st-key-pnl_branch_slab_btn_"] button:hover {
            border-color:#9bb7d8 !important;background:linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important;
            color:#174a7e !important;box-shadow:inset 0 1px 0 #ffffff,0 2px 5px rgba(15,42,67,.08) !important;
        }
        div[class*="st-key-pnl_branch_slab_btn_"] button[data-testid="stBaseButton-primary"] {
            border-color:#123f73 !important;background:linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important;
            color:#ffffff !important;box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 2px 5px rgba(15,42,67,.18) !important;
        }
        div[class*="st-key-pnl_branch_slab_btn_"] button[data-testid="stBaseButton-primary"] p,
        div[class*="st-key-pnl_branch_slab_btn_"] button[data-testid="stBaseButton-primary"] span {color:#ffffff !important;}
        div[class*="st-key-pnl_branch_slab_btn_"] button p,
        div[class*="st-key-pnl_branch_slab_btn_"] button span {
            margin:0 !important;padding:0 !important;font-size:11px !important;font-weight:650 !important;white-space:nowrap !important;
        }

        /* P&L Trend buttons - same real-button design as Business Overview */
        div[class*="st-key-pnl_trend_btn_"] {margin:0 !important;padding:0 !important;}
        div[class*="st-key-pnl_trend_btn_"] div[data-testid="stButton"] {width:100% !important;margin:0 !important;}
        div[class*="st-key-pnl_trend_btn_"] button {
            width:100% !important;min-height:34px !important;height:34px !important;padding:4px 8px !important;
            margin:0 !important;border:1px solid #d8e2ee !important;border-radius:8px !important;
            background:linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important;color:#334155 !important;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.95),0 1px 2px rgba(15,23,42,.05) !important;
            transform:none !important;font-size:11px !important;font-weight:650 !important;white-space:nowrap !important;
            transition:border-color .14s ease,background .14s ease,color .14s ease,box-shadow .14s ease !important;
        }
        div[class*="st-key-pnl_trend_btn_"] button:hover {
            border-color:#9bb7d8 !important;background:linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important;
            color:#174a7e !important;box-shadow:inset 0 1px 0 #ffffff,0 2px 5px rgba(15,42,67,.08) !important;
            transform:none !important;
        }
        div[class*="st-key-pnl_trend_btn_"] button[data-testid="stBaseButton-primary"] {
            border-color:#123f73 !important;background:linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important;
            color:#ffffff !important;box-shadow:inset 0 1px 0 rgba(255,255,255,.18),0 2px 5px rgba(15,42,67,.18) !important;
        }
        div[class*="st-key-pnl_trend_btn_"] button[data-testid="stBaseButton-primary"] p,
        div[class*="st-key-pnl_trend_btn_"] button[data-testid="stBaseButton-primary"] span {color:#ffffff !important;}
        div[class*="st-key-pnl_trend_btn_"] button p,
        div[class*="st-key-pnl_trend_btn_"] button span {
            margin:0 !important;padding:0 !important;font-size:11px !important;font-weight:650 !important;
            color:inherit !important;white-space:nowrap !important;
        }
        /* Final header overrides must come after the shared selectbox rules.
           This keeps the native controls on top and fully clickable. */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pnl-header-marker) {
            position:relative !important;
            overflow:visible !important;
            transform:none !important;
        }
        .pnl-header-marker, .pnl-inline-label,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pnl-header-marker) .filter-summary,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.pnl-header-marker) .filter-chip {
            pointer-events:none !important;
        }
        .st-key-pnl_view_type, .st-key-pnl_fy {
            position:relative !important;
            z-index:20 !important;
            pointer-events:auto !important;
            overflow:visible !important;
        }
        .st-key-pnl_view_type div[data-testid="stSelectbox"],
        .st-key-pnl_fy div[data-testid="stSelectbox"] {
            gap:0 !important;
            margin:0 !important;
            pointer-events:auto !important;
        }
        .st-key-pnl_view_type div[data-testid="stSelectbox"] > label,
        .st-key-pnl_view_type div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
        .st-key-pnl_fy div[data-testid="stSelectbox"] > label,
        .st-key-pnl_fy div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
            display:none !important;
            height:0 !important;
            min-height:0 !important;
            margin:0 !important;
            padding:0 !important;
        }
        .st-key-pnl_view_type div[data-baseweb="select"],
        .st-key-pnl_fy div[data-baseweb="select"],
        .st-key-pnl_view_type div[data-baseweb="select"] > div,
        .st-key-pnl_fy div[data-baseweb="select"] > div {
            position:relative !important;
            z-index:21 !important;
            pointer-events:auto !important;
            cursor:pointer !important;
            min-height:34px !important;
            height:34px !important;
        }
        .st-key-pnl_view_type div[data-baseweb="select"] *,
        .st-key-pnl_fy div[data-baseweb="select"] * {
            pointer-events:auto !important;
            cursor:pointer !important;
        }
        .st-key-pnl_view_type div[data-baseweb="select"] > div:hover,
        .st-key-pnl_fy div[data-baseweb="select"] > div:hover {
            border-color:#2563eb !important;
            background:#ffffff !important;
            box-shadow:0 0 0 2px rgba(37,99,235,.14), 0 3px 7px rgba(15,42,67,.12) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# Data helpers
# =====================================================
def _normalized_name(value: str) -> str:
    return str(value).strip().replace("_", "").replace(" ", "").casefold()


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    if df is None:
        return None
    column_map = {_normalized_name(c): c for c in df.columns}
    for candidate in candidates:
        found = column_map.get(_normalized_name(candidate))
        if found is not None:
            return found
    return None


def normalize_pnl_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise SP output without changing accounting values."""
    if df is None:
        return pd.DataFrame()

    out = df.copy()
    aliases = {
        "COMPNAME": ["COMPNAME", "compname", "company", "companyname"],
        "zone": ["zone", "zonename"],
        "circle": ["circle", "circlename", "hubname"],
        "branch": ["branch", "branchname"],
        "grno": ["grno", "gr_no", "grnumber"],
        "grdt": ["grdt", "grdate", "bookingdate"],
        "GRTYPE": ["GRTYPE", "grtype"],
        "LOADTYPE": ["LOADTYPE", "loadtype", "load_type"],
        "FIN_MONTH": ["FIN_MONTH", "fin_month", "financialmonth"],
        "REVENUE": ["REVENUE", "revenue", "business"],
        "EXPENSE": ["EXPENSE", "expense", "expenses", "cost"],
        "PNL": ["PNL", "pnl", "profitloss", "profit_loss", "profitandloss"],
        "Consignor": ["Consignor", "consignor"],
        "Consignee": ["Consignee", "consignee"],
        "Route": ["Route", "route"],
    }

    rename_map = {}
    for target, candidates in aliases.items():
        source = _find_column(out, candidates)
        if source is not None and source != target:
            rename_map[source] = target
    out = out.rename(columns=rename_map)

    for col in ["REVENUE", "EXPENSE", "PNL", "FIN_MONTH"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    if "grdt" in out.columns:
        out["grdt"] = pd.to_datetime(out["grdt"], errors="coerce")

    for col in ["COMPNAME", "zone", "circle", "branch", "GRTYPE", "LOADTYPE"]:
        if col in out.columns:
            out[col] = out[col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")

    if "FIN_MONTH" in out.columns:
        out["FIN_MONTH"] = out["FIN_MONTH"].astype(int)
        out["Month"] = out["FIN_MONTH"].map(MONTH_MAP)
        out["Quarter"] = out["FIN_MONTH"].map(QUARTER_MAP)

    return out


def validate_pnl_data(df: pd.DataFrame) -> list[str]:
    required = ["COMPNAME", "zone", "circle", "branch", "grno", "grdt", "LOADTYPE", "FIN_MONTH", "REVENUE", "EXPENSE", "PNL"]
    return [col for col in required if col not in df.columns]


def get_previous_fy(fy: str) -> str:
    start_year, end_year = map(int, fy.split("-"))
    return f"{start_year - 1}-{end_year - 1}"


def get_conversion(conversion_type: str) -> tuple[float, str]:
    return (100_000, "Lac") if conversion_type == "Lac" else (10_000_000, "Cr")


def amount_text(value: float, conversion_type: str) -> str:
    divisor, unit = get_conversion(conversion_type)
    return f"₹{value / divisor:,.2f} {unit}"


def pct_change(current: float, previous: float) -> float:
    if previous is None or pd.isna(previous) or previous == 0:
        return 0.0
    return ((current - previous) / abs(previous)) * 100


def pnl_margin(revenue: float, pnl: float) -> float:
    return (pnl / revenue * 100) if revenue else 0.0


def _apply_filter(df: pd.DataFrame, column: str, selected: str) -> pd.DataFrame:
    if selected == "All" or column not in df.columns:
        return df
    return df[df[column] == selected]


def _safe_options(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str).str.strip()
    values = values[values.ne("")]
    return sorted(values.unique().tolist(), key=str.casefold)



def _checkbox_slicer(label, options, key, locked_values=None, searchable=False):
    options = [x for x in options if pd.notna(x)]
    options = list(dict.fromkeys(options))

    st.markdown(
        f'<div class="checkbox-slicer-label">{escape(str(label))}</div>',
        unsafe_allow_html=True,
    )

    if locked_values:
        locked_values = [x for x in locked_values if x is not None]
        summary = str(locked_values[0]) if len(locked_values) == 1 else f"{len(locked_values)} selected"
        with st.popover(summary, use_container_width=True):
            for value in locked_values:
                st.checkbox(str(value), value=True, disabled=True, key=f"{key}__locked__{value}")
        return locked_values

    def state_key(value):
        return f"{key}__item__{str(value)}"

    if searchable:
        selection_key = f"{key}__instant_selected"
        legacy_selected = [value for value in options if st.session_state.get(state_key(value), False)]
        if selection_key not in st.session_state:
            st.session_state[selection_key] = legacy_selected
        else:
            st.session_state[selection_key] = [
                value for value in st.session_state.get(selection_key, []) if value in options
            ]

        selected_before = st.session_state.get(selection_key, [])
        summary = "All" if not selected_before else (str(selected_before[0]) if len(selected_before) == 1 else f"{len(selected_before)} selected")

        with st.popover(summary, use_container_width=True):
            action_cols = st.columns(2, gap="small")
            with action_cols[0]:
                if st.button("Select all", key=f"{key}__select_all", use_container_width=False):
                    st.session_state[selection_key] = list(options)
                    st.rerun()
            with action_cols[1]:
                if st.button("Clear", key=f"{key}__clear", use_container_width=False):
                    st.session_state[selection_key] = []
                    st.rerun()

            selected_values = st.multiselect(
                f"Search {str(label).replace('◎', '').replace('⌂', '').strip()}",
                options=options,
                key=selection_key,
                placeholder="Type to search...",
                label_visibility="collapsed",
            )
            if not options:
                st.caption("No values available")

        selected_set = set(selected_values)
        for value in options:
            st.session_state[state_key(value)] = value in selected_set
        return selected_values

    selected_before = [value for value in options if st.session_state.get(state_key(value), False)]
    summary = "All" if not selected_before else (str(selected_before[0]) if len(selected_before) == 1 else f"{len(selected_before)} selected")

    with st.popover(summary, use_container_width=True):
        action_cols = st.columns(2, gap="small")
        with action_cols[0]:
            if st.button("Select all", key=f"{key}__select_all", use_container_width=False):
                for value in options:
                    st.session_state[state_key(value)] = True
                st.rerun()
        with action_cols[1]:
            if st.button("Clear", key=f"{key}__clear", use_container_width=False):
                for value in options:
                    st.session_state[state_key(value)] = False
                st.rerun()

        if not options:
            st.caption("No values available")
        else:
            for value in options:
                st.checkbox(str(value), key=state_key(value))

    return [value for value in options if st.session_state.get(state_key(value), False)]


def calculate_pnl_kpis(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "revenue": 0.0, "expense": 0.0, "pnl": 0.0, "margin": 0.0,
            "ftl_pnl": 0.0, "ltl_pnl": 0.0, "profit_gr": 0, "loss_gr": 0,
            "avg_pnl_gr": 0.0,
        }

    revenue = float(df["REVENUE"].sum())
    expense = float(df["EXPENSE"].sum())
    pnl = float(df["PNL"].sum())
    gr_count = int(df["grno"].nunique()) if "grno" in df.columns else len(df)

    return {
        "revenue": revenue,
        "expense": expense,
        "pnl": pnl,
        "margin": pnl_margin(revenue, pnl),
        "ftl_pnl": float(df.loc[df["LOADTYPE"].eq("FTL"), "PNL"].sum()),
        "ltl_pnl": float(df.loc[df["LOADTYPE"].eq("LTL"), "PNL"].sum()),
        "profit_gr": int(df.loc[df["PNL"] > 0, "grno"].nunique()),
        "loss_gr": int(df.loc[df["PNL"] < 0, "grno"].nunique()),
        "avg_pnl_gr": pnl / gr_count if gr_count else 0.0,
    }


# =====================================================
# UI helpers
# =====================================================
def render_kpi_card(
    title: str,
    value: str,
    previous: str,
    growth: float,
    icon: str,
    accent: str,
    reverse_good: bool = False,
) -> None:
    """Render a P&L KPI using the same typography and card design as Overview."""
    positive = growth <= 0 if reverse_good else growth >= 0
    growth_color = "#15803d" if positive else "#dc2626"
    growth_border = "#86efac" if positive else "#fda4af"
    growth_arrow = "▲" if growth >= 0 else "▼"

    html = (
        f'<div class="kpi-3d-card" style="--kpi-accent:{accent};">'
        f'<div class="kpi-3d-gloss"></div>'
        f'<div class="kpi-3d-topline"></div>'
        f'<div class="kpi-3d-head">'
        f'<div class="kpi-3d-title">{escape(title)}</div>'
        f'<div class="kpi-3d-icon">{icon}</div>'
        f'</div>'
        f'<div class="kpi-3d-value">{escape(value)}</div>'
        f'<div class="kpi-3d-footer">'
        f'<span class="kpi-3d-ly">LY: {escape(previous)}</span>'
        f'<span class="kpi-3d-growth" '
        f'style="background:#ffffff;border-color:{growth_border};'
        f'color:{growth_color};">'
        f'{growth_arrow} {abs(growth):.1f}%'
        f'</span>'
        f'</div>'
        f'</div>'
    )

    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_header(on_filter_change=None):
    with st.container(border=True):
        title_col, view_label_col, view_col, fy_label_col, fy_col, run_col, content_col, right = st.columns(
            [1.55, .45, .72, .22, .82, .82, 3.10, 1.05], gap="small", vertical_alignment="center"
        )
        with title_col:
            st.markdown('<div class="pnl-header-marker">P&amp;L Dashboard</div>', unsafe_allow_html=True)
        with view_label_col:
            st.markdown('<div class="pnl-inline-label">View Type</div>', unsafe_allow_html=True)
        with view_col:
            view_type = st.selectbox("View Type", ["Origin", "Destination"], key="pnl_view_type", label_visibility="collapsed", on_change=on_filter_change)
        with fy_label_col:
            st.markdown('<div class="pnl-inline-label">F.Y.</div>', unsafe_allow_html=True)
        with fy_col:
            fy = st.selectbox("Financial Year", FY_OPTIONS, key="pnl_fy", label_visibility="collapsed", on_change=on_filter_change)
        with run_col:
            run_report = st.button("▶ Run Report", key="pnl_run_report", type="primary", width="stretch")
        with content_col:
            # Keep this column as genuine empty space. Rendering filter chips
            # here can create an overflowing layer over the controls.
            st.markdown('<div aria-hidden="true" style="height:1px"></div>', unsafe_allow_html=True)
        with right:
            export_placeholder = st.empty()
    return view_type, fy, run_report, export_placeholder


def build_monthly_comparison(df: pd.DataFrame, prev_df: pd.DataFrame, divisor: float) -> pd.DataFrame:
    current = df.groupby("Month", observed=False, as_index=False).agg(
        Business=("REVENUE", "sum"), Expense=("EXPENSE", "sum"), PNL=("PNL", "sum")
    )
    previous = prev_df.groupby("Month", observed=False, as_index=False).agg(
        PY_PNL=("PNL", "sum")
    ) if prev_df is not None and not prev_df.empty else pd.DataFrame(columns=["Month", "PY_PNL"])

    result = current.merge(previous, on="Month", how="left")
    result["Month"] = pd.Categorical(result["Month"], MONTH_ORDER, ordered=True)
    result = result.sort_values("Month")
    for col in ["Business", "Expense", "PNL", "PY_PNL"]:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0) / divisor
    result["Margin %"] = result.apply(
        lambda r: (r["PNL"] / r["Business"] * 100) if r["Business"] else 0,
        axis=1,
    )
    return result


def build_group_summary(df: pd.DataFrame, prev_df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    current = df.groupby(group_col, dropna=False, as_index=False).agg(
        Business=("REVENUE", "sum"),
        Expense=("EXPENSE", "sum"),
        PNL=("PNL", "sum"),
        GRs=("grno", "nunique"),
    )

    previous = (
        prev_df.groupby(group_col, dropna=False, as_index=False).agg(
            PY_BUSINESS=("REVENUE", "sum"),
            PY_PNL=("PNL", "sum"),
        )
        if (
            prev_df is not None
            and not prev_df.empty
            and group_col in prev_df.columns
        )
        else pd.DataFrame(columns=[group_col, "PY_BUSINESS", "PY_PNL"])
    )

    summary = current.merge(previous, on=group_col, how="left")
    summary["PY_BUSINESS"] = pd.to_numeric(
        summary["PY_BUSINESS"], errors="coerce"
    ).fillna(0)
    summary["PY_PNL"] = pd.to_numeric(
        summary["PY_PNL"], errors="coerce"
    ).fillna(0)

    summary["Margin %"] = summary.apply(
        lambda r: pnl_margin(r["Business"], r["PNL"]),
        axis=1,
    )
    summary["LY Margin %"] = summary.apply(
        lambda r: pnl_margin(r["PY_BUSINESS"], r["PY_PNL"]),
        axis=1,
    )
    summary["Growth %"] = summary.apply(
        lambda r: pct_change(r["PNL"], r["PY_PNL"]),
        axis=1,
    )

    return summary


def build_pnl_yoy_trend(current_df, previous_df, trend_type, date_col, fy_start, prev_fy_start):
    cur = current_df[[date_col, "PNL", "FIN_MONTH"]].copy()
    prev = previous_df[[date_col, "PNL", "FIN_MONTH"]].copy() if previous_df is not None and not previous_df.empty else pd.DataFrame()
    cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty:
        prev[date_col] = pd.to_datetime(prev[date_col], errors="coerce")
    fy_start_ts = pd.to_datetime(fy_start)
    prev_start_ts = pd.to_datetime(prev_fy_start)
    if trend_type == "Daily":
        trend = cur.groupby(cur[date_col].dt.date)["PNL"].sum().reset_index(); trend.columns = ["Period", "PNL"]
        trend["Key"] = (pd.to_datetime(trend["Period"]) - fy_start_ts).dt.days
        py = prev.groupby(prev[date_col].dt.date)["PNL"].sum().reset_index() if not prev.empty else pd.DataFrame()
        if not py.empty:
            py.columns = ["Period", "PY_PNL"]; py["Key"] = (pd.to_datetime(py["Period"]) - prev_start_ts).dt.days
    elif trend_type == "Weekly":
        trend = cur.groupby(cur[date_col].dt.to_period("W"))["PNL"].sum().reset_index()
        trend["Period"] = trend[date_col].astype(str); trend["Key"] = (trend[date_col].dt.start_time - fy_start_ts).dt.days // 7
        trend = trend.drop(columns=[date_col])
        py = prev.groupby(prev[date_col].dt.to_period("W"))["PNL"].sum().reset_index() if not prev.empty else pd.DataFrame()
        if not py.empty:
            py["Key"] = (py[date_col].dt.start_time - prev_start_ts).dt.days // 7
            py = py.rename(columns={"PNL": "PY_PNL"}).drop(columns=[date_col])
    elif trend_type == "Quarterly":
        trend = cur.assign(Period=cur["FIN_MONTH"].map(QUARTER_MAP)).groupby("Period")["PNL"].sum().reset_index()
        trend["Period"] = pd.Categorical(trend["Period"], QUARTER_ORDER, ordered=True); trend = trend.sort_values("Period"); trend["Key"] = trend["Period"].astype(str)
        py = prev.assign(Key=prev["FIN_MONTH"].map(QUARTER_MAP)).groupby("Key")["PNL"].sum().reset_index().rename(columns={"PNL": "PY_PNL"}) if not prev.empty else pd.DataFrame()
    else:
        trend = cur.assign(Period=cur["FIN_MONTH"].map(MONTH_MAP)).groupby("Period")["PNL"].sum().reset_index()
        trend["Period"] = pd.Categorical(trend["Period"], MONTH_ORDER, ordered=True); trend = trend.sort_values("Period"); trend["Key"] = trend["Period"].astype(str)
        py = prev.assign(Key=prev["FIN_MONTH"].map(MONTH_MAP)).groupby("Key")["PNL"].sum().reset_index().rename(columns={"PNL": "PY_PNL"}) if not prev.empty else pd.DataFrame()
    if py.empty:
        py = pd.DataFrame(columns=["Key", "PY_PNL"])
    trend = trend.merge(py[["Key", "PY_PNL"]], on="Key", how="left")
    trend["PY_PNL"] = pd.to_numeric(trend["PY_PNL"], errors="coerce").fillna(0)
    return trend


def render_top_n_pnl_table(
    df,
    prev_df,
    group_col,
    entity_name,
    unit,
    divisor,
    widget_key,
    subtitle="",
):
    """Render the Overview-style Top-N insight table using P&L instead of business."""
    title_col, selector_col = st.columns(
        [4.2, 1.0],
        gap="small",
        vertical_alignment="center",
    )

    with selector_col:
        top_n = st.selectbox(
            f"{entity_name} to display",
            TOP_N_OPTIONS,
            index=0,
            format_func=lambda value: f"Top {value}",
            key=f"{widget_key}_top_n",
            label_visibility="collapsed",
        )

    with title_col:
        st.markdown(
            f"<div style='font-size:18px;font-weight:400;color:#0f2744;"
            f"margin:1px 0 9px 2px;'>Top {top_n} {entity_name} by P&amp;L</div>"
            f"<div style='font-size:12px;font-weight:400;color:#64748b;"
            f"margin-top:-4px;'>{escape(subtitle)}</div>",
            unsafe_allow_html=True,
        )

    current_data = df[[group_col, "PNL"]].copy()
    current_data[group_col] = (
        current_data[group_col]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Unknown")
    )
    current_rank = (
        current_data[current_data[group_col].ne("Unknown")]
        .groupby(group_col, dropna=False)["PNL"]
        .sum()
        .reset_index(name="Current PNL")
    )

    if (
        prev_df is not None
        and not prev_df.empty
        and group_col in prev_df.columns
        and "PNL" in prev_df.columns
    ):
        previous_data = prev_df[[group_col, "PNL"]].copy()
        previous_data[group_col] = (
            previous_data[group_col]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
        )
        previous_rank = (
            previous_data[previous_data[group_col].ne("Unknown")]
            .groupby(group_col, dropna=False)["PNL"]
            .sum()
            .reset_index(name="Previous PNL")
        )
    else:
        previous_rank = pd.DataFrame(columns=[group_col, "Previous PNL"])

    ranking = current_rank.merge(previous_rank, on=group_col, how="left")
    ranking["Previous PNL"] = pd.to_numeric(
        ranking["Previous PNL"], errors="coerce"
    ).fillna(0.0)
    ranking["P&L Display"] = (
        pd.to_numeric(ranking["Current PNL"], errors="coerce").fillna(0.0)
        / divisor
    ).round(2)

    # Share is based on absolute P&L so mixed profit/loss values remain meaningful.
    total_abs_pnl = float(ranking["Current PNL"].abs().sum())
    ranking["Share %"] = (
        ranking["Current PNL"].abs() / total_abs_pnl * 100
        if total_abs_pnl else 0.0
    )
    ranking["Growth %"] = ranking.apply(
        lambda row: pct_change(row["Current PNL"], row["Previous PNL"])
        if row["Previous PNL"] != 0 else None,
        axis=1,
    )
    ranking = (
        ranking.sort_values("Current PNL", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    if ranking.empty:
        st.info(f"No {entity_name.lower()} P&L is available for the selected filters.")
        return

    max_abs_value = max(float(ranking["P&L Display"].abs().max()), 1.0)
    prefix = "cust" if entity_name == "Customers" else "route"
    bar_gradient = (
        "linear-gradient(90deg,#60a5fa,#2563eb)"
        if prefix == "cust"
        else "linear-gradient(90deg,#2dd4bf,#0f766e)"
    )
    singular_name = "Customer" if entity_name == "Customers" else "Route"
    rows = []

    for idx, row in ranking.iterrows():
        pnl_display = float(row["P&L Display"] or 0)
        share_pct = float(row["Share %"] or 0)
        bar_width = min((abs(pnl_display) / max_abs_value) * 100, 100)
        growth = row["Growth %"]

        if pd.isna(growth):
            growth_html = f"<span class='{prefix}-growth new'>NEW</span>"
        else:
            positive = growth >= 0
            growth_class = "up" if positive else "down"
            growth_arrow = "▲" if positive else "▼"
            growth_html = (
                f"<span class='{prefix}-growth {growth_class}'>"
                f"{growth_arrow} {abs(growth):.1f}%</span>"
            )

        full_name = escape(str(row[group_col]))
        value_color = "#0f172a" if pnl_display >= 0 else "#dc2626"
        rows.append(
            "<tr>"
            f"<td class='{prefix}-rank'>{idx + 1}</td>"
            f"<td class='{prefix}-name' title='{full_name}'>{full_name}</td>"
            f"<td class='{prefix}-revenue'>"
            f"<div class='{prefix}-value' style='color:{value_color};'>"
            f"₹{pnl_display:.2f} {escape(str(unit))}</div>"
            f"<div class='{prefix}-bar-track'>"
            f"<div class='{prefix}-bar-fill' style='width:{bar_width:.1f}%'></div>"
            "</div></td>"
            f"<td class='{prefix}-share'>{share_pct:.1f}%</td>"
            f"<td class='{prefix}-yoy'>{growth_html}</td>"
            "</tr>"
        )

    table_html = f"""
    <style>
        .{prefix}-insight-wrap {{
            width:100%; overflow-x:auto; margin-top:5px;
            border:1px solid #e2e8f0; border-radius:10px;
            background:#ffffff;
        }}
        .{prefix}-insight-table {{
            width:100%; border-collapse:collapse;
            table-layout:fixed; font-size:12px; color:#334155;
        }}
        .{prefix}-insight-table th {{
            padding:7px 6px; background:#f8fafc;
            color:#64748b; font-size:12px; font-weight:400;
            text-align:left; border-bottom:1px solid #e2e8f0;
            white-space:nowrap;
        }}
        .{prefix}-insight-table td {{
            padding:8px 6px; border-bottom:1px solid #edf2f7;
            vertical-align:middle;
        }}
        .{prefix}-insight-table tr:last-child td {{border-bottom:0;}}
        .{prefix}-insight-table tbody tr:hover {{background:#f8fbff;}}
        .{prefix}-rank {{
            width:4%; padding-left:2px !important; padding-right:2px !important;
            text-align:center; font-weight:400; color:#64748b;
        }}
        .{prefix}-name {{
            width:38%; padding-left:3px !important;
            font-weight:400; color:#1e293b;
            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }}
        .{prefix}-revenue {{width:32%;}}
        .{prefix}-value {{font-weight:400; margin-bottom:3px;}}
        .{prefix}-bar-track {{
            width:100%; height:5px; border-radius:999px;
            background:#e8eef8; overflow:hidden;
        }}
        .{prefix}-bar-fill {{
            height:5px; border-radius:999px;
            background:{bar_gradient};
        }}
        .{prefix}-share {{
            width:12%; text-align:right; font-weight:400; color:#475569;
        }}
        .{prefix}-yoy {{width:14%; text-align:right;}}
        .{prefix}-growth {{
            display:inline-block; min-width:50px; text-align:right;
            font-size:11px; font-weight:400;
        }}
        .{prefix}-growth.up {{color:#16a34a;}}
        .{prefix}-growth.down {{color:#dc2626;}}
        .{prefix}-growth.new {{color:#7c3aed;}}
    </style>
    <div class="{prefix}-insight-wrap">
        <table class="{prefix}-insight-table">
            <colgroup>
                <col style="width:4%">
                <col style="width:38%">
                <col style="width:32%">
                <col style="width:12%">
                <col style="width:14%">
            </colgroup>
            <thead>
                <tr>
                    <th style="text-align:center;">#</th>
                    <th>{singular_name}</th>
                    <th>P&amp;L ({escape(str(unit))})</th>
                    <th style="text-align:right;">% Share</th>
                    <th style="text-align:right;">vs LY</th>
                </tr>
            </thead>
            <tbody>{''.join(rows)}</tbody>
        </table>
    </div>
    """

    if hasattr(st, "html"):
        st.html(table_html)
    else:
        st.markdown(table_html, unsafe_allow_html=True)

# =====================================================
# Main page
# =====================================================
def show_pnl_dashboard() -> None:
    _inject_pnl_css()
    if "pnl_report_ready" not in st.session_state:
        st.session_state["pnl_report_ready"] = False

    def _invalidate_pnl_report():
        st.session_state["pnl_report_ready"] = False
        st.session_state.pop("pnl_report_df", None)
        st.session_state.pop("pnl_report_prev_df", None)

    pending_view_type, pending_fy, run_report, export_placeholder = render_header(_invalidate_pnl_report)

    if pending_fy == "Select FY":
        if run_report:
            st.warning("Please select a financial year before running the report.")
        else:
            st.info("Select a financial year, then click ▶ Run Report.")
        return

    if run_report:
        st.session_state["pnl_report_ready"] = False
        start_date, end_date = get_date_range(pending_fy)
        prev_fy = get_previous_fy(pending_fy)
        prev_start, prev_end = get_date_range(prev_fy)
        with st.spinner("Loading P&L data..."):
            raw_df, raw_prev_df = load_pnl_data_pair(
                start_date, end_date, prev_start, prev_end, pending_view_type
            )
        st.session_state["pnl_report_df"] = raw_df
        st.session_state["pnl_report_prev_df"] = raw_prev_df
        st.session_state["pnl_active_fy"] = pending_fy
        st.session_state["pnl_active_view_type"] = pending_view_type
        st.session_state["pnl_report_ready"] = True

    if not st.session_state.get("pnl_report_ready", False):
        st.info("Select a financial year, then click ▶ Run Report.")
        return
    active_fy = st.session_state.get("pnl_active_fy")
    active_view_type = st.session_state.get("pnl_active_view_type")
    if not active_fy or not active_view_type:
        st.session_state["pnl_report_ready"] = False
        st.info("Select a financial year, then click ▶ Run Report.")
        return
    if pending_fy != active_fy or pending_view_type != active_view_type:
        st.info("Selections changed. Click ▶ Run Report to refresh the dashboard.")
        return

    stored_df = st.session_state.get("pnl_report_df")
    stored_prev_df = st.session_state.get("pnl_report_prev_df")
    if stored_df is None:
        st.session_state["pnl_report_ready"] = False
        st.info("Click ▶ Run Report to load the dashboard.")
        return

    fy = active_fy
    view_type = active_view_type
    # Date context is also required by downstream trend charts on every
    # Streamlit rerun, including reruns caused only by secondary filters.
    start_date, end_date = get_date_range(fy)
    prev_fy = get_previous_fy(fy)
    prev_start, prev_end = get_date_range(prev_fy)
    raw_df = stored_df.copy()
    raw_prev_df = stored_prev_df.copy() if stored_prev_df is not None else pd.DataFrame()

    df = normalize_pnl_columns(raw_df)
    prev_df = normalize_pnl_columns(raw_prev_df)

    if df.empty:
        st.warning("No P&L data found for the selected financial year.")
        return

    missing = validate_pnl_data(df)
    if missing:
        st.error(f"Missing columns returned by stored procedure: {missing}")
        st.write("Available columns:", list(df.columns))
        return

    filter_cols = st.columns(8, gap="small")

    data_scope = st.session_state.get("data_scope", {}) or {}
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")

    if locked_branch:
        branch_rows = df[df["branch"].astype(str).str.casefold() == str(locked_branch).casefold()]
        if not branch_rows.empty:
            locked_branch = branch_rows["branch"].iloc[0]
            locked_circle = branch_rows["circle"].iloc[0]
            locked_zone = branch_rows["zone"].iloc[0]
    elif locked_circle:
        circle_rows = df[df["circle"].astype(str).str.casefold() == str(locked_circle).casefold()]
        if not circle_rows.empty:
            locked_circle = circle_rows["circle"].iloc[0]
            locked_zone = circle_rows["zone"].iloc[0]

    # Overview-equivalent filter behavior.
    # Company and Load Type remain single-select. Zone/Circle/Branch/Quarter/Month
    # use checkbox slicers; Circle and Branch have instant search. Empty selection = All.
    with filter_cols[0]:
        company = st.selectbox("▥ Company", ["All"] + _safe_options(df, "COMPNAME"), key="pnl_company")
    df = _apply_filter(df, "COMPNAME", company)

    filter_source_df = df.copy()

    # Cascading hierarchy filters:
    # Zone -> Circle -> Branch -> Quarter -> Month
    with filter_cols[1]:
        zone_options = _safe_options(filter_source_df, "zone")
        selected_zones = _checkbox_slicer(
            "◉ Zone", zone_options, key="pnl_zone_slicer",
            locked_values=[locked_zone] if locked_zone else None,
        )

    circle_source_df = filter_source_df.copy()
    if selected_zones:
        circle_source_df = circle_source_df[
            circle_source_df["zone"].isin(selected_zones)
        ]

    with filter_cols[2]:
        circle_options = _safe_options(circle_source_df, "circle")
        selected_circles = _checkbox_slicer(
            "◎ Circle", circle_options, key="pnl_circle_slicer",
            locked_values=[locked_circle] if locked_circle else None,
            searchable=True,
        )

    branch_source_df = circle_source_df.copy()
    if selected_circles:
        branch_source_df = branch_source_df[
            branch_source_df["circle"].isin(selected_circles)
        ]

    with filter_cols[3]:
        branch_options = _safe_options(branch_source_df, "branch")
        selected_branches = _checkbox_slicer(
            "⌂ Branch", branch_options, key="pnl_branch_slicer",
            locked_values=[locked_branch] if locked_branch else None,
            searchable=True,
        )

    quarter_source_df = branch_source_df.copy()
    if selected_branches:
        quarter_source_df = quarter_source_df[
            quarter_source_df["branch"].isin(selected_branches)
        ]

    with filter_cols[4]:
        available_quarters = [
            q for q in QUARTER_ORDER
            if q in quarter_source_df["Quarter"].dropna().unique().tolist()
        ]
        selected_quarters = _checkbox_slicer(
            "▦ Quarter", available_quarters, key="pnl_quarter_slicer"
        )

    month_source_df = quarter_source_df.copy()
    if selected_quarters:
        month_source_df = month_source_df[
            month_source_df["Quarter"].isin(selected_quarters)
        ]

    with filter_cols[5]:
        available_months = [
            m for m in MONTH_ORDER
            if m in month_source_df["Month"].dropna().unique().tolist()
        ]
        selected_months = _checkbox_slicer(
            "▣ Month", available_months, key="pnl_month_slicer"
        )

    if selected_zones:
        df = df[df["zone"].isin(selected_zones)]
    if selected_circles:
        df = df[df["circle"].isin(selected_circles)]
    if selected_branches:
        df = df[df["branch"].isin(selected_branches)]
    if selected_quarters:
        df = df[df["Quarter"].isin(selected_quarters)]
    if selected_months:
        df = df[df["Month"].isin(selected_months)]

    with filter_cols[6]:
        load_type = st.selectbox(
            "▤ Load Type", ["All"] + _safe_options(df, "LOADTYPE"), key="pnl_loadtype"
        )
    df = _apply_filter(df, "LOADTYPE", load_type)

    with filter_cols[7]:
        conversion_type = st.selectbox("₹ Conversion", ["Crore", "Lac"], key="pnl_conversion")

    divisor, unit = get_conversion(conversion_type)

    # Compatibility aliases for existing downstream code.
    zone = selected_zones[0] if len(selected_zones) == 1 else "All"
    circle = selected_circles[0] if len(selected_circles) == 1 else "All"
    branch = selected_branches[0] if len(selected_branches) == 1 else "All"
    quarter = selected_quarters[0] if len(selected_quarters) == 1 else "All"
    month = selected_months[0] if len(selected_months) == 1 else "All"

    # Apply the same active selections to LY data.
    if prev_df is not None and not prev_df.empty:
        if company != "All":
            prev_df = prev_df[prev_df["COMPNAME"].eq(company)]
        if selected_zones:
            prev_df = prev_df[prev_df["zone"].isin(selected_zones)]
        if selected_circles:
            prev_df = prev_df[prev_df["circle"].isin(selected_circles)]
        if selected_branches:
            prev_df = prev_df[prev_df["branch"].isin(selected_branches)]
        if selected_quarters:
            prev_df = prev_df[prev_df["Quarter"].isin(selected_quarters)]
        if selected_months:
            prev_df = prev_df[prev_df["Month"].isin(selected_months)]
        if load_type != "All":
            prev_df = prev_df[prev_df["LOADTYPE"].eq(load_type)]

    st.markdown("<div aria-hidden='true' style='height:4px'></div>", unsafe_allow_html=True)

    if df.empty:
        st.warning("No data found for selected filters.")
        return

    # Lazy CSV export
    safe_fy = fy.replace("/", "-")
    export_key = f"pnl_export_ready_{view_type}_{safe_fy}"
    with export_placeholder:
        if not st.session_state.get(export_key, False):
            if st.button("⬇ Prepare CSV", key=f"prepare_{export_key}", width="content"):
                st.session_state[export_key] = True
                st.rerun()
        else:
            st.download_button(
                "⬇ Download CSV",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"pnl_dashboard_{view_type.lower()}_{safe_fy}.csv",
                mime="text/csv",
                key=f"download_{export_key}",
                width="content",
                on_click=lambda: st.session_state.update({export_key: False}),
            )

    current = calculate_pnl_kpis(df)
    previous = calculate_pnl_kpis(prev_df)

    kpi_specs = [
        ("Business", amount_text(current["revenue"], conversion_type), amount_text(previous["revenue"], conversion_type), pct_change(current["revenue"], previous["revenue"]), "💰", "#2563eb", False),
        ("Expense", amount_text(current["expense"], conversion_type), amount_text(previous["expense"], conversion_type), pct_change(current["expense"], previous["expense"]), "🧾", "#2563eb", True),
        ("P&L", amount_text(current["pnl"], conversion_type), amount_text(previous["pnl"], conversion_type), pct_change(current["pnl"], previous["pnl"]), "📈", "#2563eb" if current["pnl"] >= 0 else "#dc2626", False),
        ("P&L Margin", f'{current["margin"]:.2f}%', f'{previous["margin"]:.2f}%', current["margin"] - previous["margin"], "🎯", "#2563eb", False),
        ("FTL P&L", amount_text(current["ftl_pnl"], conversion_type), amount_text(previous["ftl_pnl"], conversion_type), pct_change(current["ftl_pnl"], previous["ftl_pnl"]), "🚛", "#2563eb", False),
        ("LTL P&L", amount_text(current["ltl_pnl"], conversion_type), amount_text(previous["ltl_pnl"], conversion_type), pct_change(current["ltl_pnl"], previous["ltl_pnl"]), "🚚", "#2563eb", False),
        ("Profit GR", f'{current["profit_gr"]:,}', f'{previous["profit_gr"]:,}', pct_change(current["profit_gr"], previous["profit_gr"]), "✅", "#2563eb", False),
        ("Loss GR", f'{current["loss_gr"]:,}', f'{previous["loss_gr"]:,}', pct_change(current["loss_gr"], previous["loss_gr"]), "⚠️", "#2563eb", True),
        ("Avg P&L / GR", f'₹{current["avg_pnl_gr"]:,.0f}', f'₹{previous["avg_pnl_gr"]:,.0f}', pct_change(current["avg_pnl_gr"], previous["avg_pnl_gr"]), "📦", "#2563eb", False),
    ]

    kpi_cols = st.columns(9, gap="small")
    for col, spec in zip(kpi_cols, kpi_specs):
        with col:
            render_kpi_card(*spec)

    # =====================================================
    # STEP 1: Overview-style P&L Trend, Load Type and Company
    # =====================================================
    compact_spacer()

    row1, row2 = st.columns([1.20, 0.80], gap="medium")

    with row1:
        with st.container(border=True):
            title_col, filter_col = st.columns([2, 2], gap="small")

            total_growth = pct_change(current["pnl"], previous["pnl"])
            with title_col:
                trend_badge_color = "#166534" if total_growth >= 0 else "#dc2626"
                trend_arrow = "▲" if total_growth >= 0 else "▼"
                st.markdown(
                    f"<div style='font-size:14px;font-weight:400;color:#0f172a;'>P&L Trend "
                    f"<span style='font-size:11px;font-weight:700;color:{trend_badge_color};'>"
                    f"({trend_arrow} {abs(total_growth):.1f}% vs LY)</span></div>",
                    unsafe_allow_html=True,
                )

            with filter_col:
                trend_options = ["Daily", "Weekly", "Monthly", "Quarterly"]
                trend_type = st.session_state.get("pnl_trend_type_value", "Monthly")
                if trend_type not in trend_options:
                    trend_type = "Monthly"
                    st.session_state["pnl_trend_type_value"] = "Monthly"

                trend_btn_cols = st.columns(len(trend_options), gap="small")
                for trend_index, trend_label in enumerate(trend_options):
                    with trend_btn_cols[trend_index]:
                        if st.button(
                            trend_label,
                            key=f"pnl_trend_btn_{trend_index}",
                            type="primary" if trend_type == trend_label else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["pnl_trend_type_value"] = trend_label
                            st.rerun()

            trend_df = build_pnl_yoy_trend(
                df, prev_df, trend_type, "grdt", start_date, prev_start
            )
            trend_df["Current P&L"] = pd.to_numeric(
                trend_df["PNL"], errors="coerce"
            ).fillna(0) / divisor
            trend_df["Previous P&L"] = pd.to_numeric(
                trend_df["PY_PNL"], errors="coerce"
            ).fillna(0) / divisor
            trend_df["Growth %"] = trend_df.apply(
                lambda r: pct_change(r["Current P&L"], r["Previous P&L"]),
                axis=1,
            )
            trend_df["Growth Label"] = trend_df["Growth %"].apply(
                lambda value: f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"
            )

            fig_yoy = go.Figure()
            fig_yoy.add_trace(
                go.Bar(
                    x=trend_df["Period"],
                    y=trend_df["Previous P&L"],
                    name=f"LY ({prev_fy})",
                    marker=dict(
                        color="#cbd5e1",
                        line=dict(color="#94a3b8", width=1.3),
                    ),
                    text=trend_df["Previous P&L"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#475569", family="Arial"),
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>LY P&L: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )
            fig_yoy.add_trace(
                go.Bar(
                    x=trend_df["Period"],
                    y=trend_df["Current P&L"],
                    name=f"Current ({fy})",
                    marker=dict(
                        color="#2563eb",
                        line=dict(color="#1d4ed8", width=1.3),
                    ),
                    text=trend_df["Current P&L"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#2563eb", family="Arial"),
                    cliponaxis=False,
                    hovertemplate=(
                        f"<b>%{{x}}</b><br>Current P&L: ₹%{{y:.2f}} {unit}<extra></extra>"
                    ),
                )
            )

            all_trend_values = pd.concat(
                [
                    trend_df["Current P&L"].abs(),
                    trend_df["Previous P&L"].abs(),
                ],
                ignore_index=True,
            )
            trend_max = all_trend_values.max()
            trend_max = trend_max if pd.notna(trend_max) and trend_max > 0 else 1

            if len(trend_df) <= 40:
                for _, trend_row in trend_df.iterrows():
                    growth_value = float(trend_row["Growth %"] or 0)
                    label_color = "#166534" if growth_value >= 0 else "#dc2626"
                    current_value = float(trend_row["Current P&L"] or 0)
                    previous_value = float(trend_row["Previous P&L"] or 0)
                    positive_top = max(current_value, previous_value, 0)
                    negative_bottom = min(current_value, previous_value, 0)
                    gap = trend_max * (0.24 if trend_type == "Monthly" else 0.16)
                    annotation_y = positive_top + gap if positive_top > 0 else negative_bottom - gap
                    fig_yoy.add_annotation(
                        x=trend_row["Period"],
                        y=annotation_y,
                        text=trend_row["Growth Label"],
                        showarrow=False,
                        font=dict(size=12, color=label_color, family="Arial"),
                    )

            fig_yoy.add_hline(y=0, line_color="#64748b", line_width=1)
            fig_yoy.update_layout(
                barmode="group",
                height=310,
                margin=dict(l=8, r=8, t=24, b=8),
                plot_bgcolor="#fbfdff",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    x=0,
                    font=dict(size=11),
                ),
                font=dict(size=11, family="Arial"),
                xaxis_title="",
                yaxis_title=f"P&L ({unit})",
                bargap=0.22,
                bargroupgap=0.08,
            )
            fig_yoy.update_xaxes(
                showgrid=False,
                showline=False,
                zeroline=False,
                tickfont=dict(size=11),
            )
            fig_yoy.update_yaxes(
                showgrid=False,
                showline=False,
                zeroline=False,
                tickfont=dict(size=11),
                title_font=dict(size=12),
            )
            st.plotly_chart(
                fig_yoy,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )

    with row2:
        LOAD_TITLE_FONT = 16
        LOAD_CENTER_VALUE_FONT = 19
        LOAD_CENTER_LABEL_FONT = 12
        LOAD_LABEL_FONT = 14
        LOAD_VALUE_FONT = 14
        LOAD_SUBTEXT_FONT = 12

        COMPANY_TITLE_FONT = 16
        COMPANY_NAME_FONT = 13
        COMPANY_VALUE_FONT = 13
        COMPANY_SUBTEXT_FONT = 11

        # P&L by Load Type — same Overview layout with LY arrow indicators.
        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:{LOAD_TITLE_FONT}px;font-weight:600;'
                f'color:#0f172a;margin:0 0 5px 0;line-height:1.1;">'
                f'P&L by Load Type (CY)</div>',
                unsafe_allow_html=True,
            )

            ftl = float(df.loc[df["LOADTYPE"].eq("FTL"), "PNL"].sum())
            ltl = float(df.loc[df["LOADTYPE"].eq("LTL"), "PNL"].sum())
            prev_ftl = float(
                prev_df.loc[prev_df["LOADTYPE"].eq("FTL"), "PNL"].sum()
            ) if prev_df is not None and not prev_df.empty else 0.0
            prev_ltl = float(
                prev_df.loc[prev_df["LOADTYPE"].eq("LTL"), "PNL"].sum()
            ) if prev_df is not None and not prev_df.empty else 0.0

            load_abs_total = abs(ftl) + abs(ltl)
            ftl_share = abs(ftl) / load_abs_total * 100 if load_abs_total else 0
            ltl_share = abs(ltl) / load_abs_total * 100 if load_abs_total else 0
            ftl_yoy = pct_change(ftl, prev_ftl)
            ltl_yoy = pct_change(ltl, prev_ltl)

            load_chart_col, load_legend_col = st.columns(
                [0.80, 1.20],
                gap="small",
                vertical_alignment="center",
            )

            with load_chart_col:
                fig_load = go.Figure(
                    data=[
                        go.Pie(
                            labels=["FTL", "LTL"],
                            values=[abs(ftl), abs(ltl)],
                            customdata=[ftl / divisor, ltl / divisor],
                            hole=0.66,
                            sort=False,
                            rotation=0,
                            direction="clockwise",
                            marker=dict(
                                colors=["#2563eb", "#0f766e"],
                                line=dict(color="#ffffff", width=1.5),
                            ),
                            textinfo="none",
                            hovertemplate=(
                                "<b>%{label}</b><br>"
                                f"P&L: ₹%{{customdata:.2f}} {unit}<br>"
                                "Share: %{percent}<extra></extra>"
                            ),
                        )
                    ]
                )
                fig_load.update_layout(
                    height=178,
                    margin=dict(l=0, r=0, t=12, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    annotations=[
                        dict(
                            x=0.5,
                            y=0.55,
                            text=f"<b>₹{(ftl + ltl) / divisor:.2f} {unit}</b>",
                            showarrow=False,
                            font=dict(
                                size=LOAD_CENTER_VALUE_FONT,
                                color="#0f172a",
                                family="Arial",
                            ),
                        ),
                        dict(
                            x=0.5,
                            y=0.39,
                            text="Total P&L",
                            showarrow=False,
                            font=dict(
                                size=LOAD_CENTER_LABEL_FONT,
                                color="#64748b",
                                family="Arial",
                            ),
                        ),
                    ],
                )
                st.plotly_chart(
                    fig_load,
                    width="stretch",
                    config={"displayModeBar": False, "responsive": True},
                )

            with load_legend_col:
                def _load_row(label, value, share, py_value, growth, dot_color):
                    growth_color = "#16a34a" if growth >= 0 else "#dc2626"
                    growth_arrow = "▲" if growth >= 0 else "▼"
                    value_color = "#0f172a" if value >= 0 else "#dc2626"
                    return (
                        '<div style="display:grid;'
                        'grid-template-columns:13px minmax(40px,.75fr) minmax(84px,auto) minmax(48px,auto);'
                        'align-items:center;gap:8px;">'
                        f'<span style="width:11px;height:11px;border-radius:50%;background:{dot_color};display:inline-block;"></span>'
                        f'<span style="font-size:{LOAD_LABEL_FONT}px;font-weight:600;color:#334155;">{label}</span>'
                        f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;color:{value_color};white-space:nowrap;">'
                        f'₹{value / divisor:.2f} {unit}</span>'
                        f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;color:#334155;white-space:nowrap;text-align:right;">'
                        f'{share:.1f}%</span>'
                        f'<span style="grid-column:2/5;font-size:{LOAD_SUBTEXT_FONT}px;color:#64748b;white-space:nowrap;">'
                        f'LY ₹{py_value / divisor:.2f} {unit} · '
                        f'<span style="color:{growth_color};font-weight:700;">'
                        f'{growth_arrow} {abs(growth):.1f}%</span></span>'
                        '</div>'
                    )

                load_legend_html = (
                    '<div style="display:flex;flex-direction:column;gap:17px;padding:12px 0 3px;line-height:1.2;">'
                    + _load_row("FTL", ftl, ftl_share, prev_ftl, ftl_yoy, "#2563eb")
                    + _load_row("LTL", ltl, ltl_share, prev_ltl, ltl_yoy, "#0f766e")
                    + '</div>'
                )
                if hasattr(st, "html"):
                    st.html(load_legend_html)
                else:
                    st.markdown(load_legend_html, unsafe_allow_html=True)

        # P&L by Company — same Overview layout with LY arrow indicators.
        company_df = (
            df.groupby("COMPNAME", dropna=False)["PNL"]
            .sum()
            .reset_index()
            .rename(columns={"COMPNAME": "Company", "PNL": "CY PNL"})
        )
        company_df["Company"] = company_df["Company"].fillna("Unknown").astype(str)

        if prev_df is not None and not prev_df.empty and "COMPNAME" in prev_df.columns:
            prev_company_df = (
                prev_df.groupby("COMPNAME", dropna=False)["PNL"]
                .sum()
                .reset_index()
                .rename(columns={"COMPNAME": "Company", "PNL": "PY PNL"})
            )
            prev_company_df["Company"] = (
                prev_company_df["Company"].fillna("Unknown").astype(str)
            )
        else:
            prev_company_df = pd.DataFrame(columns=["Company", "PY PNL"])

        company_df = company_df.merge(prev_company_df, on="Company", how="left")
        company_df["PY PNL"] = pd.to_numeric(
            company_df["PY PNL"], errors="coerce"
        ).fillna(0)
        company_df["P&L Display"] = company_df["CY PNL"] / divisor
        company_df["PY P&L Display"] = company_df["PY PNL"] / divisor
        company_abs_total = company_df["CY PNL"].abs().sum()
        company_df["Contribution %"] = (
            company_df["CY PNL"].abs() / company_abs_total * 100
            if company_abs_total
            else 0
        )
        company_df["Growth %"] = company_df.apply(
            lambda row: pct_change(row["CY PNL"], row["PY PNL"]),
            axis=1,
        )
        company_df = company_df.sort_values(
            "CY PNL", ascending=False
        ).reset_index(drop=True)
        company_chart_df = company_df.head(6).copy()

        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:{COMPANY_TITLE_FONT}px;font-weight:600;'
                f'color:#0f172a;margin:0 0 7px 0;line-height:1.2;">'
                f'P&L by Company (CY)</div>',
                unsafe_allow_html=True,
            )

            if company_chart_df.empty:
                st.info("No company P&L is available for the selected filters.")
            else:
                company_colors = [
                    "#2563eb", "#0f766e", "#7c3aed",
                    "#f59e0b", "#ec4899", "#64748b",
                ]
                max_company_value = float(company_chart_df["CY PNL"].abs().max() or 1)
                company_rows = []

                for idx, company_row in company_chart_df.iterrows():
                    company_name = escape(str(company_row["Company"]))
                    raw_value = float(company_row["CY PNL"] or 0)
                    value = float(company_row["P&L Display"] or 0)
                    share = float(company_row["Contribution %"] or 0)
                    py_value = float(company_row["PY P&L Display"] or 0)
                    growth = float(company_row["Growth %"] or 0)
                    width_pct = min(abs(raw_value) / max_company_value * 100, 100)
                    color = company_colors[idx % len(company_colors)]
                    growth_color = "#16a34a" if growth >= 0 else "#dc2626"
                    growth_arrow = "▲" if growth >= 0 else "▼"
                    value_color = "#0f172a" if raw_value >= 0 else "#dc2626"
                    bar_color = color if raw_value >= 0 else "#dc2626"

                    company_rows.append(
                        f'<div title="{company_name} | LY ₹{py_value:.2f} {unit} | {growth_arrow} {abs(growth):.1f}%" '
                        f'style="display:grid;grid-template-columns:minmax(150px,195px) minmax(55px,1fr) '
                        f'minmax(84px,auto) minmax(58px,auto);align-items:center;gap:8px;margin:9px 0;line-height:1.2;">'
                        f'<div style="font-size:{COMPANY_NAME_FONT}px;font-weight:600;color:#334155;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{company_name}</div>'
                        f'<div style="height:9px;background:#e8eef5;border-radius:999px;overflow:hidden;box-shadow:inset 0 1px 2px rgba(15,23,42,.10);">'
                        f'<div style="height:9px;width:{width_pct:.2f}%;background:{bar_color};border-radius:999px;"></div></div>'
                        f'<div style="font-size:{COMPANY_VALUE_FONT}px;font-weight:700;color:{value_color};white-space:nowrap;">₹{value:.2f} {unit}</div>'
                        f'<div style="font-size:{COMPANY_VALUE_FONT}px;font-weight:700;color:#334155;min-width:54px;text-align:right;white-space:nowrap;">{share:.2f}%</div>'
                        f'<div style="grid-column:2/5;margin-top:-3px;font-size:{COMPANY_SUBTEXT_FONT}px;color:#64748b;white-space:nowrap;">'
                        f'LY ₹{py_value:.2f} {unit} · <span style="color:{growth_color};font-weight:700;">'
                        f'{growth_arrow} {abs(growth):.1f}%</span></div></div>'
                    )

                company_html = (
                    '<div style="padding:0 3px 4px 3px;">'
                    + ''.join(company_rows)
                    + '</div>'
                )
                if hasattr(st, "html"):
                    st.html(company_html)
                else:
                    st.markdown(company_html, unsafe_allow_html=True)

    # =====================================================
    # Month-on-Month P&L and P&L by Zone — side by side
    # =====================================================
    compact_spacer()
    mom_col, zone_col = st.columns([1.35, 1.0], gap="medium")

    with mom_col:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:16px;font-weight:600;color:#0f2744;margin:2px 0 8px 2px;'>"
                "Month on Month P&L & Growth</div>",
                unsafe_allow_html=True,
            )

            mom_df = df.groupby("Month", observed=False, as_index=False)["PNL"].sum()
            mom_df["Month"] = pd.Categorical(
                mom_df["Month"], categories=MONTH_ORDER, ordered=True
            )
            mom_df = mom_df.sort_values("Month").reset_index(drop=True)
            mom_df["P&L Display"] = mom_df["PNL"] / divisor

            def _safe_mom_growth(values: pd.Series) -> pd.Series:
                result = pd.Series(index=values.index, dtype="float64")
                result.iloc[0] = float("nan")
                for idx in range(1, len(values)):
                    previous_value = float(values.iloc[idx - 1])
                    current_value = float(values.iloc[idx])
                    if previous_value == 0:
                        result.iloc[idx] = float("nan")
                    else:
                        result.iloc[idx] = (
                            (current_value - previous_value) / abs(previous_value)
                        ) * 100
                return result

            mom_df["MoM Growth"] = _safe_mom_growth(mom_df["PNL"])
            mom_df["Growth Label"] = mom_df["MoM Growth"].apply(
                lambda value: (
                    f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"
                    if pd.notna(value) else ""
                )
            )

            if mom_df.empty:
                st.info("No monthly P&L data is available for the selected filters.")
            else:
                bar_colors = ["#bfdbfe"] * len(mom_df)
                growth_colors = [
                    "#16a34a" if pd.notna(value) and value >= 0 else "#dc2626"
                    for value in mom_df["MoM Growth"]
                ]

                fig_mom = go.Figure()
                fig_mom.add_trace(
                    go.Bar(
                        x=mom_df["Month"],
                        y=mom_df["P&L Display"],
                        name="P&L",
                        marker=dict(
                            color=bar_colors,
                            line=dict(color="#2563eb", width=1.3),
                        ),
                        opacity=0.92,
                        text=mom_df["P&L Display"],
                        texttemplate=f"₹%{{text:.2f}} {unit}",
                        textposition="outside",
                        textfont=dict(size=10, color="#1e3a8a", family="Arial"),
                        cliponaxis=False,
                        hovertemplate=(
                            f"<b>%{{x}}</b><br>P&L: ₹%{{y:.2f}} {unit}<extra></extra>"
                        ),
                    )
                )
                fig_mom.add_trace(
                    go.Scatter(
                        x=mom_df["Month"],
                        y=mom_df["MoM Growth"],
                        name="MoM Growth",
                        mode="lines+markers+text",
                        yaxis="y2",
                        line=dict(color="#f59e0b", width=3),
                        marker=dict(
                            size=8,
                            color=growth_colors,
                            line=dict(color="#ffffff", width=2),
                        ),
                        text=mom_df["Growth Label"],
                        textposition="top center",
                        textfont=dict(size=10, color="#334155"),
                        connectgaps=False,
                        hovertemplate=(
                            "<b>%{x}</b><br>MoM Growth: %{y:.1f}%<extra></extra>"
                        ),
                    )
                )

                pnl_values = mom_df["P&L Display"].dropna()
                pnl_min = float(pnl_values.min()) if not pnl_values.empty else 0.0
                pnl_max = float(pnl_values.max()) if not pnl_values.empty else 0.0
                pnl_span = max(abs(pnl_min), abs(pnl_max), 1.0)

                growth_values = mom_df["MoM Growth"].dropna()
                if growth_values.empty:
                    growth_range = [-100, 100]
                else:
                    growth_min = float(growth_values.min())
                    growth_max = float(growth_values.max())
                    growth_padding = max((growth_max - growth_min) * 0.25, 15.0)
                    growth_range = [growth_min - growth_padding, growth_max + growth_padding]

                fig_mom.add_hline(y=0, line_color="#94a3b8", line_width=1)
                fig_mom.update_layout(
                    height=370,
                    margin=dict(l=8, r=12, t=22, b=8),
                    plot_bgcolor="#fbfdff",
                    paper_bgcolor="rgba(0,0,0,0)",
                    bargap=0.34,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        x=0.01,
                        font=dict(size=10),
                    ),
                    xaxis=dict(
                        title="", showgrid=False, zeroline=False,
                        tickfont=dict(size=10),
                    ),
                    yaxis=dict(
                        title=dict(text=f"P&L ({unit})", font=dict(size=11)),
                        showgrid=False,
                        zeroline=False,
                        range=[
                            min(pnl_min - pnl_span * 0.18, 0),
                            max(pnl_max + pnl_span * 0.28, 0),
                        ],
                        tickfont=dict(size=10),
                    ),
                    yaxis2=dict(
                        title=dict(text="Growth (%)", font=dict(size=11)),
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        zeroline=False,
                        range=growth_range,
                        ticksuffix="%",
                        tickfont=dict(size=10),
                    ),
                )
                st.plotly_chart(
                    fig_mom,
                    width="stretch",
                    config={"displayModeBar": False, "responsive": True},
                )

    with zone_col:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:16px;font-weight:600;color:#0f2744;margin:2px 0 8px 2px;'>"
                "P&L by Zone</div>",
                unsafe_allow_html=True,
            )

            zone_df = (
                df.groupby("zone", as_index=False)["PNL"]
                .sum()
                .sort_values("PNL", ascending=False)
                .reset_index(drop=True)
            )
            zone_df["Display"] = zone_df["PNL"] / divisor
            absolute_zone_total = float(zone_df["PNL"].abs().sum())
            zone_df["Pct"] = (
                zone_df["PNL"].abs() / absolute_zone_total * 100
                if absolute_zone_total else 0.0
            )

            zone_name_map = {
                "NORTH ZONE": "North", "WEST ZONE": "West",
                "SOUTH ZONE": "South", "EAST ZONE": "East",
                "NORTH EAST ZONE": "NE", "NEPAL ZONE": "Nepal",
                "North Zone": "North", "West Zone": "West",
                "South Zone": "South", "East Zone": "East",
                "North East Zone": "NE", "Nepal Zone": "Nepal",
            }
            zone_df["Display Zone"] = zone_df["zone"].map(zone_name_map).fillna(zone_df["zone"])
            zone_colors = [
                "#2563eb", "#0f766e", "#f59e0b",
                "#7c3aed", "#ec4899", "#ef5b5b", "#64748b",
            ]

            fig_zone = go.Figure(
                go.Pie(
                    labels=zone_df["Display Zone"],
                    values=zone_df["PNL"].abs(),
                    customdata=zone_df[["Display", "Pct"]],
                    hole=0.64,
                    sort=False,
                    rotation=90,
                    direction="clockwise",
                    domain=dict(x=[0.00, 0.60], y=[0.03, 0.97]),
                    marker=dict(
                        colors=zone_colors[:len(zone_df)],
                        line=dict(color="#ffffff", width=2),
                    ),
                    textinfo="none",
                    hovertemplate=(
                        f"<b>%{{label}}</b><br>P&L: ₹%{{customdata[0]:.2f}} {unit}"
                        "<br>Contribution: %{customdata[1]:.1f}%<extra></extra>"
                    ),
                )
            )

            legend_step = 0.17 if len(zone_df) <= 6 else 0.125
            for idx, row in zone_df.iterrows():
                y_pos = 0.91 - idx * legend_step
                color = zone_colors[idx % len(zone_colors)]
                fig_zone.add_annotation(
                    x=0.65, y=y_pos, xref="paper", yref="paper",
                    text="●", showarrow=False, xanchor="left",
                    font=dict(size=19, color=color),
                )
                fig_zone.add_annotation(
                    x=0.705, y=y_pos, xref="paper", yref="paper",
                    text=(
                        f"<b>{escape(str(row['Display Zone']))}</b><br>"
                        f"₹{row['Display']:.2f} {unit} "
                        f"<span style='color:{color}'>({row['Pct']:.1f}%)</span>"
                    ),
                    showarrow=False,
                    xanchor="left",
                    align="left",
                    font=dict(size=14, color="#1f2937"),
                )

            net_zone_pnl = float(zone_df["Display"].sum())
            fig_zone.add_annotation(
                x=0.30,
                y=0.53,
                xref="paper",
                yref="paper",
                text=f"<b>₹{net_zone_pnl:.2f} {unit}</b>",
                showarrow=False,
                xanchor="center",
                yanchor="middle",
                align="center",
                font=dict(size=25, color="#17152f", family="Arial"),
            )
            fig_zone.add_annotation(
                x=0.30,
                y=0.43,
                xref="paper",
                yref="paper",
                text="Net P&L",
                showarrow=False,
                xanchor="center",
                yanchor="middle",
                align="center",
                font=dict(size=14, color="#746d91", family="Arial"),
            )
            fig_zone.update_layout(
                height=335,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(
                fig_zone,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )

    compact_spacer()
    if view_type == "Origin" and "COUNTRY" in df.columns:
        with st.container(border=True):
            st.markdown(
                "<div style='display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 0 8px 2px;'>"
                "<div style='font-size:15px;font-weight:500;color:#0f2744;'>Zone-wise Country P&L</div>"
                "<div style='display:flex;gap:14px;flex-wrap:wrap;font-size:10px;'>"
                "<span style='color:#1d4ed8;'>■ Current Year</span>"
                "<span style='color:#0f766e;'>■ Last Year</span>"
                "<span style='color:#6d28d9;'>■ YoY Comparison</span>"
                "</div></div>",
                unsafe_allow_html=True,
            )

            zone_country_pnl = (
                df.groupby(["zone", "COUNTRY"], dropna=False)["PNL"]
                .sum()
                .reset_index()
            )
            zone_country_pnl["P&L Display"] = zone_country_pnl["PNL"] / divisor
            current_matrix = zone_country_pnl.pivot(
                index="zone", columns="COUNTRY", values="P&L Display"
            ).fillna(0)
            current_matrix["Total"] = current_matrix.sum(axis=1)
            current_matrix = current_matrix.sort_values("Total", ascending=False)
            if (
                prev_df is not None
                and not prev_df.empty
                and {"zone", "COUNTRY", "PNL"}.issubset(prev_df.columns)
            ):
                prev_zone_country_pnl = (
                    prev_df.groupby(["zone", "COUNTRY"], dropna=False)["PNL"]
                    .sum()
                    .reset_index()
                )
                prev_zone_country_pnl["P&L Display"] = prev_zone_country_pnl["PNL"] / divisor
                previous_matrix = prev_zone_country_pnl.pivot(
                    index="zone", columns="COUNTRY", values="P&L Display"
                ).fillna(0)
                previous_matrix["Total"] = previous_matrix.sum(axis=1)
            else:
                previous_matrix = pd.DataFrame()

            zone_colors = {
                "NORTH ZONE": "#1565C0", "WEST ZONE": "#009688",
                "SOUTH ZONE": "#FB8C00", "EAST ZONE": "#7E57C2",
                "NORTH EAST ZONE": "#EC407A", "NEPAL ZONE": "#EF5350",
                "North Zone": "#1565C0", "West Zone": "#009688",
                "South Zone": "#FB8C00", "East Zone": "#7E57C2",
                "North East Zone": "#EC407A", "Nepal Zone": "#EF5350",
            }

            zone_name_map = {
                "NORTH ZONE": "North", "WEST ZONE": "West", "SOUTH ZONE": "South",
                "EAST ZONE": "East", "NORTH EAST ZONE": "NE", "NEPAL ZONE": "Nepal",
            }

            country_cols = sorted(
                set(col for col in current_matrix.columns if col != "Total")
                | set(col for col in previous_matrix.columns if col != "Total")
            )
            zone_order = list(current_matrix.index)
            for zone_key in previous_matrix.index:
                if zone_key not in zone_order:
                    zone_order.append(zone_key)

            current_matrix = current_matrix.reindex(index=zone_order, columns=country_cols + ["Total"], fill_value=0)
            previous_matrix = previous_matrix.reindex(index=zone_order, columns=country_cols + ["Total"], fill_value=0)

            current_grand_total = float(current_matrix[country_cols].to_numpy().sum()) if country_cols else 0.0
            previous_grand_total = float(previous_matrix[country_cols].to_numpy().sum()) if country_cols else 0.0

            def _safe_growth(current_value, previous_value):
                if previous_value:
                    return ((current_value - previous_value) / previous_value) * 100
                return 100.0 if current_value else 0.0

            def _growth_html(growth_value, suffix="%"):
                positive = growth_value >= 0
                color = "#16a34a" if positive else "#dc2626"
                arrow = "▲" if positive else "▼"
                return f'<span style="color:{color};font-weight:600;white-space:nowrap;">{arrow} {abs(growth_value):.2f}{suffix}</span>'

            header_groups = [f'<th class="country-group" colspan="3">{escape(str(country))}</th>' for country in country_cols]
            header_groups.append('<th class="country-group total-group" colspan="3">TOTAL</th>')
            sub_headers = ''.join(
                '<th class="cy-head">CY</th><th class="ly-head">LY</th><th class="yoy-head">YoY %</th>'
                for _ in range(len(country_cols) + 1)
            )

            body_rows = []
            for zone_key in zone_order:
                display_zone = zone_name_map.get(zone_key, str(zone_key).title())
                zone_color = zone_colors.get(zone_key, "#2563eb")
                revenue_cells, share_cells = [], []

                for country in country_cols:
                    cy = float(current_matrix.at[zone_key, country] or 0)
                    ly = float(previous_matrix.at[zone_key, country] or 0)
                    growth = _safe_growth(cy, ly)
                    cy_share = (cy / current_grand_total * 100) if current_grand_total else 0.0
                    ly_share = (ly / previous_grand_total * 100) if previous_grand_total else 0.0
                    share_change = cy_share - ly_share
                    revenue_cells.extend([
                        f'<td class="num cy-cell">{cy:.2f}</td>',
                        f'<td class="num ly-cell">{ly:.2f}</td>',
                        f'<td class="num yoy-cell">{_growth_html(growth)}</td>',
                    ])
                    share_cells.extend([
                        f'<td class="num cy-share">{cy_share:.2f}%</td>',
                        f'<td class="num ly-share">{ly_share:.2f}%</td>',
                        f'<td class="num yoy-cell">{_growth_html(share_change, " pp")}</td>',
                    ])

                zone_cy_total = float(current_matrix.loc[zone_key, country_cols].sum()) if country_cols else 0.0
                zone_ly_total = float(previous_matrix.loc[zone_key, country_cols].sum()) if country_cols else 0.0
                zone_growth = _safe_growth(zone_cy_total, zone_ly_total)
                zone_cy_share = (zone_cy_total / current_grand_total * 100) if current_grand_total else 0.0
                zone_ly_share = (zone_ly_total / previous_grand_total * 100) if previous_grand_total else 0.0
                zone_share_change = zone_cy_share - zone_ly_share
                revenue_cells.extend([
                    f'<td class="num total-cell cy-cell">{zone_cy_total:.2f}</td>',
                    f'<td class="num total-cell ly-cell">{zone_ly_total:.2f}</td>',
                    f'<td class="num total-cell yoy-cell">{_growth_html(zone_growth)}</td>',
                ])
                share_cells.extend([
                    f'<td class="num total-cell cy-share">{zone_cy_share:.2f}%</td>',
                    f'<td class="num total-cell ly-share">{zone_ly_share:.2f}%</td>',
                    f'<td class="num total-cell yoy-cell">{_growth_html(zone_share_change, " pp")}</td>',
                ])
                body_rows.append(
                    '<tr class="zone-revenue-row">'
                    f'<td class="zone-name" rowspan="2" style="border-left:4px solid {zone_color};">{escape(display_zone)}</td>'
                    '<td class="metric-name">P&L</td>' + ''.join(revenue_cells) + '</tr>'
                    '<tr class="zone-share-row"><td class="metric-name">% Share</td>' + ''.join(share_cells) + '</tr>'
                )

            grand_revenue_cells, grand_share_cells = [], []
            for country in country_cols:
                cy = float(current_matrix[country].sum())
                ly = float(previous_matrix[country].sum())
                growth = _safe_growth(cy, ly)
                cy_share = (cy / current_grand_total * 100) if current_grand_total else 0.0
                ly_share = (ly / previous_grand_total * 100) if previous_grand_total else 0.0
                share_change = cy_share - ly_share
                grand_revenue_cells.extend([
                    f'<td class="num cy-cell">{cy:.2f}</td>',
                    f'<td class="num ly-cell">{ly:.2f}</td>',
                    f'<td class="num yoy-cell">{_growth_html(growth)}</td>',
                ])
                grand_share_cells.extend([
                    f'<td class="num cy-share">{cy_share:.2f}%</td>',
                    f'<td class="num ly-share">{ly_share:.2f}%</td>',
                    f'<td class="num yoy-cell">{_growth_html(share_change, " pp")}</td>',
                ])

            grand_growth = _safe_growth(current_grand_total, previous_grand_total)
            grand_revenue_cells.extend([
                f'<td class="num total-cell cy-cell">{current_grand_total:.2f}</td>',
                f'<td class="num total-cell ly-cell">{previous_grand_total:.2f}</td>',
                f'<td class="num total-cell yoy-cell">{_growth_html(grand_growth)}</td>',
            ])
            grand_share_cells.extend([
                '<td class="num total-cell cy-share">100.00%</td>',
                '<td class="num total-cell ly-share">100.00%</td>',
                '<td class="num total-cell yoy-cell">—</td>',
            ])
            total_rows = (
                '<tr class="grand-total-row"><td class="zone-name" rowspan="2">TOTAL</td><td class="metric-name">P&L</td>'
                + ''.join(grand_revenue_cells) + '</tr>'
                '<tr class="grand-total-row"><td class="metric-name">% Share</td>'
                + ''.join(grand_share_cells) + '</tr>'
            )

            dynamic_font = "9px" if len(country_cols) >= 5 else "10px"
            matrix_html = f"""
            <style>
                .compact-zone-matrix-wrap {{width:100%;overflow:visible;border:1px solid #dbe4ef;border-radius:10px;background:#ffffff;}}
                .compact-zone-matrix {{width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;font-family:'Segoe UI',Arial,sans-serif;font-size:{dynamic_font};color:#243b53;}}
                .compact-zone-matrix th,.compact-zone-matrix td {{padding:5px 3px;border-right:1px solid #cbd5e1;border-bottom:1px solid #cbd5e1;text-align:center;line-height:1.15;overflow:hidden;text-overflow:ellipsis;}}
                /* Light separators around every country group (CY / LY / YoY). */
                .compact-zone-matrix .country-group {{border-left:1px solid #94a3b8!important;border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix thead tr:nth-child(2) th:nth-child(3n+1) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix thead tr:nth-child(2) th:nth-child(3n) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-revenue-row td:nth-child(3n+3) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-revenue-row td:nth-child(3n+2) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-share-row td:nth-child(3n+2) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-share-row td:nth-child(3n+1) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:first-of-type td:nth-child(3n+3) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:first-of-type td:nth-child(3n+2) {{border-right:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:last-of-type td:nth-child(3n+2) {{border-left:1px solid #94a3b8!important;}}
                .compact-zone-matrix .grand-total-row:last-of-type td:nth-child(3n+1) {{border-right:1px solid #94a3b8!important;}}
                /* Light horizontal border around each two-row zone block. */
                .compact-zone-matrix .zone-revenue-row td {{border-top:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-revenue-row .zone-name {{border-bottom:1px solid #94a3b8!important;}}
                .compact-zone-matrix .zone-share-row td {{border-bottom:1px solid #94a3b8!important;}}
                .compact-zone-matrix thead th {{font-weight:500;}}
                .compact-zone-matrix .zone-head {{width:7%;background:#eef4fb;text-align:left;padding-left:8px;}}
                .compact-zone-matrix .metric-head {{width:7%;background:#eef4fb;text-align:left;padding-left:7px;}}
                .compact-zone-matrix .country-group {{background:#eaf2ff;color:#0f2744;font-size:11px;border-top:3px solid #2563eb;}}
                .compact-zone-matrix .total-group {{background:#edf4ff;}}
                .compact-zone-matrix .cy-head {{background:#eff6ff;color:#1d4ed8;}}
                .compact-zone-matrix .ly-head {{background:#ecfdf8;color:#0f766e;}}
                .compact-zone-matrix .yoy-head {{background:#f7f2ff;color:#6d28d9;}}
                .compact-zone-matrix .zone-name {{text-align:left;padding-left:8px;font-size:11px;font-weight:500;background:#f8fbff;white-space:normal;}}
                .compact-zone-matrix .metric-name {{text-align:left;padding-left:7px;color:#475569;font-weight:400;background:#fbfdff;white-space:nowrap;}}
                .compact-zone-matrix .num {{white-space:nowrap;font-weight:400;}}
                .compact-zone-matrix .cy-cell,.compact-zone-matrix .cy-share {{background:#f8fbff;}}
                .compact-zone-matrix .ly-cell,.compact-zone-matrix .ly-share {{background:#f7fcfb;}}
                .compact-zone-matrix .yoy-cell {{background:#fbfdff;}}
                .compact-zone-matrix .total-cell {{font-weight:500;}}
                .compact-zone-matrix .zone-share-row td {{color:#64748b;}}
                .compact-zone-matrix .grand-total-row td {{background:#eaf2ff!important;font-weight:500;color:#0f2744;}}
                .compact-zone-matrix tr:last-child td {{border-bottom:0;}}
                .compact-zone-matrix th:last-child,.compact-zone-matrix td:last-child {{border-right:0;}}
                .zone-matrix-note {{display:flex;gap:18px;flex-wrap:wrap;margin:7px 2px 0;color:#64748b;font-size:10px;}}
                @media (max-width:1200px) {{.compact-zone-matrix {{font-size:8px;}}.compact-zone-matrix th,.compact-zone-matrix td {{padding:4px 2px;}}.compact-zone-matrix .country-group,.compact-zone-matrix .zone-name {{font-size:9px;}}}}
            </style>
            <div class="compact-zone-matrix-wrap">
                <table class="compact-zone-matrix">
                    <thead>
                        <tr><th class="zone-head" rowspan="2">Zone</th><th class="metric-head" rowspan="2">Metric</th>{''.join(header_groups)}</tr>
                        <tr>{sub_headers}</tr>
                    </thead>
                    <tbody>{''.join(body_rows)}{total_rows}</tbody>
                </table>
            </div>
            <div class="zone-matrix-note">
                <span>Values in ₹ {escape(str(unit))}</span>
                <span style="color:#16a34a;">▲ Positive movement</span>
                <span style="color:#dc2626;">▼ Negative movement</span>
                <span>YoY % = (CY − LY) ÷ LY × 100</span>
            </div>
            """
            if hasattr(st, "html"):
                st.html(matrix_html)
            else:
                st.markdown(matrix_html, unsafe_allow_html=True)

    elif view_type == "Origin":
        with st.container(border=True):
            st.info("Zone-wise Country P&L cannot be displayed because COUNTRY is missing from the P&L dataset.")

    compact_spacer()
    # Use the same GR-wise P&L, but attribute it to the selected view dimension.
    # Origin view uses consignor/customer; Destination view uses consignee/customer.
    if view_type == "Destination":
        customer_col = _find_column(
            df,
            ["Consignee", "consigneename", "customer", "customername"],
        )
    else:
        customer_col = _find_column(
            df,
            ["Consignor", "consignorname", "customer", "customername"],
        )

    route_col = _find_column(df, ["Route", "routename"])
    customer_layout_col, route_layout_col = st.columns(2, gap="medium")

    with customer_layout_col:
        with st.container(border=True):
            if customer_col:
                render_top_n_pnl_table(
                    df,
                    prev_df,
                    customer_col,
                    "Customers",
                    unit,
                    divisor,
                    "pnl_customer",
                    subtitle=(
                        "Customer basis: Consignor | Current FY P&L, share and YoY movement."
                        if view_type == "Origin"
                        else "Customer basis: Consignee | Current FY P&L, share and YoY movement."
                    ),
                )
            else:
                st.info("Customer column not found.")

    with route_layout_col:
        with st.container(border=True):
            if route_col:
                render_top_n_pnl_table(
                    df,
                    prev_df,
                    route_col,
                    "Routes",
                    unit,
                    divisor,
                    "pnl_route",
                    subtitle=(
                        "Origin → Destination | Current FY P&L, share and YoY movement."
                        if view_type == "Origin"
                        else "Destination → Origin | Current FY P&L, share and YoY movement."
                    ),
                )
            else:
                st.info("Route column not found.")

    compact_spacer()

    # Reusable summaries for the branch section and detail tabs.
    branch_summary = build_group_summary(df, prev_df, "branch")
    monthly = build_monthly_comparison(df, prev_df, divisor)

    current_month_count = max(int(df["FIN_MONTH"].dropna().nunique()), 1)
    previous_month_count = (
        max(int(prev_df["FIN_MONTH"].dropna().nunique()), 1)
        if prev_df is not None and not prev_df.empty and "FIN_MONTH" in prev_df.columns
        else current_month_count
    )

    all_branch_pnl = branch_summary[["branch", "PNL", "PY_PNL"]].copy()
    all_branch_pnl["branch"] = (
        all_branch_pnl["branch"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    )
    all_branch_pnl["PNL"] = pd.to_numeric(all_branch_pnl["PNL"], errors="coerce").fillna(0.0)
    all_branch_pnl["PY_PNL"] = pd.to_numeric(all_branch_pnl["PY_PNL"], errors="coerce").fillna(0.0)
    all_branch_pnl["Monthly_Avg_PNL"] = all_branch_pnl["PNL"] / current_month_count
    all_branch_pnl["LY_Monthly_Avg_PNL"] = all_branch_pnl["PY_PNL"] / previous_month_count

    branch_options = [
        "All", "Loss", "₹0–5 Lac", "₹5–10 Lac", "₹10–15 Lac",
        "₹15–25 Lac", "₹25–50 Lac", "₹50 Lac & Above",
    ]
    slab_ranges = {
        "All": (None, None), "Loss": (None, 0),
        "₹0–5 Lac": (0, 500_000), "₹5–10 Lac": (500_000, 1_000_000),
        "₹10–15 Lac": (1_000_000, 1_500_000), "₹15–25 Lac": (1_500_000, 2_500_000),
        "₹25–50 Lac": (2_500_000, 5_000_000), "₹50 Lac & Above": (5_000_000, None),
    }

    selected_branch_slab = st.session_state.get("pnl_branch_slab_value", "All")
    if selected_branch_slab not in slab_ranges:
        selected_branch_slab = "All"
        st.session_state["pnl_branch_slab_value"] = "All"

    with st.container(border=True):
        st.markdown(
            "<div style='font-size:16px;font-weight:400;color:#0f2744;margin:1px 0 7px 2px;'>"
            "Branches by Monthly Avg P&amp;L</div>",
            unsafe_allow_html=True,
        )

        slab_button_cols = st.columns(len(branch_options), gap="small")
        for slab_index, slab_label in enumerate(branch_options):
            with slab_button_cols[slab_index]:
                is_active = slab_label == selected_branch_slab
                if st.button(
                    slab_label,
                    key=f"pnl_branch_slab_btn_{slab_index}",
                    type="primary" if is_active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["pnl_branch_slab_value"] = slab_label
                    selected_branch_slab = slab_label
                    st.rerun()

        selected_branch_pnl = all_branch_pnl.copy()
        slab_low, slab_high = slab_ranges[selected_branch_slab]
        if selected_branch_slab == "Loss":
            selected_branch_pnl = selected_branch_pnl[selected_branch_pnl["Monthly_Avg_PNL"] < 0]
        else:
            if slab_low is not None:
                selected_branch_pnl = selected_branch_pnl[selected_branch_pnl["Monthly_Avg_PNL"] >= slab_low]
            if slab_high is not None:
                selected_branch_pnl = selected_branch_pnl[selected_branch_pnl["Monthly_Avg_PNL"] < slab_high]

        selected_branch_pnl = selected_branch_pnl.sort_values(
            "Monthly_Avg_PNL", ascending=False
        ).reset_index(drop=True)

        total_abs_branch_pnl = float(all_branch_pnl["Monthly_Avg_PNL"].abs().sum())
        selected_pnl_total = float(selected_branch_pnl["Monthly_Avg_PNL"].sum())
        selected_ly_total = float(selected_branch_pnl["LY_Monthly_Avg_PNL"].sum())
        selected_abs_share = (
            float(selected_branch_pnl["Monthly_Avg_PNL"].abs().sum()) / total_abs_branch_pnl * 100
            if total_abs_branch_pnl else 0.0
        )
        selected_growth = (
            ((selected_pnl_total - selected_ly_total) / abs(selected_ly_total)) * 100
            if selected_ly_total != 0 else None
        )
        if selected_growth is None:
            selected_growth_html = '<span style="color:#7c3aed;font-weight:700;">NEW</span>'
        else:
            selected_growth_color = "#16a34a" if selected_growth >= 0 else "#dc2626"
            selected_growth_arrow = "▲" if selected_growth >= 0 else "▼"
            selected_growth_html = (
                f'<span style="color:{selected_growth_color};font-weight:700;">'
                f'{selected_growth_arrow} {abs(selected_growth):.1f}%</span>'
            )

        st.markdown(
            f'<div style="color:#31557d;font-size:12px;font-weight:500;margin:7px 0 8px 1px;">'
            f'Showing {len(selected_branch_pnl):,} branches in {escape(selected_branch_slab)}. '
            f'CY Avg P&amp;L: <b>₹{selected_pnl_total / divisor:,.2f} {escape(unit)}</b> · '
            f'LY Avg P&amp;L: <b>₹{selected_ly_total / divisor:,.2f} {escape(unit)}</b> · '
            f'Share: <b>{selected_abs_share:.2f}%</b> · Growth: {selected_growth_html}. Scroll to view all.'
            f'</div>',
            unsafe_allow_html=True,
        )

        if selected_branch_pnl.empty:
            st.info(f"No branch falls in the {selected_branch_slab} monthly-average P&L slab.")
        else:
            max_abs_pnl = float(selected_branch_pnl["Monthly_Avg_PNL"].abs().max()) or 1.0
            branch_rows = []
            for index, branch_row in selected_branch_pnl.iterrows():
                branch_value = float(branch_row["Monthly_Avg_PNL"] or 0)
                previous_value = float(branch_row["LY_Monthly_Avg_PNL"] or 0)
                width_pct = min(abs(branch_value) / max_abs_pnl * 100, 100)
                fill_color = "#2563eb" if branch_value >= 0 else "#dc2626"
                amount_color = "#111827" if branch_value >= 0 else "#dc2626"
                rank = index + 1
                branch_name = escape(str(branch_row["branch"]))
                share_pct = abs(branch_value) / total_abs_branch_pnl * 100 if total_abs_branch_pnl else 0.0

                if previous_value == 0:
                    growth_html = '<span style="color:#7c3aed;font-weight:700;">NEW</span>'
                else:
                    growth_value = ((branch_value - previous_value) / abs(previous_value)) * 100
                    growth_color = "#16a34a" if growth_value >= 0 else "#dc2626"
                    growth_arrow = "▲" if growth_value >= 0 else "▼"
                    growth_html = (
                        f'<span style="color:{growth_color};font-weight:700;">'
                        f'{growth_arrow} {abs(growth_value):.1f}%</span>'
                    )

                branch_rows.append(
                    f'<div style="margin-bottom:7px;padding:8px 10px;border:1px solid #dbe4ef;border-radius:12px;background:#fbfdff;">'
                    f'<div style="display:grid;grid-template-columns:34px minmax(175px,280px) minmax(100px,1fr) 105px 105px 70px 82px;align-items:center;gap:10px;">'
                    f'<div style="text-align:center;font-size:13px;color:#334155;">{rank}</div>'
                    f'<div style="font-size:14px;color:#0f2744;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{branch_name}</div>'
                    f'<div style="height:7px;background:#e8eef5;border-radius:999px;overflow:hidden;box-shadow:inset 0 1px 2px rgba(15,23,42,.08);">'
                    f'<div style="width:{width_pct:.1f}%;height:7px;background:{fill_color};border-radius:999px;"></div></div>'
                    f'<div style="text-align:right;color:{amount_color};font-size:13px;font-weight:700;white-space:nowrap;">₹{branch_value / divisor:,.2f} {escape(unit)}</div>'
                    f'<div style="text-align:right;color:#64748b;font-size:12px;white-space:nowrap;">₹{previous_value / divisor:,.2f} {escape(unit)}</div>'
                    f'<div style="text-align:right;color:#31557d;font-size:12px;font-weight:600;white-space:nowrap;">{share_pct:.2f}%</div>'
                    f'<div style="text-align:right;font-size:12px;white-space:nowrap;">{growth_html}</div>'
                    f'</div></div>'
                )

            branch_header = (
                '<div style="display:grid;grid-template-columns:34px minmax(175px,280px) minmax(100px,1fr) 105px 105px 70px 82px;align-items:center;gap:10px;'
                'padding:0 10px 5px 10px;color:#64748b;font-size:10px;font-weight:700;">'
                '<div style="text-align:center;">#</div><div>Branch</div><div>P&L Scale</div>'
                '<div style="text-align:right;">CY Avg</div><div style="text-align:right;">LY Avg</div>'
                '<div style="text-align:right;">Share</div><div style="text-align:right;">Growth</div></div>'
            )
            branch_html = (
                branch_header
                + '<div style="max-height:430px;overflow-y:auto;padding-right:3px;">'
                + "".join(branch_rows)
                + "</div>"
            )
            if hasattr(st, "html"):
                st.html(branch_html)
            else:
                st.markdown(branch_html, unsafe_allow_html=True)

    # Detailed tabs
    tab1, tab2, tab3 = st.tabs(["Branch Summary", "Monthly Summary", "Detailed GR Records"])

    with tab1:
        display = branch_summary.sort_values("PNL", ascending=False).copy()

        for col in ["Business", "Expense", "PNL", "PY_BUSINESS", "PY_PNL"]:
            display[col] = display[col] / divisor

        display = display[
            [
                "branch",
                "Business",
                "Expense",
                "PNL",
                "Margin %",
                "GRs",
                "PY_BUSINESS",
                "PY_PNL",
                "LY Margin %",
                "Growth %",
            ]
        ]

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
            height=430,
            column_config={
                "Business": st.column_config.NumberColumn(
                    f"Business ({unit})",
                    format="%.2f",
                ),
                "Expense": st.column_config.NumberColumn(
                    f"Expense ({unit})",
                    format="%.2f",
                ),
                "PNL": st.column_config.NumberColumn(
                    f"P&L ({unit})",
                    format="%.2f",
                ),
                "Margin %": st.column_config.NumberColumn(
                    "Margin %",
                    format="%.2f%%",
                ),
                "GRs": st.column_config.NumberColumn(
                    "GRs",
                    format="%d",
                ),
                "PY_BUSINESS": st.column_config.NumberColumn(
                    f"LY Business ({unit})",
                    format="%.2f",
                ),
                "PY_PNL": st.column_config.NumberColumn(
                    f"LY P&L ({unit})",
                    format="%.2f",
                ),
                "LY Margin %": st.column_config.NumberColumn(
                    "LY Margin %",
                    format="%.2f%%",
                ),
                "Growth %": st.column_config.NumberColumn(
                    "Growth %",
                    format="%.1f%%",
                ),
            },
        )

    with tab2:
        monthly_display = monthly.copy()
        st.dataframe(
            monthly_display,
            width="stretch",
            hide_index=True,
            column_config={
                "Business": st.column_config.NumberColumn(f"Business ({unit})", format="%.2f"),
                "Expense": st.column_config.NumberColumn(f"Expense ({unit})", format="%.2f"),
                "PNL": st.column_config.NumberColumn(f"P&L ({unit})", format="%.2f"),
                "PY_PNL": st.column_config.NumberColumn(f"LY P&L ({unit})", format="%.2f"),
                "Margin %": st.column_config.NumberColumn("Margin %", format="%.2f%%"),
            },
        )

    with tab3:
        detail_columns = [
            col for col in [
                "COMPNAME", "zone", "circle", "branch", "grno", "grdt", "GRTYPE",
                "LOADTYPE", "Consignor", "Consignee", "Route", "REVENUE",
                "DELIVERYINCOME", "ADDITIONALFREIGHT", "OTHERINCOME", "RAW_EXPENSE",
                "EXPENSE", "PNL",
            ] if col in df.columns
        ]
        detail_df = df[detail_columns].copy()
        search_text = st.text_input("Search GR, branch, customer or route", key="pnl_detail_search")
        if search_text:
            mask = detail_df.astype(str).apply(
                lambda col: col.str.contains(search_text, case=False, na=False)
            ).any(axis=1)
            detail_df = detail_df[mask]

        st.dataframe(
            detail_df,
            width="stretch",
            hide_index=True,
            height=460,
            column_config={
                "REVENUE": st.column_config.NumberColumn("Business/Freight (₹)", format="₹%.0f"),
                "DELIVERYINCOME": st.column_config.NumberColumn("Delivery Income (₹)", format="₹%.0f"),
                "ADDITIONALFREIGHT": st.column_config.NumberColumn("Additional Freight (₹)", format="₹%.0f"),
                "OTHERINCOME": st.column_config.NumberColumn("Other Income (₹)", format="₹%.0f"),
                "RAW_EXPENSE": st.column_config.NumberColumn("Raw Expense (₹)", format="₹%.0f"),
                "EXPENSE": st.column_config.NumberColumn("Adjusted Expense (₹)", format="₹%.0f"),
                "PNL": st.column_config.NumberColumn("P&L (₹)", format="₹%.0f"),
                "grdt": st.column_config.DateColumn("GR Date", format="DD-MMM-YYYY"),
            },
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            detail_df.to_excel(writer, index=False, sheet_name="GR Detail")
            branch_summary.to_excel(writer, index=False, sheet_name="Branch Summary")
            monthly.to_excel(writer, index=False, sheet_name="Monthly Summary")
        excel_buffer.seek(0)

        st.download_button(
            "Download P&L analysis (Excel)",
            data=excel_buffer.getvalue(),
            file_name=f"pnl_analysis_{view_type.lower()}_{safe_fy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="pnl_excel_download",
            width="content",
        )


# Optional alias if your app menu expects a shorter function name.
def show_pnl() -> None:
    show_pnl_dashboard()
