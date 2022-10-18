class ElectronBase(HasEnvironment):
    def build(self, config_name='Electron'):
        self.config = getattr(config, config_name)
        if hasattr(self.config, 'devices')
            devices_names = self.config.devices
        else:
            print(">>> Devices not configured properly!")
            exit(1)
        
        for device in devices_names:
            self.setattr_device(device)
        
        if hasattr(self.config, 'arguments')
            args = self.config.arguments
        else:
            args = {}
            print(">>> WARNING: No arguments is configured!")

        for arg_name in args:
            self.setattr_argument(arg_name, args[arg_name])


    def prepare(self):
        # results:
        if hasattr(self.config, 'datasets'):
            datasets = self.config.datasets
            for dataset in datasets:
                args, kwargs = dataset['args'], dataset['kwargs']
                self.set_dataset(*args, **kwargs)
        else:
            print(">>> WARNGING: Datasets not configured!")


        if hasattr(self.config, 'parameters'):
            params = self.config.parameters
            for param_name in params:
                setattr(self, param_name, params[param_name])
        else:
            print(">>> WARNING: Parameters not configured!")

    
    def launch_GUI(self):       
        #launch GUI
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        MainWindow = QtWidgets.QMainWindow()
        self.setupUi(MainWindow) 
        MainWindow.show()
        ret = app.exec_()


    def run(self):
        return


    def setupUi(self, win):
        self.title = 'Electron GUI'
        self.left = 0
        self.top = 0
        self.width = 1200 # 600
        self.height = 600 # 200
        win.setWindowTitle(self.title)
        win.setGeometry(self.left, self.top, self.width, self.height)
        self.tab_widget = MyTabWidget(self,win)
        win.setCentralWidget(self.tab_widget)


    def rolling_run(self):
        self.loadDACoffset()
        self.get_dac_vs()
        self.get_parameter_dict()
        self.get_run_mode()
        if self.run_mode == 4:
            self.kernel_run_lifetime_measurement()
            return
        number_of_datapoints = np.int(self.parameter_dict["number_of_datapoints"])
        self.update_cycle = np.int(self.parameter_dict["update_cycle"])
        self.count_tot = 0
        self.count_bins = 0      
        for i in range(int(number_of_datapoints/self.update_cycle)):
            self.load_dac = False
            self.index = i
            if not self.check_user_update():
                return
            if self.run_mode == 0:
                self.kernel_run_pulse_counting()
            elif self.run_mode == 1:
                self.kernel_run_ROI_counting()
            elif self.run_mode == 2:
                self.kernel_run_hist_counting()
            elif self.run_mode == 3:
                self.kernel_run_outputting()


    def get_run_mode(self):
        self.run_mode = np.int32(self.get_dataset(key="optimize.flag.run_mode"))


    def get_dac_vs(self):
        dac_vs = {}
        self.dac_pins = []
        self.dac_pins_voltages = []
        for e in self.controlled_electrodes:
            if e == "trigger_level":
                dac_vs[e] = self.get_dataset(key="optimize.parameter.trigger_level")
                self.dac_pins.append(self.pin_matching[e])
                self.dac_pins_voltages.append(self.get_dataset(key="optimize.parameter.trigger_level"))
            else:
                dac_vs[e] = self.get_dataset(key="optimize.e."+e)
                self.dac_pins.append(self.pin_matching[e])
                self.dac_pins_voltages.append(self.get_dataset(key="optimize.e."+e))
        self.dac_vs = dac_vs


    def get_parameter_dict(self):
        self.parameter_name_list = []
        self.parameter_value_list = []
        parameter_dict = {}
        for p in self.controlled_parameters:
            # parameter_list.append(np.int(self.get_dataset(key="optimize.parameter."+i)))
            parameter_dict[p] = self.get_dataset(key="optimize.parameter."+p)
            self.parameter_name_list.append(p)
            self.parameter_value_list.append(parameter_dict[p])
        self.parameter_dict = parameter_dict
        self.get_parameter_list()


    def get_parameter_list(self):
        t_load_index = self.parameter_name_list.index("t_load")
        t_wait_index = self.parameter_name_list.index("t_wait")
        t_delay_index = self.parameter_name_list.index("t_delay")
        t_acquisition_index = self.parameter_name_list.index("t_acquisition")
        number_of_repetitions_index = self.parameter_name_list.index("number_of_repetitions")
        number_of_datapoints_index = self.parameter_name_list.index("number_of_datapoints")
        pulse_counting_time_index = self.parameter_name_list.index("pulse_counting_time")

        t_load = np.int32(self.parameter_value_list[t_load_index])
        t_wait = np.int32(self.parameter_value_list[t_wait_index])
        t_delay = np.int32(self.parameter_value_list[t_delay_index])
        t_acquisition = np.int32(self.parameter_value_list[t_acquisition_index])
        number_of_repetitions = np.int32(self.parameter_value_list[number_of_repetitions_index])
        number_of_datapoints = np.int32(self.parameter_value_list[number_of_datapoints_index])
        pulse_counting_time = np.int32(self.parameter_value_list[pulse_counting_time_index])
        self.ordered_parameter_list = [t_load,t_wait,t_delay,t_acquisition,number_of_repetitions,number_of_datapoints,pulse_counting_time]

        return [t_load,t_wait,t_delay,t_acquisition,number_of_repetitions,number_of_datapoints,pulse_counting_time]


    #TODO: exist difference from 3-layer, ?dac_calibration_fit
    def loadDACoffset(self):
        # create list of lines from dataset
        f = '/home/electron/artiq/electron/zotino_offset.txt'
        tmp = np.loadtxt(f)
        offset = np.zeros((tmp.shape[0],tmp.shape[1]+1))
        for i in range(tmp.shape[0]):
            a = np.append(tmp[i],tmp[i][-1])
            offset[i] = a
        self.offset = offset


    def set_dac_voltages(self):
        #,dac_vs):
        self.loadDACoffset()
        self.get_dac_vs()
        # self.load_voltages()
        self.kernel_load_dac()


    def check_user_update(self):
        flag_dac = np.int32(self.get_dataset(key="optimize.flag.e"))
        flag_parameter = np.int32(self.get_dataset(key="optimize.flag.p"))
        flag_stop = np.int32(self.get_dataset(key="optimize.flag.stop"))
        if flag_stop == 1:
            if self.run_mode == 0:
                self.set_dataset('optimize.result.count_tot',[-100]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 in pusle counting
                # self.set_dataset('optimize.result.count_PI',[-10]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 in shutter optimize
                # for i in range(self.index*self.update_cycle):
                    # self.mutate_dataset('optimize.result.count_tot',i,-100)
                # print("Experiment terminated")
                return False
            elif self.run_mode == 1:
                self.set_dataset('optimize.result.count_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI in optimize
                self.set_dataset('optimize.result.countrate_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI in optimize without accumulating
                # for j in range(self.index*self.update_cycle):
                #     self.mutate_dataset('optimize.result.count_ROI',j,-2)
                #     self.mutate_dataset('optimzie.result.countrate_ROI',j,-2)
                # print("Experiment terminated")
                return False
            elif self.run_mode == 2:
                self.set_dataset('optimize.result.bin_times', [-1]*0,broadcast=True)
                # print("Experiment terminated")
                return False
            elif self.run_mode == 3:
                return False
        if flag_dac == 1:
            # load dac voltages
            self.get_dac_vs()
            self.load_dac = True
            self.set_dataset(key="optimize.flag.e", value = 0, broadcast=True, persist=True)
        if flag_parameter == 1:
            self.get_parameter_dict()
            self.set_dataset(key="optimize.flag.p", value = 0, broadcast=True, persist=True)
        return True
    

    #TODO: difference: offset value, related to prev DACOffset diff
    @ kernel
    def kernel_load_dac(self):
        
        self.core.reset()
        self.zotino0.init()
        self.core.break_realtime() 
        # for e in self.controlled_electrodes:
        #     delay(500*us)
        #     # print(self.pin_matching[e])
        #     self.zotino0.write_dac(self.pin_matching[e],self.dac_vs[e])
        #     index = 10+int(np.rint(self.dac_vs[e]))
        #     self.zotino0.write_offset(self.pin_matching[e],self.offset[self.pin_matching[e]][index])
        for i in range(len(self.dac_pins)):
            delay(500*us)
            # print(self.pin_matching[e])
            self.zotino0.write_dac(self.dac_pins[i],self.dac_pins_voltages[i])
            index = 10+int(np.rint(self.dac_pins_voltages[i]))
            self.zotino0.write_offset(self.dac_pins[i],self.offset[self.dac_pins[i]][index])
        for pin in self.gnd:
            delay(500*us)
            self.zotino0.write_dac(pin,0.0)
            index = 10
            self.zotino0.write_offset(pin,self.offset[pin][index])
        self.zotino0.load()
        print("Loaded dac voltages")


    @ kernel
    def set_individual_electrode_voltages(self,e):
        # self.core.reset()
        # self.zotino0.init()
        # self.core.break_realtime() 
        # for pin in range(self.ne):
        #     delay(500*us)
        #     self.zotino0.write_dac(self.pins[pin],e[pin])
        #     index = 10+int(np.rint(e[pin]))
        #     self.zotino0.write_offset(self.pins[pin],self.offset[self.pins[pin]][index])    
        # self.zotino0.load()
        # print("Loaded dac voltages")

        self.core.reset()
        self.zotino0.init()
        self.core.break_realtime() 
        for key in e:
            delay(500*us)
            self.zotino0.write_dac(self.pin_matching[key],e[key])
            index = 10+int(np.rint(e[key]))
            self.zotino0.write_offset(self.pin_matching[key],self.offset[self.pin_matching[key]][index])    
        self.zotino0.load()
        print("Loaded dac voltages")


    #TODO: need 'subclass' style config
    @ kernel
    def kernel_run_outputting(self):
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]
        
        # t_load = np.int32(self.parameter_dict["t_load"])
        # t_wait = np.int32(self.parameter_dict["t_wait"])
        # t_delay = np.int32(self.parameter_dict["t_delay"])
        # # t_acquisition = np.int32(self.parameter_dict[3])
        # # trigger_level = self.parameter_dict[5]
        # number_of_repetitions = np.int32(self.parameter_dict["number_of_repetitions"])
        # number_of_datapoints = np.int32(self.parameter_dict["number_of_datapoints"])

        if self.load_dac:
            self.kernel_load_dac()
            
        for k in range(self.update_cycle):
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(t_load*us)
                    self.ttl8.off()
                    delay(1500*ns) # get rid of the photo diode fall time
                    self.ttl9.on()  
                    delay(t_wait*ns)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                    # delay(1*us)
                    delay(t_delay*ns)

    #TODO: same as above
    @ kernel
    def kernel_run_ROI_counting(self):
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]
        
        if self.load_dac:
            self.kernel_load_dac()
            
        for k in range(self.update_cycle):
            countrate_tot = 0 
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay(t_wait*ns)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                        with sequential:
                            delay(t_delay*ns)
                            t_count = self.ttl2.gate_rising(t_acquisition*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    self.count_tot += count
                    countrate_tot += count
                    delay(1*us)
            self.mutate_dataset('optimize.result.count_ROI',self.index*self.update_cycle+k,self.count_tot)
            self.mutate_dataset('optimize.result.countrate_ROI',self.index*self.update_cycle+k,countrate_tot)


    @ kernel
    def kernel_run_hist_counting(self):
        self.core.reset() # this is important to avoid overflow error
        self.core.break_realtime()

        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]

        t_total = t_load*1000+t_wait+t_delay+t_acquisition+1000 # cycle duration (ns)
        gate_rising_time = t_total + 1000 # hard coded gate_rising_time for now

        if self.load_dac:
            self.kernel_load_dac()

        for k in range(self.update_cycle):
            for j in range(number_of_repetitions):
                self.core.break_realtime()
                t_start = now_mu()
                t_end = self.ttl2.gate_rising(gate_rising_time*ns) # somehow it only works if the gate_rising is within the loop    
                at_mu(t_start)
                self.ttl8.on()
                delay(t_load*us)   
                self.ttl8.off()
                delay(t_wait*ns) # negative t_wait cause it to output 6/10
                self.ttl10.pulse(200*ns)
                delay((t_delay+t_acquisition)*ns)
                delay(1*us)
            
                # Timestamp events
                tstamp = self.ttl2.timestamp_mu(t_end)
                while tstamp != -1:
                    timestamp = self.core.mu_to_seconds(tstamp)-self.core.mu_to_seconds(t_start)
                    timestamp_us = timestamp*1e6 # in ns scale for now
                    self.append_to_dataset('optimize.result.bin_times',timestamp_us)
                    tstamp = self.ttl2.timestamp_mu(t_end)
                    # delay(100*ns) 
            delay(100*ns)
            self.make_hist()


    def make_hist(self):

        hist_data = self.get_dataset("optimize.result.bin_times")
        self.bins = int(self.get_dataset("optimize.parameter.bins"))
        hist_data = np.array(hist_data)
        #np.save('/home/electron/Desktop/hist_data.npy', hist_data)
        #print("timestamp list:", hist_data)
        #range_timestamps = round(max(hist_data)) #us
        #self.set_dataset('optimize.result.bin_boundaries', np.arange(0,range_timestamps,1), broadcast=True)
        '''
        hist_final = [0]*(round(max(hist_data))+1)
        self.set_dataset('optimize.result.final_hist', hist_final, broadcast=True)


        # for n in hist_data:
        #     i = round(n)
        #     hist_final[i] += 1
        '''
        # a,b,c=plt.hist(hist_data,50)
        # a,b=np.histogram(hist_data[(hist_data > 1 ) & (hist_data<1000)],bins=50)      
        
        a,b=np.histogram(hist_data,bins=self.bins)           
        self.set_dataset('optimize.result.hist_ys', a, broadcast=True)
        self.set_dataset('optimize.result.hist_xs', b, broadcast=True)
        return 


    #TODO: ttl8 vs 16, difference?
    @kernel
    def kernel_run_pulse_counting(self):
        self.core.break_realtime()
        t_load = self.ordered_parameter_list[0]
        t_wait = self.ordered_parameter_list[1]
        t_delay = self.ordered_parameter_list[2]
        t_acquisition = self.ordered_parameter_list[3]
        number_of_repetitions = self.ordered_parameter_list[4]
        number_of_datapoints = self.ordered_parameter_list[5]
        pulse_counting_time = self.ordered_parameter_list[6]

        if self.load_dac:
            self.kernel_load_dac()

        if self.index == 0:
            self.ttl8.on() # AOM
        # self.core.break_realtime()
        for k in range(self.update_cycle):
            self.core.break_realtime()
            with parallel:
                t_count = self.ttl2.gate_rising(pulse_counting_time*ms)
                self.ttl10.pulse(2*us) # extraction pulse    
            count = self.ttl2.count(t_count)

            self.mutate_dataset('optimize.result.count_tot',self.index*self.update_cycle+k,count)


