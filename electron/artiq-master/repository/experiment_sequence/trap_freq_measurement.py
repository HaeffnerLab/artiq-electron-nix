

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


class tickle_experiment(DAC):

    def build(self):
        super().build()
        pulse_sequence.pulse_sequence.build(self)
        start_devices.Devices.build(self)

        self.setattr_device("ccb")
        # self.setattr_argument("output_pulse", BooleanValue(default = True), group = "Main sequence")
    
        self.setattr_argument('att',NumberValue(default=20,unit='dB',scale=1,ndecimals=0,step=1)) #
        self.setattr_argument('freq_start',NumberValue(default=290,unit='MHz',scale=1,ndecimals=0,step=1)) # tickle freq start
        self.setattr_argument('freq_stop',NumberValue(default=300,unit='MHz',scale=1,ndecimals=0,step=1)) # tickle freq stop
        self.setattr_argument('step_size',NumberValue(default=1,unit='MHz',scale=1,ndecimals=1,step=0.1)) # tickle freq step size
        self.setattr_argument('t_load',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # load time
        self.setattr_argument('t_wait',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # wait time

        self.dds_tickle = self.get_device("urukul0_ch0")
        self.setattr_device("ttl12")

    def prepare(self):
        self.number_of_datapoints = int(np.abs(self.freq_stop - self.freq_start)/self.step_size + 1)
        self.trap_freqs = np.linspace(self.freq_start, self.freq_stop, self.number_of_datapoints)
        self.set_dataset('count_tickle',[-50]*self.number_of_datapoints,broadcast=True)
        self.set_dataset('count_tickle_x',self.trap_freqs,broadcast=True)
        self.set_dataset('rid',self.scheduler.rid,broadcast=True)
        print(self.scheduler.rid)
        print(self.trap_freqs)
    
    
    def run(self):
        
        start_devices.Devices.start_rigol(self)
        self.load_DAC()
        # self.kernel_run_initial()
        print("start")
        self.kernel_run_tickle_experiment()
        print("{:d} finished".format(self.scheduler.rid) )

    @ kernel
    def kernel_run_initial(self):
        self.core.reset()
        self.core.break_realtime()
        
        for i in range(self.number_of_datapoints):
            self.core.break_realtime()
            t_wait = 100
            t_load = 100
            n_repetitions = 500
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
    def kernel_run_tickle_experiment(self):

        self.core.reset()
        self.core.break_realtime()
        self.dds_tickle.cpld.init()
        self.dds_tickle.init()
        self.dds_tickle.set_att(self.att*dB)
        
        for i in range(self.number_of_datapoints):
            self.core.break_realtime()
            # freq_tickle = self.step_size*i+self.freq_start
            freq_tickle = self.trap_freqs[i]
            t = now_mu()
            self.dds_tickle.set(freq_tickle*MHz, phase=0., ref_time_mu=t)
            self.dds_tickle.sw.on()
            count_tot = 0
            for j in range(self.n_repetitions):
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
                            t_count = self.ttl_MCP_in.gate_rising(self.t_acquisition*ns)
                    count = self.ttl_MCP_in.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(10*us)
            self.dds_tickle.sw.off()
            # cycle_duration = t_load+self.t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            self.mutate_dataset('count_tickle',i,count_tot)


