from GUI_develop import Electron
from artiq.experiment import EnvExperiment
from artiq.experiment import *

class Electron_2Layer(Electron, EnvExperiment):
    def build(self, config_name='Electron'):
        self.config_name = config_name
        Electron.build(self, config_name=self.config_name)

    def prepare(self):
        Electron.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        #self.launch_GUI()
        print("Bye World")

class Electron_3Layer(Electron, EnvExperiment):
    def build(self, config_name='ThreeLayer'):
        self.config_name = config_name
        Electron.build(self, config_name=self.config_name)

    def prepare(self):
        Electron.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        #self.launch_GUI()
        print("Bye World")



class Electron_3Dprint(Electron, EnvExperiment):
    def build(self, config_name='3Dprint'):
        self.config_name = config_name
        Electron.build(self, config_name=self.config_name)

    def prepare(self):
        Electron.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        #self.launch_GUI()
        print("Bye World")

