import vxi11
import numpy as np

class rigol():
    def __init__(self,ip=115,pulse_width_ej=800.E-9, pulse_delay_ej=2.E-9,offset_ej=0,amplitude_ej=-20,phase=0,period_ej=1000.E-9,sampling_time=2.E-9):
        # self.sampling_time = sampling_time # 
        
        # initial phase != 0, voltage 0 ~ -20 V, need to manually adjust and see on the scope or AWG
        self.pulse_width_ej = pulse_width_ej
        self.pulse_delay_ej = pulse_delay_ej
        self.offset_ej = offset_ej
        self.amplitude_ej = amplitude_ej
        self.phase = phase
        self.period_ej = period_ej
        self.sampling_time = sampling_time
        self.inst = vxi11.Instrument('TCPIP0::192.168.169.'+str(ip)+'::INSTR')
        
       

    def run(self):
        inst = self.inst
        inst.write("OUTPUT2 OFF")
        inst.write("OUTPUT1 OFF")   
        # hardcode sampling rate for ejection pulse, since only need the first few hundred ns
        
        # ###### use channel one to extrac on the bottom two central electrodes
        # waveform_ej = np.zeros(int(self.period_ej/self.sampling_time))
        waveform_ej = np.zeros(500)
        waveform_ej[:] = -1
        waveform_ej[np.int(self.pulse_delay_ej/self.sampling_time):np.int((self.pulse_delay_ej+self.pulse_width_ej)/self.sampling_time)] = 1
        ej_str = ",".join(map(str,waveform_ej))
        # Channel 1
        inst.write(":OUTPut1:LOAD INFinity")
        inst.write("SOURCE1:PERIOD {:.9f}".format(self.period_ej))
        # print(inst.ask("SOURCE2:PERIOD?"))
        inst.write("SOURCE1:VOLTage:UNIT VPP")
        inst.write("SOURCE1:VOLTage {:.3f}".format(self.amplitude_ej))
        inst.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(self.offset_ej))
        inst.write("SOURCE1:TRACE:DATA VOLATILE,"+ ej_str)
        # inst.write("SOURCE2:PHASe 20")
        
        inst.write("SOURce1:BURSt ON")

        # inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))

        # inst.write("SOURce1:BURSt:GATE:POL NORMal")

        # inst.write("SOURce1:BURSt:PHASe {:.3f}".format(self.phase))


        inst.write("SOURce1:BURSt:MODE TRIGgered")
        inst.write("SOURce1:BURSt:NCYCles 1")
        # inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
        inst.write("SOURCe1:BURSt:TRIGger:SOURce EXTernal")
        inst.write("SOURce1:BURSt:TRIGger:SLOPe POSitive")


        inst.write("OUTPUT1 ON")
        # inst.write("OUTPUT2 ON")
        return

class RS():
    def __init__(self, sampling_time=0):
        self.inst = vxi11.Instrument('TCPIP::192.168.169.101::INSTR')
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
        #print(inst.ask("OUTPUT?"))
        return 

    # def stop(self):
    #     inst = self.inst
    #     inst.write('OUTPut OFF')
    #     inst.write('SOURce:MOD:ALL:STAT OFF')




'''
rs = RS()
frequencies = np.arange(66, 77, 0.1) * 1E6
amp_trapfreq = -20.0
U2 = -0.7
Prf = +2.5
load_time = 200 E-6
wait_time = 4000E-6
for freq_trapfreq in frequencies:
    rs.run(freq_trapfreq,amp_trapfreq)
'''
