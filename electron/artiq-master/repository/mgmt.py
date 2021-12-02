from artiq.experiment import *
from artiq.language.core import TerminationRequested, kernel
from artiq.coredevice.ad9910 import PHASE_MODE_TRACKING
import numpy as np
import time

class MgmtTutorial(EnvExperiment):
    """Management tutorial"""
    def build(self):
        self.setattr_device("core")
        self.t = self.get_device("ttl8")
        self.setattr_device("ttl9")
        self.d0 = self.get_device("urukul0_ch0") #channel to the AOM
        self.setattr_device("ttl10")
        self.setattr_device("ttl11")
        self.setattr_device("ttl12")
        self.setattr_device("sampler0")
        self.setattr_argument("Attenuation", NumberValue(ndecimals=0, step=1,min = -63*dB,max = -5*dB,default = -63*dB,unit = "dB"))
        self.setattr_argument("Frequency", NumberValue(ndecimals=0, step=1,min = 0*MHz,max = 240*MHz,default = 220*MHz,unit = "MHz"))
        self.setattr_argument("rep", NumberValue(ndecimals=0, step=1))
        self.setattr_argument("AOM_pw", NumberValue(ndecimals=0, step=0.1,min = 0*us,max = 200*us,default = 10*us,unit = "us"))
        self.setattr_argument("RF_ON_time", NumberValue(ndecimals=0, step=0.1,min = 0*us,max = 200*us,default = 10*us,unit = "us"))
        self.setattr_argument("RF_pw", NumberValue(ndecimals=0, step=0.1,min = 0*us,max = 200*us,default = 10*us,unit = "us"))

    def prepare(self):
        self.timestamp = dict()
        self.set_dataset("time", [])
        # self.set_dataset("parabola", np.full(self.count, np.nan)
        # self.data = np.full((8),0,dtype=np.int32)


    @kernel   
    def run(self):
        self.core.reset()
        #self.ttl8.output()
        self.ttl9.output()
        self.ttl10.output()
        self.ttl11.output()
        self.ttl12.output()
        self.d0.cpld.init()
        self.d0.init()
        self.sampler0.init()
        # self.set_dataset("data", np.full(self.count, np.nan), broadcast=True)

        t = now_mu() #initializing the clock wrt artiq

        #AOM parameters
        self.d0.set_att(self.Attenuation*dB) #Attenuation of the laser power
        #self.d0.set_frequency(10*MHz) #frequency
        self.d0.set(self.Frequency*MHz, phase=0., ref_time_mu=t)# starts with t


        for i in range(self.rep):

            self.core.reset()

            #AOM ON and OFF
            self.core.reset()
            self.t.on()
            self.d0.sw.on()
            self.t.pulse(self.AOM_pw*us)# length of the pulse to the AOM
            self.d0.sw.off()

            #delay between AOM and RF
            delay(self.RF_ON_time*us) #time between the start of the AOM pulse and the start of rf pulse

            #RF ON
            self.ttl9.pulse(self.RF_pw*us) # TTL pulse to the rf generator--> need to substitute with a AM modulated signal

            # self.sampler0.sample_mu(self.data)

            
           




        print("Hello World122")