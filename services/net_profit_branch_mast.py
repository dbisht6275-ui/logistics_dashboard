import streamlit as st
import pandas as pd
from sqlalchemy import text
from services.database import get_engine


@st.cache_data(ttl=3600, show_spinner=False, max_entries=1)
def load_net_profit_branch_mast():

    engine = get_engine()

    query = text("""
        SELECT 
            ZONE.ZONENAME AS ZONE,
            c.hubname as circle,
            IIF(S.OWNED='Y','BRANCH',IIF(S.ISAGENCY='Y','AGENCY','')) AS TYPE,
            S.STNNAME AS BRANCH,
            S.STNCODE AS CODE,
            S.CITY,
            S.STATE,
            S.ZIPCODE AS PINCODE,
            S.COUNTRY,
            S.ACTIVEDATE,
            S.CLOSEDATE,
            S.ACTIVE,
            S.BOOKING,
            S.DELIVERY,
            S.ISHUB,
            S.LATPOSITION,
            S.LONGPOSITION
                    
        FROM STATIONMAST S
        LEFT JOIN ZONEMAST ZONE 
            ON ZONE.ZONECODE = S.ZONECODE
        left join viewstationmast c on c.stncode=s.stncode
        WHERE 
            (S.OWNED = 'Y' OR S.ISAGENCY = 'Y')
            AND LEN(S.STNCODE) = 3
            AND S.STNCODE NOT IN (
                '583', '921', '911', '880', '881', '437', '584', '901', 
                '650', '906', '931', '932', '938', '021', '100', '941', 
                '421', '585', '250', '912', '450', '195', '922', '923', 
                '380', '952', '933', '935', '934', '052', '051', '200', 
                '942', '007', '914', '915', '904', '902', '936', '937', 
                '381', '924', '451', '903', '905', '913', '916', '709',
                '710', '711', '712', '713', '714', '716', '053'
            )

        ORDER BY 
            IIF(ZONE.ZONENAME='NORTH ZONE','1',
            IIF(ZONE.ZONENAME='EAST ZONE','2',
                IIF(ZONE.ZONENAME='NORTH EAST ZONE','3',
                IIF(ZONE.ZONENAME='WEST ZONE','4',
                    IIF(ZONE.ZONENAME='SOUTH ZONE','5',
                    IIF(ZONE.ZONENAME='NEPAL ZONE','6','')))))),
            S.STNCODE,
            S.STNNAME
    """)

    df = pd.read_sql(query, engine)

    return df
