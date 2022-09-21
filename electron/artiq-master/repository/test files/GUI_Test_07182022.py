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


class Electron(HasEnvironment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0') # artiq DAC
        self.setattr_device('ttl1')
        self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        self.setattr_device('ttl8') # use this channel to trigger AOM, connect to switch near VCO and AOM
        self.setattr_device('ttl9') # use this channel to trigger R&S for tickle pulse, connect to R&S
        self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device('ttl11') # use this channel to reset threshold detector, connect to reset of threshold detector
        self.setattr_device("ttl12")  # sync ttl pulse as the rigol extraction pulse (440 ns delay to the ejection trigger pulse as of ttl10)
        # self.setattr_device("ttl13")  # sending ttl to shutter motor servo 422
        self.setattr_device("ttl13") # synchronized ttl pulse as the acuiquisition time
        self.setattr_device('scheduler') # scheduler used
        self.setattr_device("sampler0")

        self.setattr_argument('number_of_datapoints', NumberValue(default=5000,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot, run experiment & pulse counting
        self.setattr_argument('number_of_bins', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis, pulse counting

    def prepare(self):
        # for i in ['Grid', 'Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']:
            # self.set_dataset(key="optimize.multipoles."+i, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["bl"]:
        #     for j in ["1","2","3","4","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["br"]:
        #     for j in ["1","2","3","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["tl"]:
        #     for j in ["1","2","3","4","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["tr"]:
        #     for j in ["1","2","3","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.btr4", value=np.float32(0), broadcast=True, persist=False)
        # self.set_dataset(key="optimize.e.t0", value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.b0", value=np.float32(0), broadcast=True, persist=True)
        
        # # flags: indicating changes from GUI, 1 = there is change that needs to be implemented
        # self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True) # electrode voltages
        # self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True) # experiment parameters
        # self.set_dataset(key="optimize.flag.stop", value = 0, broadcast=True, persist=True) # whether or not terminate the experiment

        # # parameters: t_load(us),t_wait(ns),t_delay(ns), t_acquisition(ns),pulse_counting_time(ms), trigger_level (V), # repetitions, # datapoints
        # self.set_dataset(key="optimize.parameter.t_load", value = np.int(100), broadcast=True, persist=True) # t_load(us)
        # self.set_dataset(key="optimize.parameter.t_wait", value = np.int(100), broadcast=True, persist=True) # t_wait(ns)
        # self.set_dataset(key="optimize.parameter.t_delay", value = np.int(600), broadcast=True, persist=True) # t_delay(ns)
        # self.set_dataset(key="optimize.parameter.t_acquisition", value = np.int(100), broadcast=True, persist=True) # t_acquisition(ns)
        # self.set_dataset(key="optimize.parameter.pulse_counting_time", value = np.int(500), broadcast=True, persist=True) # pulse_counting_time(ms)
        # self.set_dataset(key="optimize.parameter.trigger_level", value = 0.3, broadcast=True, persist=True) # trigger level (V)
        # self.set_dataset(key="optimize.parameter.number_of_repetitions", value = np.int(1000), broadcast=True, persist=True) # number of repetitions
        # self.set_dataset(key="optimize.parameter.number_of_datapoints", value = np.int(5000), broadcast=True, persist=True) # number of datapoints


        # self.set_dataset(key="optimize.e.br4", value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.tr4", value=np.float32(0), broadcast=True, persist=True)


        # results:
        self.set_dataset('optimize.result.count_tot',[-100]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 in pusle counting
        self.set_dataset('optimize.result.count_PI',[-10]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 in shutter optimize
        self.set_dataset('optimize.result.count_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI in optimize
        self.set_dataset('optimize.result.countrate_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI in optimize without accumulating
        self.set_dataset('count_threshold',[-200]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 from threshold detector
        self.set_dataset('optimize.result.bin_times', [-1]*0,broadcast=True) #self.number_of_bins*self.number_of_datapoints,broadcast=True) # Small bins for histogram
        # self.set_dataset('optimize.result.xs', [0,1,2,3,4,5,6],broadcast=False) # Small bins for histogram
        #self.set_dataset('optimize.result.h_bins', [0,2,4,6],broadcast=False) # Small bins for histogram
        #self.set_dataset('optimize.result.h_counts', np.array([[2,0,0],[1,0,0]]),broadcast=False) # Small bins for histogram
        #self.set_dataset('optimize.result.h_counts', np.array([[0,3],[1,2],[2,1],[0,2],[1,3],[2,1]]),broadcast=True) # Small bins for histogram
        


        # # electrodes: [bl1,...,bl5,br1,...,br5 (except br4),tl1,...,tl5,tr1,...,tr5 (except tr4),btr4,t0,b0], notice br4 and tr4 are shorted together, channel 3
        # self.pins = [13,15,17,19,21,23,7,5,1,24,2,26,28,30,9,20,18,14,16, 4,11] # Unused dac channels: 0 (bad),3 (original br4), 6,8,10,12,22 (bad) ,25,27,29,31

        # electrodes: [bl1,...,bl5,br1,...,br5,tl1,...,tl5,tr1,...,tr5,t0,b0]
        self.pins = [13,15,17,19,21,23,7,5,3,1,24,2,26,28,30,9,20,18,16,14,4,11] # Unused dac channels: 0 (bad), 6,8,10,12,22 (bad) ,25,27,29,31


        self.ne = int(len(self.pins)) # number of electrodes
        self.np = 8 # number of experiment parameters
    
    def launch_GUI(self):       
        #launch GUI
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        MainWindow = QtWidgets.QMainWindow()
        self.setupUi(MainWindow) 
        MainWindow.show()
        ret = app.exec_()

    def run(self):
        return
        
    def setupUi(self, win):
        self.title = 'Electron'
        self.left = 0
        self.top = 0
        self.width = 1200 # 600
        self.height = 600 # 200
        win.setWindowTitle(self.title)
        win.setGeometry(self.left, self.top, self.width, self.height)
        self.tab_widget = MyTabWidget(self,win)

        
        # print("testing function without GUI (for debugging)")
        # self.tab_widget.on_run_click_main()
        

        win.setCentralWidget(self.tab_widget)

    @ kernel
    def shut_off(self):
        self.ttl8.off()
        self.ttl9.off()
        self.ttl10.off()
        self.ttl11.off()
        self.core.reset()


    @ kernel
    def set_threshold_voltages(self):
        self.core.break_realtime()
        self.zotino0.init()
        delay(500*us)
        self.zotino0.write_dac(6,3.3)
        self.zotino0.load()

    def get_dac_vs(self):
        dac_vs = []
        for i in ["bl"]:
            for j in ["1","2","3","4","5"]:
                dac_vs.append(self.get_dataset(key="optimize.e."+i+j))
        for i in ["br"]:
            for j in ["1","2","3","4", "5"]:
                dac_vs.append(self.get_dataset(key="optimize.e."+i+j))
        for i in ["tl"]:
            for j in ["1","2","3","4","5"]:
                dac_vs.append(self.get_dataset(key="optimize.e."+i+j))
        for i in ["tr"]:
            for j in ["1","2","3","4", "5"]:
                dac_vs.append(self.get_dataset(key="optimize.e."+i+j))
        # dac_vs.append(self.get_dataset(key="optimize.e.btr4"))
        # self.set_dataset(key="optimize.e.t0",value = -9.00, broadcast=True, persist=True)
        dac_vs.append(self.get_dataset(key="optimize.e.t0"))
        dac_vs.append(self.get_dataset(key="optimize.e.b0"))
        
        self.dac_vs = dac_vs
        # return dac_vs

    def get_parameter_list(self):
        parameter_list = [] # note this is only in int type, trigger level = 0
        for i in ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints"]:
            # parameter_list.append(np.int(self.get_dataset(key="optimize.parameter."+i)))
            parameter_list.append(self.get_dataset(key="optimize.parameter."+i))
        self.parameter_list = parameter_list

    @ kernel
    def kernel_run_optimize (self,i,load_dac,update_cycle):
        #print("kernel run optimize is runnning")
        self.core.break_realtime()
        t_load = np.int32(self.parameter_list[0])
        t_wait = np.int32(self.parameter_list[1])
        t_delay = np.int32(self.parameter_list[2])
        t_acquisition = np.int32(self.parameter_list[3])
        trigger_level = self.parameter_list[5]
        number_of_repetitions = np.int32(self.parameter_list[6])
        number_of_datapoints = np.int32(self.parameter_list[7])
        
        if load_dac:
            self.zotino0.init()
            self.core.break_realtime() 
            for pin in range(self.ne):
                delay(500*us)
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])    
            self.zotino0.load()
            print("Loaded dac voltages")

        pulseindex = 0
        for k in range(update_cycle):
            countrate_tot = 0 
            
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay(t_wait*ns)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                        with parallel:
                            with sequential:
                                delay(440*ns)
                                self.ttl12.pulse(1*us)
                            with sequential:
                                # t_extract = self.t_load + self.t_wait + t_delay
                                delay(t_delay*ns)
                                with parallel:
                                    with sequential:
                                        delay(20*ns)
                                        self.ttl13.pulse(t_acquisition*ns)

                                    t_count = self.ttl2.gate_rising(t_acquisition*ns)


                                    

                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    self.count_tot += count
                    countrate_tot += count
                    delay(1*us)
            self.mutate_dataset('optimize.result.count_ROI',i*update_cycle+k,self.count_tot)
            self.mutate_dataset('optimize.result.countrate_ROI',i*update_cycle+k,countrate_tot)

    @ kernel
    def kernel_run_optimize_hist(self,i,load_dac,update_cycle):

        # print("kernel run optimize hist is running")
        self.core.break_realtime()
        t_load = np.int32(self.parameter_list[0])
        t_wait = np.int32(self.parameter_list[1])
        t_delay = np.int32(self.parameter_list[2])
        t_acquisition = np.int32(self.parameter_list[3])
        number_of_repetitions = np.int32(self.parameter_list[6])
        number_of_datapoints = np.int32(self.parameter_list[7])
        
        t_bins = 10 # bin width (ns) for histogram
        t_total = t_load*1000+t_wait+t_delay+t_acquisition # cycle duration (ns)
        n_bins = 32000 # int(t_total/t_bins)+1 #bins

        if load_dac:
            self.zotino0.init()
            self.core.break_realtime() 
            for pin in range(self.ne):
                delay(500*us)
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])    
            self.zotino0.load()
            print("Loaded dac voltages")


        for k in range(update_cycle):
            # countrate_tot = 0
            # self.reset_time_tag()

            for j in range(number_of_repetitions):


                self.core.break_realtime()
            
                with parallel:
                    
                    #experiment cycle
                    with parallel:
                        with sequential:
                            self.ttl8.on()
                            delay(t_load*us)
                            self.ttl8.off()
                        with sequential:
                            delay(t_load*us+t_wait*ns)
                            self.ttl10.pulse(50*ns)

            
                        
        
                        with parallel:
                            
                            # self.ttl10.pulse(2*us)
                            with parallel:
                                with sequential:
                                    delay(440*ns)
                                    self.ttl12.pulse(1*us)
                                with sequential:
                                    delay(t_delay*ns)
                                    with sequential:
                                        delay(20*ns)
                                        self.ttl13.pulse(t_acquisition*ns)

                    # Parallel with experiment cycle
                    with sequential:

                        # Set start time and open input channel
                        t_start = now_mu()
                        t_end = self.ttl2.gate_rising(t_total*ns) #opens gate for rising edges to be detected on TTL2 for 250 us
                        
                        # Timestamp events
                        tstamp=self.ttl2.timestamp_mu(t_end)

                        # Add timestamp to dataset
                        while tstamp != -1:
                            timestamp = self.core.mu_to_seconds(tstamp)-self.core.mu_to_seconds(t_start)
                            timestamp_us = timestamp*10**6
                            self.append_to_dataset('optimize.result.bin_times',timestamp_us)
                            tstamp=self.ttl2.timestamp_mu(t_end)
                            delay(10*ns) 

            # self.make_hist()

     


                     

    def reset_time_tag(self):
        self.hist = np.zeros(5)
        return
    def time_tag(self,bin_,count):
        self.hist = count
        return
    def update_hist(self):
        print('updating histogram')
        
        return 

    def make_hist(self):

        hist_data = self.get_dataset("optimize.result.bin_times")
        hist_data = np.array(hist_data)
        #np.save('/home/electron/Desktop/hist_data.npy', hist_data)
        #print("timestamp list:", hist_data)

        #range_timestamps = round(max(hist_data)) #us
        #self.set_dataset('optimize.result.bin_boundaries', np.arange(0,range_timestamps,1), broadcast=True)


        '''
        hist_final = [0]*(round(max(hist_data))+1)
        self.set_dataset('optimize.result.final_hist', hist_final, broadcast=True)


        # for n in hist_data:
        #     i = round(n)
        #     hist_final[i] += 1
        '''
        # a,b,c=plt.hist(hist_data,50)
        a,b,c=plt.hist(hist_data[(hist_data > 1 ) & (hist_data<1000)],50)           

        self.set_dataset('optimize.result.hist_ys', a, broadcast=True)
        self.set_dataset('optimize.result.hist_xs', b, broadcast=True)

        # print(b)

        return 


    def rolling_optimize(self):
        self.get_dac_vs()
        # print("dac_vs",self.dac_vs)
        self.get_parameter_list()
        # print("parameter_list",self.parameter_list)
        self.count_tot = 0
        self.count_bins = 0
        number_of_datapoints = np.int(self.parameter_list[7])
        update_cycle = 10 # artiq will check for user update every 10 experiment cycles


        for i in range(int(number_of_datapoints/update_cycle)):
            load_dac = False
            flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
            flag_parameter = np.int32(self.get_dataset(key="optimize.flag.p"))
            flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
            if flag_stop == 1:
                for j in range(i*update_cycle):
                    self.mutate_dataset('optimize.result.count_ROI',j,-2)
                    self.mutate_dataset('optimize.result.countrate_ROI',j,-2)
                print("Experiment terminated")
                return
            
            if flag_dac == 1:
                # load dac voltages
                self.get_dac_vs()
                load_dac = True
                self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True)
            if flag_parameter == 1:
                # t_load, t_wait, t_delay, t_acquisition, number_of_repetitions, number_of_datapoints = self.get_parameter_list()
                self.get_parameter_list()
                self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True)

            hist = True
            if hist:
                self.kernel_run_optimize_hist(i,load_dac,update_cycle)
            else:
                self.kernel_run_optimize(i,load_dac,update_cycle)


    
    @ kernel
    def set_dac_voltages(self,dac_vs):
        # self.core.reset()
        
        self.core.break_realtime() 
        self.zotino0.init()
        # self.core.break_realtime() 
        for pin in range(self.ne):
            delay(500*us)

            #if dac_vs[pin] < 10:
            self.zotino0.write_dac(self.pins[pin],dac_vs[pin])    
            #else:
                #print(f"WARNING: pin {self.pins[pin]} was not updated (votage {dac_vs[pin]} exceeds voltage limit")
        self.zotino0.load()

    @kernel
    def kernel_run_shutter_optimize(self, j=0, load_dac=False, N=20, detection_time=500):
        '''N is the number of datapoints taken for each configuration
        '''

        self.core.break_realtime()

        if load_dac:
            self.zotino0.init()
            self.core.break_realtime() 
            for pin in range(self.ne):
                delay(500*us)
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])    
            self.zotino0.load()
            print("Loaded dac voltages")
        
        # self.core.break_realtime()
        if j == 0:
            self.ttl8.on()

        # count electrons with both 422 and 390 on
        count_on = 0
        count_off = 0
        for i in range(N):
            with parallel:
                self.ttl10.pulse(2*us)
                t_count = self.ttl2.gate_rising(detection_time*ms)
            count_on += self.ttl2.count(t_count)/(detection_time*ms)
            self.mutate_dataset('optimize.result.count_PI',i+j*2*N,self.ttl2.count(t_count)/(detection_time*ms))

        # then block 390 to count 422 background scatter              
        self.ttl12.off()   
        self.ttl12.pulse(100*ms)
        delay(20*ms)
        self.ttl12.pulse(100*ms)
        delay(2*s) # it takes a long time for the motor to rotate


        # count electrons with only 422
        for i in range(N):
            with parallel:
                self.ttl10.pulse(2*us)
                t_count = self.ttl2.gate_rising(detection_time*ms)
            count_off += self.ttl2.count(t_count)/(detection_time*ms)
            self.mutate_dataset('optimize.result.count_PI',i+N+j*2*N,self.ttl2.count(t_count)/(detection_time*ms))

        count_PI = (count_on-count_off)/N
        print(f"PI electrons = {count_PI}")


    def shutter_optimize(self):
        detection_time = np.int32(self.parameter_list[4])
        # with parallel:
        N = 20
        for j in range(int(self.number_of_datapoints/2/N)):
            print("Move the stage:")
            sleep(5) # wait for the user to move the stage
            load_dac = False
            flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
            flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
            if flag_stop == 1:
                for i in range(j*2*N):
                    self.mutate_dataset('optimize.result.count_PI',i,-100)
                print("Experiment terminated")
                return
            if flag_dac == 1:
                # load dac voltages
                dac_vs = self.get_dac_vs()
                load_dac = True
                self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True)
            print("Start counting...")
            self.kernel_run_shutter_optimize(j,load_dac, N, detection_time)


    @kernel
    def kernel_run_pulse_counting(self,j,load_dac,detection_time):
        self.core.break_realtime()
        if load_dac:
            self.zotino0.init()
            self.core.break_realtime() 
            for pin in range(self.ne):
                delay(500*us)


                #if self.dac_vs[pin] < 10:
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])    
                #else:
                    #print("WARNING: pin", self.pins[pin], "was not updated (votage", self.dac_vs[pin],  "exceeds voltage limit)")    
            self.zotino0.load()
            print("Loaded dac voltages")

        # self.core.break_realtime()
        if j == 0:
            self.ttl8.on() # AOM
        # with parallel:
        #     self.ttl10.pulse(2*us) # extraction pulse
        #     t_count = self.ttl2.gate_rising(detection_time*ms)

        # self.mutate_dataset('optimize.result.count_tot',j,self.ttl2.count(t_count)/(detection_time*ms))

        # N = 5000
        # self.core.break_realtime()
        # t_count = self.ttl2.gate_rising(detection_time*ms)
        # for i in range(N):
        #     # self.core.break_realtime()
        #     with parallel:
        #         with parallel:
        #             self.ttl10.pulse(2*us) # extraction pulse
        #             with sequential:
        #                 delay(440*ns)
        #                 self.ttl12.pulse(1*us)
                
        # count = self.ttl2.count(t_count)

        self.core.break_realtime()
        
        with parallel:
            t_count = self.ttl2.gate_rising(detection_time*ms)
            self.ttl10.pulse(2*us) # extraction pulse
            with sequential:
                delay(440*ns)
                self.ttl10.pulse(1*us)
                
        count = self.ttl2.count(t_count)


        self.mutate_dataset('optimize.result.count_tot',j,count/(detection_time*ms))
        # self.mutate_dataset('optimize.result.count_tot',j,count)
