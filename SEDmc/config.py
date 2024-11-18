# coding=utf-8
# Imports
import numpy as np
import pandas as pd

# Define global variable
#global store_all, starmodel, min_model_temp, max_model_temp, Tau_Teff, \
#    Tau_Radius, wl_min, wl_max, bad_data_idx, bad_cnt, gx, gy, bx, by, \
#    obs_flux, obs_flux_err, obs_wl, obs_wl_idx, min_radius, max_radius
#global star_model, plx, plx_err, teff_dr2, rstar_dr2, mf_df_out, mf_df_temp, \
#    sampler, samples, theta_max, tau, Teff_bmk, Teff_bmk_err, Rstar_bmk, \
#    Rstar_bmk_err, ang_dia_bmk, ang_dia_bmk_err, plx_bmk, plx_bmk_err, \
#    sname, source_name, teff_med, teff_u_neg, teff_u_plus, Rstar_med, Rstar_u_neg, \
#    Rstar_u_plus, fit_err_init, fit_pts_min, teff_pct_u, Rstar_pct_u
#global teff_med_pct_bmk, scale_med, scale_u_neg, scale_u_plus, apprad_med, \
#    apprad_u_neg, apprad_u_plus, ang_dia_emc, ang_dia_emc_u_neg, ang_dia_emc_u_plus, \
#    ang_dia_emc_pct_bmk, Rstar_pct_bmk,teff_pct_u, Rstar_pct_u, fit_pts, \
#    fit_err, fit_qual, fit_star, bl_star, good_data, bad_data, obs_data, position


# Show sampler progress bar?
prog_flag = False

# Set default sampling parameters
nwalkers = 50
niter = 5000
burn_in = 1000
thin = 1
f = 0.1
log_f = np.log(f)

model_lst = ['ck04','nextgen']
starmodel = 'ck04'

use_Teff_bmk = False  # Force use of bennchmark file
bl_source = 'NASA'

# # Observed Photometry Filter Function
# Configuration parameters
wl_min = 0.4
wl_max = 8
# fit_err_max = 0.2
fit_err_init = 0.1
fit_pts_min = 12

## Create tables to store all input parameters and results
## Fit Star using source name
source_name = sname =""
store_all = pd.DataFrame({'Source':sname}, index=[0])

## Create tables to store all samplers data and results
store_sampler_all = pd.DataFrame([])
store_sampler = pd.DataFrame([])
store_test = pd.DataFrame()
check = 0

# Capture all paralax data to chose one with lowest uncertainty
plx_data = pd.DataFrame(columns = ['Plx', 'Plx_err', 'Plx_pre'])



