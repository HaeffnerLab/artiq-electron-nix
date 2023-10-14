# Creating tab widgets
class MyTabWidget(HasEnvironment,QWidget):
    
    def __init__(self, Env, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.HasEnvironment = Env
        self.controlled_electrodes = self.HasEnvironment.controlled_electrodes
        self.controlled_multipoles = self.HasEnvironment.controlled_multipoles
        self.controlled_parameters = self.HasEnvironment.controlled_parameters
        self.controlled_multipoles_dict = self.HasEnvironment.controlled_multipoles_dict
        self.controlled_parameters_dict = self.HasEnvironment.controlled_parameters_dict
        self.controlled_electrodes_dict = self.HasEnvironment.controlled_electrodes_dict
        self.old_c_file = self.HasEnvironment.old_c_file
        self.c_file_csv = self.HasEnvironment.c_file_csv

        self.setup_UI()
        self.ne = self.HasEnvironment.ne
        self.e=np.full(self.ne, 0.0)



    
    def set_dac_voltages(self):#,dac_vs):
        self.HasEnvironment.set_dac_voltages()#dac_vs)

    def setup_UI(self):
  
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()
        self.tab7 = QWidget()
        self.tabs.resize(300, 150)
  
        # Add tabs
        # self.tabs.addTab(self.tab2, "MULTIPOLES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        # self.tabs.addTab(self.tab3, "PARAMETERS")
        self.tabs.addTab(self.tab4, "Main Experiment") # This tab could mutate dac_voltage, parameters, flags dataset and run_self_updated
        self.tabs.addTab(self.tab1, "ELECTRODES") # This tab could mutate dac_voltage datasets and update voltages (not integrated)
        self.tabs.addTab(self.tab5, "DEVICES")
        self.tabs.addTab(self.tab7, "RS")
        self.tabs.addTab(self.tab6, "Cryostat")
    
          
        '''
        ELECTRODES TAB
        '''
        grid1 = QGridLayout()  
        self.ELECTRODES = ["DC0","DC1","DC2","DC3","DC4","DC5","DC6","DC7","DC8"]  # Labels for text entry
        xcoord_labels = [0,0,0,0,0,0,0,0,0]
        xcoord_entrys = [1,1,1,1,1,1,1,1,1]
        ycoords = [0,1,2,3,4,5,6,7,8]

        
        self.electrode_spin = {}
        
        #electrode grid
        for i in range(9):            
            
            
            xcoord_label = xcoord_labels[i]
            xcoord_entry = xcoord_entrys[i]
            ycoord = ycoords[i]
            
            spin = QtWidgets.QDoubleSpinBox(self)
            spin.setRange(-10,10)
            spin.setSingleStep(0.01)
            spin.setDecimals(4)
            # spin.setValue(self.default_voltages[index_v]) # set default values
            # index_v += 1
            grid1.addWidget(spin,ycoord,xcoord_entry,1,1)
            # self.electrodes.append(spin)
            self.electrode_spin[self.ELECTRODES[i]] = spin
            label = QLabel('       '+self.ELECTRODES[i], self)
            label.setAlignment(QtCore.Qt.AlignRight)
            grid1.addWidget(label,ycoord,xcoord_label,1,1)
    
        

        # add textbox color
        for el in self.electrode_spin.values():
            el.editingFinished.connect(lambda el=el: self.change_background(el))
       
        # add voltage button
        v_button = QPushButton('Set Voltage values (only mutate the dataset)', self)
        v_button.clicked.connect(self.on_voltage_click)
        grid1.addWidget(v_button, 0, 6, 2, 1)

        # add voltage button
        v_button = QPushButton('Load Individual Voltage values', self)
        v_button.clicked.connect(self.on_load_individual_voltage_click)
        grid1.addWidget(v_button, 1, 6, 2, 1)


        
        #add grid layout (grid1) to tab1
        grid1.setRowStretch(4, 1)
        self.tab1.setLayout(grid1)
        
        #set electrode values for dataset
        self.e=self.electrode_spin
    

        '''
        MAIN EXPERIMENT TAB
        '''
        grid4 = QGridLayout() #make grid layout
        
        self.parameter_spin = {}  
        #create parameter text entry boxes
        # self.default = [100,100,600,100,500,0.3,1000,1000,50,10] # default values
        self.default_parameter = self.get_default_parameter() # read data from dataset
        
        # PARAMETERS1 = ['Load time (us):', 'Wait time (ns):', 'Delay time (ns):','Acquisition time(ns):' , 'Pulse counting time (ms):']
        # DEFAULTS1 = self.default_parameter[0:5] # default values
        i = 0
        for p in self.controlled_parameters:  
            spin = QtWidgets.QDoubleSpinBox(self)
            if p == "trigger_level":
                spin.setRange(0,5)
                spin.setSingleStep(0.01)
                spin.setDecimals(4)
            else:
                spin.setRange(-10000000,10000000)
                spin.setSingleStep(10)
            spin.setValue(self.default_parameter[p]) # set default values
            self.parameter_spin[p] = spin
            label = QLabel('    '+self.controlled_parameters_dict[p], self)
            if i < int(len(self.controlled_parameters)/2):
                grid4.addWidget(spin,i+12,1,1,1)
                grid4.addWidget(label,i+12,0,1,1)
            else:
                grid4.addWidget(spin,i-int(len(self.controlled_parameters)/2)+12,5,1,1)
                grid4.addWidget(label,i-int(len(self.controlled_parameters)/2)+12,4,1,1)  
            i += 1

          
        #spacing
        label_gap = QLabel('', self)
        grid4.addWidget(label_gap,0,2,1,2)



    
        #[values (from list), x-coord (label), x-coord (entrtyBox), y-coord (first entry)]
        self.ELECTRODES = ["DC0","DC1","DC2","DC3","DC4","DC5","DC6","DC7","DC8"]  # Labels for text entry
        xcoord_labels = [0,0,0,0,0,0,0,0,0]
        xcoord_entrys = [1,1,1,1,1,1,1,1,1]
        ycoords = [0,1,2,3,4,5,6,7,8]

        self.electrode_labels = {}     
        # get default electrode voltages
        self.default_voltages = self.get_default_voltages()
        #electrode grid
        for i in range(len(self.ELECTRODES)):  
            xcoord_label = xcoord_labels[i]
            xcoord_entry = xcoord_entrys[i]
            ycoord = ycoords[i]  
            label = QLabel('       '+ self.ELECTRODES[i], self)
            label.setAlignment(QtCore.Qt.AlignRight)
            grid4.addWidget(label,ycoord,xcoord_label, 1,1)
            # label0 = QLabel('0.00', self)
            label0 = QLabel(str(self.default_voltages[self.ELECTRODES[i]]), self)
            self.electrode_labels[self.ELECTRODES[i]] = label0
            label0.setStyleSheet("border: 1px solid black;")
            grid4.addWidget(label0,ycoord,xcoord_entry,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid4.addWidget(label_gap,5,1,1,1)

        #create multipole text entry boxes
        self.multipole_spin = {}
        self.default_multipoles = self.get_default_multipoles()
        i = 0
        for m in self.controlled_multipoles:  
            spin = QtWidgets.QDoubleSpinBox(self)
            spin.setDecimals(4)
            if m == 'Grid':
                spin.setRange(-1000,3000)
            else:
                spin.setRange(-10,10)
            spin.setSingleStep(0.01)
            spin.setValue(self.default_multipoles[m])
            grid4.addWidget(spin,i,8,1,1)
            self.multipole_spin[m] = spin
            label = QLabel(self.controlled_multipoles_dict[m], self)
            label.setAlignment(QtCore.Qt.AlignRight)
            grid4.addWidget(label,i,7,1,1)
            i += 1


        # from left to right, top to bottom : 11,7 -> 16,7, 11,8 -> 16,8

        # add update dataset button, this is to update the dataset from the user set values in GUI
        v_button = QPushButton('Update Dataset', self)
        v_button.clicked.connect(self.on_update_dataset_click)
        grid4.addWidget(v_button, 12, 7)

        # add load multipole voltage button, this is to update the dataset and load the voltages
        self.lm_button = QPushButton('Load Multipole Voltages', self)
        self.lm_button.clicked.connect(self.on_load_multipole_voltages_click)
        grid4.addWidget(self.lm_button, 13, 7)

        # add c-file button, this is to load c file
        c_button = QPushButton('Load C-file', self)
        c_button.clicked.connect(self.openFileDialog)
        grid4.addWidget(c_button, 14, 7)

        # add make hist button, this is to populate the histogram dataset based on bin times dataset for plotting histogram in applet
        hist_button = QPushButton('Make histogram', self)
        hist_button.clicked.connect(self.HasEnvironment.make_hist)
        grid4.addWidget(hist_button, 17, 7)


        self.lifetime_button = QPushButton('Run Lifetime Optimize', self)
        self.lifetime_button.clicked.connect(self.on_lifetime_optimize_click)
        grid4.addWidget(self.lifetime_button, 12, 8)


        # add pulse counting button, this is to set run_mode = 0 and run the kernel pulse counting
        self.pc_button = QPushButton('Run Pulse Counting', self)
        self.pc_button.clicked.connect(self.on_pulse_counting_click)
        grid4.addWidget(self.pc_button, 12, 9)


        # add ROI counting button, this is to set run_mode = 1 and run the kernel ROI counting
        self.rc_button = QPushButton('Run ROI Counting', self)
        self.rc_button.clicked.connect(self.on_roi_counting_click)
        grid4.addWidget(self.rc_button, 13, 9)

        # # add ROI counting button, this is to set run_mode = 1 and run the kernel ROI counting
        # self.rc_button = QPushButton('Run ROI with trap freq', self)
        # self.rc_button.clicked.connect(self.on_roi_trap_freq_click)
        # grid4.addWidget(self.rc_button, 14, 9)

        # add hist counting button, this is to set run_mode = 2 and run the kernel histogram counting
        self.hc_button = QPushButton('Run Hist Counting', self)
        self.hc_button.clicked.connect(self.on_hist_counting_click)
        grid4.addWidget(self.hc_button, 13, 8)

        # add hist counting button, this is to set run_mode = 2 and run the kernel histogram counting
        self.op_button = QPushButton('Run Outputting', self)
        self.op_button.clicked.connect(self.on_outputting_click)
        grid4.addWidget(self.op_button, 14, 8)

        # add lifetime measurement button, this is to set run_mode = 4 and run the kernel histogram counting
        self.lm_button = QPushButton('Lifetime Measurement', self)
        self.lm_button.clicked.connect(self.on_lifetime_measurement_click)
        grid4.addWidget(self.lm_button, 15, 9)

        # add stop button, this is to terminate the current run program on the kernel and reset the dataset
        t_button = QPushButton('Terminate', self)
        t_button.clicked.connect(self.on_terminate_click)
        grid4.addWidget(t_button, 16+1, 8)

        grid4.setRowStretch(4, 1)
        self.tab4.setLayout(grid4)


        '''
        DEVICE TAB
        '''
        grid5 = QGridLayout() #make grid layout
        
        self.device_parameter_list = []  
        # rigol_PARAMETERS = ['Pulse width (ns):', 'Pulse delay (ns):','Offset (V):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):']
        rigol_PARAMETERS = ['Ejection pulse width (ns):', 'Pulse delay (ns):','Offset (V)(= -Amplitude/2):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):'] # make it to be less confusing
        rigol_DEFAULTS = [100, 100, -5, 10, 0,1000,2]

        for i in range(len(rigol_PARAMETERS)):  
            spin = QtWidgets.QSpinBox(self)
            spin.setRange(-1E6,1E9)
            spin.setSingleStep(10)
            spin.setValue(rigol_DEFAULTS[i]) # set default values
            grid5.addWidget(spin,i+11,1,1,1)
            self.device_parameter_list.append(spin)
            label = QLabel('    '+rigol_PARAMETERS[i], self)
            grid5.addWidget(label,i+11,0,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid5.addWidget(label_gap,0,2,1,2)
        
        # add extraction button
        v_button = QPushButton('Run Rigol Extraction', self)
        v_button.clicked.connect(self.on_run_rigol_extraction_click)
        grid5.addWidget(v_button, 8+2, 8)

        grid5.setRowStretch(4, 1)
        self.tab5.setLayout(grid5)


        '''
        RS
        '''
        grid6 = QGridLayout() #make grid layout
        
        self.device_parameter_list_RS = []  
        # rigol_PARAMETERS = ['Pulse width (ns):', 'Pulse delay (ns):','Offset (V):',  'Amplitude (V):', 'Phase:','Burst period (ns):','Sampling time (ns):']
        RS_PARAMETERS = ['Frequency:', 'Amplitude:'] # make it to be less confusing
        RS_DEFAULTS = [1e6, -20]
        self.rs_param = RS_DEFAULTS

        for i in range(len(RS_PARAMETERS)):  
            spin = QtWidgets.QSpinBox(self)
            spin.setRange(-1E6,1E9)
            spin.setSingleStep(10)
            spin.setValue(RS_DEFAULTS[i]) # set default values
            grid6.addWidget(spin,i+11,1,1,1)
            self.device_parameter_list_RS.append(spin)
            label = QLabel('    '+RS_PARAMETERS[i], self)
            grid6.addWidget(label,i+11,0,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid6.addWidget(label_gap,0,2,1,2)
        
        # add extraction button
        v_button = QPushButton('Run RS Extraction', self)
        v_button.clicked.connect(self.on_run_RS_click)
        grid6.addWidget(v_button, 8+2, 8)

        grid6.setRowStretch(4, 1)
        self.tab7.setLayout(grid6)


        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)        
        return

    def on_run_RS_click(self):
        self.rs = RS()
        self.dev_list = []
        for m in self.device_parameter_list_RS:
            text = m.text() or "0"
            self.dev_list.append(float(text))
        freq = self.dev_list[0]
        amp = self.dev_list[1]
        self.rs.run(freq, amp)

    def on_run_rigol_extraction_click(self):
        self.dev_list = []
        for m in self.device_parameter_list:
            text = m.text() or "0"
            self.dev_list.append(float(text))
        pulse_width_ej = self.dev_list[0]*1e-9
        pulse_delay_ej = self.dev_list[1]*1e-9
        offset_ej = self.dev_list[2]
        amplitude_ej = self.dev_list[3]
        phase = self.dev_list[4]
        period_ej = self.dev_list[5]*1e-9
        sampling_time = self.dev_list[6]*1e-9

        #uncomment
        # self.rigol101 =  rigol(101,pulse_width_ej,pulse_delay_ej,offset_ej,amplitude_ej,phase,period_ej,sampling_time)

        self.rigol113 =  rigol(113,pulse_width_ej,pulse_delay_ej,offset_ej,amplitude_ej,phase,period_ej,sampling_time)

        #uncomment
        # self.rigol101.run()

        self.rigol113.run()

    def on_update_dataset_click(self):
        self.update_parameters()
        self.update_multipoles()
        

    def on_load_multipole_voltages_click(self):
        self.on_update_dataset_click()
        # self.e.append(self.HasEnvironment.get_dataset(key="optimize.parameter.trigger_level"))       
        self.set_dac_voltages()
        # print("on_multipole_click has updated voltages and mutated datasets")

    def on_voltage_click(self):
        # Create electrode list of floats
        self.elec_dict = {}
        for e in self.electrode_spin:
            text = self.electrode_spin[e].text() or "0"
            self.elec_dict[e] = float(text)
        
        self.elec_dict["trigger_level"] = self.HasEnvironment.get_dataset(key="optimize.parameter.trigger_level")
        print(self.elec_dict)
        # # #after adjusting self.e order, same as pin order: [ bl1,...,bl5,br1,...,br5,tl1,...,tl5,tr1,..,tr5,b0(grid),t0]
        self.mutate_dataset_electrode()


    def on_load_individual_voltage_click(self):
        self.elec_dict = {}
        for e in self.electrode_spin:
            text = self.electrode_spin[e].text() or "0"
            self.elec_dict[e] = float(text)
        
        self.elec_dict["trigger_level"] = self.HasEnvironment.get_dataset(key="optimize.parameter.trigger_level")
        print(self.elec_dict)
        # # #after adjusting self.e order, same as pin order: [ bl1,...,bl5,br1,...,br5,tl1,...,tl5,tr1,..,tr5,b0(grid),t0]
        self.mutate_dataset_electrode()
        self.HasEnvironment.set_individual_electrode_voltages(self.elec_dict)

    def on_terminate_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.stop",1, broadcast=True, persist=True)
        return

    def on_pulse_counting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",0, broadcast=True, persist=True)
        self.on_run_click()

    def on_roi_counting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",1, broadcast=True, persist=True)
        self.on_run_click()

    def on_hist_counting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",2, broadcast=True, persist=True)
        self.on_run_click()

    def on_outputting_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",3, broadcast=True, persist=True)
        self.on_run_click()

    def on_lifetime_measurement_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",4, broadcast=True, persist=True)
        self.on_run_click()

    def on_lifetime_optimize_click(self):
        self.HasEnvironment.set_dataset("optimize.flag.run_mode",5, broadcast=True, persist=True)
        self.on_run_click()


    def on_run_click(self):
        self.thread = QThread() # create a QThread object
        self.worker = Worker(self.long_run_task) # create a worker object
        self.worker.moveToThread(self.thread) # move worker to the thread
        # connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)
        self.thread.start() # start the thread
        # final resets
        self.lm_button.setEnabled(False)
        self.rc_button.setEnabled(False)
        self.hc_button.setEnabled(False)
        self.op_button.setEnabled(False)
        self.pc_button.setEnabled(False)
        self.lm_button.setEnabled(False)
        self.lifetime_button.setEnabled(False)

        self.thread.finished.connect(
            lambda: self.lm_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.rc_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.hc_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.pc_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.op_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.lm_button.setEnabled(True)
            )
        self.thread.finished.connect(
            lambda: self.lifetime_button.setEnabled(True)
            )

    def long_run_task(self):
        self.HasEnvironment.set_dataset("optimize.flag.stop",0, broadcast=True, persist=True)
        self.on_update_dataset_click()
        self.on_run_rigol_extraction_click()
        self.HasEnvironment.core.reset()
        self.HasEnvironment.rolling_run()
        return

    
    def get_default_voltages(self):
        default = {}
        for e in self.controlled_electrodes_dict:
            if e == "trigger_level":
                default[e] = self.HasEnvironment.get_dataset(key="optimize.parameter."+e)
            else:
                default[e] = self.HasEnvironment.get_dataset(key="optimize.e."+e)
        return default

    def get_default_parameter(self):
        default = {}
        for p in self.controlled_parameters_dict:
            default[p] = self.HasEnvironment.get_dataset(key="optimize.parameter."+p)
        return default

    def get_default_multipoles(self):
        default = {}
        for m in self.controlled_multipoles:
            # default.append(0)
            default[m] = self.HasEnvironment.get_dataset("optimize.multipoles."+m)
        return default


    def update_multipoles(self):
        
        # Create multiple list of floats
        self.mul_dict = {}
        
        for m in self.multipole_spin:
            text = self.multipole_spin[m].text() or "0"
            self.mul_dict[m] = float(text)

    
        for m in self.controlled_multipoles:
            self.HasEnvironment.set_dataset("optimize.multipoles."+m, self.mul_dict[m], broadcast=True, persist=True)
       
        
        if not self.old_c_file:
            df = pd.read_csv(self.c_file_csv,index_col = 0)
            voltages = pd.Series(np.zeros(len(self.controlled_electrodes)-1),index = df.index.values)
            # grid_m = {'C': 0.019940897983726433,'Ey': -3.360905574255682e-05,'Ez': 0.00022449376590844223,'Ex': 0.06399536424651765,'U3': 0.13434433573433666,'U4': 0.0011390387152830977,'U2': 0.03015271954151855,'U5': -0.021575389610886914,'U1': 0.050389617844847405}
            # V_grid = self.mul_dict["Grid"]
            # print("V_grid:",V_grid)
            # for m in self.controlled_multipoles:   
            #     if m == "Grid":
            #         pass
            #     else:
            #         self.mul_dict[m] = self.mul_dict[m] - grid_m[m]*V_grid/150
            #         # voltages += df[m] * self.mul_dict[m]
            print("Multipoles:",self.mul_dict)
            for m in self.controlled_multipoles:   
                if m == "Grid":
                    pass
                else:
                    # self.mul_dict[m] = self.mul_dict[m] - grid_m[m]*V_grid
                    voltages += df[m] * self.mul_dict[m]
            self.elec_dict = voltages.to_dict()
            self.elec_dict["trigger_level"] = self.parameter_dict["trigger_level"]
            for e in self.elec_dict:
                self.elec_dict[e] = round(self.elec_dict[e],3)    
            print(self.elec_dict)

            for e in self.controlled_electrodes:
                if e == "trigger_level":
                    pass
                else:
                    self.electrode_labels[e].setText(str(round(self.elec_dict[e],3)))      
            self.mutate_dataset_electrode()


        else:
            self.mul_list = []
            for m in self.HasEnvironment.controlled_multipoles[1:]:
                self.mul_list.append(self.mul_dict[m])
            
            # Calculate and print electrode values
            try:
                
                self.m=np.array([self.mul_list])
                self.grid_multipole_150V = np.array([0.0203082,0.00042961,-0.00124763,-0.047735,-0.00441363,0.00081879,0.00012903,-0.03539802,-0.00083521])
                self.grid_multipole_150V = self.grid_multipole_150V[0:len(self.HasEnvironment.controlled_multipoles)-1]
                grid_multipole = [g*grid_V/150 for g in self.grid_multipole_150V]
                self.m=self.m-grid_multipole
                self.e=np.matmul(self.m, self.C_Matrix_np)
            except:
                f = open('/home/electron/artiq-nix/electron/Cfile_3layer.txt','r')
                # create list of lines from selected textfile
                self.list_of_lists = []
                for line in f:
                    stripped_line = line.strip()
                    line_list = stripped_line.split()
                    self.list_of_lists.append(float(line_list[0]))
                    
                # create list of values from size 21*9 C-file
                curr_elt = 0
                self.C_Matrix = []
                for i in range(len(self.HasEnvironment.controlled_multipoles)-1):
                    C_row = []
                    for i in range(self.ne-1): #-1 because of the channel 0 for trigger level
                        C_row.append(self.list_of_lists[curr_elt])
                        curr_elt+=1
                    self.C_Matrix.append(C_row) 
                    
                self.C_Matrix_np = np.array(self.C_Matrix)
                self.m=np.array([self.mul_list])
                #print(shape(self.m))
                # grid_V = 150
                self.grid_multipole_150V = np.array([0.0203082,0.00042961,-0.00124763,-0.047735,-0.00441363,0.00081879,0.00012903,-0.03539802,-0.00083521])
                self.grid_multipole_150V = self.grid_multipole_150V[0:len(self.HasEnvironment.controlled_multipoles)-1]
                grid_multipole = [g*grid_V/150 for g in self.grid_multipole_150V]
                self.m=self.m-grid_multipole
                self.e=np.matmul(self.m, self.C_Matrix_np)
                
            for i in range(len(self.e[0])):
                if self.e[0][i]>=self.HasEnvironment.max_voltage:
                    print(f'warning: voltage {round(self.e[0][i],3)}  exceeds limit')
                    self.e[0][i]=self.HasEnvironment.max_voltage
                elif self.e[0][i]<=-self.HasEnvironment.max_voltage:
                    print(f'warning: voltage {round(self.e[0][i],3)} exceeds limit')
                    self.e[0][i]=-self.HasEnvironment.max_voltage

            self.e = self.e[0].tolist()
            #self.e.append(self.e.pop(10))      
            for i in range(len(self.e)):
                self.e[i]=round(self.e[i],3)
            print("self.e:",self.e)

            

            
            #self.e is in alphabetical order as in c file: [bl1,...,bl5,br1,...,br5, tg("grid"),tl1,...,tl5,tr1,..,tr5]
            self.elec_dict={'bl1':self.e[0],'bl2':self.e[1],'bl3':self.e[2],'bl4':self.e[3],'bl5':self.e[4],'br1':self.e[5],'br2':self.e[6],'br3':self.e[7],'br4':self.e[8],'br5':self.e[9],'tg':self.e[10],'tl1':self.e[11],'tl2':self.e[12],'tl3':self.e[13],'tl4':self.e[14],'tl5':self.e[15],'tr1':self.e[16],'tr2':self.e[17],'tr3':self.e[18],'tr4':self.e[19],'tr5':self.e[20]}
            # print(self.elec_dict)
            

            for e in self.electrode_labels:
                self.electrode_labels[e].setText(str(round(self.elec_dict[e],3)))      
            self.mutate_dataset_electrode()
       

    def mutate_dataset_electrode(self):
        for e in self.elec_dict:
            self.HasEnvironment.set_dataset("optimize.e."+e,self.elec_dict[e], broadcast=True, persist=True)
        self.HasEnvironment.set_dataset("optimize.flag.e",1, broadcast=True, persist=True)


    def update_parameters(self):
        self.parameter_dict = {}
        for p in self.parameter_spin:
            m = self.parameter_spin[p]
            text = m.text() or str(self.default_parameter[p])
            self.parameter_dict[p] = float(text)
        self.mutate_dataset_parameters()
        self.HasEnvironment.set_dataset("optimize.flag.p",1, broadcast=True, persist=True)
        # print("update_parameters has mutated dataset")

    def mutate_dataset_parameters(self):
        for p in self.parameter_dict:
            self.HasEnvironment.set_dataset(key="optimize.parameter."+p,value = self.parameter_dict[p], broadcast=True, persist=True)

        
    def openFileDialog(self):
        
        # create list of lines from dataset
        #self.list_of_lists = [-1.512326312102017623e+00,1.637941648087839042e+01,-2.304713098445680952e+00,4.188495113946148507e+01,-1.808897796925718948e+00,1.422206623834767758e-01,3.921182615775121860e+01,1.025963357992092817e+01,2.264705463741543312e+01,-2.360850721028599608e+00,-1.895921784207670271e+02,-7.648869380779895755e-01,2.690463378718400733e+01,5.920669516490001172e+01,4.943331910064007673e+01,-1.107648341966514183e+00,2.773790806348027660e-01,5.090354436109951308e+01,6.115483000423661508e+01,2.884358204769423750e+01,-1.605923921094738471e+00,-5.511533629856346650e-01,-1.250094470782944001e+01,-2.523380065533868399e-01,1.364501006265611061e+01,6.337975904091774915e-01,-5.480274437008441080e-01,-1.245780766135806950e+01,-2.286003102594457437e-01,1.360866409448358638e+01,6.327547911920178292e-01,-3.581946332944305200e-01,-7.840193523786034291e-01,-1.250454759590978959e+01,-1.352301122949902124e-01,1.357806762434341152e+01,7.405668850198696695e-01,-7.820502094663634995e-01,-1.245920669079553988e+01,-1.315495203521160894e-01,1.353916763714750005e+01,7.396254978812962788e-01,-1.001784083043502985e-02,1.749003805973549097e+00,1.416105840153299411e+01,2.349319628607441146e+00,4.075482545269065726e-02,3.065805231873156012e-02,-1.725189274673949003e+00,-1.415274385706719862e+01,-2.320799656347184214e+00,-7.420901469804227352e-03,-1.119376892950579155e-01,1.929492144214527485e-02,2.054620140324989741e+00,1.525123613966764680e+01,2.724594031293268603e+00,5.153221867133202239e-02,4.094843007809051069e-03,-2.004372950912953311e+00,-1.518251428157990013e+01,-2.674585566944683190e+00,-1.848882493866542756e-02,4.427532075829812563e-02,8.042836776307868973e-01,2.950966392151396445e+00,8.813158696214824506e-01,5.415755296136771924e-02,5.112540161328654048e-02,8.988133916930655110e-01,3.002984734310525372e+00,8.016679970913439535e-01,5.187238232761943318e-02,-7.849409969514320462e-01,-9.739010458369092016e-03,-5.308815076084497653e-01,-2.880086903674786036e+00,-3.787437517912086715e-01,1.466480792631248004e-02,-5.423867636373652310e-03,-4.315222990769136402e-01,-2.872021323566237960e+00,-4.639884536766597511e-01,1.260186981834057925e-02,1.104387857448935861e+00,1.414190511080105850e+01,-6.903196031951223333e+00,1.434398252363142490e+01,1.231685905914327472e+00,1.093640837035562141e+00,1.399594276745827059e+01,-6.968179365203829967e+00,1.447137949024534187e+01,1.235291190060973765e+00,1.228843073661495255e+00,1.177207796745266322e+00,1.324438949879065319e+01,-7.117337983139794488e+00,1.282549463442225246e+01,1.370263617803965994e+00,1.170461529642176757e+00,1.309120659785244634e+01,-7.112284368120354472e+00,1.296207663271408883e+01,1.373533700803296398e+00,-5.665926477634710245e+00,-6.788983420775350908e+01,3.912332929695216399e-01,6.802030265346905935e+01,1.266426079420123196e+00,4.997696544746094816e+00,6.810992431655101598e+01,-5.068732646262870123e-01,-6.769403352277257113e+01,-2.375654562875646025e+00,5.527709148760519275e-02,-3.730374804048214532e+00,-7.631695682031620720e+01,1.806400857676365712e+00,6.783939892248946535e+01,1.087870016205992885e+00,2.991802337819332802e+00,7.611659304759672295e+01,-1.769582802804737787e+00,-6.793311253242865178e+01,-2.161400721059941521e+00,-6.067963966733943559e-01,-1.326802042886387056e+01,-1.007199728894146995e-01,1.352405994382151810e+01,7.080539093337696599e-01,-6.174106604108499097e-01,-1.341449509643709881e+01,-1.813228759133266310e-01,1.364747506008922606e+01,7.115948023984169923e-01,1.216273345726305299e+00,7.007152510876333285e-01,1.327939210304557527e+01,-3.598155512414831780e-01,-1.360567741897219562e+01,-6.643401944674592885e-01,6.940288973135760875e-01,1.312543408905663611e+01,-3.723132423312838779e-01,-1.347358996377454687e+01,-6.611436527600553781e-01,-1.498396939369385672e+00,4.775290053332635232e+00,-5.382571064047478870e+00,2.283210820570276312e+01,-1.715576131392834824e+00,-3.108692319523179148e-01,2.114886337596763255e+01,3.535544986357319619e+00,9.009750377985021430e+00,-2.111853164610799194e+00,-1.360612505558479768e+02,-9.897187636141845379e-01,1.254684322450274436e+01,3.865875789400611495e+01,2.886342341390053789e+01,-1.268976369146711303e+00,-2.417893517119287516e-01,2.975551776450667418e+01,3.995075842496849816e+01,1.406837578934314692e+01,-1.626807989492804696e+00,4.100607983092512815e-02,2.569968194327167499e+00,1.692203694724078389e+01,1.962548614527418467e+00,2.215096122618124760e-02,-1.827907786909331936e-02,-2.572890988440327931e+00,-1.689742564150423831e+01,-1.966051845797390119e+00,1.557339160813818110e-02,-4.614777135054736953e-03,-4.749955903610175549e-03,-2.279481596629263862e+00,-1.703984776866616002e+01,-2.871240313745817563e+00,-1.956369307675694461e-02,2.942840974861685860e-02,2.281398971963211952e+00,1.701854536599861234e+01,2.873040947197679440e+00,5.582624154462705740e-02]
        

        # open file navigation
        #self.textedit = QPlainTextEdit()
        filename = QFileDialog.getOpenFileName(parent=self, options=QtWidgets.QFileDialog.DontUseNativeDialog)

        if filename[0]:
            f = open(filename[0],'r')
        # create list of lines from selected textfile
        self.list_of_lists = []
        for line in f:
            stripped_line = line.strip()
            line_list = stripped_line.split()
            self.list_of_lists.append(float(line_list[0]))
            
        # create list of values from size 22*9 C-file
        curr_elt = 0
        self.C_Matrix = []
        for i in range(9):
            C_row = []
            for i in range(self.ne):
                C_row.append(self.list_of_lists[curr_elt])
                curr_elt+=1
            self.C_Matrix.append(C_row) 
            
        self.C_Matrix_np = np.array(self.C_Matrix)
    
    def keyPressEvent(self, qKeyEvent):
        #print(qKeyEvent.key())
        if qKeyEvent.key() == QtCore.Qt.Key_Return:
            
            if self.tabs.currentIndex() == 0:
                self.on_update_dataset_click()
            elif self.tabs.currentIndex() == 1:
                self.on_voltage_click()
            elif self.tabs.currentIndex() == 2:
                self.on_run_rigol_extraction_click()
        else:
            super().keyPressEvent(qKeyEvent)
                           

        

    def change_background(self, entry):

        if entry.text() == '':
            pass
        else:
            val = float(entry.text())
            a = np.abs(val/10)

            if val>0:
                r = 1
                b = 0
                col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),0,int(255*b))
                entry.setStyleSheet(f'QWidget {{background-color: {col};}}')
            elif val<0:
                r = 0
                b = 1
                col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),0,int(255*b))
                entry.setStyleSheet(f'QWidget {{background-color: {col};}}')
            elif val==0:
                r = 0
                b = 0
                entry.setStyleSheet(f'QWidget {{background-color: "white";}}')


    def change_background_labels(self):
        for label in self.all_labels:
            if label == False:
                label = 0
            if label.text() == '':
                pass
            else:
                val = float(label.text())
                a = np.abs(val/10)

                if val>0:
                    r = 1
                    b = 0
                elif val<0:
                    r = 0
                    b = 1
                elif val==0:
                    r = 0
                    b = 0
                col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),0,int(255*b))
                label.setStyleSheet(f'QWidget {{background-color: {col};}}')

