import sys
sys.path.append('/usr/lib/python3/dist-packages')

from matplotlib import pyplot as plt
import numpy as np
import TimeTagger
import os
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure



class CustomTimeTagger: 
    def __init__(self): 
        self.tagger = TimeTagger.createTimeTagger() 
        self.set_parameters() 
        self.Counter = self.init_counter(self.click_channel, self.bin_width, self.n_bins)
        self.Histogram = self.init_histogram(self.click_channel, self.start_channel, self.bin_width, self.n_bins)


    def set_parameters(self, start_channel=1, click_channel=2, 
                             expected_start=0, expected_stop=10, 
                             bin_width=1000, n_bins=1e6): 
        self.start_channel = start_channel 
        self.click_channel = click_channel 
        self.expected_start = expected_start
        self.expected_stop = expected_stop 
        self.bin_width = bin_width
        self.n_bins = n_bins
    
    def init_counter(self, click_channel, binwidth, n_bins): 
        return TimeTagger.Counter(self.tagger, [click_channel], n_bins, binwidth)
    
    def get_counter_data(self): 
        # FIXME
        return self.Counter.getIndex(), self.Counter.getData()
    
    def init_histogram(self, start_channel, click_channel, binwidth, n_bins): 
        # Create a SynchronizedMeasurements instance that allows you to control all child
        synchronized = TimeTagger.SynchronizedMeasurements(self.tagger)

        # To create synchronized measurement instances, we need a special TimeTagger object
        # that we can obtain by the getTagger method. The returned proxy object is not identical
        # with the "tagger" object we created above. If we pass the "sync_tagger_proxy" object to a
        # measurement, the measurement will NOT start immediately on creation.
        # Instead, the "synchronized" object takes control
        sync_tagger_proxy = synchronized.getTagger()

        # Histogram is very similar to Correlation, but with fixed roles of start and click channel
        # instead of both channels playing both roles.
        hist = TimeTagger.Histogram(tagger=sync_tagger_proxy,
                                    click_channel=start_channel,
                                    start_channel=click_channel,
                                    binwidth=binwidth,
                                    n_bins=n_bins)
        synchronized.startFor(n_bins*binwidth*1e3)
        synchronized.waitUntilFinished()
        return hist
    
    def get_hist_data(self): 
        # FIXME
        return self.Histogram.getIndex(), self.Histogram.getData()
    

