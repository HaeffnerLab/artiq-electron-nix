from artiq.experiment import *
import DAC_config

class Constants(EnvExperiment):
    def build(self):

        ### general
        self.setattr_argument("n_repetitions", NumberValue(default = 1000, ndecimals = 1, step = 1), group = "General", tooltip = "[ ] | Number of repeated experiment cycles") 
        self.setattr_argument("t_manual_delay", NumberValue(default = 10, ndecimals = 2, step = .01), group = "General", tooltip = "[us] | manual delay between different experiment cycles to avoid RTIO underflow errors")

        ### pulse counting
        self.setattr_argument("t_pulse_counting", NumberValue(default = 500, ndecimals = 1, step = 1), group = "Pulse counting", tooltip = "[ms] | Bin width for pulse counting mode")
        self.setattr_argument("n_datapoints", NumberValue(default = 10000, ndecimals = 1, step = 1), group = "Pulse counting", tooltip = "[ ] | Number of datapoints for pulse counting")

        ### loading
        self.setattr_argument("t_load", NumberValue(default = 200, ndecimals = 0, step = 1), group = "Loading", tooltip = "[us] | loading time for 390 on")


        ### wait
        self.setattr_argument("t_wait", NumberValue(default = 10, ndecimals = 2, step = .01), group = "Wait and tickle", tooltip = "[us] | wait time between the 390 off and extraction on")


        ### tickle


        ### Detection
        self.setattr_argument("t_delay", NumberValue(default = 450, ndecimals = 0, step = 1), group = "Detection", tooltip = "[ns] | delay time for the ttl input after the extraction trigger ttl")
        self.setattr_argument("t_acquisition", NumberValue(default = 600, ndecimals = 0, step = 1), group = "Detection", tooltip = "[ns] | time window for the ttl input data acquisition")
        self.setattr_argument("trigger_level", NumberValue(default = 0.06, ndecimals = 3, step = .001, unit = 'V'), group = "Detection", tooltip = "[V] | threshold voltage for threshold detector")
        
        
        
    def build_DAC(self):
        DAC_config.DAC_config.build(self)
        ### DC
        self.setattr_argument("multipole_control",BooleanValue(default = True))
        self.setattr_argument("compensate_grid",BooleanValue(default = True))
        self.setattr_argument("V_grid", NumberValue(default = 0., ndecimals = 3, step = .001), group = "DC.grid", tooltip = "V")
        for e in self.pin_matching:
            self.setattr_argument(e, NumberValue(default = 0., ndecimals = 3, step = .001, unit = 'V'), group = "DC.electrodes", tooltip = "[V] | electrode voltage")

        for m in self.controlled_multipoles:
            self.setattr_argument(m, NumberValue(default = 0., ndecimals = 3, step = .001), group = "DC.multipoles", tooltip = "V/mm")
    
    def build_rigol(self):
        ### rigol extraction
        # rigol_PARAMETERS = ['Ejection pulse width (ns):', 'Pulse delay (ns):','Offset (V)(= -Amplitude/2):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):'] # make it to be less confusing
        # rigol_DEFAULTS = [100, 100, -5, 10, 0,1000,2]
        self.setattr_argument("pulse_width_ej", NumberValue(default = 100, ndecimals = 0, step = 1), group = "Rigol", tooltip = "[ns] | ejectrion pulse width")
        self.setattr_argument("pulse_delay_ej", NumberValue(default = 100, ndecimals = 0, step = 1), group = "Rigol", tooltip = "[ns] | ejectrion pulse delay")
        self.setattr_argument("offset_ej", NumberValue(default = -5, ndecimals = 1, step = .1), group = "Rigol", tooltip = "[V] | (-Amplitude/2)")
        self.setattr_argument("amplitude_ej", NumberValue(default = 10, ndecimals = 1, step = .1), group = "Rigol", tooltip = "[V] | ejectrion pulse amplitude")
        self.setattr_argument("phase_ej", NumberValue(default = 0, ndecimals = 0, step = 1), group = "Rigol", tooltip = "[ ] | ejectrion pulse phase")
        self.setattr_argument("period_ej", NumberValue(default = 1000, ndecimals = 0, step = 1), group = "Rigol", tooltip = "[ns] | ejectrion pulse burst period")
        self.setattr_argument("sampling_time_ej", NumberValue(default = 2, ndecimals = 0, step = 1), group = "Rigol", tooltip = "[ns] | ejectrion pulse sampling time")



