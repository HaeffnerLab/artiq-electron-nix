from artiq.experiment import *
import Constants
import Variables


class pulse_sequence(EnvExperiment):

    def build(self):
        self.setattr_device('core')
        # self.setattr_device('zotino0')

        self.setattr_device('ttl_MCP_in') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        self.setattr_device('ttl_Extraction') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device("ttl_TimeTagger") # time tagger start click
        self.setattr_device("ttl_390") # use this channel to trigger AOM, connect to switch near VCO and AOM
        self.setattr_device('ttl_Tickle') # use this channel to trigger R&S for tickle pulse, connect to R&S
        self.setattr_device("ttl20") # use this ttl to trigger the RF switch to pulse the trap drive RF during extraction

        self.setattr_device('scheduler') # scheduler used
        # self.setattr_device("sampler0")

        
        # Variables.Variables.build_pulse_sequence(self)
        Constants.Constants.build(self)

    @kernel
    def run(self):
        self.core.reset()
        self.kernel_run_outputting()
    
    def prepare(self):
        self.set_dataset('main_sequence.result.countrate_CW',[-100]*int(self.n_datapoints),broadcast=True) # Number of pulses sent to ttl_MCP_in in pusle counting
    

    @kernel
    def kernel_run_outputting(self):
        
        t_load = self.t_load
        t_wait = self.t_wait
        number_of_repetitions = int(self.n_repetitions)
        t_manual_delay = self.t_manual_delay
               
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
                        delay(560*ns) # 570
                        self.ttl20.pulse(2*us)

                delay(t_manual_delay*us)
        
    @kernel
    def kernel_run_ROI_counting(self):
        t_load = self.t_load
        t_wait = self.t_wait
        number_of_repetitions = int(self.n_repetitions)
        t_delay = self.t_delay
        t_acquisition = self.t_acquisition
        t_manual_delay = self.t_manual_delay
                   
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
                        delay(t_delay*ns)
                        t_count = self.ttl_MCP_in.gate_rising(t_acquisition*ns)
                count = self.ttl_MCP_in.count(t_count)
                if count > 0:
                    count = 1
                countrate_tot += count
                self.set_countrate_ROI(countrate_tot)
                delay(t_manual_delay*us)
        

    @rpc(flags={"async"})
    def set_countrate_ROI(self, value):
        self.set_dataset(key="main_sequence.result.countrate_ROI", value = value, broadcast=True) 

    @kernel
    def kernel_run_pulse_counting(self):
        pulse_counting_time = self.t_pulse_counting
        n_datapoints = self.n_datapoints

        self.ttl_390.on()
        for k in range(n_datapoints):
            self.core.break_realtime()
            with parallel:
                t_count = self.ttl_MCP_in.gate_rising(pulse_counting_time*ms)
                self.ttl_Extraction.pulse(2*us) # extraction pulse    
            count = self.ttl_MCP_in.count(t_count)
            self.set_countrate_CW(k,count)
        
    @rpc(flags={"async"})
    def set_countrate_CW(self, index, value):
        self.mutate_dataset(key="main_sequence.result.countrate_CW", index = index, value = value, broadcast=True) 