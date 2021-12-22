

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


class run_experiment(EnvExperiment):
    def build(self):
         self.setattr_device('core')
         self.setattr_device('zotino0') 
         self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
         # self.setattr_device('ttl3') # where sync of extraction pulses are being sent in by ttl
         self.setattr_device('ttl8') # use this channel to trigger AOM, connect to AOM
         self.setattr_device('ttl9') # use this channel to trigger R&S for exciting motion, connect to R&S
         self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
         self.setattr_device('ttl11') # use this channel to reset threshold detector, connect to reset of threshold detector
         self.setattr_argument('t_load',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # loading time
         self.setattr_argument('t_wait',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # wait time
         # self.setattr_argument('cycle_duration',NumberValue(default=500,unit='us',scale=1,ndecimals=2,step=1)) # half of the time length of one experiment cycle, notice it's only doing something in the first half
         self.setattr_argument('number_of_repetitions', NumberValue(default=1000,unit=' ',scale=1,ndecimals=0,step=1)) #how many experiment cycles per data point
         self.setattr_argument('number_of_datapoints', NumberValue(default=1000,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot
         # self.setattr_argument('detection_time',NumberValue(default=500,unit='ms',scale=1,ndecimals=0,step=1))
         self.setattr_argument('t_delay', NumberValue(default=600,unit='ns',scale=1,ndecimals=0,step=1)) # the delay between the extraction pulse and the MCP signal
         self.setattr_argument('time_window_width', NumberValue(default=100,unit='ns',scale=1,ndecimals=0,step=1)) # width of the detection time window
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.set_dataset('count_ROI',[-2]*self.number_of_datapoints,broadcast=True)

    # @kernel
    # def run(self):
    #     self.core.reset()
    #     # while loop continuously repopulates the graph
    #     while True:
    #         # self.scheduler.pause() # allows for "terminate instances" functionality
    #         self.counting2()

    
    @kernel
    def run(self):
        self.core.reset()
        count_tot = 0
        for i in range(self.number_of_datapoints):
            # count_tot = 0
            # count_ext = 0
            for j in range(self.number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(self.t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay(self.t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                        with sequential:
                            # t_extract = self.t_load + self.t_wait + t_delay
                            delay(self.t_delay*ns)
                            t_count = self.ttl2.gate_rising(self.time_window_width*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(1*us)
            # print(count_tot)
            # print(count_ext)
            cycle_duration = self.t_load+self.t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            # self.mutate_dataset('count_ROI',i,count_tot/(self.number_of_repetitions*cycle_duration*us))
            # self.mutate_dataset('count_ROI',i,count_tot/(self.number_of_repetitions*self.time_window_width*ns))
            self.mutate_dataset('count_ROI',i,count_tot)






            #     with parallel:
            #         with sequential:
            #             self.ttl8.on()
            #             delay(self.t_load*us)
            #             self.ttl8.off()
            #             self.ttl9.on()
            #             delay(self.t_wait*us)
            #             self.ttl9.off()
            #             self.ttl10.pulse(2*us)




            #         with sequential:
            #             t_delay = 0.1
            #             pulse_width_ej = 0.1
            #             t_extract = self.t_load + self.t_wait + t_delay
            #             delay(t_extract*us)
            #             t_count = self.ttl2.gate_rising(self.time_window_width*ns)
            #             # print(now_mu())
            #             count = self.ttl2.count(t_count)
            #             if count > 0:
            #                 count = 1
            #             count_tot += count
            #             # delay(self.cycle_duration*us)
            #             # self.ttl8.off()
            # # print(count_tot)
            # # print(count_ext)
            # self.mutate_dataset('count_ROI',i,count_tot/(self.number_of_repetitions*self.cycle_duration*us))


                # print(self.ttl2.count(now_mu()))
                # print(self.ttl2.count(t_count)/(self.detection_time*ms))

                                        # self.core.break_realtime()
                        # print(now_mu())
                        # t_extraction = self.ttl3.gate_rising(self.cycle_duration*us)
                        # print(now_mu())
                        # print(self.ttl3.count(t_extraction))

                        # count_ext += self.ttl3.count(t_extraction)


                        # print(t_count)
                        # print(now_mu())
                            # with sequential:
                            # delay(50*us)
                                # for _ in range(n):
                                    # ttl_out.pulse(2*us)
                                    # delay(2*us)
                        # self.mutate_dataset('count_ROI',j,self.ttl2.count(now_mu())/(self.detection_time*ms))
                        # delay(self.delay_time*ns)
                        # print(now_mu())
                        # delay(1*us)