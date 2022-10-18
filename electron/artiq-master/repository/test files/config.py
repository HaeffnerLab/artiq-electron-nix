class Electron:
    """
    Configuration adapted from the GUI_test Electron object.
    """
    ## Environment Config ##

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

    ## GUI Config ##
    #[values (from list), x-coord (label), x-coord (entryBox), y-coord (first entry)]
    electrodes = {'bl': [0,0,1,4], 
                  'br': [1,4,5,4],
                  'b0': [7,3,1,1],
                  'tl': [3,0,1,10], 
                  'tr': [4,4,5,10],
                  't0': None
                 }
    electrode_sec = {'t0': {'Range': (-10, 10)
                            'SingleStep': 0.1,
                            'Decimals': 4,
                            'Coordinates': [1,3,1,1],
                            'Label': (2, 0),
                            'LabelCoord': (1, 2)
                           }, 
                     'b0': {'Range': (-10, 10)
                            'SingleStep': 0.1,
                            'Decimals': 4,
                            'Coordinates': [7,3,1,1],
                            'Label': (5, 0),
                            'LabelCoord': (7,2,1,1)
                            }
                    }

    