# 
#     @kernel
#     def kernel_run_pulse_counting_hist(self,j,load_dac,detection_time):
#         self.core.break_realtime()
#         if load_dac:
#             self.zotino0.init()
#             self.core.break_realtime() 
#             for pin in range(self.ne):
#                 delay(500*us)
#                 self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])    
#             self.zotino0.load()
#             print("Loaded dac voltages")

#         # self.core.break_realtime()
#         if j == 0:
#             self.ttl8.on() # AOM
#         # with parallel:
#         #     self.ttl10.pulse(2*us) # extraction pulse
#         #     t_count = self.ttl2.gate_rising(detection_time*ms)

#         # self.mutate_dataset('optimize.result.count_tot',j,self.ttl2.count(t_count)/(detection_time*ms))

#         count = 0
#         N = 5000
#         for i in range(N):
#             self.core.break_realtime()
#             with parallel:
#                 with parallel:
#                     self.ttl10.pulse(2*us) # extraction pulse
#                     with sequential:
#                         delay(440*ns)
#                         self.ttl12.pulse(1*us)
            
#                     t_count = self.ttl2.gate_rising(detection_time*1000/N*us)
#                     #tstamp = self.ttl2.timestamp_mu(detection_time*1000/N*us)
#                 #print(tstamp)
#             count += self.ttl2.count(t_count)

