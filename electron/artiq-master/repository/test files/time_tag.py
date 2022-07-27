from artiq.experiment import *
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QComboBox, QGridLayout, QLineEdit, QPlainTextEdit
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
from datetime import datetime
import time
import os
import sys
import csv
from matplotlib import pyplot as plt


class Time_tag(EnvExperiment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0') # artiq DAC
        self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        self.setattr_device('ttl8') # use this channel to trigger AOM, connect to switch near VCO and AOM
        self.setattr_device('ttl9') # use this channel to trigger R&S for tickle pulse, connect to R&S
        self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device("ttl18") # send out sync pulses as ttl10
        self.setattr_device('scheduler') # scheduler used
        self.setattr_device("sampler0")

        self.setattr_argument('bins', NumberValue(default=50,unit=' ',scale=1,ndecimals=0,step=1)) # number of bins in the histogram
        self.setattr_argument('update_cycle', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1))
        self.setattr_argument('t_load',NumberValue(default=250,unit='us',scale=1,ndecimals=0,step=1)) # loading time
        self.setattr_argument('t_wait',NumberValue(default=-100,unit='ns',scale=1,ndecimals=0,step=1)) # wait time
        self.setattr_argument('t_delay', NumberValue(default=500,unit='ns',scale=1,ndecimals=0,step=1)) # the delay between the extraction pulse and the MCP signal
        self.setattr_argument('t_acquisition', NumberValue(default=600,unit='ns',scale=1,ndecimals=0,step=1)) # width of the detection time window
        self.setattr_argument('number_of_repetitions', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many experiment cycles per data point
        self.setattr_argument('number_of_datapoints', NumberValue(default=100,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot
        self.setattr_argument('gate_rising_time',NumberValue(default=61060,unit='ns',scale=1,ndecimals=0,step=1)) 

    def prepare(self):
        # results:
        self.set_dataset('test.bin_times', [-1]*0,broadcast=True) #self.number_of_bins*self.number_of_datapoints,broadcast=True) # Small bins for histogram
        self.pins = [21,22,11,24,25,6,17,13,15,14,8,10,16,12,23,18,4,3,2,1,9,20]
        self.ne = int(len(self.pins)) # number of electrodes
        self.np = 8 # number of experiment parameters
        # self.bins = 50
        self.parameter_list = np.zeros(self.np)
        # self.update_cycle = 10 # artiq will check for user update every 10 experiment cycles
        

    @ kernel
    def kernel_run_optimize_hist(self):
        self.core.reset() # this is important to avoid overflow error
        self.core.break_realtime()
        t_load = np.int32(self.parameter_list[0])
        t_wait = np.int32(self.parameter_list[1])
        t_delay = np.int32(self.parameter_list[2])
        t_acquisition = np.int32(self.parameter_list[3])
        number_of_repetitions = np.int32(self.parameter_list[6])
        number_of_datapoints = np.int32(self.parameter_list[7])

        t_total = t_load*1000+t_wait+t_delay+t_acquisition # cycle duration (ns)
        
        t_bins = 10 # bin width (ns) for histogram
        n_bins = 32000 # int(t_total/t_bins)+1 #bins

        if self.load_dac:
            self.zotino0.init()
            self.core.break_realtime() 
            for pin in range(self.ne):
                delay(500*us)
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])
                index = 10+int(np.rint(self.dac_vs[pin]))
                self.zotino0.write_offset(self.pins[pin],self.offset[self.pins[pin]][index])    
            self.zotino0.load()
            print("Loaded dac voltages")


        for k in range(self.update_cycle):
            
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                t_start = now_mu()
                # tmp = t_total + 1000 
                # t_end = self.ttl2.gate_rising(tmp*ns) 
                t_end = self.ttl2.gate_rising(self.gate_rising_time*ns) # somehow it only works if the gate_rising is within the loop    
                at_mu(t_start)
                self.ttl8.on()
                with parallel:
                    with sequential:
                        delay(t_load*us)   
                        self.ttl8.off()
                    with sequential:
                        delay((t_load*1000+t_wait)*ns) # negative t_wait cause it to output 6/10
                        with parallel:
                            # self.ttl18.pulse(200*ns)
                            self.ttl10.pulse(200*ns)
                delay(300*ns)
            
                # Timestamp events
                tstamp = self.ttl2.timestamp_mu(t_end)
                while tstamp != -1:
                    timestamp = self.core.mu_to_seconds(tstamp)-self.core.mu_to_seconds(t_start)
                    timestamp_us = timestamp*1e9 # in ns scale for now
                    self.append_to_dataset('test.bin_times',timestamp_us)
                    tstamp = self.ttl2.timestamp_mu(t_end)
                    # delay(100*ns) 
            delay(100*ns)
            self.make_hist()

 
# # when number_of_repetition = 30 for example, the output histogram is not evenly distributed in time (increase bins solve the problem)
#         for k in range(self.update_cycle):
#             self.core.break_realtime()
#             t_start = now_mu()
#             # with parallel:
#             t_end = self.ttl2.gate_rising(self.gate_rising_time*ns)    
#             at_mu(t_start)
#             # for j in range(number_of_repetitions):
#             #     self.ttl8.on()
#             #     delay(t_load*us)
#             #     with parallel:
#             #         with sequential:       
#             #             self.ttl8.off()
#             #             delay(300*ns)
#             #         with sequential:
#             #             delay(t_wait*ns) # negative t_wait cause it to output 6/10
#             #             self.ttl10.pulse(200*ns)
#             #     delay(300*ns)

#             for j in range(number_of_repetitions):
#                 self.ttl8.on()
#                 with parallel:
#                     with sequential:
#                         delay(t_load*us)   
#                         self.ttl8.off()
#                     with sequential:
#                         delay((t_load*1000+t_wait)*ns) # negative t_wait cause it to output 6/10
#                         self.ttl10.pulse(200*ns)
#                 delay(300*ns)
            
#             # Timestamp events
#             tstamp = self.ttl2.timestamp_mu(t_end)
#             while tstamp != -1:
#                 timestamp = self.core.mu_to_seconds(tstamp)-self.core.mu_to_seconds(t_start)
#                 timestamp_us = timestamp*1e6
#                 self.append_to_dataset('test.bin_times',timestamp_us)
#                 tstamp = self.ttl2.timestamp_mu(t_end)
#                 delay(100*ns) 
#             delay(100*ns)
#             self.make_hist()



    @ kernel
    def kernel_run_optimize_hist1(self):
        self.core.reset() # this is important to avoid overflow error
        self.core.break_realtime()
        t_load = np.int32(self.parameter_list[0])
        t_wait = np.int32(self.parameter_list[1])
        t_delay = np.int32(self.parameter_list[2])
        t_acquisition = np.int32(self.parameter_list[3])
        number_of_repetitions = np.int32(self.parameter_list[6])
        number_of_datapoints = np.int32(self.parameter_list[7])

        t_total = t_load*1000+t_wait+t_delay+t_acquisition # cycle duration (ns)
        
        t_bins = 10 # bin width (ns) for histogram
        n_bins = 32000 # int(t_total/t_bins)+1 #bins

        if self.load_dac:
            self.zotino0.init()
            self.core.break_realtime() 
            for pin in range(self.ne):
                delay(500*us)
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])
                index = 10+int(np.rint(self.dac_vs[pin]))
                self.zotino0.write_offset(self.pins[pin],self.offset[self.pins[pin]][index])    
            self.zotino0.load()
            print("Loaded dac voltages")
 
