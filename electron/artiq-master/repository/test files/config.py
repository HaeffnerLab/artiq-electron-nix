class channelConfiguration(object):
    """
    Stores complete information for each DAC channel
    """


    def __init__(self, dacChannelNumber, trapElectrodeNumber = None, smaOutNumber = None, name = None, boardVoltageRange = (-40, 40), allowedVoltageRange = (-35, 35)):
        self.dacChannelNumber = dacChannelNumber
        self.trapElectrodeNumber = trapElectrodeNumber
        self.smaOutNumber = smaOutNumber
        self.boardVoltageRange = boardVoltageRange
        self.allowedVoltageRange = allowedVoltageRange
        if (name == None) & (trapElectrodeNumber != None):
            self.name = str(trapElectrodeNumber).zfill(2)
        else:
            self.name = name

    def computeDigitalVoltage(self, analogVoltage):
        return int(round(sum([ self.calibration[n] * analogVoltage ** n for n in range(len(self.calibration)) ])))

class hardwareConfiguration(object):
    EXPNAME = 'CCT'
    default_multipoles = ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3']
    okDeviceID = 'DAC Controller'
    okDeviceFile = 'control_nonnoninverted.bit'
    centerElectrode = 23 #write False if no Centerelectrode
    PREC_BITS = 16
    pulseTriggered = True
    maxCache = 126
    filter_RC = 5e4 * 4e-7
    elec_dict = {
        '01': channelConfiguration(28, trapElectrodeNumber=1),
        '02': channelConfiguration(27, trapElectrodeNumber=2),
        '03': channelConfiguration(24, trapElectrodeNumber=3),
        '04': channelConfiguration(5, trapElectrodeNumber=4),
        '05': channelConfiguration(14, trapElectrodeNumber=5),
        '06': channelConfiguration(18, trapElectrodeNumber=6),
        '07': channelConfiguration(16, trapElectrodeNumber=7),
        '08': channelConfiguration(13, trapElectrodeNumber=8),
        '09': channelConfiguration(11, trapElectrodeNumber=9),
        '10': channelConfiguration(9, trapElectrodeNumber=10), # broken, ground outside
        '11': channelConfiguration(10, trapElectrodeNumber=11), # broken, ground outside
        '12': channelConfiguration(7, trapElectrodeNumber=12),
        '13': channelConfiguration(8, trapElectrodeNumber=13),
        '14': channelConfiguration(26, trapElectrodeNumber=14),
        '15': channelConfiguration(25, trapElectrodeNumber=15),
        '16': channelConfiguration(23, trapElectrodeNumber=16),
        '17': channelConfiguration(4, trapElectrodeNumber=17),
        '18': channelConfiguration(19, trapElectrodeNumber=18),
        '19': channelConfiguration(17, trapElectrodeNumber=19),
        '20': channelConfiguration(3, trapElectrodeNumber=20),
        '21': channelConfiguration(20, trapElectrodeNumber=21),
        '22': channelConfiguration(12, trapElectrodeNumber=22),
        '23': channelConfiguration(6, trapElectrodeNumber=23) #6
        }

    notused_dict = {
        '23': channelConfiguration(1, trapElectrodeNumber=23),
        '24': channelConfiguration(2, trapElectrodeNumber=24),
        '25': channelConfiguration(3, trapElectrodeNumber=25),
        '26': channelConfiguration(4, trapElectrodeNumber=26),
        '27': channelConfiguration(16, trapElectrodeNumber=27),
        '28': channelConfiguration(22, trapElectrodeNumber=28)
               }

    sma_dict = {
        'RF bias': channelConfiguration(1, smaOutNumber=1, name='RF bias', boardVoltageRange=(-40., 40.), allowedVoltageRange=(-2.0, 0))
        }


