# %%
import pandas as pd
import os
import re
import time
import sys
import requests
from time import sleep

import EDGAR_Forms  # This module contains some predefined form groups
import EDGAR_Pac
import General_Utilities


#PARM_FORMS = EDGAR_Forms.f_10Q  # or, for example, PARM_FORMS = ['8-K', '8-K/A']
PARM_FORMS = ['10-Q','10-K'] # ONLY need 10-K report
PARM_BGNYEAR = 2020  # User selected bgn period.  Earliest available is 1994
PARM_ENDYEAR = 2024  # User selected end period.
PARM_BGNQTR = 1  # Beginning quarter of each year
PARM_ENDQTR = 4  # Ending quarter of each year

PARM_EDGARPREFIX = 'https://www.sec.gov/Archives/'

# %%
# Check and filter S&P index
def Sp500Filter(allIndex, year):
    df = pd.read_csv('sp500_ciks/sp500_cik_'+str(year)+'.csv')
    sp500Ciks = df['cik'].apply(lambda x: str(x).zfill(10)).tolist();
    filtered=[]
    for idx in allIndex:
        if idx.cik in sp500Ciks:
            filtered.append(idx)
    return filtered

# %%
def download_forms():

    n_tot = 0
    n_errs = 0
    for year in range(PARM_BGNYEAR, PARM_ENDYEAR + 1):
        for qtr in range(PARM_BGNQTR, PARM_ENDQTR + 1):
            #startloop = time.clock()
            n_qtr = 0
            file_count = {}
            # Setup output path
            path = "index_files/" + str(year) + "/QTR" + str(qtr) + "/" #'{0}{1}\\QTR{2}\\'.format(PARM_PATH, str(year), str(qtr))
            if not os.path.exists(path):
                os.makedirs(path)
                print('Path: {0} created'.format(path))
            master_index = EDGAR_Pac.download_masterindex(year, qtr, True)
            print(master_index[3]);
            masterindex = Sp500Filter(master_index,str(year))
            # ftrd=list(set(list(map(lambda x:re.sub('[\W_]+', '',x.name),masterindex))))
            # z=[i for i in dows if i not in ftrd]
            # any=set([i.name for i in master_index if 'WALGREEN' in i.name])
            if masterindex:
                for item in masterindex:
                    # while EDGAR_Pac.edgar_server_not_available(True):  # kill time when server not available
                    #     pass
                    if item.form in PARM_FORMS:
                        n_qtr += 1
                        # Keep track of filings and identify duplicates
                        fid = str(item.cik) + str(item.filingdate) + item.form
                        if fid in file_count:
                            file_count[fid] += 1
                        else:
                            file_count[fid] = 1
                        # Setup EDGAR URL and output file name
                        url = PARM_EDGARPREFIX + item.path
                        fname = (path + str(item.filingdate) + '_' + item.form.replace('/', '-') + '_' +
                                 item.path.replace('/', '_'))
                        fname = fname.replace('.txt', '_' + str(file_count[fid]) + '.txt')
                        sleep(0.2)
                        return_url = General_Utilities.download_to_file(url, fname)
                        if return_url:
                            n_errs += 1
                        n_tot += 1
                        # time.sleep(1)  # Space out requests
            print(str(year) + ':' + str(qtr) + ' -> {0:,}'.format(n_qtr) + ' downloads completed.') #  Time = ' +
                  # time.strftime('%H:%M:%S', time.gmtime(time.clock() - startloop)) + ' | ' + time.strftime('%c'))
            # f_log.write('{0} | {1} | n_qtr = {2:>8,} | n_tot = {3:>8,} | n_err = {4:>6,} | {5}\n'.
            #            format(year, qtr, n_qtr, n_tot, n_errs, time.strftime('%c')))

            # f_log.flush()

    print('{0:,} total forms downloaded.'.format(n_tot))
    # f_log.write('\n{0:,} total forms downloaded.'.format(n_tot))


if __name__ == '__main__':
    # start = time.clock()
    #print('\n' + time.strftime('%c') + '\nND_SRAF:  Program EDGAR_DownloadForms.py\n')
    download_forms()
    print('\nEDGAR_DownloadForms.py | Normal termination | ')
          # + time.strftime('%H:%M:%S', time.gmtime(time.clock() - start)))
    #print(time.strftime('%c'))



