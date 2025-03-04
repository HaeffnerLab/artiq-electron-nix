

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


class tickle_experiment(EnvExperiment):
    def build(self):
         self.setattr_device('core') 
         self.setattr_device('ttl_MCP_in') # ttl2, where MCP pulses are being sent in by ttl
         # self.setattr_device('ttl3') # where sync of extraction pulses are being sent in by ttl
         self.setattr_device('ttl8') # use this channel to trigger AOM, connect to AOM
         self.dds_tickle = self.get_device("dds_tickle")


         self.setattr_device('ttl_Tickle') # ttl9, use this channel to trigger R&S for tickle pulse, connect to R&S
         self.setattr_device('ttl_Extraction') # ttl10, use this channel to trigger extraction pulse, connect to RIGOL external trigger
         self.setattr_device("ttl_TimeTagger") # time tagger start click
         self.setattr_argument('att',NumberValue(default=10,unit='dB',scale=1,ndecimals=0,step=1)) #
         self.setattr_argument('freq_start',NumberValue(default=10,unit='MHz',scale=1,ndecimals=0,step=1)) # tickle freq start
         self.setattr_argument('freq_stop',NumberValue(default=300,unit='MHz',scale=1,ndecimals=0,step=1)) # tickle freq stop
         self.setattr_argument('step_size',NumberValue(default=1,unit='MHz',scale=1,ndecimals=1,step=0.1)) # tickle freq step size
         self.setattr_argument('t_load',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # load time
         self.setattr_argument('t_wait',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # wait time
         self.setattr_argument('number_of_repetitions', NumberValue(default=10000,unit=' ',scale=1,ndecimals=0,step=1)) #how many experiment cycles per data point
         # self.setattr_argument('number_of_datapoints', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot
         self.setattr_argument('t_delay', NumberValue(default=600,unit='ns',scale=1,ndecimals=0,step=1)) # the delay between the extraction pulse and the MCP signal
         self.setattr_argument('time_window_width', NumberValue(default=500,unit='ns',scale=1,ndecimals=0,step=1)) # width of the detection time window
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.number_of_datapoints = int((self.freq_stop - self.freq_start)/self.step_size + 1)
        self.set_dataset('count_tickle',[-50]*self.number_of_datapoints,broadcast=True)

    
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        self.dds_tickle.cpld.init()
        self.dds_tickle.init()
        self.dds_tickle.set_att(self.att*dB)
        
        for i in range(self.number_of_datapoints):
            
            freq_tickle = self.step_size*i+self.freq_start
            t = now_mu()
            self.dds_tickle.set(freq_tickle*MHz, phase=0., ref_time_mu=t)
            self.dds_tickle.sw.on()
            count_tot = 0
            for j in range(self.number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl_390.on()
                    delay(self.t_load*us)
                    with parallel:
                        self.ttl_390.off()
                        self.ttl_Tickle.on()
                    delay(self.t_wait*us)
                    with parallel:
                        self.ttl_Tickle.off()
                        self.ttl_Extraction.pulse(2*us)
                        self.ttl_TimeTagger.pulse(2*us)
                        with sequential:
                            delay(200*ns)
                            self.ttl12.pulse(2*us)
                        with sequential:
                            delay(self.t_delay*ns)
                            t_count = self.ttl_MCP_in.gate_rising(self.time_window_width*ns)
                    count = self.ttl_MCP_in.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(10*us)
            self.dds_tickle.sw.off()
            # cycle_duration = t_load+self.t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            self.mutate_dataset('count_tickle',i,count_tot)


