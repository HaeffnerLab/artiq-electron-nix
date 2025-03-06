
# 
import sys
import os
#import datetime import datetime
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np

import pulse_sequence
import start_devices
import load_DAC
from load_DAC import DAC

#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')


class lifetime_experiment(DAC):

    def build(self):
        super().build()
        pulse_sequence.pulse_sequence.build(self)
        start_devices.Devices.build(self)

        self.setattr_device("ccb")
        self.setattr_argument('t_wait_start',NumberValue(default=10,unit='us',scale=1,ndecimals=0,step=1)) # 
        self.setattr_argument('t_wait_stop',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) #
        self.setattr_argument('number_of_datapoints',NumberValue(default=10,unit='',scale=1,ndecimals=0,step=1))
        self.setattr_argument('t_load',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # 

        self.setattr_device("ttl12")

    def prepare(self):

        # self.number_of_datapoints = int((self.t_wait_stop - self.t_wait_start)/self.step_size + 1)
        # print(self.number_of_datapoints)
        self.set_dataset('count_lifetime',[-50]*self.number_of_datapoints,broadcast=True)
        # self.wait_times = np.linspace(self.t_wait_start,self.t_wait_stop,self.number_of_datapoints)
        self.wait_times = np.logspace(np.log10(self.t_wait_start),np.log10(self.t_wait_stop),self.number_of_datapoints,base=10.)
        self.set_dataset('count_lifetime_x',self.wait_times,broadcast=True)
        self.set_dataset('rid',self.scheduler.rid,broadcast=True)
        print(self.scheduler.rid)
        print(self.wait_times)
    
    
    def run(self):
        start_devices.Devices.start_rigol(self)
        self.load_DAC()
        self.kernel_run_initial()
        self.kernel_run_lifetime_experiment()

    @ kernel
    def kernel_run_initial(self):
        self.core.reset()
        self.core.break_realtime()
        
        for i in range(self.number_of_datapoints):
            self.core.break_realtime()
            t_wait = 100
            t_load = 100
            n_repetitions = 50000
            count_tot = 0
            for j in range(n_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl_390.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl_390.off()
                        self.ttl_Tickle.on()
                    delay(t_wait*us)
                    with parallel:
                        self.ttl_Tickle.off()
                        self.ttl_Extraction.pulse(2*us)
                        self.ttl_TimeTagger.pulse(2*us)
                        with sequential:
                            delay(200*ns)
                            self.ttl12.pulse(2*us)
                        with sequential:
                            delay(self.t_delay*ns)
                            t_count = self.ttl_MCP_in.gate_rising(self.t_acquisition*ns)
                    count = self.ttl_MCP_in.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(10*us)

    @ kernel
    def kernel_run_lifetime_experiment(self):

        self.core.reset()
        self.core.break_realtime()
        
        for i in range(self.number_of_datapoints):
            self.core.break_realtime()
            t_wait = self.wait_times[i]
            count_tot = 0
            for j in range(self.n_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl_390.on()
                    delay(self.t_load*us)
                    with parallel:
                        self.ttl_390.off()
                        self.ttl_Tickle.on()
                    delay(t_wait*us)
                    with parallel:
                        self.ttl_Tickle.off()
                        self.ttl_Extraction.pulse(2*us)
                        self.ttl_TimeTagger.pulse(2*us)
                        with sequential:
                            delay(200*ns)
                            self.ttl12.pulse(2*us)
                        with sequential:
                            delay(self.t_delay*ns)
                            t_count = self.ttl_MCP_in.gate_rising(self.t_acquisition*ns)
                    count = self.ttl_MCP_in.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(10*us)
            # cycle_duration = t_load+self.t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            self.mutate_dataset('count_lifetime',i,count_tot)



