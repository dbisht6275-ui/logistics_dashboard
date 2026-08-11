# OVERVIEW VERSION: 8.7.2
from pathlib import Path
import streamlit as st
import pandas as pd
from html import escape
import plotly.graph_objects as go
import plotly.express as px
from services.data_loader import load_booking_data_pair, get_date_range
from services.branch_agency_mast import load_stationmast_data

SPACER_HEIGHT = 1
REVENUE_CHART_HEIGHT = 420
ALIGNED_CHART_HEIGHT = 245
RANKING_CHART_HEIGHT = 330

TOP_N_OPTIONS = [10, 20, 30, 40]

def compact_spacer(height=SPACER_HEIGHT):
    """Render a consistent, minimal vertical gap between sections."""
    st.markdown(f"<div aria-hidden='true' style='height:{height}px'></div>", unsafe_allow_html=True)

                           

def _inject_overview_css():
    """
    Apply the same top-alignment logic used on the Outstanding page.

    Keeping CSS inside a function prevents Streamlit from rendering separate
    top-level markdown blocks before the page heading.
    """
    st.markdown(
        """
        <style>
            
            .block-container {
                padding-top: 0.5rem;
                padding-bottom: 1rem;
            }

            .block-container > div:first-child {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

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

            h5, h6 {
                margin-top: 0rem !important;
                margin-bottom: 0.35rem !important;
            }

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
                display: none !important;
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
                display: grid;
                grid-template-columns: minmax(0, 1fr) 27px;
                align-items: center;
                gap: 6px;
            }

            .kpi-3d-head::before {
                display: none;
                content: none;
            }

            .kpi-3d-title {
                color: var(--kpi-accent);
                font-size: 11px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-weight: 400;
                letter-spacing: .15px;
                text-align: left;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
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
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 6px;
            }

            .kpi-3d-ly {
                min-width: 0;
                color: #64748b;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 9px;
                font-weight: 600;
                line-height: 1.1;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .kpi-3d-growth {
                display: inline-block;
                padding: 2px 7px;
                border: 1px solid;
                border-radius: 999px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 9px;
                font-weight: 400;
                letter-spacing: 0;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.9), 0 2px 3px rgba(15,23,42,.10);
            }

            div[data-testid="stDataFrame"] {
                font-size: 12px;
            }

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

            .filter-field-label {
                display: flex;
                align-items: center;
                gap: 5px;
                margin: 0 0 5px 3px;
                color: #243b53;
                font-size: 10px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-weight: 400;
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

            .stButton > button {
                position: relative !important;
                overflow: hidden !important;
                min-height: 34px !important;
                padding: 5px 13px !important;
                border: 1px solid #d8e2ee !important;
                border-radius: 8px !important;
                background: linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important;
                color: #334155 !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.95), 0 1px 2px rgba(15,23,42,.05) !important;
                transform: none !important;
                font-size: 11px !important;
                font-weight: 650 !important;
                letter-spacing: .05px !important;
                transition: border-color .14s ease, background .14s ease, color .14s ease, box-shadow .14s ease !important;
            }

            .stButton > button::after {
                content: "";
                position: absolute;
                left: 14px;
                right: 14px;
                bottom: 0;
                height: 2px;
                border-radius: 2px 2px 0 0;
                background: transparent;
                transition: background .14s ease, left .14s ease, right .14s ease !important;
            }

            .stButton > button:hover {
                border-color: #9bb7d8 !important;
                background: linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important;
                color: #174a7e !important;
                box-shadow: inset 0 1px 0 #ffffff, 0 2px 5px rgba(15,42,67,.08) !important;
                transform: none !important;
            }

            .stButton > button:hover::after {
                left: 10px;
                right: 10px;
                background: #60a5fa;
            }

            .stButton > button[data-testid="stBaseButton-primary"] {
                border-color: #123f73 !important;
                background: linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important;
                color: #ffffff !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 2px 5px rgba(15,42,67,.18) !important;
            }

            .stButton > button[data-testid="stBaseButton-primary"]::after {
                left: 9px;
                right: 9px;
                background: #93c5fd;
            }

            .stButton > button[data-testid="stBaseButton-primary"] p,
            .stButton > button[data-testid="stBaseButton-primary"] span {
                color: #ffffff !important;
            }

            .stButton > button p,
            .stButton > button span {
                margin: 0 !important;
                padding: 0 !important;
                color: inherit !important;
                font-size: inherit !important;
                font-weight: inherit !important;
            }

            .stButton > button:active {
                background: #e8f0fa !important;
                box-shadow: inset 0 1px 3px rgba(15,23,42,.10) !important;
                transform: none !important;
            }

            
            .block-container {max-width:100%;padding:.35rem .75rem .75rem!important;}
            div[data-testid="stVerticalBlock"] {gap:.55rem!important;}
            div[data-testid="stHorizontalBlock"] {gap:.5rem!important;}
            div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:11px!important;box-shadow:0 3px 10px rgba(15,42,67,.07)!important;}
            div[data-testid="stVerticalBlockBorderWrapper"] > div {padding:.55rem .65rem!important;}
            .executive-title {font-size:19px;}
            .filter-summary {margin:0;gap:7px;}
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
            
            div[data-testid="stElementContainer"]:has(.filter-summary) {
                position: relative !important;
                z-index: 5 !important;
                margin-top: 0 !important;
                margin-bottom: 0 !important;
            }
            .filter-summary {
                display: flex;
                flex-wrap: wrap;
                justify-content: flex-start;
                align-items: center;
                width: 100%;
                min-height: 32px;
                gap: 7px;
                margin: 0;
                padding: 0;
                line-height: 1;
                position: relative;
                z-index: 5;
                transform: none;
            }
            .filter-chip {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-height: 28px;
                padding: 6px 13px;
                border: 1px solid #b8d1f2;
                border-radius: 999px;
                background: #f5f9ff;
                color: #31557d;
                font-size: 11px;
                font-weight: 500;
                line-height: 1;
                box-shadow: inset 0 1px 0 #ffffff;
                white-space: nowrap;
            }

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

            [data-testid="stDataFrame"] {
                border: 1px solid #e2eaf3;
                box-shadow: none !important;
                background: #fbfdff;
            }

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

            
            div[data-testid="stSelectbox"] {
                display: flex !important;
                flex-direction: column !important;
                gap: 7px !important;
                padding: 0 !important;
                margin: 0 0 2px 0 !important;
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
                font-family: "Segoe UI", Arial, sans-serif !important;
                font-weight: 400 !important;
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
                    margin-bottom: 2px !important;
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

            
            div[class*="st-key-branch_slab_btn_"] {
                margin: 0 !important;
                padding: 0 !important;
            }

            div[class*="st-key-branch_slab_btn_"] div[data-testid="stButton"] {
                width: 100% !important;
                margin: 0 !important;
            }

            div[class*="st-key-branch_slab_btn_"] button {
                width: 100% !important;
                min-height: 34px !important;
                height: 34px !important;
                padding: 4px 8px !important;
                margin: 0 !important;
                border: 1px solid #d8e2ee !important;
                border-radius: 8px !important;
                background: linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important;
                color: #334155 !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.95), 0 1px 2px rgba(15,23,42,.05) !important;
                transform: none !important;
                font-size: 11px !important;
                font-weight: 650 !important;
                white-space: nowrap !important;
                transition: border-color .14s ease, background .14s ease, color .14s ease, box-shadow .14s ease !important;
            }

            div[class*="st-key-branch_slab_btn_"] button:hover {
                border-color: #9bb7d8 !important;
                background: linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important;
                color: #174a7e !important;
                box-shadow: inset 0 1px 0 #ffffff, 0 2px 5px rgba(15,42,67,.08) !important;
                transform: none !important;
            }

            div[class*="st-key-branch_slab_btn_"] button[data-testid="stBaseButton-primary"] {
                border-color: #123f73 !important;
                background: linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important;
                color: #ffffff !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 2px 5px rgba(15,42,67,.18) !important;
            }

            div[class*="st-key-branch_slab_btn_"] button[data-testid="stBaseButton-primary"] p,
            div[class*="st-key-branch_slab_btn_"] button[data-testid="stBaseButton-primary"] span {
                color: #ffffff !important;
            }

            div[class*="st-key-branch_slab_btn_"] button p,
            div[class*="st-key-branch_slab_btn_"] button span {
                margin: 0 !important;
                padding: 0 !important;
                font-size: 11px !important;
                font-weight: 650 !important;
                white-space: nowrap !important;
            }

            @media (max-width: 1500px) {
                div[class*="st-key-branch_slab_btn_"] button {
                    min-height: 34px !important;
                    height: 34px !important;
                    padding: 4px 5px !important;
                    font-size: 9.5px !important;
                }
                div[class*="st-key-branch_slab_btn_"] button p,
                div[class*="st-key-branch_slab_btn_"] button span {
                    font-size: 9.5px !important;
                }
            }

            div[class*="st-key-revenue_period_btn_"],
            div[class*="st-key-weight_period_btn_"],
            div[class*="st-key-target_level_btn_"] {
                margin: 0 !important;
                padding: 0 !important;
            }

            div[class*="st-key-revenue_period_btn_"] div[data-testid="stButton"],
            div[class*="st-key-weight_period_btn_"] div[data-testid="stButton"],
            div[class*="st-key-target_level_btn_"] div[data-testid="stButton"] {
                width: 100% !important;
                margin: 0 !important;
            }

            div[class*="st-key-revenue_period_btn_"] button,
            div[class*="st-key-weight_period_btn_"] button,
            div[class*="st-key-target_level_btn_"] button {
                width: 100% !important;
                min-height: 34px !important;
                height: 34px !important;
                padding: 4px 8px !important;
                margin: 0 !important;
                border: 1px solid #d8e2ee !important;
                border-radius: 8px !important;
                background: linear-gradient(180deg,#ffffff 0%,#f7f9fc 100%) !important;
                color: #334155 !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.95), 0 1px 2px rgba(15,23,42,.05) !important;
                transform: none !important;
                font-size: 11px !important;
                font-weight: 650 !important;
                white-space: nowrap !important;
                transition: border-color .14s ease, background .14s ease, color .14s ease, box-shadow .14s ease !important;
            }

            div[class*="st-key-revenue_period_btn_"] button:hover,
            div[class*="st-key-weight_period_btn_"] button:hover,
            div[class*="st-key-target_level_btn_"] button:hover {
                border-color: #9bb7d8 !important;
                background: linear-gradient(180deg,#ffffff 0%,#eef5ff 100%) !important;
                color: #174a7e !important;
                box-shadow: inset 0 1px 0 #ffffff, 0 2px 5px rgba(15,42,67,.08) !important;
                transform: none !important;
            }

            div[class*="st-key-revenue_period_btn_"] button[data-testid="stBaseButton-primary"],
            div[class*="st-key-weight_period_btn_"] button[data-testid="stBaseButton-primary"],
            div[class*="st-key-target_level_btn_"] button[data-testid="stBaseButton-primary"] {
                border-color: #123f73 !important;
                background: linear-gradient(180deg,#174f8d 0%,#123f73 100%) !important;
                color: #ffffff !important;
                box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 2px 5px rgba(15,42,67,.18) !important;
            }

            /* ---------------------------------------------------------
               Period selector selected colors
               0 = Daily, 1 = Weekly, 2 = Monthly, 3 = Quarterly
               Applies to both Revenue and Weight trend selectors.
               --------------------------------------------------------- */

            /* DAILY - Green */
            .st-key-revenue_period_btn_0 button[data-testid="stBaseButton-primary"],
            .st-key-weight_period_btn_0 button[data-testid="stBaseButton-primary"] {
                border-color: #15803d !important;
                background: linear-gradient(180deg, #22c55e 0%, #16a34a 58%, #15803d 100%) !important;
                color: #ffffff !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.24),
                    0 3px 7px rgba(22,163,74,.26) !important;
            }

            /* WEEKLY - Amber / Orange */
            .st-key-revenue_period_btn_1 button[data-testid="stBaseButton-primary"],
            .st-key-weight_period_btn_1 button[data-testid="stBaseButton-primary"] {
                border-color: #b45309 !important;
                background: linear-gradient(180deg, #f59e0b 0%, #d97706 58%, #b45309 100%) !important;
                color: #ffffff !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.24),
                    0 3px 7px rgba(217,119,6,.28) !important;
            }

            /* MONTHLY - Blue */
            .st-key-revenue_period_btn_2 button[data-testid="stBaseButton-primary"],
            .st-key-weight_period_btn_2 button[data-testid="stBaseButton-primary"] {
                border-color: #1d4ed8 !important;
                background: linear-gradient(180deg, #3b82f6 0%, #2563eb 58%, #1d4ed8 100%) !important;
                color: #ffffff !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.24),
                    0 3px 7px rgba(37,99,235,.28) !important;
            }

            /* QUARTERLY - Purple */
            .st-key-revenue_period_btn_3 button[data-testid="stBaseButton-primary"],
            .st-key-weight_period_btn_3 button[data-testid="stBaseButton-primary"] {
                border-color: #6d28d9 !important;
                background: linear-gradient(180deg, #8b5cf6 0%, #7c3aed 58%, #6d28d9 100%) !important;
                color: #ffffff !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.24),
                    0 3px 7px rgba(124,58,237,.28) !important;
            }

            /* Keep selected text white for every period */
            .st-key-revenue_period_btn_0 button[data-testid="stBaseButton-primary"] p,
            .st-key-revenue_period_btn_0 button[data-testid="stBaseButton-primary"] span,
            .st-key-revenue_period_btn_1 button[data-testid="stBaseButton-primary"] p,
            .st-key-revenue_period_btn_1 button[data-testid="stBaseButton-primary"] span,
            .st-key-revenue_period_btn_2 button[data-testid="stBaseButton-primary"] p,
            .st-key-revenue_period_btn_2 button[data-testid="stBaseButton-primary"] span,
            .st-key-revenue_period_btn_3 button[data-testid="stBaseButton-primary"] p,
            .st-key-revenue_period_btn_3 button[data-testid="stBaseButton-primary"] span,
            .st-key-weight_period_btn_0 button[data-testid="stBaseButton-primary"] p,
            .st-key-weight_period_btn_0 button[data-testid="stBaseButton-primary"] span,
            .st-key-weight_period_btn_1 button[data-testid="stBaseButton-primary"] p,
            .st-key-weight_period_btn_1 button[data-testid="stBaseButton-primary"] span,
            .st-key-weight_period_btn_2 button[data-testid="stBaseButton-primary"] p,
            .st-key-weight_period_btn_2 button[data-testid="stBaseButton-primary"] span,
            .st-key-weight_period_btn_3 button[data-testid="stBaseButton-primary"] p,
            .st-key-weight_period_btn_3 button[data-testid="stBaseButton-primary"] span {
                color: #ffffff !important;
            }

            div[class*="st-key-revenue_period_btn_"] button p,
            div[class*="st-key-revenue_period_btn_"] button span,
            div[class*="st-key-weight_period_btn_"] button p,
            div[class*="st-key-weight_period_btn_"] button span,
            div[class*="st-key-target_level_btn_"] button p,
            div[class*="st-key-target_level_btn_"] button span {
                margin: 0 !important;
                padding: 0 !important;
                font-size: 11px !important;
                font-weight: 650 !important;
                color: inherit !important;
                white-space: nowrap !important;
            }

            .checkbox-slicer-label {
                display: block;
                min-height: 22px;
                margin: 0 0 2px 2px;
                padding: 0;
                line-height: 22px;
                color: #243b53;
                font-size: 10px;
                font-family: "Segoe UI", Arial, sans-serif;
                font-weight: 400;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            div[data-testid="stPopover"] {
                width: 100% !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            div[data-testid="stPopover"] > div {
                width: 100% !important;
            }

            div[data-testid="stPopover"] > div > button {
                width: 100% !important;
                min-height: 40px !important;
                height: 40px !important;
                padding: 0 9px !important;
                margin: 0 !important;
                border: 1px solid #cbd9ea !important;
                border-radius: 10px !important;
                background: linear-gradient(180deg, #ffffff 0%, #f5f8fc 100%) !important;
                box-shadow: inset 0 1px 2px rgba(15,23,42,.06) !important;
                color: #102a43 !important;
                font-size: 11px !important;
                font-weight: 800 !important;
                justify-content: space-between !important;
                transform: none !important;
            }

            div[data-testid="stPopover"] > div > button:hover,
            div[data-testid="stPopover"] > div > button:focus {
                border-color: #cbd9ea !important;
                background: linear-gradient(180deg, #ffffff 0%, #f5f8fc 100%) !important;
                box-shadow: inset 0 1px 2px rgba(15,23,42,.06) !important;
                transform: none !important;
            }

            div[data-testid="stPopoverBody"] {
                max-height: 360px !important;
                overflow-y: auto !important;
            }

            @media (max-width: 1500px) {
                .checkbox-slicer-label {
                    min-height: 21px !important;
                    line-height: 21px !important;
                    font-size: 9px !important;
                }
                div[data-testid="stPopover"] > div > button {
                    min-height: 38px !important;
                    height: 38px !important;
                    padding-left: 7px !important;
                    padding-right: 6px !important;
                    font-size: 10px !important;
                }
            }

            .st-key-branch_achievement_top_n div[data-testid="stSelectbox"] > label,
            .st-key-branch_achievement_top_n div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
                display: none !important;
                min-height: 0 !important;
                height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                line-height: 0 !important;
                overflow: hidden !important;
            }

            .st-key-branch_achievement_top_n div[data-testid="stSelectbox"] {
                gap: 0 !important;
                margin: 0 !important;
            }

            /* Consistent small breathing room between dashboard rows. */
            div[data-testid="stHorizontalBlock"] {
                margin-bottom: 6px !important;
            }

            /* Bordered visual cards get a little extra vertical separation. */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                margin-top: 1px !important;
                margin-bottom: 2px !important;
                box-sizing: border-box !important;
            }

            div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"]) {
                gap: 16px !important;
                column-gap: 16px !important;
                margin-top: 1px !important;
                margin-bottom: 1px !important;
            }

            div[data-testid="stHorizontalBlock"]:has(div[data-testid="stVerticalBlockBorderWrapper"])
            > div[data-testid="stColumn"] {
                padding-left: 2px !important;
                padding-right: 2px !important;
                box-sizing: border-box !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stPlotlyChart"] {
                margin-top: 3px !important;
                margin-bottom: 5px !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stDataFrame"] {
                margin-bottom: 5px !important;
            }

            @media (max-width: 1500px) {
                div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"]) {
                    gap: 12px !important;
                    column-gap: 12px !important;
                    margin-bottom: 2px !important;
                }
                div[data-testid="stVerticalBlockBorderWrapper"] {
                    margin-bottom: 2px !important;
                }
            }

            @media (max-width: 1180px) {
                .checkbox-slicer-label {
                    font-size: 8.5px !important;
                }
                div[data-testid="stPopover"] > div > button {
                    min-height: 36px !important;
                    height: 36px !important;
                    padding-left: 6px !important;
                    padding-right: 5px !important;
                    font-size: 9px !important;
                }
            }

            div[data-testid="stVerticalBlock"]:has(.checkbox-slicer-label) {
                gap: 0 !important;
            }

            div[data-testid="stElementContainer"]:has(.checkbox-slicer-label) {
                min-height: 31px !important;
                height: 31px !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow: visible !important;
            }

            .checkbox-slicer-label {
                height: 22px !important;
                min-height: 22px !important;
                margin: 0 0 9px 2px !important;
                line-height: 22px !important;
            }

            div[data-testid="stVerticalBlock"]:has(.checkbox-slicer-label) div[data-testid="stPopover"] {
                margin: 0 !important;
                padding: 0 !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stButton"] {
                width: auto !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stButton"] > button {
                width: auto !important;
                min-width: 0 !important;
                min-height: 26px !important;
                height: 26px !important;
                padding: 2px 8px !important;
                margin: 0 !important;
                border: 1px solid #dbe4ef !important;
                border-radius: 6px !important;
                background: #ffffff !important;
                color: #2563eb !important;
                box-shadow: none !important;
                transform: none !important;
                font-size: 10px !important;
                font-weight: 600 !important;
                line-height: 1 !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stButton"] > button:hover {
                border-color: #93c5fd !important;
                background: #eff6ff !important;
                color: #1d4ed8 !important;
                box-shadow: none !important;
                transform: none !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stTextInput"] {
                margin: 0 0 7px 0 !important;
                padding: 0 !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stTextInput"] input {
                min-height: 32px !important;
                height: 32px !important;
                padding: 5px 9px !important;
                border: 1px solid #cbd9ea !important;
                border-radius: 7px !important;
                background: #ffffff !important;
                font-size: 11px !important;
                color: #102a43 !important;
                box-shadow: inset 0 1px 2px rgba(15,23,42,.05) !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stTextInput"] input:focus {
                border-color: #60a5fa !important;
                box-shadow: 0 0 0 2px rgba(37,99,235,.10) !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stMultiSelect"] {
                margin-top: 7px !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
                min-height: 36px !important;
                border: 1px solid #cbd9ea !important;
                border-radius: 8px !important;
                background: #ffffff !important;
                box-shadow: inset 0 1px 2px rgba(15,23,42,.05) !important;
            }

            div[data-testid="stPopoverBody"] div[data-testid="stButton"] > button p {
                margin: 0 !important;
                padding: 0 !important;
                color: inherit !important;
                font-size: 10px !important;
                font-weight: 600 !important;
                line-height: 1 !important;
                white-space: nowrap !important;
            }

            @media (min-width: 1800px) {
                div[data-testid="stElementContainer"]:has(.checkbox-slicer-label) {
                    min-height: 31px !important;
                    height: 31px !important;
                }
                .checkbox-slicer-label {
                    height: 22px !important;
                    min-height: 22px !important;
                    line-height: 22px !important;
                    margin-bottom: 9px !important;
                    font-size: 11px !important;
                }
            }

            @media (max-width: 1500px) {
                div[data-testid="stElementContainer"]:has(.checkbox-slicer-label) {
                    min-height: 29px !important;
                    height: 29px !important;
                }
                .checkbox-slicer-label {
                    height: 21px !important;
                    min-height: 21px !important;
                    line-height: 21px !important;
                    margin-bottom: 8px !important;
                    font-size: 9px !important;
                }
            }

            @media (max-width: 1180px) {
                div[data-testid="stElementContainer"]:has(.checkbox-slicer-label) {
                    min-height: 29px !important;
                    height: 29px !important;
                }
                .checkbox-slicer-label {
                    height: 21px !important;
                    min-height: 21px !important;
                    line-height: 21px !important;
                    margin-bottom: 8px !important;
                    font-size: 8.5px !important;
                }
            }


            /* =========================================================
               OVERVIEW FILTER BOXES - PROFESSIONAL BLUE STYLE
               Applied consistently to ALL selectboxes and slicer boxes.
               ========================================================= */

            /* Native selectbox container */
            div[data-testid="stSelectbox"] {
                background: transparent !important;
                border: 0 !important;
                box-shadow: none !important;
                padding: 0 !important;
                transform: none !important;
            }

            /* Native selectbox control */
            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                min-height: 40px !important;
                height: 40px !important;
                padding: 0 8px !important;
                border: 1px solid #a9bfd8 !important;
                border-radius: 9px !important;
                background: linear-gradient(
                    180deg,
                    #f9fbfe 0%,
                    #eef4fa 58%,
                    #e4edf7 100%
                ) !important;
                color: #173b63 !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.95),
                    0 2px 5px rgba(30,64,105,.10) !important;
            }

            div[data-testid="stSelectbox"] div[data-baseweb="select"] span {
                color: #173b63 !important;
                font-weight: 700 !important;
            }

            div[data-testid="stSelectbox"] div[data-baseweb="select"] svg {
                color: #376d9f !important;
                background: #e2edf8 !important;
                border-radius: 5px !important;
            }

            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
            div[data-testid="stSelectbox"]:focus-within div[data-baseweb="select"] > div {
                border-color: #6f99c4 !important;
                background: linear-gradient(
                    180deg,
                    #ffffff 0%,
                    #edf5fd 55%,
                    #dfeaf6 100%
                ) !important;
                box-shadow:
                    0 0 0 2px rgba(71,120,166,.10),
                    0 3px 7px rgba(30,64,105,.13) !important;
            }

            /* Checkbox slicer / popover filter trigger */
            div[data-testid="stPopover"] > div > button {
                min-height: 40px !important;
                height: 40px !important;
                padding: 0 9px !important;
                border: 1px solid #a9bfd8 !important;
                border-radius: 9px !important;
                background: linear-gradient(
                    180deg,
                    #f9fbfe 0%,
                    #eef4fa 58%,
                    #e4edf7 100%
                ) !important;
                color: #173b63 !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.95),
                    0 2px 5px rgba(30,64,105,.10) !important;
                transform: none !important;
            }

            div[data-testid="stPopover"] > div > button p,
            div[data-testid="stPopover"] > div > button span {
                color: #173b63 !important;
                font-weight: 700 !important;
            }

            div[data-testid="stPopover"] > div > button svg {
                color: #376d9f !important;
            }

            div[data-testid="stPopover"] > div > button:hover,
            div[data-testid="stPopover"] > div > button:focus {
                border-color: #6f99c4 !important;
                background: linear-gradient(
                    180deg,
                    #ffffff 0%,
                    #edf5fd 55%,
                    #dfeaf6 100%
                ) !important;
                color: #173b63 !important;
                box-shadow:
                    0 0 0 2px rgba(71,120,166,.10),
                    0 3px 7px rgba(30,64,105,.13) !important;
                transform: none !important;
            }

            /* Dropdown option list stays clean and professional */
            div[data-baseweb="popover"] ul {
                background: #ffffff !important;
                border: 1px solid #c5d3e2 !important;
                border-radius: 10px !important;
                box-shadow: 0 12px 26px rgba(30,64,105,.16) !important;
            }

            div[data-baseweb="popover"] li {
                background: #ffffff !important;
                color: #173b63 !important;
            }

            div[data-baseweb="popover"] li:hover {
                background: #eaf2fa !important;
                color: #12395f !important;
            }


            /* =========================================================
               TOP NATIVE FILTERS = SAME DESIGN AS SLICER FILTERS
               Version 8.6.5
               View Type, Financial Year, Company, Load Type, Conversion
               ========================================================= */

            .st-key-overview_view_type div[data-testid="stSelectbox"],
            .st-key-overview_fy div[data-testid="stSelectbox"],
            .st-key-overview_company div[data-testid="stSelectbox"],
            .st-key-overview_loadtype div[data-testid="stSelectbox"],
            .st-key-overview_conversion_type div[data-testid="stSelectbox"] {
                display: flex !important;
                flex-direction: column !important;
                gap: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                border: 0 !important;
                border-radius: 0 !important;
                background: transparent !important;
                box-shadow: none !important;
                transform: none !important;
                overflow: visible !important;
            }

            /* Same heading typography/spacing as checkbox-slicer-label */
            .st-key-overview_view_type div[data-testid="stSelectbox"] > label,
            .st-key-overview_view_type div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
            .st-key-overview_fy div[data-testid="stSelectbox"] > label,
            .st-key-overview_fy div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
            .st-key-overview_company div[data-testid="stSelectbox"] > label,
            .st-key-overview_company div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
            .st-key-overview_loadtype div[data-testid="stSelectbox"] > label,
            .st-key-overview_loadtype div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
            .st-key-overview_conversion_type div[data-testid="stSelectbox"] > label,
            .st-key-overview_conversion_type div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] {
                display: block !important;
                height: 22px !important;
                min-height: 22px !important;
                line-height: 22px !important;
                margin: 0 0 9px 2px !important;
                padding: 0 !important;
                color: #243b53 !important;
                font-family: "Segoe UI", Arial, sans-serif !important;
                font-size: 10px !important;
                font-weight: 400 !important;
                letter-spacing: 0 !important;
                white-space: nowrap !important;
            }

            .st-key-overview_view_type div[data-testid="stSelectbox"] label p,
            .st-key-overview_fy div[data-testid="stSelectbox"] label p,
            .st-key-overview_company div[data-testid="stSelectbox"] label p,
            .st-key-overview_loadtype div[data-testid="stSelectbox"] label p,
            .st-key-overview_conversion_type div[data-testid="stSelectbox"] label p {
                margin: 0 !important;
                padding: 0 !important;
                font-size: 10px !important;
                font-weight: 400 !important;
                line-height: 22px !important;
                color: #243b53 !important;
            }

            /* Match popover trigger: exact same size, fill, border, radius and shadow */
            .st-key-overview_view_type div[data-baseweb="select"] > div,
            .st-key-overview_fy div[data-baseweb="select"] > div,
            .st-key-overview_company div[data-baseweb="select"] > div,
            .st-key-overview_loadtype div[data-baseweb="select"] > div,
            .st-key-overview_conversion_type div[data-baseweb="select"] > div {
                width: 100% !important;
                min-height: 40px !important;
                height: 40px !important;
                padding: 0 9px !important;
                margin: 0 !important;
                border: 1px solid #a9bfd8 !important;
                border-radius: 9px !important;
                background: linear-gradient(
                    180deg,
                    #f9fbfe 0%,
                    #eef4fa 58%,
                    #e4edf7 100%
                ) !important;
                box-shadow:
                    inset 0 1px 0 rgba(255,255,255,.95),
                    0 2px 5px rgba(30,64,105,.10) !important;
                color: #173b63 !important;
                transform: none !important;
            }

            /* Remove Streamlit/BaseWeb grey inner layers */
            .st-key-overview_view_type div[data-baseweb="select"] > div > div,
            .st-key-overview_view_type div[data-baseweb="select"] > div > div > div,
            .st-key-overview_fy div[data-baseweb="select"] > div > div,
            .st-key-overview_fy div[data-baseweb="select"] > div > div > div,
            .st-key-overview_company div[data-baseweb="select"] > div > div,
            .st-key-overview_company div[data-baseweb="select"] > div > div > div,
            .st-key-overview_loadtype div[data-baseweb="select"] > div > div,
            .st-key-overview_loadtype div[data-baseweb="select"] > div > div > div,
            .st-key-overview_conversion_type div[data-baseweb="select"] > div > div,
            .st-key-overview_conversion_type div[data-baseweb="select"] > div > div > div {
                background: transparent !important;
                box-shadow: none !important;
            }

            /* Same value text as slicers: normal weight, same size */
            .st-key-overview_view_type div[data-baseweb="select"] span,
            .st-key-overview_fy div[data-baseweb="select"] span,
            .st-key-overview_company div[data-baseweb="select"] span,
            .st-key-overview_loadtype div[data-baseweb="select"] span,
            .st-key-overview_conversion_type div[data-baseweb="select"] span {
                color: #173b63 !important;
                font-family: "Segoe UI", Arial, sans-serif !important;
                font-size: 10px !important;
                font-weight: 400 !important;
                line-height: 1 !important;
            }

            /* Same blue arrow treatment */
            .st-key-overview_view_type div[data-baseweb="select"] svg,
            .st-key-overview_fy div[data-baseweb="select"] svg,
            .st-key-overview_company div[data-baseweb="select"] svg,
            .st-key-overview_loadtype div[data-baseweb="select"] svg,
            .st-key-overview_conversion_type div[data-baseweb="select"] svg {
                width: 15px !important;
                height: 15px !important;
                padding: 0 !important;
                border-radius: 0 !important;
                background: transparent !important;
                color: #376d9f !important;
            }

            .st-key-overview_view_type div[data-baseweb="select"] > div:hover,
            .st-key-overview_view_type div[data-testid="stSelectbox"]:focus-within div[data-baseweb="select"] > div,
            .st-key-overview_fy div[data-baseweb="select"] > div:hover,
            .st-key-overview_fy div[data-testid="stSelectbox"]:focus-within div[data-baseweb="select"] > div,
            .st-key-overview_company div[data-baseweb="select"] > div:hover,
            .st-key-overview_company div[data-testid="stSelectbox"]:focus-within div[data-baseweb="select"] > div,
            .st-key-overview_loadtype div[data-baseweb="select"] > div:hover,
            .st-key-overview_loadtype div[data-testid="stSelectbox"]:focus-within div[data-baseweb="select"] > div,
            .st-key-overview_conversion_type div[data-baseweb="select"] > div:hover,
            .st-key-overview_conversion_type div[data-testid="stSelectbox"]:focus-within div[data-baseweb="select"] > div {
                border-color: #6f99c4 !important;
                background: linear-gradient(
                    180deg,
                    #ffffff 0%,
                    #edf5fd 55%,
                    #dfeaf6 100%
                ) !important;
                box-shadow:
                    0 0 0 2px rgba(71,120,166,.10),
                    0 3px 7px rgba(30,64,105,.13) !important;
            }

            /* Keep exact same sizing at responsive widths too */
            @media (max-width: 1500px) {
                .st-key-overview_view_type div[data-baseweb="select"] > div,
                .st-key-overview_fy div[data-baseweb="select"] > div,
                .st-key-overview_company div[data-baseweb="select"] > div,
                .st-key-overview_loadtype div[data-baseweb="select"] > div,
                .st-key-overview_conversion_type div[data-baseweb="select"] > div {
                    min-height: 38px !important;
                    height: 38px !important;
                }

                .st-key-overview_view_type div[data-testid="stSelectbox"] > label,
                .st-key-overview_fy div[data-testid="stSelectbox"] > label,
                .st-key-overview_company div[data-testid="stSelectbox"] > label,
                .st-key-overview_loadtype div[data-testid="stSelectbox"] > label,
                .st-key-overview_conversion_type div[data-testid="stSelectbox"] > label {
                    height: 21px !important;
                    min-height: 21px !important;
                    line-height: 21px !important;
                    margin-bottom: 8px !important;
                    font-size: 9px !important;
                }

                .st-key-overview_view_type div[data-baseweb="select"] span,
                .st-key-overview_fy div[data-baseweb="select"] span,
                .st-key-overview_company div[data-baseweb="select"] span,
                .st-key-overview_loadtype div[data-baseweb="select"] span,
                .st-key-overview_conversion_type div[data-baseweb="select"] span {
                    font-size: 10px !important;
                    font-weight: 400 !important;
                }
            }


            /* Compact Target Meter card */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[data-testid="stPlotlyChart"]
            ) {
                overflow: hidden !important;
            }

            .st-key-target_meter_compact div[data-testid="stVerticalBlockBorderWrapper"] > div {
                padding: .35rem .50rem .30rem !important;
            }


            /* =========================================================
               COMPACT BUSINESS + WEIGHT TREND LAYOUT - VERSION 8.7.0
               ========================================================= */

            /* Less vertical gap between dashboard rows */
            div[data-testid="stHorizontalBlock"] {
                margin-bottom: 2px !important;
            }

            div[data-testid="stHorizontalBlock"]:has(
                div[class*="st-key-revenue_period_btn_"]
            ),
            div[data-testid="stHorizontalBlock"]:has(
                div[class*="st-key-weight_period_btn_"]
            ) {
                margin-top: 0 !important;
                margin-bottom: 2px !important;
            }

            /* Tight chart-card padding */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[class*="st-key-revenue_period_btn_"]
            ) > div,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[class*="st-key-weight_period_btn_"]
            ) > div {
                padding-top: .38rem !important;
                padding-bottom: .30rem !important;
            }

            /* Reduce Plotly whitespace inside trend cards */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[class*="st-key-revenue_period_btn_"]
            ) div[data-testid="stPlotlyChart"],
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[class*="st-key-weight_period_btn_"]
            ) div[data-testid="stPlotlyChart"] {
                margin-top: -2px !important;
                margin-bottom: 0 !important;
            }

            /* Compact Daily / Weekly / Monthly / Quarterly controls */
            div[class*="st-key-revenue_period_btn_"] button,
            div[class*="st-key-weight_period_btn_"] button {
                min-height: 30px !important;
                height: 30px !important;
                padding: 2px 7px !important;
                border-radius: 7px !important;
            }

            div[class*="st-key-revenue_period_btn_"] button p,
            div[class*="st-key-revenue_period_btn_"] button span,
            div[class*="st-key-weight_period_btn_"] button p,
            div[class*="st-key-weight_period_btn_"] button span {
                font-size: 9.5px !important;
            }


            /* =========================================================
               TREND ROW GAP REDUCTION - VERSION 8.7.1
               ========================================================= */

            /* Remove extra bottom space after the Business Trend row */
            div[data-testid="stHorizontalBlock"]:has(
                div[class*="st-key-revenue_period_btn_"]
            ) {
                margin-bottom: 0 !important;
                padding-bottom: 0 !important;
            }

            /* Remove extra top space before the Weight Trend row */
            div[data-testid="stHorizontalBlock"]:has(
                div[class*="st-key-weight_period_btn_"]
            ) {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

            /* Trend cards themselves should not add exterior vertical margin */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[class*="st-key-revenue_period_btn_"]
            ),
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[class*="st-key-weight_period_btn_"]
            ) {
                margin-top: 0 !important;
                margin-bottom: 1px !important;
            }

            /* If Streamlit inserts an empty spacer/element container between rows,
               collapse it as much as possible. */
            div[data-testid="stElementContainer"]:empty {
                min-height: 0 !important;
                height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            /* Keep the outer vertical layout compact around trend sections */
            div[data-testid="stVerticalBlock"]:has(
                div[class*="st-key-revenue_period_btn_"]
            ),
            div[data-testid="stVerticalBlock"]:has(
                div[class*="st-key-weight_period_btn_"]
            ) {
                gap: 0.15rem !important;
            }


            /* 8.7.2: let the taller Business Trend fill the row instead of leaving a blank band. */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(
                div[class*="st-key-revenue_period_btn_"]
            ) div[data-testid="stPlotlyChart"] {
                min-height: 420px !important;
            }

            /* Keep Weight Trend immediately after the preceding row. */
            div[data-testid="stHorizontalBlock"]:has(
                div[class*="st-key-weight_period_btn_"]
            ) {
                margin-top: -1px !important;
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
    Returns columns: Period, Business Cr, Prev Business Cr, Growth %, Growth Label
    """
    required = [c for c in [date_col, "REVENUE", "FIN_MONTH"] if c in current_df.columns]
    cur = current_df[required].copy()
    prev = (
        previous_df[[c for c in [date_col, "REVENUE", "FIN_MONTH"] if c in previous_df.columns]].copy()
        if previous_df is not None and not previous_df.empty
        else pd.DataFrame()
    )

    if date_col in cur.columns and not pd.api.types.is_datetime64_any_dtype(cur[date_col]):
        cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty and date_col in prev.columns and not pd.api.types.is_datetime64_any_dtype(prev[date_col]):
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

    else:           
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

    trend_df["Business Cr"] = (trend_df["REVENUE"] / 10000000).round(2)

    if not prev_trend.empty:
        prev_trend["Prev Business Cr"] = (prev_trend["PREV_REVENUE"] / 10000000).round(2)
        trend_df = trend_df.merge(prev_trend[["Key", "Prev Business Cr"]], on="Key", how="left")
    else:
        trend_df["Prev Business Cr"] = None

    trend_df["Growth %"] = trend_df.apply(
        lambda r: pct_growth(r["Business Cr"], r["Prev Business Cr"]) if pd.notna(r["Prev Business Cr"]) else None,
        axis=1
    )
    trend_df["Growth Label"] = trend_df["Growth %"].apply(lambda x: growth_label(x) if pd.notna(x) else "N/A")

    return trend_df

def build_weight_yoy_trend(current_df, previous_df, trend_type, date_col, fy_start, prev_fy_start, month_map):
    """Build Current-FY vs LY weight trend in MT for Daily/Weekly/Monthly/Quarterly views."""
    required = [c for c in [date_col, "aweight", "FIN_MONTH"] if c in current_df.columns]
    cur = current_df[required].copy()
    prev = (
        previous_df[[c for c in [date_col, "aweight", "FIN_MONTH"] if c in previous_df.columns]].copy()
        if previous_df is not None and not previous_df.empty
        else pd.DataFrame()
    )

    if date_col in cur.columns and not pd.api.types.is_datetime64_any_dtype(cur[date_col]):
        cur[date_col] = pd.to_datetime(cur[date_col], errors="coerce")
    if not prev.empty and date_col in prev.columns and not pd.api.types.is_datetime64_any_dtype(prev[date_col]):
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

    else:           
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

def create_card(
    title, value, color, icon, growth_value=0.0, previous_value=None,
    target_value=None, target_achievement=None
):
    """Render a compact KPI card with LY value, optional target/achievement, and YoY growth."""
    positive = growth_value >= 0
    growth_color = "#15803d" if positive else "#dc2626"
    growth_bg = "#ffffff"
    growth_border = "#86efac" if positive else "#fda4af"
    growth_text = growth_label(growth_value)
    previous_text = previous_value if previous_value is not None else "N/A"

    target_achievement_text = (
        f" / {target_achievement:.1f}%"
        if target_achievement is not None and pd.notna(target_achievement)
        else ""
    )
    target_html = (
        f'<div style="position:relative;z-index:1;margin-top:3px;font-size:9px;font-weight:800;'
        f'color:#c2410c;line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'Target: {target_value}{target_achievement_text}</div>'
        if target_value is not None else ""
    )

    html = (
        f'<div class="kpi-3d-card" style="--kpi-accent:{color};">'
        f'<div class="kpi-3d-gloss"></div>'
        f'<div class="kpi-3d-topline"></div>'
        f'<div class="kpi-3d-head">'
        f'<div class="kpi-3d-title">{title}</div>'
        f'<div class="kpi-3d-icon">{icon}</div>'
        f'</div>'
        f'<div class="kpi-3d-value">{value}</div>'
        f'{target_html}'
        f'<div class="kpi-3d-footer">'
        f'<span class="kpi-3d-ly">LY: {previous_text}</span>'
        f'<span class="kpi-3d-growth" '
        f'style="background:{growth_bg};border-color:{growth_border};color:{growth_color};">'
        f'{growth_text}'
        f'</span>'
        f'</div>'
        f'</div>'
    )

    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)

