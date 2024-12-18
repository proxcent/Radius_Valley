"""
SEDmc is a Bayesian enhanced SED fitting module for estimating high accuracy and precision stellar parameters

Current parameters supported are Teff and Rstar with MCMC derived uncertianties

This version is currently a procedural Python script that cannot be imported into other Python programs. 
A version of SEDmc that can be imported can be found in the GitHub repo Proxcent/SEDmc. However, that
version is not optimized for the high precision Radius Valley parameter estimation for a large group of
exoplanet host stars and may fail to provide results for the Radius Valley analysis as decribed in this repo.

Notes: 
a. Package versions used in this version can be found in SEDmc_packages.txt.
b. Data/Planet_Sample/Radius Valley Planet Sample.xlsx (Sample) file is use to create input files (e.g., batch, baseline) 
   and will be used to estimate all planet parameters from SEDmc output files.
c. Each star can take several minutes to run depending on the processing speed of the host system. The input batch file
   can seperated in smaller groups of stars (e.g., Batch_1_IN_RV_1-300.csv) and be ran concurrently using TMUX or equivalent. 

To use this module to reproduce the Radius Valley analysis described in the repo, use the following prodedure:

1. If needed, seperate Data/Batch_1/Batch_1_IN_RV_1-1923.csv file into smaller files with corresponding Batch directories and scripts.
2. Ensure SED/SEDmc_batch_1.py references the correct input and output files (e.g., Data/Batch_1/Batch_1_IN_RV_1-1923.csv)
3. Ensure prog_flag = False in config.py. Otherwise, log files in Data/Logs will fill up with progress bar data
4. If no new host stars are being analyzed, then the Data/Baseline_NASA.csv file will have all the baseline data needed 
   for reproducing previous results.
5. From OS, run "python SEDmc/SEDmc_Batch_1.py" command from the Radius_Valley directory. 
6. Copy data from batch output files (e.g., Data/Batch_1/Batch_1_OUT_RV_1-1923.csv) to Sample file as described in step 5 of the README
   tab of that file.
7. If no other modifications are needed, then the steps 6 & 7 in the README tab of the Sample should not be needed and data will update 
   in Planet & Host-Filtered tab automatically.
8. Steps 8 & 9 in Sample file README tab may still be needed to confirm Planet & Host-Final tab contains original results. 

"""

# coding=utf-8
# Imports
# Import all the needed libraries

# Standard Python packages
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import math
from datetime import date, datetime
from multiprocessing import Pool
from contextlib import closing
from PIL import Image
from io import BytesIO
from http.client import HTTPConnection

# Special Python packages
import pickle
import emcee
import corner
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from astroquery.simbad import Simbad
from astroquery.gaia import Gaia
from astropy import units as u
from astropy.table import Table

#Local Python files
from config import *


# # Function to prompt user for input parameters
def prompt_input(err_str):
    sname = input('Enter Object Name (e.g., WASP95): ')
    if sname == "":
        print(err_str)
        sys.exit(0)                                   # If Object Name not entered, print error and exit
    # sname = sname.strip('\n')
    print(sname)
    rad = input('Enter RA (e.g., 313.783235, not required): ')
    position = (0,0)  ### Null Position
    if rad == "":
        sposition = False
    else:                                             # Only prompt for DEC if RA entered
        print(rad)
        dec = input('Enter DEC (e.g., -34.135745, not required): ')

        if dec == "":
            sposition = False
        else:
            position = (float('{:.7f}'.format(rad)), float('{:.7f}'.format(dec)))     # Set position SED() input parameter
            sposition = True
            print(dec)
    plx = input('Enter Parallax (default = GAIA value (if available), not required): ')
    if plx != "":
        plx = float(plx)                       # If GAIA doesn't return parallax, look up in SIMBAD and enter manually
    Teff_bmk =  input('Enter estimated Teff (default = GAIA DR2 value): ')
    if Teff_bmk == "":
        use_Teff_bmk = False   # Set flag to use SEDFit Teff
    else:
        Teff_bmk = int(Teff_bmk)
        use_Teff_bmk = True   # Set flag to use estimated Teff when known
    ang_dia = input('Enter estimated Angular Diameter (default = GAIA DR2 value): ')
    if ang_dia == "":
        use_ang_dia = False                 # Set flag to use SEDFit ang_dia
    else:
        ang_dia = float(ang_dia)
        use_ang_dia = True   # Set flag to use estimated ang_dia when known
    starmodel = input('Enter Stellar Model (default = nextgen, not required): ')
    if starmodel == "":                      # Enter any model supported by SED()
        smodel = False
    else:
        smodel = True
    # star_model = starmodel = starmodel.strip('\n')
    print(starmodel, smodel)
    # Enter EMCEE sampling parameters or accept defaults
    nwalkers = input('Enter Number of Walkers (default = 50, not required): ')
    if nwalkers == "":
        nwalkers = 50
    nwalkers = int(nwalkers)
    niter = input('Enter Number of Iterations (default = 10,000, not required): ')
    if niter == "":
        niter = 10000
    niter = int(niter)
    burn_in = input('Enter Number of Burn In Iterations (default = 500, not required): ')
    if burn_in == "":
        burn_in = 500
    burn_in = int(burn_in)
    use_stored = input('Use Stored Photometry Data? (default = no, not required): ')
    if use_stored == "":
        use_stored = False
    else:
        use_stored = True
    return sname, sposition, plx, Teff_bmk, use_Teff_bmk, ang_dia, use_ang_dia, smodel, nwalkers, niter, burn_in, \
           use_stored, starmodel, position


# # If "-p" not found this command line parameters expected
#  in this order-> required: Object(e.g., WASP94); optional: RA DEC Model
#  Can't use spaces in Object Name
def parse_arg(len_arg, err_str):
    position = (0,0)  ### Null Position
    star_model = "ck04"
    if len_arg > 1:
        sname = str(sys.argv[1])         # Object name is first argument (required)
        if len_arg > 2:
            plx = float(sys.argv[2])     # Parallax is 2nd argument (optional)
            if len_arg > 3:
                Teff_bmk = int(sys.argv[3])     # Teff for Benchmark Star is 3nd argument (optional)
                use_Teff_bmk = True
                if len_arg > 4:
                    ang_dia_bmk = float(sys.argv[4])     # Angular Diameter for Benchmark Star is 4th argument (optional)
                    use_ang_dia_bmk = True
                    if len_arg > 5:
                        star_model = starmodel = sys.argv[5]           # Stellar model is 5th argument (optional)
                        smodel = True
                        if len_arg > 6:
                            use_stored_flag = (sys.argv[6])    # Use Stored Data flag is 6th argument (optional)
                            print(use_stored_flag)
                            if use_stored_flag == "n":
                                use_stored = False
                            else:
                                use_stored = True
                            print(use_stored)
                            if len_arg > 9:      # Too many parameters, give error and exit
                                print(err_str)
                                sys.exit(0)
                            elif len_arg == 9:
                                position = (float(sys.argv[7]), float(sys.argv[8]))  # Position (RA & DEC are 7th & 8th argument (optional)
                                sposition = True
                                return sname, plx, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, \
                                       use_stored, star_model, position
                            elif len_arg == 8:   # Position incomplete, give error and exit
                                print(err_str)
                                sys.exit(0)
                            sposition = False      #   Only 6 args, no postiion
                            return sname, plx, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, \
                                   use_stored, star_model, position
                        else:   #  Only 5 arg, no stored flag
                            use_stored, sposition = False, False
                            return sname, plx, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, \
                                   use_stored, star_model, position
                    else:     #  Only 4 args, no star model
                        smodel, sposition, use_stored = False, False, False
                        return sname, plx, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, \
                               use_stored, star_model, position
                else:     # Only 3 arg, no ang_dia
                    ang_dia_bmk, smodel, sposition, use_ang_dia_bmk, use_stored = "", False, False, False, False
                    return sname, plx, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, use_stored, star_model, position
            else:    # Only 2 args, no Teff_bmk
                Teff_bmk, ang_dia_bmk, smodel, sposition, use_Teff_bmk, use_ang_dia_bmk, use_stored = "", "", False, False, False, False, False
                return sname, plx, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, use_stored, star_model, position
        else:    # Only 1 arg, no plx
            plx, Teff_bmk, ang_dia_bmk, smodel, sposition, use_Teff_bmk, use_ang_dia_bmk, use_stored = "", "", "", False, False, False, False, False
            return sname, plx, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, use_stored, star_model, position
    else:
        print(err_str)
        sys.exit(0)



def query_sed(pos, radius=1):
    """ Query VizieR Photometry
    The VizieR photometry tool extracts photometry points around a given position
    or object name from photometry-enabled catalogs in VizieR.

    Code copied from https://gist.github.com/mfouesneau/6caaae8651a926516a0ada4f85742c95

    The VizieR photometry tool is developed by Anne-Camille Simon and Thomas Boch
    .. url:: http://vizier.u-strasbg.fr/vizier/sed/doc/
    Parameters
    ----------
    pos: tuple or str
        position tuple or object name
    radius: float
        position matching in arseconds.
    Returns
    -------
    table: astropy.Table
        VO table returned by the Vizier service.

    >>> query_sed((1.286804, 67.840))
    >>> query_sed("HD1")
    """

    try:
        ra, dec = pos
        target = "{0:f},{1:f}".format(ra, dec)
    except:
        target = pos

    #url = "http:///viz-bin/sed?-c={target:s}&-c.rs={radius:f}"
    host = "vizier.u-strasbg.fr"
    port = 80
    viz_err = "None"
    while True:  # Added while, try, except loop to avoid errors at small radius
        viz_err = "None"            
        print('Current Radius = ', radius)
        try:
            path = "/viz-bin/sed?-c={target:s}&-c.rs={radius:f}".format(target=target, radius=radius)
            connection = HTTPConnection(host, port)
            connection.request("GET", path)
            response = connection.getresponse()
            table = Table.read(BytesIO(response.read()), format="votable")
        except Exception as viz_err: 
            print('VizierSED Error = ', viz_err)
            radius += 1
            if radius > 20:
                print('radius limit break')
                break
        else:
            print('clean break')
            break
    print('Vizier SED Radius (arcsec) = ', radius)
    print('Final VizierSED Error = ', viz_err)
    table_df = table.to_pandas()
    table_df['wl'] = 3e14 / (table_df['sed_freq'] * 1e9)   # convert sed_freq(Ghz) to wl(microns)
    table_df.to_csv('Data/Photometry/VizierSED/' + target + '_' + str(radius) + '.csv', index=False)
    obs_table = table_df.rename(columns={"_tabname": "src", "sed_flux": "fl", "sed_eflux": "efl", "sed_filter": "band"})
    return obs_table, viz_err


# Filter bands with known bad data
def filter_bands(obs_data):
    # Remove 2MASS data
    obs_2mass = obs_data[obs_data['band'].isin(['2massH.dat', '2massJ.dat', '2massK.dat'])]
    obs_data = obs_data.drop(obs_2mass.index)
    return obs_data


# Combine observed data and drop all duplicates
def remove_dups(obs_data):
    obs_data = obs_data.round(6)
    obs_data = obs_data.sort_values(by=['wl', 'efl'])
    obs_data = obs_data.drop_duplicates(subset=['wl'], keep='first')
    obs_data = obs_data.reset_index(drop=True)
    return obs_data


# Limit wavelength to specified range
def filter_wl(obs_data, wl_min, wl_max):
    obs_data_range = obs_data[(wl_min <= obs_data.wl) & (obs_data.wl <= wl_max)]
    obs_data_range = obs_data_range.reset_index(drop=True)
    return obs_data_range


def Get_source_id(object_ID):
    result_table = Simbad.query_objectids(object_ID)
    src_ID_name_3 = src_ID_3 = src_ID_name_2 = src_ID_2 ='NaN'
    for x in result_table:
        if 'Gaia EDR3' in x['ID']:
            src_ID_name_3 = (x['ID'])
            print(src_ID_name_3)
            src_ID_3 = x['ID'].replace('Gaia EDR3 ','')
        if 'Gaia DR2' in x['ID']:
            src_ID_name_2 = (x['ID'])
            print(src_ID_name_2)
            src_ID_2 = x['ID'].replace('Gaia DR2 ','')
    return src_ID_name_3, src_ID_3, src_ID_name_2, src_ID_2


