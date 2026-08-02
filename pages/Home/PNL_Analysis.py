import io
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.pnl_data_loader import load_pnl_data_pair
from services.data_loader import get_date_range

SPACER_HEIGHT = 4
REVENUE_CHART_HEIGHT = 310
ALIGNED_CHART_HEIGHT = 310
TOP_N_OPTIONS = [10, 20, 30, 40]
MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
MONTH_MAP = {1:"Apr",2:"May",3:"Jun",4:"Jul",5:"Aug",6:"Sep",7:"Oct",8:"Nov",9:"Dec",10:"Jan",11:"Feb",12:"Mar"}
QUARTER_ORDER = ["Q1", "Q2", "Q3", "Q4"]
QUARTER_MAP = {1:"Q1",2:"Q1",3:"Q1",4:"Q2",5:"Q2",6:"Q2",7:"Q3",8:"Q3",9:"Q3",10:"Q4",11:"Q4",12:"Q4"}
FY_OPTIONS = ["Select FY", "2026-2027", "2025-2026", "2024-2025", "2023-2024", "2022-2023", "2021-2022", "2020-2021"]


def compact_spacer(height=SPACER_HEIGHT):
    st.markdown(f"<div aria-hidden='true' style='height:{height}px'></div>", unsafe_allow_html=True)


def _inject_pnl_css():
    st.markdown("""
    <style>
    .block-container{max-width:100%;padding:.35rem .75rem .75rem!important}
    div[data-testid="stVerticalBlock"]{gap:.35rem!important}
    div[data-testid="stHorizontalBlock"]{gap:.5rem!important;align-items:flex-start!important}
    div[data-testid="stHorizontalBlock"]>div[data-testid="stColumn"]{min-width:0!important}
    div[data-testid="stVerticalBlockBorderWrapper"]{border:1px solid #dce5ef!important;border-radius:14px!important;background:linear-gradient(180deg,#fff 0%,#fbfdff 100%)!important;box-shadow:0 7px 18px rgba(15,42,67,.075),inset 0 1px 0 #fff!important}
    div[data-testid="stVerticalBlockBorderWrapper"]>div{padding:.55rem .65rem!important}
    .executive-title{color:#102a43;font-size:19px;font-weight:850;letter-spacing:-.3px;margin:0}
    .executive-subtitle{color:#64748b;font-size:11px;margin-top:2px}
    .filter-summary{display:flex;flex-wrap:wrap;align-items:center;min-height:32px;gap:7px;margin:0}
    .filter-chip{display:inline-flex;align-items:center;min-height:28px;padding:6px 13px;border:1px solid #b8d1f2;border-radius:999px;background:#f5f9ff;color:#31557d;font-size:11px;font-weight:500;white-space:nowrap}
    div[data-testid="stSelectbox"]{display:flex!important;flex-direction:column!important;gap:7px!important;margin:0 0 2px!important}
    div[data-testid="stSelectbox"]>label,div[data-testid="stSelectbox"] [data-testid="stWidgetLabel"]{min-height:22px!important;line-height:22px!important;margin:0 0 2px 2px!important;font-size:10px!important;color:#243b53!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important}
    div[data-testid="stSelectbox"] div[data-baseweb="select"]>div{min-height:40px!important;height:40px!important;padding:0 8px!important;border:1px solid #cbd9ea!important;border-radius:10px!important;background:linear-gradient(180deg,#fff,#f5f8fc)!important}
    div[data-testid="stSegmentedControl"]{display:flex!important;justify-content:flex-end!important;width:100%!important}
    div[data-testid="stSegmentedControl"]>div,div[data-testid="stSegmentedControl"] [role="radiogroup"]{display:grid!important;grid-auto-flow:column!important;gap:6px!important;width:auto!important;background:#edf2f7!important;border:1px solid #c9d5e3!important;border-radius:8px!important;padding:3px!important}
    div[data-testid="stSegmentedControl"] label,div[data-testid="stSegmentedControl"] button{min-height:28px!important;height:28px!important;padding:3px 9px!important;border:1px solid #cbd5e1!important;border-radius:6px!important;background:linear-gradient(180deg,#fff,#e9eef5)!important;box-shadow:0 2px 0 #aebac8,inset 0 1px 0 #fff!important;font-size:10px!important;font-weight:700!important}
    div[data-testid="stSegmentedControl"] label:has(input:checked),div[data-testid="stSegmentedControl"] button[aria-pressed="true"]{color:#fff!important;background:#123f73!important;border-color:#123f73!important;box-shadow:inset 0 1px 2px rgba(0,0,0,.18)!important}
    .kpi-3d-card{position:relative;overflow:hidden;min-height:70px;padding:8px 9px;border:1px solid #cbd5e1;border-radius:14px;background:linear-gradient(145deg,#fff 0%,#f8fafc 45%,#e7edf5 100%);box-shadow:0 3px 8px rgba(15,23,42,.10)}
    .kpi-3d-head{display:grid;grid-template-columns:minmax(0,1fr) 27px;align-items:center;gap:6px}.kpi-3d-title{color:var(--kpi-accent);font-size:11px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.kpi-3d-icon{width:27px;height:27px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;background:linear-gradient(145deg,#fff,#dfe7f1);border:1px solid #cbd5e1}.kpi-3d-value{margin-top:2px;color:#102a43;font-size:16px;font-weight:900}.kpi-3d-footer{margin-top:4px;display:flex;justify-content:space-between;gap:6px}.kpi-3d-ly{color:#64748b;font-size:9px;font-weight:600}.kpi-3d-growth{padding:2px 7px;border:1px solid;border-radius:999px;font-size:9px;font-weight:600}
    [data-testid="stDataFrame"]{border:1px solid #e2eaf3;border-radius:10px;overflow:hidden}[data-testid="stDataFrame"] table{font-size:11px}
    </style>""", unsafe_allow_html=True)


