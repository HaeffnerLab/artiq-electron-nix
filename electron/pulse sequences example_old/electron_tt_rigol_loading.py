import sys
import numpy as np
import matplotlib.pyplot as plt
from electron_rigol_class import *
try:
    import TimeTagger
except:
    print ("Time Tagger lib is not in the search path.")
    pyversion = sys.version_info
    from winreg import ConnectRegistry, OpenKey, HKEY_LOCAL_MACHINE, QueryValueEx
    registry_path = "SOFTWARE\\Python\\PythonCore\\" + str(pyversion.major) + "." + str(pyversion.minor) + "\\PythonPath\\Time Tagger"
    reg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)
    key = OpenKey(reg, registry_path) 
    module_path = QueryValueEx(key,'')[0]
    print ("adding " + module_path)
    sys.path.append(module_path)
    
from TimeTagger import createTimeTagger, Coincidence, Counter, Countrate, Correlation, TimeDifferences, CHANNEL_UNUSED, UNKNOWN, LOW, HIGH
from time import sleep
from pylab import *

# create a timetagger instance
tagger = createTimeTagger()
tagger.reset()

###############################
# Set up experiment: variable parameters
###############################
U2 = -1.0
# parameters for the Rigol waveforms
pulse_width_loading = np.arange(200, 10000, 200) * 1.E-9
# pulse_delay_ao = 2E-9
pulse_delay_ao = 2.E-9 + 426.E-9

pulse_width_ej = 20.E-9
pulse_delay_ej = 2.E-9 + pulse_width_ao - pulse_width_ej - 10.E-9
# pulse_delay_ej = 2E-9
delay = 0
wait_time = 2.E-6
exp_cycles = 1E5  # how many experiment repetitions
################################
for pulse_width_ao in pulse_width_loading:
    # program and switch on Rigol, returns repetition period in s
    cycle_duration = rigol(pulse_width_ao, pulse_delay_ao, pulse_width_ej, pulse_delay_ej, wait_time,delay)
    # sleep(5) # necessary?
    print (cycle_duration)
    filename = 'Exp-name_U2_' + str("{:.1f}".format(U2)) + '_Pao' + str("{:f}".format(pulse_width_ao/1E-9)) + 'ns_Pej' \
    + str("{:f}".format(pulse_width_ej/1E-9) + 'ns_wait' + str("{:f}".format(wait_time/1E-6)) + 'us.txt'
    print (filename)
    ###############################
    # set up time tagger histogram and take data
    histo = Histogram(tagger, click_channel = 2, start_channel = 1, binwidth = 1000, n_bins = np.int(cycle_duration/binwidth*1E12 - 100))
    print (n_bins)
    tagger.sync()
    histo.clear()
    sleep(cycle_duration * exp_cycles)
    data = histo.getData()
    
    ###############################
    # save data
    x_data = np.arange(0, n_bins * binwidth/1000)
    np.savetxt(filename, (x_data, data), delimiter=',')

