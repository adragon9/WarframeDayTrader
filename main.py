# Package imports
import sys
from pathlib import Path
# Class imports
from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QWidget,
    QPushButton, QVBoxLayout, QLabel,
    QCheckBox, QHBoxLayout, QComboBox,
    QLineEdit, QTextBrowser
)
from PyQt6.QtCore import (
    Qt, QObject, pyqtSignal,
    QThread
)

from PyQt6.QtGui import QIcon
# Splash screen
try:
    import pyi_splash # type:ignore
    pyi_splash.close()
except:
    pass

from scripts import ItemPrice

class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    main_messenger = pyqtSignal(str)
    sub_messenger = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
    def run(self, lineEdit1: QLineEdit):
        try:
            price_recommender = ItemPrice.PriceRecommender(self.main_messenger, self.sub_messenger)
            price_recommender.run(lineEdit1)
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()               
        self.worker_thread = None
        self.searchPlaceHolder = "Enter set or item you'd like info for..."
        self.settings_init()
        self.ui_init()
        
    def ui_init(self):
        # Main Widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        # Main Layout
        self.main_layout = QVBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        # Display
        display_layout = QVBoxLayout()
        self.main_layout.addLayout(display_layout)
        
        self.display = QTextBrowser()
        self.display.setOpenExternalLinks(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display.setPlaceholderText("Awaiting search...")
        
        display_layout.addWidget(self.display)
        
        # Line Edit Groups
        lineEdit_layout = QVBoxLayout()
        self.main_layout.addLayout(lineEdit_layout)
        
        le_layout1 = QHBoxLayout()
        label_group1 = QLabel("Search")
        self.lineEdit_group1 = QLineEdit()
        self.lineEdit_group1.setPlaceholderText(self.searchPlaceHolder)
        searchButton_group1 = QPushButton("Search >")
        
        lineEdit_layout.addLayout(le_layout1)
        le_layout1.addWidget(label_group1)
        le_layout1.addWidget(self.lineEdit_group1)
        le_layout1.addWidget(searchButton_group1)
        
        searchButton_group1.clicked.connect(self.run_button_action)
        self.lineEdit_group1.returnPressed.connect(self.run_button_action)
        
    def settings_init(self):
        pass
        
    def progress_action(self, signal):            
        pass
    
    def main_messenger_manager(self, signal):
        self.display.setHtml(f"""
                             <div style="
                             text-align:center;
                             font-size:12pt;
                             font-family:Calibri;
                             ">
                                {signal}
                             </div>""")
    
    def sub_messenger_manager(self, signal):
        pass
          
    def run_button_action(self):
        """Launch the CPU‑heavy job in a worker thread."""
        if self.worker_thread and self.worker_thread.isRunning():
            return

        # Create the QThread + Worker pair
        self.worker_thread = QThread()
        self.worker = Worker() # keep reference
        self.worker.moveToThread(self.worker_thread)
            
        # Connect signals & slots
        self.worker_thread.started.connect(lambda x=self.lineEdit_group1: self.worker.run(x))
        self.worker.main_messenger.connect(self.main_messenger_manager)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.finished.connect(self.worker_thread.quit)

        self.disable_elements()
        self.worker_thread.start()
        
    def on_worker_finished(self):
        """Called *after* the background thread quits."""
        # Re‑enable elements
        self.enable_elements()
    
    def disable_elements(self):
        # Buttons
        buttons = self.main_widget.findChildren(QPushButton)
        for button in buttons:
            button.setEnabled(False)
        # Checkboxes
        checkboxes = self.main_widget.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.setEnabled(False)
        # Comboboxes
        comboboxes = self.main_widget.findChildren(QComboBox)
        for combobox in comboboxes:
            combobox.setEnabled(False)
        # QTextBrowsers
        textBrowsers = self.main_widget.findChildren(QTextBrowser)
        for textBrowser in textBrowsers:
            textBrowser.setEnabled(False)
            
    def enable_elements(self):
        # Buttons
        buttons = self.main_widget.findChildren(QPushButton)
        for button in buttons:
            button.setEnabled(True)
        # Checkboxes
        checkboxes = self.main_widget.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.setEnabled(True)
        # Comboboxes
        comboboxes = self.main_widget.findChildren(QComboBox)
        for combobox in comboboxes:
            combobox.setEnabled(True)
        # QTextBrowsers
        textBrowsers = self.main_widget.findChildren(QTextBrowser)
        for textBrowser in textBrowsers:
            textBrowser.setEnabled(True)
        
    # Connections
    def update_checkboxes(self):
        pass
        
    def update_comboboxes(self):
        pass

       
if __name__ == "__main__":     
    app = QApplication(sys.argv)

    mainWindow = MainWindow()
    mainWindow.setWindowTitle("Warframe Day Trader")
    windowIcon = QIcon()
    mainWindow.setWindowIcon(QIcon('res\\img\\stonks.ico'))
    mainWindow.setMinimumSize(900, 600)

    mainWindow.show()
    sys.exit(app.exec())