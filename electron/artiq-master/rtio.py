# from artiq.experiment import *


# class Tutorial(EnvExperiment):
#     def build(self):
#         self.setattr_device("core")
#         self.setattr_device("ttl8")
#         self.setattr_device("ttl6")
#         self.setattr_device("ttl10")
    
#     @kernel
#     def init_urukul(self, cpld):
#         self.core.break_realtime()
#         cpld.init()
#     @kernel
#     def run(self):
#         self.core.reset()
#         self.ttl8.output()
#         self.ttl6.output()
#         # self.ttl10.output()

#         for i in range(10000000):
#             with parallel:
#                 with sequential:
#                     delay(4*us)
#                     self.ttl6.pulse(2*us)

#                 self.ttl8.pulse(2*us)
                
#             delay(10*us)


    
# from artiq.experiment import *


# class Blink(EnvExperiment):
#     def build(self):
#         self.setattr_device("core")
#         self.leds = [self.get_device("led1"), self.get_device("led2")]

#     @kernel
#     def run(self):
#         self.core.reset()

#         while True:
#             for led in self.leds:
#                 led.pulse(200*ms)
#                 delay(200*ms)

from artiq.experiment import *


class Tutorial(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("ttl10")

    @kernel
    def run(self):
        self.core.reset()
        self.ttl10.output()
        for i in range(100000000000):
            delay(2*us)
            self.ttl10.pulse(2*us)
            # with sequential:
            #     delay(2*us)
            #     self.ttl1.pulse(1*us)
            #     # delay(2*us)
            
            