def _normal(value):
    return str(value).strip().replace("_", "").replace(" ", "").casefold()


def _find_column(df, candidates):
    if df is None:
        return None
    mapping = {_normal(c): c for c in df.columns}
    for candidate in candidates:
        if _normal(candidate) in mapping:
            return mapping[_normal(candidate)]
    return None


def normalize_pnl_columns(df):
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    aliases = {
        "COMPNAME":["COMPNAME","compname","company","companyname"],"zone":["zone","zonename"],"circle":["circle","circlename","hubname"],"branch":["branch","branchname"],
        "grno":["grno","gr_no","grnumber"],"grdt":["grdt","grdate","bookingdate"],"GRTYPE":["GRTYPE","grtype"],"LOADTYPE":["LOADTYPE","loadtype","load_type"],
        "FIN_MONTH":["FIN_MONTH","fin_month","financialmonth"],"REVENUE":["REVENUE","revenue","business"],"EXPENSE":["EXPENSE","expense","expenses","cost"],"PNL":["PNL","pnl","profitloss","profit_loss","profitandloss"],
        "Consignor":["Consignor","consignor","consignorname","customer","customername"],"Consignee":["Consignee","consignee","consigneename"],"Route":["Route","route","routename"],"COUNTRY":["COUNTRY","country","countryname"]
    }
    rename = {}
    for target, candidates in aliases.items():
        source = _find_column(out, candidates)
        if source is not None and source != target:
            rename[source] = target
    out = out.rename(columns=rename)
    for col in ["REVENUE","EXPENSE","PNL","FIN_MONTH"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    if "grdt" in out.columns:
        out["grdt"] = pd.to_datetime(out["grdt"], errors="coerce")
    for col in ["COMPNAME","zone","circle","branch","GRTYPE","LOADTYPE","Consignor","Consignee","Route","COUNTRY"]:
        if col in out.columns:
            out[col] = out[col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    if "FIN_MONTH" in out.columns:
        out["FIN_MONTH"] = out["FIN_MONTH"].astype(int)
        out["Month"] = out["FIN_MONTH"].map(MONTH_MAP)
        out["Quarter"] = out["FIN_MONTH"].map(QUARTER_MAP)
    return out


def get_previous_fy(fy):
    start, end = map(int, fy.split("-")); return f"{start-1}-{end-1}"


def get_conversion(kind):
    return (100000, "Lac") if kind == "Lac" else (10000000, "Cr")


def pct_growth(current, previous):
    if previous in (0, None) or pd.isna(previous): return 0.0
    return ((current - previous) / abs(previous)) * 100


def growth_label(value):
    return f"{'▲' if value >= 0 else '▼'} {abs(value):.1f}%"


def create_card(title, value, color, icon, growth_value=0.0, previous_value=None):
    positive = growth_value >= 0
    html = (f'<div class="kpi-3d-card" style="--kpi-accent:{color};"><div class="kpi-3d-head"><div class="kpi-3d-title">{escape(title)}</div><div class="kpi-3d-icon">{icon}</div></div>'
            f'<div class="kpi-3d-value">{escape(value)}</div><div class="kpi-3d-footer"><span class="kpi-3d-ly">LY: {escape(previous_value or "N/A")}</span>'
            f'<span class="kpi-3d-growth" style="background:#fff;border-color:{"#86efac" if positive else "#fda4af"};color:{"#15803d" if positive else "#dc2626"};">{growth_label(growth_value)}</span></div></div>')
    st.html(html) if hasattr(st, "html") else st.markdown(html, unsafe_allow_html=True)


def build_yoy_pnl_trend(current_df, previous_df, trend_type, fy_start, prev_fy_start):
    cur = current_df[["grdt","PNL","FIN_MONTH"]].copy()
    prev = previous_df[["grdt","PNL","FIN_MONTH"]].copy() if previous_df is not None and not previous_df.empty else pd.DataFrame()
    cur["grdt"] = pd.to_datetime(cur["grdt"], errors="coerce")
    if not prev.empty: prev["grdt"] = pd.to_datetime(prev["grdt"], errors="coerce")
    fy_start_ts, prev_start_ts = pd.to_datetime(fy_start), pd.to_datetime(prev_fy_start)
    if trend_type == "Daily":
        t = cur.groupby(cur["grdt"].dt.date)["PNL"].sum().reset_index(); t.columns=["Period","PNL"]; t["Key"]=(pd.to_datetime(t["Period"])-fy_start_ts).dt.days
        p = prev.groupby(prev["grdt"].dt.date)["PNL"].sum().reset_index() if not prev.empty else pd.DataFrame()
        if not p.empty: p.columns=["Period","PREV_PNL"]; p["Key"]=(pd.to_datetime(p["Period"])-prev_start_ts).dt.days
    elif trend_type == "Weekly":
        t = cur.groupby(cur["grdt"].dt.to_period("W"))["PNL"].sum().reset_index(); t["Period"]=t["grdt"].astype(str); t["Key"]=(t["grdt"].dt.start_time-fy_start_ts).dt.days//7; t=t.drop(columns=["grdt"])
        p = prev.groupby(prev["grdt"].dt.to_period("W"))["PNL"].sum().reset_index() if not prev.empty else pd.DataFrame()
        if not p.empty: p["Key"]=(p["grdt"].dt.start_time-prev_start_ts).dt.days//7; p=p.rename(columns={"PNL":"PREV_PNL"}).drop(columns=["grdt"])
    elif trend_type == "Quarterly":
        cur["Quarter"]=cur["FIN_MONTH"].map(QUARTER_MAP); t=cur.groupby("Quarter")["PNL"].sum().reset_index(); t["Quarter"]=pd.Categorical(t["Quarter"],QUARTER_ORDER,ordered=True); t=t.sort_values("Quarter"); t.columns=["Period","PNL"]; t["Key"]=t["Period"]
        if not prev.empty: prev["Quarter"]=prev["FIN_MONTH"].map(QUARTER_MAP); p=prev.groupby("Quarter")["PNL"].sum().reset_index(); p.columns=["Key","PREV_PNL"]
        else: p=pd.DataFrame()
    else:
        cur["Month"]=cur["FIN_MONTH"].map(MONTH_MAP); t=cur.groupby("Month")["PNL"].sum().reset_index(); t["Month"]=pd.Categorical(t["Month"],MONTH_ORDER,ordered=True); t=t.sort_values("Month"); t.columns=["Period","PNL"]; t["Key"]=t["Period"]
        if not prev.empty: prev["Month"]=prev["FIN_MONTH"].map(MONTH_MAP); p=prev.groupby("Month")["PNL"].sum().reset_index(); p.columns=["Key","PREV_PNL"]
        else: p=pd.DataFrame()
    if p is None or p.empty: t["PREV_PNL"]=0.0
    else: t=t.merge(p[["Key","PREV_PNL"]],on="Key",how="left"); t["PREV_PNL"]=t["PREV_PNL"].fillna(0)
    return t


def _apply(df, col, value):
    return df if value == "All" or col not in df.columns else df[df[col] == value]


def _options(df, col):
    return sorted(df[col].dropna().astype(str).str.strip().replace("", pd.NA).dropna().unique().tolist(), key=str.casefold) if col in df.columns else []


def _rank_table(data, name_col, value_col, title, unit, top_n, key_prefix):
    with st.container(border=True):
        h1, h2 = st.columns([3,1])
        with h1: st.markdown(f"<div style='font-size:15px;font-weight:500;color:#0f2744;'>{title}</div>", unsafe_allow_html=True)
        with h2: selected = st.selectbox("Top N", TOP_N_OPTIONS, index=0, key=f"{key_prefix}_topn", label_visibility="collapsed")
        ranked = data.groupby(name_col, dropna=False)[value_col].sum().reset_index().sort_values(value_col, ascending=False).head(selected)
        total = float(data[value_col].sum())
        ranked["Display"] = ranked[value_col] / get_conversion(unit)[0]
        ranked["Share %"] = ranked[value_col].apply(lambda v: v / total * 100 if total else 0)
        ranked.insert(0, "#", range(1, len(ranked)+1))
        st.dataframe(ranked[["#",name_col,"Display","Share %"]], hide_index=True, width="stretch", height=min(410, 70+len(ranked)*31), column_config={name_col:st.column_config.TextColumn(name_col),"Display":st.column_config.NumberColumn(f"P&L ({get_conversion(unit)[1]})",format="%.2f"),"Share %":st.column_config.NumberColumn("% Share",format="%.2f%%")})


def show_pnl_dashboard():
    _inject_pnl_css()
    with st.container(border=True):
        left, right = st.columns([7,1], gap="small", vertical_alignment="center")
        with left:
            st.markdown('<div style="padding:2px 0 3px 4px;"><div class="executive-title">P&amp;L Overview</div><div class="executive-subtitle">Executive view of profitability, load mix, geography, customers, routes and branch performance</div></div>', unsafe_allow_html=True)
        with right: export_placeholder = st.empty()
    compact_spacer(4)
    filter_cols = st.columns(10, gap="small")
    with filter_cols[0]: view_type = st.selectbox("⇄ View Type", ["Origin","Destination"], key="pnl_view_type")
    with filter_cols[1]: fy = st.selectbox("◷ Financial Year", FY_OPTIONS, key="pnl_fy")
    if fy == "Select FY": st.info("Please select financial year"); return
    start_date, end_date = get_date_range(fy); prev_fy=get_previous_fy(fy); prev_start, prev_end=get_date_range(prev_fy)
    with st.spinner("Loading current and previous-year P&L data..."):
        raw, raw_prev = load_pnl_data_pair(start_date,end_date,prev_start,prev_end,view_type.lower())
    df, prev_df = normalize_pnl_columns(raw), normalize_pnl_columns(raw_prev)
    if df.empty: st.warning("No P&L data found"); return
    required=["COMPNAME","zone","circle","branch","grno","grdt","LOADTYPE","FIN_MONTH","REVENUE","EXPENSE","PNL"]
    missing=[c for c in required if c not in df.columns]
    if missing: st.error(f"Missing columns: {missing}"); st.write(list(df.columns)); return
    scope=st.session_state.get("data_scope",{}) or {}; locked_zone=scope.get("zone"); locked_circle=scope.get("circle"); locked_branch=scope.get("branch")
    with filter_cols[2]: company=st.selectbox("▥ Company",["All"]+_options(df,"COMPNAME"),key="pnl_company")
    df=_apply(df,"COMPNAME",company)
    with filter_cols[3]: zone=locked_zone or st.selectbox("◉ Zone",["All"]+_options(df,"zone"),key="pnl_zone")
    if locked_zone: st.session_state.setdefault("pnl_zone_locked",locked_zone)
    df=_apply(df,"zone",zone)
    with filter_cols[4]: circle=locked_circle or st.selectbox("◎ Circle",["All"]+_options(df,"circle"),key="pnl_circle")
    df=_apply(df,"circle",circle)
    with filter_cols[5]: branch=locked_branch or st.selectbox("⌂ Branch",["All"]+_options(df,"branch"),key="pnl_branch")
    df=_apply(df,"branch",branch)
    with filter_cols[6]: quarter=st.selectbox("▦ Quarter",["All"]+[q for q in QUARTER_ORDER if q in df["Quarter"].dropna().tolist()],key="pnl_quarter")
    df=_apply(df,"Quarter",quarter)
    with filter_cols[7]: month=st.selectbox("▣ Month",["All"]+[m for m in MONTH_ORDER if m in df["Month"].dropna().tolist()],key="pnl_month")
    df=_apply(df,"Month",month)
    with filter_cols[8]: loadtype=st.selectbox("▤ Load Type",["All"]+_options(df,"LOADTYPE"),key="pnl_loadtype")
    df=_apply(df,"LOADTYPE",loadtype)
    with filter_cols[9]: conversion_type=st.selectbox("₹ Conversion",["Crore","Lac"],key="pnl_conversion_type")
    for col,val in [("COMPNAME",company),("zone",zone),("circle",circle),("branch",branch),("Quarter",quarter),("Month",month),("LOADTYPE",loadtype)]: prev_df=_apply(prev_df,col,val)
    chips=[("FY",fy),("View",view_type),("Company",company),("Zone",zone),("Circle",circle),("Branch",branch),("Quarter",quarter),("Month",month),("Load",loadtype),("Unit",conversion_type)]
    st.markdown('<div class="filter-summary">'+''.join(f'<span class="filter-chip">{escape(k)}: {escape(str(v))}</span>' for k,v in chips if v not in (None,"","All"))+'</div>', unsafe_allow_html=True)
    if df.empty: st.warning("No data found for selected filters"); return
    divisor, unit = get_conversion(conversion_type)
    safe_fy=fy.replace("/","-"); export_key=f"pnl_export_{view_type}_{safe_fy}"
    with export_placeholder:
        st.download_button("⬇ Download CSV",df.to_csv(index=False).encode("utf-8-sig"),f"pnl_overview_{view_type.lower()}_{safe_fy}.csv","text/csv",key=export_key,width="content")
    cur_total=float(df["PNL"].sum()); py_total=float(prev_df["PNL"].sum()) if not prev_df.empty else 0
    cur_exp=float(df["EXPENSE"].sum()); py_exp=float(prev_df["EXPENSE"].sum()) if not prev_df.empty else 0
    cur_rev=float(df["REVENUE"].sum()); py_rev=float(prev_df["REVENUE"].sum()) if not prev_df.empty else 0
    ftl=float(df.loc[df["LOADTYPE"].eq("FTL"),"PNL"].sum()); py_ftl=float(prev_df.loc[prev_df["LOADTYPE"].eq("FTL"),"PNL"].sum()) if not prev_df.empty else 0
    ltl=float(df.loc[df["LOADTYPE"].eq("LTL"),"PNL"].sum()); py_ltl=float(prev_df.loc[prev_df["LOADTYPE"].eq("LTL"),"PNL"].sum()) if not prev_df.empty else 0
    cards=[("Revenue",cur_rev,py_rev,"💰","#2563eb"),("Expense",cur_exp,py_exp,"🧾","#dc2626"),("P&L",cur_total,py_total,"📈","#16a34a" if cur_total>=0 else "#dc2626"),("P&L Margin",cur_total/cur_rev*100 if cur_rev else 0,py_total/py_rev*100 if py_rev else 0,"🎯","#7c3aed"),("FTL P&L",ftl,py_ftl,"🚛","#2563eb"),("LTL P&L",ltl,py_ltl,"🚚","#0f766e")]
    cols=st.columns(6,gap="small")
    for c,(title,cur,py,icon,color) in zip(cols,cards):
        with c:
            if "Margin" in title: create_card(title,f"{cur:.2f}%",color,icon,cur-py,f"{py:.2f}%")
            else: create_card(title,f"₹{cur/divisor:.2f} {unit}",color,icon,pct_growth(cur,py),f"₹{py/divisor:.2f} {unit}")
    compact_spacer()
    row1,row2=st.columns([1.20,.80])
    with row1:
        with st.container(border=True):
            t1,t2=st.columns([2,2])
            with t1:
                g=pct_growth(cur_total,py_total); st.markdown(f"<div style='font-size:14px;font-weight:400;color:#0f172a;'>P&L Trend <span style='font-size:11px;font-weight:700;color:{'#166534' if g>=0 else '#dc2626'};'>({growth_label(g)} vs LY)</span></div>",unsafe_allow_html=True)
            with t2: trend_type=st.segmented_control("P&L trend period",["Daily","Weekly","Monthly","Quarterly"],default="Monthly",label_visibility="collapsed",key="pnl_trend_type") or "Monthly"
            trend=build_yoy_pnl_trend(df,prev_df,trend_type,start_date,prev_start); trend["Current"]=trend["PNL"]/divisor; trend["Previous"]=trend["PREV_PNL"]/divisor
            fig=go.Figure(); fig.add_bar(x=trend["Period"],y=trend["Previous"],name=f"LY ({prev_fy})",marker=dict(color="#cbd5e1",line=dict(color="#94a3b8",width=1.3)),text=trend["Previous"],texttemplate="%{text:.2f}",textposition="outside")
            fig.add_bar(x=trend["Period"],y=trend["Current"],name=f"Current ({fy})",marker=dict(color="#2563eb",line=dict(color="#1e3a8a",width=1.3)),text=trend["Current"],texttemplate="%{text:.2f}",textposition="outside")
            fig.add_hline(y=0,line_color="#64748b",line_width=1); fig.update_layout(barmode="group",height=REVENUE_CHART_HEIGHT,margin=dict(l=8,r=8,t=24,b=8),plot_bgcolor="#f8fafc",paper_bgcolor="rgba(0,0,0,0)",legend=dict(orientation="h",y=1.05,x=0),yaxis_title=f"P&L ({unit})")
            st.plotly_chart(fig,width="stretch",config={"displayModeBar":False,"responsive":True})
    with row2:
        with st.container(border=True):
            st.markdown('<div style="font-size:16px;font-weight:600;color:#0f172a;margin:0 0 5px;">P&L by Load Type (CY)</div>',unsafe_allow_html=True)
            vals=[ftl,ltl]; total=sum(vals); fig=go.Figure(go.Pie(labels=["FTL","LTL"],values=vals,hole=.66,marker=dict(colors=["#2563eb","#0f766e"],line=dict(color="#fff",width=2)),textinfo="none",hovertemplate=f"<b>%{{label}}</b><br>P&L: ₹%{{value:.2f}}<extra></extra>"))
            fig.add_annotation(text=f"<b>₹{total/divisor:.2f}</b><br><span style='font-size:10px'>{unit}</span>",x=.5,y=.5,showarrow=False); fig.update_layout(height=REVENUE_CHART_HEIGHT,margin=dict(l=5,r=5,t=10,b=5),showlegend=True,legend=dict(orientation="h",y=-.05,x=.5,xanchor="center"),paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
    compact_spacer()
    zone_left,zone_right=st.columns([1.55,1],gap="small")
    with zone_left:
        if view_type=="Origin" and "COUNTRY" in df.columns:
            with st.container(border=True):
                st.markdown("<div style='font-size:15px;font-weight:500;color:#0f2744;margin-bottom:8px;'>Zone-wise Country P&L</div>",unsafe_allow_html=True)
                matrix=df.pivot_table(index="zone",columns="COUNTRY",values="PNL",aggfunc="sum",fill_value=0)/divisor; matrix["Total"]=matrix.sum(axis=1); matrix=matrix.sort_values("Total",ascending=False)
                st.dataframe(matrix.style.format("{:.2f}").background_gradient(cmap="RdYlGn",axis=None),width="stretch",height=ALIGNED_CHART_HEIGHT)
        else:
            with st.container(border=True): st.info("Zone-wise Country P&L is available for Origin view when COUNTRY is present.")
    with zone_right:
        with st.container(border=True):
            st.markdown("###### P&L by Zone")
            z=df.groupby("zone")["PNL"].sum().reset_index().sort_values("PNL",ascending=False); total=float(z["PNL"].sum()); colors=["#1565C0","#009688","#FB8C00","#7E57C2","#EC407A","#EF5350"]
            fig=go.Figure(go.Pie(labels=z["zone"],values=z["PNL"].abs(),hole=.62,marker=dict(colors=colors[:len(z)],line=dict(color="#fff",width=2)),customdata=z["PNL"],textinfo="none",hovertemplate=f"<b>%{{label}}</b><br>P&L: ₹%{{customdata:.2f}}<extra></extra>")); fig.add_annotation(text=f"<b>₹{total/divisor:.2f} {unit}</b><br><span style='font-size:10px'>Net P&L</span>",x=.5,y=.5,showarrow=False); fig.update_layout(height=ALIGNED_CHART_HEIGHT,margin=dict(l=0,r=0,t=4,b=0),showlegend=True,legend=dict(orientation="h",y=-.08),paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})
    compact_spacer()
    c1,c2=st.columns(2,gap="small")
    with c1:
        if "Consignor" in df.columns: _rank_table(df,"Consignor","PNL","Top N Customers by P&L",conversion_type,10,"pnl_customer")
        else: st.info("Customer column not found.")
    with c2:
        if "Route" in df.columns: _rank_table(df,"Route","PNL","Top N Routes by P&L",conversion_type,10,"pnl_route")
        else: st.info("Route column not found.")
    compact_spacer()
    with st.container(border=True):
        st.markdown("<div style='font-size:16px;font-weight:400;color:#0f2744;margin:1px 0 7px 2px;'>Branches by P&L</div>",unsafe_allow_html=True)
        options=["All","Loss","₹0–5 Lac","₹5–10 Lac","₹10–25 Lac","₹25–50 Lac","₹50 Lac & Above"]
        slab=st.segmented_control("Branch P&L slab",options,default="All",key="pnl_branch_slab",label_visibility="collapsed",width="stretch") or "All"
        b=df.groupby("branch")["PNL"].sum().reset_index(); ranges={"₹0–5 Lac":(0,500000),"₹5–10 Lac":(500000,1000000),"₹10–25 Lac":(1000000,2500000),"₹25–50 Lac":(2500000,5000000),"₹50 Lac & Above":(5000000,None)}
        if slab=="Loss": b=b[b["PNL"]<0].sort_values("PNL")
        elif slab in ranges:
            lo,hi=ranges[slab]; b=b[b["PNL"]>=lo]; b=b if hi is None else b[b["PNL"]<hi]; b=b.sort_values("PNL",ascending=False)
        else: b=b.sort_values("PNL",ascending=False)
        b["P&L Display"]=b["PNL"]/divisor
        if b.empty: st.info(f"No branch falls in {slab}.")
        else:
            fig=go.Figure(go.Bar(x=b["P&L Display"],y=b["branch"],orientation="h",marker_color=["#16a34a" if v>=0 else "#dc2626" for v in b["PNL"]],text=b["P&L Display"],texttemplate="%{text:.2f}",textposition="outside")); fig.add_vline(x=0,line_color="#64748b",line_width=1); fig.update_layout(height=max(360,min(900,80+len(b)*28)),margin=dict(l=5,r=30,t=8,b=5),xaxis_title=f"P&L ({unit})",yaxis_title="",plot_bgcolor="#f8fafc",paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig,width="stretch",config={"displayModeBar":False})


def show_pnl():
    show_pnl_dashboard()
