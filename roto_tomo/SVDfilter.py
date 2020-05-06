#!/usr/bin/env python
# -*- coding: utf-8 -*-

from numpy import *
import time
from scipy.stats.mstats import mquantiles
from scipy.signal import firwin
from scipy.fftpack import ifft,fft,fftfreq
from matplotlib.widgets import MultiCursor
from matplotlib.pyplot import *
from . import  fconf
#import  fconf


try:
    from scipy.signal.signaltools import _next_regular as next_fast_len
except:
    try:
        from scipy.fftpack.helper import next_fast_len
    except:
        from scipy.fftpack import next_fast_len 
        
        

def shift_array(x,shift):
    #roll along first axis - much faster than numpy.roll
    if shift < 0:
        raise Exception('not implemented yet')

    tmp = copy(x[-shift:])
    x[shift:] = x[:-shift]
    x[:shift] = tmp
    return x
       
from colorsys import hls_to_rgb
def colorize(z):
    r = np.abs(z)
    arg = np.angle(z) 

    h = (arg + pi)  / (2 * pi) + 0.5
    l = 1.0 - 1.0/(1.0 + r**0.3)
    s = 0.8

    c = np.vectorize(hls_to_rgb) (h,l,s) # --> tuple
    c = np.array(c)  # -->  array of (3,n,m) shape, but need (n,m,3)
    c = c.T.swapaxes(0,1)
    return c

