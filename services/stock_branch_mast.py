"""Branch hierarchy loader used only by the Stock Operations dashboard."""

import pandas as pd
import streamlit as st
from sqlalchemy import text

from services.database import get_engine

@st.cache_data(ttl=3600, show_spinner=False, max_entries=1)
def load_stock_branch_mast():
    """Return Zone, Circle and Branch details mapped by branch code."""
    query = text("""
        SELECT
            ZONE.ZONENAME AS ZONE,
            C.HUBNAME AS CIRCLE,
            IIF(
                S.OWNED = 'Y',
                'BRANCH',
                IIF(S.ISAGENCY = 'Y', 'AGENCY', '')
            ) AS TYPE,
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
        LEFT JOIN VIEWSTATIONMAST C
            ON C.STNCODE = S.STNCODE
        WHERE
            (S.OWNED = 'Y' OR S.ISAGENCY = 'Y')
            AND LEN(S.STNCODE) = 3
            
        ORDER BY
            IIF(
                ZONE.ZONENAME = 'NORTH ZONE', '1',
                IIF(
                    ZONE.ZONENAME = 'EAST ZONE', '2',
                    IIF(
                        ZONE.ZONENAME = 'NORTH EAST ZONE', '3',
                        IIF(
                            ZONE.ZONENAME = 'WEST ZONE', '4',
                            IIF(
                                ZONE.ZONENAME = 'SOUTH ZONE', '5',
                                IIF(ZONE.ZONENAME = 'NEPAL ZONE', '6', '')
                            )
                        )
                    )
                )
            ),
            S.STNCODE,
            S.STNNAME
    """)
    return pd.read_sql(query, get_engine())
