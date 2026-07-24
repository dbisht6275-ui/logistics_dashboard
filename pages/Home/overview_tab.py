import io
import streamlit as st
import pandas as pd
import calendar
from html import escape
import plotly.graph_objects as go
import plotly.express as px
from services.data_loader import load_booking_data_pair, get_date_range
from services.branch_agency_mast import load_stationmast_data

# Compact layout constants
SPACER_HEIGHT = 4
REVENUE_CHART_HEIGHT = 440
ALIGNED_CHART_HEIGHT = 310
RANKING_CHART_HEIGHT = 330


def compact_spacer(height=SPACER_HEIGHT):
    """Render a consistent, minimal vertical gap between sections."""
    st.markdown(f"<div aria-hidden='true' style='height:{height}px'></div>", unsafe_allow_html=True)


# =========================
# Compact dashboard styling
# =========================

def _inject_overview_css():
    """
    Apply the same top-alignment logic used on the Outstanding page.

    Keeping CSS inside a function prevents Streamlit from rendering separate
    top-level markdown blocks before the page heading.
    """
    st.markdown(
        """
        <style>
            /* Start page content close to the top, same as Outstanding */
            .block-container {
                padding-top: 0.5rem;
                padding-bottom: 1rem;
            }

            /* Remove unnecessary top spacing from the first page elements */
            .block-container > div:first-child {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

            /* Reduce dataframe row height */
            [data-testid="stDataFrame"] table {
                font-size: 11px;
            }

            [data-testid="stDataFrame"] tbody tr {
                height: 24px !important;
            }

            [data-testid="stDataFrame"] {
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 7px 14px rgba(15,23,42,.10), inset 0 1px 0 rgba(255,255,255,.9);
            }

            /* Compact markdown headings inside cards */
            h5, h6 {
                margin-top: 0rem !important;
                margin-bottom: 0.35rem !important;
            }

            /* KPI-style period selector: Daily / Weekly / Monthly / Quarterly */
            div[data-testid="stSegmentedControl"] {
                display: flex !important;
                justify-content: flex-end !important;
                width: 100% !important;
            }

            div[data-testid="stSegmentedControl"] > div,
            div[data-testid="stSegmentedControl"] [role="radiogroup"] {
                display: grid !important;
                grid-template-columns: repeat(4, minmax(72px, 1fr)) !important;
                gap: 8px !important;
                width: min(100%, 390px) !important;
                padding: 0 !important;
                border: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
            }

            div[data-testid="stSegmentedControl"] label,
            div[data-testid="stSegmentedControl"] button {
                position: relative !important;
                overflow: hidden !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                min-width: 72px !important;
                min-height: 46px !important;
                height: 46px !important;
                padding: 8px 10px !important;
                margin: 0 !important;
                border: 1px solid #cbd5e1 !important;
                border-radius: 12px !important;
                background: linear-gradient(145deg, #ffffff 0%, #f8fafc 48%, #e7edf5 100%) !important;
                box-shadow:
                    0 5px 0 #c2ccd9,
                    0 8px 13px rgba(15,23,42,.16),
                    inset 1px 1px 0 rgba(255,255,255,.98),
                    inset -1px -1px 0 rgba(100,116,139,.16) !important;
                color: #334155 !important;
                font-size: 11px !important;
                font-weight: 800 !important;
                line-height: 1 !important;
                letter-spacing: .15px !important;
                white-space: nowrap !important;
                transform: translateY(-2px) !important;
                transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease !important;
            }

            div[data-testid="stSegmentedControl"] label::before,
            div[data-testid="stSegmentedControl"] button::before {
                content: "";
                position: absolute;
                left: 0;
                right: 0;
                top: 0;
                height: 4px;
                border-radius: 12px 12px 0 0;
                background: linear-gradient(90deg, #60a5fa, #2563eb);
                box-shadow: 0 2px 4px rgba(37,99,235,.22);
            }

            div[data-testid="stSegmentedControl"] label::after,
            div[data-testid="stSegmentedControl"] button::after {
                content: "";
                position: absolute;
                inset: 1px 1px auto 1px;
                height: 42%;
                border-radius: 11px 11px 50% 50%;
                background: linear-gradient(180deg, rgba(255,255,255,.82), rgba(255,255,255,0));
                pointer-events: none;
            }

            div[data-testid="stSegmentedControl"] label:hover,
            div[data-testid="stSegmentedControl"] button:hover {
                transform: translateY(-4px) !important;
                border-color: #93b7ef !important;
                box-shadow:
                    0 7px 0 #aebed2,
                    0 12px 17px rgba(15,23,42,.20),
                    inset 1px 1px 0 rgba(255,255,255,.98),
                    inset -1px -1px 0 rgba(100,116,139,.18) !important;
            }

            /* Selected period looks like an active blue KPI card */
            div[data-testid="stSegmentedControl"] label:has(input:checked),
            div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
                color: #ffffff !important;
                border-color: #1749a8 !important;
                background: linear-gradient(145deg, #4f8ff7 0%, #2563eb 55%, #1749a8 100%) !important;
                transform: translateY(1px) !important;
                box-shadow:
                    0 2px 0 #123d91,
                    0 5px 9px rgba(30,64,175,.28),
                    inset 2px 2px 5px rgba(15,23,42,.28),
                    inset -1px -1px 2px rgba(191,219,254,.35) !important;
            }

            div[data-testid="stSegmentedControl"] label:has(input:checked)::before,
            div[data-testid="stSegmentedControl"] button[aria-pressed="true"]::before {
                background: linear-gradient(90deg, #bfdbfe, #ffffff) !important;
                opacity: .9;
            }

            div[data-testid="stSegmentedControl"] label p,
            div[data-testid="stSegmentedControl"] button p,
            div[data-testid="stSegmentedControl"] label span,
            div[data-testid="stSegmentedControl"] button span {
                position: relative !important;
                z-index: 2 !important;
                margin: 0 !important;
                font-size: 11px !important;
                font-weight: 800 !important;
                line-height: 1 !important;
                color: inherit !important;
            }

            @media (max-width: 900px) {
                div[data-testid="stSegmentedControl"] > div,
                div[data-testid="stSegmentedControl"] [role="radiogroup"] {
                    grid-template-columns: repeat(2, minmax(78px, 1fr)) !important;
                    width: 100% !important;
                }
            }

            /* Strong 3D KPI cards */
            .kpi-3d-card {
                position: relative;
                overflow: hidden;
                min-height: 82px;
                padding: 10px 11px 11px 11px;
                border: 1px solid #cbd5e1;
                border-radius: 14px;
                background: linear-gradient(145deg, #ffffff 0%, #f8fafc 45%, #e7edf5 100%);
                box-shadow:
                    0 7px 0 #c2ccd9,
                    0 11px 17px rgba(15,23,42,.18),
                    inset 1px 1px 0 rgba(255,255,255,.98),
                    inset -1px -1px 0 rgba(100,116,139,.18);
                transform: translateY(-3px);
                transition: transform .15s ease, box-shadow .15s ease;
            }

            .kpi-3d-card:hover {
                transform: translateY(-5px);
                box-shadow:
                    0 9px 0 #b9c5d3,
                    0 15px 22px rgba(15,23,42,.22),
                    inset 1px 1px 0 rgba(255,255,255,.98),
                    inset -1px -1px 0 rgba(100,116,139,.20);
            }

            .kpi-3d-topline {
                position: absolute;
                left: 0;
                right: 0;
                top: 0;
                height: 4px;
                background: linear-gradient(90deg, var(--kpi-accent), color-mix(in srgb, var(--kpi-accent) 55%, white));
                box-shadow: 0 2px 4px color-mix(in srgb, var(--kpi-accent) 28%, transparent);
            }

            .kpi-3d-gloss {
                position: absolute;
                inset: 1px 1px auto 1px;
                height: 38%;
                border-radius: 13px 13px 50% 50%;
                background: linear-gradient(180deg, rgba(255,255,255,.78), rgba(255,255,255,0));
                pointer-events: none;
            }

            .kpi-3d-head {
                position: relative;
                z-index: 1;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 6px;
            }

            .kpi-3d-title {
                color: var(--kpi-accent);
                font-size: 10px;
                font-weight: 900;
                letter-spacing: .15px;
                text-shadow: 0 1px 0 rgba(255,255,255,.95);
            }

            .kpi-3d-icon {
                width: 27px;
                height: 27px;
                border-radius: 9px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 15px;
                background: linear-gradient(145deg, #ffffff, #dfe7f1);
                border: 1px solid color-mix(in srgb, var(--kpi-accent) 38%, #cbd5e1);
                box-shadow:
                    0 3px 0 color-mix(in srgb, var(--kpi-accent) 24%, #b8c2cf),
                    0 5px 8px rgba(15,23,42,.14),
                    inset 1px 1px 0 rgba(255,255,255,.95);
            }

            .kpi-3d-value {
                position: relative;
                z-index: 1;
                margin-top: 4px;
                color: #102a43;
                font-size: 18px;
                font-weight: 950;
                line-height: 1.08;
                text-shadow: 0 1px 0 #ffffff, 0 2px 3px rgba(15,23,42,.12);
            }

            .kpi-3d-footer {
                position: relative;
                z-index: 1;
                margin-top: 6px;
            }

            .kpi-3d-growth {
                display: inline-block;
                padding: 2px 7px;
                border: 1px solid;
                border-radius: 999px;
                font-size: 9px;
                font-weight: 900;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.9), 0 2px 3px rgba(15,23,42,.10);
            }

            /* Reduce dataframe/table vertical spacing */
            div[data-testid="stDataFrame"] {
                font-size: 12px;
            }

            /* 3D dashboard surface treatment */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border: 1px solid rgba(148, 163, 184, 0.45) !important;
                border-radius: 16px !important;
                background: linear-gradient(145deg, #ffffff 0%, #f8fafc 58%, #e8eef7 100%) !important;
                box-shadow:
                    0 12px 24px rgba(15, 23, 42, 0.10),
                    0 4px 8px rgba(15, 23, 42, 0.08),
                    inset 1px 1px 0 rgba(255,255,255,0.95),
                    inset -1px -1px 0 rgba(148,163,184,0.18) !important;
                transform: translateZ(0);
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                transform: translateY(-2px);
                box-shadow:
                    0 16px 30px rgba(15, 23, 42, 0.14),
                    0 6px 12px rgba(15, 23, 42, 0.10),
                    inset 1px 1px 0 rgba(255,255,255,0.95) !important;
                transition: all 0.18s ease;
            }

            /* Compact outlined filter controls */
            .filter-field-label {
                display: flex;
                align-items: center;
                gap: 5px;
                margin: 0 0 5px 3px;
                color: #243b53;
                font-size: 10px;
                font-weight: 900;
                letter-spacing: .12px;
                white-space: nowrap;
            }

            .filter-field-label span:first-child {
                display: inline-flex;
                width: 18px;
                height: 18px;
                align-items: center;
                justify-content: center;
                border-radius: 6px;
                color: #1d4ed8;
                background: linear-gradient(145deg, #eff6ff, #dbeafe);
                border: 1px solid #bfdbfe;
                box-shadow: inset 0 1px 0 #ffffff, 0 2px 4px rgba(37,99,235,.12);
                font-size: 10px;
            }

            div[data-testid="stSelectbox"] {
                padding: 3px;
                border: 1px solid #cbd9ea;
                border-radius: 12px;
                background: linear-gradient(145deg, #ffffff 0%, #f7faff 58%, #edf3fb 100%);
                box-shadow: 0 5px 10px rgba(15,42,67,.09), inset 0 1px 0 #ffffff;
                transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
            }

            div[data-testid="stSelectbox"]:hover {
                transform: translateY(-2px);
                border-color: #7aa7e8;
                box-shadow: 0 8px 15px rgba(37,99,235,.14), inset 0 1px 0 #ffffff;
            }

            div[data-testid="stSelectbox"]:focus-within {
                border-color: #2563eb;
                box-shadow: 0 0 0 3px rgba(37,99,235,.13), 0 8px 16px rgba(37,99,235,.14);
            }

            div[data-baseweb="select"] > div {
                min-height: 43px !important;
                border: 0 !important;
                border-radius: 9px !important;
                background: linear-gradient(180deg, #ffffff 0%, #f4f7fb 100%) !important;
                box-shadow: inset 0 1px 0 #ffffff, inset 0 -1px 0 rgba(148,163,184,.16) !important;
                padding-left: 5px !important;
            }

            div[data-baseweb="select"] span {
                color: #102a43 !important;
                font-weight: 800 !important;
                font-size: 11px !important;
            }

            div[data-baseweb="select"] svg {
                color: #1d4ed8 !important;
                width: 18px !important;
                height: 18px !important;
                padding: 2px;
                border-radius: 5px;
                background: #eaf2ff;
                filter: none;
            }

            div[data-baseweb="popover"] ul {
                border: 1px solid rgba(148,163,184,.45) !important;
                border-radius: 12px !important;
                background: linear-gradient(145deg, #ffffff, #eef2f7) !important;
                box-shadow: 0 16px 30px rgba(15,23,42,.20) !important;
                overflow: hidden !important;
            }

            div[data-baseweb="popover"] li:hover {
                background: linear-gradient(90deg, #dbeafe, #eff6ff) !important;
            }

            div[data-testid="stNumberInput"] input,
            div[data-testid="stFileUploader"] section {
                border-radius: 10px !important;
                background: linear-gradient(145deg, #ffffff, #eef2f7) !important;
                box-shadow: inset 2px 2px 4px rgba(15,23,42,.08),
                            inset -2px -2px 4px rgba(255,255,255,.95) !important;
            }

            .stButton > button, .stDownloadButton > button {
                border-radius: 10px !important;
                background: linear-gradient(145deg, #ffffff, #dfe7f2) !important;
                box-shadow: 0 5px 0 #cbd5e1, 0 8px 14px rgba(15,23,42,.14) !important;
                transform: translateY(-2px);
                transition: all .12s ease;
            }

            .stButton > button:active, .stDownloadButton > button:active {
                transform: translateY(2px);
                box-shadow: 0 1px 0 #cbd5e1, 0 3px 7px rgba(15,23,42,.12) !important;
            }



            /* Compact layout overrides */
            .block-container {max-width:100%;padding:.35rem .75rem .75rem!important;}
            div[data-testid="stVerticalBlock"] {gap:.35rem!important;}
            div[data-testid="stHorizontalBlock"] {gap:.5rem!important;}
            div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:11px!important;box-shadow:0 3px 10px rgba(15,42,67,.07)!important;}
            div[data-testid="stVerticalBlockBorderWrapper"] > div {padding:.55rem .65rem!important;}
            .executive-title {font-size:19px;}
            .filter-summary {margin:3px 0 6px;gap:4px;}
            .filter-field-label {
                margin: 0 0 4px 2px !important;
                min-height: 18px;
                line-height: 18px;
                overflow: hidden;
                text-overflow: ellipsis;
                position: relative;
                z-index: 2;
            }
            div[data-testid="stSelectbox"] {
                padding: 2px 3px 4px !important;
                margin-top: 0 !important;
                overflow: visible !important;
            }
            div[data-baseweb="select"] > div {min-height:34px!important;}
            div[data-testid="stHorizontalBlock"] > div {min-width:0!important;}
            .kpi-3d-card {min-height:70px;padding:8px 9px;transform:none;box-shadow:0 3px 8px rgba(15,23,42,.10)!important;}
            .kpi-3d-value {font-size:16px;margin-top:2px;}
            .kpi-3d-footer {margin-top:4px;}
            [data-testid="stDataFrame"] tbody tr {height:22px!important;}
            h5,h6 {margin:.1rem 0 .25rem!important;}

            /* Executive dashboard refinement */
            :root {
                --dash-navy: #102a43;
                --dash-blue: #2563eb;
                --dash-teal: #0f766e;
                --dash-muted: #64748b;
                --dash-border: #dbe4ef;
            }

            .executive-header {
                position: relative;
                overflow: hidden;
                margin: 0 0 10px 0;
                padding: 13px 16px 12px 16px;
                border: 1px solid #d8e3f0;
                border-radius: 15px;
                background: linear-gradient(105deg, #f8fbff 0%, #edf5ff 58%, #f6fbff 100%);
                box-shadow: 0 8px 18px rgba(15, 42, 67, .08), inset 0 1px 0 #ffffff;
            }
            .executive-header:before {
                content: "";
                position: absolute;
                left: 0; top: 0; bottom: 0;
                width: 5px;
                background: linear-gradient(180deg, #2563eb, #0f766e);
            }
            .executive-title {
                color: var(--dash-navy);
                font-size: 21px;
                font-weight: 850;
                letter-spacing: -.3px;
                margin: 0;
            }
            .executive-subtitle {
                color: var(--dash-muted);
                font-size: 11px;
                margin-top: 2px;
            }
            .filter-summary {
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin: 5px 0 10px 0;
            }
            .filter-chip {
                display: inline-flex;
                align-items: center;
                padding: 3px 8px;
                border: 1px solid #cbdcf3;
                border-radius: 999px;
                background: #f5f9ff;
                color: #31557d;
                font-size: 9px;
                font-weight: 750;
                box-shadow: inset 0 1px 0 #ffffff;
            }

            /* Cleaner card hierarchy: subtle depth, no oversized floating effect */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                border-radius: 14px !important;
                border-color: #dce5ef !important;
                background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%) !important;
                box-shadow: 0 7px 18px rgba(15,42,67,.075), inset 0 1px 0 #ffffff !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:hover {
                transform: translateY(-1px);
                box-shadow: 0 10px 22px rgba(15,42,67,.10), inset 0 1px 0 #ffffff !important;
            }

            /* Refined chart mode selector */
            div[data-testid="stSegmentedControl"] > div,
            div[data-testid="stSegmentedControl"] [role="radiogroup"] {
                background: #edf2f7 !important;
                border-color: #c9d5e3 !important;
                box-shadow: inset 1px 1px 2px rgba(15,23,42,.10), 0 3px 5px rgba(15,23,42,.10) !important;
            }
            div[data-testid="stSegmentedControl"] label,
            div[data-testid="stSegmentedControl"] button {
                border-radius: 6px !important;
                min-height: 24px !important;
                height: 24px !important;
                padding: 2px 7px !important;
                background: linear-gradient(180deg,#ffffff,#e9eef5) !important;
                box-shadow: 0 2px 0 #aebac8, inset 0 1px 0 #ffffff !important;
            }

            /* Compact filter strip */
            div[data-testid="stSelectbox"] {
                padding: 3px 4px 5px 4px;
                border-radius: 9px;
                box-shadow: none;
                background: #ffffff;
            }
            div[data-baseweb="select"] > div {
                min-height: 30px !important;
                background: #ffffff !important;
                box-shadow: inset 0 1px 2px rgba(15,23,42,.06) !important;
            }

            /* Softer dataframe presentation */
            [data-testid="stDataFrame"] {
                border: 1px solid #e2eaf3;
                box-shadow: none !important;
                background: #fbfdff;
            }

            /* Compact export button in the Revenue Overview header */
            div[data-testid="stDownloadButton"] > button {
                min-height: 34px !important;
                width: auto !important;
                padding: 5px 10px !important;
                border: 1px solid #2563eb !important;
                border-radius: 8px !important;
                color: #ffffff !important;
                font-size: 10px !important;
                font-weight: 850 !important;
                letter-spacing: .1px !important;
                background: linear-gradient(145deg, #3b82f6 0%, #2563eb 58%, #1d4ed8 100%) !important;
                box-shadow: 0 3px 0 #1e40af, 0 6px 10px rgba(37,99,235,.20) !important;
                transform: translateY(-1px);
                transition: transform .14s ease, box-shadow .14s ease !important;
            }

            div[data-testid="stDownloadButton"] > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 0 #1e40af, 0 8px 12px rgba(37,99,235,.24) !important;
            }


            /* ============================================================
               Responsive filter strip
               Use Streamlit's native widget labels so the label always owns
               its vertical space and cannot overlap the select control.
               ============================================================ */
            div[data-testid="stSelectbox"] {
                display: flex !important;
                flex-direction: column !important;
                gap: 7px !important;
                padding: 0 !important;
                margin: 0 0 8px 0 !important;
                border: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
                transform: none !important;
                overflow: visible !important;
            }

            div[data-testid="stSelectbox"] > label,
            div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
                display: block !important;
                position: static !important;
                min-height: 22px !important;
                margin: 0 0 2px 2px !important;
                padding: 0 !important;
                line-height: 22px !important;
                color: #243b53 !important;
                font-size: 10px !important;
                font-weight: 850 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                z-index: auto !important;
            }

            div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p,
            div[data-testid="stSelectbox"] > label p {
                margin: 0 !important;
                padding: 0 !important;
                line-height: 22px !important;
                font-size: inherit !important;
                font-weight: inherit !important;
                color: inherit !important;
            }

            div[data-testid="stSelectbox"] div[data-baseweb="select"] {
                width: 100% !important;
                margin: 0 !important;
            }

            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                min-height: 40px !important;
                height: 40px !important;
                padding: 0 8px !important;
                border: 1px solid #cbd9ea !important;
                border-radius: 10px !important;
                background: linear-gradient(180deg, #ffffff 0%, #f5f8fc 100%) !important;
                box-shadow: inset 0 1px 2px rgba(15,23,42,.06) !important;
            }

            /* Keep columns usable on common laptop widths. */
            div[data-testid="stHorizontalBlock"] {
                align-items: flex-start !important;
            }

            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                min-width: 0 !important;
            }

            @media (min-width: 1800px) {
                .block-container {
                    padding-left: 0.85rem !important;
                    padding-right: 0.85rem !important;
                }
                div[data-testid="stSelectbox"] > label,
                div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
                    font-size: 11px !important;
                }
                div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                    min-height: 42px !important;
                    height: 42px !important;
                }
            }

            @media (max-width: 1500px) {
                .block-container {
                    padding-left: 0.45rem !important;
                    padding-right: 0.45rem !important;
                }
                div[data-testid="stHorizontalBlock"] {
                    gap: 0.35rem !important;
                }
                div[data-testid="stSelectbox"] {
                    gap: 6px !important;
                    margin-bottom: 7px !important;
                }
                div[data-testid="stSelectbox"] > label,
                div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
                    min-height: 21px !important;
                    line-height: 21px !important;
                    font-size: 9px !important;
                    letter-spacing: 0 !important;
                }
                div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                    min-height: 38px !important;
                    height: 38px !important;
                    padding-left: 6px !important;
                    padding-right: 5px !important;
                }
                div[data-baseweb="select"] span {
                    font-size: 10px !important;
                }
            }

            @media (max-width: 1180px) {
                div[data-testid="stSelectbox"] > label,
                div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
                    font-size: 8.5px !important;
                }
                div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                    min-height: 36px !important;
                    height: 36px !important;
                    padding-left: 5px !important;
                    padding-right: 4px !important;
                }
                div[data-baseweb="select"] span {
                    font-size: 9px !important;
                }
            }

            div[data-testid="stDownloadButton"] > button:active {
                transform: translateY(1px) !important;
                box-shadow: 0 1px 0 #1e40af, 0 3px 6px rgba(37,99,235,.18) !important;
            }

            div[data-testid="stDownloadButton"] > button p {
                color: #ffffff !important;
                font-size: 10px !important;
                font-weight: 850 !important;
            }

        </style>
        """,
        unsafe_allow_html=True,
    )


