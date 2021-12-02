from artiq.experiment import *
from artiq.coredevice.ad9910 import PHASE_MODE_TRACKING
import numpy as np


class pulse_sequences(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.t = self.get_device("ttl8") #base clock
        
        self.setattr_device("ttl9")
        self.setattr_device("ttl10")
        self.setattr_device("ttl11")
        self.setattr_device("ttl12")
        self.d0 = self.get_device("urukul0_ch0") #channel to the AOM
        self.setattr_device("sampler0")
        

    def prepare(self):
        self.data = np.full((8),0,dtype=np.int32)


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

        t = now_mu() #initializing the clock wrt artiq


        #AOM parameters
        self.d0.set_att(1*dB) #Attenuation of the laser power
        #self.d0.set_frequency(10*MHz) #frequency
        self.d0.set(10*MHz, phase=0., ref_time_mu=t)# starts with t

        


        for i in range(2):
            self.core.reset()
            self.t.on()
            self.d0.sw.on()
            self.t.pulse(5*us)# length of the pulse to the AOM
            self.d0.sw.off()



            delay(20*us) #time between the start of the AOM pulse and the start of rf pulse
            self.ttl9.pulse(5*us) # TTL pulse to the rf generator--> need to substitute with a AM modulated signal
            self.sampler0.sample_mu(self.data)
            # delay(5*us)# time between the rf and the extraction pulse
            # self.ttl10.pulse(5*us)

        

# #written in such a way that all the channels delay is defined wrt to the main clock that is the channel TTL 8 here

#         for i in range(2): #here the range is times not the actual clock time (set it as the number of repitation needed)
#             with parallel:
                
#                 self.t.on()
#                 self.d0.sw.on()
#                 self.t.pulse(5*us)# main clock
#                 #delay(20*us) #length of the pulse to the AOM
#                 self.d0.sw.off()


#                 with sequential:
#                     delay(5*us) #delay between ttl8 and 9: set as delta 1==0 (generation delay)
#                     self.ttl9.pulse(5*us)
#                 with sequential:
#                     delay(5*us) #delay between ttl8 and 10: set as delta 2==delta 1 + start_time (rf_start time)
#                     self.ttl10.pulse(5*us)
#                 with sequential:
#                     delay(5*us) #delay between ttl8 and 11: set as delta 3==delta 1 + delta 2 (extraction pulse to the function generator)
#                     self.ttl11.pulse(5*us)
#                 with sequential:
#                     delay(5*us) #delay between ttl8 and 12: set as delta 4 (MCP data detection start)
#                     self.ttl12.pulse(5*us)

 
                
#             delay(100*us) #main delay between the experiments: set as one experiment time
            
    
