import os
import sqlite3
import csv
import ast

from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QComboBox,
    QStackedWidget, QFileDialog, QMessageBox, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QLineEdit, QDialog,
    QCheckBox, QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon

import serial.tools.list_ports

from hives.constants import (
    CAL_BLANCO, CAL_OSCURO,
    BAUDRATE, WAVELENGTHS, CSV_HEADER,
    DB_PATH, MODEL_PATH,
    MODO_REFLECTANCIA, MODO_TRANSMITANCIA,
)
from hives.core.sensor import SerialReader
from hives.core.database import seed_database
from hives.gui.dialogs import NombreAnalisisDialog, CalibracionDialog
from hives.gui.widgets import SpectralCanvas
from hives.gui.workers import SerialWorker
from hives.inference.model import load_model, run_inference
from hives.core.paths import ICON_PATH


class SpectroControlUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setWindowTitle("HIVES — Clasificación de Miel")
        self.setGeometry(100, 100, 1100, 720)
        self.setMinimumSize(800, 550)

        self.reader: SerialReader = None
        self.worker: SerialWorker = None
        self.captured_data: list  = []
        self.cycles_edit = QLineEdit("15")
        self._connected  = False
        self._scanning   = False
        self._led_mode   = False

        self._nombre_analisis: str = ""
        self._model = load_model(MODEL_PATH)

        self._calibraciones: dict = {
            MODO_REFLECTANCIA:  {CAL_BLANCO: None, CAL_OSCURO: None},
            MODO_TRANSMITANCIA: {CAL_BLANCO: None, CAL_OSCURO: None},
        }
        self._modo_captura: str = "analisis"
        self._cal_tipo_pendiente: str = ""
        self._aplicar_calibracion: bool = True
        self._capturas_manuales: list = []

        self.setStyleSheet("QMainWindow, QWidget { background-color: #f0f0f0; color: #222; }")
        self._init_ui()
        self._scan_ports()
        self._cargar_calibraciones_db()

    def _init_ui(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        seed_database()
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_live_page())
        self.stack.addWidget(self._build_history_page())
        self.stack.addWidget(self._build_medidas_page())

        rl.addWidget(self.stack)
        rl.addWidget(self._build_bottom_bar())
        root.addWidget(right)

    # ------------------------------------------------------------------ #
    #  Inferencia                                                          #
    # ------------------------------------------------------------------ #

    def _run_inference(self, norm_vector: list) -> tuple:
        return run_inference(self._model, norm_vector)

    # ------------------------------------------------------------------ #
    #  Construcción de la UI                                               #
    # ------------------------------------------------------------------ #

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("QFrame { background: #2b2b2b; border: none; }")
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(12, 16, 12, 16)
        lay.setSpacing(4)

        title = QLabel("HIVES")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff; padding: 8px 4px 16px;")
        lay.addWidget(title)

        self._nav_btns = []
        nav_labels = ["Captura en vivo", "Historial", "Medidas"]
        for i, lbl in enumerate(nav_labels):
            btn = QPushButton(lbl)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setStyleSheet(self._nav_style(i == 0))
            btn.clicked.connect(lambda _, idx=i: self._navigate(idx))
            lay.addWidget(btn)
            self._nav_btns.append(btn)

        lay.addSpacing(20)

        lay.addWidget(self._section_label("Puerto serie"))
        port_row = QHBoxLayout()
        self.combo_port = QComboBox()
        self.combo_port.setStyleSheet(
            "QComboBox { background: #3c3c3c; color: #eee; border: 1px solid #555; "
            "padding: 4px 6px; border-radius: 3px; }"
            "QComboBox QAbstractItemView { background: #3c3c3c; color: #eee; }"
        )
        btn_refresh = QPushButton("⟳")
        btn_refresh.setFixedWidth(30)
        btn_refresh.setStyleSheet(
            "QPushButton { background: #3c3c3c; color: #ccc; border: 1px solid #555; "
            "border-radius: 3px; padding: 4px; }"
        )
        btn_refresh.setToolTip("Actualizar puertos")
        btn_refresh.clicked.connect(self._scan_ports)
        port_row.addWidget(self.combo_port)
        port_row.addWidget(btn_refresh)
        lay.addLayout(port_row)

        lbl_baud = QLabel(f"Baud: {BAUDRATE}")
        lbl_baud.setStyleSheet("color: #666; font-size: 11px; padding: 2px 0;")
        lay.addWidget(lbl_baud)

        lay.addSpacing(8)

        self.btn_connect = QPushButton("Conectar sensor")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.setStyleSheet(self._btn_style("primary"))
        self.btn_connect.clicked.connect(self._toggle_connection)
        lay.addWidget(self.btn_connect)

        lay.addSpacing(16)

        lay.addWidget(self._section_label("Modo de medición"))
        self.btn_led = QPushButton("Reflectancia")
        self.btn_led.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_led.setEnabled(False)
        self.btn_led.setStyleSheet(self._btn_style("toggle_off"))
        self.btn_led.clicked.connect(self._toggle_led)
        lay.addWidget(self.btn_led)

        lay.addStretch()

        model_ok  = self._model is not None
        lbl_model = QLabel("● Modelo cargado" if model_ok else "○ Sin modelo")
        lbl_model.setStyleSheet(
            f"color: {'#5a5' if model_ok else '#a55'}; font-size: 10px; padding: 2px 0;"
        )
        lay.addWidget(lbl_model)

        self.lbl_conn_status = QLabel("Desconectado")
        self.lbl_conn_status.setStyleSheet("color: #666; font-size: 11px;")
        self.lbl_conn_status.setWordWrap(True)
        lay.addWidget(self.lbl_conn_status)
        return sidebar

    def _build_live_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 12, 16, 8)
        lay.setSpacing(10)

        header = QHBoxLayout()
        self.lbl_readings = QLabel("Lecturas: 0")
        self.lbl_readings.setStyleSheet("color: #888; font-size: 12px;")
        header.addStretch()
        header.addWidget(self.lbl_readings)
        lay.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(self._build_params_panel())
        left.addWidget(self._build_calibration_panel())
        left.addWidget(self._build_diagnostics_panel())
        left.addStretch()
        body.addLayout(left, 1)
        body.addWidget(self._build_graph_panel(), 3)
        lay.addLayout(body)
        return page

    def _build_params_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        lay.addWidget(self._section_label("Parámetros del instrumento", dark=False))

        rows = [
            ("Canales",            "18  (410–940 nm)"),
            ("Ciclos integración", "100"),
            ("Ganancia",           "x16"),
            ("Modo",               "Continuo"),
            ("Duración",           "15"),
        ]
        grid = QGridLayout()
        grid.setSpacing(4)
        for r, (label, val) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #666; font-size: 11px;")
            grid.addWidget(lbl, r, 0)
            if label == "Duración":
                self.cycles_edit = QLineEdit()
                self.cycles_edit.setText(val)
                self.cycles_edit.setPlaceholderText("Duración análisis (s)")
                self.cycles_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
                grid.addWidget(self.cycles_edit, r, 1)
            else:
                v = QLabel(val)
                v.setStyleSheet("color: #222; font-size: 11px;")
                v.setAlignment(Qt.AlignmentFlag.AlignRight)
                grid.addWidget(v, r, 1)
        lay.addLayout(grid)
        return frame

    def _build_diagnostics_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        lay.addWidget(self._section_label("Estado", dark=False))

        grid = QGridLayout()
        grid.setSpacing(4)

        def row(r, label, default):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #666; font-size: 11px;")
            val = QLabel(default)
            val.setStyleSheet("color: #222; font-size: 11px;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lbl, r, 0)
            grid.addWidget(val, r, 1)
            return val

        self.diag_port = row(0, "Puerto",   "—")
        self.diag_conn = row(1, "Conexión", "Desconectado")
        self.diag_scan = row(2, "Escaneo",  "En espera")
        self.diag_led  = row(3, "LEDs",     "Reflectancia")
        self.diag_buf  = row(4, "Buffer",   "0 filas")

        lay.addLayout(grid)
        return frame

    def _build_graph_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #f8f8f8; border: 1px solid #ddd; border-radius: 4px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        header = QHBoxLayout()
        header.addWidget(QLabel("Espectro en tiempo real"))
        header.addStretch()
        btn_clear = QPushButton("Limpiar")
        btn_clear.setStyleSheet(self._btn_style("secondary"))
        btn_clear.clicked.connect(self._clear_graph)
        header.addWidget(btn_clear)
        lay.addLayout(header)

        self.canvas = SpectralCanvas()
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay.addWidget(self.canvas)
        return frame

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 16)
        lay.setSpacing(8)

        lbl = QLabel("Historial de datos")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(lbl)

        # ── Barra de filtros ───────────────────────────────────────────────
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; }"
        )
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(10, 8, 10, 8)
        fl.setSpacing(10)

        _combo_style = (
            "QComboBox { background: white; border: 1px solid #ccc; border-radius: 3px; "
            "padding: 4px 6px; font-size: 12px; min-width: 110px; }"
            "QComboBox QAbstractItemView { background: white; }"
        )
        _line_style = (
            "QLineEdit { border: 1px solid #ccc; border-radius: 3px; padding: 4px 8px; "
            "font-size: 12px; background: white; }"
        )
        _lbl_style = "color: #666; font-size: 11px; font-weight: bold; background: transparent; border: none;"

        lbl_b = QLabel("Buscar:")
        lbl_b.setStyleSheet(_lbl_style)
        fl.addWidget(lbl_b)
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Nombre o clase…")
        self.history_search.setClearButtonEnabled(True)
        self.history_search.setFixedHeight(28)
        self.history_search.setStyleSheet(_line_style)
        self.history_search.textChanged.connect(self._apply_filters)
        fl.addWidget(self.history_search, 1)

        lbl_m = QLabel("Modo:")
        lbl_m.setStyleSheet(_lbl_style)
        fl.addWidget(lbl_m)
        self.filter_modo = QComboBox()
        self.filter_modo.addItems(["Todos", "Reflectancia", "Transmitancia"])
        self.filter_modo.setStyleSheet(_combo_style)
        self.filter_modo.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.filter_modo)

        lbl_c = QLabel("Calibrado:")
        lbl_c.setStyleSheet(_lbl_style)
        fl.addWidget(lbl_c)
        self.filter_cal = QComboBox()
        self.filter_cal.addItems(["Todos", "Sí", "No"])
        self.filter_cal.setStyleSheet(_combo_style)
        self.filter_cal.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.filter_cal)

        lbl_cl = QLabel("Clase:")
        lbl_cl.setStyleSheet(_lbl_style)
        fl.addWidget(lbl_cl)
        self.filter_clase = QComboBox()
        self.filter_clase.addItem("Todas")
        self.filter_clase.setStyleSheet(_combo_style)
        self.filter_clase.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self.filter_clase)

        lay.addWidget(filter_frame)

        # ── Tabla ──────────────────────────────────────────────────────────
        self._history_table = self._build_history_table()
        lay.addWidget(self._history_table)

        # ── Poblar combo de clases con valores de la BD ────────────────────
        self._populate_clase_filter()

        return page

    def _build_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(52)
        bar.setStyleSheet("QFrame { background: #eeeeee; border-top: 1px solid #ccc; border-radius: 0; }")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        self.lbl_sys_status = QLabel("Listo")
        self.lbl_sys_status.setStyleSheet("color: #555; font-size: 12px;")
        self.lbl_last_save = QLabel("")
        self.lbl_last_save.setStyleSheet("color: #999; font-size: 11px;")

        self.btn_calibrar = QPushButton("Calibrar ▾")
        self.btn_calibrar.setFixedWidth(105)
        self.btn_calibrar.setEnabled(False)
        self.btn_calibrar.setStyleSheet(self._btn_style("secondary", enabled=False))
        self.btn_calibrar.setToolTip("Captura para usar como referencia (blanco u oscuro)")

        cal_menu = QMenu(self)
        cal_menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #ccc; padding: 4px; }"
            "QMenu::item { padding: 6px 18px; font-size: 12px; color: #222; }"
            "QMenu::item:selected { background: #3a7ebf; color: white; }"
        )
        cal_menu.addAction("Calibrar blanco (100%)").triggered.connect(
            lambda: self._request_calibracion(CAL_BLANCO)
        )
        cal_menu.addAction("Calibrar oscuro (0%)").triggered.connect(
            lambda: self._request_calibracion(CAL_OSCURO)
        )
        cal_menu.addSeparator()
        cal_menu.addAction("Calibración avanzada…").triggered.connect(
            self._request_calibracion_dialog
        )
        self.btn_calibrar.setMenu(cal_menu)

        self.btn_manual = QPushButton("Modo manual")
        self.btn_manual.setFixedWidth(110)
        self.btn_manual.setEnabled(False)
        self.btn_manual.setStyleSheet(self._btn_style("warning", enabled=False))
        self.btn_manual.setToolTip("Captura libre, sin guardar en BD. Exportable a CSV.")
        self.btn_manual.clicked.connect(self._request_manual)

        self.btn_start = QPushButton("Hacer captura")
        self.btn_start.setFixedWidth(140)
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(self._btn_style("primary", enabled=False))
        self.btn_start.clicked.connect(self._request_scan)

        self.btn_stop = QPushButton("■  Parar")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._btn_style("danger", enabled=False))
        self.btn_stop.clicked.connect(self._stop_acquisition)

        self.btn_save_csv = QPushButton("Exportar CSV")
        self.btn_save_csv.setFixedWidth(105)
        self.btn_save_csv.setEnabled(False)
        self.btn_save_csv.setStyleSheet(self._btn_style("secondary", enabled=False))
        self.btn_save_csv.clicked.connect(self._save_csv)

        self.btn_save_manual = QPushButton("Exportar manual")
        self.btn_save_manual.setFixedWidth(120)
        self.btn_save_manual.setEnabled(False)
        self.btn_save_manual.setStyleSheet(self._btn_style("secondary", enabled=False))
        self.btn_save_manual.setToolTip("Exporta capturas manuales (se borran al cerrar)")
        self.btn_save_manual.clicked.connect(self._save_manual_csv)

        lay.addWidget(self.lbl_sys_status)
        lay.addSpacing(8)
        lay.addWidget(self.lbl_last_save)
        lay.addStretch()

        self.chk_prediccion = QCheckBox("Predecir")
        self.chk_prediccion.setChecked(True)
        self.chk_prediccion.setToolTip("Ejecutar inferencia del modelo tras la captura")
        self.chk_prediccion.setStyleSheet(
            "QCheckBox { color: #555; font-size: 12px; background: transparent; spacing: 6px; }"
            "QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #777; "
            "border-radius: 2px; background: #e0e0e0; }"
            "QCheckBox::indicator:checked { background-color: #3a7ebf; border-color: #3a7ebf; "
            "image: url(none); }"
        )
        lay.addWidget(self.chk_prediccion)
        lay.addWidget(self.btn_calibrar)
        lay.addWidget(self.btn_manual)
        lay.addWidget(self.btn_start)
        lay.addWidget(self.btn_stop)
        lay.addWidget(self.btn_save_csv)
        lay.addWidget(self.btn_save_manual)
        return bar

    def _build_calibration_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        header = QHBoxLayout()
        self.lbl_cal_titulo = QLabel("CALIBRACIÓN · REFLECTANCIA")
        self.lbl_cal_titulo.setStyleSheet(
            "color: #999; font-size: 10px; font-weight: bold; padding: 2px 0;"
        )
        header.addWidget(self.lbl_cal_titulo)
        header.addStretch()
        self.chk_aplicar_cal = QCheckBox("Aplicar")
        self.chk_aplicar_cal.setChecked(True)
        self.chk_aplicar_cal.setToolTip(
            "Aplicar corrección R = (raw − oscuro) / (blanco − oscuro) a las lecturas"
        )
        self.chk_aplicar_cal.setStyleSheet(
            "QCheckBox { color: #555; font-size: 10px; spacing: 4px; }"
            "QCheckBox::indicator { width: 12px; height: 12px; border: 1px solid #777; "
            "border-radius: 2px; background: #e0e0e0; }"
            "QCheckBox::indicator:checked { background-color: #3a7ebf; border-color: #3a7ebf; }"
        )
        self.chk_aplicar_cal.toggled.connect(self._on_aplicar_cal_toggled)
        header.addWidget(self.chk_aplicar_cal)
        lay.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(4)

        lbl_b = QLabel("Blanco")
        lbl_b.setStyleSheet("color: #666; font-size: 11px;")
        self.lbl_cal_blanco = QLabel("Sin calibrar")
        self.lbl_cal_blanco.setStyleSheet("color: #a55; font-size: 11px;")
        self.lbl_cal_blanco.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(lbl_b, 0, 0)
        grid.addWidget(self.lbl_cal_blanco, 0, 1)

        lbl_o = QLabel("Oscuro")
        lbl_o.setStyleSheet("color: #666; font-size: 11px;")
        self.lbl_cal_oscuro = QLabel("Sin calibrar")
        self.lbl_cal_oscuro.setStyleSheet("color: #a55; font-size: 11px;")
        self.lbl_cal_oscuro.setAlignment(Qt.AlignmentFlag.AlignRight)
        grid.addWidget(lbl_o, 1, 0)
        grid.addWidget(self.lbl_cal_oscuro, 1, 1)

        lay.addLayout(grid)

        btn_clear_cal = QPushButton("Limpiar calibraciones")
        btn_clear_cal.setStyleSheet(self._btn_style("secondary"))
        btn_clear_cal.clicked.connect(self._limpiar_calibraciones)
        lay.addWidget(btn_clear_cal)

        return frame

    # ------------------------------------------------------------------ #
    #  Estilos                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _btn_style(kind: str, enabled: bool = True) -> str:
        base = "border-radius: 3px; padding: 5px 10px; font-size: 12px; border: none;"
        if not enabled:
            return base + "background: #ddd; color: #aaa;"
        if kind == "primary":
            return base + "background: #3a7ebf; color: white;"
        if kind == "danger":
            return base + "background: #c0392b; color: white;"
        if kind == "toggle_off":
            return base + "background: #ddd; color: #555; border: 1px solid #bbb;"
        if kind == "toggle_on":
            return base + "background: #2980b9; color: white;"
        if kind == "warning":
            return base + "background: #e67e22; color: white;"
        return base + "background: #e0e0e0; color: #333; border: 1px solid #ccc;"

    @staticmethod
    def _nav_style(active: bool) -> str:
        base = ("QPushButton { text-align: left; padding: 10px 12px; border: none; "
                "border-radius: 3px; font-size: 13px; ")
        if active:
            return base + "background: #3a7ebf; color: white; }"
        return base + "background: transparent; color: #aaa; } QPushButton:hover { background: #3c3c3c; color: #eee; }"

    @staticmethod
    def _section_label(text: str, dark: bool = True) -> QLabel:
        lbl = QLabel(text.upper())
        color = "#666" if dark else "#999"
        lbl.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; padding: 2px 0;")
        return lbl

    # ------------------------------------------------------------------ #
    #  Navegación y puertos                                                #
    # ------------------------------------------------------------------ #

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setStyleSheet(self._nav_style(i == index))

    def _scan_ports(self):
        self.combo_port.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.combo_port.addItems(ports)
        else:
            self.combo_port.addItem("Sin puertos disponibles")

    # ------------------------------------------------------------------ #
    #  Conexión y LEDs                                                     #
    # ------------------------------------------------------------------ #

    def _toggle_connection(self):
        if not self._connected:
            port = self.combo_port.currentText()
            if not port or "Sin puertos" in port:
                QMessageBox.warning(self, "Sin puerto", "Selecciona un puerto serie válido primero.")
                return

            self.reader = SerialReader(port=port, baudrate=BAUDRATE)
            if self.reader.connect():
                self._connected = True
                self.btn_connect.setText("Desconectar")
                self.btn_connect.setStyleSheet(self._btn_style("danger"))
                self.btn_start.setEnabled(True)
                self.btn_start.setStyleSheet(self._btn_style("primary"))
                self.btn_led.setEnabled(True)
                self.btn_calibrar.setEnabled(True)
                self.btn_calibrar.setStyleSheet(self._btn_style("secondary"))
                self.btn_manual.setEnabled(True)
                self.btn_manual.setStyleSheet(self._btn_style("warning"))
                self.lbl_conn_status.setText(f"Conectado: {port}")
                self.lbl_conn_status.setStyleSheet("color: #5a5; font-size: 11px;")
                self.diag_port.setText(port)
                self.diag_conn.setText("Conectado")
                self._set_status("Conectado")
            else:
                self.reader = None
                QMessageBox.critical(self, "Error de conexión", f"No se pudo conectar a {port}.")
        else:
            self._stop_acquisition()
            self.reader.disconnect()
            self.reader     = None
            self._connected = False

            self.btn_connect.setText("Conectar sensor")
            self.btn_connect.setStyleSheet(self._btn_style("primary"))
            self.btn_start.setEnabled(False)
            self.btn_start.setStyleSheet(self._btn_style("primary", enabled=False))
            self.btn_led.setEnabled(False)
            self.btn_led.setText("Reflectancia")
            self.btn_calibrar.setEnabled(False)
            self.btn_calibrar.setStyleSheet(self._btn_style("secondary", enabled=False))
            self.btn_manual.setEnabled(False)
            self.btn_manual.setStyleSheet(self._btn_style("warning", enabled=False))
            self.btn_led.setStyleSheet(self._btn_style("toggle_off"))

            self.lbl_conn_status.setText("Desconectado")
            self.lbl_conn_status.setStyleSheet("color: #666; font-size: 11px;")
            self.diag_port.setText("—")
            self.diag_conn.setText("Desconectado")
            self._set_status("Listo")

    def _toggle_led(self):
        if not self._connected:
            return
        if self.reader.change_leds():
            self._led_mode = self.reader.leds_enabled
            if self._led_mode:
                self.btn_led.setText("Transmitancia")
                self.btn_led.setStyleSheet(self._btn_style("toggle_on"))
                self.diag_led.setText("Transmitancia")
            else:
                self.btn_led.setText("Reflectancia")
                self.btn_led.setStyleSheet(self._btn_style("toggle_off"))
                self.diag_led.setText("Reflectancia")
            self._actualizar_label_modo_calibracion()
            self._actualizar_estado_calibracion()
        else:
            QMessageBox.warning(self, "Error LED", "No se pudo cambiar el modo de los LEDs.")

    # ------------------------------------------------------------------ #
    #  Adquisición                                                         #
    # ------------------------------------------------------------------ #

    def _request_scan(self):
        if not self._connected or self._scanning:
            return
        dlg = NombreAnalisisDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._nombre_analisis = dlg.nombre()
        self._modo_captura = "analisis"
        self._start_acquisition()

    def _request_calibracion(self, tipo: str):
        if not self._connected or self._scanning:
            return
        modo   = self._get_modo_medicion()
        nombre = "blanco" if tipo == CAL_BLANCO else "oscuro"
        detalle = (
            "Coloca el estándar reflectante (o medio transparente, según modo)."
            if tipo == CAL_BLANCO else
            "Tapa el sensor o apaga la luz para registrar el ruido de fondo."
        )
        if QMessageBox.question(
            self, f"Calibración: {nombre} ({modo})",
            f"Vas a capturar la referencia de {nombre} para el modo «{modo}».\n\n{detalle}\n\n¿Iniciar?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        ) != QMessageBox.StandardButton.Ok:
            return
        self._cal_tipo_pendiente = tipo
        self._modo_captura = "calibracion"
        self._start_acquisition(duracion_override_ms=5000)

    def _request_calibracion_dialog(self):
        if not self._connected or self._scanning:
            return
        dlg = CalibracionDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        self._cal_tipo_pendiente = dlg.tipo()
        self._modo_captura = "calibracion"
        self._start_acquisition(duracion_override_ms=dlg.duracion() * 1000)

    def _guardar_calibracion(self):
        mean = self._compute_mean()
        if not mean:
            self._set_status("Calibración fallida: sin datos")
            return
        tipo = self._cal_tipo_pendiente
        modo = self._get_modo_medicion()
        ts   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self._set_cal(tipo, modo, mean, ts)
        self._actualizar_estado_calibracion(tipo)
        self._persistir_calibracion(tipo, mean, ts, modo)

        n      = len(self.captured_data)
        nombre = "blanco" if tipo == CAL_BLANCO else "oscuro"
        self.lbl_last_save.setText(f"Calibración {nombre} ({modo}) OK  |  {ts}")
        self._set_status(
            f"Calibración «{nombre}» en {modo} registrada (media de {n} lecturas)"
        )

    def _request_manual(self):
        if not self._connected or self._scanning:
            return
        self._modo_captura = "manual"
        self._set_status("Modo manual — pulsa Parar para terminar")
        self._start_acquisition(duracion_override_ms=10 ** 9)

    def _guardar_manual(self):
        if not self.captured_data:
            self._set_status("Captura manual vacía")
            return
        mean = self._compute_mean()
        ts   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        n    = len(self.captured_data)

        modo        = self._get_modo_medicion()
        cal_completa = (self._get_cal(CAL_BLANCO, modo) is not None
                        and self._get_cal(CAL_OSCURO, modo) is not None)
        corregido = self._aplicar_correccion(mean) if cal_completa else None
        self._capturas_manuales.append({
            "timestamp":            ts,
            "n_lecturas":           n,
            "raw":                  mean,
            "corregido":            corregido,
            "modo_medicion":        modo,
            "calibracion_aplicada": self._cal_disponible_y_activa(),
        })

        self.btn_save_manual.setEnabled(True)
        self.btn_save_manual.setStyleSheet(self._btn_style("secondary"))
        self.lbl_last_save.setText(f"Manual #{len(self._capturas_manuales)} ({n} lect.)  |  {ts}")
        self._set_status(f"Captura manual guardada en memoria (total: {len(self._capturas_manuales)})")

    def _start_acquisition(self, duracion_override_ms: int = None):
        if not self._connected or self._scanning:
            return
        if not self.reader.start_scanning():
            QMessageBox.critical(self, "Error de escaneo", "No se pudo iniciar el escaneo.")
            return

        if self.reader.serial_connection:
            self.reader.serial_connection.reset_input_buffer()

        if duracion_override_ms is not None:
            duracion_ms = duracion_override_ms
        else:
            texto       = self.cycles_edit.text().strip()
            duracion_ms = (int(texto) if texto.isdigit() else 15) * 1000

        self._scanning = True
        self.captured_data.clear()

        self.worker = SerialWorker(self.reader)
        self.worker.data_received.connect(self._on_data)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(self._btn_style("primary", enabled=False))
        self.btn_calibrar.setEnabled(False)
        self.btn_calibrar.setStyleSheet(self._btn_style("secondary", enabled=False))
        self.btn_manual.setEnabled(False)
        self.btn_manual.setStyleSheet(self._btn_style("warning", enabled=False))
        self.btn_stop.setEnabled(True)
        self.btn_stop.setStyleSheet(self._btn_style("danger"))
        self.btn_save_csv.setEnabled(False)
        self.btn_save_csv.setStyleSheet(self._btn_style("secondary", enabled=False))
        self.diag_scan.setText("Escaneando")

        if self._modo_captura == "calibracion":
            self._set_status(f"Calibrando «{self._cal_tipo_pendiente}»…")
        elif self._modo_captura == "manual":
            self._set_status("Modo manual — capturando…")
        else:
            self._set_status(f"Adquiriendo «{self._nombre_analisis}»…")

        self._acq_timer = QTimer()
        self._acq_timer.setSingleShot(True)
        self._acq_timer.timeout.connect(self._stop_acquisition)
        self._acq_timer.start(duracion_ms)

    def _stop_acquisition(self):
        if not self._scanning:
            return

        if hasattr(self, '_acq_timer') and self._acq_timer.isActive():
            self._acq_timer.stop()

        if self.worker:
            self.worker.stop()
            self.worker = None
        if self.reader:
            self.reader.stop_scanning()
        self._scanning = False

        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet(self._btn_style("primary"))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(self._btn_style("danger", enabled=False))

        has_data = bool(self.captured_data)
        self.btn_save_csv.setEnabled(has_data)
        self.btn_save_csv.setStyleSheet(self._btn_style("secondary", enabled=has_data))

        self.btn_calibrar.setEnabled(True)
        self.btn_calibrar.setStyleSheet(self._btn_style("secondary"))
        self.btn_manual.setEnabled(True)
        self.btn_manual.setStyleSheet(self._btn_style("warning"))

        self.diag_scan.setText("En espera")

        if not has_data:
            self._set_status("Listo")
            self._modo_captura = "analisis"
            return

        if self._modo_captura == "calibracion":
            self._guardar_calibracion()
        elif self._modo_captura == "manual":
            self._guardar_manual()
        else:
            if self.chk_prediccion.isChecked():
                self._set_status("Analizando…")
                self._run_full_analysis()
            else:
                self._set_status("Guardando muestra…")
                self._save_sample_only()

        self._modo_captura = "analisis"

    # ------------------------------------------------------------------ #
    #  Persistencia                                                        #
    # ------------------------------------------------------------------ #

    def _run_full_analysis(self):
        mean = self._compute_mean()
        if not mean:
            self._set_status("Sin datos para analizar")
            return

        peak = max(mean) if max(mean) > 0 else 1.0
        norm = [round(v / peak, 6) for v in mean]

        clase, probs = self._run_inference(norm)

        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS muestras (
                    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                    espectro_raw         TEXT    NOT NULL,
                    espectro_normalizado TEXT    NOT NULL,
                    modo_medicion        VARCHAR(32) NOT NULL DEFAULT 'reflectancia',
                    calibracion_aplicada INTEGER    NOT NULL DEFAULT 0,
                    notas                TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS predicciones (
                    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                    clase_miel            VARCHAR(255),
                    vector_probabilidades TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analisis (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_analisis VARCHAR(255) NOT NULL,
                    timestamp       DATETIME     NOT NULL,
                    id_muestra      INTEGER      NOT NULL,
                    id_prediccion   INTEGER,
                    FOREIGN KEY (id_muestra)    REFERENCES muestras(id)     ON DELETE CASCADE,
                    FOREIGN KEY (id_prediccion) REFERENCES predicciones(id) ON DELETE SET NULL
                )
            """)

            cur.execute(
                "INSERT INTO muestras (espectro_raw, espectro_normalizado, "
                "modo_medicion, calibracion_aplicada) VALUES (?, ?, ?, ?)",
                (str(mean), str(norm),
                 self._get_modo_medicion(),
                 int(self._cal_disponible_y_activa())),
            )
            id_muestra = cur.lastrowid

            cur.execute(
                "INSERT INTO predicciones (clase_miel, vector_probabilidades) VALUES (?, ?)",
                (clase, str(probs)),
            )
            id_prediccion = cur.lastrowid

            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "INSERT INTO analisis (nombre_analisis, timestamp, id_muestra, id_prediccion) "
                "VALUES (?, ?, ?, ?)",
                (self._nombre_analisis, ts, id_muestra, id_prediccion),
            )

            conn.commit()
            conn.close()

            n = len(self.captured_data)
            self.lbl_last_save.setText(f"«{self._nombre_analisis}» → {clase}  |  {ts}")
            self._set_status(f"Análisis completado: {clase}  (media de {n} lecturas)")
            self._refresh_history()
            self._refresh_medidas()

        except sqlite3.Error as e:
            self._set_status("Error al guardar en DB")
            QMessageBox.critical(self, "Error de base de datos", str(e))

    def _save_sample_only(self):
        mean = self._compute_mean()
        if not mean:
            self._set_status("Sin datos para guardar")
            return

        peak = max(mean) if max(mean) > 0 else 1.0
        norm = [round(v / peak, 6) for v in mean]

        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS muestras (
                    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                    espectro_raw         TEXT    NOT NULL,
                    espectro_normalizado TEXT    NOT NULL,
                    modo_medicion        VARCHAR(32) NOT NULL DEFAULT 'reflectancia',
                    calibracion_aplicada INTEGER    NOT NULL DEFAULT 0,
                    notas                TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analisis (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_analisis VARCHAR(255) NOT NULL,
                    timestamp       DATETIME     NOT NULL,
                    id_muestra      INTEGER      NOT NULL,
                    id_prediccion   INTEGER,
                    FOREIGN KEY (id_muestra)    REFERENCES muestras(id)     ON DELETE CASCADE,
                    FOREIGN KEY (id_prediccion) REFERENCES predicciones(id) ON DELETE SET NULL
                )
            """)

            cur.execute(
                "INSERT INTO muestras (espectro_raw, espectro_normalizado, "
                "modo_medicion, calibracion_aplicada) VALUES (?, ?, ?, ?)",
                (str(mean), str(norm),
                 self._get_modo_medicion(),
                 int(self._cal_disponible_y_activa())),
            )
            id_muestra = cur.lastrowid

            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cur.execute(
                "INSERT INTO analisis (nombre_analisis, timestamp, id_muestra, id_prediccion) "
                "VALUES (?, ?, ?, ?)",
                (self._nombre_analisis, ts, id_muestra, None),
            )

            conn.commit()
            conn.close()

            n = len(self.captured_data)
            self.lbl_last_save.setText(f"«{self._nombre_analisis}» guardado sin predicción  |  {ts}")
            self._set_status(f"Muestra guardada  (media de {n} lecturas, sin clasificar)")
            self._refresh_history()
            self._refresh_medidas()

        except sqlite3.Error as e:
            self._set_status("Error al guardar en DB")
            QMessageBox.critical(self, "Error de base de datos", str(e))

    def _on_data(self, values: list):
        self.captured_data.append(values)
        n = len(self.captured_data)
        self.lbl_readings.setText(f"Lecturas: {n}")
        self.diag_buf.setText(f"{n} filas")

        if self._modo_captura == "calibracion":
            self.canvas.update_data(values)
        else:
            self.canvas.update_data(self._aplicar_correccion(values))

    def _on_error(self, msg: str):
        self._set_status(f"Error: {msg}")

    def _clear_graph(self):
        self.captured_data.clear()
        self.lbl_readings.setText("Lecturas: 0")
        self.diag_buf.setText("0 filas")
        self.canvas.clear_plot()
        if not self._scanning:
            self.btn_save_csv.setEnabled(False)
            self.btn_save_csv.setStyleSheet(self._btn_style("secondary", enabled=False))

    def _save_csv(self):
        mean = self._compute_mean()
        if not mean:
            return

        db_rows = []
        try:
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute("""
                SELECT m.espectro_normalizado, m.modo_medicion, m.calibracion_aplicada,
                       p.clase_miel, p.vector_probabilidades
                FROM muestras m
                LEFT JOIN analisis a     ON m.id = a.id_muestra
                LEFT JOIN predicciones p ON a.id_prediccion = p.id
            """)
            for norm, modo, cal_apl, clase, probs in cur.fetchall():
                try:
                    espectro = ast.literal_eval(norm)
                    db_rows.append((espectro, modo or "", int(cal_apl or 0),
                                    clase or "", probs or ""))
                except (ValueError, SyntaxError):
                    continue
            conn.close()
        except sqlite3.Error:
            pass

        default = f"espectro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", default, "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    CSV_HEADER + ["modo_medicion", "calibracion_aplicada",
                                  "clase_miel", "vector_probabilidades"]
                )
                if db_rows:
                    for espectro, modo, cal_apl, clase, probs in db_rows:
                        writer.writerow(espectro + [modo, cal_apl, clase, probs])
                else:
                    peak = max(mean) if max(mean) > 0 else 1.0
                    norm = [round(v / peak, 6) for v in mean]
                    writer.writerow(
                        norm + [self._get_modo_medicion(),
                                int(self._cal_disponible_y_activa()),
                                "", ""]
                    )

            self.lbl_last_save.setText(f"CSV guardado {datetime.now().strftime('%H:%M:%S')}")
            self._set_status("CSV guardado")
        except OSError as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    def _save_manual_csv(self):
        if not self._capturas_manuales:
            QMessageBox.information(self, "Sin datos", "No hay capturas manuales que exportar.")
            return
        default = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar capturas manuales", default, "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(
                    ["timestamp", "n_lecturas", "modo_medicion", "calibracion_aplicada", "tipo_dato"]
                    + CSV_HEADER
                )
                for cap in self._capturas_manuales:
                    w.writerow(
                        [cap["timestamp"], cap["n_lecturas"], cap["modo_medicion"],
                         int(cap["calibracion_aplicada"]), "raw"]
                        + cap["raw"]
                    )
                    if cap["corregido"] is not None:
                        w.writerow(
                            [cap["timestamp"], cap["n_lecturas"], cap["modo_medicion"],
                             int(cap["calibracion_aplicada"]), "corregido"]
                            + cap["corregido"]
                        )
            self._set_status(f"Exportadas {len(self._capturas_manuales)} capturas manuales")
            self.lbl_last_save.setText(f"CSV manual {datetime.now().strftime('%H:%M:%S')}")
        except OSError as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    # ── Construcción y recarga de la tabla de historial ──────────────────── #

    def _build_history_table(self) -> QTableWidget:
        """Crea la QTableWidget con los datos de la BD y un botón PDF por fila."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute('''
                SELECT a.id, a.nombre_analisis, a.timestamp,
                       m.modo_medicion, m.calibracion_aplicada,
                       p.clase_miel
                FROM analisis a
                LEFT JOIN muestras m     ON a.id_muestra   = m.id
                LEFT JOIN predicciones p ON a.id_prediccion = p.id
                ORDER BY a.timestamp DESC
            ''')
            datos = cursor.fetchall()
            conn.close()
        except sqlite3.Error:
            datos = []

        cabeceras = ["ID", "Nombre", "Fecha", "Modo", "Calibrado", "Clase", ""]
        table = QTableWidget()
        table.setColumnCount(len(cabeceras))
        table.setRowCount(len(datos))
        table.setHorizontalHeaderLabels(cabeceras)

        for i, fila in enumerate(datos):
            for j, valor in enumerate(fila):
                if j == 4:
                    valor = "Sí" if valor else "No"
                text = str(valor) if valor is not None else "—"
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                table.setItem(i, j, item)

            # Botón PDF en la última columna
            btn = QPushButton("PDF")
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton { background: #3a7ebf; color: white; border: none; "
                "border-radius: 3px; padding: 2px 12px; font-size: 11px; font-weight: bold; }"
                "QPushButton:hover { background: #2e6ea3; }"
                "QPushButton:pressed { background: #245d8c; }"
            )
            analisis_id = int(fila[0])
            btn.clicked.connect(lambda _, aid=analisis_id: self._generate_single_pdf(aid))
            table.setCellWidget(i, len(cabeceras) - 1, btn)

        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(
            "QTableWidget { gridline-color: #e0e0e0; font-size: 12px; }"
            "QTableWidget::item:selected { background: #cde4f7; color: #222; }"
            "QTableWidget { alternate-background-color: #f7f9fc; }"
        )

        hdr = table.horizontalHeader()
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Columna del botón: ancho fijo
        hdr.setSectionResizeMode(len(cabeceras) - 1, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(len(cabeceras) - 1, 60)
        hdr.setStyleSheet(
            "QHeaderView::section { background: #e8eef5; font-weight: bold; "
            "padding: 6px 4px; border: none; border-bottom: 1px solid #ccc; }"
        )

        table.verticalHeader().setVisible(False)
        return table

    def _refresh_history(self):
        """Reconstruye la tabla tras insertar un nuevo análisis."""
        history_page = self.stack.widget(1)
        layout = history_page.layout()

        layout.removeWidget(self._history_table)
        self._history_table.deleteLater()

        self._history_table = self._build_history_table()
        layout.addWidget(self._history_table)

        self._populate_clase_filter()
        self._apply_filters()

    def _populate_clase_filter(self):
        """Rellena el combo de clases con los valores únicos de la BD."""
        current = self.filter_clase.currentText()
        self.filter_clase.blockSignals(True)
        self.filter_clase.clear()
        self.filter_clase.addItem("Todas")
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT clase_miel FROM predicciones WHERE clase_miel IS NOT NULL ORDER BY clase_miel")
            for (cls,) in cur.fetchall():
                self.filter_clase.addItem(cls)
            conn.close()
        except sqlite3.Error:
            pass
        # Restaurar selección previa si existe
        idx = self.filter_clase.findText(current)
        if idx >= 0:
            self.filter_clase.setCurrentIndex(idx)
        self.filter_clase.blockSignals(False)

    # ── Filtros ────────────────────────────────────────────────────────────── #

    def _apply_filters(self, _=None):
        """Aplica todos los filtros activos sobre la tabla."""
        text_filter = self.history_search.text().strip().lower()
        modo_filter = self.filter_modo.currentText().lower()
        cal_filter  = self.filter_cal.currentText()
        clase_filter = self.filter_clase.currentText()

        # Columnas: 0=ID, 1=Nombre, 2=Fecha, 3=Modo, 4=Calibrado, 5=Clase
        for row in range(self._history_table.rowCount()):
            visible = True

            # Filtro de texto libre (busca en nombre y clase)
            if text_filter:
                nombre = (self._history_table.item(row, 1).text().lower()
                          if self._history_table.item(row, 1) else "")
                clase  = (self._history_table.item(row, 5).text().lower()
                          if self._history_table.item(row, 5) else "")
                if text_filter not in nombre and text_filter not in clase:
                    visible = False

            # Filtro por modo
            if visible and modo_filter != "todos":
                modo_cell = (self._history_table.item(row, 3).text().lower()
                             if self._history_table.item(row, 3) else "")
                if modo_cell != modo_filter:
                    visible = False

            # Filtro por calibrado
            if visible and cal_filter != "Todos":
                cal_cell = (self._history_table.item(row, 4).text()
                            if self._history_table.item(row, 4) else "")
                if cal_cell != cal_filter:
                    visible = False

            # Filtro por clase
            if visible and clase_filter != "Todas":
                clase_cell = (self._history_table.item(row, 5).text()
                              if self._history_table.item(row, 5) else "")
                if clase_cell != clase_filter:
                    visible = False

            self._history_table.setRowHidden(row, not visible)

    # ── Generación de PDF individual (botón por fila) ─────────────────────── #

    def _fetch_analisis_data(self, analisis_id: int) -> dict | None:
        """Consulta la BD y devuelve un dict con los datos del análisis."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute('''
                SELECT a.nombre_analisis, a.timestamp,
                       m.modo_medicion, m.calibracion_aplicada,
                       m.espectro_normalizado,
                       p.clase_miel, p.vector_probabilidades
                FROM analisis a
                LEFT JOIN muestras     m ON a.id_muestra   = m.id
                LEFT JOIN predicciones p ON a.id_prediccion = p.id
                WHERE a.id = ?
            ''', (analisis_id,))
            row = cur.fetchone()
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error de base de datos", str(e))
            return None

        if row is None:
            return None

        nombre, timestamp, modo, calibrado, espectro_str, clase, probs_str = row
        try:
            espectro = ast.literal_eval(espectro_str) if espectro_str else []
        except (ValueError, SyntaxError):
            espectro = []
        try:
            probs = ast.literal_eval(probs_str) if probs_str else []
        except (ValueError, SyntaxError):
            probs = []

        return {
            "id":        analisis_id,
            "nombre":    nombre or "—",
            "timestamp": timestamp or "—",
            "modo":      modo or "—",
            "calibrado": bool(calibrado),
            "espectro":  espectro,
            "clase":     clase or "—",
            "probs":     probs,
            "confianza": max(probs) if probs else 0.0,
        }

    def _generate_single_pdf(self, analisis_id: int):
        """Genera un informe PDF para un análisis concreto."""
        data = self._fetch_analisis_data(analisis_id)
        if data is None:
            QMessageBox.warning(self, "Sin datos",
                                "No se encontró el análisis en la base de datos.")
            return

        default_name = f"informe_{analisis_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar informe PDF", default_name, "PDF Files (*.pdf)"
        )
        if not path:
            return

        try:
            from hives.reports.pdf_report import generate_pdf
            generate_pdf(
                path=path,
                analisis_id=data["id"],
                nombre=data["nombre"],
                timestamp=data["timestamp"],
                modo=data["modo"],
                calibrado=data["calibrado"],
                espectro=data["espectro"],
                clase=data["clase"],
                confianza=data["confianza"],
                probabilidades=data["probs"],
            )
            self._set_status(f"Informe PDF generado: {path}")
            self.lbl_last_save.setText(f"PDF guardado {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", str(e))

    # ------------------------------------------------------------------ #
    #  Calibración                                                         #
    # ------------------------------------------------------------------ #

    def _actualizar_estado_calibracion(self, tipo: str = None):
        if tipo is None:
            self._actualizar_estado_calibracion(CAL_BLANCO)
            self._actualizar_estado_calibracion(CAL_OSCURO)
            return
        cal = self._get_cal(tipo)
        lbl = self.lbl_cal_blanco if tipo == CAL_BLANCO else self.lbl_cal_oscuro
        if cal is None:
            lbl.setText("Sin calibrar")
            lbl.setStyleSheet("color: #a55; font-size: 11px;")
        else:
            try:
                dt    = datetime.strptime(cal["timestamp"], '%Y-%m-%d %H:%M:%S')
                label = f"OK · {dt.strftime('%H:%M')}"
            except (ValueError, KeyError):
                label = "OK"
            lbl.setText(label)
            lbl.setStyleSheet("color: #5a5; font-size: 11px;")

    def _limpiar_calibraciones(self):
        if QMessageBox.question(
            self, "Limpiar calibraciones",
            "¿Borrar TODAS las calibraciones (blanco y oscuro, en ambos modos)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self._calibraciones = {
            MODO_REFLECTANCIA:  {CAL_BLANCO: None, CAL_OSCURO: None},
            MODO_TRANSMITANCIA: {CAL_BLANCO: None, CAL_OSCURO: None},
        }
        self._actualizar_estado_calibracion()
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM calibraciones")
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass
        self._set_status("Calibraciones eliminadas (todos los modos)")

    def _on_aplicar_cal_toggled(self, checked: bool):
        self._aplicar_calibracion = checked
        self._set_status(f"Corrección por calibración {'aplicada' if checked else 'desactivada'}")

    def _persistir_calibracion(self, tipo: str, valores: list, ts: str, modo: str):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS calibraciones (
                    tipo          VARCHAR(16) NOT NULL,
                    modo_medicion VARCHAR(32) NOT NULL DEFAULT 'reflectancia',
                    valores       TEXT        NOT NULL,
                    timestamp     DATETIME    NOT NULL,
                    PRIMARY KEY (tipo, modo_medicion),
                    CHECK (tipo          IN ('blanco', 'oscuro')),
                    CHECK (modo_medicion IN ('reflectancia', 'transmitancia'))
                )
            """)
            cur.execute(
                "INSERT OR REPLACE INTO calibraciones (tipo, modo_medicion, valores, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (tipo, modo, str(valores), ts),
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.warning(self, "Calibración", f"No se pudo persistir en DB:\n{e}")

    def _cargar_calibraciones_db(self):
        try:
            if not os.path.exists(DB_PATH):
                return
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute("PRAGMA table_info(calibraciones)")
            cols = [row[1] for row in cur.fetchall()]
            if not cols:
                conn.close()
                return
            if 'modo_medicion' in cols:
                cur.execute("SELECT tipo, modo_medicion, valores, timestamp FROM calibraciones")
                rows = [(t, m, v, ts) for t, m, v, ts in cur.fetchall()]
            else:
                cur.execute("SELECT tipo, valores, timestamp FROM calibraciones")
                rows = [(t, MODO_REFLECTANCIA, v, ts) for t, v, ts in cur.fetchall()]
            conn.close()

            for tipo, modo, valores_str, ts in rows:
                try:
                    valores = ast.literal_eval(valores_str)
                    if isinstance(valores, list) and len(valores) == 18:
                        self._set_cal(tipo, modo, valores, ts)
                except (ValueError, SyntaxError):
                    pass
            self._actualizar_estado_calibracion()
        except sqlite3.Error:
            pass

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _compute_mean(self) -> list:
        n = len(self.captured_data)
        if n == 0:
            return []
        num_channels = len(self.captured_data[0])
        return [
            round(sum(row[ch] for row in self.captured_data) / n, 6)
            for ch in range(num_channels)
        ]

    def _set_status(self, text: str):
        self.lbl_sys_status.setText(text)

    def _get_modo_medicion(self) -> str:
        return MODO_TRANSMITANCIA if self._led_mode else MODO_REFLECTANCIA

    def _cal_disponible_y_activa(self) -> bool:
        if not self._aplicar_calibracion:
            return False
        modo = self._get_modo_medicion()
        return (self._get_cal(CAL_BLANCO, modo) is not None
                and self._get_cal(CAL_OSCURO, modo) is not None)

    def _get_cal(self, tipo: str, modo: str = None):
        modo = modo or self._get_modo_medicion()
        return self._calibraciones.get(modo, {}).get(tipo)

    def _set_cal(self, tipo: str, modo: str, valores: list, ts: str):
        self._calibraciones.setdefault(
            modo, {CAL_BLANCO: None, CAL_OSCURO: None}
        )[tipo] = {"valores": valores, "timestamp": ts}

    def _actualizar_label_modo_calibracion(self):
        modo = self._get_modo_medicion().upper()
        self.lbl_cal_titulo.setText(f"CALIBRACIÓN · {modo}")

    def _aplicar_correccion(self, raw: list) -> list:
        if not self._aplicar_calibracion:
            return raw
        modo   = self._get_modo_medicion()
        blanco = self._get_cal(CAL_BLANCO, modo)
        oscuro = self._get_cal(CAL_OSCURO, modo)
        if blanco is None or oscuro is None:
            return raw
        b_vals, o_vals = blanco["valores"], oscuro["valores"]
        if len(b_vals) != len(raw) or len(o_vals) != len(raw):
            return raw
        out = []
        for r, b, o in zip(raw, b_vals, o_vals):
            denom = b - o
            out.append(0.0 if denom <= 0 else max(0.0, min((r - o) / denom, 1.5)))
        return out

    # ------------------------------------------------------------------ #
    #  Página de medidas (espectros de la tabla muestras)                   #
    # ------------------------------------------------------------------ #

    def _build_medidas_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 32, 32, 16)
        lay.setSpacing(10)

        header = QHBoxLayout()
        lbl = QLabel("Medidas")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(lbl)
        header.addStretch()

        lbl_tipo = QLabel("Mostrar:")
        lbl_tipo.setStyleSheet("color: #555; font-size: 12px;")
        header.addWidget(lbl_tipo)
        self.combo_medidas_tipo = QComboBox()
        self.combo_medidas_tipo.addItems(["Normalizado", "Raw (sin normalizar)"])
        self.combo_medidas_tipo.setStyleSheet(
            "QComboBox { background: white; border: 1px solid #ccc; "
            "border-radius: 3px; padding: 4px 8px; font-size: 12px; }"
        )
        self.combo_medidas_tipo.currentIndexChanged.connect(self._refresh_medidas)
        header.addWidget(self.combo_medidas_tipo)

        btn_export = QPushButton("Exportar CSV")
        btn_export.setStyleSheet(self._btn_style("secondary"))
        btn_export.clicked.connect(self._save_medidas_csv)
        header.addWidget(btn_export)
        lay.addLayout(header)

        lbl2 = QLabel("Espectros almacenados en la base de datos.")
        lbl2.setStyleSheet("color: #888; margin-bottom: 8px;")
        lay.addWidget(lbl2)

        lay.addWidget(self._get_medidas_table())
        return page

    def _get_medidas_table(self) -> QTableWidget:
        usar_raw = (self.combo_medidas_tipo.currentIndex() == 1
                    if hasattr(self, 'combo_medidas_tipo') else False)
        col_espectro = "espectro_raw" if usar_raw else "espectro_normalizado"

        cabeceras = ["ID", "Modo", "Calibrado"] + CSV_HEADER + ["Notas"]
        table = QTableWidget()
        table.setColumnCount(len(cabeceras))
        table.setHorizontalHeaderLabels(cabeceras)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

        try:
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute(
                f"SELECT id, modo_medicion, calibracion_aplicada, "
                f"{col_espectro}, notas FROM muestras ORDER BY id DESC"
            )
            rows = cur.fetchall()
            conn.close()
        except sqlite3.Error:
            rows = []

        table.setRowCount(len(rows))
        for i, (mid, modo, cal, espectro_str, notas) in enumerate(rows):
            try:
                espectro = ast.literal_eval(espectro_str)
            except (ValueError, SyntaxError):
                espectro = []

            valores_fila = [
                str(mid),
                modo or "—",
                "Sí" if cal else "No",
            ] + [str(round(v, 4)) if j < len(espectro) else "—"
                 for j, v in enumerate(espectro)] + [notas or ""]

            for j, val in enumerate(valores_fila):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                table.setItem(i, j, item)

        return table

    def _refresh_medidas(self):
        medidas_page = self.stack.widget(2)
        layout = medidas_page.layout()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(item.widget(), QTableWidget):
                old = item.widget()
                layout.removeWidget(old)
                old.deleteLater()
                break
        layout.addWidget(self._get_medidas_table())

    def _save_medidas_csv(self):
        usar_raw = self.combo_medidas_tipo.currentIndex() == 1
        col_espectro = "espectro_raw" if usar_raw else "espectro_normalizado"
        tipo_label   = "raw" if usar_raw else "normalizado"

        try:
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute(
                f"SELECT id, modo_medicion, calibracion_aplicada, "
                f"{col_espectro}, notas FROM muestras ORDER BY id DESC"
            )
            rows = cur.fetchall()
            conn.close()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error de base de datos", str(e))
            return

        if not rows:
            QMessageBox.information(self, "Sin datos", "No hay medidas que exportar.")
            return

        default = f"medidas_{tipo_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Exportar medidas", default, "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "modo_medicion", "calibracion_aplicada"] + CSV_HEADER + ["notas"])
                for mid, modo, cal, espectro_str, notas in rows:
                    try:
                        espectro = ast.literal_eval(espectro_str)
                    except (ValueError, SyntaxError):
                        espectro = [""] * len(CSV_HEADER)
                    writer.writerow([mid, modo or "", int(cal or 0)] + espectro + [notas or ""])
            self._set_status(f"Medidas exportadas ({len(rows)} filas, {tipo_label})")
        except OSError as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    # ------------------------------------------------------------------ #
    #  Ciclo de vida                                                       #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        self._stop_acquisition()
        if self.reader:
            self.reader.disconnect()
        self._capturas_manuales.clear()
        self._calibraciones = {
            MODO_REFLECTANCIA:  {CAL_BLANCO: None, CAL_OSCURO: None},
            MODO_TRANSMITANCIA: {CAL_BLANCO: None, CAL_OSCURO: None},
        }
        event.accept()
