from artiq.experiment import *
import numpy as np
from artiq.coredevice.ad9910 import AD9910, SyncDataEeprom
from artiq.coredevice.ad53xx import AD53xx
from artiq.master.databases import DeviceDB
from artiq.master.worker_db import DeviceManager
from datetime import datetime
import time
import os
import sys
import csv

class zotino_calibrator(EnvExperiment):
    def build(self): 
        self.setattr_device("core")                
        self.setattr_device("zotino0")  
        self.setattr_device("ttl18")
        self.setattr_argument('voltage',NumberValue(default=1,unit='V',scale=1,ndecimals=2,step=1))
        self.setattr_argument('zotino_channel',NumberValue(default=0,unit=' ',scale=1,ndecimals=0, step=1))
        self.setattr_argument("voltage_scan", BooleanValue(default=True))
        
    def prepare(self):
        # self.Vs = np.arange(-10,10,1)
        # self.Vs = [-10.0,-9.0,-8.0,-7.0,-6.0,-5.0,-4.0,-3.0,-2.0,-1.0,0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,9.9]
        # self.Vs = [-6.5,-6.0,-5.5,-5.0,-4.5,-4.0,-3.5,-3.0,-2.5,-2.0,-1.5,-1.0,-0.5,0.0,0.5,1.0, 1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0,5.5,6.0,6.5]
        # self.Vs = [-1.50000000e+00, -1.40000000e+00, -1.30000000e+00, -1.20000000e+00,-1.10000000e+00, -1.00000000e+00, -9.00000000e-01, -8.00000000e-01,-7.00000000e-01, -6.00000000e-01, -5.00000000e-01, -4.00000000e-01,-3.00000000e-01, -2.00000000e-01, -1.00000000e-01,  1.33226763e-15,1.00000000e-01,  2.00000000e-01,  3.00000000e-01,  4.00000000e-01,5.00000000e-01,  6.00000000e-01,  7.00000000e-01,  8.00000000e-01,9.00000000e-01,  1.00000000e+00,  1.10000000e+00,  1.20000000e+00,1.30000000e+00,  1.40000000e+00,  1.50000000e+00]
        # self.Vs = [2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2] 
        self.Vs = [-3. , -2.5, -2. , -1.5, -1. , -0.5,  0. ,  0.5,  1. ,  1.5,  2. ,
        2.5,  3. ]

    def run(self):
        # self.loadDACoffset()
        if self.voltage_scan:
            self.run_scan()
        else:
            self.run_once()


    @kernel
    def run_once(self):
        self.core.reset()
        self.core.break_realtime()                                          
        self.zotino0.init()
        for zotino_channel in range(32):
            delay(500*us) # avoid RTIO underflow error
            #if dac_vs[zotino_channel] < 10:
            self.zotino0.write_dac(zotino_channel,self.voltage)
            #index = 10+int(np.rint(self.voltage))
            #self.zotino0.write_offset(zotino_channel,self.offset[zotino_channel][index])    
        self.zotino0.load()
        print("done")
        # self.zotino0.write_offset_dacs_mu()

    @kernel
    def run_scan(self):
        self.core.reset()
        self.core.break_realtime()                                          
        self.zotino0.init()
        
        for i in range(len(self.Vs)):
            print(self.Vs[i])
            delay(100000*us) # avoid RTIO underflow error
            # print(self.Vs[i])
            self.zotino0.write_dac(self.zotino_channel,self.Vs[i])
            # index = 10+int(np.rint(self.Vs[i]))
            # self.zotino0.write_offset(self.zotino_channel,self.offset[self.zotino_channel][index])
            with parallel:
                self.zotino0.load()
                with sequential:
                    # delay(100*us)
                    self.ttl18.pulse(2000*us)
                    delay(10*us)
            delay(4*s)
            time.sleep(4)
        print("done scanning")
            # self.zotino0.write_offset_dacs_mu()

    def loadDACoffset(self):
        # create list of lines from dataset
        f = '/home/electron/artiq/electron/zotino_offset.txt'
        tmp = np.loadtxt(f)
        offset = np.zeros((tmp.shape[0],tmp.shape[1]+1))
        for i in range(tmp.shape[0]):
            a = np.append(tmp[i],tmp[i][-1])
            offset[i] = a
        self.offset = offset

        







