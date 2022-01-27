from artiq.experiment import *
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPlainTextEdit
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
import time
import os
import sys


class Electron(HasEnvironment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0')
        self.setattr_device('ttl2') # where MCP pulses are being sent in by ttl, connect to Q of threshold detector
        # self.setattr_device('ttl3') # where sync of extraction pulses are being sent in by ttl
        self.setattr_device('ttl8') # use this channel to trigger AOM, connect to VCO near AOM
        self.setattr_device('ttl9') # use this channel to trigger R&S for exciting motion, connect to R&S
        self.setattr_device('ttl10') # use this channel to trigger extraction pulse, connect to RIGOL external trigger
        self.setattr_device('ttl11') # use this channel to reset threshold detector, connect to reset of threshold detector
        

        # run experiment:
        self.setattr_argument('t_load',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # loading time
        self.setattr_argument('t_wait',NumberValue(default=100,unit='us',scale=1,ndecimals=0,step=1)) # wait time
        # self.setattr_argument('cycle_duration',NumberValue(default=500,unit='us',scale=1,ndecimals=2,step=1)) # half of the time length of one experiment cycle, notice it's only doing something in the first half
        self.setattr_argument('number_of_repetitions', NumberValue(default=1000,unit=' ',scale=1,ndecimals=0,step=1)) #how many experiment cycles per data point
        self.setattr_argument('number_of_datapoints', NumberValue(default=1000,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot
        # self.setattr_argument('detection_time',NumberValue(default=500,unit='ms',scale=1,ndecimals=0,step=1))
        self.setattr_argument('t_delay', NumberValue(default=600,unit='ns',scale=1,ndecimals=0,step=1)) # the delay between the extraction pulse and the MCP signal
        self.setattr_argument('time_window_width', NumberValue(default=100,unit='ns',scale=1,ndecimals=0,step=1)) # width of the detection time window
        self.setattr_device('scheduler') # scheduler used

        # pulse counting:
        self.setattr_argument('time_count', NumberValue(default=1000,unit='number of counts',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis
        self.setattr_argument('detection_time',NumberValue(default=500,unit='ms',scale=1,ndecimals=0,step=1))

        # threshold detector test:
        self.setattr_argument('trigger_level', NumberValue(default=0.3,unit='V',scale=1,ndecimals=2,step=1))



    def prepare(self):
        self.ne = 22 # number of electrodes
        self.set_dataset(key="dac_voltages", value=np.zeros(self.ne), broadcast=True) # Dac voltages
        self.set_dataset('count_tot',[-100]*self.time_count,broadcast=True) # Number of pulses sent to ttl2
        self.set_dataset('count_ROI',[-2]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 with ROI
        self.set_dataset('count_threshold',[-200]*self.number_of_datapoints,broadcast=True) # Number of pulses sent to ttl2 from threshold detector
    
    def launch_GUI(self):       
        #launch GUI
        app = QtWidgets.QApplication(sys.argv)
        MainWindow = QtWidgets.QMainWindow()
        self.setupUi(MainWindow) 
        MainWindow.show()
        ret = app.exec_()

    def run(self):
        print("HasEnvironment is running :)")
        
    def setupUi(self, win):
        self.title = 'Electron'
        self.left = 0
        self.top = 0
        self.width = 1200 # 600
        self.height = 400 # 200
        win.setWindowTitle(self.title)
        win.setGeometry(self.left, self.top, self.width, self.height)
        self.tab_widget = MyTabWidget(self,win)
        win.setCentralWidget(self.tab_widget)



    @ kernel
    def set_dac_voltages(self,dac_vs):

        # electrodes: [bl1,...,bl5,br1,...,br5,tl1,...,tl5,tr1,...,tr5,t0,b0]
        pins=[13,15,17,19,21,22,7,5,3,1,24,2,26,28,30,9,20,18,16,14,0,11] # Unused dac channels: 4,6,8,10,12,23,25,27,29,31

        self.core.reset()
        # self.core.break_realtime()
        self.zotino0.init()
        self.core.break_realtime() 
        for pin in range(self.ne):
            delay(500*us)
            self.zotino0.write_dac(pins[pin],dac_vs[pin]) 
            #i=i+1     
        self.zotino0.load()

    @kernel
    def pulse_counting(self):
        self.core.reset()
        # while loop continuously repopulates the graph
        while True:
            self.core.reset()
            self.ttl8.on() # AOM
            # with parallel:
            for j in range(self.time_count):
                self.core.break_realtime()
                with parallel:
                    self.ttl10.pulse(2*us) # extraction pulse
                    t_count = self.ttl2.gate_rising(self.detection_time*ms)
                self.mutate_dataset('count_tot',j,self.ttl2.count(t_count)/(self.detection_time*ms))
                # print(self.ttl2.count(now_mu()))
                # print(self.ttl2.count(t_count)/(self.detection_time*ms))

    @kernel
    def run_experiment(self):
        self.core.reset()
        count_tot = 0
        for i in range(self.number_of_datapoints):
            # count_tot = 0
            # count_ext = 0
            for j in range(self.number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(self.t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay(self.t_wait*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)
                        with sequential:
                            # t_extract = self.t_load + self.t_wait + t_delay
                            delay(self.t_delay*ns)
                            t_count = self.ttl2.gate_rising(self.time_window_width*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(1*us)
            # print(count_tot)
            # print(count_ext)
            cycle_duration = self.t_load+self.t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            # self.mutate_dataset('count_ROI',i,count_tot/(self.number_of_repetitions*cycle_duration*us))
            # self.mutate_dataset('count_ROI',i,count_tot/(self.number_of_repetitions*self.time_window_width*ns))
            self.mutate_dataset('count_ROI',i,count_tot)

    @kernel
    def threshold_detector_test(self): # zotino4 for trigger, zotino 6 give 3.3 V
        self.core.reset()
        count_tot = 0
        self.zotino0.init()
        delay(500*us)
        self.zotino0.write_dac(4,self.trigger_level)
        self.zotino0.write_dac(6,3.3)
        self.zotino0.load()

        for i in range(self.number_of_datapoints):
            for j in range(self.number_of_repetitions):
                self.core.break_realtime()
                with sequential:
                    self.ttl8.on()
                    delay(self.t_load*us)
                    with parallel:
                        self.ttl8.off()
                        self.ttl9.on()
                    delay((self.t_wait-2)*us)
                    with parallel:
                        delay(2*us)
                        self.ttl11.pulse(2*us)
                    with parallel:
                        self.ttl9.off()
                        self.ttl10.pulse(2*us)

                        with sequential:
                            # t_extract = self.t_load + self.t_wait + t_delay
                            delay(self.t_delay*ns)
                            t_count = self.ttl2.gate_rising(self.time_window_width*ns)
                    count = self.ttl2.count(t_count)
                    if count > 0:
                        count = 1
                    count_tot += count
                    delay(1*us)
            cycle_duration = self.t_load+self.t_wait+2+self.t_delay/1000+self.time_window_width/1000+1
            self.mutate_dataset('count_threshold',i,count_tot)




    def get_artiq_dataset(self,k):
        delay(1000*us)
        print(self.get_dataset(key=k))
        return self.get_dataset(key=k)



import vxi11
import matplotlib.pyplot as plt
# Control the rigol to give out extraction pulse

class rigol(HasEnvironment):
    def __init__(self):
        # self.sampling_time = sampling_time # 
        self.offset_ej = 0
        self.amplitude_ej = 20
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
 
        return


    '''
    rigol =  rigol()
    # parameters for the Rigol waveforms
    pulse_width_ej = 20.E-9
    pulse_delay_ej = 2.E-9
    rigol.run(pulse_width_ej, pulse_delay_ej)
    '''

# Creating tab widgets
class MyTabWidget(HasEnvironment,QWidget):
    
    def __init__(self, Env, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.HasEnvironment = Env
        self.setup_UI()
        self.ne = 22
        self.e=np.full(self.ne, 0.0)    
    

    def mutate_dataset(self,key,index,value):
        self.HasEnvironment.mutate_dataset(key=key, index=index, value=value)

    def set_dac_voltages(self,dac_vs):
        self.HasEnvironment.set_dac_voltages(dac_vs)


    # def get_artiq_dataset(self,k):
        # self.HasEnvironment.get_artiq_dataset(k)

    # def delay(self,time_in_us):
        # self.HasEnvironment.delay_kernel(time_in_us)

    def setup_UI(self):
  
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tabs.resize(300, 200)
  
        # Add tabs
        self.tabs.addTab(self.tab1, "ELECTRODES")
        self.tabs.addTab(self.tab2, "MULTIPOLES")
        
  
        '''
        ELECTRODES TAB
        '''

        grid1 = QGridLayout()  
        self.ELECTRODES = []  # Labels for text entry
        for n in ['tl', 'tr', 't0', 'bl', 'br', 'b0']:
            self.electrode_sec = [] #electrode sections
            if n=='t0' or n=='b0':
                ei = n + ":"
                self.electrode_sec.append(ei)
            else:
                for i in range(1,6):
                    ei = n + f'{i}:'
                    self.electrode_sec.append(ei)
            self.ELECTRODES.append(self.electrode_sec)
        self.ELECTRODES.append('t0:')
        self.ELECTRODES.append('b0:')

        print(self.ELECTRODES)

        self.electrodes = []
        
        #[values (from list), x-coord (label), x-coord (entrtyBox), y-coord (first entry)]
        self.bl_electrodes = [0,0,1,4] 
        self.br_electrodes = [1,4,5,4]
        self.tl_electrodes = [3,0,1,10]
        self.tr_electrodes = [4,4,5,10]

        
        #electrode grid
        for e in [self.tl_electrodes, self.tr_electrodes, self.bl_electrodes, self.br_electrodes]:            
            
            el_values = e[0]
            xcoord_label = e[1]
            xcoord_entry = e[2]
            ycoord = e[3]
            
        
            for i in range(len(self.ELECTRODES[el_values])):      
                textbox = QLineEdit(self)
                grid1.addWidget(textbox,ycoord-i,xcoord_entry,1,1)
                textbox.setPlaceholderText("0.0")
                self.electrodes.append(textbox)
                
                label = QLabel(self.ELECTRODES[el_values][i], self)
                grid1.addWidget(label,ycoord-i,xcoord_label,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid1.addWidget(label_gap,5,1,1,1)
        
        #t0
        textbox_t0 = QLineEdit(self)
        grid1.addWidget(textbox_t0,1,3,1,1)
        textbox_t0.setPlaceholderText("0.0")
        self.electrodes.append(textbox_t0)
        label_t0 = QLabel(self.ELECTRODES[2][0], self)
        grid1.addWidget(label_t0,1,2,1,1)

        #b0
        textbox_b0 = QLineEdit(self)
        grid1.addWidget(textbox_b0,7,3,1,1)
        textbox_b0.setPlaceholderText("0.0")
        self.electrodes.append(textbox_b0)
        label_b0 = QLabel(self.ELECTRODES[5][0], self)
        grid1.addWidget(label_b0,7,2,1,1)

        #ad textbox color
        for el in self.electrodes:
            el.editingFinished.connect(lambda el=el: self.change_background(el))
       
        # add voltage button
        v_button = QPushButton('Set Voltage values', self)
        v_button.clicked.connect(self.on_voltage_click)
        grid1.addWidget(v_button, 0, 6, 2, 1)
        
        #add grid layout (grid1) to tab1
        grid1.setRowStretch(4, 1)
        self.tab1.setLayout(grid1)
        
        #set electrode values for dataset
        self.e=self.electrodes
        
        '''
        MULTIPOLES TAB
        '''
        grid2 = QGridLayout() #make grid layout
        
        #[values (from list), x-coord (label), x-coord (entrtyBox), y-coord (first entry)]
        self.bl_electrodes0 = [0,0,1,4] 
        self.br_electrodes0 = [1,4,5,4]
        self.tl_electrodes0 = [3,0,1,10]
        self.tr_electrodes0 = [4,4,5,10]

        self.all_labels =[]        

        #electrode grid
        for e in [self.tl_electrodes0, self.tr_electrodes0, self.bl_electrodes0, self.br_electrodes0]:            
            
            el_values = e[0]
            xcoord_label = e[1]
            xcoord_entry = e[2]
            ycoord = e[3]
            
            for i in range(len(self.ELECTRODES[e[0]])):      
                label = QLabel(self.ELECTRODES[e[0]][i], self)
                grid2.addWidget(label,e[3]-i,e[1], 1,1)
                label0 = QLabel('0', self)
                self.all_labels.append(label0)
                label0.setStyleSheet("background-color:lightgreen;  border: 1px solid black;")
                grid2.addWidget(label0,e[3]-i,e[2],1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid2.addWidget(label_gap,5,1,1,1)
        
        #t0
        label_t0 = QLabel(self.ELECTRODES[2][0], self)
        grid2.addWidget(label_t0,1,2,1,1)
        self.label0_t0 = QLabel('0', self)
        self.label0_t0.setStyleSheet("background-color:yellow;  border: 1px solid black;")
        grid2.addWidget(self.label0_t0,1,3,1,1)

        
        #b0
        label_b0 = QLabel(self.ELECTRODES[5][0], self)
        grid2.addWidget(label_b0,7,2,1,1)
        self.label0_b0 = QLabel('0', self)
        self.label0_b0.setStyleSheet("background-color:yellow;  border: 1px solid black;")
        grid2.addWidget(self.label0_b0,7,3,1,1)
        

        #spacing  
        label_gap = QLabel('          ', self)
        grid2.addWidget(label_gap,1,6,1,1)
    
        #create multipole text entry boxes
        MULTIPOLES = ['Ex', 'Ey', 'Ez', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6']
        self.multipoles = []
        for i in range(len(MULTIPOLES)):  
            textbox = QLineEdit(self)
            grid2.addWidget(textbox,i,8,1,1)
            textbox.setPlaceholderText("0.0")
            self.multipoles.append(textbox)
            label = QLabel(MULTIPOLES[i], self)
            grid2.addWidget(label,i,7,1,1)
    
        # add voltage button
        v_button = QPushButton('Set Multipole Values', self)
        v_button.clicked.connect(self.on_multipoles_click)
        grid2.addWidget(v_button, 0, 9)
        
        # add c-file button
        c_button = QPushButton('Load C-file', self)
        c_button.clicked.connect(self.openFileDialog)
        grid2.addWidget(c_button, 1, 9)
        self.tab2.setLayout(grid2)
      
  
        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        
        
    def openFileDialog(self):
        '''
        Now this function just let us utilize the c-file that is copied down below
        Future improve idea: click this button let us load the c-file that is saved as a dataset in artiq, 
        so maybe get_dataset in this function, and mutate_dataset in the initialization of the gui, and 
        set_dataset in the main experiment or has environment?

        '''
        
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
               
            
    def on_voltage_click(self):
        # Create electrode list of floats
        self.el_list = []
        for i in self.electrodes:
            text = i.text() or "0"
            self.el_list.append(float(text))
        self.e=self.el_list
        for c in range(len(self.e)):
            self.mutate_dataset("dac_voltages", c, self.e[c])
        print("on_voltage_click has mutated dataset")
        # dac_vs = self.get_artiq_dataset("dac_voltages")
        # print("has got artiq dataset")
        # print(dac_vs)
        # self.delay(10000)
        self.set_dac_voltages(self.e)
        print("on_voltage_click has updated voltages")
        print(self.e)

        #print(self.e)
        # dummy_object = HasEnvironment()
        # self.mutate_dataset(key="dac_voltages", index=0, value=1)

    def on_multipoles_click(self):

    
        # Create multiple list of floats
        self.mul_list = []
        for m in self.multipoles:
            text = m.text() or "0"
            self.mul_list.append(float(text))
        
        # Calculate and print electrode values
        try:
            self.m=np.array([self.mul_list])
            self.e=np.matmul(self.m, self.C_Matrix_np)
        except:
            f = open('/home/electron/artiq/electron/Cfile.txt','r')
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
            self.m=np.array([self.mul_list])
            #print(shape(self.m))
            grid_multipole = np.array([0.00862239,0.00089517,0.0019013,-0.01988827,-0.01471916,0.0042531,0.00176647,0.00671031,0.00186274])
            
            self.m=self.m-grid_multipole
            self.e=np.matmul(self.m, self.C_Matrix_np)


            
        for i in range(len(self.e[0])):
            if self.e[0][i]>=10:
                print(f'warning: voltage {round(self.e[0][i],3)}  exceeds limit')
                self.e[0][i]=10
            elif self.e[0][i]<=-10:
                print(f'warning: voltage {round(self.e[0][i],3)} exceeds limit')
                self.e[0][i]=-10


        self.e = self.e[0].tolist()
        #self.e.append(self.e.pop(10))      
        for i in range(len(self.e)):
            self.e[i]=round(self.e[i],3)

        print('before changing order', self.e)


        #assuming electrode order is [tl1,...,tl5,bl1,...,bl5,tr1,...,tr5,br1,...,br5,t0,b0]
        #new order: [ bl1,...,bl5,br1,...,br5,b0,t0,tl1,...,tl5,tr1,..,tr5]

        self.elec_dict={'bl1':self.e[0],'bl2':self.e[1],'bl3':self.e[2],'bl4':self.e[3],'bl5':self.e[4],'br1':self.e[5],'br2':self.e[6],'br3':self.e[7],'br4':self.e[8],'br5':self.e[9],'b0':0.0,'t0':self.e[11],'tl1':self.e[12],'tl2':self.e[13],'tl3':self.e[14],'tl4':self.e[15],'tl5':self.e[16],'tr1':self.e[17],'tr2':self.e[18],'tr3':self.e[19],'tr4':self.e[20],'tr5':self.e[21]}
        print(self.elec_dict)

#print:before changing order [-0.148, -3.811, 2.036, -3.659, -0.144, -0.148, -3.833, 2.009, -3.639, -0.144, 0.537, 0.021, -0.111, -3.203, 0.181, -3.58, -0.131, -0.111, -3.222, 0.22, -3.555, 0.0]
#print:{'tl1': -0.148, 'tl2': -3.811, 'tl3': 2.036, 'tl4': -3.659, 'tl5': -0.144, 'bl1': -0.148, 'bl2': -3.833, 'bl3': 2.009, 'bl4': -3.639, 'bl5': -0.144, 'tr1': 0.537, 'tr2': 0.021, 'tr3': -0.111, 'tr4': -3.203, 'tr5': 0.181, 'br1': -3.58, 'br2': -0.131, 'br3': -0.111, 'br4': -3.222, 'br5': 0.22, 't0': -3.555, 'b0': 0.0}
#print:[-0.148, -3.833, 2.009, -3.639, -0.144, -3.58, -0.131, -0.111, -3.222, 0.22, -0.148, -3.811, 2.036, -3.659, -0.144, 0.537, 0.021, -0.111, -3.203, 0.181, -3.555, 0.0]
 
        for i in range(5):
            self.all_labels[i].setText(str(round(self.elec_dict['bl'+f'{1+i}'],3)))
            self.all_labels[5+i].setText(str(round(self.elec_dict['br'+f'{1+i}'],3)))
            self.all_labels[10+i].setText(str(round(self.elec_dict['tl'+f'{1+i}'],3)))
            self.all_labels[15+i].setText(str(round(self.elec_dict['tr'+f'{1+i}'],3)))
        self.label0_t0.setText(str(round(self.elec_dict['t0'],3)))
        self.label0_b0.setText(str(round(self.elec_dict['b0'],3)))

        self.e=[]
        for string in ['bl','br','tl','tr']:
            for i in range(5):
                self.e.append(self.elec_dict[string+f'{1+i}'])
        self.e.append(self.elec_dict['t0'])
        self.e.append(self.elec_dict['b0'])
        print(self.e)

        print(self.e)
        for c in range(len(self.e)):
            self.mutate_dataset("dac_voltages", c, self.e[c])
        print("on_multipole_click has mutated dataset")
        self.set_dac_voltages(self.e)
        print("on_multipole_click has updated voltages")

    def change_background(self, entry):
        if entry.text() == '':
            pass
        else:
            entry.setPlaceholderText("0.0")
            val = float(entry.text())
            a = np.abs(val/10)

            if val>0:
                r = 0
                g = 1
            elif val<0:
                r = 1
                g = 0
            elif val==0:
                r = 0
                g = 0
            col = '#{:02x}{:02x}{:02x}{:02x}'.format(int(255*a),int(255*r),int(255*g),0)
            entry.setStyleSheet(f'QWidget {{background-color: {col};}}')







class Electron_GUI(Electron, EnvExperiment):#, object):
    def build(self):
        Electron.build(self)

    def prepare(self):
        Electron.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        print("Hello World")