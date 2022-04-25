from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QComboBox, QGridLayout, QLineEdit, QPlainTextEdit
import select
import time
import os
import sys
import csv


class PulseSequence(HasEnvironment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0') # artiq DAC
        self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        self.setattr_device('ttl8') # use this channel to trigger AOM, connect to switch near VCO and AOM
        self.setattr_device('ttl9') # use this channel to trigger R&S for tickle pulse, connect to R&S
        self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device('ttl11') # use this channel to reset threshold detector, connect to reset of threshold detector
        self.setattr_device('scheduler') # scheduler used

        self.setattr_argument('number_of_datapoints', NumberValue(default=5000,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot, run experiment & pulse counting
        # self.setattr_argument('time_count', NumberValue(default=5000,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis, pulse counting

    def prepare(self):
        
        # electrodes: [bl1,...,bl5,br1,...,br5 (except br4),tl1,...,tl5,tr1,...,tr5 (except tr4),btr4,t0,b0], notice br4 and tr4 are shorted together, channel 3 
        # pins=[13,15,17,19,21,23,7,5,1,24,2,26,28,30,9,20,18,14,16, 4,11] # Unused dac channels: 0 (bad),3, 6,8,10,12,22 (bad) ,25,27,29,31
        
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
        # self.set_dataset(key="optimize.e.btr4", value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.t0", value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.b0", value=np.float32(0), broadcast=True, persist=True)
        
        # # flags: indicating changes from GUI, 1 = there is change that needs to be implemented
        # self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True) # electrode voltages
        # self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True) # experiment parameters
        # self.set_dataset(key="optimize.flag.stop", value = 0, broadcast=True, persist=True) # whether or not terminate the experiment

        # # parameters: t_load(us),t_wait(us),t_delay(ns), t_acquisition(ns),pulse_counting_time(ms), trigger_level (V), # repetitions, # datapoints
        # self.set_dataset(key="optimize.parameter.t_load", value = np.int(100), broadcast=True, persist=True) # t_load(us)
        # self.set_dataset(key="optimize.parameter.t_wait", value = np.int(100), broadcast=True, persist=True) # t_wait(us)
        # self.set_dataset(key="optimize.parameter.t_delay", value = np.int(600), broadcast=True, persist=True) # t_delay(ns)
        # self.set_dataset(key="optimize.parameter.t_acquisition", value = np.int(100), broadcast=True, persist=True) # t_acquisition(ns)
        # self.set_dataset(key="optimize.parameter.pulse_counting_time", value = np.int(500), broadcast=True, persist=True) # pulse_counting_time(ms)
        # self.set_dataset(key="optimize.parameter.trigger_level", value = 0.3, broadcast=True, persist=True) # trigger level (V)
        # self.set_dataset(key="optimize.parameter.number_of_repetitions", value = np.int(1000), broadcast=True, persist=True) # number of repetitions
        # self.set_dataset(key="optimize.parameter.number_of_datapoints", value = np.int(5000), broadcast=True, persist=True) # number of datapoints

        # results:
        self.set_dataset('optimize.result.count_tot',[-100]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2
        self.set_dataset('optimize.result.count_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI in optimize
        self.set_dataset('count_threshold',[-200]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 from threshold detector

        self.ne = 21 # number of electrodes
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
            for j in ["1","2","3","5"]:
                dac_vs.append(self.get_dataset(key="optimize.e."+i+j))
        for i in ["tl"]:
            for j in ["1","2","3","4","5"]:
                dac_vs.append(self.get_dataset(key="optimize.e."+i+j))
        for i in ["tr"]:
            for j in ["1","2","3","5"]:
                dac_vs.append(self.get_dataset(key="optimize.e."+i+j))
        dac_vs.append(self.get_dataset(key="optimize.e.btr4"))
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
    def kernel_run_optimize (self,i,load_dac):
        # electrodes: [bl1,...,bl5,br1,...,br5 (except br4),tl1,...,tl5,tr1,...,tr5 (except tr4),btr4,t0,b0], notice br4 and tr4 are shorted together, channel 3 
        pins=[13,15,17,19,21,23,7,5,1,24,2,26,28,30,9,20,18,14,16, 4,11] # Unused dac channels: 0 (bad),3, 6,8,10,12,22 (bad) ,25,27,29,31
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
                self.zotino0.write_dac(pins[pin],self.dac_vs[pin])    
            self.zotino0.load()
            print("Loaded dac voltages")

        for j in range(number_of_repetitions):
            self.core.break_realtime()
            with sequential:
                self.ttl8.on()
                delay(t_load*us)
                with parallel:
                    self.ttl8.off()
                    self.ttl9.on()
                delay(t_wait*us)
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
                self.count_tot += count
                delay(1*us)
        self.mutate_dataset('optimize.result.count_ROI',i,self.count_tot)

    def rolling_optimize(self):
        self.get_dac_vs()
        print("dac_vs",self.dac_vs)
        self.get_parameter_list()
        print("parameter_list",self.parameter_list)
        self.count_tot = 0
        number_of_datapoints = np.int(self.parameter_list[7])

        for i in range(number_of_datapoints):
            load_dac = False
            flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
            flag_parameter = np.int32(self.get_dataset(key="optimize.flag.p"))
            flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
            if flag_stop == 1:
                for j in range(i):
                    self.mutate_dataset('optimize.result.count_ROI',i,-2)
                print("Experiment terminated")
                return
            if flag_dac == 1:
                # load dac voltages
                dac_vs = self.get_dac_vs()
                load_dac = True
                self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True)
            if flag_parameter == 1:
                # t_load, t_wait, t_delay, t_acquisition, number_of_repetitions, number_of_datapoints = self.get_parameter_list()
                parameter_list = self.get_parameter_list()
                self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True)
            self.kernel_run_optimize(i,load_dac)

    
    @ kernel
    def set_dac_voltages(self,dac_vs):
        # electrodes: [bl1,...,bl5,br1,...,br5 (except br4),tl1,...,tl5,tr1,...,tr5 (except tr4),btr4,t0,b0], notice br4 and tr4 are shorted together, channel 3 
        pins=[13,15,17,19,21,23,7,5,1,24,2,26,28,30,9,20,18,14,16, 4,11] # Unused dac channels: 0 (bad),3, 6,8,10,12,22 (bad) ,25,27,29,31
        self.core.reset()
        self.zotino0.init()
        self.core.break_realtime() 
        for pin in range(len(pins)):
            delay(500*us)
            self.zotino0.write_dac(pins[pin],dac_vs[pin])    
        self.zotino0.load()

    @kernel
    def kernel_run_pulse_counting(self,j,detection_time):
        self.core.break_realtime()
        if j== 0:
            self.ttl8.on() # AOM
        with parallel:
            self.ttl10.pulse(2*us) # extraction pulse
            t_count = self.ttl2.gate_rising(detection_time*ms)
        self.mutate_dataset('optimize.result.count_tot',j,self.ttl2.count(t_count)/(detection_time*ms))


    def pulse_counting(self):
        detection_time = np.int32(self.parameter_list[4])
        # with parallel:
        for j in range(self.number_of_datapoints):
            flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
            if flag_stop == 1:
                for i in range(j):
                    self.mutate_dataset('optimize.result.count_tot',i,-100)
                print("Experiment terminated")
                return
            self.kernel_run_pulse_counting(j,detection_time)
            
         
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