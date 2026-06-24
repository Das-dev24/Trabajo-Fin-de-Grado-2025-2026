import sqlite3
import pytest
from PyQt6.QtWidgets import QTableWidgetItem

from hives.constants import (
    CAL_BLANCO, CAL_OSCURO,
    MODO_REFLECTANCIA, MODO_TRANSMITANCIA,
)


# ── _compute_mean ─────────────────────────────────────────────────────────────
# -------------------------------------------------------------------- #
#            Modulo de cálculo de medias                               #
# -------------------------------------------------------------------- #

def test_compute_mean_empty(window):
    window.captured_data = []
    assert window._compute_mean() == []


def test_compute_mean_single_row(window):
    row = [float(i) for i in range(18)]
    window.captured_data = [row]
    result = window._compute_mean()
    assert len(result) == 18
    for expected, got in zip(row, result):
        assert got == pytest.approx(expected)


def test_compute_mean_multiple_rows(window):
    window.captured_data = [
        [1.0, 2.0] + [0.0] * 16,
        [3.0, 4.0] + [0.0] * 16,
        [5.0, 6.0] + [0.0] * 16,
    ]
    result = window._compute_mean()
    assert result[0] == pytest.approx(3.0)  # (1+3+5)/3
    assert result[1] == pytest.approx(4.0)  # (2+4+6)/3
    assert result[2] == pytest.approx(0.0)


# -------------------------------------------------------------------- #
#                   Aplicación de las calibraciones                    #
# -------------------------------------------------------------------- #

def _set_cals(win, blanco_vals, oscuro_vals, modo=MODO_REFLECTANCIA):
    win._calibraciones[modo][CAL_BLANCO] = {"valores": blanco_vals, "timestamp": "2025-01-01 00:00:00"}
    win._calibraciones[modo][CAL_OSCURO] = {"valores": oscuro_vals, "timestamp": "2025-01-01 00:00:00"}
    win._led_mode = (modo == MODO_TRANSMITANCIA)
    win._aplicar_calibracion = True


def test_aplicar_correccion_no_calibration(window):
    raw = [5.0] * 18
    result = window._aplicar_correccion(raw)
    assert result == raw


def test_aplicar_correccion_disabled(window):
    _set_cals(window, [10.0] * 18, [2.0] * 18)
    window._aplicar_calibracion = False
    raw = [6.0] * 18
    assert window._aplicar_correccion(raw) == raw


def test_aplicar_correccion_midpoint(window):
    _set_cals(window, [10.0] * 18, [2.0] * 18)
    raw = [6.0] * 18   # (6-2)/(10-2) = 0.5
    result = window._aplicar_correccion(raw)
    assert all(v == pytest.approx(0.5) for v in result)


def test_aplicar_correccion_clamps_max(window):
    _set_cals(window, [10.0] * 18, [2.0] * 18)
    raw = [20.0] * 18  # (20-2)/(10-2) = 2.25 > 1.5
    result = window._aplicar_correccion(raw)
    assert all(v == pytest.approx(1.5) for v in result)


def test_aplicar_correccion_clamps_min(window):
    _set_cals(window, [10.0] * 18, [2.0] * 18)
    raw = [0.0] * 18   # (0-2)/(10-2) = -0.25 < 0
    result = window._aplicar_correccion(raw)
    assert all(v == pytest.approx(0.0) for v in result)


def test_aplicar_correccion_zero_denominator(window):
    _set_cals(window, [5.0] * 18, [5.0] * 18)  # blanco == oscuro → denom = 0
    raw = [5.0] * 18
    result = window._aplicar_correccion(raw)
    assert all(v == pytest.approx(0.0) for v in result)


# -------------------------------------------------------------------- #
#                      Extraer el modo de medición                     #
# -------------------------------------------------------------------- #

def test_get_modo_medicion_reflectancia(window):
    window._led_mode = False
    assert window._get_modo_medicion() == MODO_REFLECTANCIA


def test_get_modo_medicion_transmitancia(window):
    window._led_mode = True
    assert window._get_modo_medicion() == MODO_TRANSMITANCIA


# -------------------------------------------------------------------- #
#                              Calibraciones                           #
# -------------------------------------------------------------------- #

def test_cal_disponible_false_when_missing(window):
    window._aplicar_calibracion = True
    window._led_mode = False
    assert window._cal_disponible_y_activa() is False


def test_cal_disponible_true_when_complete(window):
    window._aplicar_calibracion = True
    window._led_mode = False
    _set_cals(window, [10.0] * 18, [2.0] * 18)
    assert window._cal_disponible_y_activa() is True


