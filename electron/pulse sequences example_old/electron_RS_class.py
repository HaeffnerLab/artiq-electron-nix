import vxi11
import matplotlib.pyplot as plt
class RS():
    def __init__(self, sampling_time=0):
        self.inst = vxi11.Instrument('TCPIP::192.168.169.114::INSTR')
        print(self.inst.ask('*IDN?'))

    def run(self, freq, power):
        self.freq = freq
        self.power = power
        inst = self.inst
        # inst.write("OUTPut OFF")
        # Channel 1
        # print(inst.ask(":OUTPut:IMPedance?"))
        inst.write("SOURce:FREQuency: MODE CW")
        inst.write("SOURce:FREQuency {:.9f}".format(self.freq))
        inst.write("SOURce:POWer:POWer {:.3f}".format(self.power))
        inst.write('SOURce:MOD:ALL:STAT ON')
        inst.write("OUTPut ON")
        # print(inst.ask("OUTPUT?"))
        return 

    def stop(self):
        inst = self.inst
        inst.write('OUTPut OFF')
        inst.write('SOURce:MOD:ALL:STAT OFF')


    