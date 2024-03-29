l_step_dat=[130.,140.,150.,135.,155.,160.]#,130.,140.,150.]

if __name__=='__main__':
	""" This is the iterator for batch processing the map creation through HTCondor. Each map is done separately, and argument is map_id."""
	import numpy as np
	from hades.params import BICEP
	a=BICEP()
	import time
	start_time=time.time()
	import sys
	import pickle
	sys.path.append('/data/ohep2/')
	sys.path.append('/home/ohep2/Masters/')
	import os
	
	all_id=int(sys.argv[1]) # batch_id number
	
	# First load good IDs:
	goodFile=a.root_dir+'%sdeg%sGoodIDs.npy' %(a.map_size,a.sep)
	
	outDir=a.root_dir+'HexBatchData/f%s_ms%s_s%s_fw%s_np%s_d%s/' %(a.freq,a.map_size,a.sep,a.FWHM,a.noise_power,a.delensing_fraction)
	
	if all_id<110: # create first time
		from hades.batch_maps import create_good_map_ids
		create_good_map_ids()
		print 'creating good IDs'
		
	goodIDs=np.load(goodFile)
	
	batch_id=all_id%len(goodIDs)
	param_id=all_id//len(goodIDs)
	
	l_step=l_step_dat[param_id]
	
	if a.remakeErrors:
		if os.path.exists(outDir+'%s_%s.npy' %(batch_id,param_id)):
			sys.exit()
	
	if param_id>len(l_step_dat)-1:
		print 'Process %s terminating' %batch_id
		sys.exit() # stop here
	
	map_id=goodIDs[batch_id] # this defines the tile used here
	
	print 'Run %s tile %s starting for map_id %s' %(param_id,batch_id,map_id)

		
	# Now run the estimation
	from hades.hex_wrap import estimator_wrap
	def runner(map_id):
		return estimator_wrap(map_id,l_step=l_step)
	
	output=runner(map_id)
	
	# Save output to file
	if not os.path.exists(outDir): # make directory
		os.makedirs(outDir)
		
	np.save(outDir+'%s_%s.npy' %(batch_id,param_id), output) # save output
	
	print "Task %s tile %s complete in %s seconds" %(param_id,batch_id,time.time()-start_time)
	
	if batch_id==len(l_step_dat)*len(goodIDs)-2:
		if a.send_email:
			from hades.NoiseParams import sendMail
			sendMail('Single Map Params')
			
def create_significances():
	""" Recreate significances from parameters."""
	import warnings
	for i in range(len(l_step_dat)):
		from hades.wrapper import hex_patch_anisotropy
		suffix='_'+str(i)
		try:
			sigs,sigsA=hex_patch_anisotropy(suffix=suffix)
		except ValueError:
			print 'err'
			continue
		print 'l_step %s, Hex sig: %s, A sig: %s' %(l_step_dat[i],sigs,sigsA)
		
