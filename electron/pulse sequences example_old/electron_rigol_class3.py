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
        self.inst_trapfreq = vxi11.Instrument('TCPIP0::192.168.169.117::INSTR')
		# print(self.inst.ask('*IDN?'))

	def run(self, pulse_width_ao, pulse_delay_ao, pulse_width_ej, pulse_delay_ej, wait_time,delay):
		self.pulse_width_ao = pulse_width_ao
		self.pulse_delay_ao = pulse_delay_ao
		self.pulse_width_ej = pulse_width_ej
		self.pulse_delay_ej = pulse_delay_ej
		self.wait_time = wait_time
		self.delay = delay
		inst = self.inst
		inst.write("OUTPUT2 OFF")
		inst.write("OUTPUT1 OFF")
		period = 0.4E-6 + self.pulse_width_ao	# this is duration of the AW
		# print("{:.9f}".format(period))
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
		waveform_ej = np.zeros(samples)
		waveform_ej[:] = -1
		waveform_ej[np.int(self.pulse_delay_ej/self.sampling_time):np.int((self.pulse_delay_ej+self.pulse_width_ej)/self.sampling_time)] = 1

		waveform_ao = np.zeros(samples)
		waveform_ao[:] = -1
		waveform_ao[np.int(self.pulse_delay_ao/self.sampling_time):np.int((self.pulse_delay_ao+self.pulse_width_ao)/self.sampling_time)] = 1

		plt.figure(figsize = (3.5, 2.8), dpi = 200)
		plt.plot(x/1E-6, np.roll(waveform_ej, 0))
		plt.plot(x/1E-6, waveform_ao)
		plt.show()

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
		inst.write("SOURCE2:PERIOD {:.9f}".format(period))
		# print(inst.ask("SOURCE2:PERIOD?"))
		inst.write("SOURCE2:VOLTage:UNIT VPP")
		inst.write("SOURCE2:VOLTage {:.3f}".format(self.amplitude_ej))
		inst.write("SOURCE2:VOLTage:OFFSet {:.3f}".format(self.offset_ej))

		inst.write("SOURCE2:TRACE:DATA VOLATILE,"+ ej_str)

		inst.write("SOURce2:BURSt ON")
		inst.write("SOURce2:BURSt:INTernal:PERiod {:.9f}".format(period_burst))
		inst.write("SOURce2:BURSt:MODE TRIGgered")
		inst.write("SOURce2:BURSt:NCYCles 1")
		inst.write("SOURce2:BURSt:TDELay {:f}".format(self.delay))
		inst.write("SOURCe2:BURSt:TRIGger:SOURce EXTernal")
		inst.write("SOURce2:BURSt:TRIGger:SLOPe POSitive")

		inst.write("OUTPUT1 ON")
		inst.write("OUTPUT2 ON")
 
		# print(inst.ask("OUTPUT1?"))
		# print(inst.ask("OUTPUT2?"))

		return period_burst, wait_time_corrected

    def run_trapfreq(self, freq_trapfreq, amplitude_trapfreq, offset_trapfreq = 0, phase_trapfreq = 0):
        self.freq_trapfreq = freq_trapfreq
        self.amplitude_trapfreq = amplitude_trapfreq
        self.offset_trapfreq = offset_trapfreq
        self.phase_trapfreq = phase_trapfreq
        inst_trapfreq = self.inst_trapfreq
        inst_trapfreq.write("OUTPUT2 OFF")
        inst_trapfreq.write("OUTPUT1 OFF")       
        # Channel 1
        inst_trapfreq.write(":OUTPut1:LOAD 50")
        inst_trapfreq.write("SOURce1:APPLy:SINusoid {:.3f}".format(self.freq_trapfreq) + "," + "{:.3f}".format(self.amplitude_trapfreq))


        inst_trapfreq.write("OUTPUT1 ON")

        return



