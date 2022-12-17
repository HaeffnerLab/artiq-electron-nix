import traceback
from PyQt5.QtWidgets import QMessageBox


class SafeFunction:
    def __init__(self, func):
        self.func = func
    
    def error_message(self, message):
        msg = QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText(str(message))
        msg.exec_()

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except TypeError: # sometimes the function is called with self.f()
            return self.__call__(*args[1:], **kwargs)
        except:
            self.error_message(traceback.format_exc())