class PlottingApp(QWidget):
    def __init__(self, Tagger: CustomTimeTagger):
        super().__init__()
        self.time_tagger = Tagger


        # Initialize the variables
        self.x_min = 0
        self.x_max = 10
        self.is_plotting = False
        self.timer = QTimer(self)

        # Set up the main window
        self.setWindowTitle('Time Tagger')
        self.setGeometry(100, 100, 1000, 600)  # Increased window size for better layout

        # Main layout (horizontal layout with plot on the left and control panel on the right)
        main_layout = QHBoxLayout(self)

        # Plot area (contains two subplots)
        self.figure = Figure(figsize=(8, 7))  # Overall figure size
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)  # Plot area takes the left side

        # Create a vertical layout for the right-side control panel
        control_layout = QVBoxLayout()

        # Add a spacer item to push the control layout to the bottom
        spacer = QSpacerItem(20, 35, QSizePolicy.Minimum, QSizePolicy.Expanding)
        control_layout.addItem(spacer)  # Spacer at the top, pushing everything else to the bottom

        # Channels (put click_channel and start_channel in one line)
        self.channel_layout = QHBoxLayout()
        self.click_channel_input = QLineEdit(self)
        self.click_channel_input.setPlaceholderText('Click')
        self.start_channel_input = QLineEdit(self)
        self.start_channel_input.setPlaceholderText('Start')
        self.channel_layout.addWidget(QLabel("Channels:"))
        self.channel_layout.addWidget(self.click_channel_input)
        self.channel_layout.addWidget(self.start_channel_input)
        control_layout.addLayout(self.channel_layout)

        # Timing (put x_min_input and x_max_input in one line)
        self.timing_layout = QHBoxLayout()
        self.x_min_input = QLineEdit(self)
        self.x_min_input.setPlaceholderText('Expected Start')
        self.x_max_input = QLineEdit(self)
        self.x_max_input.setPlaceholderText('Expected Stop')
        self.timing_layout.addWidget(QLabel("Timing:"))
        self.timing_layout.addWidget(self.x_min_input)
        self.timing_layout.addWidget(self.x_max_input)
        control_layout.addLayout(self.timing_layout)

        # Bins (put bin_width and n_bins in one line)
        self.bins_layout = QHBoxLayout()
        self.bin_width_input = QLineEdit(self)
        self.bin_width_input.setPlaceholderText('Bin Width (ns)')
        self.n_bins_input = QLineEdit(self)
        self.n_bins_input.setPlaceholderText('Number of Bins')
        self.bins_layout.addWidget(QLabel("Bins:"))
        self.bins_layout.addWidget(self.bin_width_input)
        self.bins_layout.addWidget(self.n_bins_input)
        control_layout.addLayout(self.bins_layout)

        # Refresh Rate (one field on one line)
        self.refresh_rate_layout = QHBoxLayout()
        self.plot_refresh_rate = QLineEdit(self)
        self.plot_refresh_rate.setPlaceholderText("Plot Refresh Rate (ms)")
        self.refresh_rate_layout.addWidget(QLabel("Refresh Rate:"))
        self.refresh_rate_layout.addWidget(self.plot_refresh_rate)
        control_layout.addLayout(self.refresh_rate_layout)

        # Data file name
        self.data_filename_layout = QHBoxLayout()
        self.data_filename = QLineEdit(self)
        self.data_filename.setPlaceholderText("Default to current time")
        self.data_filename_layout.addWidget(QLabel("Saving file name:"))
        self.data_filename_layout.addWidget(self.data_filename)
        control_layout.addLayout(self.data_filename_layout)
        
        # Data folder
        self.data_dir_layout = QVBoxLayout()
        self.data_dir = QLineEdit(self)
        self.data_dir.setPlaceholderText("Default to $HOME/time_tagger_data/<date>")
        self.data_dir_layout.addWidget(QLabel("Data saving folder:"))
        self.data_dir_layout.addWidget(self.data_dir)
        control_layout.addLayout(self.data_dir_layout)

        # Add the Start and Stop buttons at the bottom
        self.start_button = QPushButton('Start')
        self.stop_button = QPushButton('Stop')
        self.start_button.clicked.connect(self.start_plotting)
        self.stop_button.clicked.connect(self.stop_plotting)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)

        # Add the Clear Output button
        self.clear_button = QPushButton('Refresh')
        self.clear_button.clicked.connect(self.clear_output)
        control_layout.addWidget(self.clear_button)

        # Add the Save Data button
        self.save_button = QPushButton('Save Data')
        self.save_button.clicked.connect(self.save_data)
        control_layout.addWidget(self.save_button)

        # Add the control layout to the right side of the main layout
        main_layout.addLayout(control_layout)  # Control layout will be on the right side

        # Initialize plots with different subplot sizes
        # Create subplots with custom aspect ratios
        self.gs = self.figure.add_gridspec(2, 1, height_ratios=[5, 2])  # Set height ratios for the subplots
        self.ax1 = self.figure.add_subplot(self.gs[0])  # Top subplot (larger)
        self.ax2 = self.figure.add_subplot(self.gs[1])  # Bottom subplot (smaller)
        
        self.plot_histogram()
        self.plot_counter()
        
        # Set timer for asynchronous updates
        self.timer.timeout.connect(self.update_plots)

    def start_plotting(self):
        # Read inputs from the user
        self.x_min = float(self.x_min_input.text() or self.x_min)
        self.x_max = float(self.x_max_input.text() or self.x_max)
        
        # Custom settings based on new input fields
        self.click_channel = self.click_channel_input.text()
        self.start_channel = int(self.start_channel_input.text() or 1)
        self.expected_start = float(self.x_min_input.text() or 0)
        self.expected_stop = float(self.x_max_input.text() or 10)
        self.bin_width = float(self.bin_width_input.text() or 1)
        self.n_bins = int(self.n_bins_input.text() or 1e6)
        self.plot_refresh_rate_ms = int(self.plot_refresh_rate.text() or 100)
        
        self.update_time_tagger_parameters()
        self.is_plotting = True
        self.timer.start(self.plot_refresh_rate_ms)  # Update rate based on user input

    def stop_plotting(self):
        self.is_plotting = False
        self.timer.stop()

    def update_time_tagger_parameters(self): 
        self.time_tagger.set_parameters(start_channel=self.start_channel, 
                                        click_channel=self.click_channel, 
                                        expected_start=self.expected_start, 
                                        expected_stop=self.expected_stop, 
                                        bin_width=self.bin_width, 
                                        n_bins=self.n_bins)
    def update_plots(self):
        if self.is_plotting:
            self.counter_x, self.counter_y = self.time_tagger.get_counter_data()
            self.hist_x, self.hist_y = self.time_tagger.get_hist_data()
            # Update the data for both plots
            self.plot_histogram(self.hist_x, self.hist_y)
            self.plot_counter(self.counter_x, self.counter_y)

    def plot_histogram(self, x=[], y=[]):
        self.ax1.clear()
        self.ax1.bar(x, height=y, alpha=0.75, color='blue')
        self.ax1.set_title('Histogram')
        self.ax1.set_xlabel('Time (us)')
        self.ax1.set_ylabel(f'Counts')
        self.ax1.grid(True)

    def plot_counter(self, x=[], y=[]):
        self.ax2.clear()
        self.ax2.plot(x, y, color='red')
        self.ax2.set_title('Counter')
        self.ax2.set_xlabel('X')
        self.ax2.set_ylabel('Y')
        self.ax2.grid(True)

        self.canvas.draw()

    def clear_output(self):
        """Clear the plot and reset the data."""
        self.ax1.clear()
        self.ax2.clear()
        self.start_plotting()

    def save_data(self):
        # Determine the directory for saving data
        if self.data_dir.text():
            data_dir = self.data_dir.text()
        else:
            # Default directory: $HOME/time_tagger_data/<date>
            home_dir = os.path.expanduser("~")
            data_dir = os.path.join(home_dir, f"time_tagger_data/{datetime.now().strftime('%Y-%m-%d')}")
        os.makedirs(data_dir, exist_ok=True)

        # Determine the filename for saving data
        if self.data_filename.text():
            data_filename = self.data_filename.text()
        else:
            # Default filename: current timestamp
            data_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Save the plot as a PNG file
        plot_filepath = os.path.join(data_dir, f"{data_filename}.png")
        self.figure.savefig(plot_filepath)
        
        # Save the x and y data as an NPZ file
        data_filepath = os.path.join(data_dir, f"{data_filename}.npz")
        np.savez(data_filepath, counter_x=self.counter_x, counter_y=self.counter_y, 
                                hist_x=self.hist_x, hist_y=self.hist_y)

        print(f">>> Data saved to: {data_filepath}")
        print(f">>> Plot saved to: {plot_filepath}")





if __name__ == '__main__':
    # Initialize the PyQt application
    app = QApplication(sys.argv)
    
    # connect to the TimeTagger
    tagger = CustomTimeTagger()

    # Start the application's event loop
    window = PlottingApp(tagger)
    window.show()
    sys.exit(app.exec_())

