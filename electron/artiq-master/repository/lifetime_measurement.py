

import sys
import os
#import datetime import datetime
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np

#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')


class lifetime_experiment(EnvExperiment):
    def build(self):
         self.setattr_device('core') 
         self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl
         # self.setattr_device('ttl3') # where sync of extraction pulses are being sent in by ttl
         self.setattr_device('ttl8') # use this channel to trigger AOM, connect to AOM
         self.setattr_device('ttl9') # use this channel to trigger R&S for exciting motion, connect to R&S
         self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL
         self.setattr_argument('t_load',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # loading time
         self.setattr_argument('t_wait_start',NumberValue(default=50,unit='us',scale=1,ndecimals=0,step=1)) # wait time start
         self.setattr_argument('t_wait_stop',NumberValue(default=1050,unit='us',scale=1,ndecimals=0,step=1)) # wait time stop
         self.setattr_argument('number_of_repetitions', NumberValue(default=10000,unit=' ',scale=1,ndecimals=0,step=1)) #how many experiment cycles per data point
         self.setattr_argument('number_of_datapoints', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot
         self.setattr_argument('t_delay', NumberValue(default=600,unit='ns',scale=1,ndecimals=0,step=1)) # the delay between the extraction pulse and the MCP signal
         self.setattr_argument('time_window_width', NumberValue(default=100,unit='ns',scale=1,ndecimals=0,step=1)) # width of the detection time window
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.set_dataset('count_lifetime',[-50]*self.number_of_datapoints,broadcast=True)

   
    @kernel
    def run(self):
        self.core.reset()
        # wait_time = np.logspace(self.t_wait_start,self.t_wait_stop,self.number_of_datapoints)
        # wait_times = [ 1000.,2154.43469003,4641.58883361,10000.,21544.34690032,46415.88833613,100000.,215443.46900319,464158.88336128,1000000.]
        # wait_times = [ 1000,2154,4641,10000,21544,46415,100000,215443,464158,1000000]
        wait_times = [ 1.000,2.154,4.641,10.000,21.544,46.415,100.000,215.443,464.158,1000.000,10000.0,50000.0]
        # wait_times = [ 1.000,2.154,4.641,10.000,21.544,46.415,100.000,215.443,464.158,1000.000]
        for i in range(self.number_of_datapoints):
            count_tot = 0
            t_wait = wait_times[i]
            for j in range(self.number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(self.t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay(t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                        with sequential:
                            delay(self.t_delay*ns)
                            t_count = self.ttl2.gate_rising(self.time_window_width*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(1*us)
            cycle_duration = self.t_load+t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            self.mutate_dataset('count_lifetime',i,count_tot)


