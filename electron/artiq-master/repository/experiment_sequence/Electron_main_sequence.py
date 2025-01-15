from artiq.experiment import *
import numpy as np

import pulse_sequence
import start_devices
import load_DAC
from load_DAC import DAC

class Main_sequence(DAC):
    def build(self):
        super().build()
        pulse_sequence.pulse_sequence.build(self)
        start_devices.Devices.build(self)

        self.setattr_device("ccb")
        # self.setattr_argument("output_pulse", BooleanValue(default = True), group = "Main sequence")

    #def prepare(self):


    def run(self):
        print("RUN")
        start_devices.Devices.start_rigol(self)

        msm = MultiScanManager(
            ("pulse_delay_ej", self.pulse_delay_ej_Scan),
            ("t_load", self.t_load_Scan),
            ("t_wait", self.t_wait_Scan),
            ("U2", self.U2_Scan),
            ("Ex", self.Ex_Scan),
            ("Ey", self.Ey_Scan),
            ("Ez", self.Ez_Scan),
            ("DC0_bias",self.DC0_bias_Scan)
        )

        applet_command = "python /home/electron/artiq-nix/artiq/applets/small_number.py" #FIXME
        #test_point = next(iter(msm))
        #all_param_names = [*test_point.__dict__]
        total = len(list(enumerate(msm)))
        all_param_names = ['ScanRunNumber', 'TotRunNumber']
        all_datasets = [' main_sequence.' + i for i in all_param_names]
        for dataset in all_datasets:
            applet_command += dataset
        for count, point in enumerate(msm):
            print(count,point)
            self.Assign_scan_run_values(point)

            # self.ccb.issue("create_applet", "progress_bar","${artiq_applet}progress_bar Progress")
            #self.ccb.issue("create_applet", "big_number","${artiq_applet}big_number main_sequence.ScanRunNumber")
            
            
            self.ccb.issue("create_applet", "small_number", applet_command)
            #self.set_ScanRunNumber(count)
            #print(point)
            self.set_scan_output(count, total, point)

            self.run_seq()
            print("done scan No.", count)
            
        print("Finished scan")

    
    def Assign_scan_run_values(self, point):
        for key in [*point.__dict__]:
            if key != 'attr':
                setattr(self,key,getattr(point,key))
    
    @rpc(flags={"async"})
    def set_ScanRunNumber(self,value):
        self.set_dataset(key = "main_sequence.ScanRunNumber",value=value,broadcast = True)

    @rpc(flags={"async"})
    def set_scan_output(self, count, total, point):
        self.set_dataset(key = "main_sequence.ScanRunNumber",value=count,broadcast = True)
        self.set_dataset(key = "main_sequence.TotRunNumber",value=total,broadcast = True)
        '''
        for key in [*point.__dict__]:
            if key != 'attr':
                self.set_dataset(key=f"main_sequence.{key}", value=getattr(point,key), broadcast=True)
        '''

    @rpc(flags={"async"})
    def set_progress(self):

        n = 100
        t_period = self.t_load + self.t_wait + self.t_manual_delay + 2
        T_total = t_period * self.n_repetitions
        for i in range(n):
            self.set_dataset("Progress",100*(i+1)/n, broadcast = True)
            time.sleep(T_total/n)


    def run_seq(self):
        # self.core.reset() # double @kernel cuz an error for load_dac

        # self.set_progress()
        # self.core.break_realtime()
        
        self.load_DAC()
        #load_DAC.DAC.load_DAC(self)
        pulse_sequence.pulse_sequence.kernel_run_outputting(self)



        


        






        