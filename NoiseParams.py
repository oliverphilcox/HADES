import numpy as np
from hades.params import BICEP
a=BICEP()

def create_params(map_size=a.map_size,sep=a.sep):
	""" Create parameter space + map_id grid for batch processing."""
	# Load in good map IDs;
	goodMaps=np.load(a.root_dir+'%sdeg%sGoodIDs.npy' %(map_size,sep))
	
	# Create meshed list of all parameters
	ID,NP,FW=np.meshgrid(goodMaps,a.noi_par_NoisePower,a.noi_par_FWHM)
	
	# Save output
	np.savez(a.root_dir+'%sdeg%sBatchNoiseParams.npz' %(map_size,sep),map_id=ID.ravel(),noise_power=NP.ravel(),FWHM=FW.ravel())
	
	

if __name__=='__main__':
	""" Code to create data for some noise parameters defined in param file to plot output epsilon against """
	import time
	start_time=time.time()
	import sys
	import os
	index=int(sys.argv[1])
	
	# First load in parameters
	from hades.NoiseParams import create_params
	create_params()
	paramFile=np.load(a.root_dir+'%sdeg%sBatchNoiseParams.npz' %(a.map_size,a.sep))
	map_id=paramFile['map_id'][index]
	noise_power=paramFile['noise_power'][index]
	FWHM=paramFile['FWHM'][index]
	length=len(paramFile['FWHM']) # total number of processes
	paramFile.close()
	
	# Now compute the estimators:
	from hades.wrapper import best_estimates
	output=best_estimates(map_id,FWHM=FWHM,noise_power=noise_power)
	
	eps_est=output[5][0] # just estimate
	eps_MC=output[7][5] # all MC values
	ang_est=output[6][0] # angle
	A_est=output[0][0] # monopole amplitude
	A_MC=output[7][0] # MC amplitude
	
	# Save output to file:
	outDir=a.root_dir+'NoiseParamsBatch/'
	if not os.path.exists(outDir):
		os.makedirs(outDir)
		
	# Just save the epsilon estimate and MC values to reduce file space
	np.savez(outDir+'id%s_fwhm%s_power%s.npz' %(map_id,FWHM,noise_power),\
	eps=eps_est,eps_MC=eps_MC,ang=ang_est,A=A_est,A_MC=A_MC)
	
	print 'Job %s of %s complete in %s seconds' %(index+1,length,time.time()-start_time)
	
	
def reconstruct_epsilon(map_size=a.map_size,sep=a.sep):
	import os
	""" Create a 2D array of epsilon for noise parameter data."""
	# First load in all iterated parameters
	paramFile=np.load(a.root_dir+'%sdeg%sBatchNoiseParams.npz' %(map_size,sep))
	
	# Initialise output array
	eps_num=np.zeros([len(a.noi_par_NoisePower),len(a.noi_par_FWHM)]) # numerator
	norm=np.zeros_like(eps_num) # normalisation
	fwhm_arr=np.zeros_like(eps_num) # array of FWHM for plotting
	power_arr=np.zeros_like(eps_num) # noise power values
	
	# For MC values:
	eps_MC_num=np.zeros([len(a.noi_par_NoisePower),len(a.noi_par_FWHM),a.N_sims])
	norm_MC=np.zeros_like(eps_MC_num)
	
	inDir=a.root_dir+'NoiseParamsBatch/'
	
	# Iterate over parameter number:
	for index in range(len(paramFile['map_id'])):
		if index%10==0:
			print 'Reconstructing job %s of %s' %(index+1,len(paramFile['map_id']))
		map_id=paramFile['map_id'][index]
		noise_power=paramFile['noise_power'][index]
		FWHM=paramFile['FWHM'][index]
	
		# Load in data file
		path=inDir+'id%s_fwhm%s_power%s.npz' %(map_id,FWHM,noise_power)
		if not os.path.exists(path): # if file not found
			continue
		dat=np.load(path)
		eps=dat['eps']
		eps_err=np.std(dat['eps_MC'])
		eps_MC=dat['eps_MC']
		dat.close()
		
		# Find relevant position in array
		noi_pow_index=np.where(a.noi_par_NoisePower==noise_power)[0][0]
		fwhm_index=np.where(a.noi_par_FWHM==FWHM)[0][0]
		
		power_arr[noi_pow_index,fwhm_index]=noise_power
		fwhm_arr[noi_pow_index,fwhm_index]=FWHM
		
		# Construct mean epsilon
		SNR=1./eps_err*2.
		eps_num[noi_pow_index,fwhm_index]+=SNR*eps
		for j in range(len(eps_MC)):
			eps_MC_num[noi_pow_index][fwhm_index][j]+=SNR*eps_MC[j]
			norm_MC[noi_pow_index][fwhm_index][j]+=SNR
		norm[noi_pow_index,fwhm_index]+=SNR
	
	paramFile.close()
	
	# Now compute normalised mean epsilon
	patch_eps=eps_num/norm
	patch_eps_MC=eps_MC_num/norm_MC
	
	# Compute number of significance of detection
	sig=(patch_eps-np.mean(patch_eps_MC,axis=2))/np.std(patch_eps_MC,axis=2)
	
	# Save output
	np.savez(a.root_dir+'PatchEpsilonNoiseParams.npz',\
	eps=patch_eps,eps_MC=patch_eps_MC,sig=sig,FWHM=fwhm_arr,noise_power=power_arr)
	
