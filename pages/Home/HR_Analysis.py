"""HR & Salary Analytics | SQL Server + Streamlit.
Run: streamlit run app.py
Salary figures are indicative until payroll-head mapping and effective-date rules are approved.
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
import calendar
from html import escape

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


EMPLOYEE_SQL = """
SELECT
    E.EMPLOYEEID, E.EMPCODE, ZONE.ZONENAME AS ZONE,
    BR.STNNAME AS BRANCH, E.EMPNAME, E.GENDER,
    DEPT.DEPTNAME AS DEPARTMENT, E.DOB, E.DOJ,
    E.RESIGNDT, E.DATEOFLEAVING, E.EMAILID,
    E.RETIREMENTDT, E.AADHARNO, E.PAN
FROM EMPLOYEEMAST E
INNER JOIN STATIONMAST BR ON BR.STNCODE = E.BRANCHCODE
LEFT JOIN ZONEMAST ZONE ON ZONE.ZONECODE = BR.ZONECODE
LEFT JOIN DEPARTMENTMAST DEPT ON DEPT.DEPTID = E.DEPTID
"""

SALARY_SQL = """
SELECT
    S.EMPLOYEEID, S.EMPCODE, S.EMPNAME,
    S.BRANCHCODE, S.DEPARTMENTID, DEP.DEPTNAME AS SALARY_DEPARTMENT,
    S.DESIGNATIONID, DESG.DESIGNATION,
    S.SALARYHEAD, S.AMOUNT, S.PCTG, S.FROMDT, S.TODT
