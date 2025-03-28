#!/usr/bin/env python3
import numpy as np
import PyQt5  # make sure pyqtgraph imports Qt5
import pyqtgraph
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTabWidget, QCheckBox
)
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
        self.first_call = True  # flag for initial zoom
        self.dark_mode = False  # Dark mode flag (default False)
        self.update_color_scheme()
        self.showGrid(x=True, y=True)  # enable grid
        # Interpolation flag; when True, draw a dashed line connecting data points.
        self.interpolate = False
        # Set axis labels.
        xlabel = getattr(args, 'xlabel', 'X')
        ylabel = getattr(args, 'ylabel', 'Y')
        self.setLabel('bottom', xlabel)
        self.setLabel('left', ylabel)
        self.plot_error = getattr(args, 'plot_error')
        self.plot_fit = getattr(args, "plot_fit")
        # Add a legend for fit curves.
        self.legend = self.addLegend()
        self.fit_curves = {}

    def update_color_scheme(self):
        """Set the color scheme based on self.dark_mode."""
        if self.dark_mode:
            self.color_scheme = {
                "data": "#aec7e8",     # light blue
                "linear": "#ffbb78",   # light orange
                "exp": "#98df8a",      # light green
                "lor": "#ff9896",      # light red
                "gauss": "#c5b0d5",    # light purple
                "interp": "#aec7e8"    # same as data
            }
            self.setBackground("k")  # Black background
            self.getAxis('bottom').setTextPen(pyqtgraph.mkPen("w"))
            self.getAxis('left').setTextPen(pyqtgraph.mkPen("w"))
        else:
            self.color_scheme = {
                "data": "#1f77b4",     # default blue
                "linear": "#ff7f0e",   # default orange
                "exp": "#2ca02c",      # default green
                "lor": "#d62728",      # default red
                "gauss": "#9467bd",    # default purple
                "interp": "#1f77b4"    # same as data
            }
            self.setBackground("w")  # White background
            self.getAxis('bottom').setTextPen(pyqtgraph.mkPen("k"))
            self.getAxis('left').setTextPen(pyqtgraph.mkPen("k"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            if (self.latest_x is not None and self.latest_y is not None and len(self.latest_x) > 0):
                # Zoom to only data points with positive y.
                if len(np.where(self.latest_y > 0)[0]) > 0:
                    x_min = np.min(self.latest_x[np.where(self.latest_y > 0)])
                    x_max = np.max(self.latest_x[np.where(self.latest_y > 0)])
                    y_min = np.min(self.latest_y[np.where(self.latest_y > 0)])
                    y_max = np.max(self.latest_y[np.where(self.latest_y > 0)])
                else: 
                    x_min = np.min(self.latest_x)
                    x_max = np.max(self.latest_x)
                    y_min = np.min(self.latest_y)
                    y_max = np.max(self.latest_y)
                self.getViewBox().setRange(xRange=(x_min, x_max),
                                           yRange=(y_min, y_max), padding=0.1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def toggleFit(self, fit_type, update=False):
        # If toggling off (and not an update), remove the fit curve.
        if fit_type in self.fit_curves and not update:
            # For 'find dips', remove both curve and associated text labels.
            if fit_type == 'find dips':
                self.removeItem(self.fit_curves[fit_type]['curve'])
                for t in self.fit_curves[fit_type]['labels']:
                    self.removeItem(t)
            else:
                self.removeItem(self.fit_curves[fit_type]['curve'])
                self.legend.removeItem(self.fit_curves[fit_type]['label'])
            del self.fit_curves[fit_type]
            return

        if self.latest_x is None or self.latest_y is None:
            return
        mask = self.latest_y != 0
        if not mask.any():
            return
        xdata = self.latest_x[mask]
        ydata = self.latest_y[mask]

        # ----- Linear Fit -----
        if fit_type == 'linear':
            def func(x, A, B):
                return A * x + B
            A0 = 1; B0 = 0
            p0 = [A0, B0]
            eq_str = 'A x + B'
            color = self.color_scheme["linear"]

        # ----- Exponential Decay Fit -----
        elif fit_type == 'exponential decay':
            def func(x, A, B, C):
                return A * np.exp(-x/B/1000) + C
            A0 = max(ydata) - min(ydata)
            B0 = 1.0; C0 = min(ydata)
            p0 = [A0, B0, C0]
            eq_str = 'A exp(-x/B/1000) + C'
            color = self.color_scheme["exp"]

        # ----- Lorentzian Fit -----
        elif fit_type == 'lorentzian':
            def func(x, A, x0, gamma, C):
                return A / (1 + ((x - x0)/gamma)**2) + C
            A0 = max(ydata) - min(ydata)
            x0_0 = xdata[np.argmax(ydata)]
            gamma0 = (max(xdata) - min(xdata)) / 2; C0 = min(ydata)
            p0 = [A0, x0_0, gamma0, C0]
            eq_str = 'A/(1+((x-x0)/gamma)**2) + C'
            color = self.color_scheme["lor"]

        # ----- Gaussian Fit -----
        elif fit_type == 'gaussian':
            def func(x, A, mu, sigma, C):
                return A * np.exp(-((x - mu)**2)/(2*sigma**2)) + C
            A0 = max(ydata) - min(ydata)
            mu0 = xdata[np.argmax(ydata)]
            sigma0 = (max(xdata) - min(xdata)) / 4; C0 = min(ydata)
            p0 = [A0, mu0, sigma0, C0]
            eq_str = 'A exp(-((x-mu)**2)/(2 sigma**2)) + C'
            color = self.color_scheme["gauss"]

        # ----- Double Exponential Fit -----
        elif fit_type == 'double exponential':
            def func(x, A, B, C, D):
                return A * np.exp(-x/B/1000) + C * np.exp(-x/D/1000)
            A0 = max(ydata) - min(ydata)
            D0 = 30
            B0 = 5
            C0 = A0/3
            p0 = [A0, B0, C0, D0]
            eq_str = 'A exp(-x/B/1000) + C exp(-x/D/1000)'
            color = self.color_scheme["exp"]

        # ----- Double Lorentzian Fit -----
        elif fit_type == 'double lorentzian':
            def func(x, A1, x01, gamma1, A2, x02, gamma2, C):
                return (A1 / (1 + ((x - x01)/gamma1)**2) +
                        A2 / (1 + ((x - x02)/gamma2)**2) + C)
            amp = max(ydata) - min(ydata)
            A1_0 = amp / 2
            A2_0 = amp / 2
            x01_0 = xdata[np.argmax(ydata)]
            x_range = np.max(xdata) - np.min(xdata)
            x02_0 = x01_0 + x_range/4
            gamma1_0 = x_range / 4
            gamma2_0 = x_range / 4
            C0 = min(ydata)
            p0 = [A1_0, x01_0, gamma1_0, A2_0, x02_0, gamma2_0, C0]
            eq_str = 'A1/(1+((x-x01)/gamma1)**2) + A2/(1+((x-x02)/gamma2)**2) + C'
            color = self.color_scheme["lor"]

        # ----- Find Dips -----
        elif fit_type == 'find dips':
            # Use a default sliding window of 10 data points.
            window = 10
            if window % 2 == 0:
                window += 1
            half = window // 2
            dip_indices = []
            for i in range(len(ydata)):
                start_win = max(0, i - half)
                end_win = min(len(ydata), i + half + 1)
                if ydata[i] == np.min(ydata[start_win:end_win]):
                    dip_indices.append(i)
            if not dip_indices:
                return
            # Plot the dips as 'x' markers.
            curve = self.plot(xdata[dip_indices], ydata[dip_indices],
                              pen=None, symbol='x', symbolSize=12, symbolBrush='m')
            # Add text labels for each dip.
            labels = []
            for i in dip_indices:
                text = f"({xdata[i]:.2f}, {ydata[i]:.2f})"
                t = pyqtgraph.TextItem(text, anchor=(0, 1), color='m')
                t.setPos(xdata[i], ydata[i])
                self.addItem(t)
                labels.append(t)
            self.fit_curves[fit_type] = {'curve': curve, 'label': 'Dips', 'labels': labels}
            return

        else:
            return

        try:
            popt, pcov = curve_fit(func, xdata, ydata, p0=p0,
                                   xtol=1e-10, ftol=1e-10, maxfev=10000)
        except Exception:
            return

        x_fit = np.linspace(np.min(xdata), np.max(xdata), 200)
        y_fit = func(x_fit, *popt)
        param_str = ', '.join([f'{p:.3e}' for p in popt])
        label_text = f'Fit {eq_str}\nparams: {param_str}'
        pen = pyqtgraph.mkPen(color, width=3)
        curve = self.plot(x_fit, y_fit, pen=pen, name=label_text)
        self.fit_curves[fit_type] = {'curve': curve, 'label': label_text}

    def data_changed(self, data, mods, title0):
        try:
            y = data[self.args.y][1]
        except KeyError:
            return
        x = data.get(self.args.x, (False, None))[1]
        try:
            title = f'RID: {data[self.args.rid][1]}'
        except KeyError:
            title = 'RID'
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

        self.latest_x = np.array(x)
        self.latest_y = np.array(y)
        self.clear()
        self.plot(x, y, pen=None, symbol='o', symbolSize=10,
                  symbolBrush=self.color_scheme["data"])

        if self.interpolate:
            interp_pen = pyqtgraph.mkPen(self.color_scheme["interp"],
                                         style=QtCore.Qt.DashLine, width=3)
            self.plot(x, y, pen=interp_pen)

        self.setTitle(title)
        if error is not None and self.plot_error:
            if hasattr(error, '__len__') and not isinstance(error, np.ndarray):
                error = np.array(error)
            errbars = pyqtgraph.ErrorBarItem(x=np.array(x), y=np.array(y), height=error)
            self.addItem(errbars)
        if fit is not None and self.plot_fit:
            xi = np.argsort(x)
            self.plot(np.array(x)[xi], np.array(fit)[xi])
        if self.first_call and len(self.latest_x) >= 10:
            x_initial = self.latest_x[:10]
            y_initial = self.latest_y[:10]
            self.getViewBox().setRange(xRange=(np.min(x_initial), np.max(x_initial)),
                                       yRange=(np.min(y_initial), np.max(y_initial)),
                                       padding=0.1)
            self.first_call = False
        # Update any active fit curves.
        for fit_type in list(self.fit_curves.keys()):
            self.toggleFit(fit_type, update=True)


class MainWidget(QWidget):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.resize(1200, 800)
        layout = QHBoxLayout(self)
        self.plotWidget = XYPlot(args)
        layout.addWidget(self.plotWidget, stretch=3)

        # Create a right-side vertical layout.
        right_layout = QVBoxLayout()

        # Create a separate widget for Dark Mode button.
        dark_widget = QWidget()
        dark_layout = QHBoxLayout(dark_widget)
        dark_layout.setContentsMargins(0, 0, 0, 0)
        self.cb_dark = QCheckBox('Dark Mode')
        dark_layout.addWidget(self.cb_dark)
        self.cb_dark.stateChanged.connect(self.toggleDarkMode)
        right_layout.addWidget(dark_widget)

        # Create tab widget for fitting functions.
        self.tabWidget = QTabWidget()
        right_layout.addWidget(self.tabWidget, stretch=1)

        fit_tab = QWidget()
        fit_layout = QVBoxLayout(fit_tab)
        self.cb_int = QCheckBox('Interpolate')
        self.cb_lin = QCheckBox('Linear')
        self.cb_exp = QCheckBox('Exponential decay')
        self.cb_lor = QCheckBox('Lorentzian')
        self.cb_gauss = QCheckBox('Gaussian')
        # New checkboxes:
        self.cb_dexp = QCheckBox('Double exponential')
        self.cb_dlor = QCheckBox('Double lorentzian')
        self.cb_dips = QCheckBox('Find dips')

        fit_layout.addWidget(self.cb_int)
        fit_layout.addWidget(self.cb_lin)
        fit_layout.addWidget(self.cb_exp)
        fit_layout.addWidget(self.cb_dexp)
        fit_layout.addWidget(self.cb_lor)
        fit_layout.addWidget(self.cb_gauss)
        fit_layout.addWidget(self.cb_dlor)
        fit_layout.addWidget(self.cb_dips)
        fit_layout.addStretch()
        self.tabWidget.addTab(fit_tab, 'Fitting functions')

        layout.addLayout(right_layout, stretch=1)

        # Connect checkboxes to toggle fits.
        self.cb_lin.stateChanged.connect(lambda state: self.onFitToggled('linear', state))
        self.cb_exp.stateChanged.connect(lambda state: self.onFitToggled('exponential decay', state))
        self.cb_dexp.stateChanged.connect(lambda state: self.onFitToggled('double exponential', state))
        self.cb_lor.stateChanged.connect(lambda state: self.onFitToggled('lorentzian', state))
        self.cb_gauss.stateChanged.connect(lambda state: self.onFitToggled('gaussian', state))
        self.cb_dlor.stateChanged.connect(lambda state: self.onFitToggled('double lorentzian', state))
        self.cb_dips.stateChanged.connect(lambda state: self.onFitToggled('find dips', state))
        self.cb_int.stateChanged.connect(self.toggleInterpolate)

    def toggleInterpolate(self, state):
        self.plotWidget.interpolate = (state == Qt.Checked)
        if self.plotWidget.latest_x is not None and self.plotWidget.latest_y is not None:
            dummy_data = {
                self.args.y: (True, self.plotWidget.latest_y),
                self.args.x: (True, self.plotWidget.latest_x)
            }
            self.plotWidget.data_changed(dummy_data, mods=None, title0="")

    def toggleDarkMode(self, state):
        dark = (state == Qt.Checked)
        self.plotWidget.dark_mode = dark
        self.plotWidget.update_color_scheme()
        if dark:
            self.setStyleSheet(
                "background-color: black; color: white; "
                "QTabWidget::pane { background: black; } "
                "QTabBar::tab { background: black; color: white; }"
            )
            self.tabWidget.setStyleSheet(
                "background-color: black; color: white; "
                "QTabWidget::pane { background: black; } "
                "QTabBar::tab { background: black; color: white; }"
            )
            for cb in self.findChildren(QCheckBox):
                palette = cb.palette()
                palette.setColor(cb.foregroundRole(), Qt.white)
                cb.setPalette(palette)
        else:
            self.setStyleSheet("")
            self.tabWidget.setStyleSheet("")
        if self.plotWidget.latest_x is not None and self.plotWidget.latest_y is not None:
            dummy_data = {
                self.args.y: (True, self.plotWidget.latest_y),
                self.args.x: (True, self.plotWidget.latest_x)
            }
            self.plotWidget.data_changed(dummy_data, mods=None, title0="")

    def onFitToggled(self, fit_type, state):
        self.plotWidget.toggleFit(fit_type)

    def data_changed(self, data, mods, title):
        self.plotWidget.data_changed(data, mods, title)


def main():
    applet = TitleApplet(MainWidget)
    applet.add_dataset('y', 'Y values')
    applet.add_dataset('x', 'X values', required=False)
    applet.add_dataset('rid', 'RID values', required=False)
    applet.add_dataset('error', 'Error bars for each X value', required=False)
    applet.add_dataset('fit', 'Fit values for each X value', required=False)
    try:
        applet.argparser.add_argument('--range', type=int, default=None)
        applet.argparser.add_argument('--xlabel', type=str, default='X')
        applet.argparser.add_argument('--ylabel', type=str, default='Y')
        applet.argparser.add_argument('--plot_error', action='store_true', help='Enable error bars in the plot')
        applet.argparser.add_argument('--plot_fit', action='store_true', help='Enable fitted values in the plot')
    except Exception:
        pass
    applet.run()


if __name__ == '__main__':
    main()
