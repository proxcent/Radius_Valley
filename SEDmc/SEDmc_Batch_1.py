##  SEDmc batch file for all stars ##
##  Run from OS in Radius_Valley directory using "python SEDmc/SEDmc_Batch_1.py" command
##  Ensure prog_flag = False in SEDmc spript to keep it from filling up log file 
##  Create additional batch Python scripts (e.g., SEDmc_Batch_2.py) with associated directories to run conncurrent batch processes using tmux, etc.

import os
import pandas as pd
from datetime import datetime
import subprocess

# Create Logs directory to capture all output messages
if not os.path.exists('Data/Logs'):
    os.makedirs('Data/Logs')
print(os.getcwd())
start_time = datetime.now()    # Capture start time
print('Start Time = ', start_time)

#  Input command line parameter CSV file
#  Example batch input file record: TIC100990000,15.8999	6169,0.1656,ck04,n,54.819538,-42.7630276

input_para = pd.read_csv('Data/Batch/Batch_1/Batch_1_IN_RV_1-300.csv')  # Read batch input file

## Run SEDmc for each star in batch input file
store_bmrk = pd.DataFrame([])
for i in range(len(input_para)):  
    job_start = datetime.now()
    print(i+1, input_para.iloc[i,0], job_start)   # Show star number, name and start time
    out_log = open("Data/Logs/" + input_para.iloc[i,0] + ".txt", "w")   # Start logging output
    print('python SEDmc/SEDmc.py ' + input_para.iloc[i,0] + ' ' + str(input_para.iloc[i,1]) + ' ' +
              str(input_para.iloc[i,2]) + ' ' + str(input_para.iloc[i,3]) + ' ' + input_para.iloc[i,4] + ' ' +
              input_para.iloc[i,5] + ' ' + str(input_para.iloc[i,6]) + ' ' + str(input_para.iloc[i,7]))         #Show command being run
    out = subprocess.run(['python','SEDmc/SEDmc.py',input_para.iloc[i,0],str(input_para.iloc[i,1]),
              str(input_para.iloc[i,2]),str(input_para.iloc[i,3]),input_para.iloc[i,4],
              input_para.iloc[i,5],str(input_para.iloc[i,6]),str(input_para.iloc[i,7])], capture_output=True, text=True)   # Run command
    out_log.write(out.stdout)
    out_log.write(out.stderr)
    out_log.close()
    store_all = pd.read_csv('Data/Run_Data/' + input_para.iloc[i,0] +'_store_best.csv')     # Save all data for current star
    store_bmrk = store_bmrk.append(store_all)    # Add data for current star to batch output file and save
    store_bmrk.to_csv('Data/Batch/Batch_1/Batch_1_OUT_RV_1-300.csv', index=False)
    jobtime = datetime.now() - job_start
    print('Jobtime = ', jobtime)  # Show runtime for each star

# Show runtime for all stars in batch file input
runtime = datetime.now() - start_time
print('Runtime = ', runtime)
