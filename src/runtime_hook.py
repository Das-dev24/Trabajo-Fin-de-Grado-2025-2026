import os
import sys

# Windows: TF's DLLs land in _MEIPASS/tensorflow/ (not in _MEIPASS/ root).
# PyInstaller's bootloader only adds _MEIPASS itself to the DLL search path,
# so Windows can't resolve tensorflow_cc.2.dll when loading the TF extension.
if getattr(sys, 'frozen', False) and os.name == 'nt' and hasattr(os, 'add_dll_directory'):
    for _subdir in ('tensorflow', os.path.join('tensorflow', 'python')):
        _dll_dir = os.path.join(sys._MEIPASS, _subdir)
        if os.path.isdir(_dll_dir):
            os.add_dll_directory(_dll_dir)

os.environ['MPLBACKEND'] = 'QtAgg'

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')
os.environ.setdefault('OMP_NUM_THREADS', '4')
