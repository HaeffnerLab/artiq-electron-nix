#!/usr/bin/env python3

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QApplication, QPushButton, QWidget, QAction, QTabWidget, QVBoxLayout, QLabel, QComboBox, QGridLayout, QLineEdit, QPlainTextEdit

from artiq.applets.simple import SimpleApplet, TitleApplet
from artiq.applets.plot_xy import XYPlot
import pyqtgraph


class NumberWidget2(pyqtgraph.PlotWidget):
    def __init__(self, args):
        pyqtgraph.PlotWidget.__init__(self)
        self.args = args
        self.step = 0

    def data_changed(self, data, *args, **kwargs):
        y = float(data[self.args.y][1])
        x = float(data[self.args.x][1])
        #x = self.step
        #y = x
        #self.clear()
        #self
        self.plot([x], [y], pen=None, symbol="x")
        self.step += 1


class NumberWidget(QtWidgets.QLCDNumber):
    def __init__(self, args):
        QtWidgets.QLCDNumber.__init__(self)
        self.setDigitCount(args.digit_count)
        self.x = args.x
        self.y = args.y

    def data_changed(self, data, mods):
        n = int(data[self.x][1])+1
        n2 = int(data[self.y][1])
        self.display(f'{n} - {n2}')


class DisplayWidget(QWidget):
    def __init__(self, args):
        super().__init__(self)
        #self.setDigitCount(args.digit_count)
        self.x_list = []
        self.y_list = []
        self.x = args.x
        self.y = args.y
        self.label = QLabel(self)

    def data_changed(self, data, mods):
        n = float(data[self.x][1])
        n2 = float(data[self.y][1])
        self.x_list.append(n)
        self.ylist.append(n2)
        screen = {'count': n, 'point': n2}
        self.label.setText(str(screen))
        


def main():
    applet = SimpleApplet(NumberWidget)
    #applet = TitleApplet(NumberWidget2)
    #applet.add_dataset("c", "dataset to show")
    applet.add_dataset("x", "dataset to show")
    applet.add_dataset("y", "dataset to show")
    #applet.add_dataset("z", "dataset to show")
    applet.argparser.add_argument("--digit-count", type=int, default=10,
                                  help="total number of digits to show")
    applet.run()

if __name__ == "__main__":
    main()
