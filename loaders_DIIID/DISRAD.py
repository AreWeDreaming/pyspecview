from loaders_DIIID.loader import * 
import os

#TODO lod only a data slice
#TODO calibration for all diagnostics 
#TODO 



def check(shot):
    #fastest check if the shotfile exist
    #BUG 
    status = True

    return status

verbose = False


class loader_DISRAD(loader):
    

    radial_profile=True
    units = 'V'


    def __init__(self,*args, **kargs):
        
        #prepocte se to na proud jen ze znalosti odporu ! a pak na watty
        
        super(loader_DISRAD,self).__init__(*args, **kargs)

        from time import time 
        
        t = time()
        
        self.groups = ('DISRADII',)
        self.names = list(range(1,31))
        #disradub1, disradub2 are two blinded pixels for each array
        


        #from efitview
        rvertbot = (230/100.,)*15
        zvertbot =  (74/100.,)*15

        #; Bottom channels
        rwallbot = array([ 221, 209, 197, 182, 163, 147, 129, 112, 
                    102, 102, 102, 102, 102, 102, 102       ]) / 100.
        zwallbot = array([ -78, -99,-107,-115,-136,-136,-136,-133, 
                    -118, -94, -73, -56, -40, -27, -14       ]) / 100.
        #; Top channels
        rverttop = (229/100.,)*15
        zverttop =  (78/100.,)*15
        rwalltop = array([ 102, 102, 102, 102, 102, 102, 102, 102, 
                    102, 102, 102, 102, 102, 117, 122       ]) / 100.
        zwalltop = array([   7,  16,  25,  35,  44,  53,  61,  71, 
                    80,  88,  97, 106, 115, 119, 123       ]) / 100.
    
        self.R_start = r_[rverttop,rvertbot] 
        self.R_end   = r_[rwalltop,rwallbot] 
        self.z_start = r_[zverttop,zvertbot] 
        self.z_end   = r_[zwalltop,zwallbot] 
        self.Phi = 210

  
  
    def get_names(self,group):
        return self.names
        
    def get_signal(self,group, names,calib=False,tmin=None,tmax=None):
        
        #TODO raw data ? fast?  
        if tmin is None:    tmin = self.tmin
        if tmax is None:    tmax = self.tmax
        
        if size(names) > 1:
            data = [self.get_signal(group, n, calib=calib, tmin=tmin,tmax=tmax) for n in names]
            return data
        else:
            name = int(names)
            
            
        
        sig = self.MDSconn.get('_x=PTDATA2("disradu%.2d",%d,1)'%(name, self.shot)).data()
        #disradub1, disradub2 are two blinded pixels for each array

        if not hasattr(self, 'tvec'):
            self.tvec = self.MDSconn.get('dim_of(_x)').data()
            #print self.tvec
            if len(self.tvec) <2:
                raise Exception('No DISRAD data availible')
            self.tvec /= 1e3
            
        imin,imax = self.tvec.searchsorted([tmin,tmax])
        imax+= 1
        
        return [self.tvec[imin:imax],sig[imin:imax]]


      
    def get_rho(self,group,names,time,dR=0,dZ=0):

        R_start = array([self.R_start[int(n)-1] for n in names])
        z_start = array([self.z_start[int(n)-1] for n in names])
        R_end = array([self.R_end[int(n)-1] for n in names])
        z_end = array([self.z_end[int(n)-1] for n in names])
        Phi = array([self.Phi for n in names])
        rho_tg,theta_tg,R,Z = super(loader_DISRAD,self).get_rho(time,R_start,
                                    z_start,Phi,R_end,z_end,Phi,dR=dR, dZ=dZ)

        return rho_tg, theta_tg,R,Z
    
    
    
    def signal_info(self,group,name,time):

        rho_tg = self.get_rho(group,[ name,],time)[0]
        phi = self.Phi
        info = str(name)+' Phi: %d deg, rho_tg: %.2f'%(phi,rho_tg)
        
            
            
            
        return info
    
    
 
    

    #def signal_info(self,group,name,time):
        #info = group+': '+str(name)
        #return info
    
    
