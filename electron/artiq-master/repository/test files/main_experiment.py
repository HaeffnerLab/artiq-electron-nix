

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


class pulse_counting_ROI(EnvExperiment):
    def build(self):
         self.setattr_device('core') 
         self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl
         self.setattr_device('ttl3') # where sync of extraction pulses are being sent in by ttl
         self.setattr_device('ttl8') # use this channel to trigger AWG
         self.setattr_argument 






         self.setattr_argument('cycle_duration',NumberValue(default=500,unit='us',scale=1,ndecimals=2,step=1)) # half of the time length of one experiment cycle, notice it's only doing something in the first half
         self.setattr_argument('number_of_repetitions', NumberValue(default=1000,unit='#',scale=1,ndecimals=0,step=1)) #how many experiment cycles per data point
         self.setattr_argument('number_of_datapoints', NumberValue(default=1000,unit='#',scale=1,ndecimals=0,step=1)) #how many data points on the plot
         # self.setattr_argument('detection_time',NumberValue(default=500,unit='ms',scale=1,ndecimals=0,step=1))
         self.setattr_argument('delay_time', NumberValue(default=80,unit='ns',scale=1,ndecimals=0,step=1)) # the delay between the extraction pulse and the MCP signal
         self.setattr_argument('time_window_width', NumberValue(default=50,unit='ns',scale=1,ndecimals=0,step=1)) # width of the detection time window
         self.setattr_device('scheduler') # scheduler used

    def prepare(self):
        self.set_dataset('count_ROI',[-1000]*self.number_of_datapoints,broadcast=True)

    @kernel
    def run(self):
        self.core.reset()
        # while loop continuously repopulates the graph
        while True:
            # self.scheduler.pause() # allows for "terminate instances" functionality
            self.counting2()

   

    # @kernel
    # def counting(self):
    #     self.core.break_realtime()

    #     # read the counts and store into a dataset for live updating
    #     for j in range(self.number_of_repetitions):
    #         #register rising edges for detection time
    #         t_count= self.ttl2.gate_rising(self.detection_time*ms) # reads from the channel
    #         count =self.ttl2.count(t_count)
    #         print(count)
    #         # mutate dataset at index j with the value of counts/second
    #         self.mutate_dataset('count_ROI',j,(count)/(self.detection_time*ms))
    #         # delay for as long your listening for, translates between machine time and actual time
    #         delay(self.detection_time*ms)

    
    @kernel
    def counting2(self):
        self.core.reset()
        
        for i in range(self.number_of_datapoints):
            count_tot = 0
            # count_ext = 0
            for j in range(self.number_of_repetitions):
                # self.core.break_realtime()
                with parallel:
                    self.ttl8.pulse(2*us)
                    # self.ttl8.on()
                    # delay(3*self.cycle_duration*us-2*us)
                    with sequential:
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
                        delay(self.delay_time*ns)
                        # print(now_mu())
                        # delay(1*us)
                        t_count = self.ttl2.gate_rising(self.time_window_width*ns)
                        # print(now_mu())
                        count = self.ttl2.count(t_count)
                        if count > 0:
                            count = 1
                        count_tot += count
                        delay(self.cycle_duration*us)
                        # self.ttl8.off()
            print(count_tot)
            # print(count_ext)
            self.mutate_dataset('count_ROI',i,count_tot/(self.number_of_repetitions*self.cycle_duration*us))

                # print(self.ttl2.count(now_mu()))
                # print(self.ttl2.count(t_count)/(self.detection_time*ms))