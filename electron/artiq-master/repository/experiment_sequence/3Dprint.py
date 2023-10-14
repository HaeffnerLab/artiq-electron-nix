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
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt


from Instruments import rigol, RS
from utils import *


class Electron(HasEnvironment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0') # artiq DAC
        self.setattr_device('ttl1')
        self.setattr_device('ttl_MCP_in') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        self.setattr_device('ttl8') 
        self.setattr_device('ttl9') # use this channel to trigger R&S for tickle pulse, connect to R&S
        self.setattr_device('ttl_Extraction') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device("ttl_TimeTagger") # time tagger start click
        self.setattr_device("ttl12")
        self.setattr_device("ttl13")
        self.setattr_device("ttl_390") # use this channel to trigger AOM, connect to switch near VCO and AOM
        # self.setattr_device('scheduler') # scheduler used
        self.setattr_device("sampler0")

        self.setattr_argument('update_cycle', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1))
        self.setattr_argument('number_of_datapoints', NumberValue(default=5000,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot, run experiment & pulse counting
        self.setattr_argument('number_of_bins', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis, pulse counting
        self.setattr_argument('max_lifetime', NumberValue(default=10000,unit='us',scale=1,ndecimals=0,step=1))

    def prepare(self):
        '''
        for i in ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5']:
            self.set_dataset(key="optimize.multipoles."+i, value=np.float32(0), broadcast=True, persist=True)
        for i in ["DC"]:
            for j in ["0","1","2","3","4","5","6","7","8"]:
                self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)

        self.set_dataset(key="optimize.e.trigger_level", value=np.float32(0), broadcast=True, persist=True)
        
        # flags: indicating changes from GUI, 1 = there is change that needs to be implemented
        self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True) # electrode voltages
        self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True) # experiment parameters
        self.set_dataset(key="optimize.flag.stop", value = 0, broadcast=True, persist=True) # whether or not terminate the experiment
        self.set_dataset(key="optimize.flag.run_mode", value = np.int(0), broadcast=True, persist=True) # run mode,0: pulse counting, 1: ROI counting (pulse 390), 2: histogram counting (pulse 390)
        
        # parameters: t_load(us),t_wait(us),t_delay(ns), t_acquisition(ns),pulse_counting_time(ms), trigger_level (V), # repetitions, # datapoints
        self.set_dataset(key="optimize.parameter.t_load", value = np.int(200), broadcast=True, persist=True) # t_load(us)
        self.set_dataset(key="optimize.parameter.t_wait", value = np.int(100), broadcast=True, persist=True) # t_wait(us)
        self.set_dataset(key="optimize.parameter.t_delay", value = np.int(450), broadcast=True, persist=True) # t_delay(ns)
        self.set_dataset(key="optimize.parameter.t_acquisition", value = np.int(600), broadcast=True, persist=True) # t_acquisition(ns)
        self.set_dataset(key="optimize.parameter.pulse_counting_time", value = np.int(500), broadcast=True, persist=True) # pulse_counting_time(ms)
        self.set_dataset(key="optimize.parameter.trigger_level", value = 0.03, broadcast=True, persist=True) # trigger level (V)
        self.set_dataset(key="optimize.parameter.number_of_repetitions", value = np.int(1000), broadcast=True, persist=True) # number of repetitions
        self.set_dataset(key="optimize.parameter.number_of_datapoints", value = np.int(100000), broadcast=True, persist=True) # number of datapoints
        self.set_dataset(key="optimize.parameter.bins", value = np.int(50), broadcast=True, persist=True) # number of bins in the histogram
        self.set_dataset(key="optimize.parameter.update_cycle", value = np.int(10), broadcast=True, persist=True) # number of datapoints per update cycle
        '''
        

        self.wait_times = [ 1.000,2.154,4.641,10.000,21.544,46.415,100.000,215.443,464.158,1000.000,10000.0]
        # self.wait_times = [1.00000000e+00, 1.83298071e+00, 3.35981829e+00, 6.15848211e+00,1.12883789e+01, 2.06913808e+01, 3.79269019e+01, 6.95192796e+01,1.27427499e+02, 2.33572147e+02, 4.28133240e+02, 7.84759970e+02,1.43844989e+03, 2.63665090e+03, 4.83293024e+03, 8.85866790e+03,1.62377674e+04, 2.97635144e+04, 5.45559478e+04, 1.00000000e+05]
        # results:
        self.set_dataset('optimize.result.count_tot',[-100]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in in pusle counting
        # self.set_dataset('optimize.result.count_PI',[-10]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in in shutter optimize
        self.set_dataset('optimize.result.count_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in with ROI in optimize
        self.set_dataset('optimize.result.countrate_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in with ROI in optimize without accumulating
        self.set_dataset('optimize.result.bin_times', [-1]*0,broadcast=True) #self.number_of_bins*self.number_of_datapoints,broadcast=True) # Small bins for histogram
        self.set_dataset('optimize.result.lifetime.counts',[-50]*len(self.wait_times),broadcast=True)
        self.set_dataset('optimize.result.lifetime.wait_times',[-50]*len(self.wait_times),broadcast=True)
        self.set_dataset('optimize.result.lifetime.lifetime_fit',value=np.float32(0),broadcast=True)
        # self.set_dataset('optimize.result.frequency_count_ROI',[-2]*self.freq,broadcast=True)
        # self.set_dataset('optimize.result.frequency_ROI',[-2]*self.freq,broadcast=True)
        

       
        self.pin_matching = {"DC0":9,"DC1":4,"DC2":16,"DC3":6,"DC4":17,"DC5":2,"DC6":14,"DC7":24,"DC8":23,"trigger_level":0}
        self.gnd = [3,15,25] # gnd pins
        self.use_amplifier = False
        self.max_voltage = 9.5
        # self.dac_calibration_fit = [[m0=1,b0=0],[m1,b1],...[m25,b25]]
        

        # self.ne = int(len(self.pins)) # number of electrodes
        self.np = 10 # number of experiment parameters
        

        self.controlled_electrodes = ["DC0","DC1","DC2","DC3","DC4","DC5","DC6","DC7","DC8","trigger_level"]
        self.controlled_multipoles = ["Ex","Ey","Ez","U1","U2","U3","U4","U5"]

        self.controlled_parameters = ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints","bins","update_cycle"]
        

        self.old_c_file = False
        self.c_file_csv = '/home/electron/artiq-nix/electron/flipped_Electron3dTrap_200um_v6_cfile.csv'
        
        self.controlled_multipoles_dict = {"Ex":'Ex:', "Ey":'Ey:', "Ez":'Ez:', "U1":'U1:', "U2":'U2:', "U3":'U3:', "U4":'U4:', "U5":'U5:'}
        self.controlled_parameters_dict = {"t_load":'Load time (us):', "t_wait":'Wait time (us):', "t_delay":'Delay time (ns):',"t_acquisition":'Acquisition time(ns):' , "pulse_counting_time":'Pulse counting time (ms):',"trigger_level":'Trigger level (V):',"number_of_repetitions":'# Repetitions:', "number_of_datapoints":'# Datapoints:', "bins":'# Bins:',"update_cycle":'# Update cycles:'}
        self.controlled_electrodes_dict = ["DC0","DC1","DC2","DC3","DC4","DC5","DC6","DC7","DC8","trigger_level"]
        self.ne = int(len(self.controlled_electrodes)) # number of electrodes
        
        self.run_mode = 0 # 0: pulse counting, 1: ROI counting (pulse 390), 2: histogram counting (pulse 390), 3: only outputting pulses and dacs
        self.bins = 50 # bin number for histogram
        self.update_cycle = 10 # how many datapoints per user_update_check (takes about 500 ms)
    
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
        self.title = 'Electron GUI 3Dprint_v6'
        self.left = 0
        self.top = 0
        self.width = 1200 # 600
        self.height = 600 # 200
        win.setWindowTitle(self.title)
        win.setGeometry(self.left, self.top, self.width, self.height)
        self.tab_widget = MyTabWidget(self,win)
        win.setCentralWidget(self.tab_widget)

    def rolling_run(self):
        self.loadDACoffset()
        self.get_dac_vs()
        self.get_parameter_dict()
        self.get_run_mode()
        if self.run_mode == 4:
            self.kernel_run_lifetime_measurement()
            return
        number_of_datapoints = np.int(self.parameter_dict["number_of_datapoints"])
        self.update_cycle = np.int(self.parameter_dict["update_cycle"])
        self.count_tot = 0
        self.count_bins = 0      
        for i in range(int(number_of_datapoints/self.update_cycle)):
            self.load_dac = False
            self.index = i
            if not self.check_user_update():
                return
            if self.run_mode == 0:
                self.kernel_run_pulse_counting()
            elif self.run_mode == 1:
                self.kernel_run_ROI_counting()
            elif self.run_mode == 2:
                self.kernel_run_hist_counting()
            elif self.run_mode == 3:
                self.kernel_run_outputting()
            elif self.run_mode == 5:
                self.kernel_run_ROI_lifetime_optimize()
            

    def get_run_mode(self):
        self.run_mode = np.int32(self.get_dataset(key="optimize.flag.run_mode"))

    def get_dac_vs(self):
        dac_vs = {}
        self.dac_pins = []
        self.dac_pins_voltages = []
        for e in self.controlled_electrodes:
            if e == "trigger_level":
                dac_vs[e] = self.get_dataset(key="optimize.parameter.trigger_level")
                self.dac_pins.append(self.pin_matching[e])
                self.dac_pins_voltages.append(self.get_dataset(key="optimize.parameter.trigger_level"))
            else:
                dac_vs[e] = self.get_dataset(key="optimize.e."+e)
                self.dac_pins.append(self.pin_matching[e])
                self.dac_pins_voltages.append(self.get_dataset(key="optimize.e."+e))
        self.dac_vs = dac_vs

    def get_parameter_dict(self):
        self.parameter_name_list = []
        self.parameter_value_list = []
        parameter_dict = {}
        for p in self.controlled_parameters:
            # parameter_list.append(np.int(self.get_dataset(key="optimize.parameter."+i)))
            parameter_dict[p] = self.get_dataset(key="optimize.parameter."+p)
            self.parameter_name_list.append(p)
            self.parameter_value_list.append(parameter_dict[p])
        self.parameter_dict = parameter_dict
        self.get_parameter_list()

    def get_parameter_list(self):
        t_load_index = self.parameter_name_list.index("t_load")
        t_wait_index = self.parameter_name_list.index("t_wait")
        t_delay_index = self.parameter_name_list.index("t_delay")
        t_acquisition_index = self.parameter_name_list.index("t_acquisition")
        number_of_repetitions_index = self.parameter_name_list.index("number_of_repetitions")
        number_of_datapoints_index = self.parameter_name_list.index("number_of_datapoints")
        pulse_counting_time_index = self.parameter_name_list.index("pulse_counting_time")
        

        t_load = np.int32(self.parameter_value_list[t_load_index])
        t_wait = np.int32(self.parameter_value_list[t_wait_index])
        t_delay = np.int32(self.parameter_value_list[t_delay_index])
        t_acquisition = np.int32(self.parameter_value_list[t_acquisition_index])
        number_of_repetitions = np.int32(self.parameter_value_list[number_of_repetitions_index])
        number_of_datapoints = np.int32(self.parameter_value_list[number_of_datapoints_index])
        pulse_counting_time = np.int32(self.parameter_value_list[pulse_counting_time_index])
       

        self.ordered_parameter_list = [t_load,t_wait,t_delay,t_acquisition,number_of_repetitions,number_of_datapoints,pulse_counting_time]

        return [t_load,t_wait,t_delay,t_acquisition,number_of_repetitions,number_of_datapoints,pulse_counting_time]

    # def loadDACoffset(self):
    #     # create list of lines from dataset
    #     f = '/home/electron/artiq/electron/zotino_offset_new_amplifier.txt'
    #     tmp = np.loadtxt(f)
    #     offset = np.zeros((tmp.shape[0],tmp.shape[1]+1))
    #     for i in range(tmp.shape[0]):
    #         a = np.append(tmp[i],tmp[i][-1])
    #         offset[i] = a
    #     self.offset = offset
    
    def loadDACoffset(self):
        # create list of lines from dataset
        f = '/home/electron/artiq-nix/electron/zotino_calibration_3dtrap.txt'
        tmp = np.loadtxt(f) # = np.array([y0,slope])
        self.dac_calibration_fit = tmp 
        self.dac_manual_offset = [0.,0.,-0.002,0.,0.002,0.,-0.003,0.,0.,-0.001,0.,0.,0.,0.,-0.002,0.,0.001,0.01,0.,0.,0.,0.,0.,0.005,0.003,0.]

    def set_dac_voltages(self):
        #,dac_vs):
        self.loadDACoffset()
        self.get_dac_vs()
        # self.load_voltages()
        self.kernel_load_dac()

    def check_user_update(self):
        flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
        flag_parameter = np.int32(self.get_dataset(key="optimize.flag.p"))
        flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
        if flag_stop == 1:
            if self.run_mode == 0:
                self.set_dataset('optimize.result.count_tot',[-100]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in in pusle counting
                # self.set_dataset('optimize.result.count_PI',[-10]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in in shutter optimize
                # for i in range(self.index*self.update_cycle):
                    # self.mutate_dataset('optimize.result.count_tot',i,-100)
                # print("Experiment terminated")
                return False
            elif self.run_mode == 1:
                self.set_dataset('optimize.result.count_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in with ROI in optimize
                self.set_dataset('optimize.result.countrate_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl_MCP_in with ROI in optimize without accumulating
                # for j in range(self.index*self.update_cycle):
                #     self.mutate_dataset('optimize.result.count_ROI',j,-2)
                #     self.mutate_dataset('optimzie.result.countrate_ROI',j,-2)
                # print("Experiment terminated")
                return False
            elif self.run_mode == 2:
                self.set_dataset('optimize.result.bin_times', [-1]*0,broadcast=True)
                # print("Experiment terminated")
                return False
            elif self.run_mode == 3:
                return False
        if flag_dac == 1:
            # load dac voltages
            self.get_dac_vs()
            self.load_dac = True
            self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True)
        if flag_parameter == 1:
            self.get_parameter_dict()
            self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True)
        return True
    

    @ kernel
    def kernel_load_dac(self):
        self.core.reset()
        self.zotino0.init()
        self.core.break_realtime()
        for i in range(len(self.dac_pins)):
            delay(500*us)
            m = self.dac_calibration_fit[1][self.dac_pins[i]]
            b = self.dac_calibration_fit[0][self.dac_pins[i]]
            self.zotino0.write_dac(self.dac_pins[i],(self.dac_pins_voltages[i]+b)/m - self.dac_manual_offset[self.dac_pins[i]])
            # self.zotino0.write_dac(self.dac_pins[i],self.dac_pins_voltages[i]/m)
            # self.zotino0.write_offset(self.dac_pins[i],-b/m)
        for pin in self.gnd:
            delay(500*us)
            self.zotino0.write_dac(pin,0.0)
            m = self.dac_calibration_fit[1][pin]
            b = self.dac_calibration_fit[0][pin]
            self.zotino0.write_offset(pin,-b/m)
        self.zotino0.load()
        print("Loaded dac voltages")


    @ kernel
    def set_individual_electrode_voltages(self,e):
        

        self.core.reset()
        self.zotino0.init()
        self.core.break_realtime() 
        for key in e:
            delay(500*us)
            m = self.dac_calibration_fit[1][self.pin_matching[key]]
            b = self.dac_calibration_fit[0][self.pin_matching[key]]
            self.zotino0.write_dac(self.pin_matching[key],(e[key]+b)/m)
            # self.zotino0.write_dac(self.pin_matching[key],e[key]/m)
            # self.zotino0.write_offset(self.pin_matching[key],-b/m)    
        self.zotino0.load()
        print("Loaded dac voltages")


    @ kernel
    def kernel_run_outputting(self):
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]
        
        # t_load = np.int32(self.parameter_dict["t_load"])
        # t_wait = np.int32(self.parameter_dict["t_wait"])
        # t_delay = np.int32(self.parameter_dict["t_delay"])
        # # t_acquisition = np.int32(self.parameter_dict[3])
        # # trigger_level = self.parameter_dict[5]
        # number_of_repetitions = np.int32(self.parameter_dict["number_of_repetitions"])
        # number_of_datapoints = np.int32(self.parameter_dict["number_of_datapoints"])

        if self.load_dac:
            self.kernel_load_dac()
            
        for k in range(self.update_cycle):
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    # with parallel:
                    #     self.ttl8.on()
                    #     self.ttl12.on()
                    # delay(t_load*us)
                    # with parallel:
                    #     self.ttl8.off()
                    #     self.ttl12.off()
                    self.ttl_390.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl_390.off()
                        # delay(1500*ns) # get rid of the photo diode fall time
                        self.ttl9.on()  
                    delay(t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl_Extraction.pulse(2*us)
                        self.ttl_TimeTagger.pulse(2*us)
                    # delay(1*us)
                    delay(t_delay*ns)

    @ kernel
    def kernel_run_ROI_counting(self):
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]
        
        if self.load_dac:
            self.kernel_load_dac()
            
        for k in range(self.update_cycle):
            countrate_tot = 0 
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl_390.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl_390.off()
                        self.ttl9.on()
                    delay(t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl_Extraction.pulse(2*us)
                        self.ttl_TimeTagger.pulse(2*us)
                        with sequential:
                            delay(200*ns)
                            self.ttl12.pulse(2*us)
                        with sequential:
                            delay(t_delay*ns)
                            t_count = self.ttl_MCP_in.gate_rising(t_acquisition*ns)
                    count = self.ttl_MCP_in.count(t_count)
                    if count > 0:
                        count = 1
                    self.count_tot += count
                    countrate_tot += count
                    delay(10*us)
            self.mutate_dataset('optimize.result.count_ROI',self.index*self.update_cycle+k,self.count_tot)
            self.mutate_dataset('optimize.result.countrate_ROI',self.index*self.update_cycle+k,countrate_tot)         
        
    @ kernel
    def kernel_run_ROI_lifetime_optimize(self):
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]
        wait_times = [t_wait, 5*t_wait]

        if self.load_dac:
            self.kernel_load_dac()

        
        
        for k in range(self.update_cycle):
            countrates = [0,0]
            for n in range(len(wait_times)):
                countrate_tot = 0 
                for j in range(number_of_repetitions):
                    self.core.break_realtime()
                    with sequential:
                        self.ttl_390.on()
                        delay(t_load*us)
                        with parallel:
                            self.ttl_390.off()
                            self.ttl9.on()
                        delay(wait_times[n]*us)
                        with parallel:
                            self.ttl9.off()
                            self.ttl_Extraction.pulse(2*us)
                            self.ttl_TimeTagger.pulse(2*us)
                            with sequential:
                                delay(200*ns)
                                self.ttl12.pulse(2*us)
                            with sequential:
                                delay(t_delay*ns)
                                t_count = self.ttl_MCP_in.gate_rising(t_acquisition*ns)
                        count = self.ttl_MCP_in.count(t_count)
                        if count > 0:
                            count = 1
                        self.count_tot += count
                        countrate_tot += count
                        delay(10*us)
                countrates[n] = countrate_tot
            countrate_difference = (countrates[0] - countrates[1])/(countrates[0]+1)
            self.mutate_dataset('optimize.result.differential_countrate_ROI_lifetime_optimize',self.index*self.update_cycle+k,countrate_difference)
            self.mutate_dataset('optimize.result.short_wait_countrate_ROI_lifetime_optimize',self.index*self.update_cycle+k,countrates[0])
            self.mutate_dataset('optimize.result.long_wait_countrate_ROI_lifetime_optimize',self.index*self.update_cycle+k,countrates[1])


    @ kernel
    def kernel_run_hist_counting(self):
        self.core.reset() # this is important to avoid overflow error
        self.core.break_realtime()

        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]

        t_total = t_load*1000+t_wait*1000+t_delay+t_acquisition+1000 # cycle duration (ns)
        gate_rising_time = t_total + 1000 # hard coded gate_rising_time for now

        if self.load_dac:
            self.kernel_load_dac()

        for k in range(self.update_cycle):
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                t_start = now_mu()
                t_end = self.ttl_MCP_in.gate_rising(gate_rising_time*ns) # somehow it only works if the gate_rising is within the loop    
                at_mu(t_start)
                self.ttl8.on()
                delay(t_load*us)   
                self.ttl8.off()
                delay(t_wait*us) # negative t_wait cause it to output 6/10
                self.ttl_Extraction.pulse(200*ns)
                delay((t_delay+t_acquisition)*ns)
                delay(1*us)
            
                # Timestamp events
                tstamp = self.ttl_MCP_in.timestamp_mu(t_end)
                while tstamp != -1:
                    timestamp = self.core.mu_to_seconds(tstamp)-self.core.mu_to_seconds(t_start)
                    timestamp_us = timestamp*1e6 # in ns scale for now
                    self.append_to_dataset('optimize.result.bin_times',timestamp_us)
                    tstamp = self.ttl_MCP_in.timestamp_mu(t_end)
                    # delay(100*ns) 
            delay(100*ns)
            self.make_hist()

    def make_hist(self):

        hist_data = self.get_dataset("optimize.result.bin_times")
        self.bins = int(self.get_dataset("optimize.parameter.bins"))
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
        # a,b=np.histogram(hist_data[(hist_data > 1 ) & (hist_data<1000)],bins=50)      
        
        a,b=np.histogram(hist_data,bins=self.bins)           
        self.set_dataset('optimize.result.hist_ys', a, broadcast=True)
        self.set_dataset('optimize.result.hist_xs', b, broadcast=True)
        return 

    @kernel
    def kernel_run_pulse_counting(self):
        self.core.reset()
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]

        if self.load_dac:
            self.kernel_load_dac()

        if self.index == 0:
            self.ttl_390.on() # AOM
        # self.core.break_realtime()
        for k in range(self.update_cycle):
            self.core.break_realtime()
            with parallel:
                t_count = self.ttl_MCP_in.gate_rising(pulse_counting_time*ms)
                self.ttl_Extraction.pulse(2*us) # extraction pulse    
            count = self.ttl_MCP_in.count(t_count)

            self.mutate_dataset('optimize.result.count_tot',self.index*self.update_cycle+k,count)

    def kernel_run_lifetime_measurement(self):
        self.kernel_run_lifetime_measurement1()
        self.fit_lifetime()

    @ kernel
    def kernel_run_lifetime_measurement1(self):
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        # t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]
        # wait_times = [ 1.000,2.154,4.641,10.000,21.544,46.415,100.000,215.443,464.158,1000.000,10000.0]#,50000.0]
        wait_times = self.wait_times

        if self.load_dac:
            self.kernel_load_dac()
        
        for i in range(len(wait_times)):
            count_tot = 0
            t_wait = wait_times[i]
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl_390.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl_390.off()
                        self.ttl9.on()
                    delay(t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl_Extraction.pulse(2*us)
                        self.ttl_TimeTagger.pulse(2*us)
                        with sequential:
                            delay(200*ns)
                            self.ttl12.pulse(2*us)
                        with sequential:
                            delay(t_delay*ns)
                            t_count = self.ttl_MCP_in.gate_rising(t_acquisition*ns)
                    count = self.ttl_MCP_in.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count   
            self.mutate_dataset('optimize.result.lifetime.counts',i,count_tot)
            self.mutate_dataset('optimize.result.lifetime.wait_times',i,wait_times[i])

    def exp_decay(self,time,amp,tau):
        return amp*np.exp(-time/tau)
    def number_conversion(self,detection_probability):
        lambdas = np.arange(0,30,0.0001)
        min_index = np.argmin(np.abs(np.exp(-lambdas)-(1-detection_probability)))
        return lambdas[min_index]
    def fit_lifetime(self):
        # wait_times = [ 1.000,2.154,4.641,10.000,21.544,46.415,100.000,215.443,464.158,1000.000,10000.0]#,50000.0]
        wait_times = self.wait_times
        counts = self.get_dataset(key="optimize.result.lifetime.counts")
        reps = self.get_dataset(key = "optimize.parameter.number_of_repetitions")
        counts = [count/reps for count in counts]
        ne = [(self.number_conversion(counts[i]))*3 for i in range(len(counts))]
        popt, pcov = curve_fit(self.exp_decay,wait_times[:],ne[:],p0 = [1.25,100],bounds=([0,0],[500,1000000]))
        fit_error = np.sqrt(np.diag(pcov))[1]
        lifetime = popt[1]
        self.set_dataset(key='optimize.result.lifetime.lifetime_fit',value=lifetime,broadcast=True)
        print("Lifetime = " + str (lifetime) + " us +- " + str(fit_error) + " us")



    # @ kernel
    # def load_voltages(self):
    #     self.core.reset()
    #     self.zotino0.init()
    #     self.core.break_realtime() 
    #     for pin in range(self.ne):
    #         delay(500*us)
    #         self.zotino0.write_dac(self.pins[pin],self.dac_vs[pin])
    #         index = 10+int(np.rint(self.dac_vs[pin]))
    #         self.zotino0.write_offset(self.pins[pin],self.offset[self.pins[pin]][index])    
    #     self.zotino0.load()
    #     print("Loaded dac voltages")



class Electron_GUI_3Dprint(Electron, EnvExperiment):
    def build(self):
        Electron.build(self)

    def prepare(self):
        Electron.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):

        # self.launch_GUI()
        print("Hello World")




