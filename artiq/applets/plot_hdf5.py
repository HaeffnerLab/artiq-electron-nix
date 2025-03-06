#!/usr/bin/env python3
import sys
import numpy as np
import h5py
import PyQt5  # ensures pyqtgraph loads Qt5
import pyqtgraph
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTabWidget, QCheckBox, QPushButton,
    QFileDialog, QApplication, QComboBox, QLabel, QDialog, QGridLayout, QMessageBox,
    QGroupBox, QFormLayout, QLineEdit, QSpinBox
)
from PyQt5.QtCore import Qt
from artiq.applets.simple import TitleApplet
from scipy.optimize import curve_fit

# ------------------------- XYPlot (plotting & fitting, with fit options) -------------------------
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
        xlabel = getattr(args, 'xlabel', 'X')
        ylabel = getattr(args, 'ylabel', 'Y')
        self.setLabel('bottom', xlabel)
        self.setLabel('left', ylabel)
        self.legend = self.addLegend()
        self.fit_curves = {}

    def keyPressEvent(self, event):
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
        # If updating, remove the old fit curve first.
        if fit_type in self.fit_curves and update:
            self.removeItem(self.fit_curves[fit_type]['curve'])
            self.legend.removeItem(self.fit_curves[fit_type]['label'])
            del self.fit_curves[fit_type]
        # If toggling off (and not update), remove the curve.
        if fit_type in self.fit_curves and not update:
            self.removeItem(self.fit_curves[fit_type]['curve'])
            self.legend.removeItem(self.fit_curves[fit_type]['label'])
            del self.fit_curves[fit_type]
            return

        if self.latest_x is None or self.latest_y is None:
            return
        # Use only points with nonzero y.
        mask = self.latest_y != 0
        if not mask.any():
            return
        xdata = self.latest_x[mask]
        ydata = self.latest_y[mask]

        # --- Apply user-specified fitting range if available ---
        options = None
        parent = self.parent()  # MainWidget is the parent
        if parent is not None and hasattr(parent, 'fitOptionsWidget'):
            options = parent.fitOptionsWidget.getOptions()
        if options:
            r_start, r_end = options.get('range', (None, None))
            if r_start is not None and r_end is not None:
                r_start = int(r_start)
                r_end = int(r_end)
                if r_start < 0: r_start = 0
                # When r_end is -1, interpret it as all data.
                if r_end == -1 or r_end >= len(xdata):
                    r_end = len(xdata) - 1
                if r_start <= r_end:
                    xdata = xdata[r_start:r_end+1]
                    ydata = ydata[r_start:r_end+1]

        # --- Compute default p0 and then override if user provided an initial guess ---
        if fit_type == 'exponential decay':
            def func(x, A, B, C):
                return A * np.exp(-B * x) + C
            A0 = max(ydata) - min(ydata)
            B0 = 1.0
            C0 = min(ydata)
            p0 = [A0, B0, C0]
            eq_str = 'A exp(-B x) + C'
            color = 'k'
        elif fit_type == 'lorentzian':
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
            def func(x, A, mu, sigma, C):
                return A * np.exp(-((x - mu)**2) / (2 * sigma**2)) + C
            A0 = max(ydata) - min(ydata)
            mu0 = xdata[np.argmax(ydata)]
            sigma0 = (max(xdata) - min(xdata)) / 4
            C0 = min(ydata)
            p0 = [A0, mu0, sigma0, C0]
            eq_str = 'A exp(-((x-mu)**2)/(2 sigma**2)) + C'
            color = 'g'
        else:
            return

        # Override default initial guess if user provided one.
        if options:
            initial = options.get('initial_guesses', {}).get(fit_type, None)
            if initial is not None and len(initial) > 0:
                p0 = initial

        try:
            popt, pcov = curve_fit(func, xdata, ydata, p0=p0)
        except Exception:
            return

        x_fit = np.linspace(np.min(xdata), np.max(xdata), 200)
        y_fit = func(x_fit, *popt)
        param_str = ', '.join([f'{p:.3e}' for p in popt])
        label_text = f'Fit {eq_str}, \nparams: {param_str}'
        pen = pyqtgraph.mkPen(color, width=2)
        curve = self.plot(x_fit, y_fit, pen=pen, name=label_text)
        self.fit_curves[fit_type] = {'curve': curve, 'label': label_text}

    def data_changed(self, data, mods, title):
        try:
            y = data['y'][1]
        except KeyError:
            return
        x = data.get('x', (False, None))[1]
        if x is None:
            x = np.arange(len(y))
        error = data.get('error', (False, None))[1]
        fit = data.get('fit', (False, None))[1]

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
        self.latest_x = np.array(x)
        self.latest_y = np.array(y)
        
        if self.first_call:
            if len(self.latest_x) >= 10:
                x_initial = self.latest_x[:10]
                y_initial = self.latest_y[:10]
                self.getViewBox().setRange(xRange=(np.min(x_initial), np.max(x_initial)),
                                           yRange=(np.min(y_initial), np.max(y_initial)),
                                           padding=0.1)
            self.first_call = False
        else:
            nonzero_mask = self.latest_y != 0
            if nonzero_mask.any():
                x_nz = self.latest_x[nonzero_mask]
                y_nz = self.latest_y[nonzero_mask]
                self.getViewBox().setRange(xRange=(np.min(x_nz), np.max(x_nz)),
                                           yRange=(np.min(y_nz), np.max(y_nz)),
                                           padding=0.1)
        for fit_type in list(self.fit_curves.keys()):
            self.toggleFit(fit_type, update=True)