def Get_Simbad_data(object_ID):
    custom_Simbad = Simbad()
    custom_Simbad.add_votable_fields('ra(d)', 'dec(d)', 'plx', 'plx_error', 'flux(U)', 'flux_error(U)', 'flux(B)',
                                     'flux_error(B)', 'flux(V)', 'flux_error(V)', 'flux(R)', 'flux_error(R)', 'flux(G)',
                                     'flux_error(G)', 'flux(I)', 'flux_error(I)', 'flux(J)', 'flux_error(J)', 'flux(H)',
                                     'flux_error(H)', 'flux(K)', 'flux_error(K)',
                                     'diameter', 'distance')
    object_table = custom_Simbad.query_object(object_ID)
    store_all['RA_S'] = RA = object_table['RA_d'][0]
    store_all['DEC_S'] = DEC = object_table['DEC_d'][0]
    store_all['PLX_S'] = plx_simbad = object_table['PLX_VALUE'][0]
    store_all['PLX_ERR_S'] = plx_err_simbad = object_table['PLX_ERROR'][0]
    store_all['FLUX_U_S'] = (object_table['FLUX_U'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_U_S'] = (object_table['FLUX_ERROR_U'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_B_S'] = (object_table['FLUX_B'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_B_S'] = (object_table['FLUX_ERROR_B'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_V_S'] = (object_table['FLUX_V'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_V_S'] = (object_table['FLUX_ERROR_V'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_R_S'] = (object_table['FLUX_R'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_R_S'] = (object_table['FLUX_ERROR_R'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_G_S'] = (object_table['FLUX_G'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_G_S'] = (object_table['FLUX_ERROR_G'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_I_S'] = (object_table['FLUX_I'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_I_S'] = (object_table['FLUX_ERROR_I'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_J_S'] = (object_table['FLUX_J'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_J_S'] = (object_table['FLUX_ERROR_J'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_H_S'] = (object_table['FLUX_H'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_H_S'] = (object_table['FLUX_ERROR_H'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_K_S'] = (object_table['FLUX_K'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['FLUX_ERR_K_S'] = (object_table['FLUX_ERROR_K'][0] * u.ABmag).to(u.erg/u.s/u.cm**2/u.Hz) * 1e23
    store_all['DIA_S'] = dia_simbad = object_table['Diameter_diameter'][0]
    store_all['DIA_UNIT_S'] = dia_unit_simbad = object_table['Diameter_unit'][0]
    store_all['DIST_S'] = dist_simbad = object_table['Distance_distance'][0]
    store_all['DIST_UNIT_S'] = dist_unit_simbad = object_table['Distance_unit'][0]
    return RA, DEC, plx_simbad, plx_err_simbad


def Get_Gaia_data(source_ID, release):
    if release == 'dr2':
        columns = 'source_id, ra, dec, parallax, parallax_error, teff_val, teff_percentile_lower, teff_percentile_upper,' \
                  'radius_val, radius_percentile_lower, radius_percentile_upper, lum_val, lum_percentile_lower,' \
                  ' lum_percentile_upper'
    else:
        columns = 'source_id, ra, dec, parallax, parallax_error'
    query_base = """SELECT 
    TOP 10
    {columns}
    FROM gaia{release}.gaia_source
    WHERE source_id = {source_ID}
    """
    query = query_base.format(columns=columns, source_ID=source_ID, release=release)
    job = Gaia.launch_job_async(query)
    results = job.get_results()
    i = 0
    for x in results:
        i += 1
    print("i =", i)
    if i == 1:
        if release == 'edr3':
            store_all['RA_edr3'] = ra = results['ra'][0]
            store_all['DEC_edr3'] = dec = results['dec'][0]
            store_all['PLX_edr3'] = plx = results['parallax'][0]
            store_all['PLX_ERR_edr3'] = plx_err = results['parallax_error'][0]
        if release == 'dr3':
            store_all['RA_dr3'] = ra = results['ra'][0]
            store_all['DEC_dr3'] = dec = results['dec'][0]
            store_all['PLX_dr3'] = plx = results['parallax'][0]
            store_all['PLX_ERR_dr3'] = plx_err = results['parallax_error'][0]
        if release == 'dr2':
            store_all['RA_dr2'] = ra = results['ra'][0]
            store_all['DEC_dr2'] = dec = results['dec'][0]
            store_all['PLX_dr2'] = plx = results['parallax'][0]
            store_all['PLX_ERR_dr2'] = plx_err = results['parallax_error'][0]
            store_all['TEFF_dr2'] = Teff = results['teff_val'][0]
            store_all['TEFF_NEG_dr2'] = Teff_neg = results['teff_percentile_lower'][0]
            store_all['TEFF_POS_dr2'] = Teff_pos = results['teff_percentile_upper'][0]
            store_all['RSTAR_dr2'] = Rstar = results['radius_val'][0]
            store_all['RSTAR_NEG_dr2'] = Rstar_neg = results['radius_percentile_lower'][0]
            store_all['RSTAR_POS_dr2'] = Rstar_pos = results['radius_percentile_lower'][0]
            store_all['LSTAR_dr2'] = Lstar = results['lum_val'][0]
            store_all['LSTAR_NEG_dr2'] = Lstar_neg = results['lum_percentile_lower'][0]
            store_all['LSTAR_POS_dr2'] = Lstar_pos = results['lum_percentile_lower'][0]
        else:
            Teff = Teff_neg = Teff_pos = 'NaN'
    else:
        ra = dec = plx = plx_err = Teff = Teff_neg = Teff_pos ='NaN'
    return ra, dec, plx, plx_err, Teff, Teff_neg, Teff_pos


def get_VO_Data(source_name):
    # Keep a running sum weighted average numerator (sum plx * 1/ plx_err**2) and reciprocal of plx_err**2
    plx_wav_sum_num = plx = 0    # Initial value of Numerator
    plx_err_wav_sum = plx_err = 0    # Initial value of Reciprocal of plx_err**2
    store_all['RSTAR_dr2'] ='NaN'
    store_data = pd.DataFrame([])
    try:
        RA, DEC, plx_simbad, plx_err_simbad = Get_Simbad_data(source_name)
    except:
        print("Simbad Error")
    else:
        print("Simbad", RA, DEC, plx_simbad, plx_err_simbad)
        if isinstance(plx_simbad, float): 
            plx_data.loc['Simbad'] = [plx_simbad, plx_err_simbad, plx_err_simbad / plx_simbad]
        plx_wav_sum_num = plx_wav_sum_num + plx_simbad * (1 / plx_err_simbad ** 2)  # Add Simbad plx to numerator
        plx_err_wav_sum = plx_err_wav_sum + (1 / plx_err_simbad ** 2)  # Add Simbad plx_err to reciprocal of plx_err**2
#    finally:
        src_ID_name_3, src_ID_3, src_ID_name_2, src_ID_2 = Get_source_id(source_name)
        # ra = "NaN"
        if src_ID_3 != "NaN":
            # Get data from GAIA DR3 VO tables
            release = 'dr3'
            store_all['SOURCE_ID_3'] = src_ID_name_3
            print(src_ID_3)
            ra, dec, plx, plx_err, Teff, Teff_neg, Teff_pos = Get_Gaia_data(src_ID_3, release)
            print("GAIA DR3", ra, dec, plx, plx_err, Teff, Teff_neg, Teff_pos)
            if isinstance(plx, float): 
                plx_data.loc['GAIA DR3'] = [plx, plx_err, plx_err / plx]
            if plx != 0:
                plx_wav_sum_num = plx_wav_sum_num + plx * (1 / plx_err ** 2)   # Add dr3 plx to numerator
                plx_err_wav_sum = plx_err_wav_sum + (1 / plx_err ** 2)     # Add dr3 plx_err to reciprocal of plx_err**2
            # Get data from GAIA EDR3 VO tables
            release = 'edr3'
            ra, dec, plx, plx_err, Teff, Teff_neg, Teff_pos = Get_Gaia_data(src_ID_3, release)
            print("GAIA EDR3", ra, dec, plx, plx_err, Teff, Teff_neg, Teff_pos)
            if isinstance(plx, float): 
                plx_data.loc['GAIA EDR3'] = [plx, plx_err, plx_err / plx]
            if plx != 0:
                plx_wav_sum_num = plx_wav_sum_num + plx * (1 / plx_err ** 2)   # Add edr3 plx to numerator
                plx_err_wav_sum = plx_err_wav_sum + (1 / plx_err ** 2)     # Add edr3 plx_err to reciprocal of plx_err**2
        if src_ID_2 != "NaN":
            # Get data from GAIA DR2 VO tables
            release = 'dr2'
            store_all['SOURCE_ID_2'] = src_ID_name_2
            print(src_ID_2)
            ra, dec, plx, plx_err, Teff, Teff_neg, Teff_pos = Get_Gaia_data(src_ID_2, release)
            print("GAIA DR2", ra, dec, plx, plx_err, Teff, Teff_neg, Teff_pos)
            if isinstance(plx, float): 
                plx_data.loc['GAIA DR2'] = [plx, plx_err, plx_err / plx]
            if plx != 0:
                plx_wav_sum_num = plx_wav_sum_num + plx * (1 / plx_err ** 2)   # Add dr2 plx to numerator
                plx_err_wav_sum = plx_err_wav_sum + (1 / plx_err ** 2)     # Add dr2 plx_err to reciprocal of plx_err**2
        store_all['PLX_WAVG'] = plx = plx_wav_sum_num / plx_err_wav_sum
        store_all['PLX_ERR_WAVG'] = plx_err = 1 / np.sqrt(plx_err_wav_sum)
        store_data = store_data.append(store_all)
        store_data.to_csv('Data/GAIA_data.csv', index=False)

    return RA, DEC, plx, plx_err


# Clean up data until min number of fit points found
def get_clean_data(observed_data, fit_curve, fit_err_init, fit_pts_min):
    fit_err = fit_err_init
    fit_pts = 0
    long_wl = False
    while fit_pts < fit_pts_min or not long_wl:

        # Clean up observed data not near fit curve
        fit_data = []
        for i in range(len(observed_data)):
            index = np.argmin(np.abs(fit_curve.waves - observed_data.wl[i]))  # find index where fit wl = obs wl
            fit_data.append(fit_curve.fluxes[index])  # get fit flux at obs wl

        comp_data = observed_data
        comp_data['fit'] = pd.Series(fit_data, index=comp_data.index)  # append fit flux column
        comp_data['abs_dif'] = abs((comp_data['fl'] - comp_data['fit'])/comp_data['fl'])  # append abs % diff column
        comp_data['pct_dif'] = (comp_data['fl'] - comp_data['fit'])/comp_data['fl']  # append % diff column
        good_data = comp_data[comp_data.abs_dif < fit_err]  # good data = dif less than fit error
        bad_data = comp_data[comp_data.abs_dif > fit_err]  # bad data = dif greater than fit error
        fit_pts = len(good_data)
        fit_err = fit_err + 0.01
        fit_qual = good_data['abs_dif'].sum()/len(good_data)
        long_wl = (good_data['wl'] > 2).any()        
    print("fit_pts ", fit_pts)
    print("fit_err ", fit_err)
    print("fit_qual ", fit_qual)
    return good_data, bad_data, fit_pts, fit_err, fit_qual



# Use Stored Photometry Data
def get_stored_data(fit_err_init, fit_pts_min):
    good_data = pd.read_csv('Data/Photometry/' + starmodel + '/' + sname + '_good_data.csv')
    bad_data = pd.read_csv('Data/Photometry/' + starmodel + '/' + sname + '_bad_data.csv')
    fit_pts = len(good_data)
    bad_cnt = len(bad_data)
    fit_err = fit_err_init + (fit_pts - fit_pts_min)*0.01
    # fit_qual = good_data['abs_dif'].sum()/len(good_data)
    # fit_qual = good_data['qual_factor'].sum()/len(good_data)
    fit_qual = -1
    return good_data, bad_data, fit_pts, fit_err, fit_qual, bad_cnt


def plot_obs(itr, input_data, gx, gy, bx, by):
    fig2 = plt.figure("Observed  " + str(itr), figsize=(8,6), dpi=100)
    ax2 = fig2.add_subplot(111)
    ax2.grid(True, lw=0.2)
    ax2.set_title(label=source_name + " - " + str(itr))
    ax2.set_xlabel(r"$\lambda$ $[\mu m]$", fontsize=15)
    ax2.set_ylabel(r"$F_\nu$ $[Jy]$", fontsize=15)
    # Plot observed data
    # input_data_range = input_data[(wl_min <= input_data.wl) & (input_data.wl <= wl_max)]
    # Plot good observed data
    ax2.loglog(gx,gy, 'ob', ms=3)
    # Plot bad observed data
    ax2.loglog(bx,by, 'xr', ms=6)
    # Plot SED_EMCEE Best fit curve
    ax2.plot(fit_star.waves, fit_star.fluxes, 'b-', linewidth=0.5, alpha=0.8)
    # Plot SEDfit curve
    # ax2.plot(s.star.waves, s.star.fluxes, 'k-', linewidth=0.3, alpha=0.8)
    # Plot Benchmark Star best fit curve
    ax2.plot(bl_star.waves, bl_star.fluxes, 'g-', linewidth=0.5, alpha=0.8)
    # Set x & y limits to plot
    ymin = 0.3*np.min(np.abs(input_data.fl))
    ymax = 7.0*np.max(input_data.fl)
    ax2.set_xlim(0.2, 500.0)
    ax2.set_ylim(ymin=ymin, ymax=ymax)
    ax2.set_autoscale_on(False)

# Add labels to Observed Data
    pt_i = -1
    for x,y in zip(good_data.wl, good_data.fl):
        pt_i += 1
        x_off = -3
        y_off = 2
        ha_value = "left"
        # label = "({0:.2f},{1:.2f})".format(x,y)
        # if pt_i in bad_data_idx:
        plt.annotate(pt_i,  # this is the text
                     (x, y),  # this is the point to label
                     color='black', fontsize=6,  # set fontsize
                     textcoords="offset points",  # how to position the text
                     xytext=(x_off+0, y_off+0),  # distance from text to points (x,y)
                     ha=ha_value)  # horizontal alignment can be left, right or center
        # else:
    pt_i = -1
    for x,y in zip(bad_data.wl, bad_data.fl):
        pt_i += 1
        x_off = -3
        y_off = 2
        ha_value = "left"
        plt.annotate(pt_i,  # this is the text
                     (x, y),  # this is the point to label
                     color='red', fontsize=6,  # set fontsize
                     textcoords="offset points",  # how to position the text
                     xytext=(x_off+0, y_off+0),  # distance from text to points (x,y)
                     ha=ha_value)  # horizontal alignment can be left, right or center

    # Annotate
    # anno_text = r'$T_{SED}$ = %.0f' % (sfit_tstar)
    # anno_text += '\n' + r'$apprad_{SED}$ = %.5f' % (s.sfit_apprad)
    anno_text = '\n' + r'$T_{EMCEE}$ = %.0f' % (theta_max[0])
    anno_text += '\n' + r'$apprad_{EMCEE}$ = %.5f' % (np.sqrt(theta_max[1]))
    anno_text += '\n' + r'$T_{bmk}$ = %.0f' % (Teff_bmk)
    anno_text += '\n' + r'$angdia_{bmk}$ = %.3f' % (ang_dia_bmk)
    ax2.text(0.3, 0.01, anno_text, bbox=dict(facecolor='w', alpha=0.2), fontsize=8, linespacing=1.0, \
             horizontalalignment='left', verticalalignment='bottom', transform=ax2.transAxes)
    # Show Figure and save to file
    # plt.gcf().set_size_inches(*fig_size)  # Needed to ensure figure size remains large
    fig2.savefig('Data/Figures/' + source_name + '_Observed_' + str(itr))
    plt.close()


# Create Table of Observed data
def plot_obs_table(itr):
    fig_table = plt.figure("Observed Table" + str(itr), figsize=(8, 6), dpi=100)
    # Hide axes
    ax = plt.gca()
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    # Hide axes border
    plt.box(on=None)
    table1_data = good_data[['wl', 'fl', 'efl', 'src', 'band']]
    table1_data.update(table1_data[['wl', 'fl', 'efl']].applymap('{:,.2f}'.format))
    table1 = plt.table(cellText=table1_data.values, cellLoc='center',
                       colWidths=[0.09, 0.08, 0.09, 0.23, 0.16],
                       colLabels=table1_data.columns,
                       rowLabels=table1_data.index,
                       loc='upper left')
    table1.auto_set_font_size(False)
    table1.set_fontsize(6)
    table1.scale(.7, 1)
    if len(bad_data) != 0:
        table2_data = bad_data[['wl', 'fl', 'efl', 'src', 'band']]
        table2_data.update(table2_data[['wl', 'fl', 'efl']].applymap('{:,.2f}'.format))
        rcolor=plt.cm.Reds(0.4)
        table2 = plt.table(cellText=table2_data.values, cellLoc='center',
                           colWidths=[0.09, 0.08, 0.09, 0.23, 0.16],
                           colLabels=table2_data.columns,
                           rowLabels=table2_data.index, rowColours=[rcolor] * len(bad_data),
                           loc='upper right')
        table2.auto_set_font_size(False)
        table2.set_fontsize(6)
        table2.scale(.7, 1)
    # Show Figure and save to file
    # plt.gcf().set_size_inches(*fig_size)  # Needed to ensure figure size remains large
    fig_table.savefig('Data/Figures/' + source_name + '_Observed_Table' + str(itr))
    # plt.close()


# Plot SEDfit best fit curve and observed data on LogLog Axis
def plot_SEDfit_obs(gx, gy, bx, by):
    fig2 = plt.figure("SEDfit", figsize=(8, 6), dpi=100)
    ax2 = fig2.add_subplot(111)
    ax2.grid(True, lw=0.2)
    ax2.set_title(label=source_name)
    ax2.set_xlabel(r"$\lambda$ $[\mu m]$", fontsize=15)
    ax2.set_ylabel(r"$F_\nu$ $[Jy]$", fontsize=15)
    # Plot good observed data
    ax2.loglog(gx,gy, 'ob', ms=3)
    # Plot bad observed data
    ax2.loglog(bx,by, 'xr', ms=6)
    # Plot SEDfit curve
    # ax2.plot(SED_fit.waves, SED_fit.fluxes, 'k-', linewidth=0.3, alpha=0.8)
    # Annotate
    # anno_text = r'$T_{star}$ = %.0f' % (sfit_tstar)
    # anno_text += '\n' + r'$apprad$ = %.5f' % (s.sfit_apprad)
    anno_text = '\n' + r'$Fit Points$ = %.0f' % (fit_pts)
    anno_text += '\n' + r'$Fit Error$ = %.3f' % (fit_err)
    ax2.text(0.99, 0.99, anno_text, bbox=dict(facecolor='w', alpha=0.2), linespacing=1.0, \
             horizontalalignment='right', verticalalignment='top', transform=ax2.transAxes)
    plt.gcf().set_size_inches(*fig_size)  # Needed to ensure figure size remains large
    fig2.savefig('Data/Figures/' + source_name + '_Observed')
    # plt.close()


# Plot SED_EMCEE Best Fit curve and Observed Data on LogLog Axis
def plot_SED_EMCEE_obs(gx, gy, bx, by, itr):
    fig3 = plt.figure("SEDmc" + str(itr), figsize=(8, 6), dpi=100)
    ax3 = fig3.add_subplot(111)
    ax3.grid(True, lw=0.2)
    ax3.set_title(label=source_name + " - " + str(itr))
    ax3.set_xlabel(r"$\lambda$ $[\mu m]$", fontsize=15)
    ax3.set_ylabel(r"$F_\nu$ $[Jy]$", fontsize=15)
    # Plot good observed data
    ax3.loglog(gx, gy, 'og', ms=5)
    # Plot bad observed data
    ax3.loglog(bx, by, 'xr', ms=8)
    # Plot SED_EMCEE Best fit curve
    ax3.plot(fit_star.waves, fit_star.fluxes, 'b-', linewidth=0.5, alpha=0.8)
    # Plot Benchmark Star best fit curve
    ax3.plot(bl_star.waves, bl_star.fluxes, 'k-', linewidth=0.5, alpha=0.8)
    # ... and set X and Y limits
    ymin = 0.3*np.min(np.abs(obs_data.fl))
    ymax = 7.0*np.max(obs_data.fl)
    ax3.set_xlim(0.2, 500.0)
    ax3.set_ylim(ymin=ymin, ymax=ymax)
    ax3.set_autoscale_on(False)
    # Annotate
    anno_text = ' Max Likelihood '
    anno_text += '\n' + r'$T_{eff}$ = %.4g' % (theta_max[0])
    anno_text += '\n' + r'$Radius$ = %.3g' % (theta_max[1])
    anno_text += '\n\n' + ' Fit Parameters'
    anno_text += '\n' + r'$Fit Points$ = %.0f' % (fit_pts)
    anno_text += '\n' + r'$Fit Error$ = %.3f' % (fit_err)
    anno_text += '\n' + r'$Fit Quality$ = %.3f' % (fit_qual)
    ax3.text(0.78, 0.99, anno_text, bbox=dict(facecolor='w', alpha=0.2), linespacing=1.0, \
             horizontalalignment='left', verticalalignment='top', transform=ax3.transAxes)
    fig3.savefig('Data/Figures/' + source_name + '_fit-' + str(itr))
    plt.close()


# View Sampler Behavior
def plot_chain(itr):
    # Look at sampler chain plots to see sampler behavior.
    fig, axes = plt.subplots(2, figsize=(10, 7), sharex=True)
    samples = sampler.get_chain()
    labels = ["Teff", "Radius"]
    for i in range(ndim):
        ax = axes[i]
        ax.plot(samples[:, :, i], "k", alpha=0.3)
        ax.set_xlim(0, len(samples))
        ax.set_ylabel(labels[i])
        ax.yaxis.set_label_coords(-0.1, 0.5)
    axes[-1].set_xlabel("step number");
    plt.savefig('Data/Figures/' + source_name + '_chain-' + str(itr))
    plt.close()


# # Corner Plot
def plot_corner(itr):
    # Show Posterior distribution spread in corner plot for temp index and scale values
    labels = ['Teff', 'Radius']
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig = corner.corner(samples, show_titles=False, labels=labels, plot_datapoints=True, quantiles=[0.16, 0.5, 0.84],
                        fig=fig)
    # Disabled titles in corner plot since labels didn't change with quantiles. Plotted manual titles below.
    for i in range(ndim):
        mcmc = np.percentile(samples[:, i], [16, 50, 84])
        q = np.diff(mcmc)
        if i == 0:
            txt = "$\mathrm{{{3}}} = {0:.4g}_{{-{1:.3g}}}^{{+{2:.3g}}}$"
            txt = txt.format(mcmc[1], q[0], q[1], labels[i])
            fig.text(.23, .94, txt, fontsize=12, transform=plt.gcf().transFigure)
        if i == 1:
            txt = "$\mathrm{{{3}}} = {0:.3g}_{{-{1:.3g}}}^{{+{2:.3g}}}$"
            txt = txt.format(mcmc[1], q[0], q[1], labels[i])
            fig.text(.6, .56, txt, fontsize=12, transform=plt.gcf().transFigure)
    plt.savefig('Data/Figures/' + source_name + '_corner-' + str(itr))
    plt.close()
    return labels


# # Best Fit Value Summary
def print_summary(plx, plx_err):
    # Find the best fit values of theta where probability (lnlike) is maximum value
    print("Theta max: ", theta_max)
    print("Teff =", teff_med, teff_u_plus, teff_pct_u)              # Show Teff which is temp value at index (integer)
    print("scale =", scale_med)             # Show scale value
    print("apprad =", apprad_med)   # Show apprad which is square root of scale
    #apprad = np.sqrt(theta_max[1])
    # Rstar, plx, plx_err = get_Rstar(plx, apprad)         # Get Rstar and final parallax value
    print("Rstar = ", Rstar_med, Rstar_u_plus, Rstar_pct_u)
    print("Parallax =", plx, plx_err)
    print("Fit Points = ", fit_pts)
    print("Fit Error = ", fit_err)
    print("Autocorrelation Time = ", tau)
    store_all['Good Fit Points'] = fit_pts
    store_all['Bad Points'] = bad_cnt
    store_all['Fit Error'] = fit_err
    store_all['Fit Quality'] = fit_qual
    store_all['WL_min'] = wl_min
    store_all['WL_max'] = wl_max
    return


# Calculate Uncertainties & Plot
def plot_sigmas(itr):
    # Show 2 sigma uncertainties for all parameters
    labels = ['Teff', 'Radius']
    plt.figure(figsize=(2.2, 1.6))
    plt.annotate('     Median Values', xy=(0.05, 0.9), fontsize=9)
    for i in range(ndim):
        mcmc = np.percentile(samples[:, i], [16, 50, 84])
        q = np.diff(mcmc)
        if i == 0:
            txt = "$\mathrm{{{3}}} = {0:.4g}_{{-{1:.3g}}}^{{+{2:.3g}}}$"
            txt = txt.format(mcmc[1], q[0], q[1], labels[i])
            plt.annotate(txt, xy=(0.05, 0.70), fontsize=9)
            teff_med = store_all[labels[i]] = int(mcmc[1])
            teff_u_neg = store_all['u-(' + labels[i] + ')'] = int(q[0])
            teff_u_plus = store_all['u+(' + labels[i] + ')'] = int(q[1])
            teff_pct_u = store_all['u%(' + labels[i] + ')'] = round((100 * teff_u_plus / teff_med), 1)
            if Teff_bl == 'NaN':
                teff_med_pct_bl = store_all['Teff_delta_bl'] = 'NaN'
            else:
                teff_med_pct_bl = store_all['Teff_delta_bl'] = round((100 * (teff_med - Teff_bl) / Teff_bl), 1)
        if i == 1:
            # Plot and store radius with uncertainties
            txt = "$\mathrm{{{3}}} = {0:.3g}_{{-{1:.3g}}}^{{+{2:.3g}}}$"
            txt = txt.format(mcmc[1], q[0], q[1], labels[i])
            Rstar_med = store_all[labels[i]] = float('{:.3g}'.format(mcmc[1]))
            Rstar_u_neg = store_all['u-(' + labels[i] + ')'] = float('{:.3g}'.format(q[0]))
            Rstar_u_plus = store_all['u+(' + labels[i] + ')'] = float('{:.3g}'.format(q[1]))
            Rstar_pct_u = store_all['u%(' + labels[i] + ')'] = round((100 * Rstar_u_plus / Rstar_med), 1)
            if Rstar_bl == 'NaN':
                Rstar_pct_bl = store_all['Radius_delta_bl'] = 'NaN'
            else:
                Rstar_pct_bl = store_all['Radius_delta_bl'] = round((100 * (Rstar_med - Rstar_bl) / Rstar_bl), 1)
            plt.annotate(txt, xy=(0.05, 0.5), fontsize=9)
            # Derive, plot & store scale value from radius
            scale_med = store_all['scale'] = float('{:.3g}'.format((Rstar_med * plx_mc / 1000)**2))
            scale_u_neg = store_all['u-(scale)'] = float('{:.3g}'.format((np.sqrt(2 * (Rstar_u_neg / Rstar_med)**2
                                                          + 2 * (plx_mc_err / plx_mc)**2))))
            scale_u_plus = store_all['u+(scale)'] = float('{:.3g}'.format((np.sqrt(2 * (Rstar_u_plus / Rstar_med)**2
                                                           + 2 * (plx_mc_err / plx_mc)**2))))
            txt = "$\mathrm{{{3}}} = {0:.3g}_{{-{1:.3g}}}^{{+{2:.3g}}}$"
            txt = txt.format(scale_med, scale_u_neg, scale_u_plus, 'scale')
            #plt.annotate(txt, xy=(0.05, 0.05), fontsize=9)
            # Derive, plot and store apparent radius (arcsec) with uncertainties
            apprad_med = store_all['apprad'] = float('{:.3g}'.format(np.sqrt(scale_med)))
            apprad_u_neg = store_all['u-(apprad)'] = float('{:.3g}'.format(.5 * scale_u_neg / np.sqrt(scale_med)))
            apprad_u_plus = store_all['u+(apprad)'] = float('{:.3g}'.format(.5 * scale_u_plus / np.sqrt(scale_med)))
            txt = "$\mathrm{{{3}}} = {0:.3g}_{{-{1:.3g}}}^{{+{2:.3g}}}$"
            txt = txt.format(apprad_med, apprad_u_neg, apprad_u_plus, 'apprad')
            #plt.annotate(txt, xy=(0.05, 0.39), fontsize=9)
            # Derive, plot and store angular diameter (arcsec) with uncertianties
            ang_dia_emc = store_all['angdia'] = float('{:.3g}'.format(4.65047 * 2 / 1000 * Rstar_med * plx_mc))
            ang_dia_emc_u_neg = store_all['u-(angdia)'] = float('{:.2g}'.format(4.65047 * 2 /1000 * np.sqrt((Rstar_med * plx_mc_err)**2 + (plx_mc * Rstar_u_neg)**2)))
            ang_dia_emc_u_plus = store_all['u+(angdia)'] = float('{:.2g}'.format(4.65047 * 2 / 1000 * np.sqrt((Rstar_med * plx_mc_err)**2 + (plx_mc * Rstar_u_plus)**2)))
            ang_dia_emc_pct_u = store_all['u%(angdia)'] = round((100 * ang_dia_emc_u_plus / ang_dia_emc), 1)
            if ang_dia_bl == 'NaN':
                ang_dia_emc_pct_bl = store_all['angdia_delta_bl'] = 'NaN'
            else:
                ang_dia_emc_pct_bl = store_all['angdia_delta_bl'] = round(
                (100 * (ang_dia_emc - ang_dia_bl) / ang_dia_bl), 1)
            txt = "$\mathrm{{{3}}} = {0:.3g}_{{-{1:.3g}}}^{{+{2:.3g}}}$"
            txt = txt.format(ang_dia_emc, ang_dia_emc_u_neg, ang_dia_emc_u_plus, 'ang dia')
            plt.annotate(txt, xy=(0.05, 0.3), fontsize=9)

    plt.xticks([])
    plt.yticks([])
    # plt.gcf().set_size_inches(3, 1.5)
    plt.savefig('Data/Figures/' + source_name + '_2sigma-' + str(itr))
    plt.close()
    return teff_med, teff_u_neg, teff_u_plus, teff_med_pct_bl, scale_med, scale_u_neg, scale_u_plus, \
           apprad_med, apprad_u_neg, apprad_u_plus, ang_dia_emc, ang_dia_emc_u_neg, ang_dia_emc_u_plus, \
           ang_dia_emc_pct_bl, Rstar_med, Rstar_u_neg, Rstar_u_plus, Rstar_bl, Rstar_pct_bl, ang_dia_emc_pct_u, teff_pct_u, Rstar_pct_u


def create_table(table_data, title='', data_size=8, title_size=9, align_data='L', align_header='C', cell_width='even',
                 x_start='x_default', emphasize_data=[], emphasize_style=None, emphasize_color=(0, 0, 0)):
    """
    Source of function = https://github.com/bvalgard/create-pdf-with-python-fpdf2
    table_data:
                list of lists with first element being list of headers
    title:
                (Optional) title of table (optional)
    data_size:
                the font size of table data
    title_size:
                the font size fo the title of the table
    align_data:
                align table data
                L = left align
                C = center align
                R = right align
    align_header:
                align table data
                L = left align
                C = center align
                R = right align
    cell_width:
                even: evenly distribute cell/column width
                uneven: base cell size on lenght of cell/column items
                int: int value for width of each cell/column
                list of ints: list equal to number of columns with the widht of each cell / column
    x_start:
                where the left edge of table should start
    emphasize_data:
                which data elements are to be emphasized - pass as list
                emphasize_style: the font style you want emphaized data to take
                emphasize_color: emphasize color (if other than black)

    """
    default_style = pdf.font_style
    if emphasize_style == None:
        emphasize_style = default_style

    # Get Width of Columns
    def get_col_widths():
        col_width = cell_width
        if col_width == 'even':
            col_width = pdf.epw / len(data[
                                          0]) - 1  # distribute content evenly   # epw = effective page width
            # (width of page not including margins)
        elif col_width == 'uneven':
            col_widths = []

            # searching through columns for largest sized cell (not rows but cols)
            for col in range(len(table_data[0])):  # for every row
                longest = 0
                for row in range(len(table_data)):
                    cell_value = str(table_data[row][col])
                    value_length = pdf.get_string_width(cell_value)
                    if value_length > longest:
                        longest = value_length
                col_widths.append(longest + 4)  # add 4 for padding
            col_width = col_widths

            # ## compare columns

        elif isinstance(cell_width, list):
            col_width = cell_width  # TODO: convert all items in list to int
        else:
            # TODO: Add try catch
            col_width = int(col_width)
        return col_width

    # Convert dict to lol
    if isinstance(table_data, dict):
        header = [key for key in table_data]
        data = []
        for key in table_data:
            value = table_data[key]
            data.append(value)
        # need to zip so data is in correct format (first, second, third --> not first, first, first)
        data = [list(a) for a in zip(*data)]

    else:
        header = table_data[0]
        data = table_data[1:]

    line_height = pdf.font_size * 1.3

    col_width = get_col_widths()
    pdf.set_font(size=title_size)

    # Get starting position of x
    # Determine width of table to get x starting point for centred table
    if x_start == 'C':
        table_width = 0
        if isinstance(col_width, list):
            for width in col_width:
                table_width += width
        else:  # need to multiply cell width by number of cells to get table width
            table_width = col_width * len(table_data[0])
        # Get x start by subtracting table width from pdf width and divide by 2 (margins)
        margin_width = pdf.w - table_width
        # TODO: Check if table_width is larger than pdf width

        center_table = margin_width / 2  # only want width of left margin not both
        x_start = center_table
        pdf.set_x(x_start)
    elif isinstance(x_start, int):
        pdf.set_x(x_start)
    elif x_start == 'x_default':
        x_start = pdf.set_x(pdf.l_margin)

    # TABLE CREATION #

    # add title
    if title != '':
        pdf.multi_cell(0, line_height, title, border=0, align='j', new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=pdf.font_size)
        pdf.ln(line_height)  # move cursor back to the left margin

    pdf.set_font(size=data_size)
    # add header
    y1 = pdf.get_y()
    if x_start:
        x_left = x_start
    else:
        x_left = pdf.get_x()
    x_right = pdf.epw + x_left
    if not isinstance(col_width, list):
        if x_start:
            pdf.set_x(x_start)
        for datum in header:
            pdf.multi_cell(col_width, line_height, datum, border=0, align=align_header,
                           new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=pdf.font_size)
            x_right = pdf.get_x()
        pdf.ln(line_height)  # move cursor back to the left margin
        y2 = pdf.get_y()
        pdf.line(x_left, y1, x_right, y1)
        pdf.line(x_left, y2, x_right, y2)

        for row in data:
            if x_start:  # not sure if I need this
                pdf.set_x(x_start)
            for datum in row:
                if datum in emphasize_data:
                    pdf.set_text_color(*emphasize_color)
                    pdf.set_font(style=emphasize_style)
                    pdf.multi_cell(col_width, line_height, datum, border=0, align=align_data,
                                   new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=pdf.font_size)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font(style=default_style)
                else:
                    pdf.multi_cell(col_width, line_height, datum, border=0, align=align_data,
                                   new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=pdf.font_size)  # ln = 3 - move cursor to right with same vertical offset # this uses an object named pdf
            pdf.ln(line_height)  # move cursor back to the left margin

    else:
        if x_start:
            pdf.set_x(x_start)
        for i in range(len(header)):
            datum = header[i]
            pdf.multi_cell(col_width[i], line_height, datum, border=0, align=align_header,
                           new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=pdf.font_size)
            x_right = pdf.get_x()
        pdf.ln(line_height)  # move cursor back to the left margin
        y2 = pdf.get_y()
        pdf.line(x_left, y1, x_right, y1)
        pdf.line(x_left, y2, x_right, y2)

        for i in range(len(data)):
            if x_start:
                pdf.set_x(x_start)
            row = data[i]
            for i in range(len(row)):
                datum = row[i]
                if not isinstance(datum, str):
                    datum = str(datum)
                adjusted_col_width = col_width[i]
                if datum in emphasize_data:
                    pdf.set_text_color(*emphasize_color)
                    pdf.set_font(style=emphasize_style)
                    pdf.multi_cell(adjusted_col_width, line_height, datum, border=0, align=align_data,
                                   new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=pdf.font_size)
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font(style=default_style)
                else:
                    pdf.multi_cell(adjusted_col_width, line_height, datum, border=0, align=align_data,
                                   new_x=XPos.RIGHT, new_y=YPos.TOP, max_line_height=pdf.font_size)  # ln = 3 - move cursor to right with same vertical offset # this uses an object named pdf
            pdf.ln(line_height)  # move cursor back to the left margin
    y3 = pdf.get_y()
    pdf.line(x_left, y3, x_right, y3)


def pdf_header():
    pdf.add_page()
    # Header & Date
    today = date.today().strftime("%m/%d/%Y")
    pdf.set_font('Helvetica', 'B', 15)
    pdf.cell(0, 5, 'SEDmc', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font('Helvetica', 'I', 10)
    pdf.cell(0, 5, 'Star Summary Report', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 4, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 5, sname, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font('Helvetica', 'I', 9)
    pdf.cell(0, 5, today, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 5, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    # Star Info
    pdf.set_font('Times', 'B', 9)
    pdf.set_x(19)
    pdf.cell(26, 5, 'Astrometry Data: ', new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
    # print(pdf.get_x(), pdf.get_y())
    pdf.set_font('Times', '', 8)
    pdf.cell(0, 5, 'ID = ' + sname + ';' + '  RA,DEC = ' + str(position) + ';' + ' Best Parallax (' + plx_idx
             + ') = ' +  str(plx_rpt) + ' (+/-' + str(plx_rpt_err) + ')',
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")

    # Add Stellar Parameter Title in Bold
    pdf.set_font('Times', 'B', 9)
    pdf.set_x(19)
    pdf.cell(28, 4, 'Stellar Parameters: ', new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
    pdf.set_font('Times', '', 8)    
    pdf.cell(0, 4, 'Baseline Data Source = ' + baseline, new_x=XPos.LMARGIN, new_y=YPos.TOP, align="L")

    pdf.set_font("Times", size=8)   # Set Table font

    # Create Stellar Parameter Table
    create_table(table_data=star_data, title=' ', cell_width=[45, 37, 45, 45],
                 emphasize_data=['Data Type'],
                 emphasize_style='B', emphasize_color=(0, 0, 0), x_start='C')

    # Sampling Parameters
    pdf.set_font('Times', 'B', 9)
    pdf.set_x(19)
    pdf.cell(33, 5, 'Sampling Parameters: ', new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
    # print(pdf.get_x(), pdf.get_y())
    pdf.set_font('Times', '', 8)
    pdf.cell(0, 5,  'Observed Data = ' + stored + ';   Model = ' + starmodel + ';  # of Walkers = ' + str(nwalkers)
             + ';  # of Iterations = ' + str(niter) + ';  Burn In = ' + str(burn_in), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.set_x(52)
    pdf.cell(0, 3,  'Min Wavelength = ' + str(wl_min) + ';   Max Wavelength = ' + str(wl_max)
             + ';  # of Fit Points = ' + str(fit_pts) + ';  # of Bad Points = ' + str(bad_cnt) + ';  Fit Error = ' + str(round(fit_err,2)), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")



# Add Plots to PDF Report ##
def pdf_plots(itr):
    # SEDmc Best Fit
    y1 = pdf.get_y()
    pdf.cell(35, 5, new_x=XPos.RIGHT, new_y=YPos.TOP, align="C")
    pdf.image('Data/Figures/' + sname + '_fit-' + str(itr) + '.png', w=120)
    y2 = pdf.get_y()
    pdf.set_xy(68, y2-38)
    pdf.image('Data/Figures/' + sname + '_2sigma-' + str(itr) + '.png', w=35)
    pdf.set_y(y1+3)
    pdf.cell(0, 4, 'SEDmc Observed Data & Best Fit Curve', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_xy(58, y2-5)
    pdf.set_font('Helvetica', '', 5)
    pdf.set_text_color(0, 0, 255)
    pdf.cell(15, 4, '- SEDmc', new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
    pdf.set_text_color(0, 0, 0)

    pdf.cell(10, 4, '- Baseline', new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
    pdf.set_x(120)
    pdf.set_text_color(84, 130, 53)
    pdf.cell(20, 4, '* Fitted Data', new_x=XPos.RIGHT, new_y=YPos.TOP, align="L")
    pdf.set_text_color(255, 0, 0)
    pdf.cell(20, 4, ' X Bad Data', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    # print pdf.get_x(), pdf.get_y()

    # Observed Data Table Plot
    pdf.add_page()
    # print pdf.get_x(), pdf.get_y()
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    y1 = pdf.get_y()
    # pdf.cell(22, 5, ln=0, align="C")
    pdf.cell(10, 1, new_x=XPos.RIGHT, new_y=YPos.TOP, align="C")
    pdf.image('Data/Figures/' + sname + '_Observed_Table' + str(itr) + '.png', w=170)
    # y2 = pdf.get_y()
    pdf.set_y(y1+7)
    pdf.cell(0, 4, 'Observed Data', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 4, 'Good Data Points (Used in Sampler)              Bad Data Points (All not shown)', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    # Chain Plot
    pdf.add_page()
    # print pdf.get_x(), pdf.get_y()
    pdf.set_font('Helvetica', 'B', 10)
    y1 = pdf.get_y()
    pdf.cell(22, 5, new_x=XPos.RIGHT, new_y=YPos.TOP, align="C")
    pdf.image('Data/Figures/' + sname + '_chain-' + str(itr) + '.png', w=150)
    y2 = pdf.get_y()
    pdf.set_y(y1+5)
    pdf.cell(0, 4, 'SEDmc Sampler Behavior - Markov Chain Plot', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_y(y2-5)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(0, 4, 'Auto-correlation Time:   Teff = ' + str(Tau_Teff) + ';  Radius = ' + str(Tau_Radius), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

    # Corner Plot
    pdf.set_y(pdf.get_y()+10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 4, 'SEDmc Posterior Spread - Corner Plot', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(45, 5, new_x=XPos.RIGHT, new_y=YPos.TOP, align="C")
    pdf.image('Data/Figures/' + sname + '_corner-' + str(itr) + '.png', w=100)
    # print pdf.get_x(), pdf.get_y()


def find_enclosing_temps(temp,tlist):
    """For a given temperature <temp> and a list of model temperatures <tlist>,
    find two model temperatures enclosing the given temperature."""
    p = tlist < temp    # p is a boolean array
    idx, = np.where( p[:-1] & ~p[1:] )[0]
    Tlow=tlist[idx]
    Thi =tlist[idx+1]
    return (Tlow,Thi)


def create_model_at_temp(model,temp):
    """Create a model spectrum for a given temperature
    """

    try:
        filein = open('Data/Stellar_Models/' + model + '.pickle','rb')
    except:
        raise Exception("Unrecognized model name:%s Model choice has to be [NextGen|CK04]" % model)
 
    tlist = pickle.load( filein, encoding='latin1')
    filein.close()
 
    # Check if the given temperature is already included in the model grid
    tidx, = np.where(tlist==temp)
    if len(tidx)==1:
       wl,fl = read_model_spectrum(model, temp)
       return np.rec.fromarrays((wl,fl),names="waves,fluxes")
    else:
       Tlow,Thi = find_enclosing_temps(temp,tlist)
       wllow,fllow = read_model_spectrum( model, Tlow )
       wlhi ,flhi  = read_model_spectrum( model, Thi )
    # resample the Thi spectrum using the wllow
    flhi = np.interp(wllow, wlhi, flhi)
    out_flux = (flhi*(temp - Tlow) + fllow*(Thi - temp)) /(Thi - Tlow)
 
    return np.rec.fromarrays((wllow,out_flux),names="waves,fluxes")

    
def read_model_spectrum(model,temperature):
    """Read synthetic spectral data for a given temperature. 
    Return the model in [micron, Jy]."""
    tlist,models = read_all_model_spectra(model)
 
    tidx, = np.where(tlist==temperature)
    if len(tidx)==0:
        raise Exception("Non-existing model temperature %s for model %s" % (temperature, model))
    tmodel,grav,wavelength,flux = models[tidx[0]]
 
    return (wavelength,flux)


def read_all_model_spectra(model):
        """Read all model spectra"""
        data_file=open('Data/Stellar_Models/'  + model + '.pickle', 'rb')
        tlist = pickle.load( data_file, encoding='latin1')
        models= pickle.load( data_file, encoding='latin1')
        data_file.close()
        if model=='ck04':
           tlist = tlist[:60]
           models= models[:60]   # for some reasons, high temperature CK04 model misbehave.
        # check the unit conversion for the scale parameter!!
        for m in models:
            temp,grav,wave,flux = m
            m[-1] = (m[-1] * m[-2]**2 * (5.325E-11) / np.pi) 
        return (tlist,models)
 
def get_model_flux_at_wavel(model,wave_obs):
    """
    Read all model spectra by <read_all_model_spectra> and interpolate at given wavelength points.
    Return: [temperature, wavelengths, model_flux]
    """
    tlist,models = read_all_model_spectra(model)
    models_at_waveobs = []
    for model in models:
        temp,grav,wave,flux = model
        mflux = np.interp(wave_obs, wave, flux)
        models_at_waveobs.append( [temp, wave_obs, mflux] )
    return models_at_waveobs


# # Get Model and Create 2D Model Table
def create_model_table():
    # # Get Model Fluxes at observed wavelengths using SED() get_model_flux_at_wave function
    model_fluxes = get_model_flux_at_wavel(starmodel, obs_wl)
    mf_df = pd.DataFrame(model_fluxes)
    mf_df_temp = mf_df.iloc[:,0]               # Get Model temps
    mf_df_wl = mf_df.iloc[0,1]                 # Get Model wavelengths (same as observed)
    mf_df_data = mf_df.iloc[:,2]               # Get Model flux data

    # # Create 2-D Model Flux Table
    mf_df_out = pd.DataFrame(mf_df_wl, columns=["WL"])
    for i in range(len(mf_df_temp)):
        mf_df_out[mf_df_temp[i]] = mf_df_data[i]
    return mf_df_out, mf_df_temp


# Get Interpolated Model Flux
# Get the linear interpolated model flux at the observed WL
def get_mod_at_temp_wl(temp, wl_idx):

    if starmodel == 'nextgen':
        if temp < 10000:  # For temps < 10,000 K with 100 K increments
            temp_hi = int(math.ceil(temp / 100) * 100)
            temp_lo = temp_hi - 100
        else:  # For temps 10,000+ K with 500K increments
            temp_round = round(temp, -3)
            if temp_round > temp:
                temp_hi = temp_round
                temp_lo = temp_hi - 500
            else:
                temp_lo = temp_round
                temp_hi = temp_lo + 500
    if starmodel == 'ck04':
        if temp < 13000:  # For temps < 13,000 K with 250 K increments
            temp_hi = int(math.ceil(temp / 250) * 250)
            temp_lo = temp_hi - 250
        else:  # For temps 13,000+ K with 1000K increments
            temp_round = round(temp, -3)
            if temp_round > temp:
                temp_hi = temp_round
                temp_lo = temp_hi - 1000
            else:
                temp_lo = temp_round
                temp_hi = temp_lo + 1000
    temp_lo_idx = mf_df_temp[mf_df_temp == temp_lo].index[0]  # Find the model index for lower temp
    model_at_obs_flux_lo = mf_df_out.iloc[wl_idx, temp_lo_idx + 1]  # Get the model flux for lower temp
    temp_hi_idx = mf_df_temp[mf_df_temp == temp_hi].index[0]  # Find the model index for higher temp
    model_at_obs_flux_hi = mf_df_out.iloc[wl_idx, temp_hi_idx + 1]  # Get the model flux for higher temp
    model_at_obs_flux_yp = pd.concat([model_at_obs_flux_lo, model_at_obs_flux_hi], axis=1,
                                     ignore_index=True)  # y values
    model_at_temp = []  # New list
    for i in wl_idx:  # interpolate model flux between temps @ wl
        model_at_temp_wl = np.interp(temp, [temp_lo, temp_hi], model_at_obs_flux_yp.loc[i])
        if model_at_temp_wl < 0:
            print('temp ', model_at_temp_wl, temp, temp_lo, temp_hi)
            print('yp', model_at_obs_flux_yp.loc[i], i)
            print('flux range', model_at_obs_flux_lo, model_at_obs_flux_hi)
        model_at_temp.append(model_at_temp_wl)
    return pd.Series(model_at_temp, index=wl_idx)


# # Define Model used be EMCEE
# Return scaled model flux value for model temp at wavelength observed
def model(theta, wl_idx):  # wl_idx is index of model_at_obs df rows
    temp, radius = theta
    scale = ((radius * plx) / 1000) ** 2
    return scale * get_mod_at_temp_wl(temp, wl_idx)


# # Define Log Likelihood
# Find likelihood of model fitting observed data for all wavelengths observed using Chi-Squared functions
def lnlike(theta, x, y, y_err):
    # print(x)
    # if use_stored:
    #     stored = "y"
    # else:
    #     stored = "n"
    # global store_sampler_all, store_sampler, store_test, check
    flux_model = model(theta, x)
    sigma2 = y_err**2 + flux_model**2 * np.exp(2 * log_f)  # Variance correction from emcee example
    # y_err = 0.1 * y
    #ln_like = -0.5 * np.sum((y - flux_model)**2 / flux_model)  # Pearson Chi-Squared statistic (PC2)
    # ln_like = -0.5 * np.sum(((y - flux_model/y))**2 / flux_model)  # % Diff Squared (%D2)
    # ln_like = -0.5 * np.sum(((y - flux_model/y)) / flux_model)  # % Diff (%D)
    # ln_like = -0.5 * np.sum((y - flux_model)**2 / y_err)  # Chi-Squared statistic (C2)
    #ln_like = -0.5 * np.sum((y - flux_model)**2 / y_err**2)  # Chi-Squared statistic (C22)
    ln_like = -0.5 * np.sum((y - flux_model)**2 / sigma2 + np.log(sigma2))  # Likelihood from emcee exampple
    return ln_like


# # Define Log Priors
# Define limits of theta (temp & scale)
def lnprior(theta):
    temp, radius = theta
    if min_model_temp < temp < max_model_temp and min_radius < radius < max_radius:  # Set temp_idx and scale ranges for sampling
        return 0.0  # 0.0 if True
    return -np.inf  # -inf if False


# # Define Log Probability
# Define posterior probability function
def lnprob(theta, x, y, y_err):
    # global store_sampler_all, store_sampler
    lp = lnprior(theta)  # check if sample vales of theta in range selected in lnprior
    if not np.isfinite(lp):  # if not, then don't use
        return -np.inf
    ln_like = lnlike(theta, x, y, y_err)
    return lp + ln_like  # if so, then use lnlike value


# # SED_EMCEE Sampler Data
def define_data():
    # # Define EMCEE Sampling Data
    # Uses user entered data or defaults
    data = (obs_wl_idx, obs_flux, obs_flux_err)  # data = wl index, observed flux and error
    initial = np.array([Teff_bl, Rstar_bl])  # Initial values for theta (temp, scale)
#    initial = np.array([5868, 0.0409**2])  # Initial values for theta (temp, scale)
    ndim = len(initial)  # Number of dimensions = number of theta parameters
    p0 = [np.array(initial[0]) + np.array(initial[0] / 10) * np.random.randn(1) for i in
            range(nwalkers)]
    p0_2 = [np.array(initial[1]) + np.array(initial[1] / 10) * np.random.randn(1) for i in
            range(nwalkers)]
    p0 = np.append(p0, p0_2, axis=1)
    # p0 = [np.array(initial) + 1e-5 * np.random.randn(ndim) for i in
    #       range(nwalkers)]  # p0 from another example seems to work better
    return p0, ndim, data


# # Run sampler with multiprocessor pools
def run_sampler(p0):
    with closing(Pool()) as pool:
        sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, pool=pool, args=data,
            moves=[
            (emcee.moves.StretchMove(), 0),
            (emcee.moves.KDEMove(bw_method = 1), 1),
            (emcee.moves.DESnookerMove(), 0),
        ])  # tried different Moves, but put back to default
        print("Running burn-in...")
        p0, _, _ = sampler.run_mcmc(p0, burn_in, progress=prog_flag)  # May need to adjust burn-in depending on data
        sampler.reset()
        print("Running production...")
        pos, prob, state = sampler.run_mcmc(p0, niter, thin_by=thin, progress=prog_flag)
        pool.terminate()
    return sampler, pos, prob, state


# # Set Likelihood temperature range
def temp_range(Teff_bl, starmodel):
    if starmodel == 'nextgen':
        min_model_temp = 1700
        if min_model_temp < (Teff_bl - 4000):
            min_model_temp = Teff_bl - 4000
        max_model_temp = Teff_bl + 4000
    
    if starmodel == 'ck04':
        min_model_temp = 3500
        if min_model_temp < (Teff_bl - 4000):
            min_model_temp = Teff_bl - 4000
        max_model_temp = Teff_bl + 4000
    return min_model_temp, max_model_temp
        

##  Set Likelihood radius range
def rad_range(Rstar_bl):
    radius = Rstar_bl
    min_radius = radius - 0.9 * radius
    max_radius = radius + 0.9 * radius
    return min_radius, max_radius


# # # Main Routine # # #
if __name__ == "__main__":
  # %matplotlib inline
  fig_size = plt.rcParams['figure.figsize'] = (20, 15)  # Make plots as wide as notebook page
  start_time = datetime.now()
  
  if not os.path.exists('Data/Photometry'):
      os.makedirs('Data/Photometry/VizierSED')
      os.makedirs('Data/Photometry/ck04')
      os.makedirs('Data/Photometry/nextgen') 
  
  if not os.path.exists('Data/Figures'):
      os.makedirs('Data/Figures')
      
  if not os.path.exists('Data/Reports'):
      os.makedirs('Data/Reports/ck04')
      os.makedirs('Data/Reports/nextgen')
      
  if not os.path.exists('Data/Run_Data'):
      os.makedirs('Data/Run_Data')
               
  print('Prog_Flag = ',prog_flag)
  
  # # Parse command line arguments and handle errors
  len_arg = len(sys.argv)
  err_str = 'Use command line args in this order-> required: Object(e.g., WASP94); ' \
            'optional: Parallax Teff AngDia Model UseStored RA DEC'
  
  # # Get input parameters for SED_EMCEE by either command line arguments or prompts
  if len_arg == 1:                           # If only name provided prompt for other input parameters
      sname, sposition, plx_bmk, Teff_bmk, use_Teff_bmk, ang_dia_bmk, use_ang_dia_bmk, smodel, nwalkers, niter, burn_in, \
            use_stored, star_model, position = prompt_input(err_str)
      print(sname, sposition, plx_bmk, Teff_bmk, use_Teff_bmk, ang_dia_bmk, use_ang_dia_bmk, smodel, nwalkers, niter, burn_in,
            use_stored)
  else:                            # If command lime arguments provided parse for input parameters and set sampling values
      sname, plx_bmk, Teff_bmk, ang_dia_bmk, sposition, smodel, use_ang_dia_bmk, use_Teff_bmk, \
            use_stored, star_model, position = parse_arg(len_arg, err_str)
      print(sname, plx_bmk, Teff_bmk, ang_dia_bmk, star_model, position, sposition, smodel, use_stored, nwalkers, niter, burn_in)
  
  # Convert stored data flag to text
  if use_stored:
      stored = "Stored"
  else:
      stored = "New"
  
  ## Define Star Model
  if not smodel:
      star_model = starmodel = 'ck04'
  else:
      starmodel = star_model
  print(starmodel)
  
  
  ## Create tables to store all input parameters and results
  store_all = pd.DataFrame({'Source':sname}, index=[0])
  
  ## Create tables to store all samplers data and results
  store_sampler_all = pd.DataFrame([])
  store_sampler = pd.DataFrame([])
  store_test = pd.DataFrame()
  check = 0
  
  # Capture all paralax data to chose one with lowest uncertainty
  plx_data = pd.DataFrame(columns = ['Plx', 'Plx_err', 'Plx_pre'])
  
  ## Fit Star using source name
  source_name = sname
  
  src_ID_2 = "NaN"
  RA, DEC, plx, plx_err  = get_VO_Data(source_name)
  
  # Load Benchmark Data for source if available
  use_Teff_bmk = False  # Force use of bennchmark file
  bl_source = 'NASA'
  data_bl = pd.read_csv('Data/Baseline_' + bl_source + '.csv')
  data_bl_source = data_bl[data_bl['HD'].isin([sname])]
  if data_bl_source.empty and not use_Teff_bmk:   # Set values to NaN and SEDFit data to baseline if benchmark data not available
      # use_Teff_bmk = False
      # use_ang_dia_bmk = False
      Teff_bmk = "NaN"
      Teff_bmk_err = "NaN"
      Rstar_bmk = "NaN"
      Rstar_bmk_err = "NaN"
      ang_dia_bmk = "NaN"
      ang_dia_bmk_err = "NaN"
      plx_bmk = "NaN"
      plx_bmk_err = "NaN"
      if src_ID_2 != "Nan":
          Teff_bl = store_all['TEFF_dr2'][0]   # Use GAIA DR2 Teff as baseline Temp
          Rstar_bl = store_all['RSTAR_dr2'][0]  # Use GAIA DR2 Rstar as baseline stellar radius
      # ang_dia_bmk = s.sfit_apprad * 4.65047 * 2    # Use SEDFit apprad
      apprad_bl = (Rstar_bl * plx) / 1000
      print('Teff & apprad not defined')
  elif use_Teff_bmk:   # Use user input benchmark data if available and set as baseline data
      Teff_bl = Teff_bmk    # Use SEDFit Temp and baseline Temp
      # ang_dia_bmk = s.sfit_apprad * 4.65047 * 2    # Use SEDFit apprad
      apprad_bl = ang_dia_bmk / (4.65047 * 2)
      Rstar_bmk = Rstar_bl = float('{:.3g}'.format((ang_dia_bmk * 1000) / (4.65047 * 2 * plx_bmk)))
      Teff_bmk_err = "NaN"
      Rstar_bmk_err = "NaN"
      ang_dia_bmk_err = "NaN"
      plx_bmk_err = "NaN"
      print('Use Command Line BL Data')
  else:                # Use benchmark data from file and set baseline data
      # use_Teff_bmk = True
      # use_ang_dia_bmk = True
      data_bl_source = data_bl_source.reset_index(drop=True)
      Teff_bl = data_bl_source['Teff'][0]
      Teff_bl_err = data_bl_source['Teff_err'][0]
      Rstar_bl = data_bl_source['Rstar'][0]
      Rstar_bl_err = data_bl_source['Rstar_err'][0]
      ang_dia_bl = data_bl_source['angdia'][0]
      apprad_bl = ang_dia_bl / (4.65047 * 2)
      ang_dia_bl_err = data_bl_source['angdia_err'][0]
      plx_bl = data_bl_source['plx'][0]
      plx_bl_err = data_bl_source['plx_err'][0]
      baseline = bl_source
      print('Use Baseline file')
  store_all['Teff_bl'] = Teff_bl
  store_all['Teff_bl_err'] = Teff_bl_err
  store_all['Rstar_bl'] = Rstar_bl
  store_all['Rstar_bl_err'] = Rstar_bl_err
  store_all['ang_dia_bl'] = ang_dia_bl
  store_all['ang_dia_bl_err'] = ang_dia_bl_err
  store_all['plx_bl'] = plx_bl
  store_all['plx_bl_err'] = plx_bl_err
  if isinstance(plx_bl, float): 
      plx_data.loc['Baseline'] = [plx_bl, plx_bl_err, plx_bl_err / plx_bl]
  
  min_radius, max_radius = rad_range(Rstar_bl) ##  Set Likelihood radius range
  
  # # Observed Photometry Filter Function
  # Configuration parameters
  wl_min = 0.4
  wl_max = 8
  # temp = 5134
  # scale = 0.00706841867129298
  # fit_err_max = 0.2
  fit_err_init = 0.1
  fit_pts_min = 12
  
  plx_idx = plx_data[['Plx_pre']].idxmin()[0]  # Get index of best parallax
  plx_mc, plx_mc_err, plx_mc_pre = plx_data.loc[plx_idx]   #Get best parallax for SEDmc input
  print("Best Parallax", plx_idx, plx_mc, plx_mc_err, plx_mc_pre)
  
  # Store SED_EMCEE input parameters
  store_all['Walkers'] = nwalkers
  store_all['Iterations'] = niter
  store_all['Burn In'] = burn_in
  store_all['Best Plx'] = plx_idx
  store_all['Parallax'] = plx = plx_mc
  store_all['Parallax_err'] = plx_err = plx_mc_err
  
  
  # # Use query_sed to get Photometry data
  obs_data_range, viz_err = query_sed(source_name)
  print('Done VizierSED Error = ', viz_err)
  obs_data = obs_data_range
  obs_data = remove_dups(obs_data)
  if len(obs_data) < fit_pts_min:
      fit_pts_min = len(obs_data)
  print('Observed Data Points = ', len(obs_data))
  
  
  # Run both models
  save_acc = pd.DataFrame(columns = ['Teff', 'Radius'])  #Capture %Delta bl/Bl data
  save_err = pd.DataFrame(columns = ['Teff', 'Radius'])  #Capture error data
  save_store_all = pd.DataFrame([])
  model_lst = ['ck04','nextgen']
  for starmodel in model_lst:
      low_acc = False  # reset low_acc flag for new model
      print('Start Model & Accuracy', starmodel, low_acc)
      if starmodel == 'ck04' and Teff_bl <= 3600:   ## Don't use CK04 if temp < 3600
          save_acc.loc[starmodel] = [99.99, 99.99]
          save_err.loc[starmodel] = [99.99, 99.99]
          print('CK04 skipped')
          continue
      print(starmodel)
  
      min_model_temp, max_model_temp = temp_range(Teff_bl, starmodel) # Set temp range for likelihood function
  
      # Get Baseline Best Fit curve
      bl_star = create_model_at_temp(starmodel, Teff_bl) # interpolate between model temps above and below
      apprad_bl = (Rstar_bl * plx_bl) / 1000
      bl_star.fluxes *= apprad_bl**2    # Multiply fluxes by scale factor (apprad**2)
      print("Baseline, Teff, Rstar & AppRad = ", baseline, Teff_bl, Rstar_bl, apprad_bl)
      # # FIRST ITERATION # #
      # Perform first iteration using SED best fit curve for filtering observed data #
      itr = 1
      
      if use_stored:  # Use stored observed data for fit curve
          good_data, bad_data, fit_pts, fit_err, fit_qual, bad_cnt = get_stored_data(fit_err_init, fit_pts_min)
      else:  # Get observed data for fit curve
          # # Original clean data filtering method
          # good_data, bad_data, bad_data_keep, fit_pts, fit_err, fit_qual, fit_qual2 = get_clean_data(obs_data_range, bl_star, fit_err_init, fit_pts_min)
          # # Updated clean data filtering method
          print("clean data")
          good_data, bad_data, fit_pts, fit_err, fit_qual = get_clean_data(obs_data, bl_star, fit_err_init, fit_pts_min)
          # # Vizier SED data filtering based on blackbody curve fitting method
          if fit_err > .5:  # Check if low accuracy
              low_acc = True
              print('Low Accuracy - Fit Err = ', fit_err)
              if isinstance(store_all['RSTAR_dr2'][0], float) and not np.isnan(store_all['RSTAR_dr2'][0]):
                  # Check if DR2 data available 
                  Teff_bl = int(store_all['TEFF_dr2'][0])
                  Teff_bl_err = int(store_all['TEFF_POS_dr2'][0]) - Teff_bl
                  Rstar_bl = float('{:.3g}'.format(store_all['RSTAR_dr2'][0]))
                  Rstar_bl_err = float('{:.3g}'.format(abs(store_all['RSTAR_POS_dr2'][0] - Rstar_bl)))
                  plx_bl = float('{:.3g}'.format(store_all['PLX_dr2'][0]))
                  plx_bl_err = float('{:.3g}'.format(store_all['PLX_ERR_dr2'][0]))
                  bl_star = create_model_at_temp(starmodel, Teff_bl) # interpolate between model temps above and below
                  ang_dia_bl = store_all['ang_dia_bl'] = float('{:.3g}'.format(4.65047 * 2 / 1000 * Rstar_bl * plx_bl))
                  ang_dia_bl_err = store_all['ang_dia_bl_err'] = float('{:.2g}'.format(4.65047 * 2 /1000 * np.sqrt((Rstar_bl * plx_bl_err)**2 + (plx_bl * Rstar_bl_err)**2)))
                  apprad_bl = (Rstar_bl * plx_bl) / 1000
                  bl_star.fluxes *= apprad_bl**2    # Multiply fluxes by scale factor (apprad**2)
                  print("DR2 Teff, Rstar & AppRad = ", Teff_bl, Rstar_bl, apprad_bl)
                  good_data, bad_data, fit_pts, fit_err, fit_qual = get_clean_data(obs_data, bl_star, fit_err_init, fit_pts_min)
                  min_radius, max_radius = rad_range(Rstar_bl)
                  min_model_temp, max_model_temp = temp_range(Teff_bl, starmodel)
                  store_all['Teff_bl'] = Teff_bl
                  store_all['Teff_bl_err'] = Teff_bl_err
                  store_all['Rstar_bl'] = Rstar_bl
                  store_all['Rstar_bl_err'] = Rstar_bl_err
                  baseline = 'GAIA DR2'
                  if fit_err > .5:  # Check if low accuracy
                      low_acc = True
                      print('DR2 Low Accuracy - Fit Err = ', fit_err)
              else:
                  print('DR2 data not available')
  
              
          good_data = good_data.reset_index(drop=True)
          wl_min = float('{:.3g}'.format(np.min(good_data.wl)))
          wl_max = float('{:.3g}'.format(np.max(good_data.wl)))
          bad_data_idx = bad_data.index
          bad_data = bad_data.reset_index(drop=True)
          bad_cnt = len(bad_data)
      
      # Separate plotting data
      gx = good_data.wl
      gy = good_data.fl
      bx = bad_data.wl
      by = bad_data.fl
      
      # Clean up flux error
      good_data.efl = good_data.efl.replace(np.nan, 0)   # replace NaN with 0
      good_data['efl'] = np.where(good_data['efl'] == 0, good_data['fl'] * 0.1, good_data['efl'])   # replace 0 w/ 10% flux
      
      # Separate into column lists
      obs_wl = good_data.wl  # Use SED wl range and clean data
      obs_flux = good_data.fl  # Use SED observed flux @ wl range and clean data from inphot
      obs_flux_err = good_data.efl  # Use SED observed flux error @ wl range and clean data from inphot
      obs_wl_idx = list(range(0, len(obs_wl)))  # Update wl index list for EMCEE model for wl range and clean data
      
      
      # # Get Model and Create 2D Model Table
      mf_df_out, mf_df_temp = create_model_table()
      
      # # SED_EMCEE Sampler Data
      p0, ndim, data = define_data()
      
      # Run Sampler
      print('Model, Baseline, Teff_bl, Rsun_bl, ang_dia_bl, fit_err', starmodel, baseline, Teff_bl, Rstar_bl, ang_dia_bl, fit_err)
      sampler, pos, prob, state = run_sampler(p0)
      
      #Reset Baseline data and run again if accuracy too low
      loop_cnt = 0
      while low_acc == True:
          loop_cnt += 1
          print('Loop Count =', loop_cnt)
          samples = sampler.flatchain
          temps = np.percentile(samples[:, 0], [16, 50, 84])
          Teff_bl = int(temps[0])
          Teff_bl_err = int(np.diff(temps)[0])
          radii = np.percentile(samples[:, 1], [16, 50, 84])
          Rstar_bl = float('{:.3g}'.format(radii[0]))
          Rstar_bl_err = float('{:.3g}'.format(np.diff(radii)[0]))
          plx_bl = plx_mc
          plx_bl_err = plx_mc_err
          bl_star = create_model_at_temp(starmodel, Teff_bl) # interpolate between model temps above and below
          ang_dia_bl = store_all['ang_dia_bl'] = float('{:.3g}'.format(4.65047 * 2 / 1000 * Rstar_bl * plx_bl))
          ang_dia_bl_err = store_all['ang_dia_bl_err'] = float('{:.2g}'.format(4.65047 * 2 /1000 * np.sqrt((Rstar_bl * plx_bl_err)**2 + (plx_bl * Rstar_bl_err)**2)))
          apprad_bl = (Rstar_bl * plx_bl) / 1000
          bl_star.fluxes *= apprad_bl**2    # Multiply fluxes by scale factor (apprad**2)
          print("SEDmc Teff, Rstar, AngDia & AppRad = ", Teff_bl, Rstar_bl, ang_dia_bl, apprad_bl)
          good_data, bad_data, fit_pts, fit_err, fit_qual = get_clean_data(obs_data, bl_star, fit_err_init, fit_pts_min)
          min_radius, max_radius = rad_range(Rstar_bl)
          min_model_temp, max_model_temp = temp_range(Teff_bl, starmodel)
          store_all['Teff_bl'] = Teff_bl
          store_all['Teff_bl_err'] = Teff_bl_err
          store_all['Rstar_bl'] = Rstar_bl
          store_all['Rstar_bl_err'] = Rstar_bl_err
          baseline = 'Initial SEDmc Results'
          
          #Clean up Good Data
          good_data = good_data.reset_index(drop=True)
          wl_min = float('{:.3g}'.format(np.min(good_data.wl)))
          wl_max = float('{:.3g}'.format(np.max(good_data.wl)))
          bad_data_idx = bad_data.index
          bad_data = bad_data.reset_index(drop=True)
          bad_cnt = len(bad_data)
      
          # Separate plotting data
          gx = good_data.wl
          gy = good_data.fl
          bx = bad_data.wl
          by = bad_data.fl
      
          # Clean up flux error
          good_data.efl = good_data.efl.replace(np.nan, 0)   # replace NaN with 0
          good_data['efl'] = np.where(good_data['efl'] == 0, good_data['fl'] * 0.1, good_data['efl'])   # replace 0 w/ 10% flux
          
          # Separate into column lists
          obs_wl = good_data.wl  # Use SED wl range and clean data
          obs_flux = good_data.fl  # Use SED observed flux @ wl range and clean data from inphot
          obs_flux_err = good_data.efl  # Use SED observed flux error @ wl range and clean data from inphot
          obs_wl_idx = list(range(0, len(obs_wl)))  # Update wl index list for EMCEE model for wl range and clean data
                  
          # # Get Model and Create 2D Model Table
          mf_df_out, mf_df_temp = create_model_table()
          
          # # SED_EMCEE Sampler Data
          p0, ndim, data = define_data()
          
          # Run Sampler
          print('Model, Baseline, Teff_bl, Rsun_bl, ang_dia_bl, fit_err', starmodel, baseline, Teff_bl, Rstar_bl, ang_dia_bl, fit_err)
          sampler, pos, prob, state = run_sampler(p0)
          
          # Check Accuracy and Update flag
          samples = sampler.flatchain
          radii = np.percentile(samples[:, 1], [16, 50, 84])
          Rstar_ck = float('{:.3g}'.format(radii[0]))
          Rstar_ck_acc = abs((Rstar_ck - Rstar_bl) / Rstar_bl)
          if fit_err > 0.5 or Rstar_ck_acc > 0.2:
              low_acc = True
              print('Low Accuracy Check', low_acc, fit_err, Rstar_ck_acc)
              if loop_cnt == 3:
                  low_acc = False
                  print('Loop Count Exceeded')
                  continue
          else:
              low_acc = False
              print('Low Accuracy Check', low_acc, fit_err, Rstar_ck_acc)
      
      # Plot Sampler Behavior
      plot_chain(itr)
      
      # Get samples, max values of parameter space & AutoCorrelation times
      samples = sampler.flatchain  # Per example
      theta_max = samples[np.argmax(sampler.flatlnprobability)]  # Per example
      tau = sampler.get_autocorr_time(quiet=True)
      
      # Calculate Uncertainties & Plot
      teff_med, teff_u_neg, teff_u_plus, teff_med_pct_bl, scale_med, scale_u_neg, scale_u_plus, apprad_med, \
      apprad_u_neg, apprad_u_plus, ang_dia_emc, ang_dia_emc_u_neg, ang_dia_emc_u_plus, ang_dia_emc_pct_bl, \
      Rstar_med, Rstar_u_neg, Rstar_u_plus, Rstar_bl, Rstar_pct_bl, ang_dia_emc_pct_u, teff_pct_u, Rstar_pct_u = plot_sigmas(itr)
      
      # Get SED_EMCEE Best Fit curve
      fit_star = create_model_at_temp(starmodel, theta_max[0]) # interpolate between model temps above and below
      fit_star.fluxes *= scale_med  # Multiply fluxes by scale factor (apprad**2)
      
      # # Corner Plot
      labels = plot_corner(itr)
      
      # # Print Best Fit Value Summary
      print_summary(plx_mc, plx_mc_err)
      
      # Calculate & Store additional parameters
      
      store_all['VizSed_Error'] = viz_err
      store_all['Baseln'] = baseline
      Tau_Teff = store_all['Tau_Teff'] = round(tau[0], 3)
      Tau_Radius = store_all['Tau_Radius'] = round(tau[1], 3)
      store_all['Stored'] = stored
      store_all['Model'] = starmodel
      store_all['Name'] = source_name
      store_all['Rsn'] = Rstar_med
      store_all['Rsn_err-'] = Rstar_u_neg
      store_all['Rsn_err+'] = Rstar_u_plus
      store_all['%Rsn_err-'] = Rstar_u_neg / Rstar_med
      store_all['%Rsn_err+'] = Rstar_u_plus / Rstar_med
      
      # Plot SED_EMCEE Best Fit curve and Observed Data
      plot_SED_EMCEE_obs(gx, gy, bx, by, itr)
      
      # Plot Observed Data Table
      plot_obs_table(itr)
      
      # Round parallax and error for report
      plx_rpt = float('{:.4g}'.format(plx_mc))
      plx_rpt_err = float('{:.3g}'.format(plx_mc_err))
      if isinstance(plx_bl, float): 
          plx_bl_rpt = float('{:.4g}'.format(plx_bl))
          plx_bl_rpt_err = float('{:.3g}'.format(plx_bl_err))
      else:
          plx_bl_rpt = plx_bl
          plx_bl_rpt_err = plx_bl_err
      
      # Create PDF, add header & SEDfit plot
      star_data = [
          ["Data Type", "Teff [K]", "Rstar [Rsun]", "Angular Diameter [arcsec]", ],
          ["Baseline Values {SEDmc residuals}", str(Teff_bl) + " (+/-" + str(Teff_bl_err) + ')'+ '  {' + str(teff_med_pct_bl) + '%}', 
                str(Rstar_bl) + " (+/-" + str(Rstar_bl_err) + ')' + '  {' + str(Rstar_pct_bl) + '%}',
                str(ang_dia_bl) + " (+/-" + str(ang_dia_bl_err) + ')' + '  {' + str(ang_dia_emc_pct_bl) + '%}', ],
          ["SEDmc Results {fractional error}", str(teff_med) + " (+" + str(teff_u_plus) + ', -' + str(teff_u_neg) + ')' + '  {' + str(teff_pct_u) + '%}',
               str(Rstar_med) + " (+" + str(Rstar_u_plus) + ', -' + str(Rstar_u_neg) + ')' + '  {' + str(Rstar_pct_u) + '%}',
               str(ang_dia_emc) + " (+" + str(ang_dia_emc_u_plus) + ', -' + str(ang_dia_emc_u_neg) + ')' + '  {' + str(ang_dia_emc_pct_u) + '%}', ], 
      ]
      pdf = FPDF()
      if position == (0,0):
          position = (RA,DEC)
      pdf_header()
      
      # Add Plots to PDF Report ##
      pdf_plots(itr)
      
      
      # # Edit Observed Data Point # #
      loop = False  # Disables observed data editor. Comment out to enable editor.
      while loop:
          # Enter EMCEE sampling parameters or accept defaults
          print('Would you like to edit points (y = yes)? ')
          edit_pts = sys.stdin.readline()
          if edit_pts == "y\n":
              plot_obs(itr, obs_data, gx, gy, bx, by)
              plot_obs_table(itr)
              # Reading and show png image file for XTerm sessions
              im1 = Image.open('Data/Figures/' + source_name + '_Observed_' + str(itr) + '.png')
              im2 = Image.open('Data/Figures/' + source_name + '_Observed_Table' + str(itr) + '.png')
              # show images
              im1.show()
              im2.show()
              # Pick New Bad Points
              print('Add new Bad points from Good points list. Enter return only when done.')
              try:
                  bad_pts = []
                  while True:
                      bad_pts.append(int(sys.stdin.readline()))
              # if the input is non-integer, continue
              except:
                  print(bad_pts)
                  add_bad_data_idx = bad_pts
                  add_bad_data = pd.DataFrame(good_data, index=add_bad_data_idx)
              # Pick New Good Points
              print('Add new Good points from Bad points list. Enter return only when done.')
              try:
                  good_pts = []
                  while True:
                      good_pts.append(int(sys.stdin.readline()))
              # if the input is non-integer, continue
              except:
                  print(good_pts)
                  add_good_data_idx = good_pts
                  add_good_data = pd.DataFrame(bad_data, index=add_good_data_idx)
              if len(bad_pts) != 0:
                  # Drop these from good_data
                  new_good_data = good_data.drop(index=add_bad_data_idx)
                  # Add to bad_data
                  new_bad_data = pd.concat([bad_data, add_bad_data], ignore_index=True)
                  # print(" 1 - ngd = ", len(new_good_data), "nbd = ", len(new_bad_data))
              else:
                  new_good_data = good_data
                  new_bad_data = bad_data
                  # print(" 2 - ngd = ", len(new_good_data), "nbd = ", len(new_bad_data))
              if len(good_pts) != 0:
                  # Drop these from bad data
                  new_bad_data = new_bad_data.drop(index=add_good_data_idx)
                  # Add to good_data
                  new_good_data = pd.concat([new_good_data, add_good_data], ignore_index=True)
                  # print(" 3 - ngd = ", len(new_good_data), "nbd = ", len(new_bad_data))
              # Creat new lists
              new_good_data = new_good_data.sort_values(by=['wl'])
              new_bad_data = new_bad_data.sort_values(by=['wl'])
              good_data = new_good_data.reset_index(drop=True)
              bad_data = new_bad_data.reset_index(drop=True)
              # print(" 4 - ngd = ", len(new_good_data), "nbd = ", len(new_bad_data))
      
      
              # # # Next ITERATION # # #
              # Perform next iteration using manual observed data edits#
              itr += 1
      
              # Separate plotting data
              gx = good_data.wl
              gy = good_data.fl
              bx = bad_data.wl
              by = bad_data.fl
      
              # Separate into column lists
              obs_wl = good_data.wl  # Use SED wl range and clean data
              obs_flux = good_data.fl  # Use SED observed flux @ wl range and clean data from inphot
              obs_flux_err = good_data.efl  # Use SED observed flux error @ wl range and clean data from inphot
              obs_wl_idx = list(range(0, len(obs_wl)))  # Update wl index list for EMCEE model for wl range and clean data
      
              # Plot SEDfit best fit curve and observed data
              # plot_SEDfit_obs(gx, gy, bx, by)
      
              # # Get Model and Create 2D Model Table
              mf_df_out, mf_df_temp = create_model_table()
      
              # # SED_EMCEE Sampler Data
              p0, ndim, data = define_data()
      
              # Run Sampler
              sampler, pos, prob, state = run_sampler(p0)                
      
              # Plot Sampler Behavior
              plot_chain(itr)
      
              # # Print Best Fit Value Summary
              samples, theta_max, Rstar, plx, tau = print_summary(plx)
      
              # Get SED_EMCEE Best Fit curve
              fit_star = create_model_at_temp(starmodel, theta_max[0]) # interpolate between model temps above and below
              fit_star.fluxes *= theta_max[1] # Multiply fluxes by scale factor (apprad**2)
      
              # # Corner Plot
              labels = plot_corner(itr)
      
              # Calculate Uncertainties & Plot
              teff_med, teff_u_neg, teff_u_plus, teff_med_pct_bl, scale_med, scale_u_neg, scale_u_plus, \
              apprad_med, apprad_u_neg, apprad_u_plus, ang_dia_emc, ang_dia_emc_u_neg, ang_dia_emc_u_plus, \
              ang_dia_emc_pct_bl, Rstar_med, Rstar_u_neg, Rstar_u_plus = plot_sigmas(itr)
      
              # Plot SED_EMCEE Best Fit curve and Observed Data
              plot_SED_EMCEE_obs(gx, gy, bx, by, itr)
      
              # Add Plots to PDF Report ##
              pdf.add_page()
              pdf_plots(itr)
          else:
              loop = False
      
      
      # Save PDF
      pdf.output('Data/Reports/' + starmodel + '/' + sname + '-' + stored + '.pdf')
      
      # Save Store all data for current model
      save_store_all = save_store_all.append(store_all)
      
      # Store Photometry Data
      good_data.to_csv('Data/Photometry/' + star_model + '/' + sname + '_good_data.csv', index=False)
      bad_data.to_csv('Data/Photometry/' + star_model + '/' + sname + '_bad_data.csv', index=False)
      
      # Save accuracy & precision data
      save_acc.loc[starmodel] = [abs(teff_med_pct_bl), abs(Rstar_pct_bl)]  # Accuracy data
      save_err.loc[starmodel] = [abs(teff_pct_u), abs(Rstar_pct_u)]          # Precision data
  
  # Choose most accurate and precise model results
  #starmodel = save_acc[['Teff']].idxmin()[0]   # Use for highest accuracy model
  starmodel = save_err[['Radius']].idxmin()[0]   # Use for highest precision model
  print('Best model =', starmodel)
  
  runtime = datetime.now() - start_time
  print('Runtime = ', runtime)
  
  # Store all data
  #store_all = input_para = pd.read_csv('store_all_' + starmodel +'.csv')
  store_all = save_store_all.loc[save_store_all['Model'] == starmodel]
  store_all['Runtime'] = runtime
  store_all.to_csv('Data/Run_Data/' + sname +'_store_best.csv', index=False)
