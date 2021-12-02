from artiq.experiment import *
def print_underflow():
	print("RTIO underflow occured")
class Tutorial(EnvExperiment):
	def build(self):
		self.setattr_device("core")
		self.setattr_device("ttl12")
	@kernel
	def run(self):
		self.core.reset()
		# self.ttl12.output()
		# for i in range(200):
		# 	self.ttl12.pulse(0.01*us)
		# 	delay(0.01*us)


		try:
			for i in range(20):
				self.ttl12.pulse(0.01*us)
				delay(0.01*us)
		except RTIOUnderflow:
			print_underflow()

		# while True:
		# 	should_break = True
		# 	for i in range(20):
		# 		try:
		# 			self.ttl12.pulse(0.01*us)
		# 			delay(0.01*us)
		# 		except RTIOUnderflow:
		# 			should_break = False
		# 			continue
		# 			# print_underflow()
		# 	if should_break:
		# 		break

		# i = 0
		# while True:
		# 	try:
		# 		self.ttl12.pulse(0.01*us)
		# 		delay(0.01*us)
		# 		i += 1
		# 	except RTIOUnderflow:
		# 		continue
		# 		# print_underflow()
		# 	if i == 19:
		# 		break