# ------------------ Fit Options Widget ------------------
class FitOptionsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Group for Initial Guess Parameters
        guess_group = QGroupBox("Initial Guess Parameters")
        guess_layout = QFormLayout()
        self.exp_guess = QLineEdit()
        self.lorentz_guess = QLineEdit()
        self.gauss_guess = QLineEdit()
        guess_layout.addRow("Exponential decay (A,B,C):", self.exp_guess)
        guess_layout.addRow("Lorentzian (A,x0,gamma,C):", self.lorentz_guess)
        guess_layout.addRow("Gaussian (A,mu,sigma,C):", self.gauss_guess)
        guess_group.setLayout(guess_layout)
        layout.addWidget(guess_group)

        # Group for Fitting Range
        range_group = QGroupBox("Fitting Range (Indices)")
        range_layout = QHBoxLayout()
        self.start_index = QSpinBox()
        self.start_index.setMinimum(0)
        self.start_index.setValue(0)  # default start index 0
        self.start_index.setPrefix("Start: ")
        self.end_index = QSpinBox()
        self.end_index.setMinimum(-1)  # allow -1 as special value for "all data"
        self.end_index.setValue(-1)    # default end index -1
        self.end_index.setPrefix("End: ")
        range_layout.addWidget(self.start_index)
        range_layout.addWidget(self.end_index)
        range_group.setLayout(range_layout)
        layout.addWidget(range_group)

        # Button to apply options and update fits
        self.apply_button = QPushButton("Apply Fit Options")
        layout.addWidget(self.apply_button)

        layout.addStretch()

    def getOptions(self):
        options = {}
        initial_guesses = {}
        def parse_guess(text):
            try:
                parts = [float(p.strip()) for p in text.split(',') if p.strip() != ""]
                return parts if parts else None
            except Exception:
                return None
        exp = parse_guess(self.exp_guess.text())
        lorentz = parse_guess(self.lorentz_guess.text())
        gauss = parse_guess(self.gauss_guess.text())
        if exp is not None:
            initial_guesses['exponential decay'] = exp
        if lorentz is not None:
            initial_guesses['lorentzian'] = lorentz
        if gauss is not None:
            initial_guesses['gaussian'] = gauss
        options['initial_guesses'] = initial_guesses

        start = self.start_index.value()
        end = self.end_index.value()
        options['range'] = (start, end)
        return options

# ----------------- Variable Selection Dialog -----------------
class VariableSelectionDialog(QDialog):
    def __init__(self, dataset_dict, parent=None):
        """
        dataset_dict: dictionary with keys as dataset names and values as numpy arrays.
        """
        super().__init__(parent)
        self.setWindowTitle("Select Variables")
        self.selected_x = None
        self.selected_y = None

        layout = QGridLayout(self)
        layout.addWidget(QLabel("x variable"), 0, 0)
        layout.addWidget(QLabel("y variable"), 0, 1)
        self.x_combo = QComboBox(self)
        self.y_combo = QComboBox(self)
        for name, array in dataset_dict.items():
            length = 0 if len(np.shape(array)) < 1 else np.shape(array)[0]
            display_text = f"{name} <{length}>"
            self.x_combo.addItem(display_text, userData=name)
            self.y_combo.addItem(display_text, userData=name)
        layout.addWidget(self.x_combo, 1, 0)
        layout.addWidget(self.y_combo, 1, 1)
        ok_btn = QPushButton("OK", self)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn, 2, 0, 1, 2)
        self.setLayout(layout)

    def accept(self):
        self.selected_x = self.x_combo.currentData()
        self.selected_y = self.y_combo.currentData()
        super().accept()