FROM VIEWEMPLOYEESALARYDETAIL S
LEFT JOIN DEPARTMENTMAST DEP ON DEP.DEPTID = S.DEPARTMENTID
LEFT JOIN DESIGNATIONMAST DESG ON DESG.DESIGNATIONID = S.DESIGNATIONID
"""

EARNING_HEADS = {"BASIC SALARY", "HRA", "MED. ALLW.", "TRPT. ALLW.", "SPECIAL ALLOWNCES"}
DEDUCTION_HEADS = {"EMPLOYEE PF"}
EMPLOYER_HEADS = {"EMPLOYER PF", "GRATUITY", "ADMIN CHARGES FOR PF. ACCT 2"}


@st.cache_resource(show_spinner=False)
def get_bidding_engine():
    """The exact secrets-backed SQLAlchemy + pymssql engine pattern supplied."""
    connection_url = URL.create(
        "mssql+pymssql",
        username=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_SERVER"],
        port=int(st.secrets["DB_PORT"]),
        database=st.secrets["DB_NAME"],
    )
    return create_engine(connection_url, pool_pre_ping=True, pool_recycle=1800,
                         pool_size=2, max_overflow=1)


@st.cache_data(ttl=900, show_spinner="Loading HR records...")
def load_data():
    engine = get_bidding_engine()
    with engine.connect() as con:
        emps = pd.read_sql_query(text(EMPLOYEE_SQL), con)
        salary = pd.read_sql_query(text(SALARY_SQL), con)
    return emps, salary


def dt(series):
    return pd.to_datetime(series, errors="coerce")


def prepare_employees(df, asof):
    x = df.copy()
    for col in ["DOB", "DOJ", "RESIGNDT", "DATEOFLEAVING", "RETIREMENTDT"]:
        x[col] = dt(x[col]).dt.normalize()
    ref = pd.Timestamp(asof)
    joined = x.DOJ.notna() & (x.DOJ <= ref)
    left = x.DATEOFLEAVING.notna() & (x.DATEOFLEAVING < ref)
    resigned = x.RESIGNDT.notna() & (x.RESIGNDT <= ref)
    active = joined & ~left
    # A future LWD without a resignation is reported separately, not inferred as resignation.
    x["STATUS"] = np.select(
        [~joined, left, resigned & x.DATEOFLEAVING.isna(),
         resigned & active, active & x.DATEOFLEAVING.notna()],
        ["NOT YET JOINED / DOJ MISSING", "LEFT", "RESIGNED - LWD PENDING",
         "SERVING NOTICE PERIOD", "LWD SCHEDULED (NO RESIGN DATE)"],
        default="ACTIVE",
    )
    x["ACTIVE_HEADCOUNT"] = active.astype(int)
    x["RESIGNED_NOT_LEFT"] = (resigned & active).astype(int)
    x["NOTICE_DAYS_REMAINING"] = np.where(
        resigned & active & x.DATEOFLEAVING.notna(),
        (x.DATEOFLEAVING - ref).dt.days, np.nan)
    x["NOTICE_PERIOD_DAYS"] = np.where(
        x.RESIGNDT.notna() & x.DATEOFLEAVING.notna(),
        (x.DATEOFLEAVING - x.RESIGNDT).dt.days, np.nan)
    x["AGE"] = ((ref.year - x.DOB.dt.year) -
                ((ref.month < x.DOB.dt.month) |
                 ((ref.month == x.DOB.dt.month) & (ref.day < x.DOB.dt.day))).fillna(False).astype(int))
    x.loc[x.DOB.isna() | (x.DOB > ref), "AGE"] = np.nan
    service_end = x.DATEOFLEAVING.where(left, ref)
    x["SERVICE_MONTHS"] = ((service_end.dt.year - x.DOJ.dt.year) * 12 +
                           (service_end.dt.month - x.DOJ.dt.month) -
                           (service_end.dt.day < x.DOJ.dt.day).astype(int))
    x.loc[x.DOJ.isna() | (x.DOJ > ref) | (service_end < x.DOJ), "SERVICE_MONTHS"] = np.nan
    x["SERVICE_YEARS"] = (x.SERVICE_MONTHS / 12).round(2)
    x["AGE_GROUP"] = pd.cut(x.AGE, bins=[-1,24,30,40,50,np.inf],
                            labels=["<25", "25-30", "31-40", "41-50", "51+"]).astype("object").fillna("UNKNOWN")
    x["SERVICE_GROUP"] = pd.cut(x.SERVICE_MONTHS,
                                bins=[-1,11,35,59,119,np.inf],
                                labels=["0-1 Year", "1-3 Years", "3-5 Years", "5-10 Years", "10+ Years"]).astype("object").fillna("UNKNOWN")
    x["JOINING_YEAR"] = x.DOJ.dt.year
    x["RESIGNATION_YEAR"] = x.RESIGNDT.dt.year
    x["LEAVING_YEAR"] = x.DATEOFLEAVING.dt.year
    return x



def prepare_rejoining(employees):
    """Find sequential employment spells linked by valid Aadhaar or PAN."""
    x = employees.copy()
    aadhaar = x["AADHARNO"].fillna("").astype(str).str.replace(r"\D", "", regex=True)
    pan = x["PAN"].fillna("").astype(str).str.upper().str.replace(r"\s+", "", regex=True)
    x["_aadhaar"] = aadhaar.where(aadhaar.str.fullmatch(r"[2-9][0-9]{11}").fillna(False))
    x["_pan"] = pan.where(pan.str.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]").fillna(False))
    x = x[x.DOJ.notna() & x.EMPLOYEEID.notna()].copy()
    x = x.sort_values("DOJ").drop_duplicates("EMPLOYEEID", keep="last")
    # Build every qualifying pair, then deduplicate pairs matching via both identifiers.
    pairs = {}
    for identifier in ("_aadhaar", "_pan"):
        valid = x[x[identifier].notna()]
        for _, group in valid.groupby(identifier, sort=False):
            ordered = group.sort_values(["DOJ", "EMPLOYEEID"])
            rows = list(ordered.iterrows())
            for j in range(1, len(rows)):
                current_idx, current = rows[j]
                earlier = [(idx, prior) for idx, prior in rows[:j]
                           if str(prior.EMPLOYEEID) != str(current.EMPLOYEEID)]
                if not earlier:
                    continue
                # Most recent earlier employment for each matched current ID.
                prev_idx, previous = earlier[-1]
                key = (str(previous.EMPLOYEEID), str(current.EMPLOYEEID))
                pairs[key] = (prev_idx, current_idx)
    output_columns = ["EMPCODE", "EMPNAME", "ZONE", "BRANCH", "DEPARTMENT", "DOJ", "STATUS", "PREVIOUS_EMPCODE", "PREVIOUS_DOJ", "PREVIOUS_LWD", "DAYS_BETWEEN", "REJOINING_STATUS", "MATCH_METHOD", "AADHAAR_MASKED", "PAN_MASKED", "EMPLOYEEID"]
    output = []
    for prev_idx, current_idx in pairs.values():
        previous, current = x.loc[prev_idx], x.loc[current_idx]
        aadhaar_match = (pd.notna(previous["_aadhaar"]) and previous["_aadhaar"] == current["_aadhaar"])
        pan_match = (pd.notna(previous["_pan"]) and previous["_pan"] == current["_pan"])
        if not (aadhaar_match or pan_match):
            continue
        method = "BOTH" if aadhaar_match and pan_match else "AADHAAR" if aadhaar_match else "PAN"
        aadhaar_conflict = (pd.notna(previous["_aadhaar"]) and pd.notna(current["_aadhaar"]) and not aadhaar_match)
        pan_conflict = (pd.notna(previous["_pan"]) and pd.notna(current["_pan"]) and not pan_match)
        if aadhaar_conflict or pan_conflict:
            status = "REVIEW - IDENTITY CONFLICT"
        elif pd.isna(previous.DATEOFLEAVING):
            status = "REVIEW - PRIOR LWD MISSING"
        elif current.DOJ <= previous.DATEOFLEAVING:
            status = "REVIEW - OVERLAPPING EMPLOYMENT"
        else:
            status = "REJOINED - PRIOR EXIT RECORDED"
        rec = {
            "EMPCODE": current.EMPCODE, "EMPNAME": current.EMPNAME,
            "ZONE": current.ZONE, "BRANCH": current.BRANCH,
            "DEPARTMENT": current.DEPARTMENT, "DOJ": current.DOJ,
            "STATUS": current.STATUS, "EMPLOYEEID": current.EMPLOYEEID,
            "PREVIOUS_EMPCODE": previous.EMPCODE,
            "PREVIOUS_DOJ": previous.DOJ,
            "PREVIOUS_LWD": previous.DATEOFLEAVING,
            "DAYS_BETWEEN": (current.DOJ - previous.DATEOFLEAVING).days if pd.notna(previous.DATEOFLEAVING) else np.nan,
            "REJOINING_STATUS": status, "MATCH_METHOD": method,
            "AADHAAR_MASKED": "XXXX-XXXX-" + str(current["_aadhaar"])[-4:] if pd.notna(current["_aadhaar"]) else "-",
            "PAN_MASKED": str(current["_pan"])[:2] + "******" + str(current["_pan"])[-2:] if pd.notna(current["_pan"]) else "-",
        }
        output.append(rec)
    return pd.DataFrame(output, columns=output_columns)


def prepare_salary(df):
    x = df.copy()
    for col in ["FROMDT", "TODT"]:
        x[col] = dt(x[col]).dt.normalize()
    x["SALARY_HEAD_CLEAN"] = x.SALARYHEAD.fillna("").astype(str).str.strip().str.upper()
    x["AMOUNT"] = pd.to_numeric(x.AMOUNT, errors="coerce").fillna(0)
    x["PCTG"] = pd.to_numeric(x.PCTG, errors="coerce").fillna(0)
    x["SALARY_CATEGORY"] = np.select(
        [x.SALARY_HEAD_CLEAN.isin(EARNING_HEADS),
         x.SALARY_HEAD_CLEAN.isin(DEDUCTION_HEADS),
         x.SALARY_HEAD_CLEAN.isin(EMPLOYER_HEADS)],
        ["EARNINGS", "EMPLOYEE DEDUCTION", "EMPLOYER COST"], default="UNCLASSIFIED")
    return x


def salary_snapshot(salary, asof):
    """One tentative effective record per employee+head at report date.

    If a monthly override (newer FROMDT) overlaps an open-ended salary structure,
    use latest FROMDT. Ties are flagged as ambiguous, not silently summed.
    """
    ref = pd.Timestamp(asof)
    x = salary[salary.FROMDT.notna() & (salary.FROMDT <= ref) &
               (salary.TODT.isna() | (salary.TODT >= ref))].copy()
    if x.empty:
        return x.assign(AMBIGUOUS_RECORD=False)
    x = x.sort_values(["EMPLOYEEID", "SALARY_HEAD_CLEAN", "FROMDT", "TODT"],
                      ascending=[True, True, False, True], na_position="last")
    keys = ["EMPLOYEEID", "SALARY_HEAD_CLEAN"]
    latest_from = x.groupby(keys, dropna=False).FROMDT.transform("max")
    contenders = x[x.FROMDT.eq(latest_from)].copy()
    ties = contenders.groupby(keys, dropna=False).size().rename("TIE_COUNT")
    x = x.drop_duplicates(keys, keep="first").merge(ties, on=keys, how="left")
    x["AMBIGUOUS_RECORD"] = x.TIE_COUNT.fillna(1).gt(1)
    return x


def employee_filtered(df, zones, branches, departments, genders):
    for col, chosen in [("ZONE", zones), ("BRANCH", branches),
                        ("DEPARTMENT", departments), ("GENDER", genders)]:
        if chosen:
            df = df[df[col].fillna("Unknown").astype(str).isin(chosen)]
    return df


def month_series(data, col, beginning, ending):
    dates = data[col].dropna()
    dates = dates[(dates >= pd.Timestamp(beginning)) & (dates <= pd.Timestamp(ending))]
    return dates.dt.to_period("M").value_counts().sort_index()


def download_csv(data, title):
    st.download_button("Download CSV", data.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{title}.csv", mime="text/csv", key=f"download_{title}")



# ----------------- Executive HR dashboard presentation -----------------
import plotly.graph_objects as go

st.markdown('''<style>
/* Scoped to this HR page. Leave the shared app/sidebar intact. */
[data-testid="stMainBlockContainer"], .main .block-container {
    max-width:100% !important; width:100% !important;
    padding:0.35rem 0.8rem 1.3rem !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {gap:.48rem !important;}
.hr-topbar{display:flex;justify-content:space-between;align-items:center;gap:1rem;
    padding:11px 15px;border-radius:10px;background:#122d52;color:white;
    border-left:4px solid #40c7b2;}
.hr-topbar strong{font-size:17px;letter-spacing:-.3px;color:#fff;}
.hr-topbar .hr-top-caption{font-size:11px;color:#c9dbed;}
.hr-kicker{font-size:10px;font-weight:700;letter-spacing:1.4px;color:#8eddd8;}
.hr-chip{position:relative;overflow:hidden;border:1px solid rgba(255,255,255,.24);border-radius:13px;
  background:linear-gradient(135deg,var(--kpi-a,#1465b8),var(--kpi-b,#26a4db));
  padding:12px 14px;min-height:113px;box-shadow:0 5px 14px rgba(18,45,82,.12);color:#fff;}
.hr-chip:after{content:"";position:absolute;width:110px;height:110px;right:-38px;bottom:-55px;
  background:rgba(255,255,255,.10);border-radius:50%;pointer-events:none;}
.hr-chip .hr-chip-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
.hr-chip .lbl{font-size:11px;color:rgba(255,255,255,.96);font-weight:700;line-height:1.3;}
.hr-chip .hr-kpi-icon{display:inline-flex;align-items:center;justify-content:center;flex:0 0 33px;
  width:33px;height:33px;border-radius:10px;background:rgba(255,255,255,.22);
  border:1px solid rgba(255,255,255,.27);font-size:18px;line-height:1;}
.hr-chip .val{font-size:27px;color:white;font-weight:800;line-height:1.25;margin-top:3px;letter-spacing:-.6px;}
.hr-chip .foot{font-size:10px;color:rgba(255,255,255,.83);margin-top:5px;line-height:1.28;}
@media(max-width:1100px){.hr-chip{min-height:104px;padding:10px 11px;}.hr-chip .val{font-size:24px;}}

.hr-section-header{font-size:14px !important;font-weight:750;color:#172e50;margin:18px 0 12px !important;padding:0 0 6px;line-height:1.45;clear:both;border-bottom:1px solid #e9eef6;}
.hr-note{padding:10px 13px;background:#eff7ff;border:1px solid #dceafa;border-radius:9px;color:#34516f;font-size:12px;}
.hr-small{font-size:11px;color:#64748b;}
.st-key-hr_nav_row button {min-height:35px !important;border-radius:9px !important;font-size:11.5px !important;
    padding:4px 6px !important;font-weight:650 !important;white-space:nowrap !important;}
.st-key-hr_nav_row button[kind="primary"]{background:#17618c !important;border-color:#17618c !important;color:#fff !important;}
.st-key-hr_nav_row button[kind="secondary"]{background:#f7faff !important;border-color:#dce6f0 !important;color:#29415d !important;}
.st-key-hr_nav_row button p{font-size:11.5px !important;}
.st-key-hr_filter_bar {border:1px solid #e1e9f2;border-radius:10px;padding:8px 12px;
    background:#f8fafc;margin-top:4px;}
.st-key-hr_filter_bar [data-testid="stWidgetLabel"] p{font-size:11px !important;}
[data-testid="stPlotlyChart"]{border:1px solid #e2eaf3;border-radius:10px;padding:4px;background:#fff;}
[data-testid="stDataFrame"] {border-radius:9px;overflow:hidden;}
[data-testid="stSelectbox"] label p,[data-testid="stMultiSelect"] label p {font-size:11px;}
@media(max-width:850px){[data-testid="stMainBlockContainer"],.main .block-container{padding:.35rem .4rem !important;}
 .hr-topbar .hr-top-caption{display:none;}.hr-chip .val{font-size:22px;}}
</style>''',unsafe_allow_html=True)


# Presentation-only mapping; SQL, HR logic and calculations remain unchanged.
HR_KPI_STYLES = {
    "Active workforce": ("👥", "#075985", "#0ea5e9"),
    "Resigned, still employed": ("📨", "#9a3412", "#f97316"),
    "LWD pending": ("⏳", "#a16207", "#eab308"),
    "Completed exits": ("🚪", "#6d28d9", "#a78bfa"),
    "Re-joining candidates": ("🔄", "#047857", "#34d399"),
    "Re-joining to review": ("🛡️", "#be123c", "#fb7185"),
    "Joined YTD": ("📈", "#0369a1", "#38bdf8"),
    "Exited YTD": ("📉", "#b45309", "#f59e0b"),
    "Net movement YTD": ("⚖️", "#0f766e", "#2dd4bf"),
    "Indicative exit ratio": ("📊", "#7c3aed", "#a78bfa"),
    "Confirmed re-joining": ("✅", "#15803d", "#4ade80"),
}
HR_KPI_FALLBACK = ("📌", "#1d4ed8", "#60a5fa")


def hr_metric(label, value, subtitle=""):
    icon, color_a, color_b = HR_KPI_STYLES.get(label, HR_KPI_FALLBACK)
    st.markdown(
        f'<div class="hr-chip" style="--kpi-a:{color_a};--kpi-b:{color_b}">'
        f'<div class="hr-chip-top"><div class="lbl">{escape(str(label))}</div>'
        f'<span class="hr-kpi-icon" aria-hidden="true">{icon}</span></div>'
        f'<div class="val">{escape(str(value))}</div>'
        f'<div class="foot">{escape(str(subtitle))}</div></div>',
        unsafe_allow_html=True,
    )


def hr_plot(fig, height=300):
    # Show readable dark-blue values on every horizontal / vertical bar chart.
    # Pie and other chart traces remain unchanged.
    for trace in fig.data:
        if trace.type == "bar":
            horizontal = getattr(trace, "orientation", None) == "h"
            trace.update(
                texttemplate="%{x:,.0f}" if horizontal else "%{y:,.0f}",
                textposition="outside",
                textfont=dict(color="#123B70", size=12, family="Arial Black"),
                cliponaxis=False,
            )
    fig.update_layout(template="plotly_white", height=height,
        margin=dict(l=22,r=72,t=65,b=52),font=dict(family="Arial",size=11,color="#38506b"),
        paper_bgcolor="white",plot_bgcolor="white",showlegend=True,
        legend=dict(orientation="h",y=1.02,x=0,xanchor="left",yanchor="bottom"),
        autosize=True)
    fig.update_xaxes(showgrid=True,gridcolor="#edf2f7",zeroline=False)
    fig.update_yaxes(showgrid=False,zeroline=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})


st.markdown('''<div class="hr-topbar"><div><div class="hr-kicker">SUGAM  /  PEOPLE INTELLIGENCE</div>
<strong>HR Command Center</strong></div><div class="hr-top-caption">Workforce &nbsp;•&nbsp; Retention &nbsp;•&nbsp; Re-Joining &nbsp;•&nbsp; Payroll</div></div>''',unsafe_allow_html=True)

try:
    employees_raw, salary_raw = load_data()
except Exception as exc:
    st.error("SQL Server se HR data load nahi ho raha. DB credentials, network aur database permissions check karein.")
    with st.expander("Technical error"):
        st.code(f"{type(exc).__name__}: {exc}")
    st.stop()

with st.container(key="hr_filter_bar"):
    filter_cols = st.columns([1,1.1,1.1,1.25,1,.68],gap="small")
    asof = filter_cols[0].date_input("As of date",value=date.today(),max_value=date.today(),key="hr_asof_exec")
    emp_all = prepare_employees(employees_raw,asof)
    rejoining_all = prepare_rejoining(emp_all)
    sal_all = prepare_salary(salary_raw)
    def selector(where, label, field):
        return where.multiselect(label, sorted(emp_all[field].dropna().astype(str).unique()),key=f"hr_exec_{field}")
    zones=selector(filter_cols[1],"Zone","ZONE")
    branches=selector(filter_cols[2],"Branch","BRANCH")
    departments=selector(filter_cols[3],"Department","DEPARTMENT")
    genders=selector(filter_cols[4],"Gender","GENDER")
    with filter_cols[5]:
        st.write("")
        if st.button("↻ Refresh",key="hr_exec_refresh",use_container_width=True):
            load_data.clear();st.rerun()

emp=employee_filtered(emp_all,zones,branches,departments,genders)
emp_ids=set(emp.EMPLOYEEID.dropna())
salary=sal_all[sal_all.EMPLOYEEID.isin(emp_ids)].copy()
snapshot=salary_snapshot(salary,asof)
rejoining=rejoining_all[rejoining_all.EMPLOYEEID.isin(emp_ids)].copy()
sections=[("Overview","Overview"),("Resignations & Exits","Resignations"),("Workforce Demographics","Demographics"),
          ("Salary & Cost (Provisional)","Salary & Cost"),("Employee Explorer","Employees"),("Re-Joining Analysis","Re-Joining")]
if st.session_state.get("hr_selected_section") not in [k for k,_ in sections]:
    st.session_state["hr_selected_section"]="Overview"
with st.container(key="hr_nav_row"):
    cols=st.columns(6,gap="small")
    for c,(key,label) in zip(cols,sections):
        chosen=st.session_state.hr_selected_section==key
        if c.button(("✓ " if chosen else "")+label,key="hr_nav_exec_"+label,
                    type="primary" if chosen else "secondary",use_container_width=True):
            st.session_state.hr_selected_section=key;st.rerun()

page=st.session_state.hr_selected_section
active_emp=emp.loc[emp.ACTIVE_HEADCOUNT.eq(1)].copy()

if page=="Overview":
    active=int(emp.ACTIVE_HEADCOUNT.sum())
    resigned=int(emp.RESIGNED_NOT_LEFT.sum())
    pending=int(emp.STATUS.eq("RESIGNED - LWD PENDING").sum())
    exited=int(emp.STATUS.eq("LEFT").sum())
    confirmed=int(rejoining.REJOINING_STATUS.eq("REJOINED - PRIOR EXIT RECORDED").sum())
    review=int(rejoining.REJOINING_STATUS.str.startswith("REVIEW",na=False).sum())
    asof_ts=pd.Timestamp(asof)
    month_start=asof_ts.replace(day=1)
    year_start=asof_ts.replace(month=1,day=1)
    join_ytd=int(emp.DOJ.between(year_start,asof_ts).sum())
    exit_ytd=int(emp.DATEOFLEAVING.between(year_start,asof_ts).sum())
    net_ytd=join_ytd-exit_ytd
    base_headcount=int(((emp.DOJ.notna()) & (emp.DOJ<year_start) &
       (emp.DATEOFLEAVING.isna() | (emp.DATEOFLEAVING>=year_start))).sum())
    attrition=(exit_ytd / ((base_headcount+active)/2)*100) if (base_headcount+active)>0 else 0
    kpis=[
       ("Active workforce",active,"As of selected date"),
       ("Resigned, still employed",resigned,"Includes notice & LWD pending"),
       ("LWD pending",pending,"HR follow-up required"),
       ("Completed exits",exited,"Cumulative exits"),
       ("Re-joining candidates",len(rejoining),"Aadhaar/PAN linked"),
       ("Re-joining to review",review,"Identity/history validation"),
    ]
    metric_cols=st.columns(6,gap="small")
    for c,(label,val,detail) in zip(metric_cols,kpis):
        with c: hr_metric(label,f"{val:,}",detail)
    st.markdown('<div class="hr-section-header">People movement · Year to date</div>',unsafe_allow_html=True)
    summary_cols=st.columns(5,gap="small")
    for c,(name,value,desc) in zip(summary_cols,[
       ("Joined YTD",f"{join_ytd:,}","Recorded joining dates"),
       ("Exited YTD",f"{exit_ytd:,}","Recorded last working dates"),
       ("Net movement YTD",f"{net_ytd:+,}","Joinings less exits"),
       ("Indicative exit ratio",f"{attrition:.1f}%","YTD exits / avg headcount"),
       ("Confirmed re-joining",f"{confirmed:,}","Prior exit recorded")]):
        with c:hr_metric(name,value,desc)
    a,b=st.columns([1.15,1],gap="medium")
    with a:
        st.markdown('<div class="hr-section-header">Active employees · Top 12 departments</div>',unsafe_allow_html=True)
        counts=active_emp.DEPARTMENT.fillna("Unknown").value_counts().head(12).sort_values()
        if not counts.empty:
            fig=px.bar(x=counts.values,y=counts.index,orientation="h",text=counts.values,color_discrete_sequence=["#246c9b"])
            fig.update_traces(textposition="outside",cliponaxis=False,marker_line_width=0)
            fig.update_layout(xaxis_title=None,yaxis_title=None,showlegend=False,margin=dict(l=22,r=60,t=20,b=35),xaxis=dict(range=[0,max(counts.values)*1.18]))
            hr_plot(fig,370)
        else:st.info("No active department data")
    with b:
        st.markdown('<div class="hr-section-header">Active employees · Zone distribution</div>',unsafe_allow_html=True)
        counts=active_emp.ZONE.fillna("Unknown").value_counts().head(10).sort_values()
        if not counts.empty:
            fig=px.bar(x=counts.values,y=counts.index,orientation="h",text=counts.values,color_discrete_sequence=["#13a49c"])
            fig.update_traces(textposition="outside",cliponaxis=False)
            fig.update_layout(xaxis_title=None,yaxis_title=None,showlegend=False,xaxis=dict(range=[0,max(counts.values)*1.2]))
            hr_plot(fig,370)
        else:st.info("No active zone data")
    left,right=st.columns([1.6,1],gap="medium")
    with left:
        st.markdown('<div class="hr-section-header">Monthly joining vs exits · Last 12 months</div>',unsafe_allow_html=True)
        end=asof_ts;start=(end.to_period("M")-11).to_timestamp()
        months=pd.period_range(start.to_period("M"),end.to_period("M"),freq="M")
        joined=month_series(emp,"DOJ",start,end).reindex(months,fill_value=0)
        left_dates=month_series(emp,"DATEOFLEAVING",start,end).reindex(months,fill_value=0)
        monthly=pd.DataFrame({"Month":[str(i) for i in months],"Joined":joined.values,"Exited":left_dates.values})
        fig=go.Figure()
        fig.add_bar(x=monthly.Month,y=monthly.Joined,name="Joined",marker_color="#287eae")
        fig.add_bar(x=monthly.Month,y=monthly.Exited,name="Exited",marker_color="#f19b73")
        fig.update_layout(barmode="group",yaxis_title=None,legend=dict(orientation="h",x=0,y=1.02,yanchor="bottom"))
        hr_plot(fig,305)
    with right:
        st.markdown('<div class="hr-section-header">People operations · Attention queue</div>',unsafe_allow_html=True)
        upcoming=int((emp.RESIGNED_NOT_LEFT.eq(1)&emp.NOTICE_DAYS_REMAINING.between(0,30)).sum())
        missing_doj=int(emp.DOJ.isna().sum())
        future_lwd=int((emp.ACTIVE_HEADCOUNT.eq(1)&emp.DATEOFLEAVING.between(asof_ts,asof_ts+pd.Timedelta(days=30))).sum())
        st.markdown(f"""<div class="hr-note" style="line-height:1.95">
        <b>{upcoming:,}</b> resignation exits due in 30 days<br>
        <b>{future_lwd:,}</b> scheduled LWDs within 30 days<br>
        <b>{pending:,}</b> resignations without LWD<br>
        <b>{review:,}</b> re-joining records requiring review<br>
        <b>{missing_doj:,}</b> records missing joining date
        </div>""",unsafe_allow_html=True)
    left,right=st.columns([1.12,1],gap="medium")
    with left:
        st.markdown('<div class="hr-section-header">Workforce profile · Age and service</div>',unsafe_allow_html=True)
        age=active_emp.AGE_GROUP.value_counts().reindex(["<25","25-30","31-40","41-50","51+"],fill_value=0)
        tenure=active_emp.SERVICE_GROUP.value_counts().reindex(["0-1 Year","1-3 Years","3-5 Years","5-10 Years","10+ Years"],fill_value=0)
        c1,c2=st.columns(2,gap="small")
        with c1:
            st.caption("Age distribution")
            fig=px.bar(x=age.index,y=age.values,color_discrete_sequence=["#2e88b2"])
            fig.update_layout(showlegend=False,xaxis_title=None,yaxis_title=None)
            hr_plot(fig,255)
        with c2:
            st.caption("Service tenure")
            fig=px.bar(x=tenure.index,y=tenure.values,color_discrete_sequence=["#21a49c"])
            fig.update_layout(showlegend=False,xaxis_title=None,yaxis_title=None)
            fig.update_xaxes(tickangle=-35)
            hr_plot(fig,255)
    with right:
        st.markdown('<div class="hr-section-header">Workforce status · Count and share</div>',unsafe_allow_html=True)
        status=emp.STATUS.value_counts()
        if not status.empty:
            colors=["#267eae","#f09a75","#28a9a0","#a6b5cf","#7887a8","#d7e2f1"]
            fig=go.Figure(go.Bar(x=status.values,y=status.index,orientation="h",marker_color=colors[:len(status)],
                                text=status.values,textposition="outside",cliponaxis=False))
            fig.update_layout(showlegend=False,xaxis_title=None,yaxis_title=None,
                              xaxis=dict(range=[0,max(status.values)*1.25]))
            hr_plot(fig,290)
        else:st.info("No employee status data")
    st.caption("Headcount and ratios depend on selected filters and as-of date. Exit ratio is indicative, not a statutory attrition measure. Re-joining cases are identity matches pending HR verification.")

elif page=="Resignations & Exits":
    waiting=emp[emp.RESIGNED_NOT_LEFT.eq(1)].copy()
    k=st.columns(4)
    for c,label,value,desc in zip(k,["Resigned, still employed","LWD confirmed","LWD pending","Leaving in 30 days"],
        [len(waiting),waiting.STATUS.eq("SERVING NOTICE PERIOD").sum(),waiting.STATUS.eq("RESIGNED - LWD PENDING").sum(),waiting.NOTICE_DAYS_REMAINING.between(0,30).sum()],
        ["Includes notice period","Future exit planned","Needs HR update","Priority handover"]):
        with c:hr_metric(label,f"{int(value):,}",desc)
    st.markdown('<div class="hr-section-header">Notice period tracker</div>',unsafe_allow_html=True)
    cols=["EMPCODE","EMPNAME","ZONE","BRANCH","DEPARTMENT","RESIGNDT","DATEOFLEAVING","NOTICE_DAYS_REMAINING","STATUS"]
    st.dataframe(waiting[cols].sort_values("RESIGNDT",ascending=False),use_container_width=True,hide_index=True)
    download_csv(waiting[cols],"resigned_not_left")
    st.markdown('<div class="hr-section-header">Monthly completed exits</div>',unsafe_allow_html=True)
    years=sorted(emp.DATEOFLEAVING.dropna().dt.year.unique().tolist())
    if years:
        year=st.selectbox("Exit year",years,index=len(years)-1)
        months=emp.loc[(emp.DATEOFLEAVING.dt.year==year)&(emp.DATEOFLEAVING<=pd.Timestamp(asof)),"DATEOFLEAVING"].dt.month.value_counts().reindex(range(1,13),fill_value=0)
        fig=px.bar(x=[calendar.month_abbr[i] for i in range(1,13)],y=months.values,
                   labels={"x":"Month","y":"Exits"},color_discrete_sequence=["#ee8966"])
        hr_plot(fig,270)
    else:st.info("No recorded exits for selected filters.")

elif page=="Workforce Demographics":
    k=st.columns(4)
    for c,field,title in zip(k,["GENDER","AGE_GROUP","SERVICE_GROUP","STATUS"],["Gender mix","Age bands","Tenure bands","Status breakdown"]):
        with c:
            st.markdown(f'<div class="hr-section-header">{title}</div>',unsafe_allow_html=True)
            group=active_emp[field].fillna("Unknown").value_counts()
            fig=px.pie(names=group.index,values=group.values,hole=.6,
                       color_discrete_sequence=["#216a9e","#17a5a8","#ffb474","#86a1bf","#c1d0df"])
            fig.update_layout(showlegend=False);fig.update_traces(textinfo="label+percent")
            hr_plot(fig,265)
    st.caption("Age and tenure reflect the selected as-of date; active employees only.")
    st.markdown('<div class="hr-section-header">Workforce composition by department</div>',unsafe_allow_html=True)
    top=active_emp.DEPARTMENT.value_counts().head(15).sort_values()
    fig=px.bar(x=top.values,y=top.index,orientation="h",color_discrete_sequence=["#236a95"])
    fig.update_layout(xaxis_title="Employees",yaxis_title=None,showlegend=False)
    hr_plot(fig,400)

elif page=="Salary & Cost (Provisional)":
    st.warning("Payroll calculations are provisional. Salary structure and monthly overrides overlap; deductions and employer contributions require confirmation.")
    if snapshot.empty: st.info("No salary records effective on the selected reporting date.")
    else:
        ambiguities=int(snapshot.AMBIGUOUS_RECORD.sum())
        safe=snapshot[~snapshot.AMBIGUOUS_RECORD & snapshot.SALARY_CATEGORY.ne("UNCLASSIFIED")].copy()
        pivot=safe.pivot_table(index="EMPLOYEEID",columns="SALARY_CATEGORY",values="AMOUNT",aggfunc="sum",fill_value=0).reset_index()
        for col in ["EARNINGS","EMPLOYEE DEDUCTION","EMPLOYER COST"]:
            if col not in pivot:pivot[col]=0
        pivot["INDICATIVE_NET"]=pivot["EARNINGS"]-pivot["EMPLOYEE DEDUCTION"]
        pivot["INDICATIVE_EMPLOYER_COST"]=pivot["EARNINGS"]+pivot["EMPLOYER COST"]
        current_ids=set(active_emp.EMPLOYEEID.dropna()); current=pivot[pivot.EMPLOYEEID.isin(current_ids)]
        k=st.columns(4)
        for c,title,col in zip(k,["Gross earnings","Employee deductions","Indicative take-home","Indicative employer cost"],
                                ["EARNINGS","EMPLOYEE DEDUCTION","INDICATIVE_NET","INDICATIVE_EMPLOYER_COST"]):
            with c:hr_metric(title,f'₹{current[col].sum():,.0f}',"Provisional total")
        if ambiguities:st.error(f"{ambiguities} employee/head records have ambiguous effective-date overlaps; omitted from these totals.")
        others=int(snapshot.SALARY_CATEGORY.eq("UNCLASSIFIED").sum())
        if others:st.warning(f"{others} salary records have unclassified heads and are excluded from totals.")
        names=emp[["EMPLOYEEID","EMPCODE","EMPNAME","ZONE","BRANCH","DEPARTMENT"]].drop_duplicates("EMPLOYEEID")
        details=pivot.merge(names,on="EMPLOYEEID",how="left")
        left,right=st.columns([1.2,1])
        with left:
            st.markdown('<div class="hr-section-header">Highest indicative payroll by department</div>',unsafe_allow_html=True)
            dep=details[details.EMPLOYEEID.isin(current_ids)].groupby("DEPARTMENT",dropna=False)["INDICATIVE_EMPLOYER_COST"].sum().nlargest(10).sort_values()
            fig=px.bar(x=dep.values,y=dep.index,orientation="h",color_discrete_sequence=["#23769c"])
            fig.update_layout(xaxis_title="₹ employer cost",yaxis_title=None,showlegend=False)
            hr_plot(fig,310)
        with right:
            st.markdown('<div class="hr-section-header">Salary head classification</div>',unsafe_allow_html=True)
            audit=snapshot.SALARY_CATEGORY.value_counts()
            fig=px.pie(names=audit.index,values=audit.values,hole=.65,
                       color_discrete_sequence=["#28779c","#f4a56c","#31a99e","#9aa9be"])
            hr_plot(fig,310)
        st.markdown('<div class="hr-section-header">Employee-wise provisional salary</div>',unsafe_allow_html=True)
        st.dataframe(details,use_container_width=True,hide_index=True)
        download_csv(details,"provisional_salary_summary")
        option=names.copy();option["CHOICE"]=option.EMPCODE.fillna("").astype(str)+" | "+option.EMPNAME.fillna("").astype(str)
        choice=st.selectbox("Explore an employee's salary history",option.CHOICE.tolist() if len(option) else ["No employees"])
        if len(option):
            eid=option.loc[option.CHOICE.eq(choice),"EMPLOYEEID"].iloc[0]
            st.dataframe(salary.loc[salary.EMPLOYEEID.eq(eid),["SALARY_HEAD_CLEAN","SALARY_CATEGORY","AMOUNT","PCTG","FROMDT","TODT"]].sort_values(["SALARY_HEAD_CLEAN","FROMDT"]),hide_index=True,use_container_width=True)
            st.caption("Historical percentage-based PF amounts are not estimated without a confirmed wage base.")

elif page=="Employee Explorer":
    st.markdown('<div class="hr-section-header">Employee directory</div>',unsafe_allow_html=True)
    q=st.text_input("Search employee code or name",placeholder="Type employee code or name…")
    shown=emp.copy()
    if q.strip():shown=shown[shown.EMPNAME.fillna("").astype(str).str.contains(q,case=False,regex=False)|shown.EMPCODE.fillna("").astype(str).str.contains(q,case=False,regex=False)]
    col=["EMPLOYEEID","EMPCODE","EMPNAME","ZONE","BRANCH","DEPARTMENT","GENDER","DOJ","AGE","SERVICE_YEARS","RESIGNDT","DATEOFLEAVING","STATUS"]
    st.dataframe(shown[col],use_container_width=True,hide_index=True)
    download_csv(shown[col],"employees_dashboard")
    with st.expander("Data quality monitor"):
        st.write("Duplicate employee IDs:",int(emp_all.EMPLOYEEID.duplicated().sum()))
        st.write("Missing DOJ:",int(emp_all.DOJ.isna().sum()))
        st.write("LWD before joining:",int(((emp_all.DATEOFLEAVING<emp_all.DOJ)&emp_all.DATEOFLEAVING.notna()).sum()))
        st.write("Resignation date after leaving:",int(((emp_all.RESIGNDT>emp_all.DATEOFLEAVING)&emp_all.RESIGNDT.notna()).sum()))
        st.write("Salary lines without FROMDT:",int(sal_all.FROMDT.isna().sum()))

elif page=="Re-Joining Analysis":
    confirmed=rejoining.REJOINING_STATUS.eq("REJOINED - PRIOR EXIT RECORDED")
    review=rejoining.REJOINING_STATUS.str.startswith("REVIEW",na=False)
    c=st.columns(4)
    for box,label,num,sub in zip(c,["Potential re-joins","Confirmed previous exits","Require review","Matched by PAN only"],
                                 [len(rejoining),int(confirmed.sum()),int(review.sum()),int(rejoining.MATCH_METHOD.eq("PAN").sum())],
                                 ["Multiple employee IDs","Previous LWD before new DOJ","History or identity anomaly","Aadhaar match unavailable"]):
        with box:hr_metric(label,f"{num:,}",sub)
    st.markdown('<div class="hr-note">Matching priority: Aadhaar and PAN; both identifiers matching gives higher confidence. Conflicting identifiers, missing prior LWD or overlapping employment must be reviewed. Full identity numbers are never displayed.</div>',unsafe_allow_html=True)
    if rejoining.empty:st.info("No candidate re-joining records under the current filters.")
    else:
        a,b=st.columns(2)
        with a:
            cat=rejoining.MATCH_METHOD.value_counts()
            fig=px.bar(x=cat.index,y=cat.values,labels={"x":"Match method","y":"Records"},color_discrete_sequence=["#1e799d"])
            fig.update_layout(showlegend=False);hr_plot(fig,225)
        with b:
            cat=rejoining.REJOINING_STATUS.value_counts()
            fig=px.bar(x=cat.values,y=cat.index,orientation="h",color_discrete_sequence=["#eaa06a"])
            fig.update_layout(xaxis_title="Records",yaxis_title=None,showlegend=False);hr_plot(fig,225)
        status=st.multiselect("Review status",sorted(rejoining.REJOINING_STATUS.unique()),key="hr_exec_rejoin_status")
        shown=rejoining[rejoining.REJOINING_STATUS.isin(status)] if status else rejoining
        cols=["EMPCODE","EMPNAME","MATCH_METHOD","AADHAAR_MASKED","PAN_MASKED","ZONE","BRANCH","DEPARTMENT","DOJ","PREVIOUS_EMPCODE","PREVIOUS_DOJ","PREVIOUS_LWD","DAYS_BETWEEN","REJOINING_STATUS","STATUS"]
        st.dataframe(shown[cols].sort_values("DOJ",ascending=False),use_container_width=True,hide_index=True)
        download_csv(shown[cols],"hr_rejoining_review")

st.caption("SQL Server live read · Salary estimated until payroll mapping approved · Aadhaar/PAN masked in UI/exports · LWD included in active headcount through that date. Restrict HR dashboard access to authorized roles.")