def get_revenue_conversion(conversion_type):
    """Display-only conversion; business calculations remain in rupees."""
    return (100000, "Lac") if conversion_type == "Lac" else (10000000, "Cr")


def format_revenue(v, conversion_type):
    divisor, unit = get_revenue_conversion(conversion_type)
    return f"{v / divisor:.2f} {unit}"


def _hex_to_rgb(hex_color):
    """Convert #RRGGBB into an RGB tuple."""
    value = hex_color.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _shade(hex_color, factor=0.78):
    """Create a darker shade used for the visual side/depth of 3D bars."""
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgb({int(r * factor)},{int(g * factor)},{int(b * factor)})"


def add_3d_bar(fig, x, y, name, color, text=None, texttemplate=None,
               textposition="outside", textfont=None, orientation="v",
               customdata=None, hovertemplate=None, offsetgroup=None):
    """Add a layered Plotly bar that looks three-dimensional without changing the data."""
    side_color = _shade(color, 0.68)

    if orientation == "h":
        fig.add_trace(go.Bar(
            y=y, x=y if False else x, orientation="h", name=name,
            marker=dict(color=side_color, line=dict(color=side_color, width=0)),
            opacity=0.42, hoverinfo="skip", showlegend=False,
            offsetgroup=offsetgroup,
        ))
        fig.add_trace(go.Bar(
            y=y, x=x, orientation="h", name=name,
            marker=dict(
                color=color,
                line=dict(color=_shade(color, 0.55), width=1.2),
            ),
            text=text, texttemplate=texttemplate, textposition=textposition,
            textfont=textfont, customdata=customdata, hovertemplate=hovertemplate,
            offsetgroup=offsetgroup,
        ))
    else:
        fig.add_trace(go.Bar(
            x=x, y=y, name=name,
            marker=dict(color=side_color, line=dict(color=side_color, width=0)),
            opacity=0.35, hoverinfo="skip", showlegend=False,
            offsetgroup=offsetgroup,
        ))
        fig.add_trace(go.Bar(
            x=x, y=y, name=name,
            marker=dict(
                color=color,
                line=dict(color=_shade(color, 0.55), width=1.2),
            ),
            text=text, texttemplate=texttemplate, textposition=textposition,
            textfont=textfont, customdata=customdata, hovertemplate=hovertemplate,
            offsetgroup=offsetgroup,
        ))


def apply_3d_chart_layout(fig, height=250, margin=None):
    """Apply a raised panel, perspective-like axes and soft depth to Plotly visuals."""
    fig.update_layout(
        height=height,
        margin=margin or dict(l=8, r=8, t=34, b=8),
        plot_bgcolor="#f8fafc",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#0f172a"),
        hoverlabel=dict(bgcolor="#0f172a", font_color="white", bordercolor="#334155"),
    )
    fig.update_xaxes(showline=False, showgrid=False, zeroline=False)
    fig.update_yaxes(showline=False, showgrid=False, zeroline=False)
    return fig


# =========================
# Auto growth-vs-LY helpers
# =========================

def get_previous_fy(fy):
    """Given '2025-2026' returns '2024-2025'."""
    start_year, end_year = map(int, fy.split("-"))
    return f"{start_year - 1}-{end_year - 1}"


def calculate_kpis(data):
    """Compute the same set of KPIs used on the dashboard for any dataframe."""
    if data is None or data.empty:
        return {
            "revenue": 0, "ftl": 0, "ltl": 0, "total_gr": 0,
            "aweight": 0, "topay": 0, "paid": 0, "tbb": 0
        }

    return {
        "revenue": data["REVENUE"].sum(),
        "ftl": data[data["LOADTYPE"] == "FTL"]["REVENUE"].sum(),
        "ltl": data[data["LOADTYPE"] == "LTL"]["REVENUE"].sum(),
        "total_gr": data["grno"].count(),
        "aweight": data["aweight"].sum() / 1000,
        "topay": data[data["GRTYPE"] == "TOPAY"]["REVENUE"].sum(),
        "paid": data[data["GRTYPE"] == "PAID"]["REVENUE"].sum(),
        "tbb": data[data["GRTYPE"] == "TBB"]["REVENUE"].sum(),
    }


def pct_growth(current, previous):
    """% change of current vs previous, safe against zero/NaN previous."""
    if previous in (0, None) or pd.isna(previous):
        return 0.0
    return ((current - previous) / previous) * 100


def growth_label(value):
    arrow = "▲" if value >= 0 else "▼"
    return f"{arrow} {abs(value):.1f}%"


MONTH_ORDER = [
    "Apr", "May", "Jun", "Jul",
    "Aug", "Sep", "Oct", "Nov",
    "Dec", "Jan", "Feb", "Mar"
]

QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]

QUARTER_MAP = {
    1: "Q1", 2: "Q1", 3: "Q1",
    4: "Q2", 5: "Q2", 6: "Q2",
    7: "Q3", 8: "Q3", 9: "Q3",
    10: "Q4", 11: "Q4", 12: "Q4",
}


