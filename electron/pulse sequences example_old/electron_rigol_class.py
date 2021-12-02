import numpy as np
import vxi11
import matplotlib.pyplot as plt


class rigol():

	def __init__(self, sampling_time):
		self.sampling_time = sampling_time # 
		self.offset_ej = 0
		self.amplitude_ej = 20
		self.offset_ao = 2
		self.amplitude_ao = 4
		self.inst = vxi11.Instrument('TCPIP0::192.168.169.113::INSTR')
		self.inst2 = vxi11.Instrument('TCPIP0::192.168.169.117::INSTR')
		self.delay = 0
		# print(self.inst.ask('*IDN?'))

	def run(self, pulse_width_ao, pulse_delay_ao, pulse_width_ej, pulse_delay_ej, wait_time):
		self.pulse_width_ao = pulse_width_ao
		self.pulse_delay_ao = pulse_delay_ao
		self.pulse_width_ej = pulse_width_ej
		self.pulse_delay_ej = pulse_delay_ej
		self.wait_time = wait_time
		# self.delay = delay
		inst = self.inst
		inst.write("OUTPUT2 OFF")
		inst.write("OUTPUT1 OFF")
		period = 0.4E-6 + self.pulse_width_ao	# this is duration of the AW
		# print (period)
		period_burst = self.wait_time + period - 240E-9 	# this is the repetition period
		correction = period_burst % 0.8E-6
		period_burst = period_burst + 0.8E-6 - correction
		wait_time_corrected = self.wait_time + 0.8E-6 - correction
		# print ('{:.9f}'.format(period_burst))

		samples = np.int(period/self.sampling_time)
		# print (samples)
		if (samples>16384):
		    import sys
		    sys.exit("Waveform too long!")
		x = np.linspace(0, period, samples)

		waveform_ao = np.zeros(samples)
		waveform_ao[:] = -1
		waveform_ao[np.int(self.pulse_delay_ao/self.sampling_time):np.int((self.pulse_delay_ao+self.pulse_width_ao)/self.sampling_time)] = 1

		# hardcode sampling rate for ejection pulse, since only need the first few hundred ns
		period_ej = 1000.E-9
		waveform_ej = np.zeros(500)
		waveform_ej[:] = -1
		waveform_ej[np.int(self.pulse_delay_ej/2E-9):np.int((self.pulse_delay_ej+self.pulse_width_ej)/2E-9)] = 1
		# waveform_ej[np.int(self.pulse_delay_ej/self.sampling_time):np.int((self.pulse_delay_ej+self.pulse_width_ej)/self.sampling_time)] = 1

		# plt.figure(figsize = (3.5, 2.8), dpi = 200)
		# plt.plot(x/1E-6, np.roll(waveform_ej, 0))
		# plt.plot(x/1E-6, waveform_ao)
		# plt.show()

		ao_str = ",".join(map(str,waveform_ao))
		ej_str = ",".join(map(str,waveform_ej))

		# Channel 1
		inst.write(":OUTPut1:LOAD 50")
		inst.write("SOURCE1:PERIOD {:.9f}".format(period))
		# print(inst.ask("SOURCE1:PERIOD?"))
		inst.write("SOURCE1:VOLTage:UNIT VPP")
		inst.write("SOURCE1:VOLTage {:.3f}".format(self.amplitude_ao))
		inst.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(self.offset_ao))

		inst.write("SOURCE1:TRACE:DATA VOLATILE,"+ ao_str)

		inst.write("SOURce1:BURSt ON")
		inst.write("SOURce1:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
		inst.write("SOURce1:BURSt:MODE TRIGgered")
		inst.write("SOURce1:BURSt:NCYCles 1")
		inst.write("SOURce1:BURSt:TRIGger:TRIGOut POSitive")

		# Channel 2
		inst.write(":OUTPut2:LOAD INFinity")
		inst.write("SOURCE2:PERIOD {:.9f}".format(period_ej))
		# print(inst.ask("SOURCE2:PERIOD?"))
		inst.write("SOURCE2:VOLTage:UNIT VPP")
		inst.write("SOURCE2:VOLTage {:.3f}".format(self.amplitude_ej))
		inst.write("SOURCE2:VOLTage:OFFSet {:.3f}".format(self.offset_ej))

		inst.write("SOURCE2:TRACE:DATA VOLATILE,"+ ej_str)

		inst.write("SOURce2:BURSt ON")
		inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
		inst.write("SOURce2:BURSt:MODE TRIGgered")
		inst.write("SOURce2:BURSt:NCYCles 1")
		# inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
		inst.write("SOURCe2:BURSt:TRIGger:SOURce EXTernal")
		inst.write("SOURce2:BURSt:TRIGger:SLOPe POSitive")

		inst.write("OUTPUT1 ON")
		inst.write("OUTPUT2 ON")
 
		# print(inst.ask("OUTPUT1?"))
		# print(inst.ask("OUTPUT2?"))

		return period_burst, wait_time_corrected

	def rigol2(self, pulse_width_ao, pulse_delay_ao, pulse_width_ej, pulse_delay_ej, wait_time, amp_square=1.3, offset_square=0):
		self.amp_square = amp_square
		self.offset_square = offset_square
		self.pulse_width_ao = pulse_width_ao
		self.pulse_delay_ao = pulse_delay_ao
		self.pulse_width_ej = pulse_width_ej
		self.pulse_delay_ej = pulse_delay_ej
		self.wait_time = wait_time
		inst2 = self.inst2
		inst2.write("OUTPUT2 OFF")
		inst2.write("OUTPUT1 OFF")

		period = 0.4E-6 + self.pulse_width_ao	# this is duration of the AW
		# print (period)
		period_burst = self.wait_time + period - 240E-9 	# this is the repetition period
		correction = period_burst % 0.8E-6
		period_burst = period_burst + 0.8E-6 - correction
		wait_time_corrected = self.wait_time + 0.8E-6 - correction
		# print ('{:.9f}'.format(period_burst))
		period = period_burst - 1E-6
		samples = np.int(period/self.sampling_time)
		# print (samples)
		if (samples>16384):
		    import sys
		    sys.exit("Waveform too long!")
		x = np.linspace(0, period, samples)

		waveform_square = np.zeros(samples)
		waveform_square[:] = 1
		waveform_square[0:np.int((self.pulse_delay_ao+self.pulse_width_ao)/self.sampling_time)] = -1
		waveform_square[-40:] = -1

		square_str = ",".join(map(str,waveform_square))
		


		inst2.write("SOURCE1:PERIOD {:.9f}".format(period))
		# print(inst.ask("SOURCE1:PERIOD?"))
		inst2.write("SOURCE1:VOLTage:UNIT VPP")
		inst2.write("SOURCE1:VOLTage {:.3f}".format(self.amp_square))
		inst2.write("SOURCE1:VOLTage:OFFSet {:.3f}".format(self.offset_square))
		inst2.write("OUTPut1:POLarity NORMal")

		inst2.write("SOURCE1:TRACE:DATA VOLATILE,"+ square_str)

		inst2.write("SOURce1:BURSt ON")
		inst2.write("SOURce1:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
		inst2.write("SOURce1:BURSt:MODE TRIGgered")
		inst2.write("SOURce1:BURSt:NCYCles 1")
		

		
		# inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
		inst2.write("SOURCe1:BURSt:TRIGger:SOURce EXTernal")
		inst2.write("SOURce1:BURSt:TRIGger:SLOPe POSitive")
		# inst2.write("SOURce1:BURSt:TRIGger:TRIGOut POSitive")



		inst2.write(":OUTPut1:LOAD INFinity")
		# inst_trapfreq.write("SOURce1:APPLy:SINusoid {:.3f}".format(self.freq_trapfreq),"{:.3f}".format(self.amplitude_trapfreq))
		inst2.write("OUTPUT1 ON")
		return
