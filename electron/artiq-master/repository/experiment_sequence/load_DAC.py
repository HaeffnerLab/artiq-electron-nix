from artiq.experiment import *
import Constants
import Variables
import DAC_config
import pandas as pd
import numpy as np


class DAC(EnvExperiment):

    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0')

        # Variables.Variables.build_load_DAC(self)
        Constants.Constants.build_DAC(self)
    
    def run(self):
        self.core.reset()
        self.load_DAC()

    def load_DAC(self):
        DAC_config.DAC_config.loadDACoffset(self)
        dac_pins, dac_pins_voltages = self.get_dac_vs()
        self.kernel_load_dac(dac_pins, dac_pins_voltages)
    
    @ kernel
    def kernel_load_dac(self,dac_pins, dac_pins_voltages):
        self.core.reset()
        self.core.break_realtime()
        self.zotino0.init()
        for i in range(len(dac_pins)):
            delay(500*us)
            m = self.dac_calibration_fit[1][dac_pins[i]]
            b = self.dac_calibration_fit[0][dac_pins[i]]
            self.zotino0.write_dac(dac_pins[i],(dac_pins_voltages[i]+b)/m - self.dac_manual_offset[dac_pins[i]])
        for pin in self.gnd:
            delay(500*us)
            self.zotino0.write_dac(pin,0.0)
            m = self.dac_calibration_fit[1][pin]
            b = self.dac_calibration_fit[0][pin]
            self.zotino0.write_offset(pin,-b/m)
        self.zotino0.load()
        # print("Loaded dac voltages")

    def get_dac_vs(self):
        dac_vs = {}
        dac_pins = []
        dac_pins_voltages = []

        if self.multipole_control:
            dac_vs = self.update_multipoles()
            # dac_vs["DC0"] += self.DC0_bias # with DC0 bias voltage
            # print(dac_vs)
        else:
            for e in self.pin_matching:
                dac_vs[e] = getattr(self,e)
        
        for e in dac_vs:
            dac_pins.append(self.pin_matching[e])
            dac_pins_voltages.append(dac_vs[e])
        
        self.set_DC_dataset(dac_vs)
        return dac_pins, dac_pins_voltages
    
    @rpc(flags={"async"})
    def set_DC_dataset(self,dac_vs):
        for e in dac_vs:
            self.set_dataset(key="main_sequence.e."+e, value=dac_vs[e], broadcast=True)
    
    @rpc(flags={"async"})
    def set_multipole_dataset(self,dac_ms):
        for m in dac_ms:
            self.set_dataset(key="main_sequence.multipole."+m, value=dac_ms[m], broadcast=True)

    def update_multipoles(self):
        
        # Create multiple list of floats
        dac_ms = {}
        for m in self.controlled_multipoles:
            dac_ms[m] = getattr(self,m)
        self.set_multipole_dataset(dac_ms)
        
        if not self.compensate_grid:
            df = pd.read_csv(self.c_file_csv,index_col = 0)
            voltages = pd.Series(np.zeros(len(self.pin_matching.keys())-len(self.excess_e)),index = df.index.values)
            # print("Multipoles:",dac_ms)
            for m in self.controlled_multipoles:   
                voltages += df[m] * dac_ms[m]
            dac_vs = voltages.to_dict()
            for e in self.excess_e:
                dac_vs[e] = getattr(self,e)
            # for e in dac_vs:
            #     dac_vs[e] = round(dac_vs[e],3)    
            # print(dac_vs)
            return dac_vs

        else:
            df = pd.read_csv(self.c_file_csv,index_col = 0)
            voltages = pd.Series(np.zeros(len(self.pin_matching.keys())-len(self.excess_e)),index = df.index.values)
            corrected_m = {}
            for m in self.controlled_multipoles:   
                corrected_m[m] = dac_ms[m] - self.grid_m[m]*self.V_grid
                voltages += df[m] * corrected_m[m]
            dac_vs = voltages.to_dict()
            for e in self.excess_e:
                dac_vs[e] = getattr(self,e)
            
            # print("Corrected Multipoles:",corrected_m)
            # print(dac_vs)
            return dac_vs
        







