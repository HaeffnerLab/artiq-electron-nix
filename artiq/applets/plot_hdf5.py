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
        # Instead of storing a single latest_x/y, we keep a list of datasets.
        self.datasets = []
        self.first_call = True  # for initial zoom (not used in append mode)
        # Dark mode and interpolation flag.
        self.dark_mode = False  # default light mode
        self.interpolate = False  # default no interpolation
        self.update_color_scheme()
        self.showGrid(x=True, y=True)
        xlabel = getattr(args, 'xlabel', 'X')
        ylabel = getattr(args, 'ylabel', 'Y')
        self.setLabel('bottom', xlabel)
        self.setLabel('left', ylabel)
        self.legend = self.addLegend()
        # For cycling colors (following matplotlib default cycle).
        self.color_cycle = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
                            '#bcbd22', '#17becf']
        self.next_color_index = 0

    def update_color_scheme(self):
        """Update the color palette based on dark_mode.
           Note: The individual dataset colors come from the cycle."""
        if self.dark_mode:
            self.setBackground("k")
            self.getAxis('bottom').setTextPen(pyqtgraph.mkPen("w"))
            self.getAxis('left').setTextPen(pyqtgraph.mkPen("w"))
        else:
            self.setBackground("w")
            self.getAxis('bottom').setTextPen(pyqtgraph.mkPen("k"))
            self.getAxis('left').setTextPen(pyqtgraph.mkPen("k"))

    def get_next_color(self):
        color = self.color_cycle[self.next_color_index]
        self.next_color_index = (self.next_color_index + 1) % len(self.color_cycle)
        return color

    def keyPressEvent(self, event):
        # Modified functionality: Zoom to only data points with positive y.
        if event.key() == Qt.Key_F:
            # Gather all x and y values from all datasets.
            all_x = np.hstack([d['x'] for d in self.datasets]) if self.datasets else None
            all_y = np.hstack([d['y'] for d in self.datasets]) if self.datasets else None
            if all_x is not None and all_y is not None and len(all_x) > 0:
                mask = all_y > 0
                if mask.any():
                    x_min = np.min(all_x[mask])
                    x_max = np.max(all_x[mask])
                    y_min = np.min(all_y[mask])
                    y_max = np.max(all_y[mask])
                else:
                    x_min = np.min(all_x)
                    x_max = np.max(all_x)
                    y_min = np.min(all_y)
                    y_max = np.max(all_y)
                self.getViewBox().setRange(xRange=(x_min, x_max),
                                           yRange=(y_min, y_max), padding=0.1)
            event.accept()
        else:
            super().keyPressEvent(event)

    def append_data(self, data, title):
        """Append a new dataset to the plot.
           data: dictionary with keys 'y' and optionally 'x' (each a tuple with the data).
           title: title string used to label this dataset in legends and fit labels."""
        try:
            y = data['y'][1]
        except KeyError:
            return
        x = data.get('x', (False, None))[1]
        if x is None:
            x = np.arange(len(y))
        x = np.array(x)
        y = np.array(y)
        color = self.get_next_color()
        scatter = self.plot(x, y, pen=None, symbol='o', symbolSize=10,
                            symbolBrush=color)
        dataset = {'x': x, 'y': y, 'title': title, 'color': color,
                   'scatter': scatter, 'fits': {}}
        self.datasets.append(dataset)
        # If interpolation is enabled, draw a dashed line.
        if self.interpolate:
            interp_pen = pyqtgraph.mkPen(color, style=Qt.DashLine, width=2)
            self.plot(x, y, pen=interp_pen)
        # Add an entry in the legend.
        self.legend.addItem(scatter, title)

    def clear_data(self):
        """Clear all plotted datasets and fit curves."""
        self.clear()
        self.datasets = []
        self.next_color_index = 0
        # Recreate the legend since clear() wipes it out.
        self.legend = self.addLegend()

    def toggleFit(self, fit_type, update=False):
        """For each dataset, add (or remove) a fit curve of the specified type.
           If update=True, previously computed fit curves are removed and redrawn."""
        for dataset in self.datasets:
            # Remove existing fit curve for this type if present.
            if fit_type in dataset['fits']:
                self.removeItem(dataset['fits'][fit_type]['curve'])
                self.legend.removeItem(dataset['fits'][fit_type]['label'])
                del dataset['fits'][fit_type]
                if not update:
                    continue

            xdata = dataset['x']
            ydata = dataset['y']
            mask = ydata != 0
            if not mask.any():
                continue
            xdata_fit = xdata[mask]
            ydata_fit = ydata[mask]

            # Get user-specified options if available.
            options = None
            parent = self.parent()
            if parent is not None and hasattr(parent, 'fitOptionsWidget'):
                options = parent.fitOptionsWidget.getOptions()

            # Define the fitting function and default initial guess.
            if fit_type == 'linear':
                def func(x, A, B):
                    return A * x + B
                A0, B0 = 1, 0
                p0 = [A0, B0]
                eq_str = 'A x + B'
            elif fit_type == 'exponential decay':
                def func(x, A, B, C):
                    return A * np.exp(-x/B) + C
                A0 = max(ydata_fit) - min(ydata_fit)
                B0 = 1e4; C0 = min(ydata_fit)
                p0 = [A0, B0, C0]
                eq_str = 'A exp(-x/B/1000) + C'
            elif fit_type == 'lorentzian':
                def func(x, A, x0, gamma, C):
                    return A / (1 + ((x - x0) / gamma)**2) + C
                A0 = max(ydata_fit) - min(ydata_fit)
                x0_0 = xdata_fit[np.argmax(ydata_fit)]
                gamma0 = (max(xdata_fit) - min(xdata_fit)) / 2
                C0 = min(ydata_fit)
                p0 = [A0, x0_0, gamma0, C0]
                eq_str = 'A/(1+((x-x0)/gamma)**2) + C'
            elif fit_type == 'gaussian':
                def func(x, A, mu, sigma, C):
                    return A * np.exp(-((x - mu)**2) / (2 * sigma**2)) + C
                A0 = max(ydata_fit) - min(ydata_fit)
                mu0 = xdata_fit[np.argmax(ydata_fit)]
                sigma0 = (max(xdata_fit) - min(xdata_fit)) / 4
                C0 = min(ydata_fit)
                p0 = [A0, mu0, sigma0, C0]
                eq_str = 'A exp(-((x-mu)**2)/(2 sigma**2)) + C'
            else:
                continue

            # Override default initial guess if provided.
            if options:
                initial = options.get('initial_guesses', {}).get(fit_type, None)
                if initial is not None and len(initial) > 0:
                    p0 = initial
                start, end = options['range']
            else: 
                start, end = 0, -1

            try:
                if np.max(xdata_fit) > 1e3: 
                    x_data_scaled = xdata_fit / 1e3
                popt, pcov = curve_fit(func, x_data_scaled[start:end], ydata_fit[start:end], p0=p0)
            except Exception:
                continue

            x_fit = np.linspace(np.min(x_data_scaled), np.max(x_data_scaled), 200)
            y_fit = func(x_fit, *popt)
            param_str = ', '.join([f'{p:.3e}' for p in popt])
            label_text = f'{dataset["title"]}: Fit {eq_str}, params: {param_str}'
            pen = pyqtgraph.mkPen(dataset['color'], width=2)
            curve_item = self.plot(x_fit*1e3, y_fit, pen=pen, name=label_text)
            dataset['fits'][fit_type] = {'curve': curve_item, 'label': label_text}
            #self.legend.addItem(curve_item, label_text)

    def data_changed(self, data, mods, title):
        """
        Modified original data_changed method to append new data (instead of clearing the plot)
        so that multiple datasets can be plotted continuously.
        Only data points are appended; fit curves are not updated automatically.
        """
        # Use getattr with a fallback to the literal 'y'
        y_key = getattr(self.args, 'y', 'y')
        try:
            y = data[y_key][1]
        except KeyError:
            return
        x = data.get(getattr(self.args, 'x', 'x'), (False, None))[1]
        if x is None:
            x = np.arange(len(y))
        error = data.get(getattr(self.args, 'error', 'error'), (False, None))[1]
        fit = data.get(getattr(self.args, 'fit', 'fit'), (False, None))[1]

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

        # Append the new dataset without updating fits.
        x = np.array(x)
        y = np.array(y)
        color = self.get_next_color()
        scatter = self.plot(x, y, pen=None, symbol='o', symbolSize=10,
                            symbolBrush=color)
        # Plot error bars if available.
        if error is not None:
            if hasattr(error, '__len__') and not isinstance(error, np.ndarray):
                error = np.array(error)
            errbars = pyqtgraph.ErrorBarItem(x=x, y=y, height=error)
            self.addItem(errbars)
        # Plot pre-computed fit if provided.
        if fit is not None:
            xi = np.argsort(x)
            self.plot(x[xi], np.array(fit)[xi])
        # Append the new dataset.
        self.datasets.append({'x': x, 'y': y, 'title': title, 'color': color,
                              'scatter': scatter, 'fits': {}})
        self.setTitle(title)
        # Update view range using all datasets.
        all_x = np.hstack([d['x'] for d in self.datasets])
        all_y = np.hstack([d['y'] for d in self.datasets])
        self.getViewBox().setRange(xRange=(np.min(all_x), np.max(all_x)),
                                   yRange=(np.min(all_y), np.max(all_y)),
                                   padding=0.1)
        # Do not update fits automatically.

