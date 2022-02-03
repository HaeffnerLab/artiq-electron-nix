from artiq.experiment import *
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPlainTextEdit
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
import time
import os
import sys





class Electron(HasEnvironment):
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
        for i in ["bl","br","tl","tr"]:
            for j in ["1","2","3","4","5"]:
                if i+j == 'br4' or 'tr4':
                    continue
                else:
                    self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True)
        self.set_dataset(key="optimize.e.btr4", value=np.float32(0), broadcast=True)
        self.set_dataset(key="optimize.e.t0", value=np.float32(0), broadcast=True)
        self.set_dataset(key="optimize.e.b0", value=np.float32(0), broadcast=True)
        
        # flags: indicating changes from GUI, 1 = there is change that needs to be implemented
        self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True) # electrode voltages
        self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True) # experiment parameters

        # parameters: t_load(us),t_wait(us),t_delay(ns), t_acquisition(ns),pulse_counting_time(ms), trigger_level (V), # repetitions, # datapoints
        self.set_dataset(key="optimize.parameter.t_load", value = np.int(100), broadcast=True) # t_load(us)
        self.set_dataset(key="optimize.parameter.t_wait", value = np.int(100), broadcast=True) # t_wait(us)
        self.set_dataset(key="optimize.parameter.t_delay", value = np.int(600), broadcast=True) # t_delay(ns)
        self.set_dataset(key="optimize.parameter.t_acquisition", value = np.int(100), broadcast=True) # t_acquisition(ns)
        self.set_dataset(key="optimize.parameter.pulse_counting_time", value = np.int(500), broadcast=True) # pulse_counting_time(ms)
        self.set_dataset(key="optimize.parameter.trigger_level", value = 0.3, broadcast=True) # trigger level (V)
        self.set_dataset(key="optimize.parameter.number_of_repetitions", value = np.int(1000), broadcast=True) # number of repetitions
        self.set_dataset(key="optimize.parameter.number_of_datapoints", value = np.int(5000), broadcast=True) # number of datapoints

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

    def get_dac_vs(self):
        dac_vs = []
        for i in ["bl","br","tl","tr"]:
            for j in ["1","2","3","4","5"]:
                if i+j == 'br4' or 'tr4':
                    continue
                else:
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
        load_dac = False
        number_of_datapoints = np.int(self.parameter_list[7])

        for i in range(number_of_datapoints):
            flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
            flag_parameter = np.int32(self.get_dataset(key="optimize.flag.p"))
            if flag_dac == 1:
                # load dac voltages
                dac_vs = self.get_dac_vs()
                load_dac = True
                self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True)
            if flag_parameter == 1:
                # t_load, t_wait, t_delay, t_acquisition, number_of_repetitions, number_of_datapoints = self.get_parameter_list()
                parameter_list = self.get_parameter_list()
                self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True)
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
    def pulse_counting(self):
        detection_time = np.int32(self.parameter_list[4])
        print("detectionn_time",detection_time)
        self.core.reset()
        self.ttl8.on() # AOM
        # with parallel:
        for j in range(self.number_of_datapoints):
            self.core.break_realtime()
            with parallel:
                self.ttl10.pulse(2*us) # extraction pulse
                t_count = self.ttl2.gate_rising(detection_time*ms)
            self.mutate_dataset('optimize.result.count_tot',j,self.ttl2.count(t_count)/(detection_time*ms))
         

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
# Control the rigol to give out extraction pulse

