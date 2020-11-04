import numpy as np
import pandas as pd
from scipy.signal import periodogram

def power_law(a, b, g, size):
    ''' Power-law gen for pdf(x) prop to x^{g} for a<=x<=b '''
    if g == -1:
        raise Exception('g must be different from -1')
    r = np.random.random(size=size)
    ag, bg = a**(g+1), b**(g+1)

    return (ag + (bg - ag)*r)**(1./(g+1))


def normalize(W):
    ''' Normalize each entry in a matrix by the sum of its row'''
    return W / np.sum(W, axis=1)[:,None]


def correlation(mat):
    '''
    Return the (mean and std) correlation btw N time series.
    mat -> MxN matrix where:
    - M is the legth of each time series
    - N is the number of different time series
    '''    
    N = mat.shape[1]
    
    Cij = pd.DataFrame(mat).corr().to_numpy()   # compute NxN correlation matrix
    Cij = Cij[np.triu_indices(N, k=1)]          # get only upper-triangular values

    return ( np.mean(Cij), np.std(Cij) )


def entropy(data):
    '''
    Compute the ensamble entropy and its std
    '''
    p = np.mean(data, axis=1) # node activation average
    ent = -( p*np.log2(p) + (1-p)*np.log2(1-p) ) # node entropy
    ent = np.mean(ent, axis=1) # run entropy

    # return ensemble mean/std
    return np.mean(ent), np.std(ent)


def power_spectrum(data, dt=1.):
    '''
    Compute the power spectrum of a collection of time series
    using a periodogram.
    - Input: data(runs,steps), timestep
    - Output: frequencies, power spectrum
    '''
    # compute the power spectrum for each run
    return periodogram(data, scaling='spectrum', fs=1./dt)

def avg_pow_spec(data):
    '''
    Compute the average power spectrum of a collection of time series
    using a periodogram.
    - Input: data(runs,steps), timestep
    - Output: frequencies, power spectrum
    '''
    spectr = np.array(list(map(power_spectrum, data)))
    
    freq = spectr[0,0]
    spectr = np.mean(spectr[:,1], axis=0)
    
    return np.array([freq, spectr])


def interevent(data):
    '''
    Compute the time btw two consecutives activations
    of a node
    '''
    steps, nodes = data.shape
    
    # check nodes with O or 1 activation
    # -> set dt equal to length of simulation
    not_active = np.sum(np.sum(data, axis=1)<=1.)
    
    ind = np.where(data==1)             # get active times
    
    dt = ind[1][1:]-ind[1][:-1]         # compute dt
    dt = dt[ind[0][1:]-ind[0][:-1]==0]  # discard dt from different trials
    dt = np.append(dt, [steps]*not_active)
    
    return np.mean(dt), np.std(dt)