def test_cal_disponible_false_when_disabled(window):
    _set_cals(window, [10.0] * 18, [2.0] * 18)
    window._aplicar_calibracion = False  # Desctivamos el aplicar las calibraciones
    assert window._cal_disponible_y_activa() is False


# -------------------------------------------------------------------- #
#                        Set / Get Calibración                         #
# -------------------------------------------------------------------- #

def test_set_cal_and_get_cal(window):
    ts = "2025-06-01 10:00:00"
    vals = [float(i) for i in range(18)]
    window._set_cal(CAL_BLANCO, MODO_REFLECTANCIA, vals, ts)
    cal = window._get_cal(CAL_BLANCO, MODO_REFLECTANCIA)
    assert cal is not None
    assert cal["valores"] == vals
    assert cal["timestamp"] == ts


# -------------------------------------------------------------------- #
#                   Comportamiento al recibir datos                    #
# -------------------------------------------------------------------- #

def test_on_data_appends_to_captured(window):
    window.captured_data.clear()
    window._on_data([1.0] * 18)
    assert len(window.captured_data) == 1
    assert window.captured_data[0] == [1.0] * 18


def test_on_data_updates_readings_label(window):
    window.captured_data.clear()
    window._on_data([1.0] * 18)
    assert window.lbl_readings.text() == "Lecturas: 1"


# -------------------------------------------------------------------- #
#                         Análisis completo                            #
# -------------------------------------------------------------------- #

def test_run_full_analysis_writes_to_db(window, test_db, mocker):
    window.captured_data = [[float(i + 1)] * 18 for i in range(5)]
    window._nombre_analisis = "AnalisisTest"
    mocker.patch.object(window, "_run_inference", return_value=("Manuka", [1.0 / 12] * 12))

    window._run_full_analysis()

    conn = sqlite3.connect(test_db)
    assert conn.execute("SELECT COUNT(*) FROM muestras").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM predicciones").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM analisis").fetchone()[0] == 1
    conn.close()


def test_run_full_analysis_empty_data(window, mocker):
    window.captured_data = []
    spy = mocker.patch.object(window, "_run_inference")
    window._run_full_analysis()
    spy.assert_not_called()
    assert "Sin datos" in window.lbl_sys_status.text()

# -------------------------------------------------------------------- #
#                       Guardado de Calibraciónes                      #
# -------------------------------------------------------------------- #

def test_guardar_calibracion_updates_memory(window):
    window.captured_data = [[3.0] * 18]
    window._cal_tipo_pendiente = CAL_BLANCO
    window._led_mode = False
    window._guardar_calibracion()
    cal = window._get_cal(CAL_BLANCO, MODO_REFLECTANCIA)
    assert cal is not None
    assert len(cal["valores"]) == 18
    assert all(v == pytest.approx(3.0) for v in cal["valores"])

# -------------------------------------------------------------------- #
#                      Aplicación de filtros en historial              #
# -------------------------------------------------------------------- #

def _setup_filter_table(win, rows):
    """Populate the history table widget with test rows (bypassing DB)."""
    table = win._history_table
    table.setRowCount(len(rows))
    for i, (nombre, modo, calibrado, clase) in enumerate(rows):
        table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
        table.setItem(i, 1, QTableWidgetItem(nombre))
        table.setItem(i, 2, QTableWidgetItem("2025-01-01"))
        table.setItem(i, 3, QTableWidgetItem(modo))
        table.setItem(i, 4, QTableWidgetItem(calibrado))
        table.setItem(i, 5, QTableWidgetItem(clase))


def test_apply_filters_text_search(window):
    _setup_filter_table(window, [
        ("Muestra A", "reflectancia", "Sí", "Manuka"),
        ("Muestra B", "reflectancia", "Sí", "Clover"),
    ])
    window.history_search.setText("manuka")  # lanza el filtro
    assert not window._history_table.isRowHidden(0)
    assert window._history_table.isRowHidden(1)


def test_apply_filters_modo_filter(window):
    _setup_filter_table(window, [
        ("Muestra A", "reflectancia",  "Sí", "Manuka"),
        ("Muestra B", "transmitancia", "Sí", "Clover"),
    ])
    window.filter_modo.setCurrentIndex(1)  # "Reflectancia"
    assert not window._history_table.isRowHidden(0)
    assert window._history_table.isRowHidden(1)


def test_apply_filters_cal_filter_si(window):
    _setup_filter_table(window, [
        ("Muestra A", "reflectancia", "Sí", "Manuka"),
        ("Muestra B", "reflectancia", "No", "Clover"),
    ])
    window.filter_cal.setCurrentIndex(1)  # "Sí"
    assert not window._history_table.isRowHidden(0)
    assert window._history_table.isRowHidden(1)


