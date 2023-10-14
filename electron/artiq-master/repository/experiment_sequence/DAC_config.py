from artiq.experiment import *
import numpy as np

class DAC_config(EnvExperiment):

    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0')

        # pin matching: electrode name, zotino channel number
        self.pin_matching = {
            "DC0":9,
            "DC1":4,
            "DC2":16,
            "DC3":6,
            "DC4":17,
            "DC5":2,
            "DC6":14,
            "DC7":24,
            "DC8":23,
            "trigger_level":0,
            }
        
        # whether or not having a grid voltage
        # self.grid = False
        # grid multipole for 1V

        self.grid_m = {'C': 1.781389e-02,'Ey': -4.649592e-06,'Ez': 9.989530e-02,'Ex': 4.148890e-06,'U3': 4.179541e-07,'U4':2.342674e-05,'U2': 1.304532e-01,'U5': 2.279447e-05,'U1': 6.951562e-07}
        # list of excess electrodes which is not included in the cfile, in this case it's the threshold voltage
        self.excess_e = ["trigger_level"]
        # c file in csv format
        self.c_file_csv = '/home/electron/artiq-nix/electron/flipped_Electron3dTrap_200um_v6_cfile_grid.csv'

        # gnd pins
        self.gnd = [3,15,25]
        # if or not use amplifier
        self.use_amplifier = False
        # max absolute voltage of the zotino channel
        self.max_voltage = 9.5
        
        # self.controlled_electrodes = ["DC0","DC1","DC2","DC3","DC4","DC5","DC6","DC7","DC8","trigger_level"]
        self.controlled_multipoles = ["Ex","Ey","Ez","U1","U2","U3","U4","U5"]
        # self.controlled_multipoles_dict = {"Ex":'Ex:', "Ey":'Ey:', "Ez":'Ez:', "U1":'U1:', "U2":'U2:', "U3":'U3:', "U4":'U4:', "U5":'U5:'}


    @kernel
    def run(self):
        self.core.reset()
    
    def loadDACoffset(self):
        # calibration file, = np.array([y0,slope])
        f = '/home/electron/artiq-nix/electron/zotino_calibration_3dtrap.txt'
        tmp = np.loadtxt(f)
        self.dac_calibration_fit = tmp 
        self.dac_manual_offset = [0.,0.,-0.002,0.,0.002,0.,-0.003,0.,0.,-0.001,0.,0.,0.,0.,-0.002,0.,0.001,0.01,0.,0.,0.,0.,0.,0.005,0.003,0.]