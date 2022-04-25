from artiq.experiment import *
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QComboBox, QGridLayout, QLineEdit, QPlainTextEdit
import select
from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
from datetime import datetime
import time
import os
import sys
import csv

class Shutter(EnvExperiment):
    def build(self): 
        self.setattr_device("core")                
        self.setattr_device("ttl12")  # sending ttl to shutter motor servo 390
        self.setattr_device("ttl13")  # sending ttl to shutter motor servo 422
        self.setattr_argument('pulse_width',NumberValue(default=100,unit='ms',scale=1,ndecimals=2,step=1))
        self.setattr_argument('laser',) 

        
        
    def prepare(self):
        pass


    def run(self):



    @kernel
    def rotate_390(self):
        self.core.reset()                          
        self.core.break_realtime()                  
        self.ttl12.off()   
        self.ttl12.pulse(self.pulse_width*ms)
        delay(20*ms)
        self.ttl12.pulse(self.pulse_width*ms)


    @kernel
    def rotate_422(self):
        self.core.reset()                          
        self.core.break_realtime()                  
        self.ttl13.off()   
        self.ttl13.pulse(self.pulse_width*ms)
        delay(20*ms)
        self.ttl13.pulse(self.pulse_width*ms)





