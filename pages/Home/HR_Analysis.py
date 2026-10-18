"""HR & Salary Analytics | SQL Server + Streamlit.
Run: streamlit run app.py
Salary figures are indicative until payroll-head mapping and effective-date rules are approved.
"""
from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
import calendar

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


# Compact top header and checkmark-style navigation tabs.
st.markdown("""<style>
/* Pull the report closer to the top without changing the app's navigation. */
[data-testid="stMainBlockContainer"] {padding-top: 0.45rem !important;}
.hr-compact-header{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:10px 16px;border-radius:9px;background:linear-gradient(100deg,#12335f,#175f8c);color:white;margin:0 0 5px;box-shadow:0 2px 7px #0c244015}
.hr-compact-header .eyebrow{font-size:9px;letter-spacing:1.1px;font-weight:750;color:#c2e3ff;white-space:nowrap}
.hr-compact-header h2{font-size:18px;line-height:1.2;margin:0;color:white;font-weight:750}
.hr-compact-header .subtitle{font-size:10px;color:#dfedfa;margin:0;white-space:nowrap}
.hr-mini-caption{font-size:10px;color:#79869a;margin:0 0 5px}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:5px;border-bottom:1px solid #dfe8f3;flex-wrap:wrap}
[data-testid="stTabs"] button[role="tab"]{padding:7px 12px;font-size:12px;font-weight:650;border-radius:8px 8px 0 0;color:#3b506e;background:#f4f7fc;border:1px solid #e1e8f1;border-bottom:0;min-height:35px}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]{background:#e8f4ff;color:#10558e;border-color:#7ab7e8;font-weight:750}
/* A tick is shown ONLY on the active tab. */
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::before{content:"✓";display:inline-grid;place-items:center;background:#178064;color:#fff;width:16px;height:16px;min-width:16px;border-radius:50%;font-size:11px;font-weight:800;margin-right:6px}
[data-testid="stMetric"]{padding:9px 11px;border-radius:9px;border:1px solid #e2eaf4;background:#fbfdff}
[data-testid="stMetricValue"]{font-size:22px;color:#143b71}
[data-testid="stMetricLabel"]{font-size:12px}
@media(max-width:850px){.hr-compact-header{display:block}.hr-compact-header .subtitle{white-space:normal;margin-top:3px}}
</style>""", unsafe_allow_html=True)
st.markdown("""<div class="hr-compact-header"><div><div class="eyebrow">SUGAM GROUP / PEOPLE INTELLIGENCE</div><h2>Human Resources Analytics</h2></div><div class="subtitle">Workforce · Resignations · Re-Joining · Salary &amp; Cost</div></div><div class="hr-mini-caption">Live SQL Server data · Payroll estimates provisional pending verification</div>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("**HR Report Controls**")
    asof = st.date_input("Report as of", value=date.today(), max_value=date.today())
    if st.button("Refresh from SQL Server"):
        load_data.clear()
        st.rerun()

try:
    employees_raw, salary_raw = load_data()
except Exception as exc:
    st.error("Could not load data from SQL Server. Check DB secrets, network access, pymssql, and database permissions.")
    with st.expander("Technical details"):
        st.code(f"{type(exc).__name__}: {str(exc)}")
    raise RuntimeError("HR data loading failed; see SQL error above")

emp_all = prepare_employees(employees_raw, asof)
rejoining_all = prepare_rejoining(emp_all)
sal_all = prepare_salary(salary_raw)
with st.sidebar:
    def choose(label, frame, col):
        choices = sorted(frame[col].dropna().astype(str).unique().tolist())
        return st.multiselect(label, choices)
    zones = choose("Zone", emp_all, "ZONE")
    branches = choose("Branch", emp_all, "BRANCH")
    departments = choose("Department", emp_all, "DEPARTMENT")
    genders = choose("Gender", emp_all, "GENDER")
    st.divider()
    st.caption(f"{len(employees_raw):,} employee rows · {len(salary_raw):,} salary rows")

emp = employee_filtered(emp_all, zones, branches, departments, genders)
emp_ids = set(emp.EMPLOYEEID.dropna())
salary = sal_all[sal_all.EMPLOYEEID.isin(emp_ids)].copy()
snapshot = salary_snapshot(salary, asof)

p1, p2, p3, p4, p5, p6 = st.tabs([
    "Overview", "Resignations & Exits", "Workforce Demographics",
    "Salary & Cost (Provisional)", "Employee Explorer", "Re-Joining Analysis"])

with p1:
    active = int(emp.ACTIVE_HEADCOUNT.sum())
    serving = int(emp.RESIGNED_NOT_LEFT.sum())
    left_count = int((emp.STATUS == "LEFT").sum())
    pending = int((emp.STATUS == "RESIGNED - LWD PENDING").sum())
    rejoining_filtered = rejoining_all[rejoining_all.EMPLOYEEID.isin(emp_ids)]
    metrics = [("Active Headcount", active), ("Resigned, Not Left", serving),
               ("LWD Pending", pending), ("Already Left", left_count),
               ("Re-Joining Records", len(rejoining_filtered))]
    cols = st.columns(5)
    for c, (label, value) in zip(cols, metrics):
        c.metric(label, f"{value:,}")
    st.markdown("<div class='hr-section'>Workforce distribution</div>", unsafe_allow_html=True)
    plot_emp = emp[emp.ACTIVE_HEADCOUNT.eq(1)]
    a, b = st.columns(2)
    with a:
        st.subheader("Active headcount by department")
        grp = plot_emp.groupby("DEPARTMENT", dropna=False).size().reset_index(name="Employees")
        st.plotly_chart(px.bar(grp.sort_values("Employees"), x="Employees", y="DEPARTMENT", orientation="h", color="Employees", color_continuous_scale="Blues"), use_container_width=True)
    with b:
        st.subheader("Active headcount by zone")
        grp = plot_emp.groupby("ZONE", dropna=False).size().reset_index(name="Employees")
        st.plotly_chart(px.bar(grp.sort_values("Employees"), x="Employees", y="ZONE", orientation="h", color="Employees", color_continuous_scale="Teal"), use_container_width=True)

    st.markdown("<div class='hr-section'>Talent movement</div>", unsafe_allow_html=True)
    st.subheader("Monthly joining and actual exits — latest 24 months")
    end = pd.Timestamp(asof)
    start = (end.to_period("M") - 23).to_timestamp()
    index = pd.period_range(start.to_period("M"), end.to_period("M"), freq="M")
    new = month_series(emp, "DOJ", start, end).reindex(index, fill_value=0)
    exit_ = month_series(emp, "DATEOFLEAVING", start, end).reindex(index, fill_value=0)
    growth = pd.DataFrame({"Month": index.astype(str), "Joined": new.values, "Left": exit_.values})
    st.plotly_chart(px.line(growth, x="Month", y=["Joined", "Left"], markers=True, color_discrete_sequence=["#1466b8", "#ef7e47"]), use_container_width=True)

with p2:
    st.subheader("Resignations and Notice Period")
    waiting = emp[emp.RESIGNED_NOT_LEFT.eq(1)].copy()
    cols = st.columns(3)
    cols[0].metric("Resigned but still on rolls", len(waiting))
    cols[1].metric("Serving notice with known LWD", int((waiting.STATUS == "SERVING NOTICE PERIOD").sum()))
    cols[2].metric("Resigned, LWD not available", int((waiting.STATUS == "RESIGNED - LWD PENDING").sum()))
    detail_cols = ["EMPCODE", "EMPNAME", "ZONE", "BRANCH", "DEPARTMENT", "RESIGNDT",
                   "DATEOFLEAVING", "NOTICE_PERIOD_DAYS", "NOTICE_DAYS_REMAINING", "STATUS"]
    st.dataframe(waiting[detail_cols].sort_values("RESIGNDT", ascending=False),
                 use_container_width=True, hide_index=True)
    download_csv(waiting[detail_cols], "resigned_not_left")
    st.subheader("Actual exit trend")
    years = sorted(emp.DATEOFLEAVING.dropna().dt.year.unique().tolist())
    if years:
        selected_year = st.selectbox("Exit year", years, index=len(years)-1)
        exits = emp[(emp.DATEOFLEAVING.dt.year == selected_year) &
                    (emp.DATEOFLEAVING <= pd.Timestamp(asof))]
        monthly = exits.DATEOFLEAVING.dt.month.value_counts().reindex(range(1, 13), fill_value=0)
        st.plotly_chart(px.bar(x=[calendar.month_abbr[i] for i in range(1, 13)],
                                y=monthly.values, labels={"x": "Month", "y": "Exits"}),
                        use_container_width=True)
    else:
        st.info("No completed exits in selected employee data.")

with p3:
    active_only = emp[emp.ACTIVE_HEADCOUNT.eq(1)]
    for field, label in [("GENDER", "Gender"), ("AGE_GROUP", "Age groups"),
                         ("SERVICE_GROUP", "Service bands"), ("STATUS", "Current status")]:
        st.subheader(label)
        grp = active_only[field].fillna("UNKNOWN").value_counts().reset_index()
        grp.columns = [label, "Employees"]
        st.plotly_chart(px.bar(grp, x=label, y="Employees"), use_container_width=True)
    st.caption("Age and tenure are evaluated as of the selected reporting date.")

with p4:
    st.warning("Payroll estimates are PROVISIONAL. This source mixes effective salary structures and dated monthly overrides. Gross, deductions, employer cost and net figures require confirmation.")
    if snapshot.empty:
        st.info("No salary records effective on selected report date for the selected employees.")
    else:
        ambiguous = int(snapshot.AMBIGUOUS_RECORD.sum())
        unclassified = int((snapshot.SALARY_CATEGORY == "UNCLASSIFIED").sum())
        if ambiguous:
            st.error(f"{ambiguous} employee/head combinations have multiple records with the same latest FROMDT. Review before relying on totals.")
        if unclassified:
            st.warning(f"{unclassified} selected salary records have unclassified salary heads and are not included in totals.")
        st.caption("Snapshot selection: record effective on the reporting date with latest FROMDT, per employee + salary head. This does not prove payroll paid or month proration.")
        safe = snapshot[~snapshot.AMBIGUOUS_RECORD].copy()
        pivot = safe.pivot_table(index="EMPLOYEEID", columns="SALARY_CATEGORY", values="AMOUNT",
                                 aggfunc="sum", fill_value=0).reset_index()
        for cat in ["EARNINGS", "EMPLOYEE DEDUCTION", "EMPLOYER COST", "UNCLASSIFIED"]:
            if cat not in pivot:
                pivot[cat] = 0.0
        pivot["INDICATIVE_NET"] = pivot["EARNINGS"] - pivot["EMPLOYEE DEDUCTION"]
        pivot["INDICATIVE_EMPLOYER_COST"] = pivot["EARNINGS"] + pivot["EMPLOYER COST"]
        headcount_ids = set(emp.loc[emp.ACTIVE_HEADCOUNT.eq(1), "EMPLOYEEID"])
        pivot_active = pivot[pivot.EMPLOYEEID.isin(headcount_ids)]
        cols = st.columns(4)
        for c, name, val in zip(cols,
            ["Gross earnings (₹)", "Employee deductions (₹)", "Indicative net (₹)", "Indicative employer cost (₹)"],
            [pivot_active["EARNINGS"].sum(), pivot_active["EMPLOYEE DEDUCTION"].sum(),
             pivot_active.INDICATIVE_NET.sum(), pivot_active.INDICATIVE_EMPLOYER_COST.sum()]):
            c.metric(name, f"₹{val:,.0f}")
        st.subheader("Employee salary breakdown — selected effective date")
        names = emp[["EMPLOYEEID", "EMPCODE", "EMPNAME", "BRANCH", "DEPARTMENT"]].drop_duplicates("EMPLOYEEID")
        table = pivot.merge(names, on="EMPLOYEEID", how="left")
        st.dataframe(table, use_container_width=True, hide_index=True)
        download_csv(table, "provisional_salary_summary")
        st.subheader("Salary heads and effective periods")
        emp_opts = names.sort_values("EMPNAME").copy()
        emp_opts["CHOICE"] = emp_opts.EMPCODE.fillna("").astype(str) + " | " + emp_opts.EMPNAME.fillna("").astype(str)
        selection = st.selectbox("Select employee", emp_opts.CHOICE.tolist()) if len(emp_opts) else None
        if selection:
            eid = emp_opts.loc[emp_opts.CHOICE.eq(selection), "EMPLOYEEID"].iloc[0]
            this_emp = salary[salary.EMPLOYEEID.eq(eid)]
            st.dataframe(this_emp[["SALARY_HEAD_CLEAN", "SALARY_CATEGORY", "AMOUNT", "PCTG", "FROMDT", "TODT"]]
                         .sort_values(["SALARY_HEAD_CLEAN", "FROMDT"]), use_container_width=True, hide_index=True)
            st.caption("For historical PF rows with AMOUNT=0 and PCTG=12, no PF amount is inferred. Validate the statutory wage base first.")
        st.subheader("Salary head mapping audit")
        audit = salary.groupby(["SALARY_HEAD_CLEAN", "SALARY_CATEGORY"], dropna=False).size().reset_index(name="Rows")
        st.dataframe(audit, use_container_width=True, hide_index=True)

with p5:
    st.subheader("Employee Master")
    term = st.text_input("Find by employee name or code").strip()
    display = emp.copy()
    if term:
        display = display[display.EMPNAME.fillna("").str.contains(term, case=False, regex=False) |
                          display.EMPCODE.fillna("").astype(str).str.contains(term, case=False, regex=False)]
    fields = ["EMPLOYEEID", "EMPCODE", "EMPNAME", "ZONE", "BRANCH", "DEPARTMENT",
              "GENDER", "DOJ", "DOB", "AGE", "SERVICE_YEARS", "RESIGNDT",
              "DATEOFLEAVING", "NOTICE_DAYS_REMAINING", "STATUS", "ACTIVE_HEADCOUNT"]
    st.dataframe(display[fields], use_container_width=True, hide_index=True)
    download_csv(display[fields], "employees_dashboard")
    with st.expander("Data quality checks"):
        st.write("Duplicate employee IDs:", int(emp_all.EMPLOYEEID.duplicated().sum()))
        st.write("Missing DOJ:", int(emp_all.DOJ.isna().sum()))
        st.write("Leaving date earlier than joining:", int(((emp_all.DATEOFLEAVING < emp_all.DOJ) & emp_all.DATEOFLEAVING.notna()).sum()))
        st.write("Resignation date after leaving date:", int(((emp_all.RESIGNDT > emp_all.DATEOFLEAVING) & emp_all.RESIGNDT.notna()).sum()))
        st.write("Salary rows missing FROMDT:", int(sal_all.FROMDT.isna().sum()))

with p6:
    st.subheader("Re-Joining Analysis · Aadhaar / PAN matching")
    st.caption("Matches use valid Aadhaar and/or PAN (BOTH when both match). Conflicting IDs and uncertain exits are flagged for HR review. Full IDs are not shown or exported.")
    found = rejoining_all[rejoining_all.EMPLOYEEID.isin(emp_ids)].copy()
    k1, k2, k3 = st.columns(3)
    k1.metric("Potential rejoining records", len(found))
    k2.metric("Prior exit recorded", int(found.REJOINING_STATUS.eq("REJOINED - PRIOR EXIT RECORDED").sum()) if not found.empty else 0)
    k3.metric("Needs HR verification", int(found.REJOINING_STATUS.str.startswith("REVIEW").sum()) if not found.empty else 0)
    if found.empty:
        st.info("No matching re-joining records found within these filters. Check Aadhaar and PAN completeness in Employee Master.")
    else:
        state = st.multiselect("Rejoining status", sorted(found.REJOINING_STATUS.unique().tolist()), key="hr_rejoin_status")
        if state:
            found = found[found.REJOINING_STATUS.isin(state)]
        columns = ["EMPCODE", "EMPNAME", "MATCH_METHOD", "AADHAAR_MASKED", "PAN_MASKED", "ZONE", "BRANCH", "DEPARTMENT", "DOJ", "PREVIOUS_EMPCODE", "PREVIOUS_DOJ", "PREVIOUS_LWD", "DAYS_BETWEEN", "REJOINING_STATUS", "STATUS"]
        shown = found[columns].sort_values("DOJ", ascending=False)
        st.dataframe(shown, use_container_width=True, hide_index=True)
        download_csv(shown, "hr_rejoining_review")
        st.caption("Aadhaar / PAN matching is a review signal, not proof of identity. Contradictory identity numbers, missing prior LWD and overlapping employment are flagged.")

st.divider()
st.caption("Privacy: Full Aadhaar and PAN are excluded from visualizations and exports. Restrict dashboard access because names, salary and resignation data are sensitive. LWD is treated as the final working day (employee exits next day).")