def build_yoy_trend(current_df, previous_df, trend_type, date_col, fy_start, prev_fy_start, month_map):
    """
    Build a Period-wise Current-FY vs LY revenue comparison dataframe for a chosen granularity.
    trend_type: 'Daily' | 'Weekly' | 'Monthly' | 'Quarterly'
    Returns columns: Period, Revenue Cr, Prev Revenue Cr, Growth %, Growth Label
    """
    cur = current_df.copy()
    prev = previous_df.copy() if previous_df is not None and not previous_df.empty else pd.DataFrame()

    cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty and date_col in prev.columns:
        prev[date_col] = pd.to_datetime(prev[date_col], errors="coerce")

    fy_start_ts = pd.to_datetime(fy_start) if fy_start else None
    prev_fy_start_ts = pd.to_datetime(prev_fy_start) if prev_fy_start else None

    if trend_type == "Daily":
        trend_df = cur.groupby(cur[date_col].dt.date)["REVENUE"].sum().reset_index()
        trend_df.columns = ["Period", "REVENUE"]
        trend_df["Key"] = (
            (pd.to_datetime(trend_df["Period"]) - fy_start_ts).dt.days
            if fy_start_ts is not None else range(len(trend_df))
        )

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.date)["REVENUE"].sum().reset_index()
            prev_trend.columns = ["Period", "PREV_REVENUE"]
            prev_trend["Key"] = (pd.to_datetime(prev_trend["Period"]) - prev_fy_start_ts).dt.days
        else:
            prev_trend = pd.DataFrame(columns=["Period", "PREV_REVENUE", "Key"])

    elif trend_type == "Weekly":
        trend_df = cur.groupby(cur[date_col].dt.to_period("W"))["REVENUE"].sum().reset_index()
        trend_df["Period"] = trend_df[date_col].astype(str)
        trend_df["Key"] = (
            ((trend_df[date_col].dt.start_time - fy_start_ts).dt.days // 7)
            if fy_start_ts is not None else range(len(trend_df))
        )
        trend_df = trend_df.drop(columns=[date_col])

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.to_period("W"))["REVENUE"].sum().reset_index()
            prev_trend["Key"] = (prev_trend[date_col].dt.start_time - prev_fy_start_ts).dt.days // 7
            prev_trend = prev_trend.rename(columns={"REVENUE": "PREV_REVENUE"}).drop(columns=[date_col])
        else:
            prev_trend = pd.DataFrame(columns=["PREV_REVENUE", "Key"])

    elif trend_type == "Quarterly":
        cur["Quarter"] = cur["FIN_MONTH"].map(QUARTER_MAP)
        trend_df = cur.groupby("Quarter")["REVENUE"].sum().reset_index()
        trend_df["Quarter"] = pd.Categorical(trend_df["Quarter"], categories=QUARTER_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Quarter")
        trend_df.columns = ["Period", "REVENUE"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Quarter"] = prev["FIN_MONTH"].map(QUARTER_MAP)
            prev_trend = prev.groupby("Quarter")["REVENUE"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_REVENUE"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_REVENUE"])

    else:  # Monthly
        cur["Month"] = cur["FIN_MONTH"].map(month_map)
        trend_df = cur.groupby("Month")["REVENUE"].sum().reset_index()
        trend_df["Month"] = pd.Categorical(trend_df["Month"], categories=MONTH_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Month")
        trend_df.columns = ["Period", "REVENUE"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Month"] = prev["FIN_MONTH"].map(month_map)
            prev_trend = prev.groupby("Month")["REVENUE"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_REVENUE"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_REVENUE"])

    trend_df["Revenue Cr"] = (trend_df["REVENUE"] / 10000000).round(2)

    if not prev_trend.empty:
        prev_trend["Prev Revenue Cr"] = (prev_trend["PREV_REVENUE"] / 10000000).round(2)
        trend_df = trend_df.merge(prev_trend[["Key", "Prev Revenue Cr"]], on="Key", how="left")
    else:
        trend_df["Prev Revenue Cr"] = None

    trend_df["Growth %"] = trend_df.apply(
        lambda r: pct_growth(r["Revenue Cr"], r["Prev Revenue Cr"]) if pd.notna(r["Prev Revenue Cr"]) else None,
        axis=1
    )
    trend_df["Growth Label"] = trend_df["Growth %"].apply(lambda x: growth_label(x) if pd.notna(x) else "N/A")

    return trend_df



def build_weight_yoy_trend(current_df, previous_df, trend_type, date_col, fy_start, prev_fy_start, month_map):
    """Build Current-FY vs LY weight trend in MT for Daily/Weekly/Monthly/Quarterly views."""
    cur = current_df.copy()
    prev = previous_df.copy() if previous_df is not None and not previous_df.empty else pd.DataFrame()

    cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty and date_col in prev.columns:
        prev[date_col] = pd.to_datetime(prev[date_col], errors="coerce")

    fy_start_ts = pd.to_datetime(fy_start) if fy_start else None
    prev_fy_start_ts = pd.to_datetime(prev_fy_start) if prev_fy_start else None

    if trend_type == "Daily":
        trend_df = cur.groupby(cur[date_col].dt.date)["aweight"].sum().reset_index()
        trend_df.columns = ["Period", "AWEIGHT"]
        trend_df["Key"] = (
            (pd.to_datetime(trend_df["Period"]) - fy_start_ts).dt.days
            if fy_start_ts is not None else range(len(trend_df))
        )

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.date)["aweight"].sum().reset_index()
            prev_trend.columns = ["Period", "PREV_AWEIGHT"]
            prev_trend["Key"] = (pd.to_datetime(prev_trend["Period"]) - prev_fy_start_ts).dt.days
        else:
            prev_trend = pd.DataFrame(columns=["Period", "PREV_AWEIGHT", "Key"])

    elif trend_type == "Weekly":
        trend_df = cur.groupby(cur[date_col].dt.to_period("W"))["aweight"].sum().reset_index()
        trend_df["Period"] = trend_df[date_col].astype(str)
        trend_df["Key"] = (
            ((trend_df[date_col].dt.start_time - fy_start_ts).dt.days // 7)
            if fy_start_ts is not None else range(len(trend_df))
        )
        trend_df = trend_df.rename(columns={"aweight": "AWEIGHT"}).drop(columns=[date_col])

        if not prev.empty and prev_fy_start_ts is not None:
            prev_trend = prev.groupby(prev[date_col].dt.to_period("W"))["aweight"].sum().reset_index()
            prev_trend["Key"] = (prev_trend[date_col].dt.start_time - prev_fy_start_ts).dt.days // 7
            prev_trend = prev_trend.rename(columns={"aweight": "PREV_AWEIGHT"}).drop(columns=[date_col])
        else:
            prev_trend = pd.DataFrame(columns=["PREV_AWEIGHT", "Key"])

    elif trend_type == "Quarterly":
        cur["Quarter"] = cur["FIN_MONTH"].map(QUARTER_MAP)
        trend_df = cur.groupby("Quarter")["aweight"].sum().reset_index()
        trend_df["Quarter"] = pd.Categorical(trend_df["Quarter"], categories=QUARTER_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Quarter")
        trend_df.columns = ["Period", "AWEIGHT"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Quarter"] = prev["FIN_MONTH"].map(QUARTER_MAP)
            prev_trend = prev.groupby("Quarter")["aweight"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_AWEIGHT"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_AWEIGHT"])

    else:  # Monthly
        cur["Month"] = cur["FIN_MONTH"].map(month_map)
        trend_df = cur.groupby("Month")["aweight"].sum().reset_index()
        trend_df["Month"] = pd.Categorical(trend_df["Month"], categories=MONTH_ORDER, ordered=True)
        trend_df = trend_df.sort_values("Month")
        trend_df.columns = ["Period", "AWEIGHT"]
        trend_df["Key"] = trend_df["Period"]

        if not prev.empty and "FIN_MONTH" in prev.columns:
            prev["Month"] = prev["FIN_MONTH"].map(month_map)
            prev_trend = prev.groupby("Month")["aweight"].sum().reset_index()
            prev_trend.columns = ["Key", "PREV_AWEIGHT"]
        else:
            prev_trend = pd.DataFrame(columns=["Key", "PREV_AWEIGHT"])

    trend_df["Weight MT"] = (trend_df["AWEIGHT"] / 1000).round(0)

    if not prev_trend.empty:
        prev_trend["Prev Weight MT"] = (prev_trend["PREV_AWEIGHT"] / 1000).round(0)
        trend_df = trend_df.merge(prev_trend[["Key", "Prev Weight MT"]], on="Key", how="left")
    else:
        trend_df["Prev Weight MT"] = None

    trend_df["Growth %"] = trend_df.apply(
        lambda r: pct_growth(r["Weight MT"], r["Prev Weight MT"])
        if pd.notna(r["Prev Weight MT"]) else None,
        axis=1,
    )
    trend_df["Growth Label"] = trend_df["Growth %"].apply(
        lambda x: growth_label(x) if pd.notna(x) else "N/A"
    )

    return trend_df

def add_revenue_forecast(yoy_df, trend_type, selected_quarter="All", selected_month="All"):
    """
    Add forecast revenue only for the current ongoing financial month.

    Logic:
    - Forecast is shown only in Monthly view.
    - Forecast is shown only for the current calendar month, e.g. July.
    - Future months like Aug-Mar are removed from the chart.
    - Formula: current month actual revenue till today / days passed * total days in month.
    """
    from datetime import datetime

    result = yoy_df.copy()

    if result.empty or "Revenue Cr" not in result.columns:
        result["Forecast Revenue Cr"] = None
        return result

    result["Revenue Cr"] = pd.to_numeric(result["Revenue Cr"], errors="coerce")
    if "Prev Revenue Cr" in result.columns:
        result["Prev Revenue Cr"] = pd.to_numeric(result["Prev Revenue Cr"], errors="coerce")

    # Default: no forecast bar anywhere
    result["Forecast Revenue Cr"] = None

    # Forecast only monthly chart. No forecast for Daily/Weekly/Quarterly.
    if trend_type != "Monthly":
        return result

    today = datetime.today()

    # Convert calendar month into your FY month number: Apr=1, May=2 ... Mar=12
    current_fin_month = ((today.month - 4) % 12) + 1
    current_month_name = MONTH_ORDER[current_fin_month - 1]

    month_to_quarter = {MONTH_ORDER[i]: QUARTER_MAP[i + 1] for i in range(len(MONTH_ORDER))}
    current_quarter = month_to_quarter.get(current_month_name)

    # Remove future months from Monthly chart when Month filter is All.
    # Example in July: show Apr, May, Jun, Jul only. Hide Aug-Mar completely.
    if selected_month == "All":
        if selected_quarter == "All":
            allowed_months = MONTH_ORDER[:current_fin_month]
        elif selected_quarter == current_quarter:
            allowed_months = [
                m for m in MONTH_ORDER
                if month_to_quarter.get(m) == selected_quarter
                and MONTH_ORDER.index(m) <= MONTH_ORDER.index(current_month_name)
            ]
        else:
            allowed_months = [m for m in MONTH_ORDER if month_to_quarter.get(m) == selected_quarter]

        result = result[result["Period"].astype(str).isin(allowed_months)].copy()

    # Respect filters: if user selected a different month/quarter, do not show forecast.
    if selected_month != "All" and selected_month != current_month_name:
        return result

    if selected_quarter != "All" and selected_quarter != current_quarter:
        return result

    # Find current month actual revenue till today
    current_rows = result["Period"].astype(str).eq(current_month_name)
    if not current_rows.any():
        return result

    current_value = result.loc[current_rows, "Revenue Cr"].iloc[0]

    if pd.isna(current_value) or current_value <= 0:
        return result

    days_elapsed = max(today.day, 1)
    total_days = calendar.monthrange(today.year, today.month)[1]

    forecast_value = round((current_value / days_elapsed) * total_days, 2)

    # Forecast bar only for current ongoing month
    result.loc[current_rows, "Forecast Revenue Cr"] = forecast_value

    return result


def create_card(title, value, color, icon, growth_value=0.0):
    """Render a compact KPI card without Markdown parsing the HTML as code."""
    positive = growth_value >= 0
    growth_color = "#15803d" if positive else "#dc2626"
    growth_bg = "#ecfdf3" if positive else "#fff1f2"
    growth_border = "#86efac" if positive else "#fda4af"
    growth_text = growth_label(growth_value)

    # Keep the complete HTML on one logical line. Blank lines or indented lines
    # inside st.markdown can be interpreted by Markdown as a fenced code block.
    html = (
        f'<div class="kpi-3d-card" style="--kpi-accent:{color};">'
        f'<div class="kpi-3d-gloss"></div>'
        f'<div class="kpi-3d-topline"></div>'
        f'<div class="kpi-3d-head">'
        f'<div class="kpi-3d-title">{title}</div>'
        f'<div class="kpi-3d-icon">{icon}</div>'
        f'</div>'
        f'<div class="kpi-3d-value">{value}</div>'
        f'<div class="kpi-3d-footer">'
        f'<span class="kpi-3d-growth" '
        f'style="background:{growth_bg};border-color:{growth_border};color:{growth_color};">'
        f'{growth_text} vs LY'
        f'</span>'
        f'</div>'
        f'</div>'
    )

    # st.html bypasses Markdown parsing. The fallback supports older Streamlit versions.
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)

def create_target_card(title, actual, target, unit="", decimals=2, icon="🎯"):
    """Render a compact Target vs Actual card.

    A target of zero means that the target has not yet been configured. Targets
    entered through the dashboard are stored only in the current Streamlit
    session and can later be replaced with database/config values.
    """
    actual = float(actual or 0)
    target = float(target or 0)

    if target > 0:
        achievement = (actual / target) * 100
        gap = actual - target
        progress_width = min(max(achievement, 0), 100)
        status_color = "#16a34a" if achievement >= 100 else "#f59e0b" if achievement >= 80 else "#dc2626"
        gap_label = f"{gap:+,.{decimals}f}{unit} gap"
        target_label = f"Target {target:,.{decimals}f}{unit}"
        achievement_label = f"{achievement:,.1f}% achieved"
    else:
        progress_width = 0
        status_color = "#94a3b8"
        gap_label = "Enter target to calculate gap"
        target_label = "Target not set"
        achievement_label = "Waiting for target"

    html = f"""
    <div style="background:linear-gradient(145deg,#ffffff 0%,#f8fafc 60%,#e5edf7 100%);border:1px solid #d7e0eb;border-radius:15px;
                padding:11px 12px;box-shadow:0 8px 0 #d6deea,0 13px 22px rgba(15,23,42,.14),inset 1px 1px 0 rgba(255,255,255,.95);min-height:114px;transform:translateY(-3px);">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <div style="font-size:11px;font-weight:800;color:#334155;">{title}</div>
            <div style="font-size:17px;">{icon}</div>
        </div>
        <div style="font-size:18px;font-weight:900;color:#0f172a;line-height:1.1;">
            {actual:,.{decimals}f}{unit}
        </div>
        <div style="display:flex;justify-content:space-between;gap:6px;margin-top:4px;
                    font-size:10px;color:#64748b;">
            <span>{target_label}</span>
            <span style="font-weight:800;color:{status_color};">{achievement_label}</span>
        </div>
        <div style="height:7px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin-top:7px;">
            <div style="height:7px;width:{progress_width:.1f}%;background:{status_color};border-radius:999px;"></div>
        </div>
        <div style="font-size:10px;font-weight:700;color:{status_color};margin-top:5px;">{gap_label}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def mini_rank_card(rank, name, value, max_value, color):
    """Compact ranked branch row with medal treatment and contribution bar."""
    pct = min((value / max_value * 100), 100) if max_value else 0
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

    html = f"""
    <div style="margin-bottom:7px;padding:5px 6px;border:1px solid #e5ebf2;border-radius:9px;background:#fbfdff;">
        <div style="display:flex;align-items:center;gap:7px;">
            <div style="width:22px;text-align:center;font-size:12px;font-weight:850;color:#486581;">{medal}</div>
            <div style="font-size:10px;font-weight:800;color:#243b53;min-width:102px;max-width:102px;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
            <div style="flex:1;height:8px;background:#e8eef5;border-radius:999px;overflow:hidden;
                        box-shadow:inset 0 1px 2px rgba(15,23,42,.12);">
                <div style="width:{pct}%;height:8px;background:{color};border-radius:999px;"></div>
            </div>
            <div style="font-size:10px;font-weight:900;color:#102a43;min-width:53px;text-align:right;">₹{value:.2f}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)



def _find_normalized_column(data, target_name):
    """Find a dataframe column while ignoring spaces, underscores and case."""
    if data is None or data.empty:
        return None

    target = str(target_name).replace("_", "").replace(" ", "").casefold()
    for column in data.columns:
        normalized = str(column).replace("_", "").replace(" ", "").casefold()
        if normalized == target:
            return column
    return None


def _build_sla_metrics(current_df, previous_df):
    """Build SLA operational metrics from the SLAStatus column."""
    statuses = ["Before EDD", "On EDD", "After EDD", "In Transit", "Overdue"]

    def status_counts(data):
        column = _find_normalized_column(data, "slastatus")
        if column is None:
            return None, {status: 0 for status in statuses}

        cleaned = (
            data[column]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.casefold()
        )
        counts = {
            status: int(cleaned.eq(status.casefold()).sum())
            for status in statuses
        }
        return column, counts

    current_col, current = status_counts(current_df)
    previous_col, previous = status_counts(previous_df)

    current_completed = (
        current["Before EDD"] + current["On EDD"] +
        current["After EDD"] + current["Overdue"]
    )
    previous_completed = (
        previous["Before EDD"] + previous["On EDD"] +
        previous["After EDD"] + previous["Overdue"]
    )

    current_on_time = (
        (current["Before EDD"] + current["On EDD"]) / current_completed * 100
        if current_completed else 0.0
    )
    previous_on_time = (
        (previous["Before EDD"] + previous["On EDD"]) / previous_completed * 100
        if previous_completed else 0.0
    )

    metrics = [
        {
            "label": "On-Time Delivery",
            "icon": "🚚",
            "current": current_on_time,
            "previous": previous_on_time,
            "is_percent": True,
            "accent": "#2563eb",
            "icon_bg": "#dbeafe",
        },
        {
            "label": "Before EDD",
            "icon": "⏱️",
            "current": current["Before EDD"],
            "previous": previous["Before EDD"],
            "is_percent": False,
            "accent": "#16a34a",
            "icon_bg": "#dcfce7",
        },
        {
            "label": "On EDD",
            "icon": "✅",
            "current": current["On EDD"],
            "previous": previous["On EDD"],
            "is_percent": False,
            "accent": "#0f766e",
            "icon_bg": "#ccfbf1",
        },
        {
            "label": "After EDD",
            "icon": "📅",
            "current": current["After EDD"],
            "previous": previous["After EDD"],
            "is_percent": False,
            "accent": "#f59e0b",
            "icon_bg": "#fef3c7",
        },
        {
            "label": "In Transit",
            "icon": "📦",
            "current": current["In Transit"],
            "previous": previous["In Transit"],
            "is_percent": False,
            "accent": "#7c3aed",
            "icon_bg": "#ede9fe",
        },
        {
            "label": "Overdue",
            "icon": "⚠️",
            "current": current["Overdue"],
            "previous": previous["Overdue"],
            "is_percent": False,
            "accent": "#dc2626",
            "icon_bg": "#fee2e2",
        },
    ]

    return current_col, previous_col, metrics


def _render_operational_highlights(current_df, previous_df):
    """Render a compact SLAStatus panel that fits beside branch rankings."""
    current_col, previous_col, metrics = _build_sla_metrics(current_df, previous_df)

    with st.container(border=True):
        st.markdown(
            "<div style='font-size:14px;font-weight:950;color:#0f2744;margin:1px 0 7px 2px;'>"
            "Operational Highlights</div>",
            unsafe_allow_html=True,
        )

        if current_col is None:
            st.info("SLAStatus column is missing.")
            return

        rows = []
        for metric in metrics:
            current = float(metric["current"] or 0)
            previous = float(metric["previous"] or 0)

            if metric["is_percent"]:
                change = current - previous
                current_text = f"{current:.2f}%"
                previous_text = f"{previous:.2f}%"
                change_text = f"{abs(change):.2f} pp"
            else:
                change = ((current - previous) / previous * 100) if previous else 0.0
                current_text = f"{int(current):,}"
                previous_text = f"{int(previous):,}"
                change_text = f"{abs(change):.2f}%" if previous else "N/A"

            lower_is_better = metric["label"] in {"After EDD", "In Transit", "Overdue"}
            is_good = change <= 0 if lower_is_better else change >= 0
            arrow = "▲" if change >= 0 else "▼"
            change_color = "#16a34a" if is_good else "#dc2626"

            rows.append(
                f'<div style="display:grid;grid-template-columns:30px minmax(88px,1fr) minmax(64px,.72fr) minmax(62px,.65fr);'
                f'align-items:center;gap:6px;padding:7px 2px;border-bottom:1px solid #edf2f7;">'
                f'<div style="width:27px;height:27px;border-radius:50%;display:flex;align-items:center;'
                f'justify-content:center;background:{metric["icon_bg"]};font-size:13px;'
                f'border:1px solid {metric["accent"]}33;">{metric["icon"]}</div>'
                f'<div style="font-size:10px;font-weight:850;color:#243b53;line-height:1.15;">{metric["label"]}</div>'
                f'<div style="line-height:1.1;">'
                f'<div style="font-size:12px;font-weight:950;color:#102a43;">{current_text}</div>'
                f'<div style="font-size:8px;color:#64748b;">LY {previous_text}</div></div>'
                f'<div style="font-size:9px;font-weight:900;color:{change_color};text-align:right;white-space:nowrap;">'
                f'{arrow} {change_text}</div></div>'
            )

        note = "" if previous_col is not None else (
            "<div style='font-size:8px;color:#94a3b8;margin-top:5px;'>LY SLAStatus unavailable.</div>"
        )
        st.markdown("<div>" + "".join(rows) + note + "</div>", unsafe_allow_html=True)

def show_overview():
    """Compact overview dashboard page."""

    _inject_overview_css()

    # Revenue Overview header card with the CSV export button inside it.
    # The placeholder is filled after all filters have been applied.
    with st.container(border=True):
        header_left, header_right = st.columns([7, 1], gap="small", vertical_alignment="center")

        with header_left:
            st.markdown(
                """
                <div style="padding:2px 0 3px 4px;">
                    <div class="executive-title">Revenue Overview</div>
                    <div class="executive-subtitle">Executive view of revenue, shipments, load mix, geography and branch performance</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with header_right:
            export_placeholder = st.empty()

    # Responsive single-row filter strip. Native labels reserve their own
    # vertical space, preventing label/select overlap on laptop screens.
    compact_spacer(4)
    filter_cols = st.columns(10, gap="small")

    with filter_cols[0]:
        view_type = st.selectbox(
            "⇄ View Type",
            ["Origin", "Destination"],
            key="overview_view_type",
        )

    with filter_cols[1]:
        fy = st.selectbox(
            "◷ Financial Year",
            ["Select FY", "2026-2027", "2025-2026", "2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"],
            key="overview_fy",
        )

    if fy == "Select FY":
        st.info("Please select financial year")
        return

    start_date, end_date = get_date_range(fy)
    prev_fy = get_previous_fy(fy)
    prev_start, prev_end = get_date_range(prev_fy)

    with st.spinner("Loading data..."):
        df, prev_df = load_booking_data_pair(start_date, end_date, prev_start, prev_end, view_type.lower())

    station_df = load_stationmast_data(start_date, end_date)
    if "FIN_MONTH" not in station_df.columns:
        def get_fin_month(date_str):
            try:
                date = pd.to_datetime(date_str)
                return ((date.month - 4) % 12) + 1
            except Exception:
                return None
        if "activedate" in station_df.columns:
            station_df["FIN_MONTH"] = station_df["activedate"].apply(get_fin_month)
        elif "closedate" in station_df.columns:
            station_df["FIN_MONTH"] = station_df["closedate"].apply(get_fin_month)
        else:
            station_df["FIN_MONTH"] = None

    if df.empty:
        st.warning("No data found")
        return

    # Company is supplied by the booking query as COMPNAME/compname.
    company_col = next(
        (col for col in df.columns if str(col).strip().casefold() == "compname"),
        None,
    )
    if company_col is None:
        st.error("Company filter cannot be displayed because the compname column is missing from the booking data.")
        return

    # Standardise the column name so all filters and visuals use one stable field.
    if company_col != "compname":
        df = df.rename(columns={company_col: "compname"})
    df["compname"] = df["compname"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")

    if prev_df is not None and not prev_df.empty:
        prev_company_col = next(
            (col for col in prev_df.columns if str(col).strip().casefold() == "compname"),
            None,
        )
        if prev_company_col is not None and prev_company_col != "compname":
            prev_df = prev_df.rename(columns={prev_company_col: "compname"})
        if "compname" in prev_df.columns:
            prev_df["compname"] = (
                prev_df["compname"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
            )

    month_map = {1:"Apr",2:"May",3:"Jun",4:"Jul",5:"Aug",6:"Sep",7:"Oct",8:"Nov",9:"Dec",10:"Jan",11:"Feb",12:"Mar"}
    df["Month"] = df["FIN_MONTH"].map(month_map)
    df["Quarter"] = df["FIN_MONTH"].map(QUARTER_MAP)
    if not prev_df.empty:
        prev_df["Month"] = prev_df["FIN_MONTH"].map(month_map)
        prev_df["Quarter"] = prev_df["FIN_MONTH"].map(QUARTER_MAP)

    data_scope = st.session_state.get("data_scope", {})
    locked_zone = data_scope.get("zone")
    locked_circle = data_scope.get("circle")
    locked_branch = data_scope.get("branch")
    if locked_branch:
        branch_row = df[df["branch"] == locked_branch]
        if not branch_row.empty:
            locked_circle = branch_row["circle"].iloc[0]
            locked_zone = branch_row["zone"].iloc[0]
    elif locked_circle:
        circle_row = df[df["circle"] == locked_circle]
        if not circle_row.empty:
            locked_zone = circle_row["zone"].iloc[0]

    with filter_cols[2]:
        company_options = sorted(df["compname"].dropna().unique().tolist())
        company = st.selectbox(
            "▥ Company",
            ["All"] + company_options,
            key="overview_company",
        )
    if company != "All":
        df = df[df["compname"] == company]

    with filter_cols[3]:
        if locked_zone:
            zone = locked_zone
            st.selectbox("◉ Zone", [zone], disabled=True, key="overview_zone_locked")
        else:
            zone = st.selectbox("◉ Zone", ["All"] + sorted(df["zone"].dropna().unique().tolist()), key="overview_zone")
    if zone != "All":
        df = df[df["zone"] == zone]

    with filter_cols[4]:
        if locked_circle:
            circle = locked_circle
            st.selectbox("◎ Circle", [circle], disabled=True, key="overview_circle_locked")
        else:
            circle = st.selectbox("◎ Circle", ["All"] + sorted(df["circle"].dropna().unique().tolist()), key="overview_circle")
    if circle != "All":
        df = df[df["circle"] == circle]

    with filter_cols[5]:
        if locked_branch:
            branch = locked_branch
            st.selectbox("⌂ Branch", [branch], disabled=True, key="overview_branch_locked")
        else:
            branch = st.selectbox("⌂ Branch", ["All"] + sorted(df["branch"].dropna().unique().tolist()), key="overview_branch")
    if branch != "All":
        df = df[df["branch"] == branch]

    with filter_cols[6]:
        available_quarters = [q for q in QUARTER_ORDER if q in df["Quarter"].dropna().unique().tolist()]
        quarter = st.selectbox("▦ Quarter", ["All"] + available_quarters, key="overview_quarter")
    if quarter != "All":
        df = df[df["Quarter"] == quarter]

    with filter_cols[7]:
        available_months = [m for m in MONTH_ORDER if m in df["Month"].dropna().unique().tolist()]
        month = st.selectbox("▣ Month", ["All"] + available_months, key="overview_month")
    if month != "All":
        df = df[df["Month"] == month]

    with filter_cols[8]:
        loadtype = st.selectbox("▤ Load Type", ["All"] + sorted(df["LOADTYPE"].dropna().unique().tolist()), key="overview_loadtype")
    if loadtype != "All":
        df = df[df["LOADTYPE"] == loadtype]

    with filter_cols[9]:
        conversion_type = st.selectbox(
            "₹ Conversion",
            ["Crore", "Lac"],
            key="overview_conversion_type",
        )
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)

    # Separate filters from the summary chips/KPIs on every screen size.
    compact_spacer(6)

    if df.empty:
        st.warning("No data found for selected filters")
        return

    # Export exactly the rows currently visible under the selected filters.
    export_df = df.copy()
    export_csv = export_df.to_csv(index=False).encode("utf-8-sig")
    safe_view = str(view_type).strip().lower().replace(" ", "_")
    safe_fy = str(fy).strip().replace("/", "-").replace(" ", "_")
    export_placeholder.download_button(
        label="⬇ Export CSV",
        data=export_csv,
        file_name=f"revenue_overview_{safe_view}_{safe_fy}.csv",
        mime="text/csv",
        key="overview_export_csv",
        help="Download the revenue overview data after applying the selected filters.",
        width="content",
    )

    active_filter_items = [
        ("FY", fy), ("View", view_type), ("Company", company), ("Zone", zone), ("Circle", circle),
        ("Branch", branch), ("Quarter", quarter), ("Month", month), ("Load", loadtype), ("Unit", conversion_type),
    ]
    active_filter_html = "".join(
        f'<span class="filter-chip">{label}: {value}</span>'
        for label, value in active_filter_items
        if value not in (None, "", "All")
    )
    if active_filter_html:
        st.markdown(f'<div class="filter-summary">{active_filter_html}</div>', unsafe_allow_html=True)

    # =========================
    # Apply the same company/zone/circle/branch/quarter/month/loadtype filters to the LY data
    # =========================
    if not prev_df.empty:
        if company != "All" and "compname" in prev_df.columns:
            prev_df = prev_df[prev_df["compname"] == company]
        if zone != "All":
            prev_df = prev_df[prev_df["zone"] == zone]
        if circle != "All":
            prev_df = prev_df[prev_df["circle"] == circle]
        if branch != "All":
            prev_df = prev_df[prev_df["branch"] == branch]
        if quarter != "All":
            prev_df = prev_df[prev_df["Quarter"] == quarter]
        if month != "All":
            prev_df = prev_df[prev_df["Month"] == month]
        if loadtype != "All":
            prev_df = prev_df[prev_df["LOADTYPE"] == loadtype]

    prev_kpis = calculate_kpis(prev_df)

    # KPI calculations after all selected filters are applied
    current_kpis = calculate_kpis(df)

    revenue = current_kpis["revenue"]
    ftl = current_kpis["ftl"]
    ltl = current_kpis["ltl"]
    total_gr = current_kpis["total_gr"]
    aweight = round(current_kpis["aweight"], 1)
    topay = current_kpis["topay"]
    paid = current_kpis["paid"]
    tbb = current_kpis["tbb"]

    # Delivered consignments: a GR is treated as delivered when Deliverydt is populated.
    delivery_col = next(
        (col for col in df.columns if str(col).replace("_", "").replace(" ", "").casefold() == "deliverydt"),
        None,
    )
    prev_delivery_col = next(
        (col for col in prev_df.columns if str(col).replace("_", "").replace(" ", "").casefold() == "deliverydt"),
        None,
    ) if prev_df is not None and not prev_df.empty else None

    delivered_gr = int(pd.to_datetime(df[delivery_col], errors="coerce").notna().sum()) if delivery_col else 0
    prev_delivered_gr = (
        int(pd.to_datetime(prev_df[prev_delivery_col], errors="coerce").notna().sum())
        if prev_delivery_col else 0
    )

    # Auto-calculated growth % vs Last Year for each KPI
    revenue_growth = pct_growth(revenue, prev_kpis["revenue"])
    ftl_growth = pct_growth(ftl, prev_kpis["ftl"])
    ltl_growth = pct_growth(ltl, prev_kpis["ltl"])
    gr_growth = pct_growth(total_gr, prev_kpis["total_gr"])
    delivered_growth = pct_growth(delivered_gr, prev_delivered_gr)
    weight_growth = pct_growth(aweight, prev_kpis["aweight"])
    topay_growth = pct_growth(topay, prev_kpis["topay"])
    paid_growth = pct_growth(paid, prev_kpis["paid"])
    tbb_growth = pct_growth(tbb, prev_kpis["tbb"])

    # KPI Cards
    k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9, gap="small")

    with k1:
        create_card("Revenue", format_revenue(revenue, conversion_type), "#2563eb", "💰", revenue_growth)

    with k2:
        create_card("FTL Revenue", format_revenue(ftl, conversion_type), "#2563eb", "🚛", ftl_growth)

    with k3:
        create_card("LTL Revenue", format_revenue(ltl, conversion_type), "#2563eb", "🚚", ltl_growth)

    with k4:
        create_card("Total GR", f"{total_gr:,}", "#2563eb", "📦", gr_growth)

    with k5:
        create_card("Delivered GR", f"{delivered_gr:,}", "#16a34a", "✅", delivered_growth)

    with k6:
        create_card("Total Weight (MT)", f"{aweight:,.0f}", "#2563eb", "⚓", weight_growth)

    with k7:
        create_card("Topay", format_revenue(topay, conversion_type), "#2563eb", "🧾", topay_growth)

    with k8:
        create_card("Paid", format_revenue(paid, conversion_type), "#2563eb", "🔗", paid_growth)

    with k9:
        create_card("T.B.B", format_revenue(tbb, conversion_type), "#2563eb", "🚚", tbb_growth)

    # =====================================================
    # Actual vs Target (shown only when user clicks the button)
    # =====================================================
    target_toggle_key = "show_actual_vs_target"
    if target_toggle_key not in st.session_state:
        st.session_state[target_toggle_key] = False

    target_button_label = (
        "✕ Hide Actual vs Target"
        if st.session_state[target_toggle_key]
        else "🎯 Actual vs Target"
    )

    if st.button(target_button_label, key="actual_vs_target_button", width="content"):
        st.session_state[target_toggle_key] = not st.session_state[target_toggle_key]
        st.rerun()

    if st.session_state[target_toggle_key]:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:13px;font-weight:900;color:#0f172a;'>Actual vs Target</div>"
                "<div style='font-size:10px;color:#64748b;margin-bottom:8px;'>"
                "Enter temporary targets for the currently selected dashboard filters."
                "</div>",
                unsafe_allow_html=True,
            )

            target_source = st.radio(
                "Target Source",
                ["Manual Entry", "Upload Excel"],
                horizontal=True,
                key=f"target_source_{fy}",
                help="Choose manual entry or upload a target file for the selected hierarchy.",
            )

            revenue_target_cr = 0.0
            ftl_target_cr = 0.0
            ltl_target_cr = 0.0
            gr_target = 0
            weight_target_mt = 0.0

            if target_source == "Manual Entry":
                with st.expander("Enter Target Values", expanded=True):
                    target_input_cols = st.columns(5)

                    with target_input_cols[0]:
                        revenue_target_cr = st.number_input(
                            f"Revenue Target ({revenue_unit})",
                            min_value=0.0,
                            value=st.session_state.get(f"target_revenue_{fy}", 0.0),
                            step=0.10,
                            key=f"target_revenue_{fy}",
                        )
                    with target_input_cols[1]:
                        ftl_target_cr = st.number_input(
                            f"FTL Target ({revenue_unit})",
                            min_value=0.0,
                            value=st.session_state.get(f"target_ftl_{fy}", 0.0),
                            step=0.10,
                            key=f"target_ftl_{fy}",
                        )
                    with target_input_cols[2]:
                        ltl_target_cr = st.number_input(
                            f"LTL Target ({revenue_unit})",
                            min_value=0.0,
                            value=st.session_state.get(f"target_ltl_{fy}", 0.0),
                            step=0.10,
                            key=f"target_ltl_{fy}",
                        )
                    with target_input_cols[3]:
                        gr_target = st.number_input(
                            "GR Target",
                            min_value=0,
                            value=int(st.session_state.get(f"target_gr_{fy}", 0)),
                            step=100,
                            key=f"target_gr_{fy}",
                        )
                    with target_input_cols[4]:
                        weight_target_mt = st.number_input(
                            "Weight Target (MT)",
                            min_value=0.0,
                            value=float(st.session_state.get(f"target_weight_{fy}", 0.0)),
                            step=100.0,
                            key=f"target_weight_{fy}",
                        )
            else:
                st.markdown(
                    "<div style='font-size:10px;color:#64748b;margin:2px 0 7px 0;'>"
                    "Excel columns required: <b>zone, circle, branch, month, ltl, ftl, total</b>. "
                    "Revenue values must be entered in the selected conversion unit. Use <b>All</b> where a target applies to the complete hierarchy."
                    "</div>",
                    unsafe_allow_html=True,
                )

                template_df = pd.DataFrame(
                    [
                        {
                            "zone": "NORTH ZONE",
                            "circle": "NCR CIRCLE",
                            "branch": "NOIDA",
                            "month": "Apr",
                            "ltl": 2.50,
                            "ftl": 4.50,
                            "total": 7.00,
                        },
                        {
                            "zone": "All",
                            "circle": "All",
                            "branch": "All",
                            "month": "May",
                            "ltl": 20.00,
                            "ftl": 35.00,
                            "total": 55.00,
                        },
                    ]
                )
                template_buffer = io.BytesIO()
                with pd.ExcelWriter(template_buffer, engine="openpyxl") as writer:
                    template_df.to_excel(writer, index=False, sheet_name="Targets")
                template_buffer.seek(0)

                upload_col, template_col = st.columns([2.5, 1])
                with upload_col:
                    target_file = st.file_uploader(
                        "Upload Target Excel",
                        type=["xlsx", "xls"],
                        key=f"target_excel_{fy}",
                    )
                with template_col:
                    st.download_button(
                        "Download Template",
                        data=template_buffer.getvalue(),
                        file_name="target_upload_template.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch",
                    )

                if target_file is not None:
                    try:
                        target_df = pd.read_excel(target_file)
                        target_df.columns = [str(col).strip().lower() for col in target_df.columns]
                        required_cols = ["zone", "circle", "branch", "month", "ltl", "ftl", "total"]
                        missing_cols = [col for col in required_cols if col not in target_df.columns]

                        if missing_cols:
                            st.error("Missing required columns: " + ", ".join(missing_cols))
                        else:
                            for col in ["zone", "circle", "branch", "month"]:
                                target_df[col] = target_df[col].fillna("All").astype(str).str.strip()
                            for col in ["ltl", "ftl", "total"]:
                                target_df[col] = pd.to_numeric(target_df[col], errors="coerce").fillna(0)

                            selected_values = {
                                "zone": zone,
                                "circle": circle,
                                "branch": branch,
                                "month": month,
                            }
                            matched_targets = target_df.copy()
                            for col, selected_value in selected_values.items():
                                if matched_targets.empty:
                                    break

                                normalized_values = matched_targets[col].str.casefold()
                                if selected_value != "All":
                                    normalized_selected = str(selected_value).strip().casefold()
                                    exact_rows = normalized_values.eq(normalized_selected)
                                    fallback_rows = normalized_values.eq("all")

                                    # Prefer the exact hierarchy target. Use an All row only
                                    # when no exact target exists at the selected level.
                                    if exact_rows.any():
                                        matched_targets = matched_targets[exact_rows]
                                    else:
                                        matched_targets = matched_targets[fallback_rows]
                                else:
                                    detailed_rows = ~normalized_values.eq("all")

                                    # For an All dashboard selection, aggregate detailed
                                    # rows when available. Otherwise use the All summary row.
                                    if detailed_rows.any():
                                        matched_targets = matched_targets[detailed_rows]
                                    else:
                                        matched_targets = matched_targets[~detailed_rows]

                            revenue_target_cr = float(matched_targets["total"].sum())
                            ftl_target_cr = float(matched_targets["ftl"].sum())
                            ltl_target_cr = float(matched_targets["ltl"].sum())

                            st.success(
                                f"Target loaded: Total ₹{revenue_target_cr:.2f} {revenue_unit} | "
                                f"FTL ₹{ftl_target_cr:.2f} {revenue_unit} | LTL ₹{ltl_target_cr:.2f} {revenue_unit}"
                            )
                            with st.expander("View Matched Target Rows", expanded=False):
                                st.dataframe(
                                    matched_targets[required_cols],
                                    width="stretch",
                                    hide_index=True,
                                )
                    except Exception as exc:
                        st.error(f"Unable to read target Excel file: {exc}")

            target_cols = st.columns(5 if target_source == "Manual Entry" else 3)
            with target_cols[0]:
                create_target_card(
                    "Revenue", revenue / 10000000, revenue_target_cr,
                    unit=f" {revenue_unit}", decimals=2, icon="💰",
                )
            with target_cols[1]:
                create_target_card(
                    "FTL Revenue", ftl / 10000000, ftl_target_cr,
                    unit=f" {revenue_unit}", decimals=2, icon="🚛",
                )
            with target_cols[2]:
                create_target_card(
                    "LTL Revenue", ltl / 10000000, ltl_target_cr,
                    unit=f" {revenue_unit}", decimals=2, icon="🚚",
                )
            if target_source == "Manual Entry":
                with target_cols[3]:
                    create_target_card(
                        "Total GR", total_gr, gr_target,
                        unit="", decimals=0, icon="📦",
                    )
                with target_cols[4]:
                    create_target_card(
                        "Weight", aweight, weight_target_mt,
                        unit=" MT", decimals=0, icon="⚓",
                    )

    # Small separator before charts
    compact_spacer()

    # Monthly revenue data used for monthly trend and MoM growth
    monthly = (
        df.groupby("Month")["REVENUE"]
        .sum()
        .reset_index()
    )

    monthly["Revenue Cr"] = (monthly["REVENUE"] / revenue_divisor).round(2)

    monthly["Month"] = pd.Categorical(
        monthly["Month"],
        categories=MONTH_ORDER,
        ordered=True
    )

    monthly = monthly.sort_values("Month")

    ftl_pct = (ftl / revenue * 100) if revenue else 0
    ltl_pct = (ltl / revenue * 100) if revenue else 0

    # Revenue trend and load type charts
    row1, row2 = st.columns([1.35, 0.65])

    with row1:
        with st.container(border=True):
            title_col, filter_col = st.columns([2, 2])

            with title_col:
                _trend_badge_color = "#166534" if revenue_growth >= 0 else "#dc2626"
                st.markdown(
                    f"###### Revenue Trend "
                    f"<span style='font-size:11px;font-weight:700;color:{_trend_badge_color};'>"
                    f"({growth_label(revenue_growth)} vs LY)</span>",
                    unsafe_allow_html=True
                )

            with filter_col:
                trend_type = st.segmented_control(
                    "Revenue trend period",
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    default="Monthly",
                    label_visibility="collapsed",
                    key="revenue_trend_type",
                ) or "Monthly"

            # Build trend data (Current FY vs LY) for the selected granularity
            DATE_COL = "grdt"   # change if your date column is different

            yoy_df = build_yoy_trend(
                df, prev_df, trend_type, DATE_COL, start_date, prev_start, month_map
            )

            # build_yoy_trend retains its original Crore calculation. Convert only
            # the returned display columns when Lac is selected.
            if conversion_type == "Lac":
                for revenue_col in ["Revenue Cr", "Prev Revenue Cr"]:
                    if revenue_col in yoy_df.columns:
                        yoy_df[revenue_col] = yoy_df[revenue_col] * 100

            # Add forecast only for the current ongoing month and remove future blank months
            yoy_df = add_revenue_forecast(
                yoy_df,
                trend_type,
                selected_quarter=quarter,
                selected_month=month
            )

            # Revenue trend in the same visual format as Weight Trend
            fig_yoy = go.Figure()

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Prev Revenue Cr"],
                    name=f"LY ({prev_fy})",
                    marker=dict(color="#cbd5e1", line=dict(color="#94a3b8", width=1.3)),
                    text=yoy_df["Prev Revenue Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#475569", family="Arial Black"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>LY Revenue: ₹%{{y:.2f}} {revenue_unit}<extra></extra>",
                )
            )

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Revenue Cr"],
                    name=f"Current ({fy})",
                    marker=dict(color="#2563eb", line=dict(color="#1e3a8a", width=1.3)),
                    text=yoy_df["Revenue Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#1d4ed8", family="Arial Black"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>Current Revenue: ₹%{{y:.2f}} {revenue_unit}<extra></extra>",
                )
            )

            forecast_df = yoy_df[yoy_df["Forecast Revenue Cr"].notna()].copy()
            if not forecast_df.empty:
                fig_yoy.add_trace(
                    go.Bar(
                        x=forecast_df["Period"],
                        y=forecast_df["Forecast Revenue Cr"],
                        name="Forecast",
                        marker=dict(color="#f97316", line=dict(color="#c2410c", width=1.3)),
                        text=forecast_df["Forecast Revenue Cr"],
                        texttemplate="%{text:.2f}",
                        textposition="outside",
                        textfont=dict(size=12, color="#ea580c", family="Arial Black"),
                        cliponaxis=False,
                        hovertemplate=f"<b>%{{x}}</b><br>Forecast Revenue: ₹%{{y:.2f}} {revenue_unit}<extra></extra>",
                    )
                )

            yoy_max = pd.concat(
                [
                    pd.to_numeric(yoy_df["Revenue Cr"], errors="coerce"),
                    pd.to_numeric(yoy_df["Prev Revenue Cr"], errors="coerce"),
                    pd.to_numeric(yoy_df["Forecast Revenue Cr"], errors="coerce"),
                ],
                ignore_index=True,
            ).max()
            yoy_max = yoy_max if pd.notna(yoy_max) and yoy_max > 0 else 1

            show_revenue_annotations = len(yoy_df) <= 40
            if show_revenue_annotations:
                for _, r in yoy_df.iterrows():
                    if r["Growth Label"] and r["Growth Label"] != "N/A":
                        growth_value = r["Growth %"] if pd.notna(r["Growth %"]) else 0
                        label_color = "#166534" if growth_value >= 0 else "#dc2626"
                        bar_top = max(
                            r["Revenue Cr"] if pd.notna(r["Revenue Cr"]) else 0,
                            r["Prev Revenue Cr"] if pd.notna(r["Prev Revenue Cr"]) else 0,
                            r["Forecast Revenue Cr"] if pd.notna(r["Forecast Revenue Cr"]) else 0,
                        )
                        growth_gap = 0.24 if trend_type == "Monthly" else 0.16
                        fig_yoy.add_annotation(
                            x=r["Period"],
                            y=bar_top + (yoy_max * growth_gap),
                            text=r["Growth Label"],
                            showarrow=False,
                            font=dict(size=12, color=label_color, family="Arial Black"),
                        )

            fig_yoy.update_layout(
                barmode="group",
                height=REVENUE_CHART_HEIGHT,
                margin=dict(l=2, r=2, t=30, b=2),
                plot_bgcolor="#f8fafc",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    x=0,
                    font=dict(size=11),
                ),
                font=dict(size=11),
                xaxis_title="",
                yaxis_title=f"Revenue ({revenue_unit})",
                yaxis_range=[0, yoy_max * (1.48 if trend_type == "Monthly" else 1.35)],
                bargap=0.22,
                bargroupgap=0.08,
            )
            apply_3d_chart_layout(fig_yoy, height=REVENUE_CHART_HEIGHT, margin=dict(l=8, r=8, t=34, b=8))
            fig_yoy.update_xaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=11))
            fig_yoy.update_yaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=11), title_font=dict(size=12))

            st.plotly_chart(fig_yoy, width="stretch")

    with row2:
        with st.container(border=True):
            st.markdown("###### Revenue by Load Type")

            # Donut chart for FTL/LTL revenue share
            fig_load = go.Figure(
                data=[
                    go.Pie(
                        labels=["FTL", "LTL"],
                        values=[ftl, ltl],
                        hole=0.64,
                        textinfo="percent+label",
                        pull=[0.018, 0.018],
                        rotation=135,
                        direction="clockwise",
                        marker=dict(
                            colors=["#2563eb", "#0f766e"],
                            line=dict(color="#ffffff", width=3),
                        ),
                        textfont=dict(size=10, color="white"),
                        hovertemplate="<b>%{label}</b><br>Revenue: ₹%{value:,.0f}<br>Share: %{percent}<extra></extra>",
                    )
                ]
            )

            fig_load.update_layout(
                annotations=[
                    dict(
                        text=f"<b>₹{(ftl + ltl)/revenue_divisor:.2f} {revenue_unit}</b><br><b>Total</b>",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        align="center",
                        font=dict(size=16, color="#0f172a", family="Arial Black")
                    )
                ],
                height=220,
                margin=dict(l=2, r=2, t=2, b=2),
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            fig_load.update_traces(sort=False)

            st.plotly_chart(fig_load, width="stretch")
            st.markdown(
                f"""
                <div style="display:flex;justify-content:center;gap:10px;margin-top:-10px;margin-bottom:2px;">
                    <span style="font-size:9px;font-weight:800;color:#2563eb;background:#eff6ff;border:1px solid #bfdbfe;border-radius:999px;padding:3px 7px;">🚛 FTL ₹{ftl/revenue_divisor:.2f} {revenue_unit}</span>
                    <span style="font-size:9px;font-weight:800;color:#0f766e;background:#f0fdfa;border:1px solid #99f6e4;border-radius:999px;padding:3px 7px;">🚚 LTL ₹{ltl/revenue_divisor:.2f} {revenue_unit}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Revenue by Company is intentionally placed below Load Type
        # inside the same right-side column as the Revenue Trend chart.
        company_df = (
            df.groupby("compname", dropna=False)["REVENUE"]
            .sum()
            .reset_index()
            .rename(columns={"compname": "Company"})
        )
        company_df["Company"] = company_df["Company"].fillna("Unknown").astype(str)
        company_df["Revenue Cr"] = company_df["REVENUE"] / revenue_divisor
        company_total = company_df["Revenue Cr"].sum()
        company_df["Contribution %"] = (
            company_df["Revenue Cr"] / company_total * 100 if company_total else 0
        )
        company_df = company_df.sort_values("Revenue Cr", ascending=False).reset_index(drop=True)

        # Keep the compact donut readable: show the five largest companies and
        # combine the remaining companies under Others.
        if len(company_df) > 6:
            top_company_df = company_df.head(5).copy()
            others_revenue = company_df.iloc[5:]["Revenue Cr"].sum()
            others_row = pd.DataFrame(
                {
                    "Company": ["Others"],
                    "REVENUE": [others_revenue * revenue_divisor],
                    "Revenue Cr": [others_revenue],
                    "Contribution %": [
                        (others_revenue / company_total * 100) if company_total else 0
                    ],
                }
            )
            company_chart_df = pd.concat([top_company_df, others_row], ignore_index=True)
        else:
            company_chart_df = company_df.copy()

        with st.container(border=True):
            st.markdown("###### Revenue by Company")

            if company_chart_df.empty or company_total <= 0:
                st.info("No company revenue is available for the selected filters.")
            else:
                company_colors = [
                    "#2563eb", "#16a34a", "#f59e0b",
                    "#7c3aed", "#f97316", "#94a3b8",
                ]

                # Define chart inputs explicitly to prevent NameError after deployment.
                company_labels = company_chart_df["Company"].astype(str).tolist()
                company_values = pd.to_numeric(
                    company_chart_df["Revenue Cr"], errors="coerce"
                ).fillna(0).tolist()

                fig_company = go.Figure(
                    data=[
                        go.Pie(
                            labels=company_labels,
                            values=company_values,
                            hole=0.64,
                            sort=False,
                            direction="clockwise",
                            domain=dict(x=[0.06, 0.94], y=[0.18, 0.98]),
                            customdata=company_chart_df[["Contribution %"]].to_numpy(),
                            texttemplate="%{percent:.0%}",
                            textposition="inside",
                            textfont=dict(size=9, color="white", family="Arial Black"),
                            hovertemplate=(
                                "<b>%{label}</b><br>"
                                "Revenue: ₹%{value:.2f} {revenue_unit}<br>"
                                "Contribution: %{customdata[0]:.1f}%"
                                "<extra></extra>"
                            ),
                            marker=dict(
                                colors=company_colors[:len(company_chart_df)],
                                line=dict(color="#ffffff", width=2),
                            ),
                        )
                    ]
                )

                fig_company.update_layout(
                    height=255,
                    margin=dict(l=2, r=2, t=2, b=42),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.03,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=8),
                        itemclick="toggle",
                        itemdoubleclick="toggleothers",
                    ),
                    annotations=[
                        dict(
                            text=(
                                f"<b>₹{company_total:.2f} {revenue_unit}</b>"
                                "<br><span style='font-size:10px'>Total</span>"
                            ),
                            x=0.5,
                            y=0.58,
                            showarrow=False,
                            align="center",
                            font=dict(size=15, color="#0f172a", family="Arial Black"),
                        )
                    ],
                    uniformtext_minsize=8,
                    uniformtext_mode="hide",
                )

                st.plotly_chart(
                    fig_company,
                    width="stretch",
                    config={
                        "displayModeBar": False,
                        "responsive": True,
                    },
                )

    compact_spacer()


    # =========================
    # Weight trend data is prepared inside the chart based on selected granularity
    # =========================

    # Zone-wise revenue data
    zone_df = (
        df.groupby("zone")["REVENUE"]
        .sum()
        .reset_index()
    )

    zone_df["Revenue Cr"] = (zone_df["REVENUE"] / revenue_divisor).round(2)
    zone_df["zone_short"] = zone_df["zone"].replace({
        "NORTH ZONE": "North",
        "WEST ZONE": "West",
        "SOUTH ZONE": "South",
        "EAST ZONE": "East",
        "NORTH EAST ZONE": "NE",
        "NEPAL ZONE": "Nepal"
    })

    zone_df = zone_df.sort_values("Revenue Cr", ascending=False)

    # Zone colors
    zone_colors = {
        "NORTH ZONE": "#1565C0",
        "WEST ZONE": "#009688",
        "SOUTH ZONE": "#FB8C00",
        "EAST ZONE": "#7E57C2",
        "NORTH EAST ZONE": "#EC407A",
        "NEPAL ZONE": "#EF5350",
        "North Zone": "#1565C0",
        "West Zone": "#009688",
        "South Zone": "#FB8C00",
        "East Zone": "#7E57C2",
        "North East Zone": "#EC407A",
        "Nepal Zone": "#EF5350",
    }

    if view_type == "Origin":
        zone_country_rev = (
            df.groupby(["zone", "COUNTRY"])["REVENUE"]
            .sum()
            .reset_index()
        )

        zone_country_rev["Revenue Cr"] = (
            zone_country_rev["REVENUE"] / revenue_divisor
        ).round(2)

        matrix_df = zone_country_rev.pivot(
            index="zone",
            columns="COUNTRY",
            values="Revenue Cr"
        ).fillna(0)

        matrix_df["Total"] = matrix_df.sum(axis=1)
        matrix_df = matrix_df.sort_values("Total", ascending=False)

    # =====================================================
    # Weight Trend and Revenue by Zone in one aligned row
    # =====================================================
    weight_zone_left, weight_zone_right = st.columns([1.55, 1], gap="small")
    aligned_chart_height = ALIGNED_CHART_HEIGHT

    with weight_zone_left:
        with st.container(border=True):
            weight_title_col, weight_filter_col = st.columns([2, 2])

            with weight_filter_col:
                weight_trend_type = st.segmented_control(
                    "Weight trend period",
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    default="Monthly",
                    label_visibility="collapsed",
                    key="weight_trend_type",
                )

            DATE_COL = "grdt"
            weight_yoy_df = build_weight_yoy_trend(
                df,
                prev_df,
                weight_trend_type,
                DATE_COL,
                start_date,
                prev_start,
                month_map,
            )

            weight_growth_total = pct_growth(
                weight_yoy_df["Weight MT"].sum(),
                weight_yoy_df["Prev Weight MT"].sum(),
            )
            _w_badge_color = "#166534" if weight_growth_total >= 0 else "#dc2626"

            with weight_title_col:
                st.markdown(
                    f"###### Weight (MT) Trend "
                    f"<span style='font-size:11px;font-weight:700;color:{_w_badge_color};'>"
                    f"({growth_label(weight_growth_total)} vs LY)</span>",
                    unsafe_allow_html=True,
                )

            fig_weight = go.Figure()

            fig_weight.add_trace(
                go.Bar(
                    x=weight_yoy_df["Period"],
                    y=weight_yoy_df["Prev Weight MT"],
                    name=f"LY ({prev_fy})",
                    marker=dict(color="#cbd5e1", line=dict(color="#94a3b8", width=1.3)),
                    text=weight_yoy_df["Prev Weight MT"],
                    texttemplate="%{text:.0f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#475569", family="Arial Black"),
                )
            )

            fig_weight.add_trace(
                go.Bar(
                    x=weight_yoy_df["Period"],
                    y=weight_yoy_df["Weight MT"],
                    name=f"Current ({fy})",
                    marker=dict(color="#0f766e", line=dict(color="#134e4a", width=1.3)),
                    text=weight_yoy_df["Weight MT"],
                    texttemplate="%{text:.0f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#0f766e", family="Arial Black"),
                )
            )

            weight_max = pd.concat([
                weight_yoy_df["Weight MT"],
                weight_yoy_df["Prev Weight MT"],
            ]).max()
            weight_max = weight_max if pd.notna(weight_max) and weight_max > 0 else 1

            show_weight_annotations = len(weight_yoy_df) <= 40
            if show_weight_annotations:
                for _, r in weight_yoy_df.iterrows():
                    if r["Growth Label"] and r["Growth Label"] != "N/A":
                        label_color = "#166534" if (r["Growth %"] or 0) >= 0 else "#dc2626"
                        bar_top = max(
                            r["Weight MT"] if pd.notna(r["Weight MT"]) else 0,
                            r["Prev Weight MT"] if pd.notna(r["Prev Weight MT"]) else 0,
                        )
                        growth_gap = 0.24 if weight_trend_type == "Monthly" else 0.16
                        fig_weight.add_annotation(
                            x=r["Period"],
                            y=bar_top + (weight_max * growth_gap),
                            text=r["Growth Label"],
                            showarrow=False,
                            font=dict(size=12, color=label_color, family="Arial Black"),
                        )

            fig_weight.update_layout(
                barmode="group",
                height=aligned_chart_height,
                margin=dict(l=8, r=8, t=40, b=8),
                plot_bgcolor="#f8fafc",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=11),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.03,
                    x=0,
                    font=dict(size=11),
                ),
                yaxis_title="Weight (MT)",
                yaxis_range=[0, weight_max * (1.48 if weight_trend_type == "Monthly" else 1.35)],
                bargap=0.22,
                bargroupgap=0.08,
            )
            apply_3d_chart_layout(
                fig_weight,
                height=aligned_chart_height,
                margin=dict(l=8, r=8, t=40, b=8),
            )
            fig_weight.update_xaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=11))
            fig_weight.update_yaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=11), title_font=dict(size=12))

            st.plotly_chart(
                fig_weight,
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )

    with weight_zone_right:
        with st.container(border=True):
            st.markdown("###### Revenue by Zone")

            # Preserve the existing zone aggregation and filters; only the
            # presentation is changed to match the executive-dashboard design.
            total_zone_revenue = zone_df["Revenue Cr"].sum()
            zone_donut_df = zone_df.copy()
            zone_donut_df["Percentage"] = (
                zone_donut_df["Revenue Cr"] / total_zone_revenue * 100
                if total_zone_revenue > 0 else 0
            ).round(1)
            zone_donut_df = zone_donut_df.sort_values(
                "Revenue Cr", ascending=False
            ).reset_index(drop=True)

            if zone_donut_df.empty or total_zone_revenue <= 0:
                st.info("No zone revenue is available for the selected filters.")
            else:
                zone_labels = zone_donut_df["zone_short"].astype(str).tolist()
                zone_values = zone_donut_df["Revenue Cr"].tolist()
                zone_percentages = zone_donut_df["Percentage"].tolist()
                zone_color_list = [
                    zone_colors.get(zone_name, "#2563eb")
                    for zone_name in zone_donut_df["zone"].tolist()
                ]

                # Keep the donut inside the left 60% of the card.  The exact
                # centre of this domain is x=0.30, y=0.50; using that same point
                # for the annotation keeps the total perfectly centred.
                donut_domain = dict(x=[0.00, 0.60], y=[0.00, 1.00])
                donut_center_x = sum(donut_domain["x"]) / 2
                donut_center_y = sum(donut_domain["y"]) / 2

                fig_zone = go.Figure(
                    data=[
                        go.Pie(
                            labels=zone_labels,
                            values=zone_values,
                            hole=0.62,
                            sort=False,
                            direction="clockwise",
                            rotation=90,
                            domain=donut_domain,
                            marker=dict(
                                colors=zone_color_list,
                                line=dict(color="#ffffff", width=2),
                            ),
                            customdata=zone_percentages,
                            textinfo="none",
                            hovertemplate=(
                                "<b>%{label}</b><br>Revenue: ₹%{value:.2f} {revenue_unit}"
                                "<br>Contribution: %{customdata:.1f}%<extra></extra>"
                            ),
                        )
                    ]
                )

                # Build a clean right-side legend with one fixed-height row per zone.
                # Extra vertical spacing prevents the zone name and value lines from
                # overlapping. The percentage uses the same colour as its zone slice.
                legend_y_start = 0.91
                legend_step = 0.145 if len(zone_donut_df) <= 6 else 0.115
                for idx, row in zone_donut_df.iterrows():
                    y_pos = legend_y_start - (idx * legend_step)
                    color = zone_color_list[idx]

                    # Coloured bullet aligned with the first line of the label.
                    fig_zone.add_annotation(
                        x=0.625,
                        y=y_pos,
                        xref="paper",
                        yref="paper",
                        text="●",
                        showarrow=False,
                        xanchor="left",
                        yanchor="middle",
                        font=dict(size=16, color=color),
                    )

                    # Zone name on line 1; revenue and coloured contribution on line 2.
                    fig_zone.add_annotation(
                        x=0.675,
                        y=y_pos,
                        xref="paper",
                        yref="paper",
                        text=(
                            f"<span style='font-size:14px;color:#0f172a'><b>"
                            f"{escape(str(row['zone_short']))}</b></span>"
                            f"<br><span style='font-size:12px;color:#334155'>"
                            f"₹{row['Revenue Cr']:.2f} {revenue_unit} &nbsp; "
                            f"<span style='color:{color};font-weight:700'>"
                            f"({row['Percentage']:.1f}%)</span></span>"
                        ),
                        showarrow=False,
                        xanchor="left",
                        yanchor="middle",
                        align="left",
                        font=dict(size=12, color="#334155", family="Arial"),
                    )

                # Use the same Plotly height as the Weight Trend chart so both
                # bordered Streamlit cards finish on the same horizontal line.
                # This changes presentation only; zone values and calculations
                # remain exactly the same.
                fig_zone.update_layout(
                    height=aligned_chart_height,
                    margin=dict(l=0, r=0, t=4, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    annotations=list(fig_zone.layout.annotations) + [
                        dict(
                            x=donut_center_x,
                            y=donut_center_y,
                            xref="paper",
                            yref="paper",
                            xanchor="center",
                            yanchor="middle",
                            text=(
                                f"<b>₹{total_zone_revenue:.2f} {revenue_unit}</b>"
                                "<br><span style='font-size:10px;color:#64748b'>Total</span>"
                            ),
                            showarrow=False,
                            align="center",
                            font=dict(size=15, color="#0f172a", family="Arial Black"),
                        )
                    ],
                )

                st.plotly_chart(
                    fig_zone,
                    width="stretch",
                    config={"displayModeBar": False, "responsive": True},
                )

    compact_spacer()

    # Keep Zone vs Country and Month-on-Month analysis on the same row.
    if view_type == "Origin":
        zone_table_col, mom_chart_col = st.columns([1.05, 0.95], gap="small")

        with zone_table_col:
            with st.container(border=True):
                st.markdown("###### Zone vs Country Revenue (%)")

                matrix_display = matrix_df.reset_index().reset_index(drop=True)

                matrix_display["zone"] = matrix_display["zone"].replace({
                    "NORTH ZONE": "North",
                    "WEST ZONE": "West",
                    "SOUTH ZONE": "South",
                    "EAST ZONE": "East",
                    "NORTH EAST ZONE": "NE",
                    "NEPAL ZONE": "Nepal"
                })

                numeric_cols = matrix_display.columns[1:]

                # The pivot already contains a Total column. Exclude it when calculating
                # the grand total, otherwise every value is counted twice.
                country_cols = [col for col in numeric_cols if col != "Total"]
                grand_total = matrix_display[country_cols].to_numpy().sum() if country_cols else 0

                # Show both revenue and contribution percentage in every cell.
                matrix_value_display = matrix_display.copy()
                for col in country_cols:
                    matrix_value_display[col] = matrix_display[col].apply(
                        lambda value: (
                            f"₹{value:.2f} {revenue_unit} | {(value / grand_total * 100):.1f}%"
                            if grand_total > 0
                            else f"₹{value:.2f} {revenue_unit} | 0.0%"
                        )
                    )

                matrix_value_display["Total"] = matrix_display["Total"].apply(
                    lambda value: (
                        f"₹{value:.2f} {revenue_unit} | {(value / grand_total * 100):.1f}%"
                        if grand_total > 0
                        else f"₹{value:.2f} {revenue_unit} | 0.0%"
                    )
                )

                # Render as HTML so the percentage part can have its own colour.
                # Revenue remains dark while contribution % is highlighted in blue.
                table_headers = "".join(
                    f"<th>{str(col)}</th>" for col in matrix_display.columns
                )
                table_rows = []
                for _, row in matrix_display.iterrows():
                    cells = [f"<td class='zone-name'>{row['zone']}</td>"]
                    for col in matrix_display.columns[1:]:
                        value = float(row[col]) if pd.notna(row[col]) else 0.0
                        pct = (value / grand_total * 100) if grand_total > 0 else 0.0
                        cells.append(
                            "<td>"
                            f"<span class='matrix-value'>₹{value:.2f} {revenue_unit}</span>"
                            "<span class='matrix-separator'> | </span>"
                            f"<span class='matrix-percent'>{pct:.1f}%</span>"
                            "</td>"
                        )
                    table_rows.append(f"<tr>{''.join(cells)}</tr>")

                # Let the table height follow its data rows. A maximum height is kept
                # so longer matrices scroll instead of making the page excessively tall.
                matrix_html = f"""
                <style>
                    .zone-country-wrap {{
                        width: 100%;
                        height: auto;
                        max-height: 300px;
                        overflow-x: auto;
                        overflow-y: auto;
                        border: 1px solid #e2e8f0;
                        border-radius: 10px;
                        background: #ffffff;
                    }}
                    .zone-country-table {{
                        width: 100%;
                        border-collapse: collapse;
                        font-size: 12px;
                        line-height: 1.35;
                        color: #334155;
                    }}
                    .zone-country-table th {{
                        position: sticky;
                        top: 0;
                        z-index: 1;
                        padding: 11px 10px;
                        font-size: 12px;
                        text-align: center;
                        white-space: nowrap;
                        background: #eef6ff;
                        color: #334155;
                        font-weight: 700;
                        border: 1px solid #dbe7f3;
                    }}
                    .zone-country-table td {{
                        padding: 10px;
                        font-size: 12px;
                        text-align: center;
                        white-space: nowrap;
                        background: #f8fbff;
                        border: 1px solid #e2e8f0;
                    }}
                    .zone-country-table .zone-name {{
                        text-align: left;
                        font-weight: 700;
                        color: #334155;
                    }}
                    .matrix-value {{ color: #475569; }}
                    .matrix-separator {{ color: #94a3b8; }}
                    .matrix-percent {{
                        color: #2563eb;
                        font-weight: 800;
                    }}
                </style>
                <div class="zone-country-wrap">
                    <table class="zone-country-table">
                        <thead><tr>{table_headers}</tr></thead>
                        <tbody>{''.join(table_rows)}</tbody>
                    </table>
                </div>
                """

                if hasattr(st, "html"):
                    st.html(matrix_html)
                else:
                    st.markdown(matrix_html, unsafe_allow_html=True)

        # Prepare Month-on-Month analysis for the right-hand column.
        monthly_chart = monthly.copy()
        monthly_chart["Growth %"] = (
            monthly_chart["Revenue Cr"].pct_change().mul(100).round(2)
        )
        monthly_chart = monthly_chart.dropna(subset=["Month"]).copy()
        monthly_chart["Month"] = monthly_chart["Month"].astype(str)

        with mom_chart_col:
            with st.container(border=True):
                st.markdown("###### Month on Month Revenue & Growth")
    
                fig_mom = go.Figure()
                fig_mom.add_trace(
                    go.Bar(
                        x=monthly_chart["Month"],
                        y=monthly_chart["Revenue Cr"],
                        name="Revenue",
                        marker=dict(color="#2563eb", line=dict(color="#1d4ed8", width=1.2)),
                        text=monthly_chart["Revenue Cr"],
                        texttemplate=f"₹%{{text:.2f}} {revenue_unit}",
                        textposition="outside",
                        cliponaxis=False,
                        hovertemplate=f"<b>%{{x}}</b><br>Revenue: ₹%{{y:.2f}} {revenue_unit}<extra></extra>",
                    )
                )
    
                growth_colors = [
                    "#16a34a" if pd.notna(v) and v >= 0 else "#dc2626"
                    for v in monthly_chart["Growth %"]
                ]
                fig_mom.add_trace(
                    go.Scatter(
                        x=monthly_chart["Month"],
                        y=monthly_chart["Growth %"],
                        name="MoM Growth",
                        mode="lines+markers+text",
                        yaxis="y2",
                        line=dict(color="#f59e0b", width=3),
                        marker=dict(size=8, color=growth_colors, line=dict(color="white", width=1.5)),
                        text=[
                            "" if pd.isna(v) else f"{'▲' if v >= 0 else '▼'} {abs(v):.1f}%"
                            for v in monthly_chart["Growth %"]
                        ],
                        textposition="top center",
                        textfont=dict(size=10, color="#ffffff"),
                        hovertemplate="<b>%{x}</b><br>MoM Growth: %{y:.2f}%<extra></extra>",
                    )
                )
    
                revenue_max = pd.to_numeric(monthly_chart["Revenue Cr"], errors="coerce").max()
                revenue_max = revenue_max if pd.notna(revenue_max) and revenue_max > 0 else 1
                growth_abs_max = pd.to_numeric(monthly_chart["Growth %"], errors="coerce").abs().max()
                growth_abs_max = growth_abs_max if pd.notna(growth_abs_max) and growth_abs_max > 0 else 10
    
                fig_mom.update_layout(
                    height=300,
                    margin=dict(l=10, r=10, t=35, b=10),
                    plot_bgcolor="#f8fafc",
                    paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=1.10, x=0),
                    bargap=0.35,
                    yaxis=dict(
                        title=f"Revenue ({revenue_unit})",
                        range=[0, revenue_max * 1.30],
                        showgrid=False,
                        zeroline=False,
                    ),
                    yaxis2=dict(
                        title="Growth (%)",
                        overlaying="y",
                        side="right",
                        range=[-growth_abs_max * 1.35, growth_abs_max * 1.35],
                        showgrid=False,
                        zeroline=True,
                        zerolinecolor="#cbd5e1",
                    ),
                    xaxis=dict(showgrid=False, title=""),
                )
                apply_3d_chart_layout(fig_mom, height=300, margin=dict(l=10, r=10, t=38, b=10))
                fig_mom.update_xaxes(showline=False, zeroline=False)
                fig_mom.update_yaxes(showline=False)
    
                st.plotly_chart(
                    fig_mom,
                    width="stretch",
                    config={"displayModeBar": False, "responsive": True},
                )
    # =====================================================
    # Management Key Insights
    # =====================================================
    compact_spacer()

    # Zone YoY movement used for management commentary.
    current_zone_insights = (
        df.groupby("zone", dropna=False)["REVENUE"]
        .sum()
        .reset_index(name="Current Revenue")
    )
    if prev_df is not None and not prev_df.empty:
        previous_zone_insights = (
            prev_df.groupby("zone", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Previous Revenue")
        )
        zone_insights = current_zone_insights.merge(
            previous_zone_insights, on="zone", how="outer"
        ).fillna(0)
    else:
        zone_insights = current_zone_insights.copy()
        zone_insights["Previous Revenue"] = 0

    zone_insights["Variance"] = (
        zone_insights["Current Revenue"] - zone_insights["Previous Revenue"]
    )
    zone_insights["Growth %"] = zone_insights.apply(
        lambda row: pct_growth(row["Current Revenue"], row["Previous Revenue"]),
        axis=1,
    )

    positive_zones = zone_insights[zone_insights["Variance"] > 0].sort_values(
        "Variance", ascending=False
    )
    declining_zones = zone_insights[zone_insights["Variance"] < 0].sort_values(
        "Variance"
    )

    zone_name_map = {
        "NORTH ZONE": "North",
        "WEST ZONE": "West",
        "SOUTH ZONE": "South",
        "EAST ZONE": "East",
        "NORTH EAST ZONE": "North East",
        "NEPAL ZONE": "Nepal",
    }
    top_driver_names = [
        zone_name_map.get(str(value), str(value).replace(" ZONE", "").title())
        for value in positive_zones["zone"].head(2).tolist()
    ]
    if len(top_driver_names) >= 2:
        driver_text = f"{top_driver_names[0]} and {top_driver_names[1]} zones"
    elif len(top_driver_names) == 1:
        driver_text = f"the {top_driver_names[0]} zone"
    else:
        driver_text = "the selected business segments"

    overall_insight_growth = pct_growth(revenue, prev_kpis["revenue"])
    revenue_direction = "up" if overall_insight_growth >= 0 else "down"

    ftl_insight_growth = pct_growth(ftl, prev_kpis["ftl"])
    ltl_insight_growth = pct_growth(ltl, prev_kpis["ltl"])
    if ftl_insight_growth >= ltl_insight_growth:
        load_growth_text = (
            f"FTL revenue growth ({ftl_insight_growth:.1f}%) is higher than "
            f"LTL revenue growth ({ltl_insight_growth:.1f}%)."
        )
    else:
        load_growth_text = (
            f"LTL revenue growth ({ltl_insight_growth:.1f}%) is higher than "
            f"FTL revenue growth ({ftl_insight_growth:.1f}%)."
        )

    # Number of branches required to reach 80% of filtered revenue.
    branch_contribution = (
        df.groupby("branch", dropna=False)["REVENUE"]
        .sum()
        .sort_values(ascending=False)
    )
    contribution_total = branch_contribution.sum()
    if contribution_total > 0:
        cumulative_share = branch_contribution.cumsum() / contribution_total
        branches_for_80 = int((cumulative_share < 0.80).sum() + 1)
    else:
        branches_for_80 = 0

    if len(declining_zones) == 1:
        decline_zone_name = zone_name_map.get(
            str(declining_zones.iloc[0]["zone"]),
            str(declining_zones.iloc[0]["zone"]).replace(" ZONE", "").title(),
        )
        zone_decline_text = f"{decline_zone_name} Zone is the only zone showing decline for the selected period."
    elif len(declining_zones) > 1:
        decline_names = [
            zone_name_map.get(str(value), str(value).replace(" ZONE", "").title())
            for value in declining_zones["zone"].head(3).tolist()
        ]
        zone_decline_text = (
            f"{len(declining_zones)} zones are showing decline, led by "
            f"{', '.join(decline_names)}."
        )
    else:
        zone_decline_text = "No zone is showing a decline for the selected period."

    # Branches declining more than 20% vs LY.
    current_branch_insights = (
        df.groupby("branch", dropna=False)["REVENUE"]
        .sum()
        .reset_index(name="Current Revenue")
    )
    if prev_df is not None and not prev_df.empty:
        previous_branch_insights = (
            prev_df.groupby("branch", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Previous Revenue")
        )
        branch_yoy_insights = current_branch_insights.merge(
            previous_branch_insights, on="branch", how="outer"
        ).fillna(0)
        branch_yoy_insights["Growth %"] = branch_yoy_insights.apply(
            lambda row: pct_growth(row["Current Revenue"], row["Previous Revenue"]),
            axis=1,
        )
        branch_decline_count = int(
            (branch_yoy_insights["Growth %"] < -20).sum()
        )
    else:
        branch_decline_count = 0

    key_insight_messages = [
        (
            f"Revenue is {revenue_direction} by {abs(overall_insight_growth):.1f}% vs LY, "
            f"driven by strong performance in {driver_text}."
        ),
        load_growth_text,
        f"Top {branches_for_80} branches contribute to 80% of total revenue.",
        zone_decline_text,
        f"{branch_decline_count} branches have declined more than 20% vs LY.",
    ]

    # =====================================================
    # Top 10 Consignors / Consignees | View-type aware
    # =====================================================
    compact_spacer()

    def _find_column(frame, candidates):
        """Find a dataframe column using exact and normalized candidate names."""
        if frame is None:
            return None
        for candidate in candidates:
            if candidate in frame.columns:
                return candidate
        normalized = {
            str(col).replace(" ", "").replace("_", "").replace("-", "").casefold(): col
            for col in frame.columns
        }
        for candidate in candidates:
            key = str(candidate).replace(" ", "").replace("_", "").replace("-", "").casefold()
            if key in normalized:
                return normalized[key]
        return None

    if view_type == "Origin":
        party_label = "Consignor"
        party_candidates = [
            "consignor", "CONSIGNOR", "Consignor", "consignorname", "CONSIGNORNAME",
            "ConsignorName", "consignor_name", "CONSIGNOR_NAME", "customer", "CUSTOMER",
            "customername", "CUSTOMERNAME", "partyname", "PARTYNAME", "clientname", "CLIENTNAME",
        ]
    else:
        party_label = "Consignee"
        party_candidates = [
            "consignee", "CONSIGNEE", "Consignee", "consigneename", "CONSIGNEENAME",
            "ConsigneeName", "consignee_name", "CONSIGNEE_NAME", "receiver", "RECEIVER",
            "receivername", "RECEIVERNAME", "deliveryparty", "DELIVERYPARTY",
        ]

    party_col = _find_column(df, party_candidates)
    prev_party_col = _find_column(prev_df, party_candidates) if prev_df is not None and not prev_df.empty else None

    party_layout_col, route_layout_col = st.columns(2, gap="medium")

    if party_col is not None:
        # Current-year customer revenue under the already-applied dashboard filters.
        current_party = (
            df.assign(_party=df[party_col].fillna("Unknown").astype(str).str.strip())
            .query("_party != ''")
            .groupby("_party", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Current Revenue")
        )

        # Same-period last-year revenue for the same customer field.
        if prev_party_col is not None:
            previous_party = (
                prev_df.assign(
                    _party=prev_df[prev_party_col].fillna("Unknown").astype(str).str.strip()
                )
                .query("_party != ''")
                .groupby("_party", dropna=False)["REVENUE"]
                .sum()
                .reset_index(name="Previous Revenue")
            )
        else:
            previous_party = pd.DataFrame(columns=["_party", "Previous Revenue"])

        customer_insights = current_party.merge(
            previous_party, on="_party", how="left"
        ).fillna({"Previous Revenue": 0})
        customer_insights["Revenue Cr"] = (
            customer_insights["Current Revenue"] / revenue_divisor
        ).round(2)
        customer_total_revenue = customer_insights["Current Revenue"].sum()
        customer_insights["Share %"] = (
            customer_insights["Current Revenue"] / customer_total_revenue * 100
            if customer_total_revenue > 0 else 0
        )
        customer_insights["Growth %"] = customer_insights.apply(
            lambda row: pct_growth(row["Current Revenue"], row["Previous Revenue"])
            if row["Previous Revenue"] > 0 else None,
            axis=1,
        )
        customer_insights = (
            customer_insights.sort_values("Current Revenue", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

        with party_layout_col:
            with st.container(border=True):
                st.markdown(
                    "###### Top 10 Customers by Revenue"
                    f"<div style='font-size:10px;color:#64748b;margin-top:-4px;'>"
                    f"Customer basis: {party_label} | Current FY revenue, share and YoY movement."
                    "</div>",
                    unsafe_allow_html=True,
                )

                if customer_insights.empty:
                    st.info("No customer revenue is available for the selected filters.")
                else:
                    max_customer_revenue = max(
                        customer_insights["Revenue Cr"].max(), 1
                    )
                    customer_rows = []

                    for idx, row in customer_insights.iterrows():
                        revenue_cr = float(row["Revenue Cr"] or 0)
                        share_pct = float(row["Share %"] or 0)
                        bar_width = min((revenue_cr / max_customer_revenue) * 100, 100)
                        growth = row["Growth %"]

                        if pd.isna(growth):
                            growth_html = (
                                "<span class='cust-growth new'>NEW</span>"
                            )
                        else:
                            positive = growth >= 0
                            growth_class = "up" if positive else "down"
                            growth_arrow = "▲" if positive else "▼"
                            growth_html = (
                                f"<span class='cust-growth {growth_class}'>"
                                f"{growth_arrow} {abs(growth):.1f}%</span>"
                            )

                        full_name = escape(str(row["_party"]))
                        customer_rows.append(
                            "<tr>"
                            f"<td class='cust-rank'>{idx + 1}</td>"
                            f"<td class='cust-name' title='{full_name}'>{full_name}</td>"
                            "<td class='cust-revenue'>"
                            f"<div class='cust-value'>₹{revenue_cr:.2f} {revenue_unit}</div>"
                            "<div class='cust-bar-track'>"
                            f"<div class='cust-bar-fill' style='width:{bar_width:.1f}%'></div>"
                            "</div></td>"
                            f"<td class='cust-share'>{share_pct:.1f}%</td>"
                            f"<td class='cust-yoy'>{growth_html}</td>"
                            "</tr>"
                        )

                    customer_table_html = f"""
                    <style>
                        .customer-insight-wrap {{
                            width:100%; overflow-x:auto; margin-top:5px;
                            border:1px solid #e2e8f0; border-radius:10px;
                            background:#ffffff;
                        }}
                        .customer-insight-table {{
                            width:100%; border-collapse:collapse;
                            table-layout:fixed; font-size:10px; color:#334155;
                        }}
                        .customer-insight-table th {{
                            padding:7px 6px; background:#f8fafc;
                            color:#64748b; font-size:9px; font-weight:800;
                            text-align:left; border-bottom:1px solid #e2e8f0;
                            white-space:nowrap;
                        }}
                        .customer-insight-table td {{
                            padding:6px; border-bottom:1px solid #edf2f7;
                            vertical-align:middle;
                        }}
                        .customer-insight-table tr:last-child td {{border-bottom:0;}}
                        .customer-insight-table tbody tr:hover {{background:#f8fbff;}}
                        /* Narrow rank column removes the unnecessary gap before Customer Name. */
                        .cust-rank {{
                            width:4%; padding-left:2px !important; padding-right:2px !important;
                            text-align:center; font-weight:800; color:#64748b;
                        }}
                        .cust-name {{
                            width:38%; padding-left:3px !important;
                            font-weight:750; color:#1e293b;
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                        }}
                        .cust-revenue {{width:32%;}}
                        .cust-value {{font-weight:850; color:#0f172a; margin-bottom:3px;}}
                        .cust-bar-track {{
                            width:100%; height:4px; border-radius:999px;
                            background:#e8eef8; overflow:hidden;
                        }}
                        .cust-bar-fill {{
                            height:4px; border-radius:999px;
                            background:linear-gradient(90deg,#60a5fa,#2563eb);
                        }}
                        .cust-share {{width:12%; text-align:right; font-weight:800; color:#475569;}}
                        .cust-yoy {{width:14%; text-align:right;}}
                        .cust-growth {{
                            display:inline-block; min-width:50px; text-align:right;
                            font-size:9px; font-weight:900;
                        }}
                        .cust-growth.up {{color:#16a34a;}}
                        .cust-growth.down {{color:#dc2626;}}
                        .cust-growth.new {{color:#7c3aed;}}
                    </style>
                    <div class="customer-insight-wrap">
                        <table class="customer-insight-table">
                            <!-- Explicit column widths keep rank and name close on every screen. -->
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
                                    <th>Customer Name</th>
                                    <th>Revenue ({revenue_unit})</th>
                                    <th style="text-align:right;">% Share</th>
                                    <th style="text-align:right;">vs LY</th>
                                </tr>
                            </thead>
                            <tbody>{''.join(customer_rows)}</tbody>
                        </table>
                    </div>
                    """

                    if hasattr(st, "html"):
                        st.html(customer_table_html)
                    else:
                        st.markdown(customer_table_html, unsafe_allow_html=True)
    else:
        with party_layout_col:
            with st.container(border=True):
                st.info(
                    "Top 10 Customers could not be displayed because a matching "
                    f"{party_label.lower()} column was not found in the booking dataset."
                )

    # =====================================================
    # Top 10 Routes | Same executive table treatment as Top Customers
    # =====================================================
    compact_spacer()

    route_candidates = ["route", "ROUTE", "Route"]
    route_col = _find_column(df, route_candidates)
    prev_route_col = (
        _find_column(prev_df, route_candidates)
        if prev_df is not None and not prev_df.empty
        else None
    )

    def _orient_route(route_value, selected_view):
        """Keep stored route for Origin view and reverse it for Destination view."""
        if pd.isna(route_value):
            return "Unknown"

        route_text = str(route_value).strip()
        if not route_text:
            return "Unknown"

        if selected_view == "Origin":
            return route_text

        # Reverse only when a clear route separator is available.
        separators = [" → ", "→", " -> ", "->", " - ", " TO ", " to "]
        for separator in separators:
            if separator in route_text:
                parts = [part.strip() for part in route_text.split(separator) if part.strip()]
                if len(parts) >= 2:
                    return " → ".join(reversed(parts))

        # Keep the original text when its format cannot be safely split.
        return route_text

    if route_col:
        current_route_data = df.copy()
        current_route_data["_route"] = current_route_data[route_col].apply(
            lambda value: _orient_route(value, view_type)
        )
        current_routes = (
            current_route_data[current_route_data["_route"] != "Unknown"]
            .groupby("_route", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Current Revenue")
        )

        if prev_route_col:
            previous_route_data = prev_df.copy()
            previous_route_data["_route"] = previous_route_data[prev_route_col].apply(
                lambda value: _orient_route(value, view_type)
            )
            previous_routes = (
                previous_route_data[previous_route_data["_route"] != "Unknown"]
                .groupby("_route", dropna=False)["REVENUE"]
                .sum()
                .reset_index(name="Previous Revenue")
            )
        else:
            previous_routes = pd.DataFrame(columns=["_route", "Previous Revenue"])

        route_yoy = current_routes.merge(
            previous_routes,
            on="_route",
            how="left",
        ).fillna({"Previous Revenue": 0})

        route_yoy["Revenue Cr"] = (route_yoy["Current Revenue"] / revenue_divisor).round(2)
        route_total_revenue = route_yoy["Current Revenue"].sum()
        route_yoy["Share %"] = (
            route_yoy["Current Revenue"] / route_total_revenue * 100
            if route_total_revenue > 0 else 0
        )
        route_yoy["Growth %"] = route_yoy.apply(
            lambda row: pct_growth(row["Current Revenue"], row["Previous Revenue"])
            if row["Previous Revenue"] > 0 else None,
            axis=1,
        )

        # Preserve the existing Top-7 ranking business rule.
        route_yoy = (
            route_yoy.sort_values("Current Revenue", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )

        with route_layout_col:
            with st.container(border=True):
                st.markdown(
                    f"###### Top 10 Routes by Revenue"
                    "<div style='font-size:10px;color:#64748b;margin-top:-4px;'>"
                    + ("Origin → Destination" if view_type == "Origin" else "Destination → Origin")
                    + " | Current FY revenue, share and YoY movement.</div>",
                    unsafe_allow_html=True,
                )

                if route_yoy.empty:
                    st.info("No route data is available for the selected filters.")
                else:
                    max_route_revenue = max(route_yoy["Revenue Cr"].max(), 1)
                    route_rows = []

                    for idx, row in route_yoy.iterrows():
                        revenue_cr = float(row["Revenue Cr"] or 0)
                        share_pct = float(row["Share %"] or 0)
                        bar_width = min((revenue_cr / max_route_revenue) * 100, 100)
                        growth = row["Growth %"]

                        if pd.isna(growth):
                            growth_html = "<span class='route-growth new'>NEW</span>"
                        else:
                            positive = growth >= 0
                            growth_class = "up" if positive else "down"
                            growth_arrow = "▲" if positive else "▼"
                            growth_html = (
                                f"<span class='route-growth {growth_class}'>"
                                f"{growth_arrow} {abs(growth):.1f}%</span>"
                            )

                        full_route = escape(str(row["_route"]))
                        route_rows.append(
                            "<tr>"
                            f"<td class='route-rank'>{idx + 1}</td>"
                            f"<td class='route-name' title='{full_route}'>{full_route}</td>"
                            "<td class='route-revenue'>"
                            f"<div class='route-value'>₹{revenue_cr:.2f} {revenue_unit}</div>"
                            "<div class='route-bar-track'>"
                            f"<div class='route-bar-fill' style='width:{bar_width:.1f}%'></div>"
                            "</div></td>"
                            f"<td class='route-share'>{share_pct:.1f}%</td>"
                            f"<td class='route-yoy'>{growth_html}</td>"
                            "</tr>"
                        )

                    route_table_html = f"""
                    <style>
                        .route-insight-wrap {{
                            width:100%; overflow-x:auto; margin-top:5px;
                            border:1px solid #e2e8f0; border-radius:10px;
                            background:#ffffff;
                        }}
                        .route-insight-table {{
                            width:100%; border-collapse:collapse;
                            table-layout:fixed; font-size:10px; color:#334155;
                        }}
                        .route-insight-table th {{
                            padding:7px 6px; background:#f8fafc;
                            color:#64748b; font-size:9px; font-weight:800;
                            text-align:left; border-bottom:1px solid #e2e8f0;
                            white-space:nowrap;
                        }}
                        .route-insight-table td {{
                            padding:6px; border-bottom:1px solid #edf2f7;
                            vertical-align:middle;
                        }}
                        .route-insight-table tr:last-child td {{border-bottom:0;}}
                        .route-insight-table tbody tr:hover {{background:#f8fbff;}}
                        /* Narrow rank column removes the unnecessary gap before Route. */
                        .route-rank {{
                            width:4%; padding-left:2px !important; padding-right:2px !important;
                            text-align:center; font-weight:800; color:#64748b;
                        }}
                        .route-name {{
                            width:38%; padding-left:3px !important;
                            font-weight:750; color:#1e293b;
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                        }}
                        .route-revenue {{width:32%;}}
                        .route-value {{font-weight:850; color:#0f172a; margin-bottom:3px;}}
                        .route-bar-track {{
                            width:100%; height:4px; border-radius:999px;
                            background:#e8eef8; overflow:hidden;
                        }}
                        .route-bar-fill {{
                            height:4px; border-radius:999px;
                            background:linear-gradient(90deg,#2dd4bf,#0f766e);
                        }}
                        .route-share {{width:12%; text-align:right; font-weight:800; color:#475569;}}
                        .route-yoy {{width:14%; text-align:right;}}
                        .route-growth {{
                            display:inline-block; min-width:50px; text-align:right;
                            font-size:9px; font-weight:900;
                        }}
                        .route-growth.up {{color:#16a34a;}}
                        .route-growth.down {{color:#dc2626;}}
                        .route-growth.new {{color:#7c3aed;}}
                    </style>
                    <div class="route-insight-wrap">
                        <table class="route-insight-table">
                            <!-- Explicit column widths keep rank and route close on every screen. -->
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
                                    <th>Route</th>
                                    <th>Revenue ({revenue_unit})</th>
                                    <th style="text-align:right;">% Share</th>
                                    <th style="text-align:right;">vs LY</th>
                                </tr>
                            </thead>
                            <tbody>{''.join(route_rows)}</tbody>
                        </table>
                    </div>
                    """

                    if hasattr(st, "html"):
                        st.html(route_table_html)
                    else:
                        st.markdown(route_table_html, unsafe_allow_html=True)
    else:
        with route_layout_col:
            with st.container(border=True):
                st.info(
                    "Top 7 Routes could not be displayed because the route column was not found "
                    "in the booking dataset."
                )

    # Small separator before branch analysis
    compact_spacer()

    # Branch summary for top/bottom branches and insights
    branch_summary = (
        df.groupby("branch")
        .agg(
            Revenue=("REVENUE", "sum"),
            GR_Count=("grno", "count"),
            Weight=("aweight", "sum"),
            FTL=("REVENUE", lambda x: x[df.loc[x.index, "LOADTYPE"] == "FTL"].sum()),
            LTL=("REVENUE", lambda x: x[df.loc[x.index, "LOADTYPE"] == "LTL"].sum())
        )
        .reset_index()
    )

    top10_df = branch_summary.sort_values("Revenue", ascending=False).head(10).copy()
    top10_df["Revenue Cr"] = (top10_df["Revenue"] / revenue_divisor).round(2)

    bottom10_df = branch_summary[branch_summary["Revenue"] >= 1000000].copy()
    bottom10_df = bottom10_df.sort_values("Revenue", ascending=True).head(10)
    bottom10_df["Revenue Cr"] = (bottom10_df["Revenue"] / revenue_divisor).round(2)

    # Keep Top Branches, Bottom Branches and Operational Highlights in one fitted row.
    b1, b2, b3 = st.columns([1, 1, 1.08], gap="small")

    with b1:
        with st.container(border=True):
            st.markdown("###### Top 10 Branches by Revenue")

            max_top = top10_df["Revenue Cr"].max() if not top10_df.empty else 1

            for i, row in top10_df.reset_index(drop=True).iterrows():
                mini_rank_card(
                    i + 1,
                    row["branch"],
                    row["Revenue Cr"],
                    max_top,
                    "#22c55e"
                )

    with b2:
        with st.container(border=True):
            st.markdown("###### Bottom 10 Branches by Revenue")

            max_bottom = bottom10_df["Revenue Cr"].max() if not bottom10_df.empty else 1

            for i, row in bottom10_df.reset_index(drop=True).iterrows():
                mini_rank_card(
                    i + 1,
                    row["branch"],
                    row["Revenue Cr"],
                    max_bottom,
                    "#ef4444"
                )

    with b3:
        _render_operational_highlights(df, prev_df)

    compact_spacer()

    with st.container(border=True):
        # Gradient management insight panel with larger, more readable typography.
        st.markdown(
            """
            <div style="font-size:16px;font-weight:950;color:#0f2744;margin:1px 0 10px 2px;
                        letter-spacing:.25px;">MANAGEMENT INSIGHTS</div>
            """,
            unsafe_allow_html=True,
        )
        insight_icons = ["📈", "🚛", "🎯", "🌐", "⚠️"]
        insight_titles = ["Revenue movement", "Load mix", "Revenue concentration", "Zone watch", "Branch watch"]
        insight_gradients = [
            ("#eaf3ff", "#dbeafe", "#2563eb"),
            ("#ecfeff", "#ccfbf1", "#0f766e"),
            ("#fff7ed", "#ffedd5", "#ea580c"),
            ("#f5f3ff", "#ede9fe", "#7c3aed"),
            ("#fff1f2", "#ffe4e6", "#dc2626"),
        ]
        insight_cols = st.columns(5, gap="small")
        for idx, (message, icon, title) in enumerate(zip(key_insight_messages, insight_icons, insight_titles)):
            start_color, end_color, accent_color = insight_gradients[idx]
            with insight_cols[idx]:
                st.markdown(
                    f"""
                    <div style="min-height:118px;padding:12px 13px;border:1px solid {accent_color}35;
                                border-radius:13px;background:linear-gradient(145deg,{start_color} 0%,#ffffff 48%,{end_color} 100%);
                                box-shadow:0 7px 16px rgba(15,42,67,.10),inset 0 1px 0 rgba(255,255,255,.95);">
                        <div style="display:flex;align-items:center;gap:7px;margin-bottom:8px;">
                            <span style="display:inline-flex;width:28px;height:28px;align-items:center;justify-content:center;
                                         font-size:17px;border-radius:9px;background:#ffffffcc;border:1px solid {accent_color}45;
                                         box-shadow:0 3px 7px rgba(15,42,67,.10);">{icon}</span>
                            <span style="font-size:11px;font-weight:950;color:{accent_color};text-transform:uppercase;
                                         letter-spacing:.30px;line-height:1.15;">{title}</span>
                        </div>
                        <div style="font-size:13px;line-height:1.48;color:#18344f;font-weight:700;">{message}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


    # Colour the branch-detail expanders and make their labels look like action buttons.
    st.markdown(
        """
        <style>
            div[data-testid="stExpander"] {
                border: 1px solid #93b4df !important;
                border-radius: 12px !important;
                overflow: hidden !important;
                background: linear-gradient(145deg,#f8fbff 0%,#eef5ff 100%) !important;
                box-shadow: 0 6px 14px rgba(37,99,235,.10) !important;
            }
            div[data-testid="stExpander"] summary {
                min-height: 46px !important;
                padding: 8px 13px !important;
                background: linear-gradient(90deg,#2563eb 0%,#1d4ed8 55%,#0f766e 100%) !important;
                color: #ffffff !important;
                border-radius: 10px !important;
            }
            div[data-testid="stExpander"] summary:hover {
                background: linear-gradient(90deg,#1d4ed8 0%,#1e40af 55%,#0f766e 100%) !important;
            }
            div[data-testid="stExpander"] summary p,
            div[data-testid="stExpander"] summary span,
            div[data-testid="stExpander"] summary svg {
                color: #ffffff !important;
                fill: #ffffff !important;
                font-size: 13px !important;
                font-weight: 900 !important;
            }
            div[data-testid="stExpander"] details[open] summary {
                border-radius: 10px 10px 0 0 !important;
                box-shadow: 0 4px 9px rgba(15,42,67,.16) !important;
            }
            div[data-testid="stExpander"] details > div {
                padding: 10px !important;
                background: #ffffff !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =====================================================
    # Branch/Agency Network Changes with revenue from Active Date
    # =====================================================
    filtered_station_df = station_df.copy()

    if "FIN_MONTH" in filtered_station_df.columns and filtered_station_df["FIN_MONTH"].notna().any():
        if month != "All":
            fin_month_for_month = [k for k, v in month_map.items() if v == month]
            if fin_month_for_month:
                filtered_station_df = filtered_station_df[filtered_station_df["FIN_MONTH"].isin(fin_month_for_month)]
        elif quarter != "All":
            quarter_fin_months = [k for k, v in QUARTER_MAP.items() if v == quarter]
            filtered_station_df = filtered_station_df[filtered_station_df["FIN_MONTH"].isin(quarter_fin_months)]

    opened_df = filtered_station_df[filtered_station_df["STATUS"].astype(str).str.upper().eq("OPENED")].copy()
    closed_df = filtered_station_df[filtered_station_df["STATUS"].astype(str).str.upper().eq("CLOSED")].copy()

    opened_branches = len(opened_df)
    closed_branches = len(closed_df)
    net_increase = opened_branches - closed_branches

    period_label = f"{fy}"
    if month != "All":
        period_label = f"{month} {fy}"
    elif quarter != "All":
        period_label = f"{quarter} {fy}"

    def _normalise_key(value):
        return "".join(ch for ch in str(value).strip().casefold() if ch.isalnum())

    # Revenue is counted only from each branch/agency's own Active Date.
    booking_date_col = _find_normalized_column(df, "grdt")
    booking_branch_col = _find_normalized_column(df, "branch")
    revenue_rows = []

    if not opened_df.empty:
        opened_df["activedate"] = pd.to_datetime(opened_df["activedate"], errors="coerce")
        booking_work = df.copy()
        if booking_date_col:
            booking_work[booking_date_col] = pd.to_datetime(booking_work[booking_date_col], errors="coerce")
        if booking_branch_col:
            booking_work["_branch_key"] = booking_work[booking_branch_col].map(_normalise_key)

        analysis_end = pd.to_datetime(end_date)
        today = pd.Timestamp.today().normalize()
        analysis_end = min(analysis_end, today)

        for _, station in opened_df.iterrows():
            active_date = station.get("activedate")
            branch_name = station.get("BRANCH", "")
            branch_code = station.get("CODE", "")
            keys = {_normalise_key(branch_name), _normalise_key(branch_code)} - {""}

            matched = booking_work.iloc[0:0].copy()
            if booking_branch_col and booking_date_col and pd.notna(active_date):
                matched = booking_work[
                    booking_work["_branch_key"].isin(keys)
                    & booking_work[booking_date_col].ge(active_date)
                    & booking_work[booking_date_col].le(analysis_end)
                ].copy()

            active_days = max((analysis_end - active_date.normalize()).days + 1, 0) if pd.notna(active_date) else 0
            active_months = max(active_days / 30.44, 1) if active_days else 1
            revenue_value = float(matched["REVENUE"].sum()) if "REVENUE" in matched.columns else 0.0
            gr_count = int(matched["grno"].count()) if "grno" in matched.columns else len(matched)
            weight_mt = float(matched["aweight"].sum() / 1000) if "aweight" in matched.columns else 0.0
            avg_monthly = revenue_value / active_months if active_days else 0.0
            revenue_per_day = revenue_value / active_days if active_days else 0.0

            if active_days < 30:
                performance = "New - Monitoring"
            elif avg_monthly >= 1000000:
                performance = "Strong"
            elif avg_monthly >= 500000:
                performance = "Developing"
            else:
                performance = "Needs Attention"

            revenue_rows.append({
                "ZONE": station.get("ZONE", ""),
                "TYPE": station.get("TYPE", ""),
                "BRANCH": branch_name,
                "CODE": branch_code,
                "CITY": station.get("CITY", ""),
                "STATE": station.get("STATE", ""),
                "Active Date": active_date,
                "Active Days": active_days,
                "GR Count": gr_count,
                "Weight MT": round(weight_mt, 1),
                f"Revenue ({revenue_unit})": round(revenue_value / revenue_divisor, 2),
                f"Avg Monthly Revenue ({revenue_unit})": round(avg_monthly / revenue_divisor, 2),
                "Revenue / Day": round(revenue_per_day, 0),
                "Performance": performance,
            })

    opened_revenue_df = pd.DataFrame(revenue_rows)
    total_new_revenue = opened_revenue_df.get(f"Revenue ({revenue_unit})", pd.Series(dtype=float)).sum()
    total_new_gr = opened_revenue_df.get("GR Count", pd.Series(dtype=float)).sum()
    avg_new_monthly = opened_revenue_df.get(f"Avg Monthly Revenue ({revenue_unit})", pd.Series(dtype=float)).sum()
    productive_count = int(opened_revenue_df.get("Performance", pd.Series(dtype=str)).isin(["Strong", "Developing"]).sum())

    with st.container(border=True):
        st.markdown(
            f"<div style='font-size:16px;font-weight:950;color:#0f2744;'>🏢 Branch/Agency Network Changes ({period_label})</div>"
            "<div style='font-size:10px;color:#64748b;margin:2px 0 9px;'>Revenue is calculated from each location's Active Date up to the selected period end.</div>",
            unsafe_allow_html=True,
        )
        n1, n2, n3, n4, n5, n6 = st.columns(6, gap="small")
        n1.metric("Opened", f"{opened_branches:,}")
        n2.metric("Closed", f"{closed_branches:,}")
        n3.metric("Net Increase", f"{net_increase:+,}")
        n4.metric(f"New Revenue ({revenue_unit})", f"{total_new_revenue:,.2f}")
        n5.metric("New-Branch GR", f"{int(total_new_gr):,}")
        n6.metric("Productive Locations", f"{productive_count}/{opened_branches}")

        if opened_revenue_df.empty:
            st.info("No newly opened branch/agency records are available for the selected period.")
        else:
            st.dataframe(
                opened_revenue_df.sort_values(f"Revenue ({revenue_unit})", ascending=False),
                width="stretch",
                hide_index=True,
                column_config={
                    "Active Date": st.column_config.DateColumn(format="DD-MMM-YYYY"),
                    f"Revenue ({revenue_unit})": st.column_config.NumberColumn(format="%.2f"),
                    f"Avg Monthly Revenue ({revenue_unit})": st.column_config.NumberColumn(format="%.2f"),
                    "Revenue / Day": st.column_config.NumberColumn(format="₹ %.0f"),
                    "Weight MT": st.column_config.NumberColumn(format="%.1f"),
                },
            )
            st.caption(
                f"Combined average monthly revenue of new locations: {avg_new_monthly:,.2f} {revenue_unit}. "
                "Performance bands: Strong ≥ ₹10 lakh/month; Developing ≥ ₹5 lakh/month; below this Needs Attention."
            )

    with st.expander(f"🔒 View Closed Branch Details ({closed_branches})"):
        closed_columns = [c for c in ["ZONE", "TYPE", "BRANCH", "CODE", "CITY", "STATE", "closedate"] if c in closed_df.columns]
        st.dataframe(closed_df[closed_columns], width="stretch", hide_index=True)
