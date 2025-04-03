

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


class loading_experiment(EnvExperiment):
    def build(self):
         self.setattr_device('core') 
         self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl
         # self.setattr_device('ttl3') # where sync of extraction pulses are being sent in by ttl
         self.setattr_device('ttl8') # use this channel to trigger AOM, connect to AOM
         self.setattr_device('ttl9') # use this channel to trigger R&S for exciting motion, connect to R&S
         self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL
         self.setattr_argument('t_load_start',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # loading time start
         self.setattr_argument('t_load_stop',NumberValue(default=1000,unit='us',scale=1,ndecimals=0,step=1)) # loading time stop
         self.setattr_argument('t_wait',NumberValue(default=1,unit='us',scale=1,ndecimals=0,step=1)) # wait time
         self.setattr_argument('number_of_repetitions', NumberValue(default=10000,unit=' ',scale=1,ndecimals=0,step=1)) #how many experiment cycles per data point
         self.setattr_argument('number_of_datapoints', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot
         self.setattr_argument('t_delay', NumberValue(default=600,unit='ns',scale=1,ndecimals=0,step=1)) # the delay between the extraction pulse and the MCP signal
         self.setattr_argument('time_window_width', NumberValue(default=100,unit='ns',scale=1,ndecimals=0,step=1)) # width of the detection time window
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.set_dataset('count_loading',[-50]*self.number_of_datapoints,broadcast=True)

    
    @kernel
    def run(self):
        self.core.reset()
        # loading_time = np.linspace(self.t_load_start,self.t_load_stop,)
        # loading_time = loading_time.tolist()
        # loading_time = np.linspace(100,1000,10)
        # i = 0
        step = (self.t_load_stop-self.t_load_start)/(self.number_of_datapoints-1)
        for i in range(self.number_of_datapoints):
            # t_load = 100*(i+1)
            t_load = step*i+self.t_load_start
            count_tot = 0
            for j in range(self.number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay(self.t_wait*us)
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
            cycle_duration = t_load+self.t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            self.mutate_dataset('count_loading',i,count_tot)


