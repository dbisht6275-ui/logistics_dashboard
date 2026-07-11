import streamlit as st
import pandas as pd
from sqlalchemy import text
from services.database import get_engine


@st.cache_data(ttl=300)
def load_stationmast_data(start_date, end_date):

    engine = get_engine()

    query = f"""
        SELECT 
            ZONE.ZONENAME AS ZONE,
            IIF(S.OWNED='Y','BRANCH',IIF(S.ISAGENCY='Y','AGENCY','')) AS TYPE,
            S.STNNAME AS BRANCH,
            S.STNCODE AS CODE,
            S.CITY,
            S.STATE,
            S.ZIPCODE AS PINCODE,
            S.COUNTRY,
            S.activedate,
            S.closedate,
            S.booking,
            S.delivery,
            S.ishub,
            S.latposition,
            S.longposition,
            CASE
                WHEN S.ACTIVEDATE BETWEEN '{start_date}' AND '{end_date}'
                    THEN 'OPENED'
                WHEN S.CLOSEDATE BETWEEN '{start_date}' AND '{end_date}'
                    THEN 'CLOSED'
            END AS STATUS
                    
        FROM 
            STATIONMAST S
        LEFT JOIN 
            ZONEMAST ZONE ON ZONE.ZONECODE = S.ZONECODE
        WHERE 
            (
                S.ACTIVEDATE BETWEEN '{start_date}' AND '{end_date}'
                OR
                S.CLOSEDATE BETWEEN '{start_date}' AND '{end_date}'
            ) and 
            (S.OWNED = 'Y'  OR S.ISAGENCY='Y')
            AND S.ACTIVE = 'Y' 
            AND LEN(S.STNCODE) = 3 
            AND S.STNCODE NOT IN (
                '583', '921', '911', '880', '881', '437', '584', '901', 
                '650', '906', '931', '932', '938', '021', '100', '941', 
                '421', '585', '250', '912', '450', '195', '922', '923', 
                '380', '952', '933', '935', '934', '052', '051', '200', 
                '942', '007', '914', '915', '904', '902', '936', '937', 
                '381', '924', '451', '903', '905', '913', '916','709',
                '710','711','712','713','714','716','053'
            )
        ORDER BY 
            IIF(ZONE.ZONENAME='NORTH ZONE','1',
            IIF(ZONE.ZONENAME='EAST ZONE','2',
                IIF(ZONE.ZONENAME='NORTH EAST ZONE','3',
                IIF(ZONE.ZONENAME='WEST ZONE','4',
                    IIF(ZONE.ZONENAME='SOUTH ZONE','5',
                    IIF(ZONE.ZONENAME='NEPAL ZONE','6','')))))),
            S.STNCODE, 
            S.STNNAME;

        """

    df = pd.read_sql(query, conn)

    return df

# -------- DATE RANGE FUNCTION --------

def get_date_range(fin_year):
    start_year = int(fin_year.split("-")[0])
    end_year = int(fin_year.split("-")[1])

    return (
        f"{start_year}-04-01",
        f"{end_year}-03-31"
    )