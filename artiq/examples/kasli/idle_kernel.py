from artiq.experiment import *

class IdleKernel(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("led1")

    @kernel
    def run(self):
        start_time = now_mu() + self.core.seconds_to_mu(500*ms)
        while self.core.get_rtio_counter_mu() < start_time:
            pass
        self.core.reset()
        while True:1
            self.led1.pulse(250*ms)
            delay(125*ms)
            self.led1.pulse(125*ms)
            delay(125*ms)
            self.led1.pulse(125*ms)
            delay(250*ms)
