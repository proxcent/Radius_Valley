
## Radius Valley Slope Estimation - Gap Bin Method with Bayesian Slope Estimation and Uncertainties

The Jupyter Notebooks in this folder are used to estimate the slope of the Radius Valley given the final planet sample from the **Data/Planet_Sample folder**.  The **RV_Gap_Bin-{x-axis}** notebooks, where **{x-axis}** can be **Period**, **Flux** or **Mass**, uses the final planet sample to generate a large amount of slope data that can be analyzed further and estimate uncertainties using Bayesian methods in the **RV_Slope_{x-axis}** notebooks. Specifically, the Gap Bin method is a piecewise segmentation that creates distinct bi-modal distributions for measuring points along the radius valley gap. This method involves segmenting the data for the horizontal axis, whether orbital period, insolation flux or stellar mass, into distinct groups. We used a 2D power law formula $R_p = X^me^{R_{p0}}$ and estimates the slope $m$ and $R_{p0}$ intercept using the Gap Bin slope measurement process with additional filtering and statistical methods to reduce computational biases and determine uncertainties. Moreover, $X$ could be either horizontal parameter $P$ (orbital period), $S_p$ (planet insolation flux) or $M_⁎$ (stellar mass), where $R_{p0}$ is the value of $R_p$ where the line intercepts the horizontal axis at $X = 0$. The complete analysis process for all planetary and stellar parameters is as follows:

1. First, the **RV_Gap_Bin-{x-axis}** notebooks will convert all data to log-log values so the slope can be estimated and visualized in log-log scale.

2. They then use the Gap Bin method for group sizes ranging from 1 to 20 and for bin sizes ranging from 10 to 60. In theory, this can generate over 3000 slope data points, but there will be group and bin size combinations where bi-modal Gaussian curves cannot be generated. In general, there will usually be 100 to 2000 data points available for statistical analysis.

3. Next, data outliers are removed using interquartile range (IQR) filtering where we calculate the IQR value. We then take 1.5 times the IQR and subtract this value from 1st quartile (Q1) and add this value to the 3rd quartile (Q3) to establish outlier thresholds. Any data points less than 1.5IQR below Q1 or more than 1.5IQR above Q3 are considered outliers and discarded.

4. We can then use linear regression as a sanity check to get the starting slope and intercept which can be used as an initial guess for step 5.

5. Then use Bayesian methods to estimate the final slope and the associated uncertainties. Bayesian methods are preferred due to the proven accuracy of Affine Invariant Markov Chain Monte Carlo (MCMC) Ensemble sampling used with the $emcee$ Python module. See **RV_Slope_{x-axis}** notebooks, where **{x-axis}** can be **Period**, **Flux** or **Mass**.

6. Finally, overlay the results of the Bayesian method to determine the slope and intercept for the 2D power law equation on the KDE contour plot of the sample planets for each horizontal parameter (i.e., orbital period, insolation flux or stellar mass). See **RV_KDE_Plots** notebook.

7. We also repeat steps 2 through 6 using a filtered sample of stellar masses between 0.8 and 1.2 $M_⊙$ to see if planets with host stars near 1 $M_⊙$ show better alignment to model data or previous observational studies. This can be done by setting **MASS_FILTER = False** for full sample and **MASS_FILTER = True** for filtered sample in the appropriate notebooks.

See the markdown comments at the beginning of each notebook for more details related to that particular notebook.