def noise_params_plot(map_size=a.map_size,sep=a.sep,createData=False):
	""" Create a 2D plot of mean epsilon for patch against FWHM and noise-power noise parameters.
	Input: createData- > whether to reconstruct from batch output files or just read from file
	Plot is saved in NoiseParamsPlot/ directory"""
	import matplotlib.pyplot as plt
	import os
	
	# First load in mean epsilon + significance:
	from .NoiseParams import reconstruct_epsilon
	
	if createData: # create epsilon data from batch data
		reconstruct_epsilon(map_size,sep)
	patch_dat=np.load(a.root_dir+'PatchEpsilonNoiseParams.npz')
	eps_arr=patch_dat['eps']
	sig_arr=patch_dat['sig']
	FWHM=patch_dat['FWHM']
	noise_power=patch_dat['noise_power']
	patch_dat.close()
	
	# Construct X,Y axes:
	#NP,FW=np.meshgrid(a.noi_par_NoisePower,a.noi_par_FWHM)
	
	# Create plot
	plt.figure()
	#plt.imshow(eps_arr,vmax=eps_arr.max(),vmin=eps_arr.min(),\
	#extent=[a.noi_par_NoisePower.min(),a.noi_par_NoisePower.max(),a.noi_par_FWHM.min(),a.noi_par_FWHM.max()])
	#plt.axes().set_aspect(1./6.)
	#plt.ylim([0,30])
	#plt.xlim([0,5])
	#plt.imshow()
	#plt.scatter(noise_power,FWHM,c=eps_arr,s=200,marker='o')
	#from scipy.interpolate import interp2d
	
	#eps_func=interp2d(noise_power.ravel(),FWHM.ravel(),eps_arr.ravel())
	#x=np.linspace(1e-30,a.noi_par_NoisePower.max(),100)
	#y=np.linspace(1e-30,a.noi_par_FWHM.max(),100)
	#xx,yy=np.meshgrid(x,y)
	#zz1=np.zeros([len(x),len(y)])
	#for i in range(len(x)):
	#	for j in range(len(y)):
	#		zz1[i,j]=eps_func(x[i],y[j])
	#zz=sig_func(xx.ravel(),yy.ravel())
	#mi1=np.min((zz1.min(),eps_arr.ravel().min()))
	#ma1=np.max((zz1.max(),eps_arr.ravel().max()))
	#import matplotlib.colors
	
	
	#norm1=matplotlib.colors.Normalize(vmin=mi1,vmax=ma1)
	#plt.contourf(x,y,zz1,100,norm=norm1)
	#plt.scatter(noise_power,FWHM,c=eps_arr,alpha=0.8,marker='x',s=60,norm=norm1)
	plt.scatter(noise_power,FWHM,c=eps_arr,s=500,marker='s',edgecolors='face',alpha=0.8)
	cbar=plt.colorbar()
	
	
	plt.ylabel('FWHM / arcmin')
	plt.xlabel('Noise-Power / uK-arcmin')
	plt.title('Noise Parameter Space for Mean Patch Epsilon')
	plt.xlim([-0.1,4.95])
	plt.ylim([-0.5,29])
	#plt.colorbar()
	
	# Save plot
	outDir=a.root_dir+'NoiseParamsPlot/'
	if not os.path.exists(outDir):
		os.makedirs(outDir)
	plt.savefig(outDir+'MeanPatchEpsilon-%sdeg%s.png' %(map_size,sep),bbox_inches='tight')
	plt.clf()
	plt.close()
	
	# Create plot 2
	plt.figure()
	#from scipy.interpolate import interp2d
	
	#sig_func=interp2d(noise_power.ravel(),FWHM.ravel(),sig_arr.ravel())
	#x=np.linspace(1e-30,a.noi_par_NoisePower.max(),200)
	#y=np.linspace(1e-30,a.noi_par_FWHM.max(),200)
	#xx,yy=np.meshgrid(x,y)
	#zz=np.zeros([len(x),len(y)])
	#for i in range(len(x)):
	#	for j in range(len(y)):
	#		zz[i,j]=sig_func(x[i],y[j])
	##zz=sig_func(xx.ravel(),yy.ravel())
	#mi=np.min((zz.min(),sig_arr.ravel().min()))
	#ma=np.max((zz.max(),sig_arr.ravel().max()))
	#import matplotlib.colors
	
	#norm=matplotlib.colors.Normalize(vmin=mi,vmax=ma)
	#plt.contourf(x,y,zz,100,norm=norm)
	#plt.scatter(noise_power,FWHM,c=sig_arr,alpha=0.8,marker='x',s=60,norm=norm)
	plt.scatter(noise_power,FWHM,c=sig_arr,s=500,marker='s',edgecolors='face',alpha=0.8)
	cbar=plt.colorbar()
	CS=plt.contour(noise_power,FWHM,sig_arr,levels=[2,3,4,5],colors='k',linestyles='--',alpha=0.8)
	plt.clabel(CS,colors='k',fontsize=14,fmt='%d')
	plt.plot(1,1.5,c='k',marker='*',ms=20)
	#plt.plot(5,30,c='k',marker='*',ms=20)
	#plt.contourf(noise_power,FWHM,sig_arr,50)
	#plt.imshow(sig_arr,vmax=eps_arr.max(),vmin=eps_arr.min(),\
	#extent=[noise_power.ravel().min(),noise_power.ravel().max(),FWHM.ravel().min(),FWHM])
	plt.ylabel('FWHM / arcmin')
	plt.xlabel('Noise-Power / uK-arcmin')
	plt.title('Noise Parameter Space for Epsilon Significance')
	plt.xlim([-0.1,4.95])
	plt.ylim([-0.5,29])
	#plt.colorbar()
	
	# Save plot
	plt.savefig(outDir+'PatchEpsilonSignificance-%sdeg%s.png' %(map_size,sep),bbox_inches='tight')
	plt.clf()
	plt.close()