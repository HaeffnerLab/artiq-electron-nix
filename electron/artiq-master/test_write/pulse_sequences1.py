from artiq.experiment import *

from artiq.coredevice.ad9910 import PHASE_MODE_TRACKING
import numpy as np


class pulse_sequences(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        #self.t = self.get_device("ttl8") #base clock
        self.setattr_device("ttl9")
        self.d0 = self.get_device("urukul0_ch0") #channel to the AOM
        self.setattr_argument("count", NumberValue(ndecimals=0, step=1))
        # self.setattr_device("ttl10")
        # self.setattr_device("ttl11")
        # self.setattr_device("ttl12")
        # self.d0 = self.get_device("urukul0_ch0") #channel to the AOM
        # self.setattr_device("sampler0")

        

    def prepare(self):
        self.data = np.full((8),0,dtype=np.int32)

    @kernel
    def run(self):
        self.core.reset()
        self.ttl9.output()
        t = now_mu() #initializing the clock wrt artiq

        #AOM parameters
        self.d0.set_att(1*dB) #Attenuation of the laser power
        #self.d0.set_frequency(10*MHz) #frequency

        for i in range(self.count):
            print("Hello World", i)