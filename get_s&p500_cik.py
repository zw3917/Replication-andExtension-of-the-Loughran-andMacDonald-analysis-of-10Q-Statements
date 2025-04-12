# %%
import os
import re
import pandas as pd
import numpy as np

from datetime import timedelta, datetime
from pathlib import Path
import wrds

# %%
db = wrds.Connection(wrds_username="zw3917") 

# Get PERMNOs in S&P500
years = ['2020','2021','2022','2023','2024']
for year in years:
    start = '12/31/'+year
    end = '01/01/'+year
    sp500_permnos = db.raw_sql(f"""
        SELECT DISTINCT permno, start, ending
        FROM crsp.msp500list
        WHERE start <= '{start}'
        AND ending >= '{end}' 
    """)

    permno_list = tuple(sp500_permnos['permno'].tolist())
    print(len(permno_list))
    link_df = db.raw_sql(f"""
        SELECT DISTINCT lpermno AS permno, gvkey
        FROM crsp.ccmxpf_linktable
        WHERE lpermno IN {permno_list}
          AND linktype IN ('LU', 'LC')
          AND usedflag = 1
    """)

    gvkey_list = tuple(link_df['gvkey'].unique().tolist())
    print(len(gvkey_list))
    cik_df = db.raw_sql(f"""
        SELECT DISTINCT gvkey, cik, conm
        FROM comp.company
        WHERE gvkey IN {gvkey_list}
        AND cik != 'None'
    """)

    cik_df.to_csv('sp500_cik_'+year+'.csv', index=False)
    print(len(cik_df['cik'].unique().tolist()))


