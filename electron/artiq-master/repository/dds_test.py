

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


class dds_test(EnvExperiment):
    def build(self):
         self.setattr_device('core')
         self.setattr_device('urukul0_ch1')
         self.setattr_device('ttl20') # where MCP pulses are being sent in by ttl
         self.d0 = self.get_device("urukul0_ch0")
         self.d1 = self.get_device("urukul0_ch1")
         self.d2 = self.get_device("urukul0_ch2")
         self.d3 = self.get_device("urukul0_ch3")
         self.setattr_argument('att',NumberValue(default=10,unit='dB',scale=1,ndecimals=0,step=1)) #
         self.setattr_argument('freq',NumberValue(default=100,unit='MHz',scale=1,ndecimals=0,step=1)) # 
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        # self.set_dataset('count_loading',[-50]*self.number_of_datapoints,broadcast=True)
        pass

    
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        self.d0.cpld.init()
        self.d0.init()
        self.d1.init()
        self.d2.init()
        self.d3.init()

        # # This calibration needs to be done only once to find good values.
        # # The rest is happening at each future init() of the DDS.
        # if self.d0.sync_delay_seed == -1:
        #     delay(100*us)
        #     d0, w0 = self.d0.tune_sync_delay()
        #     t0 = self.d0.tune_io_update_delay()
        #     d1, w1 = self.d1.tune_sync_delay()
        #     t1 = self.d0.tune_io_update_delay()
        #     d2, w2 = self.d2.tune_sync_delay()
        #     t2 = self.d0.tune_io_update_delay()
        #     d3, w3 = self.d3.tune_sync_delay()
        #     t3 = self.d0.tune_io_update_delay()
        #     print("sync_delay_seed", [d0, d1, d2, d3])
        #     print("io_update_delay", [t0, t1, t2, t3])
        #     return
        
        # self.d0.set_phase_mode(PHASE_MODE_TRACKING)
        # self.d1.set_phase_mode(PHASE_MODE_TRACKING)
        # self.d2.set_phase_mode(PHASE_MODE_TRACKING)
        # self.d3.set_phase_mode(PHASE_MODE_TRACKING)

        self.d0.set_att(self.att*dB)
        # self.d1.set_att(1*dB)
        # self.d2.set_att(1*dB)
        # self.d3.set_att(1*dB)

        t = now_mu()

        self.d0.set(self.freq*MHz, phase=0., ref_time_mu=t)
        # self.d1.set(40*MHz, phase=0., ref_time_mu=t)
        # self.d2.set(40*MHz, phase=0., ref_time_mu=t)
        # self.d3.set(40*MHz, phase=0., ref_time_mu=t)

        self.ttl20.on()
        
        self.d0.sw.on()

        self.ttl20.pulse(5*us)
        # self.d1.sw.on()
        # self.d2.sw.on()
        # self.d3.sw.on()

        # delay(2*s)
        # self.d1.set(200*MHz)
        # self.d2.set(250*MHz)
        # self.d3.set(20*MHz)
        # delay(2*s)
        # self.d1.set(80*MHz, ref_time_mu=t)
        # self.d2.set(80*MHz, ref_time_mu=t)
        # self.d3.set(80*MHz, ref_time_mu=t)

        #delay(2*us)
        # self.d0.sw.off()
        # self.d1.sw.off()
        # self.d2.sw.off()
        # self.d3.sw.off()