# ------------------ Fit Options Widget ------------------
class FitOptionsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Group for Initial Guess Parameters
        guess_group = QGroupBox("Initial Guess Parameters")
        guess_layout = QFormLayout()
        self.lin_guess = QLineEdit()
        self.exp_guess = QLineEdit()
        self.lorentz_guess = QLineEdit()
        self.gauss_guess = QLineEdit()
        guess_layout.addRow("Linear (A,B):", self.lin_guess)
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
        self.start_index.setValue(0)
        self.start_index.setPrefix("Start: ")
        self.end_index = QSpinBox()
        self.end_index.setMinimum(-999)
        self.end_index.setValue(-1)
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
        lin = parse_guess(self.lin_guess.text())
        exp = parse_guess(self.exp_guess.text())
        lorentz = parse_guess(self.lorentz_guess.text())
        gauss = parse_guess(self.gauss_guess.text())
        if lin is not None:
            initial_guesses['linear'] = lin
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
        # Tab 1: Fitting Functions (with fit type checkboxes and Interpolate toggle).
        fit_tab = QWidget()
        fit_layout = QVBoxLayout(fit_tab)
        self.cb_interp = QCheckBox('Interpolate')
        self.cb_lin = QCheckBox('Linear')
        self.cb_exp = QCheckBox('Exponential decay')
        self.cb_lor = QCheckBox('Lorentzian')
        self.cb_gauss = QCheckBox('Gaussian')
        fit_layout.addWidget(self.cb_interp)
        fit_layout.addWidget(self.cb_lin)
        fit_layout.addWidget(self.cb_exp)
        fit_layout.addWidget(self.cb_lor)
        fit_layout.addWidget(self.cb_gauss)
        self.cb_interp.stateChanged.connect(self.toggleInterpolate)
        fit_layout.addStretch()
        self.tabWidget.addTab(fit_tab, 'Fitting functions')
        # Tab 2: Fit Options
        self.fitOptionsWidget = FitOptionsWidget(self)
        self.tabWidget.addTab(self.fitOptionsWidget, 'Fit Options')
        main_layout.addWidget(self.tabWidget, stretch=1)

        # Dark Mode and Clear controls.
        controls_layout = QHBoxLayout()
        self.cb_dark = QCheckBox("Dark Mode")
        self.cb_dark.stateChanged.connect(self.toggleDarkMode)
        controls_layout.addWidget(self.cb_dark)
        self.clearBtn = QPushButton("Clear")
        self.clearBtn.clicked.connect(self.clearPlot)
        controls_layout.addWidget(self.clearBtn)
        left_panel.addLayout(controls_layout)

        self.cb_lin.stateChanged.connect(lambda state: self.onFitToggled('linear', state))
        self.cb_exp.stateChanged.connect(lambda state: self.onFitToggled('exponential decay', state))
        self.cb_lor.stateChanged.connect(lambda state: self.onFitToggled('lorentzian', state))
        self.cb_gauss.stateChanged.connect(lambda state: self.onFitToggled('gaussian', state))
        self.fitOptionsWidget.apply_button.clicked.connect(self.updateFitCurves)

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
        else:
            self.setStyleSheet("")
            self.tabWidget.setStyleSheet("")
        # Redraw existing datasets (colors remain unchanged).
        for dataset in self.plotWidget.datasets:
            dataset['scatter'].setOpts(symbolBrush=dataset['color'])

    def toggleInterpolate(self, state):
        self.plotWidget.interpolate = (state == Qt.Checked)
        # For each dataset, replot the interpolated line if needed.
        for dataset in self.plotWidget.datasets:
            x = dataset['x']
            y = dataset['y']
            if self.plotWidget.interpolate:
                interp_pen = pyqtgraph.mkPen(dataset['color'], style=Qt.DashLine, width=2)
                self.plotWidget.plot(x, y, pen=interp_pen)

    def onFitToggled(self, fit_type, state):
        self.plotWidget.toggleFit(fit_type)

    def updateFitCurves(self):
        if self.cb_lin.isChecked():
            self.plotWidget.toggleFit('linear', update=True)
        if self.cb_exp.isChecked():
            self.plotWidget.toggleFit('exponential decay', update=True)
        if self.cb_lor.isChecked():
            self.plotWidget.toggleFit('lorentzian', update=True)
        if self.cb_gauss.isChecked():
            self.plotWidget.toggleFit('gaussian', update=True)

    def clearPlot(self):
        self.plotWidget.clear_data()

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
            title = f"{x_key} vs {y_key}"
            # Use the data_changed method to add new data.
            self.plotWidget.data_changed(new_data, mods=None, title=title)

    def data_changed(self, data, mods, title):
        # This method simply calls the XYPlot.data_changed() method.
        self.plotWidget.data_changed(data, mods, title)

# --------------------------- Main -----------------------------------
def main():
    applet = TitleApplet(MainWidget)
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
