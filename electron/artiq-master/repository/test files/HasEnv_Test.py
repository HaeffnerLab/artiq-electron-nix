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

# '''
# Lets user use the gui to update the dataset and set dac voltages after click on set voltages button
# '''

class DummyEnv(HasEnvironment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0')

    def prepare(self):
        self.set_dataset(key="dac_voltages", value=np.zeros(21), broadcast=True)
    
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
        self.title = 'DAC Control'
        self.left = 0
        self.top = 0
        self.width = 600
        self.height = 200
        win.setWindowTitle(self.title)
        win.setGeometry(self.left, self.top, self.width, self.height)
        self.tab_widget = MyTabWidget(self,win)
        win.setCentralWidget(self.tab_widget)

    @ kernel
    def set_dac_voltages(self,dac_vs):
        self.core.reset()
        # self.core.break_realtime()
        self.zotino0.init()
        self.core.break_realtime() 
        for pin in range(len(dac_vs)):
            delay(500*us)
            self.zotino0.write_dac(pin,dac_vs[pin])       
        self.zotino0.load()

    # def get_artiq_dataset(self,k):
    #     delay(1000*us)
    #     print(self.get_dataset(key=k))
    #     return self.get_dataset(key=k)


# Creating tab widgets
class MyTabWidget(HasEnvironment,QWidget):
    
    def __init__(self, Env, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.HasEnvironment = Env
        self.setup_UI()
        self.e=np.full(21, 0.0)    
    

    def mutate_dataset(self,key,index,value):
        self.HasEnvironment.mutate_dataset(key=key, index=index, value=value)

    # def get_artiq_dataset(self,k):
        # self.HasEnvironment.get_artiq_dataset(k)

    def set_dac_voltages(self,dac_vs):
        self.HasEnvironment.set_dac_voltages(dac_vs)

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
        for n in ['tl', 'tr', 'tg', 'bl', 'br']:
            self.electrode_sec = [] #electrode sections
            if n=='tg':
                self.electrode_sec.append(n)
            else:
                for i in range(1,6):
                    ei = n + f'{i}:'
                    self.electrode_sec.append(ei)
            self.ELECTRODES.append(self.electrode_sec)
        self.ELECTRODES.append('tg:')
        self.ELECTRODES.append('p2:')

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
        
        #tg
        textbox_tg = QLineEdit(self)
        grid1.addWidget(textbox_tg,1,3,1,1)
        textbox_tg.setPlaceholderText("0.0")
        self.electrodes.append(textbox_tg)
        label_tg = QLabel(self.ELECTRODES[2][0], self)
        grid1.addWidget(label_tg,1,2,1,1)

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
        
        #tg
        label_tg = QLabel(self.ELECTRODES[2][0], self)
        grid2.addWidget(label_tg,1,2,1,1)
        self.label0_tg = QLabel('0', self)
        self.label0_tg.setStyleSheet("background-color:yellow;  border: 1px solid black;")
        grid2.addWidget(self.label0_tg,1,3,1,1)
        
       
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
        self.textedit = QPlainTextEdit()
        filename = QFileDialog.getOpenFileName(parent=self, options=QtWidgets.QFileDialog.DontUseNativeDialog)
        if filename[0]:
            f = open(filename[0],'r')
        
        # create list of lines from selected textfile
        self.list_of_lists = []
        for line in f:
            stripped_line = line.strip()
            line_list = stripped_line.split()
            self.list_of_lists.append(float(line_list[0]))
            
        # create list of values from size 21*9 C-file
        curr_elt = 0
        self.C_Matrix = []
        for i in range(9):
            C_row = []
            for i in range(21):
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
        self.m=np.array([self.mul_list])
        self.e = np.matmul(self.m, self.C_Matrix_np)
            
        for i in range(len(self.e[0])):
            if self.e[0][i]>=10:
                print(f'warning: voltage {round(self.e[0][i],3)}  exceeds limit')
                self.e[0][i]=10
            elif self.e[0][i]<=-10:
                print(f'warning: voltage {round(self.e[0][i],3)} exceeds limit')
                self.e[0][i]=-10
    
        curr = 0
        for label in self.all_labels:
            if curr == 10:
                curr+=1          
            label.setText(str(round(self.e[0][curr],3)))
            curr+=1
        self.label0_tg.setText(str(round(self.e[0][10],3)))    
        
        self.e = self.e[0].tolist()
        self.e.append(self.e.pop(10))       
        for i in range(len(self.e)):
            self.e[i]=round(self.e[i],3)
    
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



class DAC_Control(DummyEnv, EnvExperiment):#, object):
    def build(self):
        DummyEnv.build(self)
        # self.setattr_device('core')
        # self.setattr_device('zotino0')

    def prepare(self):
        DummyEnv.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        self.core.reset()
        self.zotino0.init()
        initial_dataset = np.zeros(21)
        for i in range(10):
            # delay(10*s)
            self.voltages = self.get_dataset(key="dac_voltages")
            print(self.voltages)
            if not np.array_equal(initial_dataset,self.voltages):
                for pin in range(len(self.voltages)):
                    delay(500*us)
                    self.zotino0.write_dac(pin,self.voltages[pin])       
                self.zotino0.load()
                print("updated voltages")
            initial_dataset = self.voltages