class SVDFilter():
    #algorithm for quasiperiodic multichannel signal filtering

    def __init__(self,tvec, data,err,dets_index,F0,dF,n_harm = 4, n_svd = 3, tau = 3):
        #savez('SVDFilter',tvec, data,err,dets_index,F0,dF,n_harm, n_svd, tau)
        self.data = copy(data)
        self.err = copy(err)
        self.tvec = tvec
        #print(data.shape, err.shape)
        #n_svd = 2
        #self.data = random.randn(len(tvec),len(err))*self.err
        #self.tvec = arange(self.data.shape[0])*1e-6
        #tau = 2

        #self.err = ones(self.data.shape[1] )
        
        #print(self.data.shape, self.err.shape)

        
        self.ndets = data.shape[1]
        self.dets_index = dets_index
        self.invalid = False

        self.f0 = F0
        self.df = dF
        self.ch0 = None

        self.window = 'blackman'
        self.n_svd = n_svd
        self.n_harm = n_harm
        self.tau = tau
        self.TSS = nan
        self.RSS = nan
        self.fig_retro = None
        self.fig_svd = None

        self.actual = False

    def set_corrupted_ch(self, removed):
        self.invalid = removed
        self.actual = False

        
    def run_filter(self,update_plots=True):
        
        if self.actual:
            return
 
        nt = len(self.tvec)
        dt = (self.tvec[-1]-self.tvec[0])/(len(self.tvec)-1)
        f =  fftfreq(nt, dt)[:nt//2+1]
        nmax = int(self.f0*dt*nt)
        

        f0 = nmax/dt/nt  
        fnq = 1/dt/2
        ntap_max = len(self.tvec)
        ntap_min = maximum(1/(f0)/dt*2,6) #at least 3 mode periodes
        ntap = logspace(log10(ntap_min),log10(ntap_max),10 )[self.tau]
        ntap = (int(ntap)//2)*2
        print(ntap,1/(f0)/dt/2 , self.tau, len(self.tvec))
        #print('SVDfilter', len(self.tvec), 2**(self.tau),ntap, self.df/self.f0*len(self.tvec))
        #print(self.tau)
        b = firwin(ntap, [(1e-3)*f0,(2e-3)*f0], pass_zero=False,nyq=1/dt/2, window = 'hanning')
      
        pad = len(b)//2

        cmpl_exp = zeros(2**int(ceil(log2(nt))),dtype='single')
        cmpl_exp[(nmax*len(cmpl_exp))//nt] = 1
        cmpl_exp = ifft(cmpl_exp)[:nt]*len(cmpl_exp)
        
        data = copy(self.data)
        err = copy(self.err)
        err[self.invalid] = inf

 
        offset = mean(data,axis=0)
        data -= offset[None,:] 


        n_fft = next_fast_len(nt+len(b)-1)
        cmpl_exp = zeros(n_fft,dtype='single')
        cmpl_exp[(nmax*n_fft)//nt] = 1
        cmpl_exp = ifft(cmpl_exp)[:nt]*len(cmpl_exp)

        fsig = fft(data,axis=0,n=n_fft)#použít RFFT? 
        fb   = fft(single(b),axis=0,n=n_fft)

        self.retrofit = zeros((nt-pad, self.ndets),dtype=single)
        weight = 1/single(err/(offset+mean(offset)/100))  #weight
       
        downsample = int(ceil(1/dt/(f0*2*self.n_harm))) *2
        downsample = max(downsample, nt//100)
    
        if self.fig_svd is not None and update_plots:
            self.fig_svd.clf()
            self.fig_svd.subplots_adjust(hspace=0.051, wspace = 0.05,left=0.05,top=0.95,right=0.99,bottom=0.04)

            axes = []
            ax2 = None
            for i in range(self.n_harm):
                ax1 = self.fig_svd.add_subplot(self.n_harm,2,2*i+1,sharex=ax2,sharey=ax2 )
                ax2 = self.fig_svd.add_subplot(self.n_harm,2,2*i+2,sharex=ax1,sharey=ax1)
                
                axes.append((ax1,ax2))
                ax1.set_ylabel('%d. harm.'%i,fontsize=10)
                ax2.yaxis.tick_right()
                for label in ax1.get_yticklabels():
                    label.set_fontsize(10) # Size here overrides font_prop
    
                ax1.yaxis.set_major_formatter( NullFormatter() )
                ax2.yaxis.set_major_formatter( NullFormatter() )
            
                
                for label in ax2.get_xticklabels()+ax2.get_yticklabels()+ax1.get_xticklabels():
                    label.set_visible(False)
                ax2.xaxis.offsetText.set_visible(False)
                ax1.xaxis.offsetText.set_visible(False)
                ax2.yaxis.offsetText.set_visible(False)
                #split detector arrays 
                for ax in [ax1, ax2]:
                    for ind in self.dets_index:
                        ax.axvline(x=1+amax(ind), linestyle='-' ,color='k')
                        ax.axvline(x=1+amax(ind), linestyle='--',color='w')
    

            for label in ax1.get_xticklabels()+ax2.get_xticklabels():
                label.set_visible(True)
                label.set_fontsize(10) # Size here overrides font_prop

            ax1.xaxis.offsetText.set_visible(True)
            ax2.xaxis.offsetText.set_visible(True)
        
            axes = array(axes)
            extent=(0,self.ndets,self.tvec[0],self.tvec[-pad])
            axes[0,0].set_title('Raw signal',fontsize=10)
            axes[0,0].set_ylim(self.tvec[0],self.tvec[-pad])
            axes[0,1].set_title('SVD filtered',fontsize=10)
            self.multi = MultiCursor(self.fig_svd.canvas, axes.flatten(),horizOn=True, color='k', lw=1)

            self.AxZoom = fconf.AxZoom()
            self.phase_cid = self.fig_svd.canvas.mpl_connect('button_press_event', self.AxZoom.on_click)
            
    
            
        len_red = max(1,pad//downsample)
        

        cmpl_exp_i = ones_like(cmpl_exp)
        phi = ones(1)
        mid_harm = zeros(( self.n_harm, self.ndets), dtype=complex) 
        svd_err = zeros(self.n_harm)
        for i_harm in range(self.n_harm):
        
            #filter out the choosen harmonics
            C1 = ifft(fsig*fb[:,None],axis=0,overwrite_x=True)[:nt+len(b)-1]

            filtered_harmonic = C1[(len(C1)-nt+len(b))//2:nt+len(b)-1-(len(C1)-nt+1)//2]


            #complex SVD filtration of the harmonics
            filtered_harmonic_low = copy(filtered_harmonic[:-len_red:downsample,:])
            filtered_harmonic_low*= weight[None,:]  #weight channels according their error

            U,s,V = linalg.svd(filtered_harmonic_low/phi[:,None]**i_harm,full_matrices=False)
            #print(sum(s[:self.n_svd]**2 )/sum(s**2 ))
            svd_err[i_harm] = sum(s[:self.n_svd]**2 )/sum(s**2 )
            fact = 1 if i_harm == 0 else 2
            svd_filtered_harm = dot(dot(conj(V[:max(1,self.n_svd-i_harm)]*weight[None,:]),
                                        filtered_harmonic.T).T, V[:max(1,self.n_svd-i_harm)]/((weight+1e-6)[None,:]/fact))
            
            #find strongest channel
            if self.ch0 is None and i_harm == 1:
                self.ch0 = argmax(abs(svd_filtered_harm*weight[None,:]).mean(0))
                

            #plotting
            if self.fig_svd is not None and update_plots:
                fun = colorize
                if i_harm == 1:  #global phase of the mode
                    phi =  U[:,0]/abs(U[:,0])
                vmax = mquantiles(abs(svd_filtered_harm[:-len_red:downsample,:]),0.95)[0]

                axes[i_harm,0].imshow(fun(filtered_harmonic[:-len_red:downsample,:]/phi[:,None]**i_harm/vmax*(~self.invalid)[None,:]),
                                        origin='lower',aspect='auto',interpolation='nearest',
                                        vmin=0,vmax=1,extent=extent)
                axes[i_harm,1].imshow(fun( svd_filtered_harm[:-len_red:downsample,:]/phi[:,None]**i_harm/vmax),
                                        origin='lower',aspect='auto',interpolation='nearest',
                                        vmin=0,vmax=1,extent=extent)
                    
                axes[i_harm,0].axis('tight')
                axes[i_harm,1].axis('tight')

            mid_harm[i_harm] = conj(svd_filtered_harm[-nt//2])*cmpl_exp_i[-nt//2]  #value in the middle of signal length

            #calculate a retrofit of the original real signal 
            self.retrofit+= einsum('ij,i->ij',svd_filtered_harm.real,cmpl_exp_i.real[pad:])
            self.retrofit+= einsum('ij,i->ij',svd_filtered_harm.imag,cmpl_exp_i.imag[pad:])
            
            #shift array to the next harmonics
            fsig = shift_array(fsig,int((nmax*n_fft//nt)))
            cmpl_exp_i*= cmpl_exp

        self.t0 = self.tvec[-nt//2]



        self.actual = True
        self.TSS = linalg.norm(data[pad:-pad])**2
        self.RSS = linalg.norm(data[pad:-pad]-self.retrofit[:-pad])**2
        #data-retrofit

        data += offset[None,:]
        self.retrofit+= offset[None,:]
        self.retrofit[self.retrofit<=0] = 1e-3  #make it nonzero
        mid_harm[0]+= offset

        #correctly estimated errorbars for gaussian noise!!
        #errors = std(data[pad:-pad]-self.retrofit[:-pad],0)*linalg.norm(self.b_comb) 
        #errors = hypot(errors, data.mean()*0.005)
        resid = data[pad:-pad]-self.retrofit[:-pad]
        
        #errors = 1.26*median(abs(resid-median(resid)[None]),0)/linalg.norm(b)
        #errors = std(self.retrofit,0)/linalg.norm(b)
        #errors = std(data,0)/linalg.norm(b)
        #print(nt, len(b), linalg.norm(b))
        #errors = std(resid,0)/linalg.norm(b)/len(b)*svd_err[0]*2
        errors = 1.26*median(abs(resid-median(resid)[None]),0)/linalg.norm(b)/len(b)*svd_err[0]*2

        
        
        #print(mean(errors),std(mid_harm[0]),sum(abs(mid_harm[1])**2)**.5/sqrt(len(mid_harm[1])),sum(abs(mid_harm[2])**2)**.5/sqrt(len(mid_harm[2])) )
        #print(mean(errors)/std(mid_harm[0]))

        
        #print(sqrt(sum((mid_harm[0].real)**2))/sqrt(len(mid_harm[0])), std(mid_harm[0]))

        #errors = median(abs(resid-median(resid)[None]),0)*nt*linalg.norm(b)/len(b) 
        fz = sum(diff(resid>0,axis=0),0)/float(len(resid))/2.
        lam = cos(2.*pi*fz)
        lam[lam == 1] = 0
        errors/= sqrt((1-lam)/(1+lam))
        #print( sqrt((1-lam)/(1+lam)))
        
        #f = random.randn(nt)
        #from scipy.signal import fftconvolve

        #nt = 1000
        #f = random.randn(nt)
        #print(std(fftconvolve(f,b))/linalg.norm(b))

                
        
        #import IPython
        #IPython.embed()
        
        
        #errorbar(arange(len(mid_harm.T)),abs(mid_harm[2]),errors)
        #errorbar(arange(len(mid_harm.T)),abs(mid_harm[1]),errors)
        #errorbar(arange(len(mid_harm.T)),abs(mid_harm[2]),errors)

        #show()
        #number of effective samples
   
        #errorbar(arange(self.ndets), abs(mid_harm[0]), errors);show()
        
        
    
        self.harm = mid_harm[:,~self.invalid]
        self.harm_err = errors[~self.invalid]#/100
        
        if self.fig_retro is not None and update_plots:
            ########  plot residdum plot 
            self.fig_retro.clf()
            
            
            import matplotlib.gridspec as gridspec
            
            gs0 = gridspec.GridSpec(2, 1,   height_ratios=[1,5] )
            gs00 = gridspec.GridSpecFromSubplotSpec(1, 1, subplot_spec=gs0[0])
            gs01 = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs0[1])


            nplots = 3
            axarr = np.empty(nplots, dtype=object)
            ax1 = Subplot(self.fig_retro, gs01[0])
            self.fig_retro.add_subplot(ax1)

            

            axarr[0] = ax1

            for i in range(1, nplots):
                axarr[i] = Subplot(self.fig_retro, gs01[i],sharex=ax1,sharey=ax1)
                self.fig_retro.add_subplot(axarr[i])

            for ax in axarr[..., 1:].flat:
                for label in ax.get_yticklabels():
                    label.set_visible(False)
                ax.yaxis.offsetText.set_visible(False)

            ax0 = Subplot( self.fig_retro, gs00[0])
            self.fig_retro.add_subplot(ax0)
            ax0.xaxis.set_ticks_position('top')
            ax0.yaxis.offsetText.set_visible(False)
            ax0.xaxis.offsetText.set_visible(False)
            for label in ax0.get_xticklabels()+ax0.get_yticklabels():
                label.set_visible(False)
                
            ax1, ax2, ax3 = axarr

            self.retrofit[:,self.invalid] = 0
            data[:,self.invalid] = np.nan
            vmax = 50

            
            
            
            for ax in (ax0,ax1,ax2,ax3):
                for label in (ax.get_xticklabels() + ax.get_yticklabels()):
                    label.set_fontsize(10) # Size here overrides font_prop



            self.fig_retro.subplots_adjust(hspace=0.1, wspace = 0.05, left=0.1,top=0.93,right=0.98,bottom=0.05)


            ax2.set_title('filtered',fontsize=10)
            extent=(0,self.ndets,self.tvec[0],self.tvec[-1])
            im1 = ax2.imshow(-(self.retrofit-data.mean(0))/sqrt(self.retrofit.std(0)+1),aspect='auto'
                            ,vmin=-vmax,vmax=vmax,cmap='seismic',extent=extent,
                            interpolation='nearest',origin='lower');
            ax1.set_title('original',fontsize=10)
            im2 = ax1.imshow(-(data[pad:,:]-data.mean(0))/sqrt(self.retrofit.std(0)+1),
                            aspect='auto',vmin=-vmax,vmax=vmax,cmap='seismic',
                            extent=extent,interpolation='nearest',origin='lower') ;
            ax3.set_title('original-filtered',fontsize=10)
            im3 = ax3.imshow(-(data[pad:,:]-self.retrofit)/sqrt(self.retrofit.std(0)+1),
                            aspect='auto',vmin=-vmax,vmax=vmax,cmap='seismic',
                            extent=extent,interpolation='nearest',origin='lower');

            #split detector arrays 
            for ax in [ax1, ax2, ax3]:
                for ind in self.dets_index:
                    ax.axvline(x=1+amax(ind), linestyle='-' ,color='k')
                    ax.axvline(x=1+amax(ind), linestyle='--',color='w')


                    
            self.multi2 = MultiCursor(self.fig_retro.canvas, (ax1,ax2,ax3),horizOn=True, color='k', lw=1)
            self.AxZoom2 = fconf.AxZoom()
            
            def update_single_plot(tmin,tmax,N):
                iimin = self.tvec.searchsorted(tmin)
                iimax = self.tvec.searchsorted(tmax)+1
                ind2 = slice(max(iimin,pad),iimax)
                if not all(isfinite(data[iimin:iimax,N])):
                    return
                    
                
                self.plt_data.set_data( self.tvec[iimin:iimax],data[iimin:iimax,N])
                self.plt_retro.set_data(self.tvec[max(0,iimin-pad)+pad:iimax],self.retrofit[ max(0,iimin-pad):iimax-pad,N])
                filtered_t = sum([outer(r,exp(2*pi*self.f0*1j*(self.tvec-self.t0)*i)).real for i,r in enumerate(mid_harm[:,N])],0).T

                

                if ax0.get_xlim() != (self.tvec[ind2][0],self.tvec[ind2][-1]):
                    ax0.set_xlim(self.tvec[ind2][0],self.tvec[ind2][-1])
                    
                ymin,ymax = mquantiles(data[ind2,N], [.02,.98])
                ax0.set_ylim(ymin,ymax)
                ax0._N = N
                self.fig_retro.canvas.draw()
                self.ch_name.set_text('ch: %d'%N)

            def mouse_interaction(event):
                if not hasattr(event,'button'):
                    tmin,tmax = event.get_ylim()
                    if ax0.get_xlim() == event.get_ylim():
                        return 
                    
                    update_single_plot(tmin,tmax,ax0._N)
                    
                elif hasattr(event,'button') and event.button == 3:
                    self.AxZoom2.on_click(event)
        
        
                    
                elif hasattr(event,'button') and event.button == 2 and event.inaxes in [ax1,ax2,ax3]:
                    tmin,tmax = event.inaxes.get_ylim()
                    N = int(event.xdata)
                    update_single_plot(tmin,tmax,N)
            
            
            self.plt_data,  = ax0.plot([],[],label='data', lw=.2)
            self.plt_retro, = ax0.plot([],[] ,'--',label='svd filtered') 

            ax0.set_xlim(self.tvec[pad],self.tvec[-1])
            ax0.axvline(self.t0,c='k',ls=':')
            self.ch_name = ax0.set_title('')
            
            def mouse_interaction2(event):
                tmin,tmax = event.get_xlim()
                ax1.set_ylim(tmin,tmax)
                ax2.set_ylim(tmin,tmax)
                ax3.set_ylim(tmin,tmax)
                if tmin < self.plt_data.get_xdata()[0] or tmax > self.plt_data.get_xdata()[-1]:
                    update_single_plot(tmin,tmax,ax0._N)
            
                self.fig_retro.canvas.draw()
            update_single_plot(0,infty, self.ch0)


        
            self.cid0 = self.fig_retro.canvas.mpl_connect('button_press_event', mouse_interaction)
            self.cid1 =  ax0.callbacks.connect('xlim_changed',  mouse_interaction2)

            ax1.callbacks.connect('ylim_changed',  mouse_interaction)
            ax2.callbacks.connect('ylim_changed',  mouse_interaction)
            ax3.callbacks.connect('ylim_changed',  mouse_interaction)
            
 



def main():
    data = load('SVDFilter.npz',allow_pickle=True)
    #print( data.keys())
    svd = SVDFilter(*[d for k,d in data.items()])
    svd.run_filter()
 
if __name__ == "__main__":
    main()
