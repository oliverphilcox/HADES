import numpy as np
from flipper import *
from hades.params import BICEP
a=BICEP()

if __name__=='__main__':
	""" This is the iterator for batch processing the map creation through HTCondor. Each map is done separately, and argument is map_id."""
	import time
	start_time=time.time()
	import os
	import sys
	
	batch_id=int(sys.argv[1]) # batch_id number
	
	# First load good IDs:
	goodFile=a.root_dir+'%sdeg%sGoodIDs.npy' %(a.map_size,a.sep)
	
	if a.true_lensing:
		outDir=a.root_dir+'LensedPaddedBatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction)
	else:
		outDir=a.root_dir+'PaddedBatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction)
	
	if a.remakeErrors:
		if os.path.exists(outDir+'%s.npy' %batch_id):
			print 'output exists; exiting'
			sys.exit()
	import pickle
	sys.path.append('/data/ohep2/')
	sys.path.append('/home/ohep2/Masters/')
	
	if batch_id<110: # create first time
		from hades.batch_maps import create_good_map_ids
		create_good_map_ids()
		print 'creating good IDs'
		
	goodIDs=np.load(goodFile)
	
	
	if batch_id>len(goodIDs)-1:
		print 'Process %s terminating' %batch_id
		sys.exit() # stop here
	
	map_id=goodIDs[batch_id] # this defines the tile used here
	
	print '%s starting for map_id %s' %(batch_id,map_id)

		
	# Now run the estimation
	#if False: 
	#	from hades.fast_wrapper import padded_wrap
	#	output=padded_wrap(map_id)
	if a.true_lensing:
		from hades.full_lens_wrap import lensed_wrap
		output=lensed_wrap(map_id)
	else:
		from hades.padded_debiased_wrap import padded_wrap
		output=padded_wrap(map_id)
	
	#print output	
	# Save output to file
	if not os.path.exists(outDir): # make directory
		os.makedirs(outDir)
		
	np.save(outDir+'%s.npy' %batch_id, output) # save output
	
	print "Job %s complete in %s seconds" %(batch_id,time.time()-start_time)
	
	if batch_id==len(goodIDs)-2:
		if a.send_email:
			from hades.NoiseParams import sendMail
			sendMail('Debiased Lensed Single Map')



