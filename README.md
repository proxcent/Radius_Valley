# Radius_Valley
## Description
Code and data repository for analyzing the Radius Valley characteristic of exoplanet distributions for close in planets with periods of < 100 days and radii < 4 $R_ꚛ$. The code, data and information in the repository can be used to reproduce the Radius Valley research methods used in the The Astronomical Journal article; "Precise Parameters from Bayesian SED Fitting Reveal Thermally-Driven Mass Loss Likely Driver of Radius Valley" (DOI: [10.3847/1538-3881/adbe30](https://doi.org/10.3847/1538-3881/adbe30)). Details for each of the main folders of this repository is as follows:

 - **Data** – Contains all initial data files used in the research as well as various inputs and outputs for the *SEDmc* Python module. The **Planet_Sample** folder contains an Excel spreadsheet with the process and data used to generate the final planet sample. See the README tab in that document.  The *SEDmc* module will also create additional sub-folders as needed when executed. Those folders that will be used for both temporary storage and final output reports and results.
 - **SEDmc** – Contains the Python module, **SEDmc.py**, which uses Bayesian enhanced Spectral Energy Density (SED) fitting methods to estimate accurate and high precision stellar parameters for exoplanet host stars as described in the article. This also contains a Python script, **SEDmc_batch_1.py**, that can be used to estimate these stellar parameters for a large batch exoplanet host stars, similar to what was done for the exoplanet sample derived from the NASA Exoplanet Archive and used in this research. See README file in this folder and and doc strings in the Python files for more information.
 - **RV_Analysis** - Contains the Jupyter Notebooks use estimate the slope of the Radius Valley using the sample of exoplanets derived from the NASA Exoplanet Archive. Theses Python notebooks use the final high-precision data from the exoplanet sample to filter and estimate the slope of the Radius Valley using the "Gap Bins" method described in the article for Planet Radius vs. Orbital Period, Planet Radius vs. Planet Insolation Flux, and Planet Radius vs. Stellar Mass. Additional notebooks are then used to estimate uncertainties for both the slope and intercept using MCMC sampling and Bayesian statistics. The **RV_KDE_Plots** notebook can be used to reproduced the plots for the results and compare them with theoretical model and previous observational research as shown in the article. See README file in this folder.


## Methods & Procedures
*Overall process and sources to replicate the Radius Valley analysis described in the article.*
 1. **Initial filtering of NASA exoplanet data:** See Radius Valley Planet Sample spreadsheet in Data/Planet_Sample folder.	
 2. **Create batch file input data:** See Radius Valley Planet Sample spreadsheet in Data/Planet_Sample folder.	
 3. **Estimate high-precision stellar parameters:** See Python files in SEDmc folder
 4. **Calculate high-precision planet parameters:** See Radius Valley Planet Sample spreadsheet in Data/Planet_Sample folder.	
 5. **Final filtering of planet sample:** See Radius Valley Planet Sample spreadsheet in Data/Planet_Sample folder.	
 6. **Estimate the slope of the Radius Valley for each parameter:** See Jupyter Notebooks in RV_Analysis folder.
 7. **Create final plots showing results:** See Jupyter Notebooks in RV_Analysis folder.

*Additional details can be found in README.md files in each main folder, as well as doc strings in individual Python files. Details on the overall research can be found in the article.*
