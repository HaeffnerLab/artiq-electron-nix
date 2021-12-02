import numpy as np
import vxi11
import matplotlib.pyplot as plt
 
# change the IP address to your instrument's IP
inst = vxi11.Instrument('TCPIP0::192.168.169.113::INSTR')
print(inst.ask('*IDN?'))


pulse_width_ao = 200E-9
# pulse_delay_ao = 2E-9
pulse_delay_ao = 2E-9 + 426E-9

pulse_width_ej = 20E-9
pulse_delay_ej = 2E-9 + pulse_width_ao - pulse_width_ej - 10E-9
# pulse_delay_ej = 2E-9
delay = 0

# Settings:
sampling_time = 1E-9
period = 0.7E-6 + pulse_width_ao
print("{:.9f}".format(period))
period_burst = 3E-6 + pulse_width_ao
print (period_burst)
print ('{:.9f}'.format(period_burst))


offset_ej = 0
amplitude_ej = 20
offset_ao = 2
amplitude_ao = 4

 
samples = np.int(period/sampling_time)
print (samples)
if (samples>16384):
    import sys
    sys.exit("Waveform too long!")
x = np.linspace(0, period, samples)
waveform_ej = np.zeros(samples)
waveform_ej[:] = -1
waveform_ej[np.int(pulse_delay_ej/sampling_time):np.int((pulse_delay_ej+pulse_width_ej)/sampling_time)] = 1

waveform_ao = np.zeros(samples)
waveform_ao[:] = -1
waveform_ao[np.int(pulse_delay_ao/sampling_time):np.int((pulse_delay_ao+pulse_width_ao)/sampling_time)] = 1

plt.figure(figsize = (3.5, 2.8), dpi = 200)
plt.plot(x/1E-6, np.roll(waveform_ej, 420))
plt.plot(x/1E-6, waveform_ao)
plt.show()

ao_str = ",".join(map(str,waveform_ao))
ej_str = ",".join(map(str,waveform_ej))

inst.write("OUTPUT2 OFF")
inst.write("OUTPUT1 OFF")

# Channel 1
inst.write(":OUTPut1:LOAD 50")
inst.write("SOURCE1:PERIOD {:.9f}".format(period))
print(inst.ask("SOURCE1:PERIOD?"))
inst.write("SOURCE1:VOLTage:UNIT VPP")
inst.write("SOURCE1:VOLTage {:.3f}".format(amplitude_ao))
inst.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(offset_ao))

inst.write("SOURCE1:TRACE:DATA VOLATILE,"+ ao_str)

# Channel 2
inst.write(":OUTPut2:LOAD INFinity")
inst.write("SOURCE2:PERIOD {:.9f}".format(period))
print(inst.ask("SOURCE2:PERIOD?"))
inst.write("SOURCE2:VOLTage:UNIT VPP")
inst.write("SOURCE2:VOLTage {:.3f}".format(amplitude_ej))
inst.write("SOURCE2:VOLTage:OFFSet {:.3f}".format(offset_ej))
# inst.write("SOURCE2:PULSe:WIDTh {:f}".format(pulse_width_ej))
# inst.write("SOURCE2:APPLy:PULSe ")

inst.write("SOURCE2:TRACE:DATA VOLATILE,"+ ej_str)


inst.write("SOURce1:BURSt ON")
inst.write("SOURce1:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
inst.write("SOURce1:BURSt:MODE TRIGgered")
inst.write("SOURce1:BURSt:NCYCles 1")
inst.write("SOURce1:BURSt:TRIGger:TRIGOut POSitive")

inst.write("SOURce2:BURSt ON")
inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
inst.write("SOURce2:BURSt:MODE TRIGgered")
inst.write("SOURce2:BURSt:NCYCles 1")
inst.write("SOURce2:BURSt:TDELay {:f}".format(delay))
inst.write("SOURCe2:BURSt:TRIGger:SOURce EXTernal")
inst.write("SOURce2:BURSt:TRIGger:SLOPe POSitive")

 
### you can also automate some other stuff
### see the programmers manual of the RIGOL DG4000 series
inst.write("OUTPUT2 ON")
inst.write("OUTPUT1 ON")
# inst.write("OUTPUT2:SYNC ON")
# print (inst.write("OUTPUT1:SYNC?"))
 
print(inst.ask("OUTPUT1?"))
print(inst.ask("OUTPUT2?"))