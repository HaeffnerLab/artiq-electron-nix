#!/usr/bin/env python3
import numpy as np
import PyQt5  # make sure pyqtgraph imports Qt5
import pyqtgraph
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTabWidget, QCheckBox
from PyQt5.QtCore import Qt
from artiq.applets.simple import TitleApplet
from scipy.optimize import curve_fit

class XYPlot(pyqtgraph.PlotWidget):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.steps = 0
        self.latest_x = None  # latest x data array
        self.latest_y = None  # latest y data array
        self.first_call = True  # flag to set initial zoom
        self.setBackground("w")  # white background
        self.showGrid(x=True, y=True)  # enable grid
        # Set axis labels if provided via command line:
        xlabel = getattr(args, 'xlabel', 'X')
        ylabel = getattr(args, 'ylabel', 'Y')
        self.setLabel('bottom', xlabel)
        self.setLabel('left', ylabel)
        # Add a legend for the fitting curves:
        self.legend = self.addLegend()
        # Dictionary to store active fit curves; keys are fit types.
        self.fit_curves = {}

    def keyPressEvent(self, event):
        # When the user presses "f", zoom to fit all data points.
        if event.key() == Qt.Key_F:
            if self.latest_x is not None and self.latest_y is not None and len(self.latest_x) > 0:
                x_min = np.min(self.latest_x)
                x_max = np.max(self.latest_x)
                y_min = np.min(self.latest_y)
                y_max = np.max(self.latest_y)
                self.getViewBox().setRange(xRange=(x_min, x_max), yRange=(y_min, y_max), padding=0.1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def toggleFit(self, fit_type, update=False):
        """
        Toggle (or update, if update=True) the fitting curve for the given fit_type.
        If the curve is active and update is False, it is removed.
        If not active (or update is True), a new fit is computed from the current data.
        """
        # If the fit curve is already active and we're not updating, remove it.
        if fit_type in self.fit_curves and not update:
            self.removeItem(self.fit_curves[fit_type]['curve'])
            self.legend.removeItem(self.fit_curves[fit_type]['label'])
            del self.fit_curves[fit_type]
            return

        # Ensure we have data; use only points with nonzero y.
        if self.latest_x is None or self.latest_y is None:
            return
        mask = self.latest_y != 0
        if not mask.any():
            return
        xdata = self.latest_x[mask]
        ydata = self.latest_y[mask]

        # Define the fitting function and initial parameters based on fit_type.
        if fit_type == 'exponential decay':
            # f(x) = A * exp(-B*x) + C
            def func(x, A, B, C):
                return A * np.exp(-B * x) + C
            A0 = max(ydata) - min(ydata)
            B0 = 1.0
            C0 = min(ydata)
            p0 = [A0, B0, C0]
            eq_str = 'A exp(-B x) + C'
            color = 'k'  # black
        elif fit_type == 'lorentzian':
            # f(x) = A/(1+((x-x0)/gamma)**2) + C
            def func(x, A, x0, gamma, C):
                return A / (1 + ((x - x0) / gamma)**2) + C
            A0 = max(ydata) - min(ydata)
            x0_0 = xdata[np.argmax(ydata)]
            gamma0 = (max(xdata) - min(xdata)) / 2
            C0 = min(ydata)
            p0 = [A0, x0_0, gamma0, C0]
            eq_str = 'A/(1+((x-x0)/gamma)**2) + C'
            color = 'r'
        elif fit_type == 'gaussian':
            # f(x) = A exp(-((x-mu)**2)/(2 sigma**2)) + C
            def func(x, A, mu, sigma, C):
                return A * np.exp(-((x - mu) ** 2) / (2 * sigma ** 2)) + C
            A0 = max(ydata) - min(ydata)
            mu0 = xdata[np.argmax(ydata)]
            sigma0 = (max(xdata) - min(xdata)) / 4
            C0 = min(ydata)
            p0 = [A0, mu0, sigma0, C0]
            eq_str = 'A exp(-((x-mu)**2)/(2 sigma**2)) + C'
            color = 'g'
        else:
            return

        try:
            popt, pcov = curve_fit(func, xdata, ydata, p0=p0)
        except Exception:
            # Fitting failed
            return

        # Create a smooth set of x values for the fit curve.
        x_fit = np.linspace(np.min(xdata), np.max(xdata), 200)
        y_fit = func(x_fit, *popt)
        # Format the fitted parameters for the legend.
        param_str = ', '.join([f'{p:.3e}' for p in popt])
        label_text = f'Fit {eq_str}, \nparams: {param_str}'
        # Plot the fit curve with a pen of width 2 and the specified color.
        pen = pyqtgraph.mkPen(color, width=2)
        curve = self.plot(x_fit, y_fit, pen=pen, name=label_text)
        # Store the curve and its label in the dictionary.
        self.fit_curves[fit_type] = {'curve': curve, 'label': label_text}

    def data_changed(self, data, mods, title):
        # Get the y data (and x if provided); also error and fit (if any).
        try:
            y = data[self.args.y][1]
        except KeyError:
            return
        x = data.get(self.args.x, (False, None))[1]
        if x is None:
            x = np.arange(len(y))
        error = data.get(self.args.error, (False, None))[1]
        fit = data.get(self.args.fit, (False, None))[1]

        if not len(y) or len(y) != len(x):
            return
        if error is not None and hasattr(error, '__len__'):
            if not len(error):
                error = None
            elif len(error) != len(y):
                return
        if fit is not None:
            if not len(fit):
                fit = None
            elif len(fit) != len(y):
                return

        # Clear the plot and re-plot the data.
        self.clear()
        self.plot(x, y, pen=None, symbol='o', symbolSize=10, symbolBrush='b')
        self.setTitle(title)
        if error is not None:
            if hasattr(error, '__len__') and not isinstance(error, np.ndarray):
                error = np.array(error)
            errbars = pyqtgraph.ErrorBarItem(x=np.array(x), y=np.array(y), height=error)
            self.addItem(errbars)
        if fit is not None:
            xi = np.argsort(x)
            self.plot(np.array(x)[xi], np.array(fit)[xi])
        # Save the latest data for future use.
        self.latest_x = np.array(x)
        self.latest_y = np.array(y)
        
        # On first update, zoom to show only the first 10 data points.
        if self.first_call:
            if len(self.latest_x) >= 10:
                x_initial = self.latest_x[:10]
                y_initial = self.latest_y[:10]
                self.getViewBox().setRange(xRange=(np.min(x_initial), np.max(x_initial)),
                                           yRange=(np.min(y_initial), np.max(y_initial)),
                                           padding=0.1)
            self.first_call = False
        else:
            # Automatically zoom to fit data points with nonzero y values.
            nonzero_mask = self.latest_y != 0
            if nonzero_mask.any():
                x_nz = self.latest_x[nonzero_mask]
                y_nz = self.latest_y[nonzero_mask]
                self.getViewBox().setRange(xRange=(np.min(x_nz), np.max(x_nz)),
                                           yRange=(np.min(y_nz), np.max(y_nz)),
                                           padding=0.1)
        # If any fit curves are active, update (recompute) them based on the new data.
        for fit_type in list(self.fit_curves.keys()):
            self.toggleFit(fit_type, update=True)

class MainWidget(QWidget):
    def __init__(self, args):
        super().__init__()
        self.args = args
        # Resize the main widget to be larger.
        self.resize(1200, 800)
        # Create a horizontal layout: plot on the left, side tab on the right.
        layout = QHBoxLayout(self)
        self.plotWidget = XYPlot(args)
        layout.addWidget(self.plotWidget, stretch=3)
        # Create a tab widget for additional controls.
        self.tabWidget = QTabWidget()
        layout.addWidget(self.tabWidget, stretch=1)
        # Create the "Fitting functions" tab.
        fit_tab = QWidget()
        fit_layout = QVBoxLayout(fit_tab)
        # Three checkboxes for the three fit options.
        self.cb_exp = QCheckBox('Exponential decay')
        self.cb_lor = QCheckBox('Lorentzian')
        self.cb_gauss = QCheckBox('Gaussian')
        fit_layout.addWidget(self.cb_exp)
        fit_layout.addWidget(self.cb_lor)
        fit_layout.addWidget(self.cb_gauss)
        fit_layout.addStretch()
        self.tabWidget.addTab(fit_tab, 'Fitting functions')
        # Connect the checkboxes to toggle the corresponding fit curves.
        self.cb_exp.stateChanged.connect(lambda state: self.onFitToggled('exponential decay', state))
        self.cb_lor.stateChanged.connect(lambda state: self.onFitToggled('lorentzian', state))
        self.cb_gauss.stateChanged.connect(lambda state: self.onFitToggled('gaussian', state))

    def onFitToggled(self, fit_type, state):
        # Qt.Checked == 2, Qt.Unchecked == 0.
        self.plotWidget.toggleFit(fit_type)

    def data_changed(self, data, mods, title):
        # Forward the data change event to the plot widget.
        self.plotWidget.data_changed(data, mods, title)

def main():
    applet = TitleApplet(MainWidget)
    applet.add_dataset('y', 'Y values')
    applet.add_dataset('x', 'X values', required=False)
    applet.add_dataset('error', 'Error bars for each X value', required=False)
    applet.add_dataset('fit', 'Fit values for each X value', required=False)
    try:
        applet.argparser.add_argument('--range', type=int, default=None)
        applet.argparser.add_argument('--xlabel', type=str, default='X')
        applet.argparser.add_argument('--ylabel', type=str, default='Y')
    except Exception:
        pass
    applet.run()

if __name__ == '__main__':
    main()
