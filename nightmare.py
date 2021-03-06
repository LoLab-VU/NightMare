from pso import PSO
import theano
import theano.tensor as t
import numpy as np
import pymc
import pylab as plt
from pymc.diagnostics import gelman_rubin

theano.config.exception_verbosity='high'

class Nightmare():
    def __init__(self,model,cost_function,start_parameters,savename,):
        self.model = model
        self.cost_function = cost_function
        self.start_parameters = start_parameters
        self.set_PSO()
        self.savename = savename
        
    def set_PSO(self,):
        self.pso = PSO()
        self.pso.set_cost_function(self.cost_function)
        self.pso.update_w = True
        self.pso.set_start_position(self.start_parameters)
        self.pso.set_bounds(1.0)
        self.pso.set_speed(-0.25,0.25)
        
    def run_pso(self,nchains,nparticles,niterations):
        self.nchains = nchains
        self.pso_results = []
        for _ in range(nchains):
            self.pso.run(nparticles,niterations)
            self.pso_results.append({'params':np.asarray(self.pso.best)})
            self.pso.set_start_position(self.start_parameters)
            self.pso.best = None
    

    
    def run_DREAM(self,nsamples=100000):
        model = pymc.Model()
        with model:
            params = pymc.Normal('params', mu=self.start_parameters, 
                                 sd=np.array([1.0
                                              ]*len(self.start_parameters)),
                                shape=(len(self.start_parameters)))
            #params = pymc.Flat('params',shape=(len(self.start_parameters)))           
              
            global cost_function
            cost_function = self.cost_function
            error = pymc.Potential('error', DREAM_cost(params))
            
            nseedchains = 10*len(self.model.parameters_rules())
            step = pymc.Dream(variables=[params],
                              nseedchains=nseedchains, 
                              blocked=True,
                              start_random=False,
                              save_history=True,
                              parallel=True,
                              adapt_crossover=False,
                              verbose=False,)
         
            trace = pymc.sample(nsamples, step,
                                start=self.pso_results, 
                                njobs=self.nchains,
                                use_mpi=False,
                                progressbar=False,) 

            
            cont_flag = True
            while cont_flag:
                cont_flag = False
                conv_stats = gelman_rubin(trace)
                for i in conv_stats['params']:
                    if i>1.2:
                        print "Parameters have not converged, will continue run."
                        print "Value so far is %s"%i
                        cont_flag = True
                        break
                trace = pymc.sample(int(nsamples*.1), step,
                                    #start=self.pso_results, 
                                    njobs=self.nchains,
                                    use_mpi=False,
                                    trace = trace,
                                    progressbar=False,)
            conv_stats = gelman_rubin(trace)
            for i in conv_stats['params']:
                print i,i<1.2
            #pymc.traceplot(trace,vars=[params,error])
            #plt.show()            
            return trace

@theano.compile.ops.as_op(itypes=[t.dvector], otypes=[t.dscalar])
def DREAM_cost(parameters):
    global cost_function
    like = cost_function(parameters)
    return np.array(-1.*like[0])
            