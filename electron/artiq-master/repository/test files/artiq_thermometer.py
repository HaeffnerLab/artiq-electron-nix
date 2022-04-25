from artiq.experiment import *
import time
import pandas as pd
import scipy
from scipy.interpolate import interp1d
import numpy as np

class Thermometer(EnvExperiment):
    def build(self): 
        self.setattr_device("core")                
        self.setattr_device("sampler1")  

        self.setattr_argument('time_interval',NumberValue(default=60,unit='s',scale=1,ndecimals=2,step=1)) 
        self.setattr_argument('number_of_datapoints', NumberValue(default=240,unit='#',scale=1,ndecimals=0,step=1)) #how many data points on the plot
        self.setattr_argument('gain',NumberValue(default=0,unit='',scale=1,ndecimals=0,step=1)) 
        
        
    def prepare(self):
        self.set_dataset('cryo.Voltage1',[0]*self.number_of_datapoints,broadcast=True)
        self.set_dataset('cryo.Voltage2',[0]*self.number_of_datapoints,broadcast=True)
        self.set_dataset('cryo.Temp1',[0]*self.number_of_datapoints,broadcast=True)
        self.set_dataset('cryo.Temp2',[0]*self.number_of_datapoints,broadcast=True)


    '''
    def run(self):
        if self.number_of_datapoints == 1:
            self.sample_once()
        else:
            # data = pd.read_csv('DT-600 Standard Curve Interpolation Table.txt',sep='   ',header=1,names=['Temp','Voltage','Sensitivity'])
            # Temp = data['Temp'].tolist()
            # Voltage = data['Voltage'].tolist()
            Temp = [1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.2, 4.4, 4.6, 4.8, 5.0, 5.2, 5.4, 5.6, 5.8, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 42.0, 44.0, 46.0, 48.0, 50.0, 52.0, 54.0, 56.0, 58.0, 60.0, 65.0, 70.0, 75.0, 77.35, 80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0, 150.0, 155.0, 160.0, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0, 200.0, 205.0, 210.0, 215.0, 220.0, 225.0, 230.0, 235.0, 240.0, 245.0, 250.0, 255.0, 260.0, 265.0, 270.0, 273.15, 275.0, 280.0, 285.0, 290.0, 295.0, 300.0, 305.0, 310.0, 315.0, 320.0, 325.0, 330.0, 335.0, 340.0, 345.0, 350.0, 355.0, 360.0, 365.0, 370.0, 375.0, 380.0, 385.0, 390.0, 395.0, 400.0, 405.0, 410.0, 415.0, 420.0, 425.0, 430.0, 435.0, 440.0, 445.0, 450.0, 455.0, 460.0, 465.0, 470.0, 475.0, 480.0, 485.0, 490.0, 495.0, 500.0]
            Voltage = [1.64429, 1.64299, 1.64157, 1.64003, 1.63837, 1.6366, 1.63472, 1.63274, 1.63067, 1.62852, 1.62629, 1.624, 1.62166, 1.61928, 1.61687, 1.61445, 1.612, 1.60951, 1.60697, 1.60438, 1.60173, 1.59902, 1.59626, 1.59344, 1.59057, 1.58764, 1.58465, 1.57848, 1.57202, 1.56533, 1.55845, 1.55145, 1.54436, 1.53721, 1.53, 1.52273, 1.51541, 1.49698, 1.47868, 1.46086, 1.44374, 1.42747, 1.41207, 1.39751, 1.38373, 1.37065, 1.3582, 1.34632, 1.33499, 1.32416, 1.31381, 1.3039, 1.29439, 1.28526, 1.27645, 1.26794, 1.25967, 1.25161, 1.24372, 1.23596, 1.2283, 1.2207, 1.21311, 1.20548, 1.197748, 1.181548, 1.162797, 1.140817, 1.125923, 1.119448, 1.115658, 1.11281, 1.110421, 1.108261, 1.106244, 1.104324, 1.102476, 1.100681, 1.09893, 1.097216, 1.095534, 1.093878, 1.092244, 1.090627, 1.089024, 1.085842, 1.082669, 1.079492, 1.076303, 1.073099, 1.069881, 1.06665, 1.063403, 1.060141, 1.056862, 1.048584, 1.040183, 1.031651, 1.027594, 1.022984, 1.014181, 1.005244, 0.996174, 0.986974, 0.97765, 0.968209, 0.958657, 0.949, 0.939242, 0.92939, 0.919446, 0.909416, 0.899304, 0.889114, 0.878851, 0.868518, 0.85812, 0.847659, 0.837138, 0.82656, 0.815928, 0.805242, 0.794505, 0.78372, 0.772886, 0.762007, 0.751082, 0.740115, 0.729105, 0.718054, 0.706964, 0.695834, 0.684667, 0.673462, 0.662223, 0.650949, 0.639641, 0.628302, 0.621141, 0.61693, 0.605528, 0.594097, 0.582637, 0.571151, 0.559639, 0.548102, 0.536542, 0.524961, 0.513361, 0.501744, 0.490106, 0.478442, 0.46676, 0.455067, 0.443371, 0.43167, 0.41996, 0.408237, 0.396503, 0.384757, 0.373002, 0.361235, 0.349453, 0.337654, 0.325839, 0.314008, 0.302161, 0.290298, 0.278416, 0.266514, 0.254592, 0.242653, 0.230697, 0.21873, 0.206758, 0.194789, 0.182832, 0.170901, 0.15901, 0.147191, 0.13548, 0.123915, 0.112553, 0.101454, 0.090681]
            T_v = interp1d(Voltage,Temp,'linear')
            self.initialize()        
            for i in range(self.number_of_datapoints):
                V1,V2 = self.sample(i)
                try:
                    self.mutate_dataset('Temp1',i,T_v(V1))
                    self.mutate_dataset('Temp2',i,T_v(V2))
                    print(str(i)+"th Voltage1:"+str(V1)+"V, "+str(i)+"th Temp1:"+str(T_v(V1))+"K")
                    print(str(i)+"th Voltage2:"+str(V2)+"V, "+str(i)+"th Temp2:"+str(T_v(V2))+"K")
                except:
                    print("Voltage out of range")
                    print(i,"th Voltage1:",V1)
                    print(i,"th Voltage2:",V2)
    '''

    @kernel
    def sample(self,i):
        self.core.break_realtime()
        n_channels = 8                              #sets number of channels to read off of
        smp = [0.0]*n_channels                      #creates list of floating point variables
        delay(1*ms)
        n_channels = 8                              #sets number of channels to read off of
        for i in range(n_channels):
            self.sampler1.set_gain_mu(i, self.gain)         #sets each channel's gain to 0db
        self.sampler1.sample(smp)                   #runs sampler and saves to list
        self.mutate_dataset('cryo.Voltage1',i,smp[0])
        self.mutate_dataset('cryo.Voltage2',i,smp[1])
        delay(self.time_interval*s)
        return smp[0],smp[1]





    @kernel
    def run(self):
        self.core.reset()                          
        self.core.break_realtime()                  
        self.sampler1.init()   
        # self.sampler0.set_gain_mu(0, 0)         #sets each channel's gain to 0db
        delay(500*us)                           #100us delay
        n_channels = 8                              #sets number of channels to read off of
        for i in range(n_channels):
            self.sampler1.set_gain_mu(i, self.gain)         #sets each channel's gain to 0db
        smp = [0.0]*n_channels                      #creates list of floating point variables                      
        delay(1*ms)

        N=1000
        n=0
        tot=0.0
        while n<N:
            delay(1*ms)
            self.sampler1.sample(smp)
            #delay(10*ms)
            
            tot = tot+smp[0]

            n=n+1
            #for i in range(len(smp)):
                #print("after sample:", smp[i]) #prints each it
        avg_v = tot/(N)
        offset =  1.0385 #1.0351298906587802

        average_adjusted = (avg_v)*offset

        print("average =", avg_v)
        print("average (calibrated) =", average_adjusted)

        self.mutate_dataset('cryo.Voltage1', 0, average_adjusted)
        #volt_list = np.array(HasEnvironment.get_dataset('cryo.Voltage1'))
        #print(volt_list)

    @kernel
    def initialize(self):
        self.core.reset()                          
        self.core.break_realtime()                  
        self.sampler1.init()   
        # self.sampler0.set_gain_mu(0, 0)         #sets each channel's gain to 0db
        delay(500*us)



    # @kernel
    # def run(self):

    #     if self.number_of_datapoints == 1:
    #         self.core.reset()                          
    #         self.core.break_realtime()                  
    #         self.sampler0.init()   
    #         # self.sampler0.set_gain_mu(0, 0)         #sets each channel's gain to 0db
    #         delay(500*us)                           #100us delay
    #         n_channels = 8                              #sets number of channels to read off of
    #         smp = [0.0]*n_channels                      #creates list of floating point variables                      
    #         delay(1*ms)
    #         self.sampler0.sample(smp)                   #runs sampler and saves to list
    #         for i in range(len(smp)):
    #             print("after sample:", smp[i])                           #prints each item

    #     else:
    #         # data = pd.read_csv('DT-600 Standard Curve Interpolation Table.txt',sep='   ',header=1,names=['Temp','Voltage','Sensitivity'])
    #         # Temp = data['Temp'].tolist()
    #         # Voltage = data['Voltage'].tolist()
    #         # Temp = [1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.2, 4.4, 4.6, 4.8, 5.0, 5.2, 5.4, 5.6, 5.8, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 42.0, 44.0, 46.0, 48.0, 50.0, 52.0, 54.0, 56.0, 58.0, 60.0, 65.0, 70.0, 75.0, 77.35, 80.0, 85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0, 150.0, 155.0, 160.0, 165.0, 170.0, 175.0, 180.0, 185.0, 190.0, 195.0, 200.0, 205.0, 210.0, 215.0, 220.0, 225.0, 230.0, 235.0, 240.0, 245.0, 250.0, 255.0, 260.0, 265.0, 270.0, 273.15, 275.0, 280.0, 285.0, 290.0, 295.0, 300.0, 305.0, 310.0, 315.0, 320.0, 325.0, 330.0, 335.0, 340.0, 345.0, 350.0, 355.0, 360.0, 365.0, 370.0, 375.0, 380.0, 385.0, 390.0, 395.0, 400.0, 405.0, 410.0, 415.0, 420.0, 425.0, 430.0, 435.0, 440.0, 445.0, 450.0, 455.0, 460.0, 465.0, 470.0, 475.0, 480.0, 485.0, 490.0, 495.0, 500.0]
    #         # Voltage = [1.64429, 1.64299, 1.64157, 1.64003, 1.63837, 1.6366, 1.63472, 1.63274, 1.63067, 1.62852, 1.62629, 1.624, 1.62166, 1.61928, 1.61687, 1.61445, 1.612, 1.60951, 1.60697, 1.60438, 1.60173, 1.59902, 1.59626, 1.59344, 1.59057, 1.58764, 1.58465, 1.57848, 1.57202, 1.56533, 1.55845, 1.55145, 1.54436, 1.53721, 1.53, 1.52273, 1.51541, 1.49698, 1.47868, 1.46086, 1.44374, 1.42747, 1.41207, 1.39751, 1.38373, 1.37065, 1.3582, 1.34632, 1.33499, 1.32416, 1.31381, 1.3039, 1.29439, 1.28526, 1.27645, 1.26794, 1.25967, 1.25161, 1.24372, 1.23596, 1.2283, 1.2207, 1.21311, 1.20548, 1.197748, 1.181548, 1.162797, 1.140817, 1.125923, 1.119448, 1.115658, 1.11281, 1.110421, 1.108261, 1.106244, 1.104324, 1.102476, 1.100681, 1.09893, 1.097216, 1.095534, 1.093878, 1.092244, 1.090627, 1.089024, 1.085842, 1.082669, 1.079492, 1.076303, 1.073099, 1.069881, 1.06665, 1.063403, 1.060141, 1.056862, 1.048584, 1.040183, 1.031651, 1.027594, 1.022984, 1.014181, 1.005244, 0.996174, 0.986974, 0.97765, 0.968209, 0.958657, 0.949, 0.939242, 0.92939, 0.919446, 0.909416, 0.899304, 0.889114, 0.878851, 0.868518, 0.85812, 0.847659, 0.837138, 0.82656, 0.815928, 0.805242, 0.794505, 0.78372, 0.772886, 0.762007, 0.751082, 0.740115, 0.729105, 0.718054, 0.706964, 0.695834, 0.684667, 0.673462, 0.662223, 0.650949, 0.639641, 0.628302, 0.621141, 0.61693, 0.605528, 0.594097, 0.582637, 0.571151, 0.559639, 0.548102, 0.536542, 0.524961, 0.513361, 0.501744, 0.490106, 0.478442, 0.46676, 0.455067, 0.443371, 0.43167, 0.41996, 0.408237, 0.396503, 0.384757, 0.373002, 0.361235, 0.349453, 0.337654, 0.325839, 0.314008, 0.302161, 0.290298, 0.278416, 0.266514, 0.254592, 0.242653, 0.230697, 0.21873, 0.206758, 0.194789, 0.182832, 0.170901, 0.15901, 0.147191, 0.13548, 0.123915, 0.112553, 0.101454, 0.090681]
    #         # T_v = interp1d(Voltage,Temp,'linear')
    #         self.core.reset()                          
    #         self.core.break_realtime()                  
    #         self.sampler0.init()   
    #         # self.sampler0.set_gain_mu(0, 0)         #sets each channel's gain to 0db
    #         delay(500*us)                           
    #         n_channels = 8                              #sets number of channels to read off of
    #         smp = [0.0]*n_channels                      #creates list of floating point variables    
    #         for i in range(self.number_of_datapoints):                      
    #             delay(1*ms)
    #             self.sampler0.sample(smp)                   #runs sampler and saves to list
    #             self.mutate_dataset('Voltage1',i,smp[0])
    #             self.mutate_dataset('Voltage2',i,smp[1])
    #             # self.mutate_dataset('Temp1',i,T_v(smp[0]))
    #             # self.mutate_dataset('Temp2',i,T_v(smp[1]))
    #             print(i,"th Voltage1:",smp[0])
    #             print(i,"th Voltage2:",smp[1])
    #             delay(self.time_interval*s)


