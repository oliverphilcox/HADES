from flipper import *
import numpy as np
from .params import BICEP
import flipperPol as fp
a=BICEP()

def makeTEB(map_id,root_dir=a.root_dir,map_size=a.map_size,sep=a.sep,flipU=a.flipU):
	Tmap=liteMap.liteMapFromFits(root_dir+'%sdeg%s/fvsmapT_' %(map_size,sep) +str(map_id).zfill(5)+'.fits')
	Qmap=liteMap.liteMapFromFits(root_dir+'%sdeg%s/fvsmapQ_' %(map_size,sep) +str(map_id).zfill(5)+'.fits')
	Umap=liteMap.liteMapFromFits(root_dir+'%sdeg%s/fvsmapU_' %(map_size,sep) + str(map_id).zfill(5)+'.fits')
	if flipU:
		Umap.data*=-1.
	mask=liteMap.liteMapFromFits(root_dir+'%sdeg%s/fvsmapMaskSmoothed_' %(map_size,sep) +str(map_id).zfill(5)+'.fits')
	modL,angL=fp.fftPol.makeEllandAngCoordinate(Tmap)
	fT,fE,fB=fp.fftPol.TQUtoPureTEB(Tmap,Qmap,Umap,mask,modL,angL,method='hybrid')
	pT=fp.fftTools.powerFromFFT(fT)
	pE=fp.fftTools.powerFromFFT(fE)
	pB=fp.fftTools.powerFromFFT(fB)
	
	return pT,pE,pB
