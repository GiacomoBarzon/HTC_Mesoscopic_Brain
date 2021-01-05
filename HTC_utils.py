import numpy as np
from scipy.signal import periodogram
import igraph as gf
from collections import Counter
from scipy.interpolate import InterpolatedUnivariateSpline


# GENERAL FUNCTION
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


def hline_intersection(x1, y1, x2, y2, y_star):
    '''
    Get intersection btw lines through two points and hline
    '''
    if np.sum((y1-y2)==0)>0:
        print('hline_intersection: the y\'s are equal')
    return (x1 - x2) / (y1 - y2) * (y_star - y2) + x2


# PDF/POWER SPECTRUM IO HANDLING
def reshape_pdf(pdf):
    ''' Reshape list of counter to sorted array '''
    pdf = [np.array(list(i.items())).T for i in pdf]
    pdf = [i[:, i[0].argsort()] for i in pdf]
    
    return pdf


def write_lists(lst, lst_norm, fname):
    ''' Write lists of numpy vectors to .txt file'''
    with open(fname, 'w') as outfile:
        for x in lst:
            np.savetxt(outfile, x)
            outfile.write('\n')
        for x in lst_norm:
            np.savetxt(outfile, x)
            outfile.write('\n')


def read_lists(fname):
    ''' Read lists of numpy vectors from .txt file'''
    text_file = open(fname, 'r')
    lines = text_file.read().split('\n\n')
    del lines[-1]

    lines = [i.split('\n') for i in lines]
    lst = []

    for i in lines:
        lst.append( np.array([j.split(' ') for j in i]).astype(float) )
    return lst[:len(lst)//2], lst[len(lst)//2:]


# HTC SIMULATION
def init_state(N, runs, fract):
    '''
    Initialize the state of the system
    fract: fraction of initial acrive neurons
    '''
    from math import ceil
        
    n_act = ceil(fract * N)     # number of initial active neurons
        
    # create vector with n_act 1's, the rest half 0's and half -1's
    ss = np.zeros(N)
    ss[:n_act] = 1.
    ss[-(N-n_act)//2:] = -1.
        
    # return shuffled array
    return np.array([np.random.choice(ss, len(ss), replace=False) for _ in range(runs)])
    
    
def update_state(S, W, T, r1, r2):
    '''
    Update state of the system according to HTC model
    '''
        
    probs = np.random.rand(S.shape[0], S.shape[1])   # generate probabilities
    s = (S==1).astype(int)                           # get active nodes
    pA = r1 + (1.-r1) * ( (W@s.T)>T )                # prob. to become active

    # update state vector
    newS = ( (S==0)*(probs<pA.T)                     # I->A
         + (S==1)*-1                                 # A->R
         + (S==-1)*(probs>r2)*-1 )                   # R->I (remain R with prob 1-r2)
        
    return (newS, (newS==1).astype(int) )


def compute_clusters(W, sj):
    '''
    Compute cluster analysis
    '''
    # mask adjacency matrix with active nodes
    mask = (W * sj).T * sj
    # create igraph object
    graph = gf.Graph.Adjacency( (mask > 0).tolist())
    # compute connected components occurrence
    counts = np.array(graph.clusters().sizes())
    counts = -np.sort(-counts)
        
    # return (biggest cluster, second biggest cluster, clusters occurrence)
    return (counts[0], counts[1], Counter(counts))


def stimulated_activity(W, runs, steps, r1, r2):
    '''
    Simulate activity with external stimulus
    '''
    N = W.shape[0]
    S = init_state(N, runs, fract)
    At = np.zeros((runs, steps))
                
    # Loop over time steps
    for t in range(steps):
        # update state vector
        S, s = update_state(S, W, T, r1=r1, r2=r2)
        # compute average activity
        At[:,t] = np.mean(s, axis=1)
    # end loop over time steps
    return np.mean(At)
    
    
def susceptibility(mat):
    '''
    Return the (mean and std) susceptibility btw N time series.
    Susceptibility = mean covariance btw elements.
    mat -> MxN matrix where:
    - M is the legth of each time series
    - N is the number of different time series
    '''    
    N = mat.shape[1]
    
    Cij = np.cov(mat, rowvar=False)        # compute NxN covariance matrix
    Cij = Cij[np.triu_indices(N, k=1)]     # get only upper-triangular values

    return ( np.mean(Cij), np.std(Cij) )


def entropy(data):
    '''
    Compute the ensamble entropy and its std
    '''
    p = np.mean(data, axis=1) # node activation average
    ent = -( p*np.log2(p) + (1.-p)*np.log2(1.-p) ) # node entropy
    ent[np.isnan(ent)] = 0.
    ent[np.logical_not(np.isfinite(ent))] = 0.
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
    - Output: power spectrum
    '''
    spectr = np.array(list(map(power_spectrum, data)))
    
    #freq = spectr[0,0]
    spectr = np.mean(spectr[:,1], axis=0)
    
    return spectr


def interevent(data):
    '''
    Compute the time btw two consecutives activations
    of a node
    '''
    steps, nodes = data.shape
    
    # check nodes with only O or 1 activation
    # -> set dt equal to length of simulation
    not_active = np.sum(np.sum(data, axis=1)<=1.)
    
    ind = np.where(data==1)             # get active times
    
    dt = ind[1][1:]-ind[1][:-1]         # compute dt
    dt = dt[ind[0][1:]-ind[0][:-1]==0]  # discard dt from different trials
    dt = np.append(dt, [steps]*not_active)
    
    return np.mean(dt), np.std(dt), Counter(dt)


def get_intersection(arr, y_star):
    '''
    Get all the intersection btw array and a hline
    '''
    # Increase intersection
    start = np.where( (arr[:-1]<y_star) * (y_star<arr[1:]) )[0]
    # Decrease intersection
    stop = np.where( (arr[:-1]>y_star) * (y_star>arr[1:]) )[0]

    # Check that first start is smaller than first stop
    if start[0]>stop[0]:
        stop = np.delete(stop, 0)
    # Check that last stop is bigger than last start
    if stop[-1]<start[-1]:
        start = np.delete(start, -1)
    
    # Get intersection with hline
    start = hline_intersection(start, arr[start], start+1, arr[start+1], y_star)
    stop = hline_intersection(stop, arr[stop], stop+1, arr[stop+1], y_star)
    
    return start, stop

def get_avalanches(arr, y_star):
    '''
    Get sizes and lifetimes of avalanches
    '''
    T = len(arr)
    t = np.arange(T)
    
    # Get start and stop of avalanches
    start, stop = get_intersection(arr, y_star)
    
    # Compute avalanche time
    dt = stop - start
    
    # Compute avalanche size as activity area
    I = np.zeros(len(start))
    
    for i in range(len(start)):
        # Get point btw each start and stop
        t_in = t[(t>start[i])*(t<stop[i])]
        y_in = arr[t_in]
    
        # Append start and stop
        t_in = np.hstack([start[i], t_in, stop[i]])
        y_in = np.hstack([y_star, y_in, y_star])
        
        # Get spline
        f = InterpolatedUnivariateSpline(t_in, y_in, k=1)
    
        # Integrate
        I[i] = f.integral(start[i], stop[i])
        
    return I, dt

# ANALYSIS POST-SIMULATION
def find_nearest(array, value):
    idx = (np.abs(array - value)).argmin()
    return idx

def get_dynamical_range(mod):
    '''
    Compute the dynamical range
    '''
    delta = np.zeros(len(mod.Trange))
    delta_norm = np.zeros(len(mod.Trange))
    
    for i in range(len(mod.Exc)):
        # Original matrix
        
        # Get A90 and A10
        Amax, Amin = np.max(mod.Exc[i]), np.min(mod.Exc[i])
        A10, A90 = (Amax-Amin)*0.15 + Amin, (Amax-Amin)*0.85 + Amin
        # Get corresponent index
        s10 = np.where( (A10 > mod.Exc[i][:-1])*(A10 < mod.Exc[i][1:]) )[0][-1]
        s90 = np.where( (A90 > mod.Exc[i][:-1])*(A90 < mod.Exc[i][1:]) )[0][0]
        # Get the s value by linear interpolation
        s10 = (mod.stimuli[s10]-mod.stimuli[s10+1]) / (mod.Exc[i][s10]-mod.Exc[i][s10+1]) * (A10 - mod.Exc[i][s10+1]) + mod.stimuli[s10+1]
        s90 = (mod.stimuli[s90]-mod.stimuli[s90+1]) / (mod.Exc[i][s90]-mod.Exc[i][s90+1]) * (A90 - mod.Exc[i][s90+1]) + mod.stimuli[s90+1]
        
        # Dynamical range
        delta[i] = 10*np.log10(s90 / s10)
    
        # Original matrix
        
        # Get A90 and A10
        Amax, Amin = np.max(mod.Exc_norm[i]), np.min(mod.Exc_norm[i])
        A10, A90 = (Amax-Amin)*0.15 + Amin, (Amax-Amin)*0.85 + Amin
        # Get corresponent index
        s10 = np.where( (A10 > mod.Exc_norm[i][:-1])*(A10 < mod.Exc_norm[i][1:]) )[0][-1]
        s90 = np.where( (A90 > mod.Exc_norm[i][:-1])*(A90 < mod.Exc_norm[i][1:]) )[0][0]
        # Get the s value by linear interpolation
        s10 = (mod.stimuli[s10]-mod.stimuli[s10+1]) / (mod.Exc_norm[i][s10]-mod.Exc_norm[i][s10+1]) * (A10 - mod.Exc_norm[i][s10+1]) + mod.stimuli[s10+1]
        s90 = (mod.stimuli[s90]-mod.stimuli[s90+1]) / (mod.Exc_norm[i][s90]-mod.Exc_norm[i][s90+1]) * (A90 - mod.Exc_norm[i][s90+1]) + mod.stimuli[s90+1]
        
        # Dynamical range
        delta_norm[i] = 10*np.log10(s90 / s10)
        
    return delta, delta_norm

def get_Tc(mod):
    '''
    Get critical parameter, define as the maximum of S2
    '''
    Tc = mod.Trange[np.argmax(mod.S2)] * mod.W_mean
    Tc_norm = mod.Trange[np.argmax(mod.S2_norm)]
    
    return Tc, Tc_norm