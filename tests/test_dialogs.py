import pytest
from PyQt6.QtWidgets import QDialog

from hives.constants import CAL_BLANCO, CAL_OSCURO
from hives.gui.dialogs import CalibracionDialog, NombreAnalisisDialog


# ── NombreAnalisisDialog ──────────────────────────────────────────────────────

def test_nombre_dialog_accepts_valid_name(qtbot):
    dlg = NombreAnalisisDialog()
    qtbot.addWidget(dlg)
    dlg.input_nombre.setText("MuEstra_001")
    dlg._on_accept()
    assert dlg.result() == QDialog.DialogCode.Accepted
    assert dlg.nombre() == "MuEstra_001"


def test_nombre_dialog_rejects_empty(qtbot):
    dlg = NombreAnalisisDialog()
    qtbot.addWidget(dlg)
    dlg.input_nombre.setText("")
    dlg._on_accept()
    assert dlg.result() != QDialog.DialogCode.Accepted


def test_nombre_dialog_rejects_whitespace_only(qtbot):
    dlg = NombreAnalisisDialog()
    qtbot.addWidget(dlg)
    dlg.input_nombre.setText("   ")
    dlg._on_accept()
    assert dlg.result() != QDialog.DialogCode.Accepted


def test_nombre_dialog_strips_whitespace(qtbot):
    dlg = NombreAnalisisDialog()
    qtbot.addWidget(dlg)
    dlg.input_nombre.setText("  Miel  ")
    dlg._on_accept()
    assert dlg.nombre() == "Miel"


def test_nombre_dialog_cancel(qtbot):
    dlg = NombreAnalisisDialog()
    qtbot.addWidget(dlg)
    dlg.reject()
    assert dlg.result() == QDialog.DialogCode.Rejected


# ── CalibracionDialog ─────────────────────────────────────────────────────────

def test_cal_dialog_tipo_blanco(qtbot):
    dlg = CalibracionDialog()
    qtbot.addWidget(dlg)
    dlg.combo_tipo.setCurrentIndex(0)
    assert dlg.tipo() == CAL_BLANCO


def test_cal_dialog_tipo_oscuro(qtbot):
    dlg = CalibracionDialog()
    qtbot.addWidget(dlg)
    dlg.combo_tipo.setCurrentIndex(1)
    assert dlg.tipo() == CAL_OSCURO


def test_cal_dialog_duracion_default(qtbot):
    dlg = CalibracionDialog()
    qtbot.addWidget(dlg)
    assert dlg.duracion() == 5


def test_cal_dialog_duracion_custom(qtbot):
    dlg = CalibracionDialog()
    qtbot.addWidget(dlg)
    dlg.input_dur.setText("10")
    assert dlg.duracion() == 10


def test_cal_dialog_duracion_non_numeric(qtbot):
    dlg = CalibracionDialog()
    qtbot.addWidget(dlg)
    dlg.input_dur.setText("abc")
    assert dlg.duracion() == 5


def test_cal_dialog_duracion_empty(qtbot):
    dlg = CalibracionDialog()
    qtbot.addWidget(dlg)
    dlg.input_dur.setText("")
    assert dlg.duracion() == 5
