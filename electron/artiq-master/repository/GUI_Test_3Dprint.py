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
import vxi11
import matplotlib.pyplot as plt

print:{'DC0': -0.5075085462745209, 'DC1': -4.115645125835921, 'DC2': 0.6052160671822544, 'DC3': -3.8292321930411064, 'DC4': 0.43824986625602186, 'DC5': -4.006012630929934, 'DC6': 0.5381631236942458, 'DC7': -3.9120137594360784, 'DC8': 0.4651545437632938, 'trigger_level': 0.06}
class Electron(HasEnvironment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0') # artiq DAC
        self.setattr_device('ttl1')
        self.setattr_device('ttl_MCP_in') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        self.setattr_device('ttl8') 
        self.setattr_device('ttl_Tickle') # use this channel to trigger R&S for tickle pulse, connect to R&S
        self.setattr_device('ttl_Extraction') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device("ttl_TimeTagger") # time tagger start click

        self.setattr_device("ttl12")
        self.setattr_device("ttl13")
        self.setattr_device("ttl20")
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
        self.set_dataset(key="optimize.parameter.V_grid", value = np.int(10), broadcast=True, persist=True) # number of datapoints per update cycle
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

        self.controlled_parameters = ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints","bins","update_cycle","V_grid"]
        

        self.old_c_file = False
        self.c_file_csv = '/home/electron/artiq-nix/electron/flipped_Electron3dTrap_200um_v6_cfile_grid.csv'
        
        self.controlled_multipoles_dict = {"Ex":'Ex:', "Ey":'Ey:', "Ez":'Ez:', "U1":'U1:', "U2":'U2:', "U3":'U3:', "U4":'U4:', "U5":'U5:'}
        self.controlled_parameters_dict = {"t_load":'Load time (us):', "t_wait":'Wait time (us):', "t_delay":'Delay time (ns):',"t_acquisition":'Acquisition time(ns):' , "pulse_counting_time":'Pulse counting time (ms):',"trigger_level":'Trigger level (V):',"number_of_repetitions":'# Repetitions:', "number_of_datapoints":'# Datapoints:', "bins":'# Bins:',"update_cycle":'# Update cycles:',"V_grid": "V gird (V)"}
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
        f = '/home/electron/artiq-nix/electron/zotino_calibration/zotino_calibration_20241114.txt'
        tmp = np.loadtxt(f) # = np.array([y0,slope])
        self.dac_calibration_fit = tmp 
        # self.dac_manual_offset = [0.,0.,-0.002,0.,0.002,0.,-0.003,0.,0.,-0.001,0.,0.,0.,0.,-0.002,0.,0.001,0.01,0.,0.,0.,0.,0.,0.005,0.003,0.]

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
            # self.zotino0.write_dac(self.dac_pins[i],(self.dac_pins_voltages[i]+b)/m - self.dac_manual_offset[self.dac_pins[i]])
            self.zotino0.write_dac(self.dac_pins[i],self.dac_pins_voltages[i]/m)
            self.zotino0.write_offset(self.dac_pins[i],-b/m)
        for pin in self.gnd:
            delay(500*us)
            self.zotino0.write_dac(pin,0.0)
            m = self.dac_calibration_fit[1][pin]
            b = self.dac_calibration_fit[0][pin]
            self.zotino0.write_offset(pin,-b/m)
        self.zotino0.load()
        print("Loaded dac voltages")


    
    def set_individual_electrode_voltages(self,e):
        
        # self.core.reset()
        # self.zotino0.init()
        # self.core.break_realtime()
        self.set_dac_voltages() 
        # for key in e:
        #     delay(500*us)
        #     m = self.dac_calibration_fit[1][self.pin_matching[key]]
        #     b = self.dac_calibration_fit[0][self.pin_matching[key]]
        #     self.zotino0.write_dac(self.pin_matching[key],(e[key]+b)/m)
        #     # self.zotino0.write_dac(self.pin_matching[key],e[key]/m)
        #     # self.zotino0.write_offset(self.pin_matching[key],-b/m)    
        # self.zotino0.load()
        # print("Loaded dac voltages")


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
                        self.ttl_Tickle.on()  
                    delay(t_wait*us)
                    with parallel:
                        self.ttl_Tickle.off()
                        self.ttl_Extraction.pulse(2*us)
                        self.ttl_TimeTagger.pulse(2*us)
                        with sequential:
                            delay(560*ns) # 570
                            self.ttl20.pulse(2*us)
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
                            self.ttl_Tickle.on()
                        delay(wait_times[n]*us)
                        with parallel:
                            self.ttl_Tickle.off()
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

class rigol():
    def __init__(self,ip=115,pulse_width_ej=800.E-9, pulse_delay_ej=2.E-9,offset_ej=0,amplitude_ej=-20,phase=0,period_ej=1000.E-9,sampling_time=2.E-9):
        # self.sampling_time = sampling_time # 
        
        # initial phase != 0, voltage 0 ~ -20 V, need to manually adjust and see on the scope or AWG
        self.pulse_width_ej = pulse_width_ej
        self.pulse_delay_ej = pulse_delay_ej
        self.offset_ej = offset_ej
        self.amplitude_ej = amplitude_ej
        self.phase = phase
        self.period_ej = period_ej
        self.sampling_time = sampling_time
        self.inst = vxi11.Instrument('TCPIP0::192.168.169.'+str(ip)+'::INSTR')
        
       

    def run(self):
        inst = self.inst
        inst.write("OUTPUT2 OFF")
        inst.write("OUTPUT1 OFF")   
        # hardcode sampling rate for ejection pulse, since only need the first few hundred ns
        
        # ###### use channel one to extrac on the bottom two central electrodes
        # waveform_ej = np.zeros(int(self.period_ej/self.sampling_time))
        waveform_ej = np.zeros(500)
        waveform_ej[:] = 1
        waveform_ej[np.int(self.pulse_delay_ej/self.sampling_time):np.int((self.pulse_delay_ej+self.pulse_width_ej)/self.sampling_time)] = -1
        ej_str = ",".join(map(str,waveform_ej))
        # Channel 1
        inst.write(":OUTPut1:LOAD INFinity")
        inst.write("SOURCE1:PERIOD {:.9f}".format(self.period_ej))
        # print(inst.ask("SOURCE2:PERIOD?"))
        inst.write("SOURCE1:VOLTage:UNIT VPP")
        inst.write("SOURCE1:VOLTage {:.3f}".format(self.amplitude_ej))
        inst.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(self.offset_ej))
        inst.write("SOURCE1:TRACE:DATA VOLATILE,"+ ej_str)
        # inst.write("SOURCE2:PHASe 20")
        
        inst.write("SOURce1:BURSt ON")

        # inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))

        # inst.write("SOURce1:BURSt:GATE:POL NORMal")

        # inst.write("SOURce1:BURSt:PHASe {:.3f}".format(self.phase))


        inst.write("SOURce1:BURSt:MODE TRIGgered")
        inst.write("SOURce1:BURSt:NCYCles 1")
        # inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
        inst.write("SOURCe1:BURSt:TRIGger:SOURce EXTernal")
        inst.write("SOURce1:BURSt:TRIGger:SLOPe POSitive")


        inst.write("OUTPUT1 ON")
        # inst.write("OUTPUT2 ON")
        return

