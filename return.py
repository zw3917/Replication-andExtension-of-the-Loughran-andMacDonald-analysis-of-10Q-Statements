# %%
import os
import re
import pandas as pd
import numpy as np

from datetime import timedelta, datetime
from pathlib import Path
import wrds

# %%
def get_permno_from_gvkey(db, gvkey):
    permno_df = db.raw_sql(f"""
                    SELECT gvkey, lpermno AS permno
                    FROM crsp.ccmxpf_linktable
                    WHERE gvkey = '{gvkey}'
                    AND lpermno IS NOT NULL
                    AND linktype IN ('LU', 'LC')  -- active links
                    AND usedflag = 1
                """)
    
    if permno_df.empty:
        print("GVKEY not linked to any PERMNO.")
        return None
    else:
        permno = permno_df['permno'].iloc[0]
        return permno

# %%
# Connect to WRDS
def connect_to_wrds(file, window = 3):
    results = []
    try:
        print("Connecting to WRDS...")
        db = wrds.Connection(wrds_username="zw3917") 
        print("Sucessfully connected to WRDS!")
        for index, row in file.iterrows():
            cik = row['cik']
            cik = str(cik).zfill(10)
            
            date = datetime.strptime(row['date'],'%Y-%m-%d')
            # print(f"CIK: {cik}, Date: {date}")

            # Query to obtain gvkey from cik
            gvkey_df = db.raw_sql(f"""
                SELECT gvkey, cik
                FROM comp.company
                WHERE cik = '{cik}'
            """)

            if gvkey_df.empty:
                print("CIK not found.")
            else:
                gvkey = gvkey_df['gvkey'].iloc[0]

                # Get permno using gvkey
                permno = get_permno_from_gvkey(db, gvkey)
                
                if(permno):
                    startDate = date
                    endDate = date + timedelta(days=window)

                    # Query for excess return data from wrds
                    returns_df = db.raw_sql(f"""
                        SELECT a.date, a.ret, b.sprtrn
                        FROM crsp.dsf AS a
                        JOIN crsp.dsp500 AS b ON a.date = b.caldt
                        WHERE a.permno = {permno}
                        AND a.date BETWEEN '{startDate}' AND '{endDate}'
                    """)

                    if returns_df.empty:
                        continue
                    returns_df = returns_df.sort_values('date').head(window)
                    if len(returns_df) < window:
                        continue
                    else:
                        firm_bh = np.prod(1 + returns_df['ret'].fillna(0)) - 1
                        mkt_bh = np.prod(1 + returns_df['sprtrn'].fillna(0)) - 1
                        cul_df = firm_bh - mkt_bh
                        #returns_df = (returns_df['ret'] - returns_df['sprtrn']).sum()
                        results.append({
                            'cik': cik,
                            'gvkey': gvkey,
                            'date': date,
                            'cumulative_excess_return': cul_df
                        })
        results_df = pd.DataFrame(results)

        results_df.to_csv('excess_returns_1.csv', index=False)

        # Close connection
        db.close()
        print("Connection closed.")
        
    except Exception as e:
        print("\nWRDS connection failed due to:", e)

# %%
if __name__ == '__main__':
    releaseDateMap = pd.read_csv('reset_lm_term_weight_results.csv')
    connect_to_wrds(releaseDateMap)

# %%


# %%



