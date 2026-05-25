# -*- mode: python ; coding: utf-8 -*-

import os
import glob
import platform


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
    for f in glob.glob(os.path.join(_models_dir, '*.keras')):
        _datas.append((f, 'models'))


# ── Hidden imports (modules PyInstaller may miss) ─────────────────────
_hiddenimports = [
    'tensorflow',
    'numpy',
    'serial',
    'serial.tools.list_ports',
    'matplotlib',
    'fpdf',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
]


# ── Analysis ──────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(_SRC_DIR, 'main.py')],
    pathex=[_SRC_DIR],
    binaries=[],
    datas=_datas,
    hiddenimports=_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test'],
    noarchive=False,
    optimize=0,
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
#  Linux / Windows — onefile executable
# ═══════════════════════════════════════════════════════════════════════
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='HIVES',
        debug=False,
        bootloader_ignore_signals=False,
        strip=_IS_LINUX,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
