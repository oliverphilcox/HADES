from .params import BICEP
a=BICEP()

from flipper import *
import numpy as np

def est_and_err(map_id,map_size=a.map_size,N_sims=a.N_sims,noise_power=a.noise_power,FWHM=a.FWHM,slope=a.slope):
	""" Compute the estimated angle, amplitude and polarisation strength in the presence of noise, following Hu & Okamoto 2002 noise model. Error is from MC simulations.
	Output: list of data for A, fs, fc (i.e. output[0]-> A etc.), with structure [map estimate, MC_standard_deviation, MC_mean]
	"""
	# First calculate the B-mode map (noiseless)
	from .PowerMap import MakePower
	Bpow=MakePower(map_id,map_size=map_size,map_type='B')
	
	# Now compute the noise power-map
	from .NoisePower import noise_map
	noiseMap=noise_map(powMap=Bpow.copy(),noise_power=a.noise_power,FWHM=a.FWHM)
	
	# Compute total map
	totMap=Bpow.copy()
	totMap.powerMap=Bpow.powerMap+noiseMap.powerMap
	
	# Initially using NOISELESS estimators
	from .KKtest import noisy_estimator
	est_data=noisy_estimator(totMap.copy(),slope=slope) # compute anisotropy parameters
		
	## Run MC Simulations	
	# First compute 1D power spectrum by binning in annuli
	from hades.PowerMap import oneD_binning
	l_cen,mean_pow = oneD_binning(totMap.copy(),0.8*a.lMin,1.5*a.lMax,0.8*a.l_step,binErr=False) # gives central binning l and mean power in annulus
	
	# Compute univariate spline model fit to 1D power spectrum
	from scipy.interpolate import UnivariateSpline
	spline_fun = UnivariateSpline(np.log10(l_cen),np.log10(mean_pow),k=4) # compute spline of log data
	
	def model_power(ell):
		return 10.**spline_fun(np.log10(ell)) # this estimates 1D spectrum for any ell
	
	if False: # testing
		import matplotlib.pyplot as plt
		plt.plot(l_cen,np.log10(mean_pow))
		plt.plot(l_cen,np.log10(model_power(l_cen)))
		plt.show()
	
	# Now run MC simulation N_sims times
	MC_data = np.zeros((N_sims,len(est_data)))
	
	for n in range(N_sims): # for each MC map
		MC_map=single_MC(totMap.copy(),model_power) # create random map from isotropic spectrum
		MC_data[n]=noisy_estimator(MC_map.copy(),slope=slope) # compute MC anisotropy parameters  
	
	# Compute mean and standard deviation of MC statistics
	MC_means=np.mean(MC_data,axis=0)
	MC_std=np.std(MC_data,axis=0)	

	# Regroup output (as described above)
	output = [[est_data[i],MC_std[i],MC_means[i]] for i in range(len(MC_means))]		
	
	return output
	
	
def single_MC(tempMap,model_power):
	""" Compute a Monte Carlo random map, created from a Gaussian isotropic spectrum.
	Inputs: tempMap -> template power-domain map
	model_power -> model function for C_l(ell) (including noise)
	
	Output -> MC random map as a two-dimensional power-map
	"""
	
	template=tempMap.copy() # to avoid overwriting data file
	
	# Create data array		
	data = np.ones_like(template.powerMap)*1e-30 # setting negiligible value for pixels out of range
	
	# Compute the power map based on Gaussian random distributions for each pixel.
	for i in range(len(data)):
		for j in range(len(data[i])):
			l = template.modLMap[i][j] # (modulus of l)
			if l>0.5*a.lMin and l<1.5*a.lMax: # if in correct range
				var = model_power(l) # variance of model-power
				amplitude = np.random.normal(loc=0.0,scale=np.sqrt(var)) # random amplitude from Gaussian
				# NB: phase term vanishes when power-map is constructed from FFT
				data[i,j] = amplitude**2.0 # (real by construction)
	template.powerMap=data
	
	return template
	

def noise_model(l,FWHM=a.FWHM,noise_power=a.noise_power):
	""" Noise model of Hu & Okamoto 2002. 
	Inputs: l, 
	Full-Width-Half-Maximum of experiment in arcminutes, 
	noise-power (Delta_P) in microK-arcmin.
	
	Unit conversions are done to put output in K^2 
	-> to match input maps in K_CMB. """
	# NB: Check dimensions
	
	#T_CMB = 2.728e6 # in microK
	FWHM_rad=FWHM/60.*np.pi/180. # in radians
	noise_power_rad_K=1.0e-6*noise_power/60.*np.pi/180. # in K-rad'
	
	exponent=l*(l+1.)*FWHM_rad**2. / (8.*np.log(2.))
	Cl_K = (noise_power_rad_K)**2.*np.exp(exponent) # Cl is in K^2-rad
	return Cl_K
	
