# -*- mode: python ; coding: utf-8 -*-

import os
import glob
import platform

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# ── Platform detection ────────────────────────────────────────────────
_SYSTEM   = platform.system()
_IS_WIN   = _SYSTEM == 'Windows'
_IS_MACOS = _SYSTEM == 'Darwin'
_IS_LINUX = _SYSTEM == 'Linux'
_MACHINE  = platform.machine()


# ── Project root (where this spec file lives) ─────────────────────────
_PROJECT_ROOT = SPECPATH
_SRC_DIR      = os.path.join(_PROJECT_ROOT, 'src')


# ── Data files ────────────────────────────────────────────────────────
_datas = []
_models_dir = os.path.join(_PROJECT_ROOT, 'models')
if os.path.isdir(_models_dir):
    for f in glob.glob(os.path.join(_models_dir, '*.json')):
        _datas.append((f, 'models'))
    # clases.json con los nombres de las clases del modelo
    _json_path = os.path.join(_models_dir, 'clases.json')
    if os.path.isfile(_json_path):
        _datas.append((_json_path, 'models'))

# Matplotlib needs its mpl-data folder (fonts, rcParams, etc.)
_datas += collect_data_files('matplotlib')

# App icon
_icon_png = os.path.join(_PROJECT_ROOT, 'assets', 'hives_icon.png')
if os.path.isfile(_icon_png):
    _datas.append((_icon_png, 'assets'))
_icon_ico = os.path.join(_PROJECT_ROOT, 'assets', 'hives.ico')
if os.path.isfile(_icon_ico):
    _datas.append((_icon_ico, 'assets'))


# ── Hidden imports (modules PyInstaller may miss) ─────────────────────
_hiddenimports = [
    # XGBoost
    'xgboost',
    # scikit-learn (necesario para xgboost) y sus dependencias
    'sklearn',
    'scipy',
    'joblib',
    'threadpoolctl',
    # NumPy
    'numpy',
    # PySerial
    'serial',
    'serial.tools.list_ports',
    # Matplotlib (backend QtAgg + core)
    'matplotlib',
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.backend_qt',
    'matplotlib.backends.backend_agg',
    'matplotlib.pyplot',
    'matplotlib.figure',
    'matplotlib.font_manager',
    # Matplotlib dependencies
    'kiwisolver',
    'pyparsing',
    'contourpy',
    'packaging',
    'fonttools',
    'dateutil',
    # PDF
    'fpdf',
    # PyQt6
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.QtSvg',
] + collect_submodules('matplotlib.backends')


# ── Analysis ──────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(_SRC_DIR, 'main.py')],
    pathex=[_SRC_DIR],
    binaries=[],
    datas=_datas,
    hiddenimports=_hiddenimports,
    hookspath=[os.path.join(_SRC_DIR, 'hooks')],
    hooksconfig={},
    runtime_hooks=[os.path.join(_SRC_DIR, 'runtime_hook.py')],
    excludes=[
        # GUI / test toolkits
        'tkinter', 'test',
        'lib2to3', 'curses', 'idlelib', 'turtledemo',
        # Unused data-science libraries (reduce build size significantly)
        'pandas', 'cv2',
        'setuptools',
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)


# ═══════════════════════════════════════════════════════════════════════
#  macOS — .app bundle (one-dir inside .app wrapper)
# ═══════════════════════════════════════════════════════════════════════
if _IS_MACOS:
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name='HIVES',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=_MACHINE,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='HIVES',
    )

    app = BUNDLE(
        coll,
        name='HIVES.app',
        icon=None,
        bundle_identifier='com.hives.app',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleDisplayName': 'HIVES',
            'CFBundleName': 'HIVES',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleIdentifier': 'com.hives.app',
        },
    )

# ═══════════════════════════════════════════════════════════════════════
#  Linux / Windows — one-dir executable (faster startup, faster build)
# ═══════════════════════════════════════════════════════════════════════
else:
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name='HIVES',
        debug=False,
        bootloader_ignore_signals=False,
        strip=_IS_LINUX,
        upx=False,
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=os.path.join(_PROJECT_ROOT, 'assets', 'hives.ico') if _IS_WIN else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=_IS_LINUX,
        upx=False,
        upx_exclude=[],
        name='HIVES',
    )
