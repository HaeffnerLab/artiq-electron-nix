from artiq.experiment import *
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QPlainTextEdit
from artiq.applets.simple import SimpleApplet
import os
import sys

class MyTabWidget(QtWidgets.QSplitter):
     
    def __init__(self):
        QtWidgets.QSplitter.__init__(self)
        self.resize(600, 200)
        self.setWindowTitle("XY/Histogram"):
        
        self.layout = QVBoxLayout(self)
        self.setup_UI()
        #self.e=np.full(21, 0.0)    
    
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
        self.bl_electrodes = [0,0,1,0] 
        self.br_electrodes = [1,4,5,0]
        self.tl_electrodes = [3,0,1,6]
        self.tr_electrodes = [4,4,5,6]

        
        #electrode grid
        for e in [self.tl_electrodes, self.tr_electrodes, self.bl_electrodes, self.br_electrodes]:            
            
            el_values = e[0]
            xcoord_label = e[1]
            xcoord_entry = e[2]
            ycoord = e[3]
            
        
            for i in range(len(self.ELECTRODES[el_values])):      
                textbox = QLineEdit(self)
                grid1.addWidget(textbox,ycoord+i,xcoord_entry,1,1)
                textbox.setPlaceholderText("0.0")
                self.electrodes.append(textbox)
                
                label = QLabel(self.ELECTRODES[el_values][i], self)
                grid1.addWidget(label,ycoord+i,xcoord_label,1,1)
          
        #spacing
        label_gap = QLabel('', self)
        grid1.addWidget(label_gap,5,1,1,1)
        
        #tg
        textbox_tg = QLineEdit(self)
        grid1.addWidget(textbox_tg,1,3,1,1)

        # Add Background color
        #testcolour = QtGui.QColor(0, 100, 0)
        #mycolor = QColor(color.red(), color.green(), color.blue(), 200)
 	
        #rgb = 255, 0, 0
        #mycolor_hex = "#" + "%02x%02x%02x" % rgb
        #print(mycolor_hex)
       
       # entry = textbox_tg.text() or "0"
       # value = float(entry)
       # if value>0:
       #     textbox_tg.setStyleSheet("background-color: #ff0000 ")#;  border: 1px solid black;")

        textbox_tg.setPlaceholderText("0.0")
        self.electrodes.append(textbox_tg)
        label_tg = QLabel(self.ELECTRODES[2][0], self)
        grid1.addWidget(label_tg,1,2,1,1)
       
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
        c_button = QPushButton('Select C-file', self)
        c_button.clicked.connect(self.openFileDialog)
        grid2.addWidget(c_button, 1, 9)
        self.tab2.setLayout(grid2)
      
  
        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        
        
        
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
        print(self.e)

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
            if self.e[0][i]>=20:
                print('warning: voltage exceeds limit')
                self.e[0][i]=20
            elif self.e[0][i]<=-20:
                print('warning: voltage exceeds limit')
                self.e[0][i]=-20 
	
        curr = 0
        for label in self.all_labels:
            if curr == 10:
                curr+=1
            
            label.setText(str(round(self.e[0][curr],2)))
            curr+=1
            
        self.label0_tg.setText(str(round(self.e[0][10],2)))
        #self.label0_p2.setText(str(round(self.e[21][0],3)))
            
        self.e = self.e[0].tolist()
        self.e.append(self.e.pop(10))        

def main():
    test = SimpleApplet(MyTabWidget)
    #applet.add_dataset("e", "electrode")
    test.run()

if __name__ == "__main__":
    main()