# when number_of_repetition = 30 for example, the output histogram is not evenly distributed in time, so we need another sync signal to feed back into artiq as a time reference
        for k in range(self.update_cycle):
            self.core.reset()
            t_start = now_mu()
            t_end = self.ttl2.gate_rising(self.gate_rising_time*ns)    
            at_mu(t_start)
            for j in range(number_of_repetitions):
                self.ttl8.on()
                with parallel:
                    with sequential:
                        delay(t_load*us)   
                        self.ttl8.off()
                    with sequential:
                        delay((t_load*1000+t_wait)*ns) # <5ns t_wait cause it to output 6/10
                        
                        self.ttl10.pulse(200*ns)
                delay(100*ns)
            
            # Timestamp events
            tstamp = self.ttl2.timestamp_mu(t_end)
            while tstamp != -1:
                timestamp = self.core.mu_to_seconds(tstamp)-self.core.mu_to_seconds(t_start)
                timestamp_us = timestamp*1e6
                self.append_to_dataset('test.bin_times',timestamp_us)
                tstamp = self.ttl2.timestamp_mu(t_end)
                delay(100*ns) 
            delay(100*ns)
            self.make_hist()
            self.core.reset()


    def make_hist(self):
        hist_data = self.get_dataset("test.bin_times")
        hist_data = np.array(hist_data)    
        a,b=np.histogram(hist_data,bins=self.bins)           
        self.set_dataset('test.hist_ys', a, broadcast=True)
        self.set_dataset('test.hist_xs', b, broadcast=True)
        return 

    def rolling_run(self):
        self.loadDACoffset()
        self.get_dac_vs() # self.dac_vs = []
        self.get_parameter_list() # self.parameter_list = [200,-100,400,600,0.3,0.3,10,1E4]
        number_of_datapoints = np.int(self.parameter_list[7])

        self.count_tot = 0
        self.count_bins = 0
        
        for i in range(int(number_of_datapoints/self.update_cycle)):
            self.load_dac = False
            self.index = i
            self.check_user_update()
            self.kernel_run_optimize_hist()

    
    def run(self):
        self.rolling_run()
        print("done")

    def get_parameter_list(self):
        self.parameter_list[0] = self.t_load
        self.parameter_list[1] = self.t_wait
        self.parameter_list[2] = self.t_delay
        self.parameter_list[3] = self.t_acquisition
        self.parameter_list[6] = self.number_of_repetitions
        self.parameter_list[7] = self.number_of_datapoints
    
    def get_dac_vs(self):
        self.dac_vs = np.zeros(self.ne)


    def loadDACoffset(self):
        # create list of lines from dataset
        f = '/home/electron/artiq/electron/zotino_offset.txt'
        tmp = np.loadtxt(f)
        offset = np.zeros((tmp.shape[0],tmp.shape[1]+1))
        for i in range(tmp.shape[0]):
            a = np.append(tmp[i],tmp[i][-1])
            offset[i] = a
        self.offset = offset

    def check_user_update(self):
        '''
        flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
        flag_parameter = np.int32(self.get_dataset(key="optimize.flag.p"))
        flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
        if flag_stop == 1:
            for j in range(i*self.update_cycle):
                self.mutate_dataset('test.count_ROI',j,-2)
                self.mutate_dataset('test.countrate_ROI',j,-2)
            print("Experiment terminated")
            return
        if flag_dac == 1:
            # load dac voltages
            self.get_dac_vs()
            self.load_dac = True
            self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True)
        if flag_parameter == 1:
            # t_load, t_wait, t_delay, t_acquisition, number_of_repetitions, number_of_datapoints = self.get_parameter_list()
            self.get_parameter_list()
            self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True)
        '''
        pass