from matplotlib.pylab import *
def main():

    
    mds_server = "localhost"
    mds_server = "atlas.gat.com"

    import MDSplus as mds
    MDSconn = mds.Connection(mds_server )
    
    #MDSconn.openTree('d3d',-1)

    #diags = MDSconn.get('getnci(".SX*:*","node_name")')
    
    from .map_equ import equ_map
    eqm = equ_map(MDSconn,debug=False)
    eqm.Open(163303,diag='EFIT01' )
    
    
    for shot in range(163355, 175000):
        print(( 163303, '  ',shot,'  ',175000))
        try:
            sxr = loader_DISRAD(shot ,exp='DIII-D',eqm=eqm,rho_lbl='rho_pol',MDSconn=MDSconn)
            g = sxr.groups[0]
            n = sxr.get_names(g)
            data1 = sxr.get_signal(  g,n,tmin=-infty, tmax=infty,calib=True)
        except:
            continue
        data = array([d for t,d in data1])
        tvec = data1[0][0]
        data-= data[:,tvec<0].mean(1)[:,None]
        imshow(data.reshape(data.shape[0], -1,1024).mean(2), interpolation='nearest',aspect='auto')
        savefig(str(shot))
        clf()
        
    
  
    import IPython
    IPython.embed()
    


    
    
    offset = tvec < .1
    data_ = data[:,offset]-data[:,offset].mean(1)[:,None]
    u1,s1,v1 = linalg.svd(data_, full_matrices=False)
    
    
    from scipy import signal
    fnq = len(tvec)/(tvec[-1]-tvec[0])/2
    #fmax = 50
    #b, a = signal.butter(4, fmax/fnq, 'low')
    noise1 = inner(u1[:,0], data.T)
    filtered_data = copy(data)
    filtered_data   -= outer( u1[:,0],noise1)
    imshow(filtered_data.T[500000:510000], interpolation='nearest',aspect='auto')
    
    
    fmax = 3000
    b, a = signal.butter(6, fmax/fnq, 'low')
    filtered_data = signal.filtfilt(b,a,filtered_data,axis=1)
    
    
    #noise1 -= signal.filtfilt(b,a,noise1)
    
    imshow(filtered_data[:,::100], interpolation='nearest',aspect='auto')

    
    import IPython
    IPython.embed()
    




    
    data1 = sxr.get_signal( '45R1',list(range(1,13)),tmin=-infty, tmax=infty,calib=True)
    data2 = sxr.get_signal('165R1',list(range(1,13)),tmin=-infty, tmax=infty,calib=True)
    data3 = sxr.get_signal('195R1',list(range(1,13)),tmin=-infty, tmax=infty,calib=True)


    data = array([d for t,d in data1]+[d for t,d in data2]+[d for t,d in data3])
    tvec = data1[0][0]
    
    
    
    

    offset = tvec < .1
    data_ = data[:,offset]-data[:,offset].mean(1)[:,None]
    u1,s1,v1 = linalg.svd(data_[:12], full_matrices=False)
    u2,s2,v2 = linalg.svd(data_[12:24], full_matrices=False)
    u3,s3,v3 = linalg.svd(data_[24:], full_matrices=False)


    from scipy import signal
    fnq = len(tvec)/(tvec[-1]-tvec[0])/2
    fmax = 50
    b, a = signal.butter(4, fmax/fnq, 'low')
    noise1 = inner(u1[:,0], data[:12].T)
    noise1 -= signal.filtfilt(b,a,noise1)
    noise2 = inner(u2[:,0], data[12:24].T)
    noise2 -= signal.filtfilt(b,a,noise2)
    noise3 = inner(u3[:,0], data[24:].T)
    noise3 -= signal.filtfilt(b,a,noise3)
    
    
    
    filtered_data = copy(data)
    filtered_data[:12]   -= outer( u1[:,0],noise1)
    filtered_data[12:24] -= outer( u2[:,0],noise2)
    filtered_data[24:]   -= outer( u3[:,0],noise3)

    fmax = 3000
    b, a = signal.butter(6, fmax/fnq, 'low')
    filtered_data = signal.filtfilt(b,a,filtered_data,axis=1)
    
    #fmax = 2000
    #b, a = signal.butter(6, fmax/fnq, 'low')
    #filtered_data = signal.filtfilt(b,a,filtered_data,axis=1)
    i1 = tvec<.1
    i2 = tvec> tvec[-1]-.5
    b1,b2 = filtered_data[:,i1].mean(1), filtered_data[:,i2].mean(1)
    a1,a2 = tvec[i1].mean(), tvec[i2].mean()

    filtered_data -= ((b2-b1)/(a2-a1)*(tvec[:,None]-a1)+b1).T
    offset_err = sqrt(mean(filtered_data[:,tvec<.3]**2,1))
    error =  offset_err[:,None]+filtered_data*0.05
    cov_mat = corrcoef(filtered_data[:,tvec<.3])

    
    f,ax=subplots(2,1,sharex=True, sharey=True)
    ax[0].plot(tvec, data[:12].T)    
    #ax[1].plot(tvec, filtered_data.T)
    ax[1].plot(tvec, filtered_data[:12].T)

    ax[1].set_xlabel('time [s]')
    ax[1].set_ylabel('filtered SXR')
    ax[0].set_ylabel('raw SXR')

    show()
    
    
    [errorbar(list(range(36)), d,e) for d,e in zip(filtered_data[:,::10000].T,error[:,::10000].T)];show()

    

    imshow(filtered_data,interpolation='nearest',aspect='auto',vmax=-0.1,vmin=0.1);colorbar();show()

    
    import IPython
    IPython.embed()
    
    exit()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    #plot(range(32),data[:32,35000:35100])
    #plot(range(32,64),data[32:,35000:35100])
    #show()
    
    

    data[2] = 0
    offset = tvec < .1
    data_ = data[:,offset]-data[:,offset].mean(1)[:,None]
    u1,s1,v1 = linalg.svd(data_[:32], full_matrices=False)
    u2,s2,v2 = linalg.svd(data_[32:], full_matrices=False)

    #plot(range(28),u1[:,0] )
    #plot(range(28,28*2), u2[:,0])
    from scipy import signal
    fnq = len(tvec)/(tvec[-1]-tvec[0])/2
    fmax = 50
    b, a = signal.butter(4, fmax/fnq, 'low')
    noise1 = inner(u1[:,0], data[:32].T)
    noise1 -= signal.filtfilt(b,a,noise1)
    noise2 = inner(u2[:,0], data[32:].T)
    noise2 -= signal.filtfilt(b,a,noise2)
    filtered_data = copy(data)
    filtered_data[:32]  -= outer( u1[:,0],noise1)
    filtered_data[32:]  -= outer( u2[:,0],noise2)
    
    
    fmax = 2000
    b, a = signal.butter(6, fmax/fnq, 'low')
    filtered_data = signal.filtfilt(b,a,filtered_data,axis=1)
    
    
    i1 = tvec<.1
    i2 = tvec> tvec[-1]-.5
    b1,b2 = filtered_data[:,i1].mean(1), filtered_data[:,i2].mean(1)
    a1,a2 = tvec[i1].mean(), tvec[i2].mean()

    filtered_data -= ((b2-b1)/(a2-a1)*(tvec[:,None]-a1)+b1).T
    offset_err = sqrt(mean(filtered_data[:,tvec<.3]**2,1))
    error =  offset_err[:,None]+filtered_data*0.05
    cov_mat = corrcoef(filtered_data[:,tvec<.3])

    #plot(v1[0])
    #plot(v2[0])

    #print data.shape, tvec.shape
    import IPython
    IPython.embed()
    #plot(abs(fft.rfft(data_[0])))

    #NOTE odecist pozadi pred aplikaci IIR  filtru!
    
    f,ax=subplots(2,1,sharex=True, sharey=True)
    ax[0].plot(tvec, data.T)    
    #ax[1].plot(tvec, filtered_data.T)
    ax[1].plot(tvec, filtered_data2.T)

    ax[1].set_xlabel('time [s]')
    ax[1].set_ylabel('filtered SXR')
    ax[0].set_ylabel('raw SXR')

    show()
    
    
    
    offset = filtered_data[:,80000:].mean(1)[:,None]

    contourf(data,20)
    
    #filtered_data-= filtered_data[:,80000:].mean(1)[:,None]
    
    imshow(filtered_data,interpolation='nearest',aspect='auto',vmin=-1000, vmax=1000, extent=(tvec[0], tvec[-1], 0,1));colorbar();show()
    
    
    [errorbar(list(range(64)), d,e) for d,e in zip(filtered_data[:,::10000].T,error[:,::10000].T)];show()

    imshow(filtered_data, interpolation='nearest',aspect='auto');colorbar();show()
    plot((filtered_data-offset)[:,40000]);show()

    import matplotlib.pylab as plt
    plt.plot(tvec, sig)
    plt.show()
    
if __name__ == "__main__":
    main()
    
