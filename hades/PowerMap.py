from flipper import *
from .params import BICEP
a=BICEP()

import numpy as np

def createMap(map_id,warnings=False,plotPNG=True,Fits=False):
    """ Create the B-,E-,T- space 2D power maps from input simulation maps. Simulation maps are those of Vansyngel+16 provided and reduced by Alex van Engelen. This uses the flipperPol hybrid scheme to minimise E-B leakage in B-maps.
    
    Input: map_id - number of map - integer from 00001-00315
    warnings - whether to ignore overwrite warnings
    plotPNG - whether to save PNG files
    Fits = whether to save FITS file

    Output: T,B,E maps are saved in the ProcMaps/ directory and pngs are in the ProcMaps/png directory 
    """
    import flipperPol as fp

    import os
    
    # Map directories
    filepath = '/data/ohep2/sims/3deg/' # This houses all the simulation data
    outdir = '/data/ohep2/ProcMaps/'
    pngdir = "/data/ohep2/ReportPlots/" #'ProcMaps/png/"
    Q_path = filepath+'fvsmapQ_'+str(map_id).zfill(5)+'.fits'
    U_path = filepath+'fvsmapU_'+str(map_id).zfill(5)+'.fits'
    T_path = filepath+'fvsmapT_'+str(map_id).zfill(5)+'.fits'
    mask_path = filepath+'fvsmapMaskSmoothed_'+str(map_id).zfill(5)+'.fits'
    
    # Create output directory
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    # Read in maps
    Tmap = liteMap.liteMapFromFits(T_path)
    Qmap = liteMap.liteMapFromFits(Q_path)
    Umap = liteMap.liteMapFromFits(U_path)
    maskMap = liteMap.liteMapFromFits(mask_path) # this is the smoothed map

    ## Convert T,Q,U maps to T,E,B maps

    # First compute modL and angL maps (common for all files)
    modLMap,angLMap = fp.fftPol.makeEllandAngCoordinate(Tmap)

    # Now compute the FFT (hybrid) maps using the mask map to minimise E->B leakage (no significant B->E since E>>B)
    fftTmap,fftEmap,fftBmap = fp.fftPol.TQUtoPureTEB(Tmap,Qmap,Umap,maskMap,modLMap,angLMap,method='hybrid')

    # Now compute the power maps from this
    pTT,pTE,pET,pTB,PBT,pEE,pEB,pBE,pBB = fp.fftPol.fourierTEBtoPowerTEB(\
        fftTmap,fftEmap,fftBmap,fftTmap,fftEmap,fftBmap)
    # (second argument allows for cross maps

    # Save these files in correct directory

    if not warnings:
        import warnings
        warnings.filterwarnings("ignore") # ignore overwrite warnings

	
    if Fits:
    	pTT.writeFits(outdir+'powerT'+str(map_id)+'.fits',overWrite=True)
    	pBB.writeFits(outdir+'powerB'+str(map_id)+'.fits',overWrite=True)
    	pEE.writeFits(outdir+'powerE'+str(map_id)+'.fits',overWrite=True)

    # Plot and save as pngs
    if plotPNG:
        if not os.path.exists(pngdir):
            os.mkdir(pngdir) # Make directory

        pTT.plot(log=True,show=False,pngFile=pngdir+"powerT"+str(map_id)+".png")
        pEE.plot(log=True,show=False,pngFile=pngdir+"powerE"+str(map_id)+".png")
        pBB.plot(log=True,show=False,pngFile=pngdir+"powerB"+str(map_id)+".png")


    return pBB

def openPower(map_id,map_type='B'): 
    """ Function to read in Power FITS file saved in createMap process.
    Input: map_ids: 0-315 denoting map number
    maptype - E,B or T map to open

    NB: THIS IS NOT CURRENTLY WORKING
    """
    import pyfits

    mapfile = '/data/ohep2/ProcMaps/power'+str(map_type)+str(map_id)+'.fits'
    oldFile = '/data/ohep2/sims/simdata/fvsmapT_'+str(map_id).zfill(5)+'.fits'
    powMap = fftTools.power2D() # generate template

    hdulist = pyfits.open(mapfile) # read in map
    header = hdulist[0].header

    powMap.powerMap = hdulist[0].data.copy() # add power data

    # Read in old T map - to recover L and ang maps
    oldMap = liteMap.liteMapFromFits(oldFile)
    modL,angL = fp.fftPol.makeEllandAngCoordinate(oldMap)
    easyFT = fftTools.fftFromLiteMap(oldMap)

    # Read in these quantities from simple FT 
    powMap.ix = easyFT.ix
    powMap.iy = easyFT.iy
    powMap.lx = easyFT.lx
    powMap.ly = easyFT.ly
    powMap.pixScaleX = easyFT.pixScaleX
    powMap.pixScaleY = easyFT.pixScaleY
    powMap.Nx = easyFT.Nx
    powMap.Ny = easyFT.Ny
    powMap.modLMap = modL
    powMap.thetaMap = angL

    return powMap

