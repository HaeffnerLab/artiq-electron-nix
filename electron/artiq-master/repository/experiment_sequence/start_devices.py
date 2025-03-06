from artiq.experiment import *
import Constants
import Variables
import Instruments
from Instruments import *


class Devices(EnvExperiment):

    def build(self):
        self.setattr_device('core')

        Constants.Constants.build_rigol(self)
        # Variables.Variables.build_rigol(self)
    
    def run(self):
        self.core.reset()
        self.start_rigol()
        self.start_rs()

    def start_rigol(self):
        pulse_width_ej = self.pulse_width_ej*1e-9
        pulse_delay_ej = self.pulse_delay_ej*1e-9
        offset_ej = self.offset_ej
        amplitude_ej = self.amplitude_ej
        phase_ej = self.phase_ej
        period_ej = self.period_ej*1e-9
        sampling_time_ej = self.sampling_time_ej*1e-9
        self.rigol113 =  rigol(115,pulse_width_ej,pulse_delay_ej,offset_ej,amplitude_ej,phase_ej,period_ej,sampling_time_ej)
        self.rigol113.run()
        
    
    def start_rs(self):
        return

    