class RS():
    def __init__(self, sampling_time=0):
        self.inst = vxi11.Instrument('TCPIP::192.168.169.101::INSTR')
        print(self.inst.ask('*IDN?'))

    def run(self, freq, power):
        self.freq = freq
        self.power = power
        inst = self.inst
        # inst.write("OUTPut OFF")
        # Channel 1
        # print(inst.ask(":OUTPut:IMPedance?"))
        inst.write("SOURce:FREQuency: MODE CW")
        inst.write("SOURce:FREQuency {:.9f}".format(self.freq))
        inst.write("SOURce:POWer:POWer {:.3f}".format(self.power))
        inst.write('SOURce:MOD:ALL:STAT ON')
        inst.write("OUTPut ON")
        #print(inst.ask("OUTPUT?"))
        return 

    # def stop(self):
    #     inst = self.inst
    #     inst.write('OUTPut OFF')
    #     inst.write('SOURce:MOD:ALL:STAT OFF')




'''
rs = RS()
frequencies = np.arange(66, 77, 0.1) * 1E6
amp_trapfreq = -20.0
U2 = -0.7
Prf = +2.5
load_time = 200 E-6
wait_time = 4000E-6
for freq_trapfreq in frequencies:
    rs.run(freq_trapfreq,amp_trapfreq)
'''


