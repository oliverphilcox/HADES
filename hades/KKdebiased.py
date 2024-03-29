import numpy as np
from hades.params import BICEP
a=BICEP()

def derotated_estimator(map,map_id,lMin=a.lMin,lMax=a.lMax,FWHM=a.FWHM,noise_power=a.noise_power,\
    slope=a.slope,factor=None,rot=0.,delensing_fraction=a.delensing_fraction,useTensors=a.useTensors,\
    debiasAmplitude=True,rot_average=a.rot_average,correct=True,OtherClMap=None,KKdebiasH2=a.KKdebiasH2,true_lensing=False):
    """Use modified KK14 estimators to compute polarisation hexadecapole amplitude and angle via Afs,Afc parameters.
    This uses the noise model in hades.NoisePower.noise_model.
    A is computed recursively, since the S/N ratio depends on it (weakly).
    Rotation is performed to account for the effect of pixellation.
    
    Inputs: map (in power-space)
    map_size = width of map in degrees
    lMin,lMax= fitting range of l
    slope -> fiducial C_l map slope
    rot -> optional angle for pre-rotation of power-space map in degrees.
    delensing_fraction -> efficiency of delensing (0.1-> 90% removed)
    factor -> expected amplitude factor (to speed convergence)
    useTensors -> Boolean whether to include r = 0.1 tensor modes from IGWs
    debiasAmplitude -> Boolean whether to subtract noise+lensing C_l for estimation of A - this is ONLY for A
    rot_average -> Whether to average over rotations to correct for pixellation (NB: this does not change mean(Afs))
    correct -> TESTING - whether to correct for angle rotation (default = True)
    true_lensing -> if true use FFP10 lensing map B-mode spectrum rather than default CAMB spectrum
    
    Outputs:
    A,fs,fc, Afs, Afc from estimators. NB these are corrected for map rotation.
    """
    snp=2.
	    
    # Compute relevant pixels and mod-l maps
    goodPix=np.where((map.modLMap.ravel()>lMin)&(map.modLMap.ravel()<lMax)) # pixels in correct range
    
    lMap=map.modLMap.ravel()[goodPix] # |ell|
    PowerMap=map.powerMap.ravel()[goodPix] # B-mode biased power
    
    if not isinstance(OtherClMap,np.ndarray):
    	from hades.NoisePower import lensed_Cl,r_Cl,noise_model
    	#Define total noise
	def Cl_total_noise_func(l):
		"""This is total C_l noise from lensing, B-modes and experimental noise"""
	        if true_lensing:
	        	from .lens_power import ffp10_lensing
	        	Cl_lens_func=ffp10_lensing(delensing_fraction=delensing_fraction)
	        else:
	        	Cl_lens_func=lensed_Cl(delensing_fraction=delensing_fraction)
	        if useTensors:
	            Cl_r_func=r_Cl()
	            return Cl_lens_func(l)+Cl_r_func(l)+noise_model(l,FWHM=FWHM,noise_power=noise_power)
	        else:
	            return Cl_lens_func(l)+noise_model(l,FWHM=FWHM,noise_power=noise_power)
	OtherClMap=Cl_total_noise_func(lMap) # extra C_l power from lensing + noise (+ tensor modes)
    
    if debiasAmplitude:
    	debiasedPowerMap=PowerMap-OtherClMap # power estimate only due to dust
    else:
    	debiasedPowerMap=PowerMap
    fiducialClMap=lMap**(-slope) # fiducial Cl
    
    if factor==None:
        # If no estimate for monopole amplitude, compute this recursively (needed in SNR)
        # A only weakly depends on the SNR so convergence is usually quick
        N=0
        if a.f_dust>0.:
        	Afactor=1e-12*a.f_dust**2. # initial estimate
        else:
        	Afactor=1e-16 # some arbitrary small value

        while N<20: # max no. iterations
            SNMap = (Afactor*fiducialClMap)/(Afactor*fiducialClMap+OtherClMap) # SN ratio

            # Compute estimate for A
            Anum=np.sum(debiasedPowerMap*(SNMap**snp)/fiducialClMap)
            Aden=np.sum(SNMap**snp)

            # Now record output
            lastFactor=Afactor
            Afactor=Anum/Aden
            
            # Stop if approximate convergence (1%) reached
            if np.abs((Afactor-lastFactor)/Afactor)<0.01:
                break
            N+=1

        if N==20:
            print 'Map %s did not converge with slope: %.3f, Afactor %.3e, last factor: %.3e' %(map_id,slope,Afactor,lastFactor)
        finalFactor=Afactor
        
    else:
        finalFactor=factor # just use the A estimate from input      
    
    if a.fixFactor:
	finalFactor=1.6e-12*a.f_dust**2.

    # Now compute A,Afs,Afc (recompute A s.t. all best estimators use same SNR)
    SNmap=(finalFactor*fiducialClMap)/(finalFactor*fiducialClMap+OtherClMap) # signal-to-noise ratio
    # Now compute estimate for A
    Anum=np.sum(debiasedPowerMap*(SNmap**snp)/fiducialClMap) # noise-debiased
    Aden=np.sum(SNmap**snp)
    A=Anum/Aden
    
    if rot_average:
    	all_rot = np.linspace(0.,45.,20)
    else:
    	all_rot=[rot] # just a single value
    Afs,Afc,fs,fc=[np.zeros_like(all_rot) for _ in range(4)]
    angGood=map.thetaMap.ravel()[goodPix]*np.pi/180.
    angOnes=np.ones_like(angGood)*np.pi/180.
    if KKdebiasH2:
    	PM=debiasedPowerMap.copy()
    else:
    	PM=PowerMap.copy()
    tempMap=PM*(SNmap**snp)/fiducialClMap
    from .KKdebiased import rotation_corrector
    for r,rot in enumerate(all_rot):
    	angMap=angGood+rot*angOnes # angle in radians
	cosMap=np.cos(4.*angMap) # map of cos(4theta)
	sinMap=np.sin(4.*angMap)
	# Now estimate Afs, Afc
	Afcnum=np.sum(tempMap*cosMap) # cosine coeff - NOT using debiased maps else introduces bias
	Afcden=np.sum((SNmap**snp)*(cosMap**2.))
	Afsnum=np.sum(tempMap*sinMap) # sine coeff 
	Afsden=np.sum((SNmap**snp)*(sinMap**2.))
	Afc_est=Afcnum/Afcden
	Afs_est=Afsnum/Afsden
	# Now correct for map rotation:
	rot_rad=rot*np.pi/180. # angle of rotation in radians
	if correct:
		Afs[r],Afc[r]=rotation_corrector(rot_rad*4.,Afs_est,Afc_est)
	else:
		Afs[r],Afc[r]=Afs_est,Afc_est
    
    # Now compute mean values
    Afs_corr=np.mean(Afs)
    Afc_corr=np.mean(Afc)
    fs_corr=Afs_corr/A # these are less reliable due to errors in both Afs and A
    fc_corr=Afc_corr/A 
    
    if factor==None:
    	return A,fs_corr,fc_corr,Afs_corr,Afc_corr,finalFactor # to save finalFactor if different to A
    else:
        return A,fs_corr,fc_corr,Afs_corr,Afc_corr


def rotation_corrector(angle,sin_field,cos_field):
	""" Correct for rotation using given angle (in radians)"""
	sin_corr=sin_field*np.cos(angle)-cos_field*np.sin(angle)
	cos_corr=sin_field*np.sin(angle)+cos_field*np.cos(angle)
	return sin_corr,cos_corr