class rigol():
    def __init__(self):
        # self.sampling_time = sampling_time # 
        self.offset_ej = 0
        self.amplitude_ej = 20
        self.inst = vxi11.Instrument('TCPIP0::192.168.169.113::INSTR')
        # self.inst2 = vxi11.Instrument('TCPIP0::192.168.169.117::INSTR')
        # print(self.inst.ask('*IDN?'))

    def run(self, pulse_width_ej, pulse_delay_ej):
        self.pulse_width_ej = pulse_width_ej
        self.pulse_delay_ej = pulse_delay_ej
        inst = self.inst
        inst.write("OUTPUT2 OFF")
        inst.write("OUTPUT1 OFF")	
        # hardcode sampling rate for ejection pulse, since only need the first few hundred ns
        period_ej = 1000.E-9
        waveform_ej = np.zeros(500)
        waveform_ej[:] = -1
        waveform_ej[np.int(self.pulse_delay_ej/2E-9):np.int((self.pulse_delay_ej+self.pulse_width_ej)/2E-9)] = 1
        ej_str = ",".join(map(str,waveform_ej))
        # Channel 2
        inst.write(":OUTPut2:LOAD INFinity")
        inst.write("SOURCE2:PERIOD {:.9f}".format(period_ej))
        # print(inst.ask("SOURCE2:PERIOD?"))
        inst.write("SOURCE2:VOLTage:UNIT VPP")
        inst.write("SOURCE2:VOLTage {:.3f}".format(self.amplitude_ej))
        inst.write("SOURCE2:VOLTage:OFFSet {:.3f}".format(self.offset_ej))
        inst.write("SOURCE2:TRACE:DATA VOLATILE,"+ ej_str)
        inst.write("SOURce2:BURSt ON")
        # inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
        inst.write("SOURce2:BURSt:MODE TRIGgered")
        inst.write("SOURce2:BURSt:NCYCles 1")
        # inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
        inst.write("SOURCe2:BURSt:TRIGger:SOURce EXTernal")
        inst.write("SOURce2:BURSt:TRIGger:SLOPe POSitive")
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

    def run_rigol_extraction(self):
        self.rigol113 =  rigol()
        # parameters for the Rigol waveforms
        pulse_width_ej = 20.E-9
        pulse_delay_ej = 2.E-9
        self.rigol113.run(pulse_width_ej, pulse_delay_ej)

    def setup_UI(self):
  
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tabs.resize(300, 150)
  
        # Add tabs
        self.tabs.addTab(self.tab1, "ELECTRODES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        # self.tabs.addTab(self.tab2, "MULTIPOLES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        # self.tabs.addTab(self.tab3, "PARAMETERS")
        self.tabs.addTab(self.tab4, "Main Experiment") # This tab could mutate dac_voltage, parameters, flags dataset and run_self_updated
          
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
                if self.ELECTRODES[el_values][i] == 'tr4:':
                    label_gap = QLabel('', self)
                    grid1.addWidget(label_gap,ycoord-i,xcoord_entry,1,1)
                elif self.ELECTRODES[el_values][i] == 'br4:':
                    continue
                else:
                    spin = QtWidgets.QDoubleSpinBox(self)
                    spin.setRange(-10,10)
                    spin.setSingleStep(0.1)
                    grid1.addWidget(spin,ycoord-i,xcoord_entry,1,1)
                    self.electrodes.append(spin)
                    label = QLabel('       '+self.ELECTRODES[el_values][i], self)
                    grid1.addWidget(label,ycoord-i,xcoord_label,1,1)
        
        # append btr4 to self.electrodes  
        spin_btr4 = QtWidgets.QDoubleSpinBox(self)
        spin_btr4.setRange(-10,10)
        spin_btr4.setSingleStep(0.1)
        grid1.addWidget(spin_btr4,ycoord-3,xcoord_entry,1,1)
        label = QLabel('       '+'btr4:', self)
        grid1.addWidget(label,ycoord-3,xcoord_label,1,1)
        self.electrodes.append(spin_btr4)
        
        #spacing
        label_gap = QLabel('', self)
        grid1.addWidget(label_gap,5,1,1,1)
        
        #t0
        spin_t0 = QtWidgets.QDoubleSpinBox(self)
        spin_t0.setRange(-10,10)
        spin_t0.setSingleStep(0.1)
        grid1.addWidget(spin_t0,1,3,1,1)
        self.electrodes.append(spin_t0)
        label_t0 = QLabel('       '+self.ELECTRODES[2][0], self)
        grid1.addWidget(label_t0,1,2)

        #b0
        spin_b0 = QtWidgets.QDoubleSpinBox(self)
        spin_b0.setRange(-10,10)
        spin_b0.setSingleStep(0.1)
        grid1.addWidget(spin_b0,7,3,1,1)
        self.electrodes.append(spin_b0)
        label_b0 = QLabel('       '+self.ELECTRODES[5][0], self)
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
        self.default = [100,100,600,100,500,0.3,1000,1000] # default values
        PARAMETERS1 = ['Load time (us):', 'Wait time (us):', 'Delay time (ns):','Acquisition time(ns):' ]
        DEFAULTS1 = self.default[0:4] # default values
        for i in range(len(PARAMETERS1)):  
            spin = QtWidgets.QSpinBox(self)
            spin.setRange(0,10000000)
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
        DEFAULTS2 = self.default[4:] # default values
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

        #electrode grid
        for e in [self.tl_electrodes0, self.tr_electrodes0, self.bl_electrodes0, self.br_electrodes0]:            
            
            el_values = e[0]
            xcoord_label = e[1]
            xcoord_entry = e[2]
            ycoord = e[3]
            
            for i in range(len(self.ELECTRODES[el_values])):
                if self.ELECTRODES[el_values][i] == 'tr4:':
                    label_gap = QLabel('', self)
                    grid4.addWidget(label_gap,ycoord-i,xcoord_label,1,1)
                elif self.ELECTRODES[el_values][i] == 'br4:':
                    continue
                else:     
                    label = QLabel('       '+ self.ELECTRODES[el_values][i], self)
                    grid4.addWidget(label,ycoord-i,xcoord_label, 1,1)
                    label0 = QLabel('0.00', self)
                    self.all_labels.append(label0)
                    label0.setStyleSheet("background-color:lightgreen;  border: 1px solid black;")
                    grid4.addWidget(label0,ycoord-i,xcoord_entry,1,1)
          
        
        # append btr4 to self.electrodes
        label = QLabel('       '+ 'btr4:', self)
        grid4.addWidget(label,ycoord-3,xcoord_label, 1,1)
        self.label0_btr4 = QLabel('0.00', self)
        self.label0_btr4.setStyleSheet("background-color:lightgreen;  border: 1px solid black;")
        grid4.addWidget(self.label0_btr4,ycoord-3,xcoord_entry,1,1)  

        #spacing
        label_gap = QLabel('', self)
        grid4.addWidget(label_gap,5,1,1,1)


        #t0
        label_t0 = QLabel('       '+self.ELECTRODES[2][0], self)
        grid4.addWidget(label_t0,1,2,1,1)
        self.label0_t0 = QLabel('0.00', self)
        self.label0_t0.setStyleSheet("background-color:lightgreen;  border: 1px solid black;")
        grid4.addWidget(self.label0_t0,1,3,1,1)

        
        #b0
        label_b0 = QLabel('       '+self.ELECTRODES[5][0], self)
        grid4.addWidget(label_b0,7,2,1,1)
        self.label0_b0 = QLabel('0.00', self)
        self.label0_b0.setStyleSheet("background-color:lightgreen;  border: 1px solid black;")
        grid4.addWidget(self.label0_b0,7,3,1,1)    

        #spacing  
        label_gap = QLabel('          ', self)
        grid4.addWidget(label_gap,1,6,1,1)

        #spacing  
        label_gap = QLabel('          ', self)
        grid4.addWidget(label_gap,11,6,2,1)
    
        #create multipole text entry boxes
        MULTIPOLES = ['Ex:', 'Ey:', 'Ez:', 'U1:', 'U2:', 'U3:', 'U4:', 'U5:', 'U6:']
        self.multipoles = []
        for i in range(len(MULTIPOLES)):  
            spin = QtWidgets.QDoubleSpinBox(self)
            spin.setRange(-10,10)
            spin.setSingleStep(0.01)
            grid4.addWidget(spin,i,8,1,1)
            self.multipoles.append(spin)
            label = QLabel(MULTIPOLES[i], self)
            grid4.addWidget(label,i,7,1,1)  

        
        # add extraction button
        v_button = QPushButton('Initialize Rigol', self)
        v_button.clicked.connect(self.run_rigol_extraction)
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
        t_button.clicked.connect(self.on_terminate_click_main)
        grid4.addWidget(t_button, 14+2, 8)


        grid4.setRowStretch(4, 1)
        self.tab4.setLayout(grid4)

       
        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)        
        return

    def update_set_values(self):
        self.update_multipoles()
        self.update_parameters()


    def update_multipoles(self):
        
        # Create multiple list of floats
        self.mul_list = []
        for m in self.multipoles:
            text = m.text() or "0"
            self.mul_list.append(float(text))
        
        # Calculate and print electrode values
        try:
            self.m=np.array([self.mul_list])
            self.e=np.matmul(self.m, self.C_Matrix_np)
        except:
            f = open('/home/electron/artiq/electron/Cfile_v2.txt','r')
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
            self.m=np.array([self.mul_list])
            #print(shape(self.m))
            grid_multipole = np.array([0.00862239,0.00089517,0.0019013,-0.01988827,-0.01471916,0.0042531,0.00176647,0.00671031,0.00186274])
            
            self.m=self.m-grid_multipole
            self.e=np.matmul(self.m, self.C_Matrix_np)
            
        for i in range(len(self.e[0])):
            if self.e[0][i]>=10:
                print(f'warning: voltage {round(self.e[0][i],3)}  exceeds limit')
                self.e[0][i]=10
            elif self.e[0][i]<=-10:
                print(f'warning: voltage {round(self.e[0][i],3)} exceeds limit')
                self.e[0][i]=-10

        self.e = self.e[0].tolist()
        #self.e.append(self.e.pop(10))      
        for i in range(len(self.e)):
            self.e[i]=round(self.e[i],3)

        # print('before changing order', self.e)

        #assuming electrode order is [tl1,...,tl5,bl1,...,bl5,tr1,...,tr5,br1,...,br5,t0,b0]
        #new order: [ bl1,...,bl5,br1,...,br5 (except for br4),btr4, b0(grid), t0,tl1,...,tl5,tr1,..,tr5 (except for tr4)]

        self.elec_dict={'bl1':self.e[0],'bl2':self.e[1],'bl3':self.e[2],'bl4':self.e[3],'bl5':self.e[4],'br1':self.e[5],'br2':self.e[6],'br3':self.e[7],'br5':self.e[8],'btr4':self.e[9],'b0':0.0,'t0':self.e[11],'tl1':self.e[12],'tl2':self.e[13],'tl3':self.e[14],'tl4':self.e[15],'tl5':self.e[16],'tr1':self.e[17],'tr2':self.e[18],'tr3':self.e[19],'tr5':self.e[20]}
        print(self.elec_dict)
 
        for i in range(5):
            self.all_labels[i].setText(str(round(self.elec_dict['bl'+f'{1+i}'],3)))
            self.all_labels[9+i].setText(str(round(self.elec_dict['tl'+f'{1+i}'],3)))
            
        for i in [0,1,2]:
            self.all_labels[5+i].setText(str(round(self.elec_dict['br'+f'{1+i}'],3)))
            self.all_labels[14+i].setText(str(round(self.elec_dict['tr'+f'{1+i}'],3)))

        self.all_labels[5+3].setText(str(round(self.elec_dict['br'+f'{1+4}'],3)))
        self.all_labels[14+3].setText(str(round(self.elec_dict['tr'+f'{1+4}'],3)))
        self.label0_btr4.setText(str(round(self.elec_dict['btr4'],3)))
        self.label0_t0.setText(str(round(self.elec_dict['t0'],3)))
        self.label0_b0.setText(str(round(self.elec_dict['b0'],3)))

        self.e=[]
        string = 'bl'
        for i in range(5):
            self.e.append(self.elec_dict[string+f'{1+i}'])
        string = 'br'
        for i in range(3):
            self.e.append(self.elec_dict[string+f'{1+i}'])
        self.e.append(self.elec_dict[string+f'{5}'])
        string = 'tl'
        for i in range(5):
            self.e.append(self.elec_dict[string+f'{1+i}'])
        string = 'tr'
        for i in range(3):
            self.e.append(self.elec_dict[string+f'{1+i}'])
        self.e.append(self.elec_dict[string+f'{5}'])
        # for string in ['bl','br','tl','tr']:
        #     for i in range(5):
        #         if string+str(i+1) == 'br4' or 'tr4':
        #             continue
                
        #         else:
        #             self.e.append(self.elec_dict[string+f'{1+i}'])     
        self.e.append(self.elec_dict['btr4'])
        self.e.append(self.elec_dict['t0'])
        self.e.append(self.elec_dict['b0'])
        print(self.e)
        self.mutate_dataset_electrode()
        # for c in range(len(self.e)):
            # self.mutate_dataset("dac_voltages", c, self.e[c])
        self.HasEnvironment.set_dataset("optimize.flag.e",1, broadcast=True)
        print("update_multipoles has mutated dataset")

    def mutate_dataset_electrode(self):
        for string in ['bl','br','tl','tr']:
            for i in range(5):
                if string+str(i+1) == 'br4' or 'tr4':
                    continue
                else:
                    self.HasEnvironment.set_dataset("optimize.e."+string+str(1+i),self.elec_dict[string+f'{1+i}'], broadcast=True)
        self.HasEnvironment.set_dataset("optimize.e.btr4",self.elec_dict['btr4'], broadcast=True)
        self.HasEnvironment.set_dataset("optimize.e.t0",self.elec_dict['t0'], broadcast=True)
        self.HasEnvironment.set_dataset("optimize.e.b0",self.elec_dict['b0'], broadcast=True)

    def mutate_dataset_parameters(self):
        p = ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints"]
        for i in range(len(p)):
            self.HasEnvironment.set_dataset(key="optimize.parameter."+p[i],value = self.parameter_dict[p[i]], broadcast=True)


    def update_parameters(self):
        self.p = []
        for i in range(len(self.parameter_list)):
            m = self.parameter_list[i]
            text = m.text() or str(self.default[i])
            self.p.append(float(text))
        self.parameter_dict={"t_load":self.p[0],"t_wait":self.p[1],"t_delay":self.p[2],"t_acquisition":self.p[3],"pulse_counting_time":self.p[4],"trigger_level":self.p[5],"number_of_repetitions":self.p[6],"number_of_datapoints":self.p[7]}
        print(self.p)
        self.mutate_dataset_parameters()
        self.HasEnvironment.set_dataset("optimize.flag.p",1, broadcast=True)
        print("update_parameters has mutated dataset")


    def long_run_task(self):
        self.update_multipoles()
        self.update_parameters()
        self.run_rigol_extraction()
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
        # self.thread.finished.connect(
        #     lambda: self.stepLabel.setText("Long-Running Step: 0")
        #     )


    def on_terminate_click_main(self):
        self.HasEnvironment.scheduler.pause()
        # self.HasEnvironment.core.reset()
        return

    def on_pulse_counting_click(self):

        self.HasEnvironment.get_parameter_list()
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
            # lambda: self.lm_button.setEnabled(True),
            # lambda: self.pc_button.setEnabled(True)
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
        print(qKeyEvent.key())
        if qKeyEvent.key() == QtCore.Qt.Key_Return:
            if self.tabs.currentIndex() == 0:
                self.on_voltage_click()
            # elif self.tabs.currentIndex() == 1:
            #     self.on_multipoles_click()
            elif self.tabs.currentIndex() == 1:
                self.update_multipoles()
                self.update_parameters()
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
                r = 0
                g = 1
            elif val<0:
                r = 1
                g = 0
            elif val==0:
                r = 0
                g = 0
            col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),int(255*g),0)
            entry.setStyleSheet(f'QWidget {{background-color: {col};}}')


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


class Electron_GUI(Electron, EnvExperiment):#, object):
    def build(self):
        Electron.build(self)

    def prepare(self):
        Electron.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        # self.launch_GUI()
        print("Hello World")