if __name__=='__main__':
     """ Batch process to use all available cores to compute the 2D power spectra
    This uses the makePower routine.

    Inputs are min and max file numbers"""

     import tqdm
     import sys
     import multiprocessing as mp

     # Default parameters
     nmin = 0
     nmax = 315
     cores = 7

     # Parameters if input from the command line
     if len(sys.argv)>=2:
         nmin = int(sys.argv[1])
     if len(sys.argv)>=3:
         nmax = int(sys.argv[2])
     if len(sys.argv)==4:
         cores = int(sys.argv[3])

     # Start the multiprocessing
     p = mp.Pool(processes=cores)
     file_ids = np.arange(nmin,nmax+1)

     # Display progress bar with tqdm
     r = list(tqdm.tqdm(p.imap(createMap,file_ids),total=len(file_ids)))


def MakePower(map_id,map_size=a.map_size,map_type='B'):
    """ Function to create 2D power map of the correct type (i.e. B,E or T). Returns this map. IN: map_type"""
    import flipperPol as fp
    import os

    # Input map directory:
    if a.root_dir=='/data/ohep2/sims/':
    	if map_size==10:
    		inDir='/data/ohep2/sims/simdata/'
    	elif map_size==5:
    		inDir='/data/ohep2/sims/5deg/'
    	elif map_size==3:
    		inDir='/data/ohep2/sims/3deg/'
    	else: 
    		raise Exception('Incorrect Map Size')
    else:
   	inDir=a.root_dir+'%sdeg%s/' %(map_size,a.sep)
    # Read in maps from file
    Tmap=liteMap.liteMapFromFits(inDir+'fvsmapT_'+str(map_id).zfill(5)+'.fits')
    Qmap=liteMap.liteMapFromFits(inDir+'fvsmapQ_'+str(map_id).zfill(5)+'.fits')
    Umap=liteMap.liteMapFromFits(inDir+'fvsmapU_'+str(map_id).zfill(5)+'.fits')
    Maskmap=liteMap.liteMapFromFits(inDir+'fvsmapMaskSmoothed_'+str(map_id).zfill(5)+'.fits')

    # Define mod(l) and ang(l) maps needed for fourier transforms
    modL,angL=fp.fftPol.makeEllandAngCoordinate(Tmap) # choice of map is arbitary

    # Create pure T,E,B maps using 'hybrid' method to minimize E->B leakage
    fT,fE,fB=fp.fftPol.TQUtoPureTEB(Tmap,Qmap,Umap,Maskmap,modL,angL,method='hybrid')

    # Transform these maps into power space
    TT,_,_,_,_,EE,_,_,BB=fp.fftPol.fourierTEBtoPowerTEB(fT,fE,fB,fT,fE,fB)
    # (remainder are cross-maps)

    # Define type of map used:
    if map_type=='B':
        return BB
    elif map_type=='E':
        return EE
    elif map_type=='T':
        return TT

def dust_emission_ratio(nu1,nu2=a.reference_frequency,Tdust=a.dust_temperature,beta=a.dust_spectral_index):
    """ Ratio of dust spectral flux at two frequencies in GHz. 
    This is uses a modified black-body spectrum, plus unit and color correction factors from Planck HFI XI (exact values from Rotti+Huffenberger16)).
    Default values (dust temperature Tdust in K and spectral index beta) are from Planck XXII.
    nu2 is a reference dust frequency"""
    h=6.6261e-34 # planck constant
    k=1.3806e-23 # boltzmann constant  
    nu1_Hz=nu1*1e9 # in Hz
    nu2_Hz=nu2*1e9
    if nu2!=353. and nu1!=150.:
    	raise Exception('Need to compute color + unit factors for this frequency.')
    flux1=nu1_Hz**(3+beta)/(np.exp(h*nu1_Hz/(k*Tdust))-1)
    flux2=nu2_Hz**(3+beta)/(np.exp(h*nu2_Hz/(k*Tdust))-1)
    
    # Unit + Colour Factor:
    col_unit_factor=0.6486 # see Planck HFI XI paper sec. 3
    
    return flux1/flux2*col_unit_factor
    
