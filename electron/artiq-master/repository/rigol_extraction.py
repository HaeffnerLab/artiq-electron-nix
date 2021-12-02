import numpy as np
import vxi11
import matplotlib.pyplot as plt


class rigol():

	def __init__(self):
		# self.sampling_time = sampling_time # 
		self.offset_ej = 0
		self.amplitude_ej = 20
		self.amplitude_reset = 3.3
		self.offset_reset = 0
		self.inst = vxi11.Instrument('TCPIP0::192.168.169.113::INSTR')
		# self.inst2 = vxi11.Instrument('TCPIP0::192.168.169.117::INSTR')
		# print(self.inst.ask('*IDN?'))

	def run(self, pulse_width_ej, pulse_delay_ej):
		self.pulse_width_ej = pulse_width_ej
		self.pulse_delay_ej = pulse_delay_ej
		inst = self.inst
		inst.write("OUTPUT2 OFF")
		inst.write("OUTPUT1 OFF")	
		# hardcode sampling rate for ejection pulse, since only need the first few hundred ns
		period_ej = 1000.E-9
		waveform_ej = np.zeros(500)
		waveform_ej[:] = -1
		waveform_ej[np.int(self.pulse_delay_ej/2E-9):np.int((self.pulse_delay_ej+self.pulse_width_ej)/2E-9)] = 1
		ej_str = ",".join(map(str,waveform_ej))

#####
		period_reset = 1000.E-9
		waveform_reset = np.zeros(500)
		waveform_reset[:] = -1
		waveform_reset[np.int(self.pulse_delay_ej/2E-9):np.int((self.pulse_delay_ej+self.pulse_width_ej)/2E-9)] = 1
		reset_str = ",".join(map(str,waveform_reset))


		# Channel 1 reset pulse of threshold detector
		inst.write(":OUTPut1:LOAD INFinity")
		inst.write("SOURCE1:PERIOD {:.9f}".format(period_reset))
		# print(inst.ask("SOURCE2:PERIOD?"))
		inst.write("SOURCE1:VOLTage:UNIT VPP")
		inst.write("SOURCE1:VOLTage {:.3f}".format(self.amplitude_reset))
		inst.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(self.offset_reset))

		inst.write("SOURCE2:TRACE:DATA VOLATILE,"+ reset_str)

		inst.write("SOURce2:BURSt ON")

		# inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
		inst.write("SOURce2:BURSt:MODE TRIGgered")
		inst.write("SOURce2:BURSt:NCYCles 1")
		# inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
		inst.write("SOURCe2:BURSt:TRIGger:SOURce EXTernal")
		inst.write("SOURce2:BURSt:TRIGger:SLOPe POSitive")



######


		# Channel 2
		inst.write(":OUTPut2:LOAD INFinity")
		inst.write("SOURCE2:PERIOD {:.9f}".format(period_ej))
		# print(inst.ask("SOURCE2:PERIOD?"))
		inst.write("SOURCE2:VOLTage:UNIT VPP")
		inst.write("SOURCE2:VOLTage {:.3f}".format(self.amplitude_ej))
		inst.write("SOURCE2:VOLTage:OFFSet {:.3f}".format(self.offset_ej))

		inst.write("SOURCE2:TRACE:DATA VOLATILE,"+ ej_str)

		inst.write("SOURce2:BURSt ON")

		# inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
		inst.write("SOURce2:BURSt:MODE TRIGgered")
		inst.write("SOURce2:BURSt:NCYCles 1")
		# inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
		inst.write("SOURCe2:BURSt:TRIGger:SOURce EXTernal")
		inst.write("SOURce2:BURSt:TRIGger:SLOPe POSitive")

		inst.write("OUTPUT2 ON")
		inst.write("OUTPUT1 ON")
 


		return