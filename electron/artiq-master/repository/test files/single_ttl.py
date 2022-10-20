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
from matplotlib import pyplot as plt

class single_ttl(EnvExperiment):
    def build(self):
        self.setattr_device('core')
        self.setattr_device('zotino0') # artiq DAC
        self.setattr_device('ttl11')
        self.setattr_device('ttl18')
        

        # self.setattr_argument('number_of_datapoints', NumberValue(default=5000,unit=' ',scale=1,ndecimals=0,step=1)) #how many data points on the plot, run experiment & pulse counting
        # self.setattr_argument('number_of_bins', NumberValue(default=10,unit=' ',scale=1,ndecimals=0,step=1)) #how many indices you have in time axis, pulse counting

    def prepare(self):
        pass

    @kernel
    def run(self):

        self.core.reset()
        self.core.break_realtime()
        # self.ttl11.on()
        # delay(1*s)

        self.ttl11.on()

        
        # self.zotino0.init()
        # delay(500*us)
        # self.zotino0.write_dac(4,0.01)
        # self.zotino0.load()
        # for i in range(2):
        #     # self.core.break_realtime()
        #     with parallel:
        #         self.ttl11.pulse(20*us)
        #         with sequential:
        #             delay(20*ns)
        #             #self.ttl18.pulse(20*ns)
        #     delay(10*us)
        