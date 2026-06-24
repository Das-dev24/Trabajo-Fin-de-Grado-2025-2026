import logging
import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from hives.core.paths import ICON_PATH
from hives.gui.main_window import SpectroControlUI
from hives.core.paths import DB_PATH

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, _SRC_DIR)

"""Función para configurar los logs de la aplicación. De forma que podamos ver que es lo que falla en la aplicación"""
# -------------------------------------------------------------------- #
#     Creación de logs de la aplicación para poder saber lo que        #
#     en la app                                                        #
# -------------------------------------------------------------------- #
def _setup_logging():
    log_dir = os.path.dirname(DB_PATH)
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG,
        filename=os.path.join(log_dir, 'hives.log'),
        filemode='w',
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        force=True,
    )
    logging.getLogger(__name__).info("Logging iniciado en %s", os.path.join(log_dir, 'hives.log'))


_setup_logging()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    window = SpectroControlUI()
    window.showMaximized()
    sys.exit(app.exec())
