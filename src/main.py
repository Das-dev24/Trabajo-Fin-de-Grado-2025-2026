import sys
import os

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, _SRC_DIR)

from PyQt6.QtWidgets import QApplication
from hives.gui.main_window import SpectroControlUI

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectroControlUI()
    window.showMaximized()
    sys.exit(app.exec())
