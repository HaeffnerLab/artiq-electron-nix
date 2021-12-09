import sys
import os
import select
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QPushButton, QAction, QLineEdit, QMessageBox, QLabel, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot
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
    return float(input("Enter desired output voltage: ") == "1")


class DAC_Control_old(EnvExperiment):
#class DAC_Control(QMainWindow):
    
    
    def build(self):
         self.setattr_device('core')
         self.setattr_device('zotino0')

    @kernel
    def run(self):
        self.core.reset()
        self.zotino0.init()
        
        # Uncomment if using CLI input
        v = 9
        
        delay(500*us)
        self.zotino0.write_dac(4,5)
        self.zotino0.load()
    
    '''
    def __init__(self):
        super().__init__()
        self.title = 'DAC Control'
        self.left = 10
        self.top = 10
        self.width = 400
        self.height = 180
        self.initUI()
    '''    
    
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        #create label 
        self.label=QLabel('voltage input', self)
        self.label.move(20,20)
    
        # Create textbox
        self.textbox = QLineEdit(self)
        self.textbox.move(20, 50)
        self.textbox.resize(280,40)
        
        # Create a button in the window
        self.v_button = QPushButton('Send to DAC', self)
        self.v_button.move(20,100)
        
        
        # C-file button
        self.c_button = QPushButton('Select C file', self)
        self.c_button.move(20, 130)
        
        
        # connect button to function on_click
        self.v_button.clicked.connect(self.on_click)
        self.show()
        
        self.c_button.clicked.connect(self.openFileDialog)
        self.show()

    
    
    

    def run_test(self, v):
        print('this is a run test: ', v)
    
    def on_click(self):
        textboxValue = self.textbox.text()
        self.run(float(textboxValue))
        
    def openFileDialog(self):
        filename = QFileDialog.getOpenFileName(self,'Open File')

        if filename[0]:
            f = open(filename[0],'r')

            with f:
                data = f.read()
                self.textedit.setText(data)
        
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DAC_Control()
    sys.exit(app.exec_())