def lensed_wrap(map_id,map_size=a.map_size,\
	sep=a.sep,N_sims=a.N_sims,N_bias=a.N_bias,noise_power=a.noise_power,FWHM=a.FWHM,\
	slope=a.slope,l_step=a.l_step,lMin=a.lMin,lMax=a.lMax,rot=a.rot,freq=a.freq,\
	delensing_fraction=a.delensing_fraction,useTensors=a.useTensors,f_dust=a.f_dust,\
	rot_average=a.rot_average,useBias=a.useBias,padding_ratio=a.padding_ratio,unPadded=a.unPadded,flipU=a.flipU,root_dir=a.root_dir,\
	KKdebiasH2=a.KKdebiasH2,cutFactor=1.35):
	""" Compute the estimated angle, amplitude and polarisation fraction with noise, correcting for bias.
	Noise model is from Hu & Okamoto 2002 and errors are estimated using MC simulations, which are all saved.
	
	Input: map_id (tile number)
	map_size (tile width in degrees)
	sep (separation of tile centres in degrees)
	N_sims (number of MC simulations)
	N_bias (no. sims used for bias computation)
	noise_power (noise power in microK-arcmin)
	FWHM (noise FWHM in arcmin)
	slope (fiducial slope of C_l isotropic dust dependance)
	lMin / lMax (range of ell values to apply the estimators over)
	l_step (step size for binning of 2D spectra)
	rot (angle to rotate by before applying estimators)
	freq (desired map frequency; 150 GHz for BICEP, 353 GHz for Vansyngel)
	delensing_fraction (efficiency of delensing; i.e. 0.1=90% removed)
	useTensors (Boolean, whether to include tensor noise from IGWs with r = 0.1)
	f_dust (factor to reduce mean dust amplitude by - for null testing - default = 1 - no reduction)
	rot_average (Boolean, whether to correct for pixellation error by performing (corrected) map rotations)
	useBias (Boolean, whether to use bias)
	padding_ratio (ratio of padded to unpadded map width >=1)
	flipU (Boolean, whether to flip sign of U-map if in Planck COSMO convention)
	root_dir (home directory)
	
	Output: First 6 values: [estimate,isotropic mean, isotropic stdev] for {A,Afs,Afc,fs,fc,str,ang}
	7th: full data for N_sims as a sequence of 7 lists for each estimate (each of length N_sims)
	8th: full data for N_sims for the monopole bias term
	9th: [estimate,isotropic mean, isotropic stdev] for Hexadecapole power
	10: true monopole (from noiseless simulation) - for testing
	11th: bias (isotropic estimate of <H^2>)
	"""
	print ('Using full lensing')
	print root_dir
	lCut=int(cutFactor*lMax) # maximum ell for Fourier space maps
	
	# First compute B-mode map from padded-real space map with desired padding ratio. Also compute the padded window function for later use
	from .PaddedPower import MakePowerAndFourierMaps,DegradeMap,DegradeFourier
	fBdust,padded_window,unpadded_window=MakePowerAndFourierMaps(map_id,padding_ratio=padding_ratio,map_size=map_size,sep=sep,freq=freq,fourier=True,power=False,returnMasks=True,flipU=flipU,root_dir=root_dir)
			
	# Also compute unpadded map to give binning values without bias
	unpadded_fBdust=MakePowerAndFourierMaps(map_id,padding_ratio=1.,map_size=map_size,sep=sep,freq=freq,fourier=True,power=False,returnMasks=False,flipU=flipU,root_dir=root_dir)
	unpadded_fBdust=DegradeFourier(unpadded_fBdust,lCut) # remove high ell pixels	
	fBdust=DegradeFourier(fBdust,lCut) # discard high-ell pixels
	padded_window=DegradeMap(padded_window.copy(),lCut) # remove high-ell data
	unpadded_window=DegradeMap(unpadded_window.copy(),lCut)
	
	if a.hexTest:
		# TESTING - replace fourier B-mode from dust with random isotropic realisation of self
		powDust=fftTools.powerFromFFT(fBdust) # compute power
		from .PowerMap import oneD_binning
		ll,pp=oneD_binning(powDust.copy(),10,lCut,l_step,binErr=False,exactCen=False) # compute one-D binned spectrum
		from .PaddedPower import fourier_noise_test
		fBdust,unpadded_fBdust=fourier_noise_test(padded_window,unpadded_window,ll,pp,padding_ratio=padding_ratio,unpadded=False,log=True)
		#fBdust.kMap=fill_from_Cell(fBdust.copy(),ll,pp,fourier=True,power=False) # generate Gaussian realisation
	
	if a.test_fix_A:
		print 'fixAtest'
		def test_pow(ell,ang,fs=0.8,fc=0.7,A=1e-10):
    			ang=ang*np.pi/180.
    			return A*(1.+ell)**(-2.42)*(1-fs*np.sin(4.*ang)-fc*np.cos(4.*ang))
		# Overwrite with fixed dust amplitude + fs,fc
		from scipy.stats import norm
		var=test_pow(fBdust.modLMap,fBdust.thetaMap)
		fBdust.kMap=norm.rvs(loc=0.,scale=var/2.)+norm.rvs(loc=0.,scale=var/2.)*1.0j
		var=test_pow(unpadded_fBdust.modLMap,unpadded_fBdust.thetaMap)
		unpadded_fBdust.kMap=norm.rvs(loc=0.,scale=var/2.)+norm.rvs(loc=0.,scale=var/2.)*1.0j

	#return powDust,fBdust,unpadded_fBdust
	# Reduce dust amplitude by 'dedusting fraction'
	unpadded_fBdust.kMap*=f_dust
	fBdust.kMap*=f_dust
	
	# Compute <W^2>^2 / <W^4> - this is a necessary correction for the H^2 quantities (since 4-field quantities)
	wCorrection = np.mean(padded_window.data**2.)**2./np.mean(padded_window.data**4.)
	
	# Input directory:
	inDir=root_dir+'%sdeg%s/' %(map_size,sep)
	
	# Compute fourier space lensing map:
	from .lens_power import MakeFourierLens2
	fourier_lens=MakeFourierLens2(map_id,padding_ratio=padding_ratio,map_size=map_size,sep=sep,\
			fourier=True,power=False,delensing_fraction=delensing_fraction)
 	unpadded_lens=MakeFourierLens2(map_id,padding_ratio=1.,map_size=map_size,sep=sep,\
 			fourier=True,power=False,delensing_fraction=delensing_fraction)
	fourier_lens=DegradeFourier(fourier_lens,lCut) # discard high-ell pixels
	unpadded_lens=DegradeFourier(unpadded_lens,lCut) # discard high-ell pixels
	
	# First compute the total noise (instrument+tensors)
	from .NoisePower import noise_model,r_Cl
	
	if useTensors: # include r = 0.1 estimate
		Cl_r_func=r_Cl()
		def total_Cl_noise(l):
			return noise_model(l,FWHM=FWHM,noise_power=noise_power)+Cl_r_func(l)
	else:
		def total_Cl_noise(l): # this DOESN'T include lensing here
			return noise_model(l,FWHM=FWHM,noise_power=noise_power)
	
	# Now create a fourier space noise map	
	from .PaddedPower import fourier_noise_map
	ellNoise=np.arange(5,lCut) # ell range for noise spectrum
	
	from .RandomField import fill_from_model
	#fourierNoise=fourier_noise_map
	
	from .PaddedPower import fourier_noise_test
	fourierNoise,unpadded_noise=fourier_noise_test(padded_window,unpadded_window,ellNoise,total_Cl_noise(ellNoise),padding_ratio=padding_ratio,unpadded=False,log=a.log_noise)
	
	from .lens_power import ffp10_lensing
	Cl_lens_func=ffp10_lensing(delensing_fraction=delensing_fraction) # function for lensed Cl
	
	#unpadded_noise=unpadded_fBdust.copy() # this map is generated completely in Fourier space to avoid errors
	#unpadded_noise.kMap=fill_from_model(unpadded_fBdust.copy(),total_Cl_noise,fourier=True,power=False)
	#fourierNoise=fourier_noise_map(padded_window.copy(),unpadded_window.copy(),ellNoise,total_Cl_noise(ellNoise),padding_ratio=padding_ratio,unpadded=False)
	#fourierNoise,unpadded_noise=fourier_noise_map(padded_window.copy(),unpadded_window.copy(),ellNoise,total_Cl_noise(ellNoise),padding_ratio=padding_ratio,unpadded=True)
	#return fourierNoise,unpadded_noise#,unpadded_noise2
	#return fftTools.powerFromFFT(fourierNoise)
	
	#return fourierNoise,unpadded_noise
	
	# Compute total map from DUST + NOISE + LENSING
	totFmap=fBdust.copy()
	totFmap.kMap+=fourierNoise.kMap+fourier_lens.kMap # for total B modes
	unpadded_totFmap=unpadded_fBdust.copy()
	unpadded_totFmap.kMap+=unpadded_noise.kMap+unpadded_lens.kMap
	
	
	# Now convert to power-space
	totPow=fftTools.powerFromFFT(totFmap) # total power map
	Bpow=fftTools.powerFromFFT(fBdust) # dust only map
	unpadded_totPow=fftTools.powerFromFFT(unpadded_totFmap)
	
	
	del fourierNoise,unpadded_noise,fourier_lens,unpadded_lens
	
	if unPadded: # only use unpadded maps here
		totFmap=unpadded_totFmap
		totPow=unpadded_totPow
		padded_window=unpadded_window
				
	# Compute true amplitude using ONLY dust map
	from .KKdebiased import derotated_estimator
	p=derotated_estimator(Bpow.copy(),map_id,lMin=lMin,lMax=lMax,slope=slope,factor=None,FWHM=0.,\
			noise_power=1.e-400,rot=rot,delensing_fraction=0.,useTensors=False,debiasAmplitude=False,\
			rot_average=rot_average,KKdebiasH2=False,true_lensing=True)
	trueA=p[0]
	del Bpow		
	
	#return totPow,trueA
	
	# Compute rough semi-analytic C_ell spectrum
	def analytic_model(ell,A_est,slope):
		"""Use the estimate for A to construct analytic model.
		NB: This is just used for finding the centres of the actual binned data.
		"""
		return total_Cl_noise(ell)+Cl_lens_func(ell)+A_est*ell**(-slope)
	
	# Compute anisotropy parameters
	A_est,fs_est,fc_est,Afs_est,Afc_est,finalFactor=derotated_estimator(totPow.copy(),map_id,lMin=lMin,\
		lMax=lMax,slope=slope,factor=None,FWHM=FWHM,noise_power=noise_power,rot=rot,\
		delensing_fraction=delensing_fraction,useTensors=useTensors,debiasAmplitude=True,\
		rot_average=rot_average,KKdebiasH2=KKdebiasH2,true_lensing=True)
	# (Factor is expected monopole amplitude (to speed convergence))
	
	## Run MC Simulations	
	
	# Compute 1D power spectrum by binning in annuli
	from .PowerMap import oneD_binning
	if a.padded_1D_spectrum:
		l_cen,mean_pow = oneD_binning(totPow.copy(),lMin,lCut,l_step,binErr=False,exactCen=a.exactCen,\
					C_ell_model=analytic_model,params=[A_est,slope])
	else:
		l_cen,mean_pow = oneD_binning(unpadded_totPow.copy(),lMin*padding_ratio,lCut,l_step*padding_ratio,binErr=False,exactCen=a.exactCen,\
					C_ell_model=analytic_model,params=[A_est,slope]) 
	#l_cen,mean_pow=oneD_binning(totPow.copy(),lMin,lCut,l_step,binErr=False,exactCen=a.exactCen,C_ell_model=analytic_model,params=[A_est,slope])
	# gives central binning l and mean power in annulus using window function corrections 
	
	# Create spline fit
	from scipy.interpolate import UnivariateSpline
	spl=UnivariateSpline(l_cen,np.log(mean_pow),k=5)
	def spline(ell):
		return np.exp(spl(ell))
	#del l_cen,mean_pow
	
	# Precompute useful data:
	from hades.RandomField import precompute
	precomp=precompute(padded_window.copy(),spline,lMin=lMin,lMax=lMax)
	
	#from .RandomField import padded_fill_from_Cell
	#fBias=padded_fill_from_Cell(padded_window.copy(),l_cen,mean_pow,lMin=lMin)#,padding_ratio=padding_ratio)
	##bias_cross=fftTools.powerFromFFT(fBias.copy(),totFmap.copy()) # cross map
	#bias_self=fftTools.powerFromFFT(fBias.copy()) # self map
	#return bias_self,l_cen,mean_pow		
		
	# First compute the bias factor
	from .RandomField import padded_fill_from_Cell
	#all_sims=[]
	if useBias:
		bias_data=np.zeros(N_bias)
		for n in range(N_bias):
			if n%100==0:
				print 'Computing bias sim %s of %s' %(n+1,N_bias)
			fBias=padded_fill_from_Cell(padded_window.copy(),l_cen,mean_pow,lMin=lMin,unPadded=unPadded,precomp=precomp)#,padding_ratio=padding_ratio)
			bias_cross=fftTools.powerFromFFT(fBias.copy(),totFmap.copy()) # cross map
			bias_self=fftTools.powerFromFFT(fBias.copy()) # self map
			# First compute estimators on cross-spectrum
			cross_ests=derotated_estimator(bias_cross.copy(),map_id,lMin=lMin,lMax=lMax,slope=slope,\
							factor=finalFactor,FWHM=FWHM,noise_power=noise_power,\
							rot=rot,delensing_fraction=delensing_fraction,useTensors=useTensors,\
							debiasAmplitude=False,rot_average=rot_average,KKdebiasH2=False,true_lensing=True)
			self_ests=derotated_estimator(bias_self.copy(),map_id,lMin=lMin,lMax=lMax,slope=slope,\
							factor=finalFactor,FWHM=FWHM,noise_power=noise_power,\
							rot=rot,delensing_fraction=delensing_fraction,useTensors=useTensors,\
							debiasAmplitude=True,rot_average=rot_average,KKdebiasH2=KKdebiasH2,true_lensing=True)
			bias_data[n]=(-1.*(self_ests[3]**4.+self_ests[4]**2.)+4.*(cross_ests[3]**2.+cross_ests[4]**2.))*wCorrection
		# Now compute the mean bias - this debiases the DATA only
		bias=np.mean(bias_data)
		del bias_self,bias_cross
	else:
		print 'No bias subtraction'
		bias=0.
			
	## Now run the MC sims proper:
	# Initialise arrays
	A_MC,fs_MC,fc_MC,Afs_MC,Afc_MC,epsilon_MC,ang_MC,HexPow2_MC=[np.zeros(N_sims) for _ in range(8)]
	#MC_map=totPow.copy() # template for SIM-SIM data
	
	for n in range(N_sims): # for each MC map
		if n%100==0:
			print('MapID %s: Starting simulation %s of %s' %(map_id,n+1,N_sims))
		# Create the map with a random implementation of Cell
		fourier_MC_map=padded_fill_from_Cell(padded_window.copy(),l_cen,mean_pow,lMin=lMin,unPadded=unPadded,precomp=precomp)
		MC_map=fftTools.powerFromFFT(fourier_MC_map.copy()) # create power domain map
		
		# Now use the estimators on the MC sims
		output=derotated_estimator(MC_map.copy(),map_id,lMin=lMin,lMax=lMax,\
			slope=slope,factor=finalFactor,FWHM=FWHM,noise_power=noise_power,\
			rot=rot, delensing_fraction=delensing_fraction,useTensors=useTensors,\
			debiasAmplitude=True,rot_average=rot_average,KKdebiasH2=KKdebiasH2,true_lensing=True) 
		
		# Compute MC anisotropy parameters  
		A_MC[n]=output[0]
		fs_MC[n]=output[3]/output[0]
		fc_MC[n]=output[4]/output[0]
		Afs_MC[n]=output[3] # these are fundamental quantities here
		Afc_MC[n]=output[4]
		epsilon_MC[n]=np.sqrt((output[3]**2.+output[4]**2.)*wCorrection)/output[0] # NOT corrected for bias in <H^2>
		ang_MC[n]=0.25*180./np.pi*np.arctan2(output[3],output[4]) # NB: this is not corrected for bias
		HexPow2_MC[n]=(output[3]**2.+output[4]**2.)*wCorrection 
	if useBias:	
		isoBias=np.mean(HexPow2_MC)
		HexPow2_MC-=isoBias*np.ones_like(HexPow2_MC) # remove the bias (i.e. mean of H^2 from all sims)
	else:
		isoBias=0.
		
	print 'MC sims complete'	
	
	del fourier_MC_map,MC_map,totFmap,unpadded_totFmap,totPow,unpadded_totPow,padded_window,unpadded_window # delete unneeded variables
	
	# Regroup data
	allMC=[A_MC,fs_MC,fc_MC,Afs_MC,Afc_MC,epsilon_MC,ang_MC,HexPow2_MC]
	
	# Compute anisotropy fraction and angle from data
	ang_est=0.25*180./np.pi*(np.arctan2(Afs_est,Afc_est)) # in degrees (already corrected for rotation) - NB: not debiased
	frac_est=np.sqrt((Afs_est**2.+Afc_est**2.)*wCorrection)/A_est # BIASED sqrt(<H^2>)/A
	HexPow2_est=(Afs_est**2.+Afc_est**2.)*wCorrection-bias # estimated hexadecapolar power - debiased + corrected for <W^4>
	
	# Compute means and standard deviations
	A_mean=np.mean(A_MC)
	A_std=np.std(A_MC)
	fc_mean=np.mean(fc_MC)
	fs_mean=np.mean(fs_MC)
	fc_std=np.std(fc_MC)
	fs_std=np.std(fs_MC)
	frac_mean=np.mean(epsilon_MC)
	frac_std=np.std(epsilon_MC)
	ang_mean=np.mean(ang_MC)
	ang_std=np.std(ang_MC)
	HexPow2_mean=np.mean(HexPow2_MC)
	HexPow2_std=np.std(HexPow2_MC)
	Afs_mean=np.mean(Afs_MC)
	Afc_mean=np.mean(Afc_MC)
	Afs_std=np.std(Afs_MC)
	Afc_std=np.std(Afc_MC)
	
	# Regroup data
	Adat=[A_est,A_mean,A_std]
	fsdat=[fs_est,fs_mean,fs_std]
	fcdat=[fc_est,fc_mean,fc_std]
	Afsdat=[Afs_est,Afs_mean,Afs_std]
	Afcdat=[Afc_est,Afc_mean,Afc_std]
	fracdat=[frac_est,frac_mean,frac_std] # hexadecapolar anisotropy fraction (epsilon)
	angdat=[ang_est,ang_mean,ang_std] # anisotropy angle
	HexPow2dat=[HexPow2_est,HexPow2_mean,HexPow2_std] # hexadecapole amplitude
	
	# Return all output
	return Adat,fsdat,fcdat,Afsdat,Afcdat,fracdat,angdat,allMC,[],HexPow2dat,trueA,bias,wCorrection,isoBias # (empty set to avoid reordering later code)

