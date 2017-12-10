import numpy as np

class BICEP:
	""" Class containing (mostly) essential model parameters for KK estimators using BICEP data"""
	
	root_dir = '/data/ohep2/BICEP2/' # '/data/ohep2/sims/'# root directory for simulations
	
	map_size =  3 # Width of each map
	N_sims = 1#100 # Number of MC sims
	l_step = 100.#100#100 # width of binning in l-space for power spectr
	lMin = 100.
	lMax = 2000. # ranges to fit spectrum over 
	
	sep = 0.5#'0.5 # separation of map centres
	
	
	# Noise model
	FWHM = 10#10. #'10. # full width half maximum of beam in arcmin
	noise_power = 100.000000#100.000000 # noise power of BICEP -> in microK-arcmin
	
	# Fiducial C_l
	slope=2.22#3.0 # C_l^f power law slope
	
	# If run analyis for different noise powers
	NoiseAnalysis = True# 
	ComparisonSetting='noise_power'#'noise_power'# must be in ['FWHM','noise_power']
	NoisePowerLists = np.logspace(0,2,5)#np.logspace(-2,2,5) # 0.01 to 100 range
	FWHM_lists=[0, 10, 20, 30, 40, 50]
