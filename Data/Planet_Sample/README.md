# Radius Valley Planet Sample README

Description of the **Radius Valley Planet Sample.xlsx**  spreadsheet and associated data.

###  Tabs
- PSCompPars_2024.06.02_18.41.42
- Planet & Host All
- Pipeline Criteria
- Planet & Host-Filtered
- Host-Filtered-Batch
- Host-Filtered-Baseline
- Planet & Host-Final
- Planet Table (4)
- Planet Table (MRT)
- Stats & Charts
- Formulas

### Host Star and Planet Parameter Estimation Process
1) Download exoplanet data from NASA Exoplanet Archive @ https://exoplanetarchive.ipac.caltech.edu/ (e.g., **PSCompPars_2024.06.02_18.41.42**)
2) Put in tabular form and filter based on **Pipeline Criteria** before SEDmc analysis (e.g., **Planet & Host All**)
3) Copy filtered planets and host stars to **Planet & Host-Filtered** tab and perform the following steps
	a. Add columns (light orange) and formulas to calculate % fractional uncertainties for relevant planet and star  parameters (e.g., orbital period, planet radius)
	b. Add columns (blue) to clean up stellar parameters, calculate angular diameter and put in batch file format.
	c. Copy these columns to **Host-Filtered-Batch** tab and remove duplicate stars.
	d. Copy columns B-I of **Host-Filtered-Batch** tab with unique host stars to a separate CSV file(s) for running SEDmc batches (e.g., **Batch_1_IN_RV_1-300.csv**).
	e. Add columns (orange) to clean up stellar parameters and put in baseline data file format.
	f. Copy this tab with unique host stars to a separate CSV file (e.g., **Baseline_NASA.csv**).
4) Use SEDmc batch scripts (e.g., **SEDmc_batch_1.py**) as described in doc strings and README.md files for those scripts to estimate accurate and high precision stellar parameters for all host stars.
5) Append columns AR-CS (54 columns) from SEDmc batch output files (e.g., **Batch_1_OUT_RV_1-300.csv**) to associated stars in **Host-Filtered-Baseline** tab (see green columns).
6) Append relevant columns for high precision stellar parameters (Teff & Rstar) from SEDmc in **Host-Filtered-Baseline** tab to the associated planets in the **Planet & Host-Filtered** tab (see XLOOKUP).
7) Perform the following steps in the **Planet & Host-Filtered** tab to estimate the high precision planetary parameters used in the Radius Valley analysis.
	a.  Add columns to calculate % fractional uncertainties and their averages to be used in propagating uncertainties for planet parameters.
b.  Add columns to calculate planet radii and associated uncertainties using both transit depth and star-planet ratio methods and then determine which has highest precision for final values
c.  Add columns to calculate planet insolation flux and associated uncertainties using both NASA provided and Kepler law calculated semi-major axis methods and then determine which has highest precision for final values
8) Perform final filtering based on Planet Criteria for planet radii < or = to 4 $R_ꚛ$ and fractional uncertainties < or = to 5.0%
9) Copy final filtered lists of planets and hosts to Planet & Host Final tab
10) Create **Planet Table (Table 4)** tab and **Planet Table (MRT)** data tab using final results from **Planet & Host Final** tab (green columns)
