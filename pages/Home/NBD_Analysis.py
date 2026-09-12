import gc
import html
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st

from services.data_CustomerAnalysis import load_booking_data


# =====================================================
# Constants / styling
# =====================================================
BLUE = "#2563eb"
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#d97706"
PURPLE = "#7c3aed"


def apply_nbd_style() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 100% !important;
            padding: .45rem .75rem 1.1rem !important;
        }
        div[data-testid="stVerticalBlock"] { gap: .45rem !important; }
        div[data-testid="stHorizontalBlock"] { gap: .55rem !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 11px !important;
            border: 1px solid #dbe4ef !important;
            box-shadow: 0 3px 10px rgba(15,42,67,.06) !important;
            background: #fff !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: .65rem .75rem !important;
        }
        .nbd-title {
            color:#102a43;
            font-size:21px;
            font-weight:850;
            line-height:1.15;
            margin:0;
        }
        .nbd-subtitle {
            color:#64748b;
            font-size:11px;
            margin-top:3px;
        }
        .nbd-period-badge {
            display:inline-block;
            padding:4px 8px;
            border-radius:999px;
            background:#ecfdf5;
            color:#166534;
            border:1px solid #bbf7d0;
            font-size:10px;
            font-weight:800;
            letter-spacing:.15px;
        }
        .nbd-kpi {
            background:#fff;
            border:1px solid #e2e8f0;
            border-left:4px solid var(--accent,#2563eb);
            border-radius:10px;
            padding:8px 10px;
            min-height:72px;
            box-shadow:0 2px 7px rgba(15,23,42,.05);
        }
        .nbd-kpi-title {font-size:10.5px;color:#64748b;font-weight:750;}
        .nbd-kpi-value {font-size:18px;color:#0f172a;font-weight:900;margin-top:2px;white-space:nowrap;}
        .nbd-kpi-note {font-size:10px;color:#64748b;margin-top:2px;}
        .nbd-section-title {font-size:14px;font-weight:850;color:#0f2744;margin-bottom:5px;}
        div[data-testid="stDataFrame"] * { font-size: 10.5px !important; }
        div[data-testid="stDownloadButton"] button,
        div[data-testid="stButton"] button {
            min-height:38px !important;
            border-radius:8px !important;
            font-size:11px !important;
            font-weight:750 !important;
        }
        @media (max-width: 768px) {
            .block-container {padding:.35rem .45rem .8rem !important;}
            div[data-testid="stHorizontalBlock"] {
                flex-direction:column !important;
                align-items:stretch !important;
            }
            div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
                width:100% !important; min-width:100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# Data normalization
# =====================================================
def _compact_name(value) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _first_existing_column(df: pd.DataFrame, candidates) -> str | None:
    if df is None or df.empty:
        return None
    compact_map = {_compact_name(col): col for col in df.columns}
    for candidate in candidates:
        hit = compact_map.get(_compact_name(candidate))
        if hit is not None:
            return hit
    return None


def normalize_nbd_data(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()

    df = df.copy()
    rename_candidates = {
        "Zone": ["zone"],
        "Circle": ["circle"],
        "Branch": ["branch", "branchname"],
        "Consignor": ["consignor", "consignorname", "cngrname"],
        "ConsignorCode": ["cngrcode", "consignorcode", "cngrcode"],
        "Consignee": ["consignee", "consigneename", "cngeename"],
        "ConsigneeCode": ["cngecode", "consigneecode", "cngeecode"],
        "Revenue": ["revenue", "freight", "business", "sale", "sales"],
        "LoadType": ["loadtype", "load_type", "servicetype", "service_type"],
        "BusinessDate": [
            "businessdate", "bookingdate", "bookingdt", "grdt", "grdate",
            "gr_date", "lrdate", "lr_date", "cndate", "docketdate",
        ],
        "Mobile": [
            "mobile", "mobileno", "mobile_no", "mobilenumber", "phone",
            "phoneno", "phone_no", "contact", "contactno", "contact_no",
        ],
        "GSTIN": ["gstin", "gst", "gstno", "gst_no", "gstnumber", "gst_number"],
    }

    compact_map = {_compact_name(col): col for col in df.columns}
    rename_map = {}
    for target, candidates in rename_candidates.items():
        if target in df.columns:
            continue
        for candidate in candidates:
            source = compact_map.get(_compact_name(candidate))
            if source is not None and source != target:
                rename_map[source] = target
                break
    if rename_map:
        df = df.rename(columns=rename_map)

    if "Revenue" in df.columns:
        df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0.0)

    if "LoadType" not in df.columns:
        df["LoadType"] = ""
    else:
        df["LoadType"] = df["LoadType"].fillna("").astype(str).str.strip()

    if "BusinessDate" in df.columns:
        df["BusinessDate"] = pd.to_datetime(df["BusinessDate"], errors="coerce", dayfirst=True)

    for col in ("Zone", "Circle", "Branch", "Consignor", "Consignee", "Mobile", "GSTIN"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    return df


# =====================================================
# Data loading
# =====================================================
@st.cache_data(show_spinner=False, ttl=900, max_entries=8)
def _load_period(start_iso: str, end_iso: str, view_type: str) -> pd.DataFrame:
    raw = load_booking_data(start_iso, end_iso, view_type)
    return normalize_nbd_data(raw)


def _clear_nbd_result() -> None:
    for key in (
        "nbd_current_df",
        "nbd_compare_df",
        "nbd_run_signature",
        "nbd_report_ready",
    ):
        st.session_state.pop(key, None)
    gc.collect()


# =====================================================
# Business logic
# =====================================================
def _customer_config(view_type: str) -> dict:
    if view_type == "origin":
        return {
            "code": "ConsignorCode",
            "name": "Consignor",
            "label": "Consignor",
        }
    return {
        "code": "ConsigneeCode",
        "name": "Consignee",
        "label": "Consignee",
    }


def _validate_columns(df: pd.DataFrame, view_type: str, period_name: str) -> tuple[bool, str]:
    config = _customer_config(view_type)
    required = [config["code"], config["name"], "Revenue"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        return False, f"{period_name}: stored procedure is missing required columns: {missing}. Available columns: {list(df.columns)}"
    return True, ""


def _canon(value) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _match_scope_value(df: pd.DataFrame, column: str, value):
    if value in (None, "") or column not in df.columns or df.empty:
        return None
    target = _canon(value)
    normalized = df[column].fillna("").astype(str).map(_canon)
    matched = df.loc[normalized.eq(target), column]
    return matched.iloc[0] if not matched.empty else value


def apply_role_scope(df: pd.DataFrame) -> pd.DataFrame:
    """Apply login data_scope used elsewhere in the dashboard."""
    if df is None or df.empty:
        return df

    scope = st.session_state.get("data_scope", {}) or {}
    scoped = df

    for scope_key, column in (("zone", "Zone"), ("circle", "Circle"), ("branch", "Branch")):
        requested = scope.get(scope_key)
        if requested and column in scoped.columns:
            exact = _match_scope_value(scoped, column, requested)
            target = _canon(exact)
            normalized = scoped[column].fillna("").astype(str).map(_canon)
            scoped = scoped[normalized.eq(target)]

    return scoped


def _safe_options(frames, column: str) -> list[str]:
    values = set()
    for frame in frames:
        if frame is not None and not frame.empty and column in frame.columns:
            cleaned = frame[column].dropna().astype(str).str.strip()
            values.update(v for v in cleaned if v)
    return sorted(values, key=str.casefold)


def _apply_multi(df: pd.DataFrame, column: str, values) -> pd.DataFrame:
    if df is None or df.empty or column not in df.columns or not values:
        return df
    return df[df[column].isin(values)]


def _apply_common_filters(
    df: pd.DataFrame,
    zones,
    circles,
    branches,
    load_types,
    customers,
    customer_name_col: str,
) -> pd.DataFrame:
    filtered = df
    filtered = _apply_multi(filtered, "Zone", zones)
    filtered = _apply_multi(filtered, "Circle", circles)
    filtered = _apply_multi(filtered, "Branch", branches)
    filtered = _apply_multi(filtered, "LoadType", load_types)
    filtered = _apply_multi(filtered, customer_name_col, customers)
    return filtered


def _first_non_blank(series: pd.Series) -> str:
    for value in series:
        if pd.notna(value):
            text = str(value).strip()
            if text and text.lower() not in {"nan", "none"}:
                return text
    return ""


def _load_group(load_type: str) -> str:
    text = _compact_name(load_type)
    if "ftl" in text:
        return "FTL"
    # PTL is included with LTL for this NBD report because both represent
    # part-load business. If your source uses only LTL, this has no effect.
    if "ltl" in text or "ptl" in text:
        return "LTL"
    return "OTHER"


def _period_customer_summary(
    df: pd.DataFrame,
    code_col: str,
    name_col: str,
    prefix: str,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=[code_col, name_col])

    work = df.copy()
    work["__LoadGroup"] = work["LoadType"].map(_load_group)

    keys = [code_col]
    base = work.groupby(keys, as_index=False).agg(**{f"{prefix} Sale": ("Revenue", "sum")})

    for group_name in ("LTL", "FTL"):
        part = (
            work[work["__LoadGroup"] == group_name]
            .groupby(keys, as_index=False)
            .agg(**{f"{prefix} {group_name}": ("Revenue", "sum")})
        )
        base = base.merge(part, on=keys, how="left")

    names = work.groupby(code_col, as_index=False).agg(**{name_col: (name_col, _first_non_blank)})
    base = base.merge(names, on=code_col, how="left")

    for col in (f"{prefix} LTL", f"{prefix} FTL"):
        if col not in base.columns:
            base[col] = 0.0
        base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0.0)

    return base


def build_nbd_report(
    current_df: pd.DataFrame,
    compare_df: pd.DataFrame,
    view_type: str,
) -> pd.DataFrame:
    config = _customer_config(view_type)
    code_col = config["code"]
    name_col = config["name"]

    current = _period_customer_summary(current_df, code_col, name_col, "Current")
    compare = _period_customer_summary(compare_df, code_col, name_col, "Compare")

    # Merge on code where possible. Name is refreshed from the period in which
    # the customer is present; this avoids duplicates when the spelling changed.
    current_by_code = current.drop(columns=[name_col], errors="ignore")
    compare_by_code = compare.drop(columns=[name_col], errors="ignore")

    codes = pd.DataFrame({code_col: pd.Index(
        set(current_by_code[code_col].dropna().tolist()) |
        set(compare_by_code[code_col].dropna().tolist())
    ).tolist()})

    report = codes.merge(compare_by_code, on=code_col, how="left").merge(current_by_code, on=code_col, how="left")

    numeric_cols = [
        "Compare Sale", "Compare LTL", "Compare FTL",
        "Current Sale", "Current LTL", "Current FTL",
    ]
    for col in numeric_cols:
        if col not in report.columns:
            report[col] = 0.0
        report[col] = pd.to_numeric(report[col], errors="coerce").fillna(0.0)

    # Customer name/details can come from either period. Current is preferred.
    detail_frames = []
    for frame, priority in ((compare_df, 1), (current_df, 2)):
        if frame is None or frame.empty:
            continue
        available = [code_col, name_col]
        for col in ("Zone", "Circle", "Branch", "Mobile", "GSTIN"):
            if col in frame.columns:
                available.append(col)
        detail = frame[available].copy()
        detail["__priority"] = priority
        detail_frames.append(detail)

    if detail_frames:
        details = pd.concat(detail_frames, ignore_index=True, sort=False)
        details = details.sort_values("__priority", ascending=False)
        agg_map = {name_col: _first_non_blank}
        for col in ("Zone", "Circle", "Branch", "Mobile", "GSTIN"):
            if col in details.columns:
                agg_map[col] = _first_non_blank
        details = details.groupby(code_col, as_index=False).agg(agg_map)
        report = report.merge(details, on=code_col, how="left")
    else:
        report[name_col] = ""

    report["Customer Type"] = ""
    report.loc[(report["Current Sale"] > 0) & (report["Compare Sale"] <= 0), "Customer Type"] = "NEW"
    report.loc[(report["Current Sale"] <= 0) & (report["Compare Sale"] > 0), "Customer Type"] = "LOST"
    report.loc[(report["Current Sale"] > 0) & (report["Compare Sale"] > 0), "Customer Type"] = "REGULAR"
    report = report[report["Customer Type"].ne("")].copy()

    report["Change"] = report["Current Sale"] - report["Compare Sale"]
    report["Growth %"] = report.apply(
        lambda r: ((r["Current Sale"] - r["Compare Sale"]) / r["Compare Sale"] * 100.0)
        if r["Compare Sale"] > 0 else (100.0 if r["Current Sale"] > 0 else 0.0),
        axis=1,
    )

    # Ensure optional display columns always exist.
    for col in ("Zone", "Circle", "Branch", "Mobile", "GSTIN"):
        if col not in report.columns:
            report[col] = ""

    display_cols = [
        "Zone", "Circle", "Branch", code_col, name_col, "Mobile", "GSTIN",
        "Compare Sale", "Compare LTL", "Compare FTL",
        "Current Sale", "Current LTL", "Current FTL",
        "Change", "Growth %", "Customer Type",
    ]
    report = report[display_cols]

    status_order = pd.Categorical(
        report["Customer Type"],
        categories=["NEW", "REGULAR", "LOST"],
        ordered=True,
    )
    report = report.assign(__status=status_order).sort_values(
        ["__status", "Current Sale", "Compare Sale"],
        ascending=[True, False, False],
    ).drop(columns="__status").reset_index(drop=True)

    return report


# =====================================================
# Export / formatting
# =====================================================
def _money(value: float) -> str:
    return f"Rs.{float(value or 0):,.0f}"


def _kpi(title: str, value: str, note: str, color: str) -> None:
    st.markdown(
        f"""
        <div class="nbd-kpi" style="--accent:{color};">
          <div class="nbd-kpi-title">{html.escape(title)}</div>
          <div class="nbd-kpi-value">{html.escape(value)}</div>
          <div class="nbd-kpi-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def export_nbd_excel(
    report_df: pd.DataFrame,
    current_start: date,
    current_end: date,
    compare_start: date,
    compare_end: date,
) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        export_df = report_df.copy()
        export_df.to_excel(writer, sheet_name="NBD MIS", index=False, startrow=4)

        workbook = writer.book
        worksheet = writer.sheets["NBD MIS"]

        title_fmt = workbook.add_format({
            "bold": True, "font_size": 15, "font_color": "#17365D",
        })
        period_fmt = workbook.add_format({
            "bold": True, "font_size": 10, "font_color": "#475569",
        })
        header_fmt = workbook.add_format({
            "bold": True, "bg_color": "#17365D", "font_color": "#FFFFFF",
            "border": 0, "align": "center", "valign": "vcenter",
        })
        money_fmt = workbook.add_format({"num_format": "#,##0.00;[Red](#,##0.00);-"})
        pct_fmt = workbook.add_format({"num_format": "0.0%;[Red](0.0%);-"})

        worksheet.write("A1", "SUGAM PARIVAHAN PVT. LTD. - NBD CUSTOMER MIS", title_fmt)
        worksheet.write(
            "A2",
            f"Current Period: {current_start:%d-%b-%Y} to {current_end:%d-%b-%Y}",
            period_fmt,
        )
        worksheet.write(
            "A3",
            f"Comparison Period: {compare_start:%d-%b-%Y} to {compare_end:%d-%b-%Y}",
            period_fmt,
        )

        for col_idx, col_name in enumerate(export_df.columns):
            worksheet.write(4, col_idx, col_name, header_fmt)
            width = max(12, min(28, len(str(col_name)) + 4))
            worksheet.set_column(col_idx, col_idx, width)

        for col_name in [
            "Compare Sale", "Compare LTL", "Compare FTL",
            "Current Sale", "Current LTL", "Current FTL", "Change",
        ]:
            if col_name in export_df.columns:
                idx = export_df.columns.get_loc(col_name)
                worksheet.set_column(idx, idx, 16, money_fmt)

        if "Growth %" in export_df.columns:
            idx = export_df.columns.get_loc("Growth %")
            # dataframe stores percent points (e.g. 25.0). Excel percent needs .25.
            for row_no, value in enumerate(export_df["Growth %"], start=5):
                worksheet.write_number(row_no, idx, float(value) / 100.0, pct_fmt)
            worksheet.set_column(idx, idx, 12, pct_fmt)

        worksheet.freeze_panes(5, 0)
        worksheet.autofilter(4, 0, 4 + len(export_df), max(0, len(export_df.columns) - 1))

    return output.getvalue()


# =====================================================
# UI helpers
# =====================================================
def _default_dates():
    today = date.today()
    # Current: first day of current month to today.
    current_start = today.replace(day=1)
    current_end = today
    # Comparison: previous 12 months ending the day before current start.
    compare_end = current_start - timedelta(days=1)
    compare_start = (pd.Timestamp(current_start) - pd.DateOffset(years=1)).date()
    return current_start, current_end, compare_start, compare_end


def _render_filters(
    current_df: pd.DataFrame,
    compare_df: pd.DataFrame,
    name_col: str,
    customer_only: bool = False,
):
    """Render filters for the selected NBD layout.

    Customer Only intentionally removes Zone/Circle/Branch slicers. Login
    data_scope is still enforced before this function, so users cannot bypass
    their assigned geography by choosing the customer-only layout.
    """
    scope = st.session_state.get("data_scope", {}) or {}
    frames = [current_df, compare_df]

    if customer_only:
        # No geography slicers in this view. The data has already been scoped
        # by apply_role_scope(), so only operational filters remain visible.
        zones, circles, branches = [], [], []
        c1, c2 = st.columns([1, 2], gap="small")
        with c1:
            load_types = st.multiselect(
                "Load Type",
                _safe_options(frames, "LoadType"),
                placeholder="All load types",
                key="nbd_customer_only_load_type",
            )
        load_frames = [_apply_multi(frame, "LoadType", load_types) for frame in frames]
        with c2:
            customers = st.multiselect(
                "Customer",
                _safe_options(load_frames, name_col),
                placeholder="All customers",
                key="nbd_customer_only_customer",
            )
        return zones, circles, branches, load_types, customers

    cols = st.columns([1, 1, 1.1, 1, 1.5], gap="small")

    with cols[0]:
        if scope.get("zone"):
            zones = [scope["zone"]]
            st.multiselect("Zone", zones, default=zones, disabled=True, key="nbd_geo_zone_locked")
        else:
            zones = st.multiselect(
                "Zone", _safe_options(frames, "Zone"), placeholder="All zones", key="nbd_geo_zone"
            )

    zone_frames = [_apply_multi(frame, "Zone", zones) for frame in frames]

    with cols[1]:
        if scope.get("circle"):
            circles = [scope["circle"]]
            st.multiselect("Circle", circles, default=circles, disabled=True, key="nbd_geo_circle_locked")
        else:
            circles = st.multiselect(
                "Circle", _safe_options(zone_frames, "Circle"), placeholder="All circles", key="nbd_geo_circle"
            )

    circle_frames = [_apply_multi(frame, "Circle", circles) for frame in zone_frames]

    with cols[2]:
        if scope.get("branch"):
            branches = [scope["branch"]]
            st.multiselect("Branch", branches, default=branches, disabled=True, key="nbd_geo_branch_locked")
        else:
            branches = st.multiselect(
                "Branch", _safe_options(circle_frames, "Branch"), placeholder="All branches", key="nbd_geo_branch"
            )

    branch_frames = [_apply_multi(frame, "Branch", branches) for frame in circle_frames]

    with cols[3]:
        load_types = st.multiselect(
            "Load Type",
            _safe_options(branch_frames, "LoadType"),
            placeholder="All load types",
            key="nbd_geo_load_type",
        )

    load_frames = [_apply_multi(frame, "LoadType", load_types) for frame in branch_frames]

    with cols[4]:
        customers = st.multiselect(
            "Customer",
            _safe_options(load_frames, name_col),
            placeholder="All customers",
            key="nbd_geo_customer",
        )

    return zones, circles, branches, load_types, customers


# =====================================================
# Main page
# =====================================================
def show_NBDAnalysis() -> None:
    apply_nbd_style()

    default_current_start, default_current_end, default_compare_start, default_compare_end = _default_dates()

    with st.container(border=True):
        title_col, mode_col = st.columns([5.2, 1.2], vertical_alignment="center")
        with title_col:
            st.markdown(
                "<div class='nbd-title'>NBD Customer Analysis</div>"
                "<div class='nbd-subtitle'>Independent manual-period comparison for NEW, LOST and REGULAR customers.</div>",
                unsafe_allow_html=True,
            )
        with mode_col:
            st.markdown("<span class='nbd-period-badge'>MANUAL PERIOD MODE</span>", unsafe_allow_html=True)

        d1, d2, d3, d4, view_col, layout_col, run_col = st.columns(
            [1, 1, 1, 1, .78, 1.18, 1.05], gap="small", vertical_alignment="bottom"
        )

        with d1:
            current_start = st.date_input(
                "Current From",
                value=st.session_state.get("nbd_current_start", default_current_start),
                key="nbd_current_start",
            )
        with d2:
            current_end = st.date_input(
                "Current To",
                value=st.session_state.get("nbd_current_end", default_current_end),
                key="nbd_current_end",
            )
        with d3:
            compare_start = st.date_input(
                "Comparison From",
                value=st.session_state.get("nbd_compare_start", default_compare_start),
                key="nbd_compare_start",
            )
        with d4:
            compare_end = st.date_input(
                "Comparison To",
                value=st.session_state.get("nbd_compare_end", default_compare_end),
                key="nbd_compare_end",
            )
        with view_col:
            view_type = st.selectbox(
                "View",
                ["origin", "destination"],
                format_func=lambda x: "Origin" if x == "origin" else "Destination",
                key="nbd_view_type",
            )
        with layout_col:
            report_layout = st.selectbox(
                "Report Layout",
                ["Customer + Geography", "Customer Only"],
                key="nbd_report_layout",
                help="Customer Only removes Zone, Circle and Branch from filters and output.",
            )
        with run_col:
            run_report = st.button("▶ Run NBD Report", type="primary", use_container_width=True)

    signature = (
        current_start.isoformat(), current_end.isoformat(),
        compare_start.isoformat(), compare_end.isoformat(), view_type,
    )

    if current_start > current_end:
        st.error("Current From cannot be after Current To.")
        return
    if compare_start > compare_end:
        st.error("Comparison From cannot be after Comparison To.")
        return

    if run_report:
        st.session_state["nbd_report_ready"] = False
        try:
            with st.spinner("Loading NBD current and comparison periods..."):
                current_df = _load_period(current_start.isoformat(), current_end.isoformat(), view_type)
                compare_df = _load_period(compare_start.isoformat(), compare_end.isoformat(), view_type)
        except Exception as exc:
            st.error(f"Unable to load NBD data: {exc}")
            return

        ok, message = _validate_columns(current_df, view_type, "Current period")
        if not ok:
            st.error(message)
            return
        ok, message = _validate_columns(compare_df, view_type, "Comparison period")
        if not ok:
            st.error(message)
            return

        current_df = apply_role_scope(current_df)
        compare_df = apply_role_scope(compare_df)

        st.session_state["nbd_current_df"] = current_df
        st.session_state["nbd_compare_df"] = compare_df
        st.session_state["nbd_run_signature"] = signature
        st.session_state["nbd_report_ready"] = True

    if not st.session_state.get("nbd_report_ready", False):
        st.info("Select the four manual dates and click ▶ Run NBD Report.")
        return

    if st.session_state.get("nbd_run_signature") != signature:
        st.warning("Period or View has changed. Click ▶ Run NBD Report to refresh the data.")
        return

    current_df = st.session_state.get("nbd_current_df", pd.DataFrame())
    compare_df = st.session_state.get("nbd_compare_df", pd.DataFrame())
    config = _customer_config(view_type)
    name_col = config["name"]

    customer_only = report_layout == "Customer Only"

    with st.container(border=True):
        filter_title = "Customer Filters" if customer_only else "Filters"
        st.markdown(f"<div class='nbd-section-title'>{filter_title}</div>", unsafe_allow_html=True)
        if customer_only:
            st.caption("Customer Only view: Zone, Circle and Branch are intentionally hidden. Login data-scope restrictions still apply in the background.")
        zones, circles, branches, load_types, customers = _render_filters(
            current_df, compare_df, name_col, customer_only=customer_only
        )

    current_filtered = _apply_common_filters(
        current_df, zones, circles, branches, load_types, customers, name_col
    )
    compare_filtered = _apply_common_filters(
        compare_df, zones, circles, branches, load_types, customers, name_col
    )

    report = build_nbd_report(current_filtered, compare_filtered, view_type)
    if customer_only and not report.empty:
        report = report.drop(columns=["Zone", "Circle", "Branch"], errors="ignore")

    total_customers = len(report)
    new_count = int((report["Customer Type"] == "NEW").sum()) if not report.empty else 0
    lost_count = int((report["Customer Type"] == "LOST").sum()) if not report.empty else 0
    regular_count = int((report["Customer Type"] == "REGULAR").sum()) if not report.empty else 0
    current_sale = float(report["Current Sale"].sum()) if not report.empty else 0.0
    compare_sale = float(report["Compare Sale"].sum()) if not report.empty else 0.0
    change = current_sale - compare_sale
    growth = ((change / compare_sale) * 100.0) if compare_sale > 0 else (100.0 if current_sale > 0 else 0.0)

    k1, k2, k3, k4, k5, k6, k7 = st.columns(7, gap="small")
    with k1: _kpi("Total Customers", f"{total_customers:,}", "Across both periods", BLUE)
    with k2: _kpi("New", f"{new_count:,}", "Current only", GREEN)
    with k3: _kpi("Regular", f"{regular_count:,}", "Active in both", PURPLE)
    with k4: _kpi("Lost", f"{lost_count:,}", "Comparison only", RED)
    with k5: _kpi("Current Business", _money(current_sale), f"{current_start:%d-%b-%Y} to {current_end:%d-%b-%Y}", BLUE)
    with k6: _kpi("Compare Business", _money(compare_sale), f"{compare_start:%d-%b-%Y} to {compare_end:%d-%b-%Y}", ORANGE)
    with k7: _kpi("Growth", f"{growth:+.1f}%", _money(change), GREEN if growth >= 0 else RED)

    status_options = ["NEW", "REGULAR", "LOST"]
    table_head_left, table_head_mid, table_head_right = st.columns([4.5, 1.3, 1.4], vertical_alignment="center")
    with table_head_left:
        st.markdown("<div class='nbd-section-title'>NBD Customer MIS</div>", unsafe_allow_html=True)
        st.caption(
            f"Current: {current_start:%d-%b-%Y} to {current_end:%d-%b-%Y}  |  "
            f"Comparison: {compare_start:%d-%b-%Y} to {compare_end:%d-%b-%Y}  |  "
            f"Layout: {report_layout}"
        )

    # Compact Customer Type filter. A normal multiselect renders one chip per
    # selected value and becomes two rows when NEW + REGULAR + LOST are all
    # selected. Keep the header row fixed-height by showing a single popover
    # summary instead; the user can still select any combination inside it.
    for _status in status_options:
        _key = f"nbd_status_{_status.lower()}"
        if _key not in st.session_state:
            st.session_state[_key] = True

    selected_status = [
        _status for _status in status_options
        if st.session_state.get(f"nbd_status_{_status.lower()}", False)
    ]

    if len(selected_status) == len(status_options):
        status_summary = "All Customer Types"
    elif not selected_status:
        status_summary = "No Customer Type"
    elif len(selected_status) == 1:
        status_summary = selected_status[0]
    else:
        status_summary = f"{len(selected_status)} types selected"

    with table_head_mid:
        with st.popover(status_summary, use_container_width=True):
            action_left, action_right = st.columns(2, gap="small")
            with action_left:
                if st.button("Select All", key="nbd_status_select_all", use_container_width=True):
                    for _status in status_options:
                        st.session_state[f"nbd_status_{_status.lower()}"] = True
                    st.rerun()
            with action_right:
                if st.button("Clear", key="nbd_status_clear", use_container_width=True):
                    for _status in status_options:
                        st.session_state[f"nbd_status_{_status.lower()}"] = False
                    st.rerun()

            for _status in status_options:
                st.checkbox(
                    _status,
                    key=f"nbd_status_{_status.lower()}",
                )

    # Re-read checkbox state after rendering so the report responds immediately
    # to individual checkbox changes on the same Streamlit rerun.
    selected_status = [
        _status for _status in status_options
        if st.session_state.get(f"nbd_status_{_status.lower()}", False)
    ]

    display_report = report[report["Customer Type"].isin(selected_status)].copy() if selected_status else report.iloc[0:0].copy()

    with table_head_right:
        export_bytes = export_nbd_excel(
            display_report,
            current_start, current_end, compare_start, compare_end,
        )
        st.download_button(
            "Download NBD Excel",
            data=export_bytes,
            file_name=f"NBD_MIS_{current_start:%Y%m%d}_{current_end:%Y%m%d}_vs_{compare_start:%Y%m%d}_{compare_end:%Y%m%d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    if display_report.empty:
        st.info("No NBD customer data found for the selected periods and filters.")
        return

    # IMPORTANT: Do not pass a Pandas Styler to st.dataframe here.
    # Large NBD reports can easily exceed Pandas Styler's default 262,144-cell
    # render limit. Streamlit's native Arrow-backed dataframe renderer is
    # virtualized and handles large reports without materializing CSS for every
    # cell. NumberColumn keeps the values numeric while formatting them in the UI.
    currency_columns = [
        "Compare Sale", "Compare LTL", "Compare FTL",
        "Current Sale", "Current LTL", "Current FTL", "Change",
    ]
    column_config = {
        col: st.column_config.NumberColumn(col, format="₹%.0f")
        for col in currency_columns
        if col in display_report.columns
    }
    if "Growth %" in display_report.columns:
        column_config["Growth %"] = st.column_config.NumberColumn(
            "Growth %", format="%.1f%%"
        )

    st.dataframe(
        display_report,
        use_container_width=True,
        hide_index=True,
        height=580,
        column_config=column_config,
    )

    # Explain any source limitations instead of fabricating fields.
    missing_optional = []
    if "Mobile" not in current_df.columns and "Mobile" not in compare_df.columns:
        missing_optional.append("Mobile")
    if "GSTIN" not in current_df.columns and "GSTIN" not in compare_df.columns:
        missing_optional.append("GSTIN")
    if missing_optional:
        st.caption(
            "Source note: " + ", ".join(missing_optional) +
            " is not present in the stored-procedure output, so that column remains blank."
        )


# Friendly aliases in case app.py uses a shorter function name.
def show_NBD() -> None:
    show_NBDAnalysis()


def show_NBDCustomerAnalysis() -> None:
    show_NBDAnalysis()