def central_ell(input_func,l1,l2):
    """ Semi-analytically compute the central-ell value of a bin using a given expected ell dependence.
    Inputs: expected function for Cell (including noise etc.) 
    [l1,l2] range of bin.
    
    This just computes the mean of input_func over the annulus by approx. integration, then computes the central ell from the inverse function."""
    def integrand(ell):
        return 2*np.pi*input_func(ell)*ell
    denom = np.pi*(l2**2.-l1**2.) # normalisation
    dl=0.1
    ell_vals = np.arange(l1,l2,dl)
    Cl_vals=integrand(ell_vals)
    num=np.sum(Cl_vals*dl)
    from pynverse import inversefunc
    inv=inversefunc(input_func,domain=[l1,l2])
    try:
    	output=inv(num/denom)
    except ValueError:
    	output=np.mean([l1,l2])
    return output
        
def oneD_binning(powMap,lMin,lMax,l_step,binErr=False,exactCen=a.exactCen,C_ell_model=None,params=[0,0]):
	""" Compute the one-dimensional power spectrum of a given map from binning in annuli.
	Inputs: powermap, min.max l and bin size.
	binErr -> whether to return error in power from binning
	exactCen -> whether to compute centre of bin semi-analytically
	C_ell_model -> function modelling the C_ell (inc. lensing etc.)
	(needed if exactCen=True)
	
	Outputs: central l value, binned power, [binned power error] """
	l_bin = np.arange(lMin,lMax,l_step) # binning positions
	l_cen, bin_pow = [], [] 
	if binErr:
		bin_err=[]
	if exactCen:
		from .PowerMap import central_ell
		def model(l):
			return C_ell_model(l,params[0],params[1])
		
	for i in range(len(l_bin)-1):
		if exactCen:
			l_cen.append(central_ell(model,l_bin[i],l_bin[i+1]))
		else:
			l_cen.append(0.5*(l_bin[i]+l_bin[i+1]))
		temp=powMap.meanPowerInAnnulus(l_bin[i],l_bin[i+1],nearestIntegerBinning=False)
		bin_pow.append(temp[0])
		if binErr:
			bin_err.append(temp[1])
	
	if binErr:
		return np.array(l_cen), np.array(bin_pow), np.array(bin_err)
	else:
		return np.array(l_cen), np.array(bin_pow)

def MapSlope(Pmap,l_min,l_max,l_step,returnFit=False):
    """ Compute slope of power spectrum of given map in the [l_min,l_max] range, using a binning of l_step. Returns power-law slope and amplitude, with covariance matrix. returnFit => Boolean - whether to return bin widths and amplitude+error"""

    from scipy.optimize import curve_fit
    
    print 'DEPRACATED'
    
    # Define arrays
    l_bin = []
    pow_mean = []
    pow_std = []

    # Compute power
    for l in np.arange(l_min,l_max,l_step):
        mean,std,pix=Pmap.meanPowerInAnnulus(l,l+l_step)
        pow_mean.append(mean)
        pow_std.append(std)
        l_bin.append(l+0.5*l_step)

    # Compute the best-fit power index in this range
   

    param,covariance=curve_fit(pow_model,l_bin,pow_mean,sigma=pow_std,absolute_sigma=True)
    slope=param[1] # model -slope
    A=param[0] # amplitude
    if returnFit:
        return slope,A,covariance,l_bin,pow_mean,pow_std
    else:
        return slope,A,covariance

def pow_model(x,A,slope): #(predicted power model)
    return A*x**(-slope)

