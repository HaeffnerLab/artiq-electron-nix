''' Differences from V3: 
 - no more hard coded detection time, dont forget to recompute all arguments'''

import sys
import os
#import datetime import datetime
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.ad53xx import AD53xx
import time
import numpy as np
# from rigol_extraction import * # use artiq for synchronization
# from electron_RS_class import *



#underflow errors happen when you are out of sync in time or trying to define a process in the past
def print_underflow():
    print('RTIO underflow occured')


# Class which defines the pmt counting experiment
class pulse_counting(EnvExperiment):
    def build(self):
         self.setattr_device('core') # need the core for everything
         self.setattr_device('ttl2') # where pulses are being sent in by ttl
         self.setattr_device('ttl8') # use this channel to trigger AOM, connect to AOM
         self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL
         self.setattr_argument('time_count', NumberValue(default=1000,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
         self.setattr_argument('detection_time',NumberValue(default=500,unit='ms',scale=1,ndecimals=0,step=1))
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.set_dataset('count_tot',[-100]*self.time_count,broadcast=True)
        # rigol =  rigol()
        # # parameters for the Rigol waveforms
        # pulse_width_ej = 20.E-9
        # pulse_delay_ej = 2.E-9
        # rigol.run(pulse_width_ej, pulse_delay_ej)

    @kernel
    def run(self):
        self.core.reset()
        # while loop continuously repopulates the graph
        while True:
            # self.scheduler.pause() # allows for "terminate instances" functionality
            # Rigol
            # sampling_time = 2.E-4
            self.counting2()

   

    # @kernel
    # def counting(self):
    #     self.core.break_realtime()

    #     # read the counts and store into a dataset for live updating
    #     for j in range(self.time_count):
    #         #register rising edges for detection time
    #         t_count= self.ttl2.gate_rising(self.detection_time*ms) # reads from the channel
    #         count =self.ttl2.count(t_count)
    #         print(count)
    #         # mutate dataset at index j with the value of counts/second
    #         self.mutate_dataset('count_tot',j,(count)/(self.detection_time*ms))
    #         # delay for as long your listening for, translates between machine time and actual time
    #         delay(self.detection_time*ms)

    
    @kernel
    def counting2(self):
        self.core.reset()
        self.ttl8.on()
        # with parallel:
        for j in range(self.time_count):
            self.core.break_realtime()
            with parallel:
                self.ttl10.pulse(2*us)
                t_count = self.ttl2.gate_rising(self.detection_time*ms)
            # print(t_count)
            # print(now_mu())
                # with sequential:
                # delay(50*us)
                    # for _ in range(n):
                        # ttl_out.pulse(2*us)
                        # delay(2*us)
            # self.mutate_dataset('count_tot',j,self.ttl2.count(now_mu())/(self.detection_time*ms))
            self.mutate_dataset('count_tot',j,self.ttl2.count(t_count)/(self.detection_time*ms))
            # print(self.ttl2.count(now_mu()))
            # print(self.ttl2.count(t_count)/(self.detection_time*ms))