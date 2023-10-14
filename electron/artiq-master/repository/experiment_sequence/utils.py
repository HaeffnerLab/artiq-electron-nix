


#### GUI utility functions ####

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(358, 126)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
       
        self.combo = QComboBox(Dialog)
        self.combo.addItem("count_ROI")
        self.string_selected = "count_ROI" #auto select first option
        self.combo.addItem("count_tot")
        self.combo.move(50, 50)

        self.qlabel = QLabel()
        self.qlabel.move(50,16)
        self.combo.activated[str].connect(self.onChanged)      

    def onChanged(self, text):
        self.qlabel.setText(text)
        self.qlabel.adjustSize()
        self.string_selected = text


# Creating a worker class
class Worker(QObject):

    finished = pyqtSignal()
    # progress = pyqtSignal(int)
    # result = pyqtSignal('QVariant')

    # def __init__(self, function, args):
    #     super().__init__()
    #     self.function = function
    #     self.args = args
    def __init__(self, function):
        super().__init__()
        self.function = function
        

    def run(self):
        self.function()
        # self.function(self.args)
        # for i in range(60):
        #     time.sleep(1)
        #     self.progress.emit(i+1)
        # self.result.emit(res)
        self.finished.emit()
