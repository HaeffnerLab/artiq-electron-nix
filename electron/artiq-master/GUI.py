from artiq.experiment import delay, sequential, parallel
from artiq.experiment import us, ns, ms, s
from artiq.experiment import HasEnvironment, EnvExperiment
from artiq.experiment import NumberValue
from artiq.language.core import kernel
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QComboBox, QGridLayout, QLineEdit, QPlainTextEdit
import select
#from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
from datetime import datetime
import time
import os
import sys
import csv
import vxi11
import matplotlib.pyplot as plt

class Electron(HasEnvironment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0') # artiq DAC
        self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        self.setattr_device('ttl8') # use this channel to trigger AOM, connect to switch near VCO and AOM
        self.setattr_device('ttl9') # use this channel to trigger R&S for tickle pulse, connect to R&S
        self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device('ttl11') # use this channel to reset threshold detector, connect to reset of threshold detector
        self.setattr_device("ttl12")  # sending ttl to shutter motor servo 390
        # self.setattr_device("ttl13")  # sending ttl to shutter motor servo 422
        self.setattr_device("ttl13") # synchronized ttl pulse as the acuiquisition time
        self.setattr_device('scheduler') # scheduler used
        self.setattr_device("sampler0")

        self.setattr_argument('number_of_datapoints', NumberValue(default=5000,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot, run experiment & pulse counting
        self.setattr_argument('number_of_bins', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis, pulse counting

    def prepare(self):

        # results:
        self.set_dataset('optimize.result.count_tot',[-100]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 in pusle counting
        self.set_dataset('optimize.result.count_PI',[-10]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 in shutter optimize
        self.set_dataset('optimize.result.count_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI in optimize
        self.set_dataset('optimize.result.countrate_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI in optimize without accumulating
        self.set_dataset('count_threshold',[-200]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 from threshold detector
        self.set_dataset('optimize.result.bin_times', [-1]*self.number_of_bins*self.number_of_datapoints,broadcast=True) # Small bins for histogram 

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

        
        print("testing function without GUI (for debugging)")
        self.tab_widget.on_run_click_main()
        

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

        print("kernel run optimize is runnning")

        self.core.break_realtime()

        t_load = np.int32(self.parameter_list[0])
        t_wait = np.int32(self.parameter_list[1])
        t_delay = np.int32(self.parameter_list[2])
        t_acquisition = np.int32(self.parameter_list[3])
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

        print("kernel run optimize hist is running")
        
        self.core.break_realtime()
        t_load = np.int32(self.parameter_list[0])
        t_wait = np.int32(self.parameter_list[1])
        t_delay = np.int32(self.parameter_list[2])
        t_acquisition = np.int32(self.parameter_list[3])
        number_of_repetitions = 2#np.int32(self.parameter_list[6])
        number_of_datapoints = np.int32(self.parameter_list[7])
        

        t_bins = 10000 #10ns bins for histogram
        t_total = t_load*us+t_wait*ns+t_delay*ns+t_acquisition*ns

        #print(t_total)
    
        n_bins = 10 #bins

        if load_dac:
            self.zotino0.init()
            self.core.break_realtime() 
            for pin in range(self.ne):
                delay(500*us)
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])    
            self.zotino0.load()
            # print("Loaded dac voltages")
                    

        for k in range(update_cycle):
            countrate_tot = 0 
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with parallel:
                    
                    
                    #time tagger sequence (single cycle)
                    with sequential:
                        time_tag = 0
                        for time_tag in range(2):
                        #while time_tag < t_total:
    
                            t_count = self.ttl2.gate_rising(t_bins*ns)
                            count = self.ttl2.count(t_count)
                            if count > 0:
                                self.mutate_dataset('optimize.result.bin_times',0,time_tag)
                            time_tag=time_tag+10*ns#t_bins
                    
                        print("parallel test")


                    #experiment cycle
                    
                    with sequential:
                        print("entered experiment cycle")
                        self.ttl8.on()
                        delay(t_load*us)
                        with parallel:
                            self.ttl8.off()
                            self.ttl9.on()
                        delay(t_wait*ns)
                        with parallel:
                            self.ttl9.off()
                            self.ttl10.pulse(2*us)
                            with sequential:
                                print("aqcuisition period")
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
                        print("leaving loop")



            self.mutate_dataset('optimize.result.count_ROI',i*update_cycle+k,self.count_tot)
            self.mutate_dataset('optimize.result.countrate_ROI',i*update_cycle+k,countrate_tot)
            

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
            self.kernel_run_optimize_hist(i,load_dac,update_cycle)

    
    @ kernel
    def set_dac_voltages(self,dac_vs):
        # self.core.reset()
        self.core.break_realtime() 
        self.zotino0.init()
        # self.core.break_realtime() 
        for pin in range(self.ne):
            delay(500*us)
            self.zotino0.write_dac(self.pins[pin],dac_vs[pin])    
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
            time.sleep(5) # wait for the user to move the stage
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
                self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])    
            self.zotino0.load()
            print("Loaded dac voltages")

        # self.core.break_realtime()
        if j == 0:
            self.ttl8.on() # AOM
        # with parallel:
        #     self.ttl10.pulse(2*us) # extraction pulse
        #     t_count = self.ttl2.gate_rising(detection_time*ms)

        # self.mutate_dataset('optimize.result.count_tot',j,self.ttl2.count(t_count)/(detection_time*ms))

        count = 0
        N = 5000
        for i in range(N):
            self.core.break_realtime()
            with parallel:
                self.ttl10.pulse(2*us) # extraction pulse
                t_count = self.ttl2.gate_rising(detection_time*1000/N*us)
            count += self.ttl2.count(t_count)

        self.mutate_dataset('optimize.result.count_tot',j,count/(detection_time*ms))


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
