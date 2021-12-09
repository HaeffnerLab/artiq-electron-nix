import sys
import os
#import datetime import datetime
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
import time
import numpy as np

class Run_UpdateVoltages(EnvExperiment):
    
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0')

    def prepare(self):
        self.voltages = self.get_dataset(key="dac_voltages")
        print(self.voltages)
        print("updating voltages")
    
    @kernel
    def run(self):
        self.core.reset()
        self.zotino0.init()        
      
        for pin in range(len(self.voltages)):
            delay(500*us)
            self.zotino0.write_dac(pin,self.voltages[pin])

        self.zotino0.load()
        
        #test first pins
        '''
        delay(500*us)
        self.zotino0.write_dac(0,voltages[0])
        self.zotino0.write_dac(1,voltages[1])
        self.zontin0.load()
        '''
