import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QPlainTextEdit, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, QGridLayout
from PyQt5.QtGui import QIcon
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
import time
import numpy as np

def print_underflow():
    print('RTIO underflow occured')
    
def input_voltage():
    return input("Enter desired output voltage: ") == "1"

class GUI(QWidget):
    
    def get_electrode_values(self):
        # Create multipole list of floats
        self.mul_list = []
        for i in range(len(self.multipoles)):
            self.mul_list.append(float(self.multipoles[i].text()))
           
        # Calculate and print electrode values
        self.m=np.array([self.mul_list]).T
        self.c=np.array([np.array(xi) for xi in self.C_Matrix])
        self.e = self.c@self.m   
        
        #for i in range(len(self.e)):
            #print(f'electrode value E{i+1} : ', self.e[i])
        
    
    def __init__(self):  
        # Initialize GUI
        super().__init__()
        self.title='DAC Control'
        self.left=10
        self.top=10
        self.width=640
        self.height=480
        self.initUI()
        self.program_continue = False
        #self.e=0
        
    def initUI(self):
        # Set geometry
        self.setWindowTitle(self.title)
        self.setGeometry(self.left,self.top,self.width,self.height)
        grid = QGridLayout()  
        self.setLayout(grid)
        
        
        # Labels for textentry
        MULTIPOLES = ['U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U8', 'U9']
    
        self.multipoles = []
        for i in range(len(MULTIPOLES)):
            
            textbox = QLineEdit(self)
            grid.addWidget(textbox,i,1,1,1)
            self.multipoles.append(textbox)
            
            label = QLabel(MULTIPOLES[i], self)
            grid.addWidget(label,i,0,1,1)
        
        # add voltage button
        v_button = QPushButton('Set Multipole Values', self)
        v_button.clicked.connect(self.on_click)
        grid.addWidget(v_button, 0, 3)
        
        # add c-file button
        c_button = QPushButton('Select C-file', self)
        c_button.clicked.connect(self.openFileDialog)
        grid.addWidget(c_button, 1, 3)
        self.show()
    
    
    def on_click(self):
        
        self.clicked_object = 'test'
        
        self.get_electrode_values()
        self.program_continue = True
        
        
    def openFileDialog(self):
        # open file navigation
        self.textedit = QPlainTextEdit()
        filename = QFileDialog.getOpenFileName(self,'Open File')
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
        for i in range(21):
            C_row = []
            for i in range(9):
                C_row.append(self.list_of_lists[curr_elt])
                curr_elt+=1
            self.C_Matrix.append(C_row)
            

class DAC_Control(EnvExperiment):

    def make_gui(self):

        app=QApplication(sys.argv)
        ex=GUI()
        app.exec_()

        #send values to electrodes
        delay(500*us)
        for i in range(21):      
            self.zotino0.write_dac(i,ex.e[i])
        self.zotino0.load()

        sys.exit(app.exec_())

    
    def build(self):  
        
        self.setattr_device('core')
        self.setattr_device('zotino0')
 
    @kernel
    def run(self):
        self.core.reset()
        self.zotino0.init()

        self.make_gui()


        
        
    
    
    