def RescaledPlot(map_id,map_size=3,map_type='B',rescale=True,show=False,save=True,showFit=False,saveFit=True,l_min=100,l_max=2000,l_step=100,returnMap=False):
    """ Create + plot the power map rescaled by a factor of l^{slope} where slope is found from radially binning the power spectrum in a specified range.

    NB: This can also plot unscaled plots using rescale=False
    
    Inputs: map_id - 0 to 315
    map_type='B'
    map_size = [3,5,10] -> map widths
    rescale - whether to rescale plot (else just return power map)
    show - Display rescaled map
    save - Save rescaled map
    showFit - show fitting of radially binned spectrum to model
    saveFit - save fitting as png
    l_min,l_max,l_step - define min/max/separation of l values
    returnMap = return power map instance + fitted slope

    Output: rescaled plot + fitted slope, saved in RescaledPlots/ dir (if save)
    + fitting plot (if saveFit)
    """

    #import flipperPol as fp
    import os
    from scipy.optimize import curve_fit

    
    # Output map directory:
    if a.root_dir=='/data/ohep2/sims/':
	if map_size==10:
        	outDir='/data/ohep2/RescaledPlots/'
    	elif map_size==5:
    		outDir='/data/ohep2/RescaledPlots/5deg/'
    	elif map_size==3:
    		outDir='/data/ohep2/RescaledPlots/3deg/'
    	else: 
    		raise Exception('Incorrect Map Size')
    else:
    	outDir=a.root_dir+'RescaledPlots/'+str(map_size)+'deg/'
    
    if not os.path.exists(outDir):
        os.makedirs(outDir)
  
    # Create power map
    Pmap=MakePower(map_id,map_size=map_size,map_type=map_type)
    
    if rescale:
        slope,A,covariance,l_bin,pow_mean,pow_std=MapSlope(Pmap,l_min,l_max,l_step,returnFit=True)
        print('Slope '+str(slope)+' +/- '+str(covariance[1,1]))

        # Plot + save fitting plot in log space
        if showFit or saveFit:
            import matplotlib.pyplot as plt
            fig=plt.figure()
            ax=fig.add_subplot(1,1,1)
            ax.errorbar(l_bin,pow_mean,yerr=pow_std)
            ax.plot(l_bin,pow_model(l_bin,A,slope))
            #print A, slope
            ax.set_xscale('log')
            ax.set_yscale('log')
            fig.suptitle(str(map_type)+' '+str(map_id)+' fit with slope '+str(slope))
            ax.set_xlabel('l')
            ax.set_ylabel('Mean power in annulus')
            if saveFit:
                fig.savefig(outDir+str(map_type)+str(map_id)+'fit.png')
            if showFit:
                fig.show()
            plt.close(fig)

        if save:
            outFile=outDir+str(map_type)+str(map_id)+'_RescaledMap.png'
        else:
            outFile=None

        # Plot rescaled power map
        Pmap.plot(powerOfL=slope,log=True,zoomUptoL=2000,\
                      pngFile=outFile,show=show,\
                      title=str(map_type)+str(map_id)+' Map with scaling by l^'+str(slope))
        
    else:
        # Plot and save unscaled map instead
        if save:
            outFile=outDir+str(map_type)+str(map_id)+'_Map.png'
        else:
            outFile=None
        if show or save:
            Pmap.plot(log=True,zoomUptoL=2000,pngFile=outFile,title=str(map_type)+str(map_id)+' Map with no scaling applied')

    if returnMap:
        return Pmap,slope,A
    else:
        return None
    
     
def AnisotropyPower(map_id,show=True,save=False,fitPlot=False):
    """ Plot the power map * l^{index} where index is the best fit power law index from radially binning the power plot.
    NB: the radial fit does not take into account errors.

    NB: NOW DEPRACATED - DO NOT USE
    
    Input: map_id number,
    plot -> whether to display map,
    save=whether to save map as png
    fitPlot = whether to plot fitting of radially binned spectrum
    
    Output: plot (if show=True) + saved in /ProcMaps/Aniso as png (if save=True)
    """
    aniso_path = '/data/ohep2/ProcMaps/Aniso/' # saving path

    # Create directory
    import os
    if not os.path.exists(aniso_path):
        os.makedirs(aniso_path)

    # Open map
    BBpower=openPower(map_id,map_type='B')

    # Bin radially
    l_bin = []
    pow_mean = []
    pow_std = []
    for i in range(5,100):
        mean,std,pix=BBpower.meanPowerInAnnulus(i*20,(i+1)*20)
        pow_mean.append(mean)
        pow_std.append(std)
        l_bin.append((i+0.5)*20)

    # Perform linear regression for slope + intercept
    from scipy.stats import linregress
    slope,intercept,_,_,err=linregress(x=np.log(l_bin),y=np.log(pow_mean))
    amplitude = np.exp(intercept)
    ytest = amplitude*l_bin**slope

    if fitPlot:
        # Plot fitting results:
        import matplotlib.pyplot as plt
        plt.errorbar(l_bin,pow_mean,xerr=10,yerr=pow_std)
        plt.errorbar(l_bin,ytest)
        plt.xscale('log')
        plt.yscale('log')
        plt.xlabel('l')
        plt.ylabel('Radially averaged power')
        plt.title('Fitting plot for radially binned power')
        plt.savefig(aniso_path+'radialFig'+str(map_id)+'.png')
        plt.show()
        #plt.clf()

    # Plot BB map * l^{-slope}
    if save:
        pngFile=aniso_path+'anisoBplot'+str(map_id)+'.png'
    else:
        pngFile=None
    BBpower.plot(show=show,log=True,powerOfL=-slope,zoomUptoL=2000,title='Power spectrum * l^-'+str(slope),pngFile=pngFile)

    return None
   
