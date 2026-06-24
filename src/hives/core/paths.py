import os
import sys

'''
Función para obtener la ruta del proyecto
'''
def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )

'''
Función para obtener la ruta temporal de pyinstaller
'''
def _get_meipass():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return _get_base_dir()

'''
Constantes de las rutas del proyecto
'''
_BASE_DIR = _get_base_dir()
_MEIPASS  = _get_meipass()

DB_PATH    = os.path.normpath(os.path.join(_BASE_DIR, 'data', 'data.db'))
MODEL_PATH = os.path.normpath(os.path.join(_MEIPASS, 'models'))
ICON_PATH  = os.path.normpath(os.path.join(_MEIPASS, 'assets', 'hives_icon.png'))
