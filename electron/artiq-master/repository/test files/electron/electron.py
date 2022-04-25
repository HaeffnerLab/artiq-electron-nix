from artiq.experiment import *
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QComboBox, QGridLayout, QLineEdit, QPlainTextEdit
import select
import time
import os
import sys
import csv

# from pulse_sequence import PulseSequence
# from electron_GUI import MyTabWidget, Ui_Dialog, Worker
from devices import rigol


class Electron(PulseSequence, EnvExperiment):#, object):
    def build(self):
        PulseSequence.build(self)

    def prepare(self):
        PulseSequence.prepare(self)
        self.launch_GUI() # if I put it in run function, this will keep getting underflow errors?
    
    @kernel
    def run(self):
        # self.launch_GUI()
        print("Hello World")