class Electron:
    """
    Configuration adapted from the GUI_test Electron object.
    """
    devices = ['core',
               'zotino0', # artiq DAC
               'ttl1', 
               'ttl2', # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
               'ttl8', # use this channel to trigger AOM, connect to switch near VCO and AOM
               'ttl9', # use this channel to trigger R&S for tickle pulse, connect to R&S
               'ttl10', # use this channel to trigger extraction pulse, connect to RIGOL external trigger
               "ttl12",
               "ttl13",
               "sampler0"
              ]

    arguments = {'update_cycle': NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1),
                 'number_of_datapoints': NumberValue(default=5000,unit=' ',scale=1,ndecimals=0,step=1), #how many data points on the plot, run experiment & pulse counting
                 'number_of_bins': NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1) #how many indices you have in time axis, pulse counting
                }
    
    datasets = [{'args': ['optimize.result.count_tot', [-100]*self.number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 in pusle counting
                {'args': ['optimize.result.count_PI',[-10]*self.number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 in shutter optimize
                {'args': ['optimize.result.count_ROI',[-2]*self.number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 with ROI in optimize
                {'args': ['optimize.result.countrate_ROI',[-2]*self.number_of_datapoints],
                 'kwargs': dict(broadcast=True)}, # Number of pulses sent to ttl2 with ROI in optimize without accumulating
                {'args': ['optimize.result.bin_times', [-1]*0], 
                 'kwargs': dict(broadcast=True)} #self.number_of_bins*self.number_of_datapoints,broadcast=True) # Small bins for histogram
               ]

    # for i in ['Grid', 'Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']:
        #     self.set_dataset(key="optimize.multipoles."+i, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["bl"]:
        #     for j in ["1","2","3","4","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["br"]:
        #     for j in ["1","2","3","4","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["tl"]:
        #     for j in ["1","2","3","4","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # for i in ["tr"]:
        #     for j in ["1","2","3","4","5"]:
        #         self.set_dataset(key="optimize.e."+i+j, value=np.float32(0), broadcast=True, persist=True)
        # # self.set_dataset(key="optimize.e.btr4", value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.t0", value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.b0", value=np.float32(0), broadcast=True, persist=True)
        # self.set_dataset(key="optimize.e.trigger_level", value=np.float32(0), broadcast=True, persist=True)
        
        # # flags: indicating changes from GUI, 1 = there is change that needs to be implemented
        # self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True) # electrode voltages
        # self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True) # experiment parameters
        # self.set_dataset(key="optimize.flag.stop", value = 0, broadcast=True, persist=True) # whether or not terminate the experiment
        # self.set_dataset(key="optimize.flag.run_mode", value = np.int(0), broadcast=True, persist=True) # run mode,0: pulse counting, 1: ROI counting (pulse 390), 2: histogram counting (pulse 390)
        
        # # parameters: t_load(us),t_wait(ns),t_delay(ns), t_acquisition(ns),pulse_counting_time(ms), trigger_level (V), # repetitions, # datapoints
        # self.set_dataset(key="optimize.parameter.t_load", value = np.int(200), broadcast=True, persist=True) # t_load(us)
        # self.set_dataset(key="optimize.parameter.t_wait", value = np.int(100), broadcast=True, persist=True) # t_wait(ns)
        # self.set_dataset(key="optimize.parameter.t_delay", value = np.int(450), broadcast=True, persist=True) # t_delay(ns)
        # self.set_dataset(key="optimize.parameter.t_acquisition", value = np.int(600), broadcast=True, persist=True) # t_acquisition(ns)
        # self.set_dataset(key="optimize.parameter.pulse_counting_time", value = np.int(500), broadcast=True, persist=True) # pulse_counting_time(ms)
        # self.set_dataset(key="optimize.parameter.trigger_level", value = 0.03, broadcast=True, persist=True) # trigger level (V)
        # self.set_dataset(key="optimize.parameter.number_of_repetitions", value = np.int(1000), broadcast=True, persist=True) # number of repetitions
        # self.set_dataset(key="optimize.parameter.number_of_datapoints", value = np.int(100000), broadcast=True, persist=True) # number of datapoints
        # self.set_dataset(key="optimize.parameter.bins", value = np.int(50), broadcast=True, persist=True) # number of bins in the histogram
        # self.set_dataset(key="optimize.parameter.update_cycle", value = np.int(10), broadcast=True, persist=True) # number of datapoints per update cycle
        
    parameters = dict(pin_matching = {"bl1":21,"bl2":22,"bl3":11,"bl4":24,"bl5":25,"br1":6,"br2":17,"br3":13,"br4":15,"br5":14,"tl1":8,"tl2":10,"tl3":16,"tl4":12,"tl5":23,"tr1":18,"tr2":4,"tr3":3,"tr4":2,"tr5":1,"t0":9,"b0":20,"trigger_level":0},
                      gnd = [5,7,19,21,22,11,24,25,6,17,13,15,14,8,23,18,1,9,20], # gnd pins
                      np = 10, # number of experiment parameters
                      controlled_electrodes = ["tl2","tl3","tl4","tr2","tr3","tr4","trigger_level"],
                      controlled_multipoles = ["Grid","Ex","Ey","Ez","U2","U3","U4"],
                      #controlled_electrodes = ["tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5","t0","br1","br2","br3","br4","br5","bl1","bl2","bl3","bl4","bl5","b0","trigger_level"],
                      #controlled_multipoles = ["Grid","Ex","Ey","Ez","U1","U2","U3","U4","U5","U6"],
                      controlled_parameters = ["t_load","t_wait","t_delay","t_acquisition","pulse_counting_time","trigger_level","number_of_repetitions","number_of_datapoints","bins","update_cycle"],
                      old_c_file = False,
                      c_file_csv = '/home/electron/artiq/electron/cfile_etrap_gen2_6electrodes_U1U5_uncontrol.csv',
                      controlled_multipoles_dict = {"Grid":'Grid: (V)',"Ex":'Ex:', "Ey":'Ey:', "Ez":'Ez:', "U1":'U1:', "U2":'U2:', "U3":'U3:', "U4":'U4:', "U5":'U5:', "U6":'U6:'},
                      controlled_parameters_dict = {"t_load":'Load time (us):', "t_wait":'Wait time (ns):', "t_delay":'Delay time (ns):',"t_acquisition":'Acquisition time(ns):' , "pulse_counting_time":'Pulse counting time (ms):',"trigger_level":'Trigger level (V):',"number_of_repetitions":'# Repetitions:', "number_of_datapoints":'# Datapoints:', "bins":'# Bins:',"update_cycle":'# Update cycles:'},
                      controlled_electrodes_dict = ["tl1","tl2","tl3","tl4","tl5","tr1","tr2","tr3","tr4","tr5","t0","br1","br2","br3","br4","br5","bl1","bl2","bl3","bl4","bl5","b0","trigger_level"],
                      ne = int(len(self.controlled_electrodes)), # number of electrodes
                      run_mode = 0, # 0: pulse counting, 1: ROI counting (pulse 390), 2: histogram counting (pulse 390), 3: only outputting pulses and dacs
                      bins = 50, # bin number for histogram
                      update_cycle = 10, # how many datapoints per user_update_check (takes about 500 ms)
                    )

    