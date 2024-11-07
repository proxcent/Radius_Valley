# Radius_Valley
*{Note: This repository is still being developed and will have several additional commits over the next few weeks in preparation for publication of the associated APJ article}*

## Description
Code and data repository for analyzing the Radius Valley characteristic of exoplanet distributions for close in planets with periods of < 100 days and radii < 4 Rꚛ. The code, data and information in the repository can be used to reproduce the Radius Valley research methods used in the APJ article "Precise Parameters from Bayesian SED Fitting Reveal Photoevaporation Likely Driver of Radius Valley" (doi: TBD). Details for each of the main folders of this repository is as follows:

 - **Data** – Contains all initial data files used in the research as well as various inputs and outputs for the SEDmc Python module. The SEDmc module will create additional sub-folders as needed when executed that will be used for both temporary storage and final output results.
 - **SEDmc** – Contains the Python module, SEDmc.py, which uses Bayesian enhanced Spectral Energy Density (SED) fitting methods to estimate accurate and high precision stellar parameters for exoplanet host stars as described in the article. This also contains a Python script, SEDmc_batch_1.py, that can be used to estimate these stellar parameters for a large batch exoplanet host stars similar to what was done for the exoplanet sample derived from the NASA Exoplanet Archive and used in this research.
 - **RV_Analysis** - *{folder to be added}* Contains the Jupyter Notebooks use estimate the slope of the Radius Valley using the sample of exoplanets derived from the NASA Exoplanet Archive. Theses Python notebooks use the final high-precision data from the exoplanet sample to filter and estimate the slope of the Radius Valley using the "Gap Bins" method described in the article for Planet Radius vs. Orbital Period, Planet Radius vs. Planet Insolation Flux, and Planet Radius vs. Stellar Mass. Additional notebooks are then used to estimate uncertainties for both the slope and intercept using Bayesian sampling and statistics. The final notebook can be used to reproduced the plots for the results and compare them with theoretical model and previous observational research as shown in the article.


## Methods & Procedures
*{Details to be added}*
 1. Initial filtering of NASA exoplanet data
 2. Creating batch file input data
 3. Using SEDmc to estimate high-precision stellar parameters
 4. Calculating high-precision planet parameters
 5. Final filtering of planet sample
 6. Estimating the slope of the Radius Valley for each parameter
 7. Creating final plots

*Additional details can be found in README.md files in each main folder, as well as doc strings in individual Python files. Details on the overall research can be found in the article.*
