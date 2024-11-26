# SEDmc README
*SEDmc* is a Bayesian enhanced SED fitting module for estimating high accuracy and precision stellar parameters. Current parameters supported are $T_{eff}$ and $R_⁎$ with MCMC derived uncertainties.

This version is currently a procedural Python script that cannot be imported into other Python programs. A version of SEDmc that can be imported can be found in the GitHub repo **Proxcent/SEDmc**. However, that version is not optimized for the high precision Radius Valley parameter estimation for a large group of exoplanet host stars and may fail to provide results for the Radius Valley analysis as described in this repo.

### Notes: 
a. Package versions used in this version can be found in **SEDmc_packages.txt**.
b. **Data/Planet_Sample/Radius Valley Planet Sample.xlsx** (*Sample*) file is use to create input files (e.g., batch, baseline) and will be used to estimate all planet parameters from *SEDmc* output files.
c. Each star can take several minutes to run depending on the processing speed of the host system. The input batch file can separated in smaller groups of stars (e.g., Batch_1_IN_RV_1-300.csv) and be ran concurrently using TMUX or equivalent. 
### SEDmc Parameter Estimation Process
To use this module to reproduce the Radius Valley analysis described in the repo, use the following procedure:
1. If needed, separate **Data/Batch_1/Batch_1_IN_RV_1-1923.csv** file into smaller files with corresponding Batch directories and scripts.
2. Ensure **SED/SEDmc_batch_1.py** references the correct input and output files (e.g., Data/Batch_1/Batch_1_IN_RV_1-1923.csv).
3. Ensure **prog_flag = False** in config.py. Otherwise, log files in Data/Logs will fill up with progress bar data.
4. If no new host stars are being analyzed, then the **Data/Baseline_NASA.csv** file will have all the baseline data needed for reproducing previous results.
5. From OS, run *"python SEDmc/SEDmc_Batch_1.py"* command from the **Radius_Valley** directory. 
6. Copy data from batch output files (e.g., Data/Batch_1/Batch_1_OUT_RV_1-1923.csv) to the *Sample* file as described in step 5 of the README tab of that file.
7. If no other modifications are needed, then the steps 6 & 7 in the README tab of the *Sample* should not be needed and data will update in the **Planet & Host-Filtered** tab automatically.
8. Steps 8 & 9 in *Sample* file README tab may still be needed to confirm **Planet & Host-Final** tab contains original results. 