def test_apply_filters_clase_filter(window):
    _setup_filter_table(window, [
        ("Muestra A", "reflectancia", "Sí", "Manuka"),
        ("Muestra B", "reflectancia", "Sí", "Clover"),
    ])
    window.filter_clase.addItem("Manuka")
    idx = window.filter_clase.findText("Manuka")
    window.filter_clase.setCurrentIndex(idx)
    assert not window._history_table.isRowHidden(0)
    assert window._history_table.isRowHidden(1)


# -------------------------------------------------------------------- #
#                    Estilos de los botones                            #
# -------------------------------------------------------------------- #

def test_btn_style_disabled(window):
    style = window._btn_style("primary", enabled=False)
    assert "background: #ddd" in style
    assert "color: #aaa" in style


def test_btn_style_primary(window):
    style = window._btn_style("primary", enabled=True)
    assert "#3a7ebf" in style


def test_btn_style_danger(window):
    style = window._btn_style("danger")
    assert "#c0392b" in style


def test_btn_style_toggle_off(window):
    style = window._btn_style("toggle_off")
    assert "#555" in style


def test_btn_style_toggle_on(window):
    style = window._btn_style("toggle_on")
    assert "#2980b9" in style


def test_btn_style_warning(window):
    style = window._btn_style("warning")
    assert "#e67e22" in style


def test_btn_style_unknown_kind(window):
    style = window._btn_style("unknown")
    assert "#e0e0e0" in style


# -------------------------------------------------------------------- #
#                    Navegación                                        #
# -------------------------------------------------------------------- #

def test_navigate_to_0(window):
    window._on_data([1.0] * 18)
    window._navigate(0)
    assert window.stack.currentIndex() == 0


def test_navigate_to_1(window):
    window._navigate(1)
    assert window.stack.currentIndex() == 1


def test_navigate_to_2(window):
    window._on_data([1.0] * 18)
    window._navigate(2)
    assert window.stack.currentIndex() == 2

# -------------------------------------------------------------------- #
#                     Manejo de errores y cierre                       #
# -------------------------------------------------------------------- #

def test_on_error_sets_status(window):
    window._on_error("test error")
    assert "test error" in window.lbl_sys_status.text()


def test_clear_graph_while_not_scanning(window):
    window._on_data([1.0] * 18)
    assert len(window.captured_data) == 1
    window._clear_graph()
    assert len(window.captured_data) == 0
    assert window.lbl_readings.text() == "Lecturas: 0"
    assert not window.btn_save_csv.isEnabled()


def test_clear_graph_while_scanning_keeps_csv_enabled(window, qtbot):
    window._scanning = True
    window._on_data([1.0] * 18)
    window._clear_graph()
    assert len(window.captured_data) == 0


# -------------------------------------------------------------------- #
#                 Aplicación de calibraciones                          #
# -------------------------------------------------------------------- #

def test_on_aplicar_cal_toggled_on(window):
    window._on_aplicar_cal_toggled(True)
    assert window._aplicar_calibracion is True


def test_on_aplicar_cal_toggled_off(window):
    window._aplicar_calibracion = True
    window._on_aplicar_cal_toggled(False)
    assert window._aplicar_calibracion is False

# -------------------------------------------------------------------- #
#                    Cambio tipo captura                               #
# -------------------------------------------------------------------- #

def test_actualizar_label_modo_calibracion_reflectancia(window):
    window._led_mode = False
    window._actualizar_label_modo_calibracion()
    assert "REFLECTANCIA" in window.lbl_cal_titulo.text()


def test_actualizar_label_modo_calibracion_transmitancia(window):
    window._led_mode = True
    window._actualizar_label_modo_calibracion()
    assert "TRANSMITANCIA" in window.lbl_cal_titulo.text()

# -------------------------------------------------------------------- #
#                        Apliación de filtros                            #
# -------------------------------------------------------------------- #

def test_apply_filters_combined_text_and_modo(window):
    _setup_filter_table(window, [
        ("Manuka Ref",   "reflectancia",  "Sí", "Manuka"),
        ("Manuka Trans", "transmitancia", "Sí", "Manuka"),
        ("Clover Ref",   "reflectancia",  "Sí", "Clover"),
    ])
    window.history_search.setText("manuka")
    window.filter_modo.setCurrentIndex(1)  # "Reflectancia"
    assert not window._history_table.isRowHidden(0)  # Que coincia con el filtro
    assert window._history_table.isRowHidden(1)       # Que no coincida con el modo
    assert window._history_table.isRowHidden(2)       # Que no coincida con el texto