# Creating tab widgets
class MyTabWidget(HasEnvironment,QWidget):
    
    def __init__(self, Env, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.HasEnvironment = Env
        self.controlled_electrodes = self.HasEnvironment.controlled_electrodes
        self.controlled_multipoles = self.HasEnvironment.controlled_multipoles
        self.controlled_parameters = self.HasEnvironment.controlled_parameters
        self.controlled_multipoles_dict = self.HasEnvironment.controlled_multipoles_dict
        self.controlled_parameters_dict = self.HasEnvironment.controlled_parameters_dict
        self.controlled_electrodes_dict = self.HasEnvironment.controlled_electrodes_dict
        self.old_c_file = self.HasEnvironment.old_c_file
        self.c_file_csv = self.HasEnvironment.c_file_csv

        self.setup_UI()
        self.ne = self.HasEnvironment.ne
        self.e=np.full(self.ne, 0.0)



    
    def set_dac_voltages(self):#,dac_vs):
        self.HasEnvironment.set_dac_voltages()#dac_vs)

    def setup_UI(self):
  
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()
        self.tab7 = QWidget()
        self.tabs.resize(300, 150)
  
        # Add tabs
        # self.tabs.addTab(self.tab2, "MULTIPOLES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        # self.tabs.addTab(self.tab3, "PARAMETERS")
        self.tabs.addTab(self.tab4, "Main Experiment") # This tab could mutate dac_voltage, parameters, flags dataset and run_self_updated
        self.tabs.addTab(self.tab1, "ELECTRODES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        self.tabs.addTab(self.tab5, "DEVICES")
        self.tabs.addTab(self.tab7, "RS")
        self.tabs.addTab(self.tab6, "Cryostat")
    
          
        '''
        ELECTRODES TAB
        '''
        grid1 = QGridLayout()  
        self.ELECTRODES = ["DC0","DC1","DC2","DC3","DC4","DC5","DC6","DC7","DC8"]  # Labels for text entry
        xcoord_labels = [0,0,0,0,0,0,0,0,0]
        xcoord_entrys = [1,1,1,1,1,1,1,1,1]
        ycoords = [0,1,2,3,4,5,6,7,8]

        
        self.electrode_spin = {}
        
        #electrode grid
        for i in range(9):            
            
            
            xcoord_label = xcoord_labels[i]
            xcoord_entry = xcoord_entrys[i]
            ycoord = ycoords[i]
            
            spin = QtWidgets.QDoubleSpinBox(self)
            spin.setRange(-10,10)
            spin.setSingleStep(0.01)
            spin.setDecimals(4)
            # spin.setValue(self.default_voltages[index_v]) # set default values
            # index_v += 1
            grid1.addWidget(spin,ycoord,xcoord_entry,1,1)
            # self.electrodes.append(spin)
            self.electrode_spin[self.ELECTRODES[i]] = spin
            label = QLabel('       '+self.ELECTRODES[i], self)
            label.setAlignment(QtCore.Qt.AlignRight)
            grid1.addWidget(label,ycoord,xcoord_label,1,1)
    
        

        # add textbox color
        for el in self.electrode_spin.values():
            el.editingFinished.connect(lambda el=el: self.change_background(el))
       
        # add voltage button
        v_button = QPushButton('Set Voltage values (only mutate the dataset)', self)
        v_button.clicked.connect(self.on_voltage_click)
        grid1.addWidget(v_button, 0, 6, 2, 1)

        # add voltage button
        v_button = QPushButton('Load Individual Voltage values', self)
        v_button.clicked.connect(self.on_load_individual_voltage_click)
        grid1.addWidget(v_button, 1, 6, 2, 1)


        
        #add grid layout (grid1) to tab1
        grid1.setRowStretch(4, 1)
        self.tab1.setLayout(grid1)
        
        #set electrode values for dataset
        self.e=self.electrode_spin
    

        '''
        MAIN EXPERIMENT TAB
        '''
        grid4 = QGridLayout() #make grid layout
        
        self.parameter_spin = {}  
        #create parameter text entry boxes
        # self.default = [100,100,600,100,500,0.3,1000,1000,50,10] # default values
        self.default_parameter = self.get_default_parameter() # read data from dataset
        
        # PARAMETERS1 = ['Load time (us):', 'Wait time (ns):', 'Delay time (ns):','Acquisition time(ns):' , 'Pulse counting time (ms):']
        # DEFAULTS1 = self.default_parameter[0:5] # default values
        i = 0
        for p in self.controlled_parameters:  
            spin = QtWidgets.QDoubleSpinBox(self)
            if p == "trigger_level":
                spin.setRange(0,5)
                spin.setSingleStep(0.01)
                spin.setDecimals(4)
            else:
                spin.setRange(-10000000,10000000)
                spin.setSingleStep(10)
            spin.setValue(self.default_parameter[p]) # set default values
            self.parameter_spin[p] = spin
            label = QLabel('    '+self.controlled_parameters_dict[p], self)
            if i < int(len(self.controlled_parameters)/2):
                grid4.addWidget(spin,i+12,1,1,1)
                grid4.addWidget(label,i+12,0,1,1)
            else:
                grid4.addWidget(spin,i-int(len(self.controlled_parameters)/2)+12,5,1,1)
                grid4.addWidget(label,i-int(len(self.controlled_parameters)/2)+12,4,1,1)  
            i += 1

          
        #spacing
        label_gap = QLabel('', self)
        grid4.addWidget(label_gap,0,2,1,2)



    
        #[values (from list), x-coord (label), x-coord (entrtyBox), y-coord (first entry)]
        self.ELECTRODES = ["DC0","DC1","DC2","DC3","DC4","DC5","DC6","DC7","DC8"]  # Labels for text entry
        xcoord_labels = [0,0,0,0,0,0,0,0,0]
        xcoord_entrys = [1,1,1,1,1,1,1,1,1]
        ycoords = [0,1,2,3,4,5,6,7,8]

        self.electrode_labels = {}     
        # get default electrode voltages
        self.default_voltages = self.get_default_voltages()
        #electrode grid
        for i in range(len(self.ELECTRODES)):  
            xcoord_label = xcoord_labels[i]
            xcoord_entry = xcoord_entrys[i]
            ycoord = ycoords[i]  
            label = QLabel('       '+ self.ELECTRODES[i], self)
            label.setAlignment(QtCore.Qt.AlignRight)
            grid4.addWidget(label,ycoord,xcoord_label, 1,1)
            # label0 = QLabel('0.00', self)
            label0 = QLabel(str(self.default_voltages[self.ELECTRODES[i]]), self)
            self.electrode_labels[self.ELECTRODES[i]] = label0
            label0.setStyleSheet("border: 1px solid black;")
            grid4.addWidget(label0,ycoord,xcoord_entry,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid4.addWidget(label_gap,5,1,1,1)

        #create multipole text entry boxes
        self.multipole_spin = {}
        self.default_multipoles = self.get_default_multipoles()
        i = 0
        for m in self.controlled_multipoles:  
            spin = QtWidgets.QDoubleSpinBox(self)
            spin.setDecimals(4)
            if m == 'Grid':
                spin.setRange(-1000,3000)
            else:
                spin.setRange(-100,100)
            spin.setSingleStep(0.01)
            spin.setValue(self.default_multipoles[m])
            grid4.addWidget(spin,i,8,1,1)
            self.multipole_spin[m] = spin
            label = QLabel(self.controlled_multipoles_dict[m], self)
            label.setAlignment(QtCore.Qt.AlignRight)
            grid4.addWidget(label,i,7,1,1)
            i += 1


        # from left to right, top to bottom : 11,7 -> 16,7, 11,8 -> 16,8

        # add update dataset button, this is to update the dataset from the user set values in GUI
        v_button = QPushButton('Update Dataset', self)
        v_button.clicked.connect(self.on_update_dataset_click)
        grid4.addWidget(v_button, 12, 7)

        # add load multipole voltage button, this is to update the dataset and load the voltages
        self.lm_button = QPushButton('Load Multipole Voltages', self)
        self.lm_button.clicked.connect(self.on_load_multipole_voltages_click)
        grid4.addWidget(self.lm_button, 13, 7)

        # add c-file button, this is to load c file
        c_button = QPushButton('Load C-file', self)
        c_button.clicked.connect(self.openFileDialog)
        grid4.addWidget(c_button, 14, 7)

        # add make hist button, this is to populate the histogram dataset based on bin times dataset for plotting histogram in applet
        hist_button = QPushButton('Make histogram', self)
        hist_button.clicked.connect(self.HasEnvironment.make_hist)
        grid4.addWidget(hist_button, 17, 7)


        self.lifetime_button = QPushButton('Run Lifetime Optimize', self)
        self.lifetime_button.clicked.connect(self.on_lifetime_optimize_click)
        grid4.addWidget(self.lifetime_button, 12, 8)


        # add pulse counting button, this is to set run_mode = 0 and run the kernel pulse counting
        self.pc_button = QPushButton('Run Pulse Counting', self)
        self.pc_button.clicked.connect(self.on_pulse_counting_click)
        grid4.addWidget(self.pc_button, 12, 9)


        # add ROI counting button, this is to set run_mode = 1 and run the kernel ROI counting
        self.rc_button = QPushButton('Run ROI Counting', self)
        self.rc_button.clicked.connect(self.on_roi_counting_click)
        grid4.addWidget(self.rc_button, 13, 9)

        # # add ROI counting button, this is to set run_mode = 1 and run the kernel ROI counting
        # self.rc_button = QPushButton('Run ROI with trap freq', self)
        # self.rc_button.clicked.connect(self.on_roi_trap_freq_click)
        # grid4.addWidget(self.rc_button, 14, 9)

        # add hist counting button, this is to set run_mode = 2 and run the kernel histogram counting
        self.hc_button = QPushButton('Run Hist Counting', self)
        self.hc_button.clicked.connect(self.on_hist_counting_click)
        grid4.addWidget(self.hc_button, 13, 8)

        # add hist counting button, this is to set run_mode = 2 and run the kernel histogram counting
        self.op_button = QPushButton('Run Outputting', self)
        self.op_button.clicked.connect(self.on_outputting_click)
        grid4.addWidget(self.op_button, 14, 8)

        # add lifetime measurement button, this is to set run_mode = 4 and run the kernel histogram counting
        self.lm_button = QPushButton('Lifetime Measurement', self)
        self.lm_button.clicked.connect(self.on_lifetime_measurement_click)
        grid4.addWidget(self.lm_button, 15, 9)

        # add stop button, this is to terminate the current run program on the kernel and reset the dataset
        t_button = QPushButton('Terminate', self)
        t_button.clicked.connect(self.on_terminate_click)
        grid4.addWidget(t_button, 16+1, 8)

        grid4.setRowStretch(4, 1)
        self.tab4.setLayout(grid4)


        '''
        DEVICE TAB
        '''
        grid5 = QGridLayout() #make grid layout
        
        self.device_parameter_list = []  
        # rigol_PARAMETERS = ['Pulse width (ns):', 'Pulse delay (ns):','Offset (V):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):']
        rigol_PARAMETERS = ['Ejection pulse width (ns):', 'Pulse delay (ns):','Offset (V)(= -Amplitude/2):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):'] # make it to be less confusing
        rigol_DEFAULTS = [100, 100, -5, 10, 0,1000,2]

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
        v_button.clicked.connect(self.on_run_rigol_extraction_click)
        grid5.addWidget(v_button, 8+2, 8)

        grid5.setRowStretch(4, 1)
        self.tab5.setLayout(grid5)


        '''
        RS
        '''
        grid6 = QGridLayout() #make grid layout
        
        self.device_parameter_list_RS = []  
        # rigol_PARAMETERS = ['Pulse width (ns):', 'Pulse delay (ns):','Offset (V):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):']
        RS_PARAMETERS = ['Frequency:', 'Amplitude:'] # make it to be less confusing
        RS_DEFAULTS = [1e6, -20]
        self.rs_param = RS_DEFAULTS

        for i in range(len(RS_PARAMETERS)):  
            spin = QtWidgets.QSpinBox(self)
            spin.setRange(-1E6,1E9)
            spin.setSingleStep(10)
            spin.setValue(RS_DEFAULTS[i]) # set default values
            grid6.addWidget(spin,i+11,1,1,1)
            self.device_parameter_list_RS.append(spin)
            label = QLabel('    '+RS_PARAMETERS[i], self)
            grid6.addWidget(label,i+11,0,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid6.addWidget(label_gap,0,2,1,2)
        
        # add extraction button
        v_button = QPushButton('Run RS Extraction', self)
        v_button.clicked.connect(self.on_run_RS_click)
        grid6.addWidget(v_button, 8+2, 8)

        grid6.setRowStretch(4, 1)
        self.tab7.setLayout(grid6)


        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)        
        return

    def on_run_RS_click(self):
        self.rs = RS()
        self.dev_list = []
        for m in self.device_parameter_list_RS:
            text = m.text() or "0"
            self.dev_list.append(float(text))
        freq = self.dev_list[0]
        amp = self.dev_list[1]
        self.rs.run(freq, amp)

    def on_run_rigol_extraction_click(self):
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

        #uncomment
        # self.rigol101 =  rigol(101,pulse_width_ej,pulse_delay_ej,offset_ej,amplitude_ej,phase,period_ej,sampling_time)

        self.rigol113 =  rigol(115,pulse_width_ej,pulse_delay_ej,offset_ej,amplitude_ej,phase,period_ej,sampling_time)

        #uncomment
        # self.rigol101.run()

        self.rigol113.run()

    def on_update_dataset_click(self):
        self.update_parameters()
        self.update_multipoles()
        

    def on_load_multipole_voltages_click(self):
        self.on_update_dataset_click()
        # self.e.append(self.HasEnvironment.get_dataset(key="optimize.parameter.trigger_level"))       
        self.set_dac_voltages()
        # print("on_multipole_click has updated voltages and mutated datasets")

    def on_voltage_click(self):
        # Create electrode list of floats
        self.elec_dict = {}
        for e in self.electrode_spin:
            text = self.electrode_spin[e].text() or "0"
            self.elec_dict[e] = float(text)
        
        # self.elec_dict["trigger_level"] = self.HasEnvironment.get_dataset(key="optimize.parameter.trigger_level")
        print(self.elec_dict)
        # # #after adjusting self.e order, same as pin order: [ bl1,...,bl5,br1,...,br5,tl1,...,tl5,tr1,..,tr5,b0(grid),t0]
        self.mutate_dataset_electrode()


    def on_load_individual_voltage_click(self):
        self.elec_dict = {}
        for e in self.electrode_spin:
            text = self.electrode_spin[e].text() or "0"
            self.elec_dict[e] = float(text)
        
        # self.elec_dict["trigger_level"] = self.HasEnvironment.get_dataset(key="optimize.parameter.trigger_level")
        print(self.elec_dict)
        # # #after adjusting self.e order, same as pin order: [ bl1,...,bl5,br1,...,br5,tl1,...,tl5,tr1,..,tr5,b0(grid),t0]
        self.mutate_dataset_electrode()
        self.HasEnvironment.set_individual_electrode_voltages(self.elec_dict)

    def on_terminate_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.stop",1, broadcast=True, persist=True)
        return

    def on_pulse_counting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",0, broadcast=True, persist=True)
        self.on_run_click()

    def on_roi_counting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",1, broadcast=True, persist=True)
        self.on_run_click()

    def on_hist_counting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",2, broadcast=True, persist=True)
        self.on_run_click()

    def on_outputting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",3, broadcast=True, persist=True)
        self.on_run_click()

    def on_lifetime_measurement_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",4, broadcast=True, persist=True)
        self.on_run_click()

    def on_lifetime_optimize_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",5, broadcast=True, persist=True)
        self.on_run_click()


    def on_run_click(self):
        self.thread = QThread() # create a QThread object
        self.worker = Worker(self.long_run_task) # create a worker object
        self.worker.moveToThread(self.thread) # move worker to the thread
        # connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)
        self.thread.start() # start the thread
        # final resets
        self.lm_button.setEnabled(False)
        self.rc_button.setEnabled(False)
        self.hc_button.setEnabled(False)
        self.op_button.setEnabled(False)
        self.pc_button.setEnabled(False)
        self.lm_button.setEnabled(False)
        self.lifetime_button.setEnabled(False)

        self.thread.finished.connect(
            lambda: self.lm_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.rc_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.hc_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.pc_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.op_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.lm_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.lifetime_button.setEnabled(True)
            )

    def long_run_task(self):
        self.HasEnvironment.set_dataset("optimize.flag.stop",0, broadcast=True, persist=True)
        self.on_update_dataset_click()
        self.on_run_rigol_extraction_click()
        self.HasEnvironment.core.reset()
        self.HasEnvironment.rolling_run()
        return

    
    def get_default_voltages(self):
        default = {}
        for e in self.controlled_electrodes_dict:
            if e == "trigger_level":
                default[e] = self.HasEnvironment.get_dataset(key="optimize.parameter."+e)
            else:
                default[e] = self.HasEnvironment.get_dataset(key="optimize.e."+e)
        return default

    def get_default_parameter(self):
        default = {}
        for p in self.controlled_parameters_dict:
            default[p] = self.HasEnvironment.get_dataset(key="optimize.parameter."+p)
        return default

    def get_default_multipoles(self):
        default = {}
        for m in self.controlled_multipoles:
            # default.append(0)
            default[m] = self.HasEnvironment.get_dataset("optimize.multipoles."+m)
        return default


    def update_multipoles(self):
        
        # Create multiple list of floats
        self.mul_dict = {}
        
        for m in self.multipole_spin:
            text = self.multipole_spin[m].text() or "0"
            self.mul_dict[m] = float(text)

    
        for m in self.controlled_multipoles:
            self.HasEnvironment.set_dataset("optimize.multipoles."+m, self.mul_dict[m], broadcast=True, persist=True)
       
        
        if not self.old_c_file:
            tmp = {}
            df = pd.read_csv(self.c_file_csv,index_col = 0)
            voltages = pd.Series(np.zeros(len(self.controlled_electrodes)-1),index = df.index.values)
            grid_m = {'C': 1.781389e-02,'Ey': -4.649592e-06,'Ez': 9.989530e-02,'Ex': 4.148890e-06,'U3': 4.179541e-07,'U4':2.342674e-05,'U2': 1.304532e-01,'U5': 2.279447e-05,'U1': 6.951562e-07}
            # grid_m = {'C': 0.019940897983726433,'Ey': -3.360905574255682e-05,'Ez': 0.00022449376590844223,'Ex': 0.06399536424651765,'U3': 0.13434433573433666,'U4': 0.0011390387152830977,'U2': 0.03015271954151855,'U5': -0.021575389610886914,'U1': 0.050389617844847405}
            V_grid = self.HasEnvironment.get_dataset(key="optimize.parameter.V_grid")
            # print("V_grid:",V_grid)
            # for m in self.controlled_multipoles:   
            #     if m == "Grid":
            #         pass
            #     else:
            #         self.mul_dict[m] = self.mul_dict[m] - grid_m[m]*V_grid/150
            #         # voltages += df[m] * self.mul_dict[m]
            print("Multipoles:",self.mul_dict)
            for m in self.controlled_multipoles:   
                if m == "Grid":
                    pass
                else:
                    tmp[m] = self.mul_dict[m] - grid_m[m]*V_grid
                    voltages += df[m] * tmp[m]
            print("Corrected Multipoles:",tmp)
            self.elec_dict = voltages.to_dict()
            self.elec_dict["trigger_level"] = self.parameter_dict["trigger_level"]
            # for e in self.elec_dict:
            #     self.elec_dict[e] = round(self.elec_dict[e],3)    
            print(self.elec_dict)

            for e in self.controlled_electrodes:
                if e == "trigger_level":
                    pass
                else:
                    self.electrode_labels[e].setText(str(round(self.elec_dict[e],4)))      
            self.mutate_dataset_electrode()


        else:
            self.mul_list = []
            for m in self.HasEnvironment.controlled_multipoles[1:]:
                self.mul_list.append(self.mul_dict[m])
            
            # Calculate and print electrode values
            try:
                
                self.m=np.array([self.mul_list])
                self.grid_multipole_150V = np.array([0.0203082,0.00042961,-0.00124763,-0.047735,-0.00441363,0.00081879,0.00012903,-0.03539802,-0.00083521])
                self.grid_multipole_150V = self.grid_multipole_150V[0:len(self.HasEnvironment.controlled_multipoles)-1]
                grid_multipole = [g*grid_V/150 for g in self.grid_multipole_150V]
                self.m=self.m-grid_multipole
                self.e=np.matmul(self.m, self.C_Matrix_np)
            except:
                f = open('/home/electron/artiq-nix/electron/Cfile_3layer.txt','r')
                # create list of lines from selected textfile
                self.list_of_lists = []
                for line in f:
                    stripped_line = line.strip()
                    line_list = stripped_line.split()
                    self.list_of_lists.append(float(line_list[0]))
                    
                # create list of values from size 21*9 C-file
                curr_elt = 0
                self.C_Matrix = []
                for i in range(len(self.HasEnvironment.controlled_multipoles)-1):
                    C_row = []
                    for i in range(self.ne-1): #-1 because of the channel 0 for trigger level
                        C_row.append(self.list_of_lists[curr_elt])
                        curr_elt+=1
                    self.C_Matrix.append(C_row) 
                    
                self.C_Matrix_np = np.array(self.C_Matrix)
                self.m=np.array([self.mul_list])
                #print(shape(self.m))
                # grid_V = 150
                self.grid_multipole_150V = np.array([0.0203082,0.00042961,-0.00124763,-0.047735,-0.00441363,0.00081879,0.00012903,-0.03539802,-0.00083521])
                self.grid_multipole_150V = self.grid_multipole_150V[0:len(self.HasEnvironment.controlled_multipoles)-1]
                grid_multipole = [g*grid_V/150 for g in self.grid_multipole_150V]
                self.m=self.m-grid_multipole
                self.e=np.matmul(self.m, self.C_Matrix_np)
                
            for i in range(len(self.e[0])):
                if self.e[0][i]>=self.HasEnvironment.max_voltage:
                    print(f'warning: voltage {round(self.e[0][i],3)}  exceeds limit')
                    self.e[0][i]=self.HasEnvironment.max_voltage
                elif self.e[0][i]<=-self.HasEnvironment.max_voltage:
                    print(f'warning: voltage {round(self.e[0][i],3)} exceeds limit')
                    self.e[0][i]=-self.HasEnvironment.max_voltage

            self.e = self.e[0].tolist()
            #self.e.append(self.e.pop(10))      
            for i in range(len(self.e)):
                self.e[i]=round(self.e[i],3)
            print("self.e:",self.e)

            

            
            #self.e is in alphabetical order as in c file: [bl1,...,bl5,br1,...,br5, tg("grid"),tl1,...,tl5,tr1,..,tr5]
            self.elec_dict={'bl1':self.e[0],'bl2':self.e[1],'bl3':self.e[2],'bl4':self.e[3],'bl5':self.e[4],'br1':self.e[5],'br2':self.e[6],'br3':self.e[7],'br4':self.e[8],'br5':self.e[9],'tg':self.e[10],'tl1':self.e[11],'tl2':self.e[12],'tl3':self.e[13],'tl4':self.e[14],'tl5':self.e[15],'tr1':self.e[16],'tr2':self.e[17],'tr3':self.e[18],'tr4':self.e[19],'tr5':self.e[20]}
            # print(self.elec_dict)
            

            for e in self.electrode_labels:
                self.electrode_labels[e].setText(str(round(self.elec_dict[e],3)))      
            self.mutate_dataset_electrode()
       

    def mutate_dataset_electrode(self):
        for e in self.elec_dict:
            self.HasEnvironment.set_dataset("optimize.e."+e,self.elec_dict[e], broadcast=True, persist=True)
        self.HasEnvironment.set_dataset("optimize.flag.e",1, broadcast=True, persist=True)


    def update_parameters(self):
        self.parameter_dict = {}
        for p in self.parameter_spin:
            m = self.parameter_spin[p]
            text = m.text() or str(self.default_parameter[p])
            self.parameter_dict[p] = float(text)
        self.mutate_dataset_parameters()
        self.HasEnvironment.set_dataset("optimize.flag.p",1, broadcast=True, persist=True)
        # print("update_parameters has mutated dataset")

    def mutate_dataset_parameters(self):
        for p in self.parameter_dict:
            self.HasEnvironment.set_dataset(key="optimize.parameter."+p,value = self.parameter_dict[p], broadcast=True, persist=True)

        
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
                self.on_update_dataset_click()
            elif self.tabs.currentIndex() == 1:
                self.on_voltage_click()
            elif self.tabs.currentIndex() == 2:
                self.on_run_rigol_extraction_click()
        else:
            super().keyPressEvent(qKeyEvent)
                           

        

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