def create_target_speedometer(actual, target, unit="", title="Target Achievement", compact=False):
    """Render a compact target-achievement meter that stays fully inside its card."""
    actual = float(actual or 0)
    target = float(target or 0)
    achievement = (actual / target * 100) if target > 0 else 0.0
    gauge_value = min(max(achievement, 0.0), 150.0)

    if target <= 0:
        status_text = "Target not set"
        status_color = "#64748b"
        status_bg = "#f1f5f9"
    elif achievement >= 100:
        status_text = "Target achieved"
        status_color = "#15803d"
        status_bg = "#dcfce7"
    elif achievement >= 80:
        status_text = "Near target"
        status_color = "#b45309"
        status_bg = "#fef3c7"
    else:
        status_text = "Below target"
        status_color = "#dc2626"
        status_bg = "#fee2e2"

    # One compact summary row.
    st.markdown(
        (
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;'
            'align-items:start;margin:4px 4px 4px 4px;line-height:1.15;">'
            f'<div style="padding:3px 0 2px 0;">'
            f'<div style="font-size:12px;font-weight:600;color:#31557d;'
            f'margin-bottom:3px;letter-spacing:.1px;">Actual</div>'
            f'<div style="font-size:15px;font-weight:700;color:#0f2744;">'
            f'{actual:,.2f}{unit}</div></div>'
            f'<div style="padding:3px 0 2px 0;text-align:right;">'
            f'<div style="font-size:12px;font-weight:600;color:#31557d;'
            f'margin-bottom:3px;letter-spacing:.1px;">Target</div>'
            f'<div style="font-size:15px;font-weight:700;color:#0f2744;">'
            f'{target:,.2f}{unit}</div></div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=gauge_value,
            domain={"x": [0.08, 0.92], "y": [0.10, 0.96]},
            number={
                "suffix": "%",
                "valueformat": ".1f",
                "font": {
                    "size": 22 if compact else 26,
                    "color": "#0f172a",
                    "family": "Arial",
                },
            },
            gauge={
                "shape": "angular",
                "axis": {
                    "range": [0, 150],
                    "tickmode": "array",
                    "tickvals": [0, 50, 80, 100, 120, 150],
                    "ticktext": ["0", "50", "80", "100", "120", "150"],
                    "tickfont": {
                        "size": 6 if compact else 7,
                        "color": "#64748b",
                    },
                    "tickwidth": 0,
                },
                "bar": {
                    "color": status_color,
                    "thickness": 0.20,
                },
                "bgcolor": "#ffffff",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 80], "color": "#fee2e2"},
                    {"range": [80, 100], "color": "#fef3c7"},
                    {"range": [100, 150], "color": "#dcfce7"},
                ],
                "threshold": {
                    "line": {"color": "#0f172a", "width": 2.5},
                    "thickness": 0.68,
                    "value": 100,
                },
            },
        )
    )

    fig.update_layout(
        height=92 if compact else 118,
        margin=dict(l=2, r=2, t=3, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial"),
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": False,
            "responsive": True,
            "staticPlot": True,
        },
    )

    # Status pill is kept in normal document flow (no negative margin),
    # so it can never fall outside the bordered card.
    st.markdown(
        (
            '<div style="display:flex;justify-content:center;align-items:center;'
            'margin:0 0 1px 0;min-height:22px;">'
            f'<span style="display:inline-flex;align-items:center;justify-content:center;'
            f'padding:3px 9px;border-radius:999px;background:{status_bg};'
            f'color:{status_color};font-size:9.5px;font-weight:600;'
            f'line-height:1;border:1px solid {status_color}33;">{status_text}</span>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def mini_rank_card(rank, name, value, max_value, color, render=True):
    """Build a compact ranked branch row with a wider name area and slimmer bar."""
    pct = min((value / max_value * 100), 100) if max_value else 0
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

                                                                            
    html = (
        f'<div style="margin-bottom:5px;padding:5px 7px;border:1px solid #e5ebf2;'
        f'border-radius:9px;background:#fbfdff;">'
        f'<div style="display:grid;grid-template-columns:25px minmax(185px,230px) '
        f'minmax(55px,.75fr) 58px;align-items:center;gap:7px;">'
        f'<div style="text-align:center;font-size:13px;font-weight:400;color:#486581;">{medal}</div>'
        f'<div title="{escape(str(name))}" style="font-size:11px;font-weight:500;color:#243b53;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{escape(str(name))}</div>'
        f'<div style="height:5px;background:#e8eef5;border-radius:999px;overflow:hidden;'
        f'box-shadow:inset 0 1px 2px rgba(15,23,42,.10);">'
        f'<div style="width:{pct}%;height:5px;background:{color};border-radius:999px;"></div>'
        f'</div>'
        f'<div style="font-size:11px;font-weight:500;color:#102a43;text-align:right;'
        f'white-space:nowrap;">₹{value:.2f}</div>'
        f'</div></div>'
    )
    if render:
        if hasattr(st, "html"):
            st.html(html)
        else:
            st.markdown(html, unsafe_allow_html=True)
    return html

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
    """Render Operational Highlights. SLA calculations remain unchanged."""
    current_col, previous_col, metrics = _build_sla_metrics(current_df, previous_df)

    with st.container(border=True):
        st.markdown(
            "<div style='font-size:16px;font-weight:400;color:#0f2744;margin:1px 0 8px 2px;'>"
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
                f'justify-content:center;background:{metric["icon_bg"]};font-size:15px;'
                f'border:1px solid {metric["accent"]}33;">{metric["icon"]}</div>'
                f'<div style="font-size:12px;font-weight:400;color:#243b53;line-height:1.15;">{metric["label"]}</div>'
                f'<div style="line-height:1.1;">'
                f'<div style="font-size:14px;font-weight:400;color:#102a43;">{current_text}</div>'
                f'<div style="font-size:10px;color:#64748b;">LY {previous_text}</div></div>'
                f'<div style="font-size:11px;font-weight:400;color:{change_color};text-align:right;white-space:nowrap;">'
                f'{arrow} {change_text}</div></div>'
            )

        note = "" if previous_col is not None else (
            "<div style='font-size:10px;color:#94a3b8;margin-top:5px;'>LY SLAStatus unavailable.</div>"
        )
        st.markdown("<div>" + "".join(rows) + note + "</div>", unsafe_allow_html=True)

TARGET_FILE_PATH = (
    Path(__file__).resolve().parents[2]
    / "services"
    / "branch_monthly_targets.csv"
)


def _normalise_target_text(values):
    """Normalise branch text for reliable target-master matching."""
    return (
        values
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )

@st.cache_data(show_spinner=False)
def load_branch_monthly_targets():
    """Load monthly branch-wise LTL and FTL targets stored in lakhs."""
    required_columns = {"BRANCHCODE", "BRANCH", "TARGETLTL", "TARGETFTL"}

    if not TARGET_FILE_PATH.exists():
        raise FileNotFoundError(
            f"Target file not found: {TARGET_FILE_PATH}. "
            "Place branch_monthly_targets.csv inside the services folder."
        )

    target_df = pd.read_csv(TARGET_FILE_PATH, encoding="utf-8-sig")
    target_df.columns = [str(col).strip().upper() for col in target_df.columns]

    missing_columns = sorted(required_columns.difference(target_df.columns))
    if missing_columns:
        raise ValueError(
            "Target CSV is missing required columns: " + ", ".join(missing_columns)
        )

    target_df = target_df[
        ["BRANCHCODE", "BRANCH", "TARGETLTL", "TARGETFTL"]
    ].copy()

    target_df["BRANCHCODE"] = pd.to_numeric(
        target_df["BRANCHCODE"], errors="coerce"
    ).astype("Int64")
    target_df["BRANCH"] = target_df["BRANCH"].fillna("").astype(str).str.strip()
    target_df["BRANCH_KEY"] = _normalise_target_text(target_df["BRANCH"])

    for col in ["TARGETLTL", "TARGETFTL"]:
        target_df[col] = pd.to_numeric(target_df[col], errors="coerce").fillna(0.0)

    target_df = (
        target_df.groupby(
            ["BRANCHCODE", "BRANCH", "BRANCH_KEY"],
            as_index=False,
            dropna=False,
        )[["TARGETLTL", "TARGETFTL"]]
        .sum()
    )
    target_df["TARGETTOTAL"] = target_df["TARGETLTL"] + target_df["TARGETFTL"]
    return target_df

def _find_target_branch_code_column(data):
    """Find a branch-code field in booking data, if one is available."""
    if data is None:
        return None

    normalized = {
        str(col).replace("_", "").replace(" ", "").replace("-", "").casefold(): col
        for col in data.columns
    }
    for candidate in [
        "branchcode", "branchcd", "stationcode", "stationcd",
        "bookingbranchcode", "originbranchcode",
    ]:
        if candidate in normalized:
            return normalized[candidate]
    return None

def _selected_target_months(filtered_df, selected_month, selected_quarter):
    """Return financial months for which monthly targets should be applied."""
    if selected_month != "All":
        return [selected_month]

    available_months = []
    if filtered_df is not None and not filtered_df.empty and "Month" in filtered_df.columns:
        present = set(filtered_df["Month"].dropna().astype(str))
        available_months = [m for m in MONTH_ORDER if m in present]

    if selected_quarter != "All":
        quarter_months = {
            "Q1": ["Apr", "May", "Jun"],
            "Q2": ["Jul", "Aug", "Sep"],
            "Q3": ["Oct", "Nov", "Dec"],
            "Q4": ["Jan", "Feb", "Mar"],
        }.get(selected_quarter, [])
        months_with_actual = [m for m in quarter_months if m in available_months]
        return months_with_actual or quarter_months

    return available_months

def convert_target_lac(target_lac, conversion_type):
    """Convert target stored in lakhs to the dashboard display unit."""
    return float(target_lac or 0) if conversion_type == "Lac" else float(target_lac or 0) / 100

def calculate_branch_target_achievement(
    filtered_df,
    branch_summary,
    selected_month,
    selected_quarter,
    selected_loadtype,
):
    """Return branch-wise actual, target, achievement and variance for active filters."""
    columns = [
        "branch", "Business", "Target_Lac", "Achievement_Pct", "Variance_Rs",
        "Status", "Matched_Target",
    ]
    if filtered_df is None or filtered_df.empty or branch_summary is None or branch_summary.empty:
        return pd.DataFrame(columns=columns), []

    target_master = load_branch_monthly_targets().copy()
    month_list = _selected_target_months(
        filtered_df, selected_month, selected_quarter
    )
    month_multiplier = len(month_list)

    result = branch_summary.copy()
    result["BRANCH_KEY"] = _normalise_target_text(result["branch"])

    branch_code_col = _find_target_branch_code_column(filtered_df)
    if branch_code_col is not None:
        code_map = filtered_df[["branch", branch_code_col]].copy()
        code_map[branch_code_col] = pd.to_numeric(
            code_map[branch_code_col], errors="coerce"
        ).astype("Int64")
        code_map = (
            code_map.dropna(subset=[branch_code_col])
            .drop_duplicates(subset=["branch"], keep="first")
        )
        result = result.merge(code_map, on="branch", how="left")
        result = result.merge(
            target_master[
                ["BRANCHCODE", "TARGETLTL", "TARGETFTL", "TARGETTOTAL"]
            ],
            left_on=branch_code_col,
            right_on="BRANCHCODE",
            how="left",
        )
    else:
        result = result.merge(
            target_master[
                ["BRANCH_KEY", "TARGETLTL", "TARGETFTL", "TARGETTOTAL"]
            ],
            on="BRANCH_KEY",
            how="left",
        )

    for col in ["TARGETLTL", "TARGETFTL", "TARGETTOTAL"]:
        if col not in result.columns:
            result[col] = 0.0
        result[col] = pd.to_numeric(result[col], errors="coerce")

    result["Matched_Target"] = result["TARGETTOTAL"].notna()
    result[["TARGETLTL", "TARGETFTL", "TARGETTOTAL"]] = result[
        ["TARGETLTL", "TARGETFTL", "TARGETTOTAL"]
    ].fillna(0.0)

    loadtype_value = str(selected_loadtype or "All").strip().upper()
    if loadtype_value == "FTL":
        result["Target_Lac"] = result["TARGETFTL"] * month_multiplier
    elif loadtype_value == "LTL":
        result["Target_Lac"] = result["TARGETLTL"] * month_multiplier
    else:
        result["Target_Lac"] = result["TARGETTOTAL"] * month_multiplier

    result["Target_Rs"] = result["Target_Lac"] * 100000.0
    result["Variance_Rs"] = result["Business"] - result["Target_Rs"]
    result["Achievement_Pct"] = result.apply(
        lambda row: (
            row["Business"] / row["Target_Rs"] * 100.0
            if row["Target_Rs"] > 0 else 0.0
        ),
        axis=1,
    )
    result["Status"] = result["Achievement_Pct"].map(
        lambda value: "Achieved" if value >= 100 else ("Near Target" if value >= 80 else "Below Target")
    )

    return result, month_list

def get_monthly_target_for_filtered_branches(filtered_df, selected_loadtype):
    """Return one-month target in lakhs for branches in the filtered dataset."""
    target_master = load_branch_monthly_targets()

    if filtered_df is None or filtered_df.empty:
        return 0.0
    if "branch" not in filtered_df.columns:
        raise ValueError("Booking data does not contain the branch column.")

    actual_branches = filtered_df.copy()
    actual_branches["BRANCH_KEY"] = _normalise_target_text(actual_branches["branch"])
    selected_branch_names = set(
        actual_branches.loc[actual_branches["BRANCH_KEY"].ne(""), "BRANCH_KEY"]
    )

    branch_code_col = _find_target_branch_code_column(actual_branches)
    selected_branch_codes = set()
    if branch_code_col is not None:
        selected_branch_codes = set(
            pd.to_numeric(actual_branches[branch_code_col], errors="coerce")
            .dropna()
            .astype(int)
        )

    if selected_branch_codes:
        matched = target_master[
            target_master["BRANCHCODE"].isin(selected_branch_codes)
        ].copy()
    else:
        matched = target_master[
            target_master["BRANCH_KEY"].isin(selected_branch_names)
        ].copy()

    loadtype_value = str(selected_loadtype or "All").strip().upper()
    if loadtype_value == "LTL":
        return float(matched["TARGETLTL"].sum())
    if loadtype_value == "FTL":
        return float(matched["TARGETFTL"].sum())
    return float(matched["TARGETTOTAL"].sum())

def build_target_trend(
    filtered_df,
    trend_type,
    date_col,
    monthly_target_lac,
    conversion_type,
    month_map,
):
    """Build target values aligned with Daily/Weekly/Monthly/Quarterly trend periods."""
    if filtered_df is None or filtered_df.empty or date_col not in filtered_df.columns:
        return pd.DataFrame(columns=["Period", "Target"])

    data = filtered_df[[date_col, "FIN_MONTH"]].copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
    data = data.dropna(subset=[date_col]).drop_duplicates(subset=[date_col])
    if data.empty:
        return pd.DataFrame(columns=["Period", "Target"])

    display_target = convert_target_lac(monthly_target_lac, conversion_type)

    if trend_type == "Daily":
        result = data[[date_col]].copy()
        result["Period"] = result[date_col].dt.date
        result["Target"] = display_target / result[date_col].dt.days_in_month
        return result[["Period", "Target"]].groupby("Period", as_index=False).sum()

    if trend_type == "Weekly":
        result = data[[date_col]].copy()
        result["Week"] = result[date_col].dt.to_period("W")
        result["Target"] = display_target / result[date_col].dt.days_in_month
        result = result.groupby("Week", as_index=False)["Target"].sum()
        result["Period"] = result["Week"].astype(str)
        return result[["Period", "Target"]]

    if trend_type == "Quarterly":
        result = data[["FIN_MONTH"]].dropna().drop_duplicates().copy()
        result["Quarter"] = result["FIN_MONTH"].map(QUARTER_MAP)
        result = result.dropna(subset=["Quarter"])
        result = result.groupby("Quarter", as_index=False).size()
        result["Target"] = result["size"] * display_target
        result["Period"] = result["Quarter"]
        return result[["Period", "Target"]]

    result = data[["FIN_MONTH"]].dropna().drop_duplicates().copy()
    result["Period"] = result["FIN_MONTH"].map(month_map)
    result = result.dropna(subset=["Period"])
    result["Target"] = display_target
    return result[["Period", "Target"]]

def _checkbox_slicer(label, options, key, locked_values=None, searchable=False):
    """Checkbox-style dropdown with optional instant client-side search.

    Empty selection means All. Circle and Branch use Streamlit's native multiselect
    inside the popover because its option search filters immediately while typing,
    without requiring Enter. Non-searchable slicers keep the existing checkbox UI.
    """
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
                st.checkbox(
                    str(value),
                    value=True,
                    disabled=True,
                    key=f"{key}__locked__{value}",
                )
        return locked_values

    def state_key(value):
        return f"{key}__item__{str(value)}"

                                                                           
    if searchable:
        selection_key = f"{key}__instant_selected"

        legacy_selected = [
            value for value in options
            if st.session_state.get(state_key(value), False)
        ]
        if selection_key not in st.session_state:
            st.session_state[selection_key] = legacy_selected
        else:
            st.session_state[selection_key] = [
                value for value in st.session_state.get(selection_key, [])
                if value in options
            ]

        selected_before = st.session_state.get(selection_key, [])
        if not selected_before:
            summary = "All"
        elif len(selected_before) == 1:
            summary = str(selected_before[0])
        else:
            summary = f"{len(selected_before)} selected"

        with st.popover(summary, use_container_width=True):
            action_cols = st.columns(2, gap="small")
            with action_cols[0]:
                if st.button(
                    "Select all",
                    key=f"{key}__select_all",
                    use_container_width=False,
                ):
                    st.session_state[selection_key] = list(options)
                    st.rerun()

            with action_cols[1]:
                if st.button(
                    "Clear",
                    key=f"{key}__clear",
                    use_container_width=False,
                ):
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

    selected_before = [
        value for value in options
        if st.session_state.get(state_key(value), False)
    ]

    if not selected_before:
        summary = "All"
    elif len(selected_before) == 1:
        summary = str(selected_before[0])
    else:
        summary = f"{len(selected_before)} selected"

    with st.popover(summary, use_container_width=True):
        action_cols = st.columns(2, gap="small")
        with action_cols[0]:
            if st.button(
                "Select all",
                key=f"{key}__select_all",
                use_container_width=False,
            ):
                for value in options:
                    st.session_state[state_key(value)] = True
                st.rerun()

        with action_cols[1]:
            if st.button(
                "Clear",
                key=f"{key}__clear",
                use_container_width=False,
            ):
                for value in options:
                    st.session_state[state_key(value)] = False
                st.rerun()

        if not options:
            st.caption("No values available")
        else:
            for value in options:
                st.checkbox(str(value), key=state_key(value))

    return [
        value for value in options
        if st.session_state.get(state_key(value), False)
    ]

def _button_selector(options, state_key, key_prefix, default):
    selected = st.session_state.get(state_key, default)
    if selected not in options:
        selected = default
        st.session_state[state_key] = default

    cols = st.columns(len(options), gap="small")
    for idx, option in enumerate(options):
        with cols[idx]:
            if st.button(
                option,
                key=f"{key_prefix}_{idx}",
                type="primary" if selected == option else "secondary",
                use_container_width=True,
            ):
                st.session_state[state_key] = option
                st.rerun()
    return selected

def show_overview():
    """Compact overview dashboard page."""

    _inject_overview_css()

                                                                    
    with st.container(border=True):
        header_left, header_right = st.columns([7, 1], gap="small", vertical_alignment="center")

        with header_left:

            header_content_placeholder = st.empty()

        with header_right:
            export_placeholder = st.empty()

                                                                        
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

    for _date_col in ["grdt", "deliverydt", "expecteddeliverydt", "lastdespdt"]:
        if _date_col in df.columns and not pd.api.types.is_datetime64_any_dtype(df[_date_col]):
            df[_date_col] = pd.to_datetime(df[_date_col], errors="coerce")
        if prev_df is not None and not prev_df.empty and _date_col in prev_df.columns \
                and not pd.api.types.is_datetime64_any_dtype(prev_df[_date_col]):
            prev_df[_date_col] = pd.to_datetime(prev_df[_date_col], errors="coerce")

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

    company_col = next(
        (col for col in df.columns if str(col).strip().casefold() == "compname"),
        None,
    )
    if company_col is None:
        st.error("Company filter cannot be displayed because the compname column is missing from the booking data.")
        return

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

                                                                             

    # ------------------------------------------------------------------
    # CASCADING HIERARCHY FILTERS
    # Zone -> Circle -> Branch
    #
    # IMPORTANT: each child filter must build its options from the rows
    # allowed by the parent selection. Previously Circle and Branch both
    # used filter_source_df directly, so Branch displayed every branch in
    # the company/FY even when a Zone and Circle had already been selected.
    # ------------------------------------------------------------------
    filter_source_df = df.copy()

    # ZONE
    with filter_cols[3]:
        zone_options = sorted(
            filter_source_df["zone"].dropna().astype(str).str.strip().unique().tolist()
        )
        selected_zones = _checkbox_slicer(
            "◉ Zone",
            zone_options,
            key="overview_zone_slicer",
            locked_values=[locked_zone] if locked_zone else None,
        )

    # CIRCLE options come only from selected/locked Zone(s).
    circle_source_df = filter_source_df.copy()
    if selected_zones:
        circle_source_df = circle_source_df[
            circle_source_df["zone"].isin(selected_zones)
        ]

    with filter_cols[4]:
        circle_options = sorted(
            circle_source_df["circle"].dropna().astype(str).str.strip().unique().tolist()
        )
        selected_circles = _checkbox_slicer(
            "◎ Circle",
            circle_options,
            key="overview_circle_slicer",
            locked_values=[locked_circle] if locked_circle else None,
            searchable=True,
        )

    # BRANCH options come only from selected/locked Zone(s) + Circle(s).
    branch_source_df = circle_source_df.copy()
    if selected_circles:
        branch_source_df = branch_source_df[
            branch_source_df["circle"].isin(selected_circles)
        ]

    with filter_cols[5]:
        branch_options = sorted(
            branch_source_df["branch"].dropna().astype(str).str.strip().unique().tolist()
        )
        selected_branches = _checkbox_slicer(
            "⌂ Branch",
            branch_options,
            key="overview_branch_slicer",
            locked_values=[locked_branch] if locked_branch else None,
            searchable=True,
        )

    # Quarter options follow the selected hierarchy as well.
    period_source_df = branch_source_df.copy()
    if selected_branches:
        period_source_df = period_source_df[
            period_source_df["branch"].isin(selected_branches)
        ]

    with filter_cols[6]:
        available_quarters = [
            q for q in QUARTER_ORDER
            if q in period_source_df["Quarter"].dropna().unique().tolist()
        ]
        selected_quarters = _checkbox_slicer(
            "▦ Quarter",
            available_quarters,
            key="overview_quarter_slicer",
        )

    with filter_cols[7]:
        month_source_df = period_source_df.copy()
        if selected_quarters:
            month_source_df = month_source_df[
                month_source_df["Quarter"].isin(selected_quarters)
            ]

        available_months = [
            m for m in MONTH_ORDER
            if m in month_source_df["Month"].dropna().unique().tolist()
        ]
        selected_months = _checkbox_slicer(
            "▣ Month",
            available_months,
            key="overview_month_slicer",
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

    with filter_cols[8]:
        loadtype = st.selectbox(
            "▤ Load Type",
            ["All"] + sorted(df["LOADTYPE"].dropna().unique().tolist()),
            key="overview_loadtype",
        )
    if loadtype != "All":
        df = df[df["LOADTYPE"] == loadtype]

    with filter_cols[9]:
        conversion_type = st.selectbox(
            "₹ Conversion",
            ["Crore", "Lac"],
            key="overview_conversion_type",
        )
    revenue_divisor, revenue_unit = get_revenue_conversion(conversion_type)

    zone = selected_zones[0] if len(selected_zones) == 1 else "All"
    circle = selected_circles[0] if len(selected_circles) == 1 else "All"
    branch = selected_branches[0] if len(selected_branches) == 1 else "All"
    quarter = selected_quarters[0] if len(selected_quarters) == 1 else "All"
    month = selected_months[0] if len(selected_months) == 1 else "All"

    compact_spacer(0)

    active_filter_items = [
        ("FY", fy),
        ("View", view_type),
        ("Company", company),
        ("Zone", ", ".join(map(str, selected_zones)) if selected_zones else "All"),
        ("Circle", ", ".join(map(str, selected_circles)) if selected_circles else "All"),
        ("Branch", ", ".join(map(str, selected_branches)) if selected_branches else "All"),
        ("Quarter", ", ".join(map(str, selected_quarters)) if selected_quarters else "All"),
        ("Month", ", ".join(map(str, selected_months)) if selected_months else "All"),
        ("Load", loadtype),
        ("Unit", conversion_type),
    ]
    active_filter_html = "".join(
        f'<span class="filter-chip">{label}: {value}</span>'
        for label, value in active_filter_items
        if value not in (None, "", "All")
    )

    header_filter_html = (
        f'<div class="filter-summary" style="width:auto;min-height:0;flex-wrap:nowrap;gap:6px;">'
        f'{active_filter_html}</div>'
        if active_filter_html else ''
    )
    with header_content_placeholder:
        st.markdown(
            f"""
            <div style="padding:2px 0 3px 4px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <div class="executive-title" style="white-space:nowrap;">Business Overview</div>
                {header_filter_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if df.empty:
        st.warning("No data found for selected filters")
        return

    safe_view = str(view_type).strip().lower().replace(" ", "_")
    safe_fy = str(fy).strip().replace("/", "-").replace(" ", "_")
    export_key = f"overview_export_ready_{safe_view}_{safe_fy}"

    with export_placeholder:
        if not st.session_state.get(export_key, False):
            if st.button(
                "⬇ Prepare CSV",
                key=f"prepare_{export_key}",
                help="Prepare the currently filtered rows for download.",
                width="content",
            ):
                st.session_state[export_key] = True
                st.rerun()
        else:
            export_csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇ Download CSV",
                data=export_csv,
                file_name=f"revenue_overview_{safe_view}_{safe_fy}.csv",
                mime="text/csv",
                key=f"download_{export_key}",
                help="Download the revenue overview data after applying the selected filters.",
                width="content",
                on_click=lambda: st.session_state.update({export_key: False}),
            )

                                                                                             
                               
    if not prev_df.empty:
        if company != "All" and "compname" in prev_df.columns:
            prev_df = prev_df[prev_df["compname"] == company]
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
        if loadtype != "All":
            prev_df = prev_df[prev_df["LOADTYPE"] == loadtype]

    prev_kpis = calculate_kpis(prev_df)

    current_kpis = calculate_kpis(df)

    revenue = current_kpis["revenue"]
    ftl = current_kpis["ftl"]
    ltl = current_kpis["ltl"]
    total_gr = current_kpis["total_gr"]
    aweight = round(current_kpis["aweight"], 1)
    topay = current_kpis["topay"]
    paid = current_kpis["paid"]
    tbb = current_kpis["tbb"]

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

    revenue_growth = pct_growth(revenue, prev_kpis["revenue"])
    ftl_growth = pct_growth(ftl, prev_kpis["ftl"])
    ltl_growth = pct_growth(ltl, prev_kpis["ltl"])
    gr_growth = pct_growth(total_gr, prev_kpis["total_gr"])
    delivered_growth = pct_growth(delivered_gr, prev_delivered_gr)
    weight_growth = pct_growth(aweight, prev_kpis["aweight"])
    topay_growth = pct_growth(topay, prev_kpis["topay"])
    paid_growth = pct_growth(paid, prev_kpis["paid"])
    tbb_growth = pct_growth(tbb, prev_kpis["tbb"])

    target_month_count = max(int(df["FIN_MONTH"].dropna().nunique()), 1) if "FIN_MONTH" in df.columns else 1
    total_target_lac = get_monthly_target_for_filtered_branches(df, "All") * target_month_count
    ftl_target_lac = get_monthly_target_for_filtered_branches(df, "FTL") * target_month_count
    ltl_target_lac = get_monthly_target_for_filtered_branches(df, "LTL") * target_month_count
    total_target_rupees = total_target_lac * 100000.0
    ftl_target_rupees = ftl_target_lac * 100000.0
    ltl_target_rupees = ltl_target_lac * 100000.0

    total_target_text = format_revenue(total_target_rupees, conversion_type)
    ftl_target_text = format_revenue(ftl_target_rupees, conversion_type)
    ltl_target_text = format_revenue(ltl_target_rupees, conversion_type)

    total_target_achievement = (revenue / total_target_rupees * 100) if total_target_rupees > 0 else None
    ftl_target_achievement = (ftl / ftl_target_rupees * 100) if ftl_target_rupees > 0 else None
    ltl_target_achievement = (ltl / ltl_target_rupees * 100) if ltl_target_rupees > 0 else None

    k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9, gap="small")

    with k1:
        create_card(
            "Business", format_revenue(revenue, conversion_type), "#2563eb", "💰", revenue_growth,
            format_revenue(prev_kpis["revenue"], conversion_type), total_target_text,
            total_target_achievement,
        )

    with k2:
        create_card(
            "FTL Business", format_revenue(ftl, conversion_type), "#2563eb", "🚛", ftl_growth,
            format_revenue(prev_kpis["ftl"], conversion_type), ftl_target_text,
            ftl_target_achievement,
        )

    with k3:
        create_card(
            "LTL Business", format_revenue(ltl, conversion_type), "#2563eb", "🚚", ltl_growth,
            format_revenue(prev_kpis["ltl"], conversion_type), ltl_target_text,
            ltl_target_achievement,
        )

    with k4:
        create_card("Total GR", f"{total_gr:,}", "#2563eb", "📦", gr_growth,
                    f"{int(prev_kpis['total_gr']):,}")

    with k5:
        create_card("Delivered GR", f"{delivered_gr:,}", "#16a34a", "✅", delivered_growth,
                    f"{prev_delivered_gr:,}")

    with k6:
        create_card("Total Weight (MT)", f"{aweight:,.0f}", "#2563eb", "⚓", weight_growth,
                    f"{prev_kpis['aweight']:,.0f}")

    with k7:
        create_card("Topay", format_revenue(topay, conversion_type), "#2563eb", "🧾", topay_growth,
                    format_revenue(prev_kpis["topay"], conversion_type))

    with k8:
        create_card("Paid", format_revenue(paid, conversion_type), "#2563eb", "🔗", paid_growth,
                    format_revenue(prev_kpis["paid"], conversion_type))

    with k9:
        create_card("T.B.B", format_revenue(tbb, conversion_type), "#2563eb", "🚚", tbb_growth,
                    format_revenue(prev_kpis["tbb"], conversion_type))

    compact_spacer()

    monthly = (
        df.groupby("Month")["REVENUE"]
        .sum()
        .reset_index()
    )

    monthly["Business Cr"] = (monthly["REVENUE"] / revenue_divisor).round(2)

    monthly["Month"] = pd.Categorical(
        monthly["Month"],
        categories=MONTH_ORDER,
        ordered=True
    )

    monthly = monthly.sort_values("Month")

    ftl_pct = (ftl / revenue * 100) if revenue else 0
    ltl_pct = (ltl / revenue * 100) if revenue else 0

    row1, row2 = st.columns([1.20, 0.80], gap="medium")

    with row1:
        with st.container(border=True):
            title_col, filter_col = st.columns(
                [1.55, 2.15], gap="small", vertical_alignment="top"
            )

            with title_col:
                _trend_badge_color = "#166534" if revenue_growth >= 0 else "#dc2626"
                st.markdown(
                    f"<div style='font-size:14px;font-weight:400;color:#0f172a;'>Business Trend "
                    f"<span style='font-size:11px;font-weight:700;color:{_trend_badge_color};'>"
                    f"({growth_label(revenue_growth)} vs LY)</span></div>",
                    unsafe_allow_html=True
                )

            with filter_col:
                trend_type = _button_selector(
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    "revenue_trend_type",
                    "revenue_period_btn",
                    "Monthly",
                )

            DATE_COL = "grdt"                                            

            yoy_df = build_yoy_trend(
                df, prev_df, trend_type, DATE_COL, start_date, prev_start, month_map
            )

                                                                
            if conversion_type == "Lac":
                for revenue_col in ["Business Cr", "Prev Business Cr"]:
                    if revenue_col in yoy_df.columns:
                        yoy_df[revenue_col] = yoy_df[revenue_col] * 100

            monthly_target_lac = get_monthly_target_for_filtered_branches(
                df, loadtype
            )
            target_trend_df = build_target_trend(
                filtered_df=df,
                trend_type=trend_type,
                date_col=DATE_COL,
                monthly_target_lac=monthly_target_lac,
                conversion_type=conversion_type,
                month_map=month_map,
            )
            if not target_trend_df.empty:
                yoy_df = yoy_df.merge(target_trend_df, on="Period", how="left")
            else:
                yoy_df["Target"] = 0.0
            yoy_df["Target"] = pd.to_numeric(
                yoy_df.get("Target", 0.0), errors="coerce"
            ).fillna(0.0)
            yoy_df["Target Achievement %"] = yoy_df.apply(
                lambda row: (
                    row["Business Cr"] / row["Target"] * 100
                    if row["Target"] > 0 else None
                ),
                axis=1,
            )

            trend_actual = float(pd.to_numeric(yoy_df["Business Cr"], errors="coerce").fillna(0).sum())
            trend_target = float(pd.to_numeric(yoy_df["Target"], errors="coerce").fillna(0).sum())

            fig_yoy = go.Figure()

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Prev Business Cr"],
                    name=f"LY ({prev_fy})",
                    marker=dict(color="#cbd5e1", line=dict(color="#94a3b8", width=1.3)),
                    text=yoy_df["Prev Business Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#475569", family="Arial"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>LY Business: ₹%{{y:.2f}} {revenue_unit}<extra></extra>",
                    offsetgroup="ly",
                    alignmentgroup="business_trend",
                )
            )

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Business Cr"],
                    name=f"Current ({fy})",
                    marker=dict(color="#2563eb", line=dict(color="#1e3a8a", width=1.3)),
                    text=yoy_df["Business Cr"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=12, color="#1d4ed8", family="Arial"),
                    cliponaxis=False,
                    hovertemplate=f"<b>%{{x}}</b><br>Current Business: ₹%{{y:.2f}} {revenue_unit}<extra></extra>",
                    offsetgroup="current",
                    alignmentgroup="business_trend",
                )
            )

            fig_yoy.add_trace(
                go.Bar(
                    x=yoy_df["Period"],
                    y=yoy_df["Target"],
                    name="Target",
                    marker=dict(
                        color="#f59e0b",
                        line=dict(color="#b45309", width=1.3),
                        pattern=dict(shape="/", solidity=0.22),
                    ),
                    opacity=0.88,
                    text=yoy_df["Target"],
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                    textfont=dict(size=11, color="#b45309", family="Arial"),
                    cliponaxis=False,
                    customdata=yoy_df[["Target Achievement %"]],
                    hovertemplate=(
                        "<b>%{x}</b><br>Target: ₹%{y:.2f} "
                        + revenue_unit
                        + "<br>Achievement: %{customdata[0]:.1f}%<extra></extra>"
                    ),
                    offsetgroup="target",
                    alignmentgroup="business_trend",
                )
            )

            yoy_max = pd.concat(
                [
                    pd.to_numeric(yoy_df["Business Cr"], errors="coerce"),
                    pd.to_numeric(yoy_df["Prev Business Cr"], errors="coerce"),
                    pd.to_numeric(yoy_df["Target"], errors="coerce"),
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
                            r["Business Cr"] if pd.notna(r["Business Cr"]) else 0,
                            r["Prev Business Cr"] if pd.notna(r["Prev Business Cr"]) else 0,
                        )
                        growth_gap = 0.24 if trend_type == "Monthly" else 0.16
                        target_achievement = r.get("Target Achievement %")
                        target_text = (
                            f" · 🎯 {target_achievement:.1f}%"
                            if pd.notna(target_achievement) else ""
                        )
                        fig_yoy.add_annotation(
                            x=r["Period"],
                            y=max(bar_top, r.get("Target", 0) or 0) + (yoy_max * growth_gap),
                            text=f"{r['Growth Label']}{target_text}",
                            showarrow=False,
                            font=dict(size=11, color=label_color, family="Arial"),
                        )

            fig_yoy.update_layout(
                barmode="group",
                height=REVENUE_CHART_HEIGHT,
                margin=dict(l=2, r=2, t=12, b=0),
                plot_bgcolor="#f8fafc",
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
                yaxis_title=f"Business ({revenue_unit})",
                yaxis_range=[0, yoy_max * (1.48 if trend_type == "Monthly" else 1.35)],
                bargap=0.22,
                bargroupgap=0.08,
            )
            apply_3d_chart_layout(fig_yoy, height=REVENUE_CHART_HEIGHT, margin=dict(l=6, r=6, t=14, b=2))
            fig_yoy.update_xaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=11))
            fig_yoy.update_yaxes(showgrid=False, showline=False, zeroline=False, tickfont=dict(size=11), title_font=dict(size=12))

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

                                                          
                                                                        
        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:{LOAD_TITLE_FONT}px;font-weight:600;'
                f'color:#0f172a;margin:0;line-height:1.1;">'
                f'Business by Load Type (CY)</div>',
                unsafe_allow_html=True,
            )

                                                                           
            compact_spacer(10)

            prev_ftl = prev_kpis["ftl"]
            prev_ltl = prev_kpis["ltl"]
            load_total = ftl + ltl
            ftl_share = (ftl / load_total * 100) if load_total else 0
            ltl_share = (ltl / load_total * 100) if load_total else 0
            ftl_yoy = pct_growth(ftl, prev_ftl)
            ltl_yoy = pct_growth(ltl, prev_ltl)

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
                            values=[ftl, ltl],
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
                                f"Revenue: ₹%{{value:.2f}}<br>"
                                "Share: %{percent}<extra></extra>"
                            ),
                        )
                    ]
                )

                fig_load.update_layout(
                    height=165,
                    margin=dict(l=0, r=0, t=8, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    annotations=[
                        dict(
                            x=0.5,
                            y=0.55,
                            text=f"<b>₹{load_total / revenue_divisor:.2f} {revenue_unit}</b>",
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
                            text="Total Revenue",
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
                ftl_growth_color = "#16a34a" if ftl_yoy >= 0 else "#dc2626"
                ltl_growth_color = "#16a34a" if ltl_yoy >= 0 else "#dc2626"
                ftl_arrow = "▲" if ftl_yoy >= 0 else "▼"
                ltl_arrow = "▲" if ltl_yoy >= 0 else "▼"

                load_legend_html = (
                    '<div style="display:flex;flex-direction:column;gap:15px;'
                    'padding:4px 0;line-height:1.2;">'

                    '<div style="display:grid;'
                    'grid-template-columns:13px minmax(40px,.75fr) minmax(84px,auto) minmax(48px,auto);'
                    'align-items:center;gap:8px;">'
                    '<span style="width:11px;height:11px;border-radius:50%;'
                    'background:#2563eb;display:inline-block;"></span>'
                    f'<span style="font-size:{LOAD_LABEL_FONT}px;font-weight:600;'
                    f'color:#334155;">FTL</span>'
                    f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;'
                    f'color:#0f172a;white-space:nowrap;">'
                    f'₹{ftl / revenue_divisor:.2f} {revenue_unit}</span>'
                    f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;'
                    f'color:#334155;white-space:nowrap;text-align:right;">'
                    f'{ftl_share:.1f}%</span>'
                    f'<span style="grid-column:2/5;font-size:{LOAD_SUBTEXT_FONT}px;'
                    f'color:#64748b;white-space:nowrap;">'
                    f'LY ₹{prev_ftl / revenue_divisor:.2f} {revenue_unit} · '
                    f'<span style="color:{ftl_growth_color};font-weight:700;">'
                    f'{ftl_arrow} {abs(ftl_yoy):.1f}%</span></span>'
                    '</div>'

                    '<div style="display:grid;'
                    'grid-template-columns:13px minmax(40px,.75fr) minmax(84px,auto) minmax(48px,auto);'
                    'align-items:center;gap:8px;">'
                    '<span style="width:11px;height:11px;border-radius:50%;'
                    'background:#0f766e;display:inline-block;"></span>'
                    f'<span style="font-size:{LOAD_LABEL_FONT}px;font-weight:600;'
                    f'color:#334155;">LTL</span>'
                    f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;'
                    f'color:#0f172a;white-space:nowrap;">'
                    f'₹{ltl / revenue_divisor:.2f} {revenue_unit}</span>'
                    f'<span style="font-size:{LOAD_VALUE_FONT}px;font-weight:700;'
                    f'color:#334155;white-space:nowrap;text-align:right;">'
                    f'{ltl_share:.1f}%</span>'
                    f'<span style="grid-column:2/5;font-size:{LOAD_SUBTEXT_FONT}px;'
                    f'color:#64748b;white-space:nowrap;">'
                    f'LY ₹{prev_ltl / revenue_divisor:.2f} {revenue_unit} · '
                    f'<span style="color:{ltl_growth_color};font-weight:700;">'
                    f'{ltl_arrow} {abs(ltl_yoy):.1f}%</span></span>'
                    '</div>'

                    '</div>'
                )

                if hasattr(st, "html"):
                    st.html(load_legend_html)
                else:
                    st.markdown(load_legend_html, unsafe_allow_html=True)

                                                                          
                                                                        
        company_df = (
            df.groupby("compname", dropna=False)["REVENUE"]
            .sum()
            .reset_index()
            .rename(columns={"compname": "Company", "REVENUE": "CY Revenue"})
        )
        company_df["Company"] = company_df["Company"].fillna("Unknown").astype(str)

        if prev_df is not None and not prev_df.empty and "compname" in prev_df.columns:
            prev_company_df = (
                prev_df.groupby("compname", dropna=False)["REVENUE"]
                .sum()
                .reset_index()
                .rename(columns={"compname": "Company", "REVENUE": "PY Revenue"})
            )
            prev_company_df["Company"] = (
                prev_company_df["Company"].fillna("Unknown").astype(str)
            )
        else:
            prev_company_df = pd.DataFrame(columns=["Company", "PY Revenue"])

        company_df = company_df.merge(prev_company_df, on="Company", how="left")
        company_df["PY Revenue"] = pd.to_numeric(
            company_df["PY Revenue"], errors="coerce"
        ).fillna(0)
        company_df["Business Cr"] = company_df["CY Revenue"] / revenue_divisor
        company_df["PY Business Cr"] = company_df["PY Revenue"] / revenue_divisor
        company_total = company_df["Business Cr"].sum()
        company_df["Contribution %"] = (
            company_df["Business Cr"] / company_total * 100
            if company_total
            else 0
        )
        company_df["Growth %"] = company_df.apply(
            lambda row: pct_growth(row["CY Revenue"], row["PY Revenue"]),
            axis=1,
        )
        company_df = company_df.sort_values(
            "Business Cr", ascending=False
        ).reset_index(drop=True)
        company_chart_df = company_df.head(6).copy()

        with st.container(border=True):
            st.markdown(
                "<div style='font-size:15px;font-weight:600;color:#0f172a;"
                "margin:0 0 2px 0;line-height:1.1;'>Target Achievement</div>",
                unsafe_allow_html=True,
            )
            create_target_speedometer(
                actual=trend_actual,
                target=trend_target,
                unit=f" {revenue_unit}",
                title="Target Achievement",
                compact=False,
            )

    compact_spacer()

                               

                            
    zone_df = (
        df.groupby("zone")["REVENUE"]
        .sum()
        .reset_index()
    )

    zone_df["Business Cr"] = (zone_df["REVENUE"] / revenue_divisor).round(2)
    zone_df["zone_short"] = zone_df["zone"].replace({
        "NORTH ZONE": "North",
        "WEST ZONE": "West",
        "SOUTH ZONE": "South",
        "EAST ZONE": "East",
        "NORTH EAST ZONE": "NE",
        "NEPAL ZONE": "Nepal"
    })

    zone_df = zone_df.sort_values("Business Cr", ascending=False)

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

        zone_country_rev["Business Cr"] = (
            zone_country_rev["REVENUE"] / revenue_divisor
        ).round(2)

        matrix_df = zone_country_rev.pivot(
            index="zone",
            columns="COUNTRY",
            values="Business Cr"
        ).fillna(0)

        matrix_df["Total"] = matrix_df.sum(axis=1)
        matrix_df = matrix_df.sort_values("Total", ascending=False)

        if prev_df is not None and not prev_df.empty and {"zone", "COUNTRY", "REVENUE"}.issubset(prev_df.columns):
            prev_zone_country_rev = (
                prev_df.groupby(["zone", "COUNTRY"])["REVENUE"]
                .sum()
                .reset_index()
            )
            prev_zone_country_rev["Business Cr"] = (
                prev_zone_country_rev["REVENUE"] / revenue_divisor
            ).round(2)
            prev_matrix_df = prev_zone_country_rev.pivot(
                index="zone",
                columns="COUNTRY",
                values="Business Cr",
            ).fillna(0)
            prev_matrix_df["Total"] = prev_matrix_df.sum(axis=1)
        else:
            prev_matrix_df = pd.DataFrame()

                                                          
                                                           
    weight_zone_left, weight_zone_right = st.columns([1.55, 1], gap="medium")
    aligned_chart_height = ALIGNED_CHART_HEIGHT

    with weight_zone_left:
        with st.container(border=True):
            weight_title_col, weight_filter_col = st.columns([2, 2])

            with weight_filter_col:
                weight_trend_type = _button_selector(
                    ["Daily", "Weekly", "Monthly", "Quarterly"],
                    "weight_trend_type",
                    "weight_period_btn",
                    "Monthly",
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
                    f"<div style='font-size:14px;font-weight:400;color:#0f172a;'>Weight (MT) Trend "
                    f"<span style='font-size:11px;font-weight:700;color:{_w_badge_color};'>"
                    f"({growth_label(weight_growth_total)} vs LY)</span></div>",
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
                    textfont=dict(size=12, color="#475569", family="Arial"),
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
                    textfont=dict(size=12, color="#0f766e", family="Arial"),
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
                            font=dict(size=12, color=label_color, family="Arial"),
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
            st.markdown("###### Business by Zone")

                                                                              
            total_zone_revenue = zone_df["Business Cr"].sum()
            zone_donut_df = zone_df.copy()
            zone_donut_df["Percentage"] = (
                zone_donut_df["Business Cr"] / total_zone_revenue * 100
                if total_zone_revenue > 0 else 0
            ).round(1)
            zone_donut_df = zone_donut_df.sort_values(
                "Business Cr", ascending=False
            ).reset_index(drop=True)

            if zone_donut_df.empty or total_zone_revenue <= 0:
                st.info("No zone revenue is available for the selected filters.")
            else:
                zone_labels = zone_donut_df["zone_short"].astype(str).tolist()
                zone_values = zone_donut_df["Business Cr"].tolist()
                zone_percentages = zone_donut_df["Percentage"].tolist()
                zone_color_list = [
                    zone_colors.get(zone_name, "#2563eb")
                    for zone_name in zone_donut_df["zone"].tolist()
                ]

                                                                                
                                                                       
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
                                "<b>%{label}</b><br>Business: ₹%{value:.2f} {revenue_unit}"
                                "<br>Contribution: %{customdata:.1f}%<extra></extra>"
                            ),
                        )
                    ]
                )

                                                                                    
                                                                                     
                legend_y_start = 0.91
                legend_step = 0.145 if len(zone_donut_df) <= 6 else 0.115
                for idx, row in zone_donut_df.iterrows():
                    y_pos = legend_y_start - (idx * legend_step)
                    color = zone_color_list[idx]

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

                    fig_zone.add_annotation(
                        x=0.675,
                        y=y_pos,
                        xref="paper",
                        yref="paper",
                        text=(
                            f"<span style='font-size:14px;color:#0f172a'><b>"
                            f"{escape(str(row['zone_short']))}</b></span>"
                            f"<br><span style='font-size:12px;color:#334155'>"
                            f"₹{row['Business Cr']:.2f} {revenue_unit} &nbsp; "
                            f"<span style='color:{color};font-weight:700'>"
                            f"({row['Percentage']:.1f}%)</span></span>"
                        ),
                        showarrow=False,
                        xanchor="left",
                        yanchor="middle",
                        align="left",
                        font=dict(size=12, color="#334155", family="Arial"),
                    )

                                                                              

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
                            font=dict(size=15, color="#0f172a", family="Arial"),
                        )
                    ],
                )

                st.plotly_chart(
                    fig_zone,
                    width="stretch",
                    config={"displayModeBar": False, "responsive": True},
                )

    compact_spacer()

                                                            
                                                           
    if view_type == "Origin":
        with st.container(border=True):
            st.markdown(
                "<div style='display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 0 8px 2px;'>"
                "<div style='font-size:15px;font-weight:500;color:#0f2744;'>Zone-wise Country Business</div>"
                "<div style='display:flex;gap:14px;flex-wrap:wrap;font-size:10px;'>"
                "<span style='color:#1d4ed8;'>■ Current Year</span>"
                "<span style='color:#0f766e;'>■ Last Year</span>"
                "<span style='color:#6d28d9;'>■ YoY Comparison</span>"
                "</div></div>",
                unsafe_allow_html=True,
            )

            current_matrix = matrix_df.copy()
            previous_matrix = prev_matrix_df.copy() if not prev_matrix_df.empty else pd.DataFrame()

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
                    '<td class="metric-name">Revenue</td>' + ''.join(revenue_cells) + '</tr>'
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
                '<tr class="grand-total-row"><td class="zone-name" rowspan="2">TOTAL</td><td class="metric-name">Revenue</td>'
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
                .compact-zone-matrix .yoy-cell {{background:#fcfaff;}}
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
                <span>Values in ₹ {escape(str(revenue_unit))}</span>
                <span style="color:#16a34a;">▲ Positive movement</span>
                <span style="color:#dc2626;">▼ Negative movement</span>
                <span>YoY % = (CY − LY) ÷ LY × 100</span>
            </div>
            """
            if hasattr(st, "html"):
                st.html(matrix_html)
            else:
                st.markdown(matrix_html, unsafe_allow_html=True)

    compact_spacer()

    monthly_chart = monthly.copy()
    monthly_chart["Growth %"] = monthly_chart["Business Cr"].pct_change().mul(100).round(2)
    monthly_chart = monthly_chart.dropna(subset=["Month"]).copy()
    monthly_chart["Month"] = monthly_chart["Month"].astype(str)

    mom_chart_col, branch_achievement_col, target_meter_col = st.columns(
        [1.20, 1.20, 0.60], gap="medium", vertical_alignment="top"
    )

    with mom_chart_col:
        with st.container(border=True):
            st.markdown("<div style='font-size:13px;font-weight:400;color:#0f172a;margin-bottom:2px;'>Month on Month Business & Growth</div>", unsafe_allow_html=True)
            fig_mom = go.Figure()
            fig_mom.add_trace(go.Bar(
                x=monthly_chart["Month"], y=monthly_chart["Business Cr"], name="Business",
                                                                                       
                marker=dict(
                    color="#bfdbfe",
                    line=dict(color="#2563eb", width=1.3),
                ),
                opacity=0.92,
                text=monthly_chart["Business Cr"], texttemplate=f"₹%{{text:.2f}} {revenue_unit}",
                textposition="outside",
                textfont=dict(size=10, color="#1e3a8a", family="Arial"),
                cliponaxis=False,
                hovertemplate=f"<b>%{{x}}</b><br>Business: ₹%{{y:.2f}} {revenue_unit}<extra></extra>",
            ))
            growth_colors = ["#16a34a" if pd.notna(v) and v >= 0 else "#dc2626" for v in monthly_chart["Growth %"]]
            fig_mom.add_trace(go.Scatter(
                x=monthly_chart["Month"], y=monthly_chart["Growth %"], name="MoM Growth",
                mode="lines+markers+text", yaxis="y2", line=dict(color="#f59e0b", width=3),
                marker=dict(size=8, color=growth_colors, line=dict(color="white", width=1.5)),
                text=["" if pd.isna(v) else f"{'▲' if v >= 0 else '▼'} {abs(v):.1f}%" for v in monthly_chart["Growth %"]],
                textposition="top center",
                textfont=dict(size=11, color=growth_colors, family="Arial"),
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>MoM Growth: %{y:.2f}%<extra></extra>",
            ))
            revenue_max = pd.to_numeric(monthly_chart["Business Cr"], errors="coerce").max()
            revenue_max = revenue_max if pd.notna(revenue_max) and revenue_max > 0 else 1
            growth_abs_max = pd.to_numeric(monthly_chart["Growth %"], errors="coerce").abs().max()
            growth_abs_max = growth_abs_max if pd.notna(growth_abs_max) and growth_abs_max > 0 else 10
            fig_mom.update_layout(
                height=235, margin=dict(l=8, r=8, t=28, b=6), plot_bgcolor="#f8fafc",
                paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.10, x=0), bargap=0.35,
                yaxis=dict(title=f"Business ({revenue_unit})", range=[0, revenue_max * 1.30], showgrid=False, zeroline=False),
                yaxis2=dict(title="Growth (%)", overlaying="y", side="right", range=[-growth_abs_max * 1.35, growth_abs_max * 1.35], showgrid=False, zeroline=True, zerolinecolor="#cbd5e1"),
                xaxis=dict(showgrid=False, title=""),
            )
            apply_3d_chart_layout(fig_mom, height=235, margin=dict(l=8, r=8, t=30, b=6))
            fig_mom.update_xaxes(showline=False, zeroline=False)
            fig_mom.update_yaxes(showline=False)
            st.plotly_chart(fig_mom, width="stretch", config={"displayModeBar": False, "responsive": True})

    with branch_achievement_col:
        with st.container(border=True):
                                                                                       
            _target_title_col, _top_dropdown_col = st.columns(
                [0.74, 0.26], gap="small", vertical_alignment="center"
            )

            with _target_title_col:
                st.markdown(
                    "<div style='font-size:13px;font-weight:700;color:#0f172a;margin:2px 0 4px 0;'>"
                    "TARGET ACHIEVEMENT</div>",
                    unsafe_allow_html=True,
                )

            with _top_dropdown_col:
                _branch_achievement_top_n = st.selectbox(
                    "Number of records",
                    options=[5, 10, 20, 30],
                    index=0,
                    key="branch_achievement_top_n",
                    label_visibility="collapsed",
                )

            _achievement_level = _button_selector(
                ["Zone", "Circle", "Branch"],
                "target_achievement_level",
                "target_level_btn",
                "Branch",
            )

            st.markdown(
                f"<div style='font-size:11px;font-weight:600;color:#475569;margin:2px 0 8px 0;'>"
                f"{_achievement_level} wise · Top {_branch_achievement_top_n}</div>",
                unsafe_allow_html=True,
            )

            try:
                _branch_summary_compact = (
                    df.groupby("branch", dropna=False)["REVENUE"]
                    .sum()
                    .reset_index(name="Business")
                )
                _branch_ach_df, _branch_ach_months = calculate_branch_target_achievement(
                    filtered_df=df,
                    branch_summary=_branch_summary_compact,
                    selected_month=month,
                    selected_quarter=quarter,
                    selected_loadtype=loadtype,
                )
                _branch_ach_df = _branch_ach_df[
                    _branch_ach_df["Matched_Target"] & (_branch_ach_df["Target_Rs"] > 0)
                ].copy()

                _level_column = {
                    "Zone": "zone",
                    "Circle": "circle",
                    "Branch": "branch",
                }[_achievement_level]

                if _achievement_level != "Branch":
                    _hierarchy_map = (
                        df[["branch", _level_column]]
                        .dropna(subset=["branch", _level_column])
                        .drop_duplicates(subset=["branch"], keep="first")
                    )
                    _branch_ach_df = _branch_ach_df.merge(
                        _hierarchy_map, on="branch", how="left"
                    )
                    _branch_ach_df = (
                        _branch_ach_df.dropna(subset=[_level_column])
                        .groupby(_level_column, as_index=False)
                        .agg(Business=("Business", "sum"), Target_Rs=("Target_Rs", "sum"))
                    )
                    _branch_ach_df["Achievement_Pct"] = _branch_ach_df.apply(
                        lambda _r: (_r["Business"] / _r["Target_Rs"] * 100)
                        if _r["Target_Rs"] > 0 else 0.0,
                        axis=1,
                    )
                    _branch_ach_df = _branch_ach_df.rename(columns={_level_column: "Display_Name"})
                else:
                    _branch_ach_df = _branch_ach_df.rename(columns={"branch": "Display_Name"})

                _branch_ach_df = _branch_ach_df.sort_values(
                    ["Achievement_Pct", "Business"], ascending=[False, False]
                ).head(_branch_achievement_top_n)

                if _branch_ach_df.empty:
                    st.info("No matched targets for the active filters.")
                else:
                    _rows_html = []
                    for _, _row in _branch_ach_df.iterrows():
                        _ach = float(_row["Achievement_Pct"] or 0)
                        _actual_display = float(_row["Business"]) / revenue_divisor
                        _target_display = float(_row["Target_Rs"]) / revenue_divisor
                        _bar_width = max(0.0, min(_ach, 100.0))
                        _status_color = (
                            "#16a34a" if _ach >= 100
                            else "#f59e0b" if _ach >= 80
                            else "#dc2626"
                        )
                        _name = escape(str(_row["Display_Name"]))
                        _rows_html.append(
                            f'<div style="display:grid;grid-template-columns:1.45fr .8fr .8fr .9fr 1.1fr;align-items:center;gap:7px;padding:6px 0;border-bottom:1px solid #eef2f7;font-size:10.5px;color:#0f172a;">'
                            f'<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="{_name}">{_name}</div>'
                            f'<div style="text-align:right;">{_actual_display:,.2f}</div>'
                            f'<div style="text-align:right;">{_target_display:,.2f}</div>'
                            f'<div style="text-align:right;font-weight:700;color:{_status_color};">{_ach:,.2f}%</div>'
                            f'<div style="height:8px;background:#e5e7eb;border-radius:999px;overflow:hidden;">'
                            f'<div style="height:100%;width:{_bar_width:.1f}%;background:{_status_color};border-radius:999px;"></div>'
                            f'</div></div>'
                        )

                    _first_header = _achievement_level
                    _table_html = (
                        '<div style="width:100%;">'
                        '<div style="display:grid;grid-template-columns:1.45fr .8fr .8fr .9fr 1.1fr;gap:7px;padding:2px 0 6px 0;border-bottom:1px solid #dbe3ec;font-size:9.5px;font-weight:700;color:#334155;">'
                        f'<div>{_first_header}</div>'
                        f'<div style="text-align:right;">Actual ({revenue_unit})</div>'
                        f'<div style="text-align:right;">Target ({revenue_unit})</div>'
                        '<div style="text-align:right;">Achievement %</div>'
                        '<div style="text-align:center;">Achievement Bar</div>'
                        '</div>' + ''.join(_rows_html) + '</div>'
                    )
                    if hasattr(st, "html"):
                        st.html(_table_html)
                    else:
                        st.markdown(_table_html, unsafe_allow_html=True)
            except Exception as _branch_achievement_exc:
                st.info(f"Target achievement unavailable: {_branch_achievement_exc}")

    with target_meter_col:
        with st.container(border=True):
            st.markdown(
                f'<div style="font-size:13px;font-weight:600;'
                f'color:#0f172a;margin:0 0 7px 0;line-height:1.2;">'
                f'Business by Company (CY)</div>',
                unsafe_allow_html=True,
            )

            if company_chart_df.empty or company_total <= 0:
                st.info("No company revenue is available for the selected filters.")
            else:
                company_colors = [
                    "#2563eb",
                    "#0f9f8f",
                    "#7c3aed",
                    "#f59e0b",
                    "#ec4899",
                    "#64748b",
                ]
                max_company_value = float(company_chart_df["Business Cr"].max() or 1)
                company_rows = []

                for idx, row in company_chart_df.iterrows():
                    company_name = escape(str(row["Company"]))
                    value = float(row["Business Cr"] or 0)
                    share = float(row["Contribution %"] or 0)
                    py_value = float(row["PY Business Cr"] or 0)
                    growth = float(row["Growth %"] or 0)
                    width_pct = (
                        min((value / max_company_value * 100), 100)
                        if max_company_value
                        else 0
                    )
                    color = company_colors[idx % len(company_colors)]
                    growth_color = "#16a34a" if growth >= 0 else "#dc2626"
                    growth_arrow = "▲" if growth >= 0 else "▼"

                    company_rows.append(
                        f'<div title="{company_name} | LY ₹{py_value:.2f} {revenue_unit} | '
                        f'{growth_arrow} {abs(growth):.1f}%" '
                        f'style="display:grid;'
                        f'grid-template-columns:minmax(150px,195px) minmax(55px,1fr) '
                        f'minmax(84px,auto) minmax(58px,auto);'
                        f'align-items:center;gap:8px;margin:9px 0;line-height:1.2;">'

                        f'<div style="font-size:10.5px;font-weight:600;'
                        f'color:#334155;white-space:nowrap;overflow:hidden;'
                        f'text-overflow:ellipsis;">{company_name}</div>'

                        f'<div style="height:9px;background:#e8eef5;border-radius:999px;'
                        f'overflow:hidden;box-shadow:inset 0 1px 2px rgba(15,23,42,.10);">'
                        f'<div style="height:9px;width:{width_pct:.2f}%;background:{color};'
                        f'border-radius:999px;"></div></div>'

                        f'<div style="font-size:10px;font-weight:700;'
                        f'color:#0f172a;white-space:nowrap;">'
                        f'₹{value:.2f} {revenue_unit}</div>'

                        f'<div style="font-size:10px;font-weight:700;'
                        f'color:#334155;min-width:54px;text-align:right;white-space:nowrap;">'
                        f'{share:.2f}%</div>'

                        f'<div style="grid-column:2/5;margin-top:-3px;'
                        f'font-size:{COMPANY_SUBTEXT_FONT}px;color:#64748b;white-space:nowrap;">'
                        f'LY ₹{py_value:.2f} {revenue_unit} · '
                        f'<span style="color:{growth_color};font-weight:700;">'
                        f'{growth_arrow} {abs(growth):.1f}%</span></div>'

                        f'</div>'
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
                                                                                    
        current_party = (
            df.assign(_party=df[party_col].fillna("Unknown").astype(str).str.strip())
            .query("_party != ''")
            .groupby("_party", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="Current Business")
        )

        if prev_party_col is not None:
            previous_party = (
                prev_df.assign(
                    _party=prev_df[prev_party_col].fillna("Unknown").astype(str).str.strip()
                )
                .query("_party != ''")
                .groupby("_party", dropna=False)["REVENUE"]
                .sum()
                .reset_index(name="Previous Business")
            )
        else:
            previous_party = pd.DataFrame(columns=["_party", "Previous Business"])

        customer_insights = current_party.merge(
            previous_party, on="_party", how="left"
        ).fillna({"Previous Business": 0})
        customer_insights["Business Cr"] = (
            customer_insights["Current Business"] / revenue_divisor
        ).round(2)
        customer_total_revenue = customer_insights["Current Business"].sum()
        customer_insights["Share %"] = (
            customer_insights["Current Business"] / customer_total_revenue * 100
            if customer_total_revenue > 0 else 0
        )
        customer_insights["Growth %"] = customer_insights.apply(
            lambda row: pct_growth(row["Current Business"], row["Previous Business"])
            if row["Previous Business"] > 0 else None,
            axis=1,
        )
        customer_insights = (
            customer_insights.sort_values("Current Business", ascending=False)
            .reset_index(drop=True)
        )

        with party_layout_col:
            with st.container(border=True):
                customer_title_col, customer_selector_col = st.columns(
                    [4.2, 1.0],
                    gap="small",
                    vertical_alignment="center",
                )

                with customer_selector_col:
                    customer_top_n = st.selectbox(
                        "Customers to display",
                        TOP_N_OPTIONS,
                        index=0,
                        format_func=lambda value: f"Top {value}",
                        key="top_customer_n",
                        label_visibility="collapsed",
                    )

                with customer_title_col:
                    st.markdown(
                        f"<div style='font-size:18px;font-weight:400;color:#0f2744;margin:1px 0 9px 2px;'>Top {customer_top_n} Customers by Business</div>"
                        f"<div style='font-size:12px;font-weight:400;color:#64748b;margin-top:-4px;'>"
                        f"Customer basis: {party_label} | Current FY revenue, share and YoY movement."
                        "</div>",
                        unsafe_allow_html=True,
                    )

                customer_insights = (
                    customer_insights.head(customer_top_n)
                    .reset_index(drop=True)
                )

                if customer_insights.empty:
                    st.info("No customer revenue is available for the selected filters.")
                else:
                    max_customer_revenue = max(
                        customer_insights["Business Cr"].max(), 1
                    )
                    customer_rows = []

                    for idx, row in customer_insights.iterrows():
                        revenue_cr = float(row["Business Cr"] or 0)
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
                            table-layout:fixed; font-size:12px; color:#334155;
                        }}
                        .customer-insight-table th {{
                            padding:7px 6px; background:#f8fafc;
                            color:#64748b; font-size:12px; font-weight:400;
                            text-align:left; border-bottom:1px solid #e2e8f0;
                            white-space:nowrap;
                        }}
                        .customer-insight-table td {{
                            padding:8px 6px; border-bottom:1px solid #edf2f7;
                            vertical-align:middle;
                        }}
                        .customer-insight-table tr:last-child td {{border-bottom:0;}}
                        .customer-insight-table tbody tr:hover {{background:#f8fbff;}}
                        
                        .cust-rank {{
                            width:4%; padding-left:2px !important; padding-right:2px !important;
                            text-align:center; font-weight:400; color:#64748b;
                        }}
                        .cust-name {{
                            width:38%; padding-left:3px !important;
                            font-weight:400; color:#1e293b;
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                        }}
                        .cust-revenue {{width:32%;}}
                        .cust-value {{font-weight:400; color:#0f172a; margin-bottom:3px;}}
                        .cust-bar-track {{
                            width:100%; height:5px; border-radius:999px;
                            background:#e8eef8; overflow:hidden;
                        }}
                        .cust-bar-fill {{
                            height:5px; border-radius:999px;
                            background:linear-gradient(90deg,#60a5fa,#2563eb);
                        }}
                        .cust-share {{width:12%; text-align:right; font-weight:400; color:#475569;}}
                        .cust-yoy {{width:14%; text-align:right;}}
                        .cust-growth {{
                            display:inline-block; min-width:50px; text-align:right;
                            font-size:11px; font-weight:400;
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
                                    <th>Business ({revenue_unit})</th>
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
                    "Customers could not be displayed because a matching "
                    f"{party_label.lower()} column was not found in the booking dataset."
                )

                                                                           
                                                           
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

        separators = [" → ", "→", " -> ", "->", " - ", " TO ", " to "]
        for separator in separators:
            if separator in route_text:
                parts = [part.strip() for part in route_text.split(separator) if part.strip()]
                if len(parts) >= 2:
                    return " → ".join(reversed(parts))

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
            .reset_index(name="Current Business")
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
                .reset_index(name="Previous Business")
            )
        else:
            previous_routes = pd.DataFrame(columns=["_route", "Previous Business"])

        route_yoy = current_routes.merge(
            previous_routes,
            on="_route",
            how="left",
        ).fillna({"Previous Business": 0})

        route_yoy["Business Cr"] = (route_yoy["Current Business"] / revenue_divisor).round(2)
        route_total_revenue = route_yoy["Current Business"].sum()
        route_yoy["Share %"] = (
            route_yoy["Current Business"] / route_total_revenue * 100
            if route_total_revenue > 0 else 0
        )
        route_yoy["Growth %"] = route_yoy.apply(
            lambda row: pct_growth(row["Current Business"], row["Previous Business"])
            if row["Previous Business"] > 0 else None,
            axis=1,
        )

        route_yoy = (
            route_yoy.sort_values("Current Business", ascending=False)
            .reset_index(drop=True)
        )

        with route_layout_col:
            with st.container(border=True):
                route_title_col, route_selector_col = st.columns(
                    [4.2, 1.0],
                    gap="small",
                    vertical_alignment="center",
                )

                with route_selector_col:
                    route_top_n = st.selectbox(
                        "Routes to display",
                        TOP_N_OPTIONS,
                        index=0,
                        format_func=lambda value: f"Top {value}",
                        key="top_route_n",
                        label_visibility="collapsed",
                    )

                with route_title_col:
                    st.markdown(
                        f"<div style='font-size:18px;font-weight:400;color:#0f2744;margin:1px 0 9px 2px;'>Top {route_top_n} Routes by Business</div>"
                        "<div style='font-size:12px;font-weight:400;color:#64748b;margin-top:-4px;'>"
                        + ("Origin → Destination" if view_type == "Origin" else "Destination → Origin")
                        + " | Current FY revenue, share and YoY movement.</div>",
                        unsafe_allow_html=True,
                    )

                route_yoy = (
                    route_yoy.head(route_top_n)
                    .reset_index(drop=True)
                )

                if route_yoy.empty:
                    st.info("No route data is available for the selected filters.")
                else:
                    max_route_revenue = max(route_yoy["Business Cr"].max(), 1)
                    route_rows = []

                    for idx, row in route_yoy.iterrows():
                        revenue_cr = float(row["Business Cr"] or 0)
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
                            table-layout:fixed; font-size:12px; color:#334155;
                        }}
                        .route-insight-table th {{
                            padding:7px 6px; background:#f8fafc;
                            color:#64748b; font-size:12px; font-weight:400;
                            text-align:left; border-bottom:1px solid #e2e8f0;
                            white-space:nowrap;
                        }}
                        .route-insight-table td {{
                            padding:8px 6px; border-bottom:1px solid #edf2f7;
                            vertical-align:middle;
                        }}
                        .route-insight-table tr:last-child td {{border-bottom:0;}}
                        .route-insight-table tbody tr:hover {{background:#f8fbff;}}
                        
                        .route-rank {{
                            width:4%; padding-left:2px !important; padding-right:2px !important;
                            text-align:center; font-weight:400; color:#64748b;
                        }}
                        .route-name {{
                            width:38%; padding-left:3px !important;
                            font-weight:400; color:#1e293b;
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
                        }}
                        .route-revenue {{width:32%;}}
                        .route-value {{font-weight:400; color:#0f172a; margin-bottom:3px;}}
                        .route-bar-track {{
                            width:100%; height:5px; border-radius:999px;
                            background:#e8eef8; overflow:hidden;
                        }}
                        .route-bar-fill {{
                            height:5px; border-radius:999px;
                            background:linear-gradient(90deg,#2dd4bf,#0f766e);
                        }}
                        .route-share {{width:12%; text-align:right; font-weight:400; color:#475569;}}
                        .route-yoy {{width:14%; text-align:right;}}
                        .route-growth {{
                            display:inline-block; min-width:50px; text-align:right;
                            font-size:11px; font-weight:400;
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
                                    <th>Business ({revenue_unit})</th>
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
                    "Routes could not be displayed because the route column was not found "
                    "in the booking dataset."
                )

    compact_spacer()

    branch_summary = (
        df.groupby("branch")
        .agg(
            Business=("REVENUE", "sum"),
            GR_Count=("grno", "count"),
            Weight=("aweight", "sum"),
            FTL=("REVENUE", lambda x: x[df.loc[x.index, "LOADTYPE"] == "FTL"].sum()),
            LTL=("REVENUE", lambda x: x[df.loc[x.index, "LOADTYPE"] == "LTL"].sum())
        )
        .reset_index()
    )

    if prev_df is not None and not prev_df.empty and "branch" in prev_df.columns:
        prev_branch_summary = (
            prev_df.groupby("branch", dropna=False)["REVENUE"]
            .sum()
            .reset_index(name="LY_Business")
        )
    else:
        prev_branch_summary = pd.DataFrame(columns=["branch", "LY_Business"])

    branch_summary = branch_summary.merge(prev_branch_summary, on="branch", how="left")
    branch_summary["LY_Business"] = pd.to_numeric(
        branch_summary["LY_Business"], errors="coerce"
    ).fillna(0.0)

                                                                                 

    current_month_count = max(int(df["FIN_MONTH"].dropna().nunique()), 1)
    previous_month_count = (
        max(int(prev_df["FIN_MONTH"].dropna().nunique()), 1)
        if prev_df is not None and not prev_df.empty and "FIN_MONTH" in prev_df.columns
        else current_month_count
    )
    branch_summary["Monthly_Avg_Business"] = branch_summary["Business"] / current_month_count
    branch_summary["LY_Monthly_Avg_Business"] = branch_summary["LY_Business"] / previous_month_count

                                                                        
    business_slab_options = [
        "All",
        "₹0–5 Lac",
        "₹5–10 Lac",
        "₹10–15 Lac",
        "₹15–25 Lac",
        "₹25–50 Lac",
        "₹50 Lac & Above",
    ]

    selected_business_slab = st.session_state.get(
        "branch_business_slab_value",
        st.session_state.get("top_branch_business_slab", "All"),
    )

    slab_ranges = {
        "All": (None, None),
        "₹0–5 Lac": (0, 500000),
        "₹5–10 Lac": (500000, 1000000),
        "₹10–15 Lac": (1000000, 1500000),
        "₹15–25 Lac": (1500000, 2500000),
        "₹25–50 Lac": (2500000, 5000000),
        "₹50 Lac & Above": (5000000, None),
    }

                                                                               
                                                                       
    if selected_business_slab not in slab_ranges:
        selected_business_slab = "All"
        st.session_state["branch_business_slab_value"] = "All"
        st.session_state["top_branch_business_slab"] = "All"

    slab_min, slab_max = slab_ranges.get(selected_business_slab, (None, None))
    top_branch_pool = branch_summary.copy()

    if slab_min is not None:
        top_branch_pool = top_branch_pool[top_branch_pool["Monthly_Avg_Business"] >= slab_min]
    if slab_max is not None:
                                                                            
        top_branch_pool = top_branch_pool[top_branch_pool["Monthly_Avg_Business"] < slab_max]

    branch_rank_df = (
        top_branch_pool
        .sort_values("Monthly_Avg_Business", ascending=False)
        .copy()
    )
    branch_rank_df["Business Cr"] = (
        branch_rank_df["Monthly_Avg_Business"] / revenue_divisor
    ).round(2)

    b1, b2 = st.columns([1.25, 0.80], gap="medium")

    with b1:
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:16px;font-weight:400;color:#0f2744;margin:1px 0 7px 2px;'>"
                "Branches by Monthly Avg Business</div>",
                unsafe_allow_html=True,
            )

                                                                       
            slab_button_cols = st.columns(len(business_slab_options), gap="small")
            for slab_index, slab_label in enumerate(business_slab_options):
                with slab_button_cols[slab_index]:
                    is_active_slab = slab_label == selected_business_slab
                    if st.button(
                        slab_label,
                        key=f"branch_slab_btn_{slab_index}",
                        type="primary" if is_active_slab else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["branch_business_slab_value"] = slab_label
                        st.session_state["top_branch_business_slab"] = slab_label
                        selected_business_slab = slab_label
                        st.rerun()

                                                     
            slab_min, slab_max = slab_ranges.get(selected_business_slab, (None, None))
            top_branch_pool = branch_summary.copy()
            if slab_min is not None:
                top_branch_pool = top_branch_pool[top_branch_pool["Monthly_Avg_Business"] >= slab_min]
            if slab_max is not None:
                top_branch_pool = top_branch_pool[top_branch_pool["Monthly_Avg_Business"] < slab_max]

            branch_rank_df = (
                top_branch_pool
                .sort_values("Monthly_Avg_Business", ascending=False)
                .copy()
            )
            branch_rank_df["Business Cr"] = (
                branch_rank_df["Monthly_Avg_Business"] / revenue_divisor
            ).round(2)

            if branch_rank_df.empty:
                st.info(f"No branch falls in the {selected_business_slab} business slab.")
            else:
                total_branch_business = float(branch_summary["Monthly_Avg_Business"].sum())
                selected_branch_business = float(branch_rank_df["Monthly_Avg_Business"].sum())
                selected_ly_business = float(branch_rank_df["LY_Monthly_Avg_Business"].sum())
                selected_business_share = (
                    selected_branch_business / total_branch_business * 100
                    if total_branch_business else 0.0
                )
                selected_growth = pct_growth(selected_branch_business, selected_ly_business)
                selected_business_display = format_revenue(
                    selected_branch_business, conversion_type
                )
                selected_ly_display = format_revenue(
                    selected_ly_business, conversion_type
                )
                selected_growth_arrow = "▲" if selected_growth >= 0 else "▼"
                selected_growth_color = "#16a34a" if selected_growth >= 0 else "#dc2626"

                st.markdown(
                    f'<div style="color:#2563eb;font-size:12px;font-weight:500;margin:2px 0 7px 1px;">'
                    f'Showing {len(branch_rank_df)} branches in {selected_business_slab}. '
                    f'CY Monthly Avg: ₹{selected_business_display} · LY Monthly Avg: ₹{selected_ly_display} · '
                    f'Share: {selected_business_share:.2f}% · '
                    f'<span style="color:{selected_growth_color};font-weight:700;">'
                    f'Growth: {selected_growth_arrow} {abs(selected_growth):.1f}%</span>. Scroll to view all.'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                branch_rank_df["CY_Display"] = branch_rank_df["Monthly_Avg_Business"] / revenue_divisor
                branch_rank_df["LY_Display"] = branch_rank_df["LY_Monthly_Avg_Business"] / revenue_divisor
                branch_rank_df["Share_Pct"] = (
                    branch_rank_df["Monthly_Avg_Business"] / total_branch_business * 100
                    if total_branch_business else 0.0
                )
                branch_rank_df["Growth_Pct"] = branch_rank_df.apply(
                    lambda row: pct_growth(row["Monthly_Avg_Business"], row["LY_Monthly_Avg_Business"]), axis=1
                )
                max_cy = float(branch_rank_df["CY_Display"].max() or 1)

                header_html = (
                    '<div style="display:grid;grid-template-columns:42px minmax(155px,1.15fr) '
                    'minmax(180px,2.1fr) 95px 95px 72px 78px;gap:8px;align-items:center;'
                    'padding:0 8px 7px 8px;border-bottom:1px solid #dbe4ef;color:#52667d;'
                    'font-size:10px;font-weight:700;">'
                    '<div style="text-align:center;">#</div><div>Branch</div><div>Scale</div>'
                    '<div style="text-align:right;">CY Avg</div>'
                    '<div style="text-align:right;">LY Avg</div>'
                    '<div style="text-align:right;">Share</div>'
                    '<div style="text-align:right;">Growth</div></div>'
                )

                rows = []
                for i, row in branch_rank_df.reset_index(drop=True).iterrows():
                    cy_value = float(row["CY_Display"] or 0)
                    ly_value = float(row["LY_Display"] or 0)
                    share_value = float(row["Share_Pct"] or 0)
                    growth_value = float(row["Growth_Pct"] or 0)
                    bar_width = min((cy_value / max_cy * 100), 100) if max_cy else 0
                    growth_arrow = "▲" if growth_value >= 0 else "▼"
                    growth_color = "#16a34a" if growth_value >= 0 else "#dc2626"
                    rows.append(
                        f'<div style="display:grid;grid-template-columns:42px minmax(155px,1.15fr) '
                        f'minmax(180px,2.1fr) 95px 95px 72px 78px;gap:8px;align-items:center;'
                        f'padding:9px 8px;margin:0 0 6px 0;border:1px solid #e1e7ef;border-radius:11px;'
                        f'background:#fbfdff;font-size:11px;">'
                        f'<div style="text-align:center;color:#52667d;">{i + 1}</div>'
                        f'<div title="{escape(str(row["branch"]))}" style="font-weight:600;color:#102a43;'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{escape(str(row["branch"]))}</div>'
                        f'<div style="height:7px;background:#e8edf4;border-radius:999px;overflow:hidden;">'
                        f'<div style="height:100%;width:{bar_width:.1f}%;background:#7c3aed;border-radius:999px;"></div></div>'
                        f'<div style="text-align:right;font-weight:700;color:#0f172a;">₹{cy_value:.2f} {revenue_unit}</div>'
                        f'<div style="text-align:right;color:#64748b;">₹{ly_value:.2f} {revenue_unit}</div>'
                        f'<div style="text-align:right;font-weight:700;color:#6d28d9;">{share_value:.2f}%</div>'
                        f'<div style="text-align:right;font-weight:700;color:{growth_color};white-space:nowrap;">'
                        f'{growth_arrow} {abs(growth_value):.1f}%</div></div>'
                    )

                branch_scroll_html = (
                    '<div style="height:285px;overflow-y:auto;overflow-x:auto;padding:1px 5px 1px 0;'
                    'scrollbar-gutter:stable;">' + header_html + ''.join(rows) + '</div>'
                )
                if hasattr(st, "html"):
                    st.html(branch_scroll_html)
                else:
                    st.markdown(branch_scroll_html, unsafe_allow_html=True)

    with b2:
        _render_operational_highlights(df, prev_df)

    compact_spacer()

                                                                                        
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

                                                      
                                                           
    network_toggle_key = "show_branch_agency_network_changes"
    if network_toggle_key not in st.session_state:
        st.session_state[network_toggle_key] = False

    network_button_label = (
        "▼ Collapse Branch/Agency Network Changes"
        if st.session_state[network_toggle_key]
        else "▶ Expand Branch/Agency Network Changes"
    )

    if st.button(
        network_button_label,
        key="branch_agency_network_changes_button",
        width="content",
    ):
        st.session_state[network_toggle_key] = not st.session_state[network_toggle_key]
        st.rerun()

                                                                                      
    if st.session_state[network_toggle_key]:
        filtered_station_df = station_df.copy()

        if "FIN_MONTH" in filtered_station_df.columns and filtered_station_df["FIN_MONTH"].notna().any():
            if month != "All":
                fin_month_for_month = [k for k, v in month_map.items() if v == month]
                if fin_month_for_month:
                    filtered_station_df = filtered_station_df[
                        filtered_station_df["FIN_MONTH"].isin(fin_month_for_month)
                    ]
            elif quarter != "All":
                quarter_fin_months = [k for k, v in QUARTER_MAP.items() if v == quarter]
                filtered_station_df = filtered_station_df[
                    filtered_station_df["FIN_MONTH"].isin(quarter_fin_months)
                ]

        station_status = filtered_station_df["STATUS"].astype(str).str.upper()
        opened_df = filtered_station_df[station_status.eq("OPENED")].copy()
        closed_df = filtered_station_df[station_status.eq("CLOSED")].copy()

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

        booking_date_col = _find_normalized_column(df, "grdt")
        booking_branch_col = _find_normalized_column(df, "branch")
        revenue_rows = []

        if not opened_df.empty and booking_date_col and booking_branch_col:
            opened_df["activedate"] = pd.to_datetime(opened_df["activedate"], errors="coerce")

            booking_columns = [
                c for c in [booking_date_col, booking_branch_col, "REVENUE", "grno", "aweight"]
                if c in df.columns
            ]
            booking_work = df[booking_columns].copy()
            if not pd.api.types.is_datetime64_any_dtype(booking_work[booking_date_col]):
                booking_work[booking_date_col] = pd.to_datetime(
                    booking_work[booking_date_col], errors="coerce"
                )
            booking_work["_branch_key"] = booking_work[booking_branch_col].map(_normalise_key)

            branch_groups = {
                key: group
                for key, group in booking_work.groupby("_branch_key", sort=False)
                if key
            }

                                                                                  
            fy_start_date = pd.to_datetime(start_date).normalize()
            fy_end_date = pd.to_datetime(end_date).normalize()

            selected_period_start = fy_start_date
            selected_period_end = fy_end_date

            if month != "All":
                selected_fin_month = next(
                    (fin_month for fin_month, month_name in month_map.items() if month_name == month),
                    None,
                )
                if selected_fin_month is not None:
                    selected_period_start = fy_start_date + pd.DateOffset(months=selected_fin_month - 1)
                    selected_period_end = selected_period_start + pd.offsets.MonthEnd(1)
            elif quarter != "All":
                quarter_start_month = {
                    "Q1": 1,
                    "Q2": 4,
                    "Q3": 7,
                    "Q4": 10,
                }.get(quarter, 1)
                selected_period_start = fy_start_date + pd.DateOffset(months=quarter_start_month - 1)
                selected_period_end = selected_period_start + pd.DateOffset(months=3) - pd.Timedelta(days=1)

            selected_period_start = pd.to_datetime(selected_period_start).normalize()
            selected_period_end = min(
                pd.to_datetime(selected_period_end).normalize(),
                pd.Timestamp.today().normalize(),
            )

            for station in opened_df.itertuples(index=False):
                station_data = station._asdict()
                active_date = station_data.get("activedate")
                branch_name = station_data.get("BRANCH", "")
                branch_code = station_data.get("CODE", "")
                keys = {_normalise_key(branch_name), _normalise_key(branch_code)} - {""}

                frames = [branch_groups[key] for key in keys if key in branch_groups]
                if pd.notna(active_date):
                    active_date = pd.to_datetime(active_date).normalize()
                    effective_active_start = max(active_date, selected_period_start)
                else:
                    effective_active_start = pd.NaT

                if frames and pd.notna(effective_active_start) and effective_active_start <= selected_period_end:
                    matched = pd.concat(frames, ignore_index=False)
                    matched = matched[
                        matched[booking_date_col].between(
                            effective_active_start,
                            selected_period_end,
                            inclusive="both",
                        )
                    ]
                else:
                    matched = booking_work.iloc[0:0]

                active_days = (
                    max((selected_period_end - effective_active_start).days + 1, 0)
                    if pd.notna(effective_active_start) and effective_active_start <= selected_period_end
                    else 0
                )
                active_months = max(active_days / 30.44, 1) if active_days else 1
                revenue_value = float(matched["REVENUE"].sum()) if "REVENUE" in matched else 0.0
                gr_count = int(matched["grno"].count()) if "grno" in matched else len(matched)
                weight_mt = float(matched["aweight"].sum() / 1000) if "aweight" in matched else 0.0
                avg_monthly = revenue_value / active_months if active_days else 0.0
                revenue_per_day = revenue_value / active_days if active_days else 0.0

                if active_days < 30:
                    performance = "New - Monitoring"
                elif avg_monthly >= 500000:
                    performance = "Strong"
                elif avg_monthly >= 100000:
                    performance = "Progressing"
                else:
                    performance = "Needs Attention"

                revenue_rows.append({
                    "ZONE": station_data.get("ZONE", ""),
                    "TYPE": station_data.get("TYPE", ""),
                    "BRANCH": branch_name,
                    "CODE": branch_code,
                    "CITY": station_data.get("CITY", ""),
                    "STATE": station_data.get("STATE", ""),
                    "Active Date": active_date,
                    "Active Days": active_days,
                    "GR Count": gr_count,
                    "Weight MT": round(weight_mt, 1),
                    f"Business ({revenue_unit})": round(revenue_value / revenue_divisor, 2),
                    f"Avg Monthly Business ({revenue_unit})": round(avg_monthly / revenue_divisor, 2),
                    "Business / Day": round(revenue_per_day, 0),
                    "Performance": performance,
                })

        opened_revenue_df = pd.DataFrame(revenue_rows)
        total_new_revenue = opened_revenue_df.get(
            f"Business ({revenue_unit})", pd.Series(dtype=float)
        ).sum()
        total_new_gr = opened_revenue_df.get("GR Count", pd.Series(dtype=float)).sum()
        avg_new_monthly = opened_revenue_df.get(
            f"Avg Monthly Business ({revenue_unit})", pd.Series(dtype=float)
        ).sum()
        productive_count = int(
            opened_revenue_df.get("Performance", pd.Series(dtype=str))
            .isin(["Strong", "Progressing"])
            .sum()
        )

        with st.container(border=True):
            st.markdown(
                f"<div style='font-size:16px;font-weight:950;color:#0f2744;'>"
                f"🏢 Branch/Agency Network Changes ({period_label})</div>"
                "<div style='font-size:10px;color:#64748b;margin:2px 0 9px;'>"
                "Active Days and business are calculated only within the selected FY, quarter or month."
                "</div>",
                unsafe_allow_html=True,
            )
            n1, n2, n3, n4, n5, n6 = st.columns(6, gap="small")
            n1.metric("Opened", f"{opened_branches:,}")
            n2.metric("Closed", f"{closed_branches:,}")
            n3.metric("Net Increase", f"{net_increase:+,}")
            n4.metric(f"New Business ({revenue_unit})", f"{total_new_revenue:,.2f}")
            n5.metric("New-Branch GR", f"{int(total_new_gr):,}")
            n6.metric("Productive Locations", f"{productive_count}/{opened_branches}")

            if opened_revenue_df.empty:
                st.info("No newly opened branch/agency records are available for the selected period.")
            else:
                st.dataframe(
                    opened_revenue_df.sort_values(
                        f"Business ({revenue_unit})", ascending=False
                    ),
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Active Date": st.column_config.DateColumn(format="DD-MMM-YYYY"),
                        f"Business ({revenue_unit})": st.column_config.NumberColumn(format="%.2f"),
                        f"Avg Monthly Business ({revenue_unit})": st.column_config.NumberColumn(format="%.2f"),
                        "Business / Day": st.column_config.NumberColumn(format="₹ %.0f"),
                        "Weight MT": st.column_config.NumberColumn(format="%.1f"),
                    },
                )
                st.caption(
                    f"Combined average monthly revenue of new locations: "
                    f"{avg_new_monthly:,.2f} {revenue_unit}. "
                    "Performance bands: Strong ≥ ₹5 lakh/month; "
                    "Progressing ≥ ₹1 lakh/month; below this Needs Attention."
                )

            with st.expander(f"🔒 View Closed Branch Details ({closed_branches})"):
                closed_columns = [
                    c for c in ["ZONE", "TYPE", "BRANCH", "CODE", "CITY", "STATE", "closedate"]
                    if c in closed_df.columns
                ]
                st.dataframe(closed_df[closed_columns], width="stretch", hide_index=True)
