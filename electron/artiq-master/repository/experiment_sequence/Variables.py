from artiq.experiment import *
import DAC_config

class Variables(EnvExperiment):

    def build_pulse_sequence(self):

        ### loading
        self.t_load = 200

        self.setattr_argument("t_load" + "_Scan", 
                              Scannable(default = [NoScan(self.t_load), RangeScan(start = 10, stop = 1010, npoints = 10)],
                                        ndecimals = 0, global_step = 1, global_min = 5, global_max = 1810),
                                        group = "Scan", tooltip = "[us] | loading time for 390 on")


        ### wait
        self.t_wait = 10

        self.setattr_argument("t_wait" + "_Scan", 
                              Scannable(default = [NoScan(self.t_wait), RangeScan(start = 10, stop = 10E3, npoints = 10)],
                                        ndecimals = 0, global_step = 1, global_min = 2, global_max = 1E6),
                                        group = "Scan", tooltip = "[us] | wait time between the 390 off and extraction on")
        
    def build_rigol(self):
        self.pulse_delay_ej = 100.
        
        self.setattr_argument("pulse_delay_ej" + "_Scan",
                              Scannable(default = [NoScan(self.pulse_delay_ej), RangeScan(start = 20, stop = 200, npoints = 181)],
                                        ndecimals = 2, global_step = 0.01, global_min = -30, global_max = 1000),
                                        group = "Scan", tooltip = "[ns] | ejectrion pulse delay")
        
    def build_load_DAC(self):

        ### multipoles
        self.U2 = -1.
        self.setattr_argument("U2" + "_Scan", 
                              Scannable(default = [NoScan(self.U2), RangeScan(start = -2, stop = 0, npoints = 10)],
                                        ndecimals = 3, global_step = .001, global_min = -30, global_max = 30),
                                        group = "Scan", tooltip = "U2 (V2/mm2)")
        
        self.Ex = 0.
        self.setattr_argument("Ex" + "_Scan", 
                              Scannable(default = [NoScan(self.Ex), RangeScan(start = -0.2, stop = 0.2, npoints = 10)],
                                        ndecimals = 3, global_step = .001, global_min = -4, global_max = 4),
                                        group = "Scan", tooltip = "Ex (V/mm)")
        
        self.Ey = 0.
        self.setattr_argument("Ey" + "_Scan", 
                              Scannable(default = [NoScan(self.Ey), RangeScan(start = -0.2, stop = 0.2, npoints = 10)],
                                        ndecimals = 3, global_step = .001, global_min = -3, global_max = 3),
                                        group = "Scan", tooltip = "Ey (V/mm)")
        
        self.Ez = 0.
        self.setattr_argument("Ez" + "_Scan", 
                              Scannable(default = [NoScan(self.Ez), RangeScan(start = -1, stop = 1, npoints = 100)],
                                        ndecimals = 3, global_step = .001, global_min = -6, global_max = 6),
                                        group = "Scan", tooltip = "Ez (V/mm)")
        
        self.DC0_bias = 0.
        self.setattr_argument("DC0_bias" + "_Scan", 
                              Scannable(default = [NoScan(self.DC0_bias), RangeScan(start = -1, stop = 1, npoints = 100)],
                                        ndecimals = 3, global_step = .001, global_min = -6, global_max = 6),
                                        group = "Scan", tooltip = "DC0_bias (V)")
        
'''        
        self.U1 = 0.
        self.setattr_argument("U1" + "_Scan", 
                              Scannable(default = [NoScan(self.U1), RangeScan(start = -0.2, stop = 0.2, npoints = 10)],
                                        ndecimals = 3, global_step = .001, global_min = -0.5, global_max = 0.5),
                                        group = "DC.multipole", tooltip = "U1 (V2/mm2)")
        
        self.U3 = 0.
        self.setattr_argument("U3" + "_Scan", 
                              Scannable(default = [NoScan(self.U3), RangeScan(start = -0.2, stop = 0.2, npoints = 10)],
                                        ndecimals = 3, global_step = .001, global_min = -0.5, global_max = 0.5),
                                        group = "DC.multipole", tooltip = "U3 (V2/mm2)")
        
        self.U4 = 0.
        self.setattr_argument("U4" + "_Scan", 
                              Scannable(default = [NoScan(self.U4), RangeScan(start = -0.2, stop = 0.2, npoints = 10)],
                                        ndecimals = 3, global_step = .001, global_min = -0.5, global_max = 0.5),
                                        group = "DC.multipole", tooltip = "U4 (V2/mm2)")
        self.U5 = 0.
        self.setattr_argument("U5" + "_Scan", 
                              Scannable(default = [NoScan(self.U5), RangeScan(start = -0.2, stop = 0.2, npoints = 10)],
                                        ndecimals = 3, global_step = .001, global_min = -0.5, global_max = 0.5),
                                        group = "DC.multipole", tooltip = "U5 (V2/mm2)")
'''
    

        


        

    

    