# # 
#         # self.mutate_dataset('optimize.result.count_tot',j,count/(detection_time*ms))
#         self.mutate_dataset('optimize.result.count_tot',j,count)


    def pulse_counting(self):
        detection_time = np.int32(self.parameter_list[4])
        # with parallel:
        for j in range(self.number_of_datapoints):
            load_dac = False
            flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
            flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
            if flag_stop == 1:
                for i in range(j):
                    self.mutate_dataset('optimize.result.count_tot',i,-100)
                print("Experiment terminated")
                return
            if flag_dac == 1:
                # load dac voltages
                dac_vs = self.get_dac_vs()
                load_dac = True
                self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True)
            self.kernel_run_pulse_counting(j,load_dac, detection_time)
            
         
    @kernel
    def threshold_detector_test(self,trigger_level,number_of_datapoints,number_of_repetitions,t_load,t_wait,t_delay,t_acquisition): # zotino8 for trigger, zotino 6 give 3.3 V
        self.set_dataset('count_threshold',[-200]*number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 from threshold detector
        self.core.reset()
        count_tot = 0
        self.zotino0.init()
        delay(500*us)
        self.zotino0.write_dac(8,trigger_level)
        self.zotino0.write_dac(6,3.3)
        self.zotino0.load()

        for i in range(number_of_datapoints):
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay((t_wait-2)*us)
                    with parallel:
                        delay(2*us)
                        self.ttl11.pulse(2*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)

                        with sequential:
                            # t_extract = self.t_load + self.t_wait + t_delay
                            delay(t_delay*ns)
                            t_count = self.ttl2.gate_rising(t_acquisition*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(1*us)
            cycle_duration = t_load+t_wait+2+t_delay/1000+t_acquisition/1000+1
            self.mutate_dataset('count_threshold',i,count_tot)

import vxi11
import matplotlib.pyplot as plt

class rigol():
    def __init__(self,ip=113,pulse_width_ej=800.E-9, pulse_delay_ej=2.E-9,offset_ej=-5,amplitude_ej=20,phase=270,period_ej=1000.E-9,sampling_time=2.E-9):
        # self.sampling_time = sampling_time # 
        
        # initial phase != 0, voltage 0 ~ -20 V, need to manually adjust and see on the scope or AWG
        self.pulse_width_ej = pulse_width_ej
        self.pulse_delay_ej = pulse_delay_ej
        self.offset_ej = offset_ej
        self.amplitude_ej = amplitude_ej
        self.phase = phase
        self.period_ej = period_ej
        self.sampling_time = sampling_time
        # self.inst = vxi11.Instrument('TCPIP0::192.168.169.113::INSTR')
        self.inst = vxi11.Instrument('TCPIP0::192.168.169.'+str(ip)+'::INSTR')
       

    def run(self):
        inst = self.inst
        inst.write("OUTPUT2 OFF")
        inst.write("OUTPUT1 OFF")   
        # hardcode sampling rate for ejection pulse, since only need the first few hundred ns
        waveform_ej = np.zeros(int(self.period_ej/self.sampling_time))
        waveform_ej[:] = -1
        waveform_ej[np.int(self.pulse_delay_ej/self.sampling_time):np.int((self.pulse_delay_ej+self.pulse_width_ej)/self.sampling_time)] = 1
        ej_str = ",".join(map(str,waveform_ej))
        
        # inst.write(":OUTPut1:LOAD INFinity")
        # inst.write("SOURCE1:PERIOD {:.9f}".format(self.period_ej))
        # # print(inst.ask("SOURCE2:PERIOD?"))
        # inst.write("SOURCE1:VOLTage:UNIT VPP")
        # inst.write("SOURCE1:VOLTage {:.3f}".format(self.amplitude_ej))
        # inst.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(self.offset_ej))
        # inst.write("SOURCE1:TRACE:DATA VOLATILE,"+ ej_str)
        # # inst.write("SOURCE2:PHASe 20")
        
        # inst.write("SOURce1:BURSt ON")
        # # inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
        # inst.write("SOURce1:BURSt:GATE:POL INVerted")

        # inst.write("SOURce1:BURSt:PHASe {:.3f}".format(self.phase))


        # inst.write("SOURce1:BURSt:MODE TRIGgered")
        # inst.write("SOURce1:BURSt:NCYCles 1")
        # # inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
        # inst.write("SOURCe1:BURSt:TRIGger:SOURce EXTernal")
        # inst.write("SOURce1:BURSt:TRIGger:SLOPe POSitive")

        # Channel 2
        inst.write(":OUTPut2:LOAD INFinity")
        inst.write("SOURCE2:PERIOD {:.9f}".format(self.period_ej))
        # print(inst.ask("SOURCE2:PERIOD?"))
        inst.write("SOURCE2:VOLTage:UNIT VPP")
        inst.write("SOURCE2:VOLTage {:.3f}".format(self.amplitude_ej))
        inst.write("SOURCE2:VOLTage:OFFSet {:.3f}".format(self.offset_ej))
        inst.write("SOURCE2:TRACE:DATA VOLATILE,"+ ej_str)
        # inst.write("SOURCE2:PHASe 20")
        
        inst.write("SOURce2:BURSt ON")
        # inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
        # inst.write("SOURce2:BURSt:GATE:POL INVerted")

        inst.write("SOURce2:BURSt:PHASe {:.3f}".format(self.phase))


        inst.write("SOURce2:BURSt:MODE TRIGgered")
        inst.write("SOURce2:BURSt:NCYCles 1")
        # inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
        inst.write("SOURCe2:BURSt:TRIGger:SOURce EXTernal")
        inst.write("SOURce2:BURSt:TRIGger:SLOPe POSitive")


        # ###### use channel one to extrac on the bottom two central electrodes
        waveform_ej = np.zeros(int(self.period_ej/self.sampling_time))
        waveform_ej[:] = 1
        waveform_ej[np.int(self.pulse_delay_ej/self.sampling_time):np.int((self.pulse_delay_ej+self.pulse_width_ej)/self.sampling_time)] = -1
        ej_str = ",".join(map(str,waveform_ej))
        # Channel 1
        inst.write(":OUTPut1:LOAD INFinity")
        inst.write("SOURCE1:PERIOD {:.9f}".format(self.period_ej))
        # print(inst.ask("SOURCE2:PERIOD?"))
        inst.write("SOURCE1:VOLTage:UNIT VPP")
        inst.write("SOURCE1:VOLTage {:.3f}".format(self.amplitude_ej))
        inst.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(-1*self.offset_ej))
        inst.write("SOURCE1:TRACE:DATA VOLATILE,"+ ej_str)
        # inst.write("SOURCE2:PHASe 20")
        
        inst.write("SOURce1:BURSt ON")
        # inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
        inst.write("SOURce1:BURSt:GATE:POL NORMal")

        # inst.write("SOURce1:BURSt:PHASe {:.3f}".format(self.phase))


        inst.write("SOURce1:BURSt:MODE TRIGgered")
        inst.write("SOURce1:BURSt:NCYCles 1")
        # inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
        inst.write("SOURCe1:BURSt:TRIGger:SOURce EXTernal")
        inst.write("SOURce1:BURSt:TRIGger:SLOPe POSitive")


        inst.write("OUTPUT1 ON")
        inst.write("OUTPUT2 ON")
        return


# Creating tab widgets
class MyTabWidget(HasEnvironment,QWidget):
    
    def __init__(self, Env, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.HasEnvironment = Env
        self.setup_UI()
        self.ne = self.HasEnvironment.ne
        self.e=np.full(self.ne, 0.0)    
    
    def set_dac_voltages(self,dac_vs):
        self.HasEnvironment.set_dac_voltages(dac_vs)

    def setup_UI(self):
  
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()
        self.tabs.resize(300, 150)
  
        # Add tabs
        
        # self.tabs.addTab(self.tab2, "MULTIPOLES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        # self.tabs.addTab(self.tab3, "PARAMETERS")
        self.tabs.addTab(self.tab4, "Main Experiment") # This tab could mutate dac_voltage, parameters, flags dataset and run_self_updated
        self.tabs.addTab(self.tab1, "ELECTRODES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        self.tabs.addTab(self.tab5, "DEVICES")
        self.tabs.addTab(self.tab6, "Cryostat")
    
          
        '''
        ELECTRODES TAB
        '''
        grid1 = QGridLayout()  
        self.ELECTRODES = []  # Labels for text entry
        for n in ['tl', 'tr', 't0', 'bl', 'br', 'b0']:
            self.electrode_sec = [] #electrode sections
            if n=='t0' or n=='b0':
                ei = n + ":"
                self.electrode_sec.append(ei)
            else:
                for i in range(1,6):
                    ei = n + f'{i}:'
                    self.electrode_sec.append(ei)
            self.ELECTRODES.append(self.electrode_sec)
        self.ELECTRODES.append('t0:')
        self.ELECTRODES.append('b0:')

        # print(self.ELECTRODES)
        # print:[['tl1:', 'tl2:', 'tl3:', 'tl4:', 'tl5:'], ['tr1:', 'tr2:', 'tr3:', 'tr4:', 'tr5:'], ['t0:'], ['bl1:', 'bl2:', 'bl3:', 'bl4:', 'bl5:'], ['br1:', 'br2:', 'br3:', 'br4:', 'br5:'], ['b0:'], 't0:', 'b0:']

        self.electrodes = []
        
        #[values (from list), x-coord (label), x-coord (entryBox), y-coord (first entry)]
        self.bl_electrodes = [0,0,1,4] 
        self.br_electrodes = [1,4,5,4]
        self.tl_electrodes = [3,0,1,10]
        self.tr_electrodes = [4,4,5,10]

        
        #electrode grid
        for e in [self.tl_electrodes, self.tr_electrodes, self.bl_electrodes, self.br_electrodes]:            
            
            el_values = e[0]
            xcoord_label = e[1]
            xcoord_entry = e[2]
            ycoord = e[3]
            
            for i in range(len(self.ELECTRODES[el_values])):
                spin = QtWidgets.QDoubleSpinBox(self)
                spin.setRange(-10,10)
                spin.setSingleStep(0.1)
                # spin.setValue(self.default_voltages[index_v]) # set default values
                # index_v += 1
                grid1.addWidget(spin,ycoord-i,xcoord_entry,1,1)
                self.electrodes.append(spin)
                label = QLabel('       '+self.ELECTRODES[el_values][i], self)
                label.setAlignment(QtCore.Qt.AlignRight)
                grid1.addWidget(label,ycoord-i,xcoord_label,1,1)
        
        #spacing
        label_gap = QLabel('', self)
        grid1.addWidget(label_gap,5,1,1,1)
        
        #t0
        spin_t0 = QtWidgets.QDoubleSpinBox(self)
        spin_t0.setRange(-10,10)
        spin_t0.setSingleStep(0.1)
        # spin_t0.setValue(self.default_voltages[-2])
        grid1.addWidget(spin_t0,1,3,1,1)
        self.electrodes.append(spin_t0)
        label_t0 = QLabel('       '+self.ELECTRODES[2][0], self)
        label_t0.setAlignment(QtCore.Qt.AlignRight)
        grid1.addWidget(label_t0,1,2)

        #b0
        spin_b0 = QtWidgets.QDoubleSpinBox(self)
        spin_b0.setRange(-10,10)
        spin_b0.setSingleStep(0.1)
        # spin_b0.setValue(self.default_voltages[-1])
        grid1.addWidget(spin_b0,7,3,1,1)
        self.electrodes.append(spin_b0)
        label_b0 = QLabel('       '+self.ELECTRODES[5][0], self)
        label_b0.setAlignment(QtCore.Qt.AlignRight)
        grid1.addWidget(label_b0,7,2,1,1)        

        # add textbox color
        for el in self.electrodes:
            el.editingFinished.connect(lambda el=el: self.change_background(el))
       
        # add voltage button
        v_button = QPushButton('Set Voltage values', self)
        v_button.clicked.connect(self.on_voltage_click)
        grid1.addWidget(v_button, 0, 6, 2, 1)
        
        #add grid layout (grid1) to tab1
        grid1.setRowStretch(4, 1)
        self.tab1.setLayout(grid1)
        
        #set electrode values for dataset
        self.e=self.electrodes
        

        '''
        MAIN EXPERIMENT TAB
        '''
        grid4 = QGridLayout() #make grid layout
        
        self.parameter_list = []  
        #create parameter text entry boxes
        # self.default = [100,100,600,100,500,0.3,1000,1000] # default values
        self.default_parameter = self.get_default_parameter() # read data from dataset
        PARAMETERS1 = ['Load time (us):', 'Wait time (ns):', 'Delay time (ns):','Acquisition time(ns):' ]
        DEFAULTS1 = self.default_parameter[0:4] # default values

        for i in range(len(PARAMETERS1)):  
            spin = QtWidgets.QSpinBox(self)
            spin.setRange(-10000000,10000000)
            spin.setSingleStep(10)
            spin.setValue(DEFAULTS1[i]) # set default values
            grid4.addWidget(spin,i+13,1,1,1)
            self.parameter_list.append(spin)
            label = QLabel('    '+PARAMETERS1[i], self)
            grid4.addWidget(label,i+13,0,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid4.addWidget(label_gap,0,2,1,2)


        PARAMETERS2 = ['Pulse counting time (ms):', 'Trigger level (V):', '# Repetitions:', '# Datapoints:']
        DEFAULTS2 = self.default_parameter[4:] # default values
        for i in range(len(PARAMETERS2)):
            if i == 1:
                spin = QtWidgets.QDoubleSpinBox(self)
                spin.setRange(0,10)
                spin.setSingleStep(0.01)
                spin.setValue(DEFAULTS2[i]) # set default values
                grid4.addWidget(spin,i+13,5,1,1)
                self.parameter_list.append(spin)
                label = QLabel('    '+PARAMETERS2[i], self)
                grid4.addWidget(label,i+13,4,1,1)
            else:
                spin = QtWidgets.QSpinBox(self)
                spin.setRange(0,100000)
                spin.setSingleStep(10)
                spin.setValue(DEFAULTS2[i]) # set default values
                self.parameter_list.append(spin)
                grid4.addWidget(spin,i+13,5,1,1)
                label = QLabel('    '+PARAMETERS2[i], self)
                grid4.addWidget(label,i+13,4,1,1)        
    
        #[values (from list), x-coord (label), x-coord (entrtyBox), y-coord (first entry)]
        self.bl_electrodes0 = [0,0,1,4] 
        self.br_electrodes0 = [1,4,5,4]
        self.tl_electrodes0 = [3,0,1,10]
        self.tr_electrodes0 = [4,4,5,10]

        self.all_labels =[]        

        

        # get default electrode voltages
        self.default_voltages = self.get_default_voltages()
        index_v = 0

        #electrode grid
        for e in [self.tl_electrodes0, self.tr_electrodes0, self.bl_electrodes0, self.br_electrodes0]:            
            
            el_values = e[0]
            xcoord_label = e[1]
            xcoord_entry = e[2]
            ycoord = e[3]
            
            for i in range(len(self.ELECTRODES[el_values])):    
                label = QLabel('       '+ self.ELECTRODES[el_values][i], self)
                label.setAlignment(QtCore.Qt.AlignRight)
                grid4.addWidget(label,ycoord-i,xcoord_label, 1,1)
                # label0 = QLabel('0.00', self)
                label0 = QLabel(str(self.default_voltages[index_v]), self)
                index_v += 1
                self.all_labels.append(label0)
                label0.setStyleSheet("border: 1px solid black;")
                grid4.addWidget(label0,ycoord-i,xcoord_entry,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid4.addWidget(label_gap,5,1,1,1)


        #t0
        label_t0 = QLabel('       '+self.ELECTRODES[2][0], self)
        label_t0.setAlignment(QtCore.Qt.AlignRight)
        grid4.addWidget(label_t0,1,2,1,1)
        self.label0_t0 = QLabel(str(self.default_voltages[-2]), self)
        self.label0_t0.setStyleSheet("border: 1px solid black;")
        grid4.addWidget(self.label0_t0,1,3,1,1)

        
        #b0
        label_b0 = QLabel('       '+self.ELECTRODES[5][0], self)
        label_b0.setAlignment(QtCore.Qt.AlignRight)
        grid4.addWidget(label_b0,7,2,1,1)
        self.label0_b0 = QLabel(str(self.default_voltages[-1]), self)
        self.label0_b0.setStyleSheet("border: 1px solid black;")
        grid4.addWidget(self.label0_b0,7,3,1,1)    

        #spacing  
        label_gap = QLabel('          ', self)
        grid4.addWidget(label_gap,1,6,1,1)

        #spacing  
        label_gap = QLabel('          ', self)
        grid4.addWidget(label_gap,11,6,2,1)
    
        #create multipole text entry boxes
        MULTIPOLES = ['Grid: (V)','Ex:', 'Ey:', 'Ez:', 'U1:', 'U2:', 'U3:', 'U4:', 'U5:', 'U6:']
        self.multipoles = []
        self.default_multipoles = self.get_default_multipoles()
        for i in range(len(MULTIPOLES)):  
            spin = QtWidgets.QDoubleSpinBox(self)
            if MULTIPOLES[i] == 'Grid: (V)':
                spin.setRange(0,3000)
            else:
                spin.setRange(-10,10)
            spin.setSingleStep(0.01)
            spin.setValue(self.default_multipoles[i])
            grid4.addWidget(spin,i,8,1,1)
            self.multipoles.append(spin)
            label = QLabel(MULTIPOLES[i], self)
            label.setAlignment(QtCore.Qt.AlignRight)
            grid4.addWidget(label,i,7,1,1)


        
        # # add extraction button
        # v_button = QPushButton('Initialize Rigol', self)
        # v_button.clicked.connect(self.run_rigol_extraction)
        # grid4.addWidget(v_button, 8+2, 8)

        # add shut_off button
        v_button = QPushButton('Switch off output', self)
        v_button.clicked.connect(self.HasEnvironment.shut_off)
        grid4.addWidget(v_button, 8+2, 8)

        # add multipole button
        self.lm_button = QPushButton('Load Multipole Voltages', self)
        self.lm_button.clicked.connect(self.on_multipoles_click)
        grid4.addWidget(self.lm_button, 9+2, 8)

        # add pulse counting button
        self.pc_button = QPushButton('Pulse Counting', self)
        self.pc_button.clicked.connect(self.on_pulse_counting_click)
        grid4.addWidget(self.pc_button, 10+2, 8)

        # add voltage button
        v_button = QPushButton('Update Set Values', self)
        v_button.clicked.connect(self.update_set_values)
        grid4.addWidget(v_button, 11+2, 8)

        # # add parameter button
        # v_button = QPushButton('Update Parameter Values', self)
        # v_button.clicked.connect(self.update_parameters)
        # grid4.addWidget(v_button, 11+2, 8)
        
        # add c-file button
        c_button = QPushButton('Load C-file', self)
        c_button.clicked.connect(self.openFileDialog)
        grid4.addWidget(c_button, 12+2, 8)

        # add run and stop button
        self.r_button = QPushButton('Run', self)
        self.r_button.clicked.connect(self.on_run_click_main)
        grid4.addWidget(self.r_button, 13+2, 8)

        t_button = QPushButton('Terminate', self)
        t_button.clicked.connect(self.on_terminate_click)
        grid4.addWidget(t_button, 14+2, 8)

        f_button = QPushButton('Data Folder', self)
        f_button.clicked.connect(self.on_data_folder_click)
        grid4.addWidget(f_button, 14+1,7)

        d_button = QPushButton('Store Data', self)
        d_button.clicked.connect(self.on_store_data_click)
        grid4.addWidget(d_button, 14+2, 7)

        t_button = QPushButton('Power threshold detector', self)
        t_button.clicked.connect(self.set_threshold_voltages)
        grid4.addWidget(t_button, 14, 7)

        t_button = QPushButton('Shutter optimize', self)
        t_button.clicked.connect(self.HasEnvironment.kernel_run_shutter_optimize)
        grid4.addWidget(t_button, 14-1, 7)

        hist_button = QPushButton('Make histogram', self)
        hist_button.clicked.connect(self.HasEnvironment.make_hist)
        grid4.addWidget(hist_button, 14-2, 7)


        grid4.setRowStretch(4, 1)
        self.tab4.setLayout(grid4)

        '''
        DEVICE TAB
        '''
        grid5 = QGridLayout() #make grid layout
        
        self.device_parameter_list = []  
        # rigol_PARAMETERS = ['Pulse width (ns):', 'Pulse delay (ns):','Offset (V):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):']
        rigol_PARAMETERS = ['Offset width (ns):', 'Pulse delay (ns):','Offset (V)(= -Amplitude/2):',  'Amplitude (V):', 'Phase:','Ejection pulse width (ns):','Sampling time (ns):'] # make it to be less confusing
        rigol_DEFAULTS = [10, 0, -5, 20, 0,200,2]

        for i in range(len(rigol_PARAMETERS)):  
            spin = QtWidgets.QSpinBox(self)
            spin.setRange(-1E6,1E9)
            spin.setSingleStep(10)
            spin.setValue(rigol_DEFAULTS[i]) # set default values
            grid5.addWidget(spin,i+11,1,1,1)
            self.device_parameter_list.append(spin)
            label = QLabel('    '+rigol_PARAMETERS[i], self)
            grid5.addWidget(label,i+11,0,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid5.addWidget(label_gap,0,2,1,2)
        
        # add extraction button
        v_button = QPushButton('Run Rigol Extraction', self)
        v_button.clicked.connect(self.run_rigol_extraction_device_tab)
        grid5.addWidget(v_button, 8+2, 8)

        grid5.setRowStretch(4, 1)
        self.tab5.setLayout(grid5)


        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)        
        return

    def run_rigol_extraction_device_tab(self):
        self.dev_list = []
        for m in self.device_parameter_list:
            text = m.text() or "0"
            self.dev_list.append(float(text))
        pulse_width_ej = self.dev_list[0]*1e-9
        pulse_delay_ej = self.dev_list[1]*1e-9
        offset_ej = self.dev_list[2]
        amplitude_ej = self.dev_list[3]
        phase = self.dev_list[4]
        period_ej = self.dev_list[5]*1e-9
        sampling_time = self.dev_list[6]*1e-9
        self.rigol113 =  rigol(113,pulse_width_ej,pulse_delay_ej,offset_ej,amplitude_ej,phase,period_ej,sampling_time)
        # self.rigol117 =  rigol(117,pulse_width_ej,pulse_delay_ej,offset_ej,amplitude_ej,phase,period_ej,sampling_time)
        self.rigol113.run()
        # self.rigol117.run()


    def set_threshold_voltages(self):
        self.HasEnvironment.set_threshold_voltages()



    def get_default_voltages(self):
        default = []
        for i in ["bl"]:
            for j in ["1","2","3","4","5"]:
                default.append(self.HasEnvironment.get_dataset(key="optimize.e."+i+j))
        for i in ["br"]:
            for j in ["1","2","3","4", "5"]:
                default.append(self.HasEnvironment.get_dataset(key="optimize.e."+i+j))
        for i in ["tl"]:
            for j in ["1","2","3","4","5"]:
                default.append(self.HasEnvironment.get_dataset(key="optimize.e."+i+j))
        for i in ["tr"]:
            for j in ["1","2","3","4","5"]:
                default.append(self.HasEnvironment.get_dataset(key="optimize.e."+i+j))
        default.append(self.HasEnvironment.get_dataset(key="optimize.e.t0"))
        default.append(self.HasEnvironment.get_dataset(key="optimize.e.b0"))

        return default

    def get_default_parameter(self):
        default = []
        for i in ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints"]:
            default.append(self.HasEnvironment.get_dataset(key="optimize.parameter."+i))
        return default

    def get_default_multipoles(self):
        default = []
        for i in ['Grid', 'Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']:
            # default.append(0)
            default.append(self.HasEnvironment.get_dataset("optimize.multipoles."+i))
        return default


    def update_set_values(self):
        self.update_multipoles()
        self.update_parameters()


    def update_multipoles(self):
        
        # Create multiple list of floats
        self.mul_list = []
        for m in self.multipoles:
            text = m.text() or "0"
            self.mul_list.append(float(text))

    
        for i, value in enumerate(['Grid','Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']):
            self.HasEnvironment.set_dataset("optimize.multipoles."+value, self.mul_list[i], broadcast=True, persist=True)
        grid_V = self.mul_list[0]

        

        # Calculate and print electrode values
        try:
            self.m=np.array([self.mul_list[1:]])
            grid_multipole_1V = np.array([5.74825920e-05 ,5.96780638e-06 ,1.26753930e-05,-1.32588496e-04,-9.81277203e-05,2.83539744e-05,1.17764523e-05,4.47353980e-05,1.24182868e-05])
            grid_multipole = [g*grid_V for g in grid_multipole_1V]
            self.m=self.m-grid_multipole
            self.e=np.matmul(self.m, self.C_Matrix_np)
        except:
            f = open('/home/electron/artiq/electron/Cfile_electron_gen2_v-1.txt','r')
            # create list of lines from selected textfile
            self.list_of_lists = []
            for line in f:
                stripped_line = line.strip()
                line_list = stripped_line.split()
                self.list_of_lists.append(float(line_list[0]))
                
            # create list of values from size 21*9 C-file
            curr_elt = 0
            self.C_Matrix = []
            for i in range(9):
                C_row = []
                for i in range(self.ne):
                    C_row.append(self.list_of_lists[curr_elt])
                    curr_elt+=1
                self.C_Matrix.append(C_row) 
                
            self.C_Matrix_np = np.array(self.C_Matrix)
            self.m=np.array([self.mul_list[1:]])
            #print(shape(self.m))
            # grid_V = 150
            grid_multipole_1V = np.array([5.74825920e-05 ,5.96780638e-06 ,1.26753930e-05,-1.32588496e-04,-9.81277203e-05,2.83539744e-05,1.17764523e-05,4.47353980e-05,1.24182868e-05])
            grid_multipole = [g*grid_V for g in grid_multipole_1V]
            self.m=self.m-grid_multipole
            self.e=np.matmul(self.m, self.C_Matrix_np)
            
        for i in range(len(self.e[0])):
            if self.e[0][i]>=10:
                print(f'warning: voltage {round(self.e[0][i],3)}  exceeds limit')
                self.e[0][i]=9.9
            elif self.e[0][i]<=-10:
                print(f'warning: voltage {round(self.e[0][i],3)} exceeds limit')
                self.e[0][i]=-9.9

        self.e = self.e[0].tolist()
        #self.e.append(self.e.pop(10))      
        for i in range(len(self.e)):
            self.e[i]=round(self.e[i],3)

        # print('before changing order', self.e)

        #assuming electrode order is [tl1,...,tl5,bl1,...,bl5,tr1,...,tr5,br1,...,br5,t0,b0]
        #new order: [ bl1,...,bl5,br1,...,br5, b0(grid), t0,tl1,...,tl5,tr1,..,tr5]

        self.elec_dict={'bl1':self.e[0],'bl2':self.e[1],'bl3':self.e[2],'bl4':self.e[3],'bl5':self.e[4],'br1':self.e[5],'br2':self.e[6],'br3':self.e[7],'br4':self.e[8],'br5':self.e[9],'b0':0.0,'t0':self.e[11],'tl1':self.e[12],'tl2':self.e[13],'tl3':self.e[14],'tl4':self.e[15],'tl5':self.e[16],'tr1':self.e[17],'tr2':self.e[18],'tr3':self.e[19],'tr4':self.e[20],'tr5':self.e[21]}
        print(self.elec_dict)



        for i in range(5):
            self.all_labels[i].setText(str(round(self.elec_dict['bl'+f'{1+i}'],3)))
            self.all_labels[5+i].setText(str(round(self.elec_dict['br'+f'{1+i}'],3)))
            self.all_labels[10+i].setText(str(round(self.elec_dict['tl'+f'{1+i}'],3)))
            self.all_labels[15+i].setText(str(round(self.elec_dict['tr'+f'{1+i}'],3)))
        self.label0_t0.setText(str(round(self.elec_dict['t0'],3)))
        self.label0_b0.setText(str(round(self.elec_dict['b0'],3)))

        self.e=[]
        for string in ['bl','br','tl','tr']:
            for i in range(5):
                self.e.append(self.elec_dict[string+f'{1+i}'])
        self.e.append(self.elec_dict['t0'])
        self.e.append(self.elec_dict['b0'])
        print(self.e)
        self.mutate_dataset_electrode()
        self.HasEnvironment.set_dataset("optimize.flag.e",1, broadcast=True, persist=True)
        print("update_multipoles has mutated dataset")

    def mutate_dataset_electrode(self):
        for string in ['bl']:
            for i in range(5):
                self.HasEnvironment.set_dataset("optimize.e."+string+str(1+i),self.elec_dict[string+f'{1+i}'], broadcast=True, persist=True)
        for string in ['br']:
            for i in range(5):
                self.HasEnvironment.set_dataset("optimize.e."+string+str(1+i),self.elec_dict[string+f'{1+i}'], broadcast=True, persist=True)
        for string in ['tl']:
            for i in range(5):
                self.HasEnvironment.set_dataset("optimize.e."+string+str(1+i),self.elec_dict[string+f'{1+i}'], broadcast=True, persist=True)
        for string in ['tr']:
            for i in range(5):
                self.HasEnvironment.set_dataset("optimize.e."+string+str(1+i),self.elec_dict[string+f'{1+i}'], broadcast=True, persist=True)
        self.HasEnvironment.set_dataset("optimize.e.t0",self.elec_dict['t0'], broadcast=True, persist=True)
        self.HasEnvironment.set_dataset("optimize.e.b0",self.elec_dict['b0'], broadcast=True, persist=True)

    def mutate_dataset_parameters(self):
        p = ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints"]
        for i in range(len(p)):
            self.HasEnvironment.set_dataset(key="optimize.parameter."+p[i],value = self.parameter_dict[p[i]], broadcast=True, persist=True)


    def update_parameters(self):
        self.p = []
        for i in range(len(self.parameter_list)):
            m = self.parameter_list[i]
            text = m.text() or str(self.default_parameter[i])
            self.p.append(float(text))
        self.parameter_dict={"t_load":self.p[0],"t_wait":self.p[1],"t_delay":self.p[2],"t_acquisition":self.p[3],"pulse_counting_time":self.p[4],"trigger_level":self.p[5],"number_of_repetitions":self.p[6],"number_of_datapoints":self.p[7]}
        print(self.p)
        self.mutate_dataset_parameters()
        self.HasEnvironment.set_dataset("optimize.flag.p",1, broadcast=True, persist=True)
        print("update_parameters has mutated dataset")


    def long_run_task(self):
        self.HasEnvironment.set_dataset("optimize.flag.stop",0, broadcast=True, persist=True)
        self.update_multipoles()
        self.update_parameters()
        # self.run_rigol_extraction()
        self.run_rigol_extraction_device_tab()
        self.HasEnvironment.core.reset()
        self.HasEnvironment.rolling_optimize()
        return

        
    def on_run_click_main(self):
        self.thread = QThread() # create a QThread object
        self.worker = Worker(self.long_run_task) # create a worker object
        # self.worker = Worker() # create a worker object
        self.worker.moveToThread(self.thread) # move worker to the thread
        # connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)
        self.thread.start() # start the thread
        # final resets
        self.r_button.setEnabled(False)
        self.lm_button.setEnabled(False)
        self.pc_button.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.r_button.setEnabled(True)
            # lambda: self.lm_button.setEnabled(True),
            # lambda: self.pc_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.lm_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.pc_button.setEnabled(True)
            )
        # self.thread.finished.connect(
        #     lambda: self.stepLabel.setText("Long-Running Step: 0")
        #     )


    def on_terminate_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.stop",1, broadcast=True, persist=True)
        return

    def on_store_data_click(self):

        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("results")
        form = Ui_Dialog()
        dialog.ui = form
        dialog.ui.setupUi(dialog)
        dialog.exec_()
        dialog.show()
        dataset_name = "optimize.result." + form.string_selected

        # DATASETS
        e_headers = ["b0","bl1","bl2","bl3","bl4","bl5","br1","br2","br3","br4","br5","t0","tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5"]
        m_headers = ["Grid","Ex","Ey","Ez","U1","U2","U3","U4","U5","U6"]
        p_headers = ["number_of_datapoints", "number_of_repetitions","pulse_counting_time","t_acquisition","t_delay","t_load","t_wait","trigger_level"]
        results = ["count_ROI","count_tot"]
        all_params = e_headers+m_headers+p_headers

        e_data = []
        for e in e_headers:
                temp_string = "optimize.e." + e
                param_data = self.HasEnvironment.get_dataset(temp_string)
                e_data.append(np.round(param_data,5))
        m_data = []
        for m in m_headers:
                temp_string = "optimize.multipoles." + m
                param_data = self.HasEnvironment.get_dataset(temp_string)
                m_data.append(np.round(param_data,5))
        p_data = []
        for p in p_headers:
                temp_string = "optimize.parameter." + p
                param_data = self.HasEnvironment.get_dataset(temp_string)
                p_data.append(np.round(param_data,5))

        dataset = np.array(self.HasEnvironment.get_dataset(dataset_name))
        param_data = np.array(e_data+m_data+p_data)
        
        # folder to store all data
        try:
            data_folder = self.folder
        except:    
            data_folder = "/home/electron/artiq/electron/artiq-master/data" #default path if none is selected 

        # folder for individual run and params
        path = os.path.join(data_folder, datetime.now().strftime("%m-%d-%y"))

        #check if path already exist:
        subfolder = 1
        orig_path = path
        if os.path.exists(path) == False:
            path = orig_path+"_"+str(subfolder)

        while os.path.exists(path):
            subfolder += 1
            #create unique name if path exists 
            path = orig_path+"_"+str(subfolder)
        os.mkdir(path)

        # create rows to write csv
        fields = all_params
        rows = [] 
        for r in dataset:
            ROW = []
            ROW.append(r)
            rows.append(ROW)

        folder_name = form.string_selected + "_results.csv"
        param_folder_name = form.string_selected + "_params.csv"
    
        # name and path of csv files
        filename = os.path.join(path, folder_name)
        param_filename = os.path.join(path, param_folder_name)
    
        # writing to data csv  
        with open(filename, 'w') as csvfile: 
            # creating a csv writer object 
            csvwriter = csv.writer(csvfile)     
            # writing the fields 
            csvwriter.writerow([fields[0]]) 
            # writing the data rows 
            csvwriter.writerows(rows)

        # write to param csv
        with open(param_filename, 'w') as csvfile: 
            # creating a csv writer object 
            csvwriter = csv.writer(csvfile)     
            # writing the fields 
            csvwriter.writerow(fields) 
            # writing the data rows 
            csvwriter.writerow(param_data)

    def on_data_folder_click(self):
        print("data folder clicked")
        self.folder = QFileDialog.getExistingDirectory(self, "Choose Directory", options=QtWidgets.QFileDialog.DontUseNativeDialog)

    def on_pulse_counting_click(self):

        self.HasEnvironment.set_dataset("optimize.flag.stop",0, broadcast=True, persist=True)
        self.HasEnvironment.get_parameter_list()
        self.HasEnvironment.core.reset()
   
        self.thread = QThread() # create a QThread object
        self.worker = Worker(self.HasEnvironment.pulse_counting) # create a worker object
        # self.worker = Worker() # create a worker object
        self.worker.moveToThread(self.thread) # move worker to the thread
        # connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)
        self.thread.start() # start the thread
        # final resets
        self.r_button.setEnabled(False)
        self.lm_button.setEnabled(False)
        self.pc_button.setEnabled(False)
        self.thread.finished.connect(
            lambda: self.r_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.lm_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.pc_button.setEnabled(True)
            )

        
    def openFileDialog(self):
        
        # create list of lines from dataset
        #self.list_of_lists = [-1.512326312102017623e+00,1.637941648087839042e+01,-2.304713098445680952e+00,4.188495113946148507e+01,-1.808897796925718948e+00,1.422206623834767758e-01,3.921182615775121860e+01,1.025963357992092817e+01,2.264705463741543312e+01,-2.360850721028599608e+00,-1.895921784207670271e+02,-7.648869380779895755e-01,2.690463378718400733e+01,5.920669516490001172e+01,4.943331910064007673e+01,-1.107648341966514183e+00,2.773790806348027660e-01,5.090354436109951308e+01,6.115483000423661508e+01,2.884358204769423750e+01,-1.605923921094738471e+00,-5.511533629856346650e-01,-1.250094470782944001e+01,-2.523380065533868399e-01,1.364501006265611061e+01,6.337975904091774915e-01,-5.480274437008441080e-01,-1.245780766135806950e+01,-2.286003102594457437e-01,1.360866409448358638e+01,6.327547911920178292e-01,-3.581946332944305200e-01,-7.840193523786034291e-01,-1.250454759590978959e+01,-1.352301122949902124e-01,1.357806762434341152e+01,7.405668850198696695e-01,-7.820502094663634995e-01,-1.245920669079553988e+01,-1.315495203521160894e-01,1.353916763714750005e+01,7.396254978812962788e-01,-1.001784083043502985e-02,1.749003805973549097e+00,1.416105840153299411e+01,2.349319628607441146e+00,4.075482545269065726e-02,3.065805231873156012e-02,-1.725189274673949003e+00,-1.415274385706719862e+01,-2.320799656347184214e+00,-7.420901469804227352e-03,-1.119376892950579155e-01,1.929492144214527485e-02,2.054620140324989741e+00,1.525123613966764680e+01,2.724594031293268603e+00,5.153221867133202239e-02,4.094843007809051069e-03,-2.004372950912953311e+00,-1.518251428157990013e+01,-2.674585566944683190e+00,-1.848882493866542756e-02,4.427532075829812563e-02,8.042836776307868973e-01,2.950966392151396445e+00,8.813158696214824506e-01,5.415755296136771924e-02,5.112540161328654048e-02,8.988133916930655110e-01,3.002984734310525372e+00,8.016679970913439535e-01,5.187238232761943318e-02,-7.849409969514320462e-01,-9.739010458369092016e-03,-5.308815076084497653e-01,-2.880086903674786036e+00,-3.787437517912086715e-01,1.466480792631248004e-02,-5.423867636373652310e-03,-4.315222990769136402e-01,-2.872021323566237960e+00,-4.639884536766597511e-01,1.260186981834057925e-02,1.104387857448935861e+00,1.414190511080105850e+01,-6.903196031951223333e+00,1.434398252363142490e+01,1.231685905914327472e+00,1.093640837035562141e+00,1.399594276745827059e+01,-6.968179365203829967e+00,1.447137949024534187e+01,1.235291190060973765e+00,1.228843073661495255e+00,1.177207796745266322e+00,1.324438949879065319e+01,-7.117337983139794488e+00,1.282549463442225246e+01,1.370263617803965994e+00,1.170461529642176757e+00,1.309120659785244634e+01,-7.112284368120354472e+00,1.296207663271408883e+01,1.373533700803296398e+00,-5.665926477634710245e+00,-6.788983420775350908e+01,3.912332929695216399e-01,6.802030265346905935e+01,1.266426079420123196e+00,4.997696544746094816e+00,6.810992431655101598e+01,-5.068732646262870123e-01,-6.769403352277257113e+01,-2.375654562875646025e+00,5.527709148760519275e-02,-3.730374804048214532e+00,-7.631695682031620720e+01,1.806400857676365712e+00,6.783939892248946535e+01,1.087870016205992885e+00,2.991802337819332802e+00,7.611659304759672295e+01,-1.769582802804737787e+00,-6.793311253242865178e+01,-2.161400721059941521e+00,-6.067963966733943559e-01,-1.326802042886387056e+01,-1.007199728894146995e-01,1.352405994382151810e+01,7.080539093337696599e-01,-6.174106604108499097e-01,-1.341449509643709881e+01,-1.813228759133266310e-01,1.364747506008922606e+01,7.115948023984169923e-01,1.216273345726305299e+00,7.007152510876333285e-01,1.327939210304557527e+01,-3.598155512414831780e-01,-1.360567741897219562e+01,-6.643401944674592885e-01,6.940288973135760875e-01,1.312543408905663611e+01,-3.723132423312838779e-01,-1.347358996377454687e+01,-6.611436527600553781e-01,-1.498396939369385672e+00,4.775290053332635232e+00,-5.382571064047478870e+00,2.283210820570276312e+01,-1.715576131392834824e+00,-3.108692319523179148e-01,2.114886337596763255e+01,3.535544986357319619e+00,9.009750377985021430e+00,-2.111853164610799194e+00,-1.360612505558479768e+02,-9.897187636141845379e-01,1.254684322450274436e+01,3.865875789400611495e+01,2.886342341390053789e+01,-1.268976369146711303e+00,-2.417893517119287516e-01,2.975551776450667418e+01,3.995075842496849816e+01,1.406837578934314692e+01,-1.626807989492804696e+00,4.100607983092512815e-02,2.569968194327167499e+00,1.692203694724078389e+01,1.962548614527418467e+00,2.215096122618124760e-02,-1.827907786909331936e-02,-2.572890988440327931e+00,-1.689742564150423831e+01,-1.966051845797390119e+00,1.557339160813818110e-02,-4.614777135054736953e-03,-4.749955903610175549e-03,-2.279481596629263862e+00,-1.703984776866616002e+01,-2.871240313745817563e+00,-1.956369307675694461e-02,2.942840974861685860e-02,2.281398971963211952e+00,1.701854536599861234e+01,2.873040947197679440e+00,5.582624154462705740e-02]
        

        # open file navigation
        #self.textedit = QPlainTextEdit()
        filename = QFileDialog.getOpenFileName(parent=self, options=QtWidgets.QFileDialog.DontUseNativeDialog)

        if filename[0]:
            f = open(filename[0],'r')
        # create list of lines from selected textfile
        self.list_of_lists = []
        for line in f:
            stripped_line = line.strip()
            line_list = stripped_line.split()
            self.list_of_lists.append(float(line_list[0]))
            
        # create list of values from size 22*9 C-file
        curr_elt = 0
        self.C_Matrix = []
        for i in range(9):
            C_row = []
            for i in range(self.ne):
                C_row.append(self.list_of_lists[curr_elt])
                curr_elt+=1
            self.C_Matrix.append(C_row) 
            
        self.C_Matrix_np = np.array(self.C_Matrix)
    
    def keyPressEvent(self, qKeyEvent):
        #print(qKeyEvent.key())
        if qKeyEvent.key() == QtCore.Qt.Key_Return:
            
            if self.tabs.currentIndex() == 0:
                self.update_multipoles()
                self.update_parameters()
            elif self.tabs.currentIndex() == 1:
                self.on_voltage_click()
            # elif self.tabs.currentIndex() == 1:
            #     self.on_multipoles_click()
            # elif self.tabs.currentIndex() == 1:
                # self.on_run_click_main()
        else:
            super().keyPressEvent(qKeyEvent)
                           
    def on_voltage_click(self):
        # Create electrode list of floats
        self.el_list = []
        for i in self.electrodes:
            text = i.text() or "0"
            self.el_list.append(float(text))
        self.e=self.el_list
        self.set_dac_voltages(self.e)
        print("on_voltage_click has updated voltages")
        # print(self.e)
        # for c in range(len(self.e)):
            # self.mutate_dataset("dac_voltages", c, self.e[c])
        # print("on_voltage_click has mutated dataset")

    def on_multipoles_click(self):
        self.update_multipoles()        
        self.set_dac_voltages(self.e)
        print("on_multipole_click has updated voltages and mutated datasets")
        

    def change_background(self, entry):

        if entry.text() == '':
            pass
        else:
            val = float(entry.text())
            a = np.abs(val/10)

            if val>0:
                r = 1
                b = 0
                col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),0,int(255*b))
                entry.setStyleSheet(f'QWidget {{background-color: {col};}}')
            elif val<0:
                r = 0
                b = 1
                col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),0,int(255*b))
                entry.setStyleSheet(f'QWidget {{background-color: {col};}}')
            elif val==0:
                r = 0
                b = 0
                entry.setStyleSheet(f'QWidget {{background-color: "white";}}')


    def change_background_labels(self):
        for label in self.all_labels:
            if label == False:
                label = 0
            if label.text() == '':
                pass
            else:
                val = float(label.text())
                a = np.abs(val/10)

                if val>0:
                    r = 1
                    b = 0
                elif val<0:
                    r = 0
                    b = 1
                elif val==0:
                    r = 0
                    b = 0
                col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),0,int(255*b))
                label.setStyleSheet(f'QWidget {{background-color: {col};}}')

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(358, 126)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
       
        self.combo = QComboBox(Dialog)
        self.combo.addItem("count_ROI")
        self.string_selected = "count_ROI" #auto select first option
        self.combo.addItem("count_tot")
        self.combo.move(50, 50)

        self.qlabel = QLabel()
        self.qlabel.move(50,16)
        self.combo.activated[str].connect(self.onChanged)      

    def onChanged(self, text):
        self.qlabel.setText(text)
        self.qlabel.adjustSize()
        self.string_selected = text

# Creating a worker class
class Worker(QObject):

    finished = pyqtSignal()
    # progress = pyqtSignal(int)
    # result = pyqtSignal('QVariant')

    # def __init__(self, function, args):
    #     super().__init__()
    #     self.function = function
    #     self.args = args
    def __init__(self, function):
        super().__init__()
        self.function = function
        

    def run(self):
        self.function()
        # self.function(self.args)
        # for i in range(60):
        #     time.sleep(1)
        #     self.progress.emit(i+1)
        # self.result.emit(res)
        self.finished.emit()


class Electron_GUI_backup1(Electron, EnvExperiment):#, object):
    def build(self):
        Electron.build(self)

    def prepare(self):
        Electron.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        # self.launch_GUI()
        print("Hello World")




