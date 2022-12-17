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

class Electron:
    """
    Configuration adapted from the GUI_test Electron object.
    """
    
    ## Environment Config ##
    devices = ['core',
               'zotino0', # artiq DAC
               'ttl1', 
               'ttl2', # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
               'ttl8', # use this channel to trigger AOM, connect to switch near VCO and AOM
               'ttl9', # use this channel to trigger R&S for tickle pulse, connect to R&S
               'ttl10', # use this channel to trigger extraction pulse, connect to RIGOL external trigger
               "ttl12",
               "ttl13",
               "sampler0"
              ]

    number_of_datapoints = 5000 # See if this will run into issues
    arguments = {'update_cycle': NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1),
                 'number_of_datapoints': NumberValue(default=number_of_datapoints,unit=' ',scale=1,ndecimals=0,step=1), #how many data points on the plot, run experiment & pulse counting
                 'number_of_bins': NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1) #how many indices you have in time axis, pulse counting
                }
    
    datasets = [{'args': ['optimize.result.count_tot', [-100]*number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 in pusle counting
                {'args': ['optimize.result.count_PI',[-10]*number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 in shutter optimize
                {'args': ['optimize.result.count_ROI',[-2]*number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 with ROI in optimize
                {'args': ['optimize.result.countrate_ROI',[-2]*number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 with ROI in optimize without accumulating
                {'args': ['optimize.result.bin_times', [-1]*0], 
                 'kwargs': dict(broadcast=True)} #self.number_of_bins*self.number_of_datapoints,broadcast=True) # Small bins for histogram
               ]

    controlled_electrodes = ["tl2","tl3","tl4","tr2","tr3","tr4","trigger_level"]
    parameters = dict(pin_matching = {"bl1":21,"bl2":22,"bl3":11,"bl4":24,"bl5":25,"br1":6,"br2":17,"br3":13,"br4":15,"br5":14,"tl1":8,"tl2":10,"tl3":16,"tl4":12,"tl5":23,"tr1":18,"tr2":4,"tr3":3,"tr4":2,"tr5":1,"t0":9,"b0":20,"trigger_level":0},
                      gnd = [5,7,19,21,22,11,24,25,6,17,13,15,14,8,23,18,1,9,20], # gnd pins
                      np = 10, # number of experiment parameters
                      controlled_electrodes = controlled_electrodes,
                      controlled_multipoles = ["Grid","Ex","Ey","Ez","U2","U3","U4"],
                      #controlled_electrodes = ["tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5","t0","br1","br2","br3","br4","br5","bl1","bl2","bl3","bl4","bl5","b0","trigger_level"],
                      #controlled_multipoles = ["Grid","Ex","Ey","Ez","U1","U2","U3","U4","U5","U6"],
                      controlled_parameters = ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints","bins","update_cycle"],
                      old_c_file = False,
                      c_file_csv = '/home/electron/artiq/electron/cfile_etrap_gen2_6electrodes_U1U5_uncontrol.csv',
                      controlled_multipoles_dict = {"Grid":'Grid: (V)',"Ex":'Ex:', "Ey":'Ey:', "Ez":'Ez:', "U1":'U1:', "U2":'U2:', "U3":'U3:', "U4":'U4:', "U5":'U5:', "U6":'U6:'},
                      controlled_parameters_dict = {"t_load":'Load time (us):', "t_wait":'Wait time (ns):', "t_delay":'Delay time (ns):',"t_acquisition":'Acquisition time(ns):' , "pulse_counting_time":'Pulse counting time (ms):',"trigger_level":'Trigger level (V):',"number_of_repetitions":'# Repetitions:', "number_of_datapoints":'# Datapoints:', "bins":'# Bins:',"update_cycle":'# Update cycles:'},
                      controlled_electrodes_dict = ["tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5","t0","br1","br2","br3","br4","br5","bl1","bl2","bl3","bl4","bl5","b0","trigger_level"],
                      ne = int(len(controlled_electrodes)), # number of electrodes
                      run_mode = 0, # 0: pulse counting, 1: ROI counting (pulse 390), 2: histogram counting (pulse 390), 3: only outputting pulses and dacs
                      bins = 50, # bin number for histogram
                      update_cycle = 10, # how many datapoints per user_update_check (takes about 500 ms)
                    )

    ## Pulse Sequence ##
    def kernel_run_outputting(arg):
        self = arg
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
                    self.ttl8.on()
                    delay(t_load*us)
                    self.ttl8.off()
                    delay(1500*ns) # get rid of the photo diode fall time
                    self.ttl9.on()  
                    delay(t_wait*ns)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                    # delay(1*us)
                    delay(t_delay*ns)
    
    
    def kernel_run_ROI_counting(arg):
        self = arg
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
                            delay(t_delay*ns)
                            t_count = self.ttl2.gate_rising(t_acquisition*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    self.count_tot += count
                    countrate_tot += count
                    delay(1*us)
            self.mutate_dataset('optimize.result.count_ROI',self.index*self.update_cycle+k,self.count_tot)
            self.mutate_dataset('optimize.result.countrate_ROI',self.index*self.update_cycle+k,countrate_tot)
    
    ## GUI Config ##
    #[values (from list), x-coord (label), x-coord (entryBox), y-coord (first entry)]
    electrodes = {'bl': [0,0,1,4], 
                  'br': [1,4,5,4],
                  't0': None,
                  'tl': [3,0,1,10], 
                  'tr': [4,4,5,10],
                  'b0': None
                 }
    electrode_sec = {'t0': {'Range': (-10, 10),
                            'SingleStep': 0.1,
                            'Decimals': 4,
                            'Coordinates': [1,3,1,1],
                           }, 
                     'b0': {'Range': (-10, 10),
                            'SingleStep': 0.1,
                            'Decimals': 4,
                            'Coordinates': [7,3,1,1],
                            }
                    }
    rigol_ip = 113
    grid_multipole = {'values': [5.74825920e-05 ,5.96780638e-06 ,1.26753930e-05,-1.32588496e-04,-9.81277203e-05,2.83539744e-05,1.17764523e-05,4.47353980e-05,1.24182868e-05],
                      'voltage': 1
                     }


    ## Rigol Run Function ##
    def run(arg):
        self = arg
        inst = self.inst
        inst.write("OUTPUT2 OFF")
        inst.write("OUTPUT1 OFF")   
        # hardcode sampling rate for ejection pulse, since only need the first few hundred ns
        waveform_ej = np.zeros(int(self.period_ej/self.sampling_time))
        waveform_ej[:] = -1
        waveform_ej[np.int(self.pulse_delay_ej/self.sampling_time):np.int((self.pulse_delay_ej+self.pulse_width_ej)/self.sampling_time)] = 1
        ej_str = ",".join(map(str,waveform_ej))
        
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


class ThreeLayer:
    """
    Configuration adapted from the GUI_3Layer.
    """
    
    ## Environment Config ##
    devices = ['core',
               'zotino0', # artiq DAC
               'ttl1', 
               'ttl2', # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
               'ttl8', # use this channel to trigger AOM, connect to switch near VCO and AOM
               'ttl9', # use this channel to trigger R&S for tickle pulse, connect to R&S
               'ttl10', # use this channel to trigger extraction pulse, connect to RIGOL external trigger
               'ttl11',
               "ttl12",
               "ttl13",
               'ttl16',
               "sampler0"
              ]

    number_of_datapoints = 5000 # See if this will run into issues
    arguments = {'update_cycle': NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1),
                 'number_of_datapoints': NumberValue(default=number_of_datapoints,unit=' ',scale=1,ndecimals=0,step=1), #how many data points on the plot, run experiment & pulse counting
                 'number_of_bins': NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1) #how many indices you have in time axis, pulse counting
                }
    
    datasets = [{'args': ['optimize.result.count_tot', [-100]*number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 in pusle counting
                {'args': ['optimize.result.count_ROI',[-2]*number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 with ROI in optimize
                {'args': ['optimize.result.countrate_ROI',[-2]*number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 with ROI in optimize without accumulating
                {'args': ['optimize.result.bin_times', [-1]*0], 
                 'kwargs': dict(broadcast=True)}, #self.number_of_bins*self.number_of_datapoints,broadcast=True) # Small bins for histogram
                {'args': ['optimize.result.lifetime.counts',[-50]*12],
                 'kwargs': dict(broadcast=True)},
                {'args': ['optimize.result.lifetime.wait_times',[-50]*12],
                 'kwargs': dict(broadcast=True)}
               ]

    controlled_electrodes = ["tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5","tg","br1","br2","br3","br4","br5","bl1","bl2","bl3","bl4","bl5","trigger_level"]
    parameters = dict(pin_matching = {"bl1":5,"bl2":11,"bl3":25,"bl4":24,"bl5":23,"br1":6,"br2":20,"br3":8,"br4":22,"br5":12,"tl1":2,"tl2":1,"tl3":10,"tl4":15,"tl5":3,"tr1":18,"tr2":19,"tr3":9,"tr4":17,"tr5":4,"tg":14,"trigger_level":0},
                      gnd = [7,13,16,21], # gnd pins
                      np = 10, # number of experiment parameters
                      use_amplifier = True,
                      max_voltage = 25,
                      controlled_electrodes = controlled_electrodes,
                      controlled_multipoles = ["Grid","Ex","Ey","Ez","U1","U2","U3","U4","U5"],
                      #controlled_electrodes = ["tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5","t0","br1","br2","br3","br4","br5","bl1","bl2","bl3","bl4","bl5","b0","trigger_level"],
                      #controlled_multipoles = ["Grid","Ex","Ey","Ez","U1","U2","U3","U4","U5","U6"],
                      controlled_parameters = ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints","bins","update_cycle"],
                      old_c_file = True,
                      c_file_csv = '/home/electron/artiq/electron/cfile_etrap_gen2_6electrodes_U1U5_uncontrol.csv',
                      controlled_multipoles_dict = {"Grid":'Grid: (V)',"Ex":'Ex:', "Ey":'Ey:', "Ez":'Ez:', "U1":'U1:', "U2":'U2:', "U3":'U3:', "U4":'U4:', "U5":'U5:',"U6":'U6:'},
                      controlled_parameters_dict = {"t_load":'Load time (us):', "t_wait":'Wait time (us):', "t_delay":'Delay time (ns):',"t_acquisition":'Acquisition time(ns):' , "pulse_counting_time":'Pulse counting time (ms):',"trigger_level":'Trigger level (V):',"number_of_repetitions":'# Repetitions:', "number_of_datapoints":'# Datapoints:', "bins":'# Bins:',"update_cycle":'# Update cycles:'},
                      controlled_electrodes_dict = ["tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5","tg","br1","br2","br3","br4","br5","bl1","bl2","bl3","bl4","bl5","trigger_level"],
                      ne = int(len(controlled_electrodes)), # number of electrodes
                      run_mode = 0, # 0: pulse counting, 1: ROI counting (pulse 390), 2: histogram counting (pulse 390), 3: only outputting pulses and dacs
                      bins = 50, # bin number for histogram
                      update_cycle = 10, # how many datapoints per user_update_check (takes about 500 ms)
                    )

    ## Pulse Sequence ##
    def kernel_run_outputting(arg):
        self = arg
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
                    self.ttl16.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl16.off()
                        # delay(1500*ns) # get rid of the photo diode fall time
                        self.ttl9.on()  
                    delay(t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                    # delay(1*us)
                    delay(t_delay*ns)
    
    
    def kernel_run_ROI_counting(arg):
        self = arg
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
                    self.ttl16.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl16.off()
                        self.ttl9.on()
                    delay(t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                        self.ttl11.pulse(2*us)
                        with sequential:
                            delay(200*ns)
                            self.ttl12.pulse(2*us)
                        with sequential:
                            delay(t_delay*ns)
                            t_count = self.ttl2.gate_rising(t_acquisition*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    self.count_tot += count
                    countrate_tot += count
                    delay(10*us)
            self.mutate_dataset('optimize.result.count_ROI',self.index*self.update_cycle+k,self.count_tot)
            self.mutate_dataset('optimize.result.countrate_ROI',self.index*self.update_cycle+k,countrate_tot)
    
    ## GUI Config for setup_UI ##
    #[values (from list), x-coord (label), x-coord (entryBox), y-coord (first entry)]
    electrodes = {'bl': [0,0,1,4], 
                  'br': [1,4,5,4],
                  'tg': None,
                  'tl': [3,0,1,10], 
                  'tr': [4,4,5,10]
                 }
    electrode_sec = {'tg': {'Range': (-10, 10),
                            'SingleStep': 0.1,
                            'Decimals': 4,
                            'Coordinates': [1,3,1,1],
                           }
                    }
    rigol_ip = 113
    grid_multipole = {'filename': '/home/electron/artiq-nix/electron/Cfile_3layer.txt',
                      'values': [0.0203082,0.00042961,-0.00124763,-0.047735,-0.00441363,0.00081879,0.00012903,-0.03539802,-0.00083521],
                      'voltage': 150
                     }


    ## Rigol Run Function ##
    def run(arg):
        self = arg
        inst = self.inst
        inst.write("OUTPUT2 OFF")
        inst.write("OUTPUT1 OFF")   
        # hardcode sampling rate for ejection pulse, since only need the first few hundred ns
        
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
        # inst.write("OUTPUT2 ON")
        return