def noise_map(realMap=None,powMap=None,lMin=a.lMin,lMax=a.lMax,FWHM=a.FWHM,noise_power=a.noise_power):
	""" Create a Gaussian random noise power map from a given noise profile.
	
	NB: either real OR power map needs to be specified as template (power map faster)
	
	Inputs: realMap -> real space map to use as template
	powMap -> power2D space map to use as a template
	lMin/lMax -> l-range to create map over (matching that for estimators)
	FWHM/noise_power -> noise parameters (see noise_model() )
	
	Output: power2D instance with Gaussian random noise power matching given C_l	
	"""
	from .NoisePower import noise_model
	
	if powMap==None:
		if realMap!=None:
			powerMap=fftTools.powerFromLiteMap(realMap)
		else:
			raise Exception('Error: Need Input Template Map')
	else:
		powerMap=powMap.copy() # to avoid rewriting
			
	data = np.ones_like(powerMap.powerMap)*1.e-30 # for pixels out of range
	
	for i in range(len(data)):
		for j in range(len(data[i])):
			l = powerMap.modLMap[i][j] # (modulus of l)
			if l>0.5*lMin and l<1.5*lMax: # if in correct range
				var = noise_model(l,FWHM=FWHM,noise_power=noise_power) # Gaussian variance = C_l^{noise}
				amplitude = np.random.normal(loc=0.0,scale=np.sqrt(var)) # random 
				# NB: phase term vanishes when power-map is constructed from FFT
				data[i,j] = amplitude**2.0 # (real by construction)
	powerMap.powerMap=data
	
	return powerMap
	
def reconstructor(map_size=a.map_size,sep=a.sep):
	""" Code to plot the noise-estimator data for the BICEP patch, assuming a flat-sky. 
	Inputs: map_size and centre separation.
	Outputs: plots saved in NoisySkyMaps/ subdirectory."""
	# Load in dataset
	dat = np.load(a.root_dir+'%sdeg%s/NoisyMCestimates%sdeg%s.npy' %(map_size,sep,map_size,sep))
	N = len(dat)
	
	# Construct A,fs,fc arrays
	A=[d[0][0] for d in dat]
	fs=[d[1][0] for d in dat]
	fc=[d[2][0] for d in dat]
	A_err=[d[0][1] for d in dat]
	fs_err=[d[1][1] for d in dat]
	fc_err=[d[2][1] for d in dat]
	
	# Compute angles and anisotropy fractions
	ang=[0.25*np.arctan(fs[i]/fc[i])*180./np.pi for i in range(N)]
	frac=[np.sqrt(fs[i]**2+fc[i]**2) for i in range(N)]
	
	def ani_frac_err(fs,fc,sig_fs,sig_fc): # error in fraction 
    		return np.sqrt(((sig_fs*fs)**2+(sig_fc*fc)**2)/(fs**2+fc**2))
    
    	def angle_err(fs,fc,sig_fs,sig_fc): # error in angle in degrees
    		return 1./4*np.sqrt(((fs*sig_fc)**2+(fc*sig_fs)**2)/(fs**2+fc**2))*180./np.pi
	
	ang_err=[angle_err(fs[i],fc[i],fs_err[i],fc_err[i]) for i in range(N)]
	frac_err=[ani_frac_err(fs[i],fc[i],fs_err[i],fc_err[i]) for i in range(N)]
	
	# Compute significances
	dat_set=[A,frac,ang,fs,fc]
	dat_errs=[A_err,frac_err,ang_err,fs_err,fc_err]
	
	dat_sig=[]
	for i in range(len(dat_set)):
		dat_sig.append([dat_set[i][j]/dat_errs[i][j] for j in range(N)])
	dat_set+=dat_sig
	
	log_A_est=np.log10(A)
	dat_set.append(log_A_est)
	
	# Load coordinates of patch centres
	from .NoisePower import good_coords
	ra,dec=good_coords(map_size,sep,N)
	
    	# Make output directory
    	import os
    	outDir=a.root_dir+'NoisySkyMaps%sdeg%s/' %(map_size,sep)
    
    	if not os.path.exists(outDir):
    		os.mkdir(outDir)
    
    	# Now plot on grid:
    	import matplotlib.pyplot as plt
    	names = ['Monopole Amplitude','Anisotropy Fraction','Polarisation Angle','fs','fc','Amplitude Significance',\
    	'Anisotropy Fraction Significance','Angle Significance','fs Significance','fc Significance','log Monopole Amplitude']
    	name_str=['A_est','frac_est','ang_est','fs','fc','A_sig','frac_sig','ang_sig','fs_sig','fc_sig','log_A_est']
    	
    	for j in range(len(names)):
    		plt.figure()
    		plt.scatter(ra,dec,c=dat_set[j],marker='o',s=80)
    		plt.title(names[j])
    		plt.colorbar()
    		plt.savefig(outDir+name_str[j]+'.png',bbox_inches='tight')
    		plt.clf()
    		plt.close()
    	
def good_coords(map_size,sep,N):
	""" Compute RA/dec coordinates in correct patch.
	Output is RA,dec in degrees. N is no. data points
	 """
	import pickle
	map_dir=a.root_dir+'%sdeg%s/' %(map_size,a.sep)
    	full_ras=pickle.load(open(map_dir+'fvsmapRas.pkl','rb'))
    	full_decs=pickle.load(open(map_dir+'fvsmapDecs.pkl','rb'))
    	goodMap=pickle.load(open(map_dir+'fvsgoodMap.pkl','rb'))
    	ras=[full_ras[i] for i in range(len(full_ras)) if goodMap[i]!=False]
    	decs=[full_decs[i] for i in range(len(full_decs)) if goodMap[i]!=False]
    	ras=ras[:N]
    	decs=decs[:N] # remove any extras
    	
    	import astropy.coordinates as coords
    	import astropy.units as u
    	
    	ra_deg=coords.Angle(ras*u.degree) # convert to correct format
    	ra_deg=ra_deg.wrap_at(180.*u.degree)
    	dec_deg=coords.Angle(decs*u.degree)

	return ra_deg,dec_deg
	
