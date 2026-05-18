import sys

from PyQt6.QtWidgets import QApplication

from hives.gui.main_window import SpectroControlUI


def main():
    app = QApplication(sys.argv)
    window = SpectroControlUI()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