# ------------------------ MainWidget (with file browsing and extra tab) ------------------------
class MainWidget(QWidget):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.resize(1200, 800)
        main_layout = QHBoxLayout(self)
        left_panel = QVBoxLayout()
        self.browseBtn = QPushButton("Browse HDF5 File", self)
        self.browseBtn.clicked.connect(self.browseFile)
        left_panel.addWidget(self.browseBtn)
        self.plotWidget = XYPlot(args)
        left_panel.addWidget(self.plotWidget, stretch=1)
        main_layout.addLayout(left_panel, stretch=3)

        self.tabWidget = QTabWidget()
        # Tab 1: Fitting Functions (unchanged)
        fit_tab = QWidget()
        fit_layout = QVBoxLayout(fit_tab)
        self.cb_exp = QCheckBox('Exponential decay')
        self.cb_lor = QCheckBox('Lorentzian')
        self.cb_gauss = QCheckBox('Gaussian')
        fit_layout.addWidget(self.cb_exp)
        fit_layout.addWidget(self.cb_lor)
        fit_layout.addWidget(self.cb_gauss)
        fit_layout.addStretch()
        self.tabWidget.addTab(fit_tab, 'Fitting functions')
        # Tab 2: Fit Options (new)
        self.fitOptionsWidget = FitOptionsWidget(self)
        self.tabWidget.addTab(self.fitOptionsWidget, 'Fit Options')
        main_layout.addWidget(self.tabWidget, stretch=1)

        self.cb_exp.stateChanged.connect(lambda state: self.onFitToggled('exponential decay', state))
        self.cb_lor.stateChanged.connect(lambda state: self.onFitToggled('lorentzian', state))
        self.cb_gauss.stateChanged.connect(lambda state: self.onFitToggled('gaussian', state))
        # Connect the Apply Fit Options button to update the fitting curves.
        self.fitOptionsWidget.apply_button.clicked.connect(self.updateFitCurves)

    def onFitToggled(self, fit_type, state):
        self.plotWidget.toggleFit(fit_type)

    def updateFitCurves(self):
        # Update each active fit curve using new options.
        if self.cb_exp.isChecked():
            self.plotWidget.toggleFit('exponential decay', update=True)
        if self.cb_lor.isChecked():
            self.plotWidget.toggleFit('lorentzian', update=True)
        if self.cb_gauss.isChecked():
            self.plotWidget.toggleFit('gaussian', update=True)

    def show_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

    def browseFile(self):
        file_dialog = QFileDialog(self, "Open HDF5 File", "", "HDF5 Files (*.h5 *.hdf5)")
        file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        if file_dialog.exec_() != QFileDialog.Accepted:
            return
        file_path = file_dialog.selectedFiles()[0]
        try:
            with h5py.File(file_path, 'r') as file:
                # We assume the file has a group named 'datasets'
                dataset_names = list(file['datasets'].keys())
                data_dict = {name: np.array(file['datasets'][name][()]) for name in dataset_names}
        except Exception as e:
            self.show_message("Error", f"Error reading file: {e}")
            return

        if not dataset_names:
            self.show_message("No Datasets", "No datasets found in the file.")
            return

        var_dialog = VariableSelectionDialog(data_dict, self)
        if var_dialog.exec_() == QDialog.Accepted:
            x_key = var_dialog.selected_x
            y_key = var_dialog.selected_y
            new_data = {'y': (True, data_dict[y_key])}
            if x_key:
                new_data['x'] = (True, data_dict[x_key])
            title = f"Plot: {x_key} vs {y_key}"
            self.plotWidget.data_changed(new_data, mods=None, title=title)

    def data_changed(self, data, mods, title):
        self.plotWidget.data_changed(data, mods, title)

# --------------------------- Main -----------------------------------
def main():
    applet = TitleApplet(MainWidget)
    # Removed x and y command-line datasets.
    applet.add_dataset('error', 'Error bars for each X value', required=False)
    applet.add_dataset('fit', 'Fit values for each X value', required=False)
    try:
        applet.argparser.add_argument('--range', type=int, default=None)
        applet.argparser.add_argument('--xlabel', type=str, default='X')
        applet.argparser.add_argument('--ylabel', type=str, default='Y')
        applet.argparser.add_argument('--title', type=str, default='RID')
    except Exception:
        pass
    applet.run()

if __name__ == '__main__':
    main()
