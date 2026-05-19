import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from gui.main_window import SpectroControlUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectroControlUI()
    window.showMaximized()
    sys.exit(app.exec())
