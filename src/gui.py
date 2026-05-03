import sys
import os
import sqlite3
import csv
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QGridLayout, QComboBox,
    QStackedWidget, QFileDialog, QMessageBox, QSizePolicy, QTableWidget,QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

import serial.tools.list_ports

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sensor import SerialReader

BAUDRATE    = 115200
WAVELENGTHS = [410, 435, 460, 485, 510, 535, 560, 585,
               610, 645, 680, 705, 730, 760, 810, 860, 900, 940]
CSV_HEADER  = ["A_410","B_435","C_460","D_485","E_510","F_535","G_560","H_585",
               "R_610","I_645","S_680","J_705","T_730","U_760","V_810","W_860",
               "K_900","L_940"]
DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'data.db')
)


class SerialWorker(QThread):
    data_received  = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, reader: SerialReader):
        super().__init__()
        self.reader   = reader
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            data = self.reader.read_data()
            if data and len(data) == 18:
                self.data_received.emit(data)
            self.msleep(50)

    def stop(self):
        self._running = False
        self.wait(2000)


if MATPLOTLIB_AVAILABLE:
    class SpectralCanvas(FigureCanvas):
        def __init__(self):
            self.fig = Figure(figsize=(6, 3.5), facecolor="#f8f8f8")
            super().__init__(self.fig)
            self.ax = self.fig.add_subplot(111)
            self._setup_axes()

        def _setup_axes(self):
            ax = self.ax
            ax.set_facecolor("#f8f8f8")
            for sp in ['top', 'right']:
                ax.spines[sp].set_visible(False)
            ax.tick_params(labelsize=7)
            ax.set_xlabel('Longitud de onda (nm)', fontsize=9)
            ax.set_ylabel('Intensidad', fontsize=9)
            ax.set_xticks(WAVELENGTHS)
            ax.set_xticklabels([str(w) for w in WAVELENGTHS], rotation=45, ha='right')
            ax.set_xlim(390, 960)
            ax.set_ylim(0, 1)
            self.fig.tight_layout(pad=1.5)

        def update_data(self, values: list):
            self.ax.clear()
            self._setup_axes()
            self.ax.bar(WAVELENGTHS, values, width=18, color='#3a7ebf', alpha=0.8, zorder=3)
            peak = max(values)
            self.ax.set_ylim(0, peak * 1.15 if peak > 0 else 1)
            self.fig.tight_layout(pad=1.5)
            self.draw()

        def clear_plot(self):
            self.ax.clear()
            self._setup_axes()
            self.draw()

else:
    class SpectralCanvas(QWidget):  # type: ignore[no-redef]
        def __init__(self):
            super().__init__()
            lay = QVBoxLayout(self)
            lbl = QLabel("matplotlib no disponible\npip install matplotlib")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl)

        def update_data(self, values: list): pass
        def clear_plot(self):               pass


class SpectroControlUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HIVES — Clasificación de Miel")
        self.setGeometry(100, 100, 1100, 720)
        self.setMinimumSize(800, 550)

        self.reader: SerialReader = None
        self.worker: SerialWorker = None
        self.captured_data: list  = []
        self._connected  = False
        self._scanning   = False
        self._led_mode   = False

        self.setStyleSheet("QMainWindow, QWidget { background-color: #f0f0f0; color: #222; }")
        self._init_ui()
        self._scan_ports()

    def _init_ui(self):
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

        rl.addWidget(self.stack)
        rl.addWidget(self._build_bottom_bar())
        root.addWidget(right)

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
        nav_labels = ["Captura en vivo", "Historial"]
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

        # Puerto serie
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
        btn_refresh.setStyleSheet("QPushButton { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 4px; }")
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
            ("Modo",              "Continuo" ),
        ]
        grid = QGridLayout()
        grid.setSpacing(4)
        for r, (label, val) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #666; font-size: 11px;")
            grid.addWidget(lbl, r, 0)
            v = QLabel(val)
            v.setStyleSheet("color: #222; font-size: 11px;")
            v.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lbl, r, 0)
            grid.addWidget(v,   r, 1)
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
        lay.setContentsMargins(32, 32, 32, 32)
        lbl = QLabel("Historial de datos")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        lay.addWidget(lbl)
        lbl2 = QLabel("Análisis guardados en la base de datos.\n")
        lbl2.setStyleSheet("color: #888; margin-top: 8px;")
        lay.addWidget(lbl2)
        lay.addWidget(self.getData())
        
        
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

        self.btn_start = QPushButton("▶  Iniciar captura")
        self.btn_start.setFixedWidth(140)
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(self._btn_style("primary", enabled=False))
        self.btn_start.clicked.connect(self._start_acquisition)

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

        lay.addWidget(self.lbl_sys_status)
        lay.addSpacing(8)
        lay.addWidget(self.lbl_last_save)
        lay.addStretch()
        lay.addWidget(self.btn_start)
        lay.addWidget(self.btn_stop)
        lay.addWidget(self.btn_save_csv)
        return bar

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
        return base + "background: #e0e0e0; color: #333; border: 1px solid #ccc;"  # secondary

    @staticmethod
    def _nav_style(active: bool) -> str:
        base = "QPushButton { text-align: left; padding: 10px 12px; border: none; border-radius: 3px; font-size: 13px; "
        if active:
            return base + "background: #3a7ebf; color: white; }"
        return base + "background: transparent; color: #aaa; } QPushButton:hover { background: #3c3c3c; color: #eee; }"

    @staticmethod
    def _section_label(text: str, dark: bool = True) -> QLabel:
        lbl = QLabel(text.upper())
        color = "#666" if dark else "#999"
        lbl.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; padding: 2px 0;")
        return lbl

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
        else:
            QMessageBox.warning(self, "Error LED", "No se pudo cambiar el modo de los LEDs.")

    
    def _start_acquisition(self):
        if not self._connected or self._scanning:
            return
        if not self.reader.start_scanning():
            QMessageBox.critical(self, "Error de escaneo", "No se pudo iniciar el escaneo.")
            return

        self._scanning = True
        self.worker = SerialWorker(self.reader)
        self.worker.data_received.connect(self._on_data)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()

        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(self._btn_style("primary", enabled=False))
        self.btn_stop.setEnabled(True)
        self.btn_stop.setStyleSheet(self._btn_style("danger"))
        self.btn_save_csv.setEnabled(False)
        self.btn_save_csv.setStyleSheet(self._btn_style("secondary", enabled=False))
        self.diag_scan.setText("Escaneando")
        self._set_status("Adquiriendo...")

    def _stop_acquisition(self):
        if not self._scanning:
            return
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

        self.diag_scan.setText("En espera")
        self._set_status("Listo")

        if has_data:
            self._save_to_db(silent=True)

    
    def _on_data(self, values: list):
        self.captured_data.append(values)
        n = len(self.captured_data)
        self.lbl_readings.setText(f"Lecturas: {n}")
        self.diag_buf.setText(f"{n} filas")
        self.canvas.update_data(values)

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
        if not self.captured_data:
            return
        default = f"espectro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", default, "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)
                writer.writerows(self.captured_data)
            self.lbl_last_save.setText(f"CSV guardado {datetime.now().strftime('%H:%M:%S')}")
            self._set_status("CSV guardado")
        except OSError as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    def _save_to_db(self, silent: bool = False):
        if not self.captured_data:
            return
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        try:
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS muestras (
                    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                    espectro_raw         TEXT,
                    espectro_normalizado TEXT
                )
            """)
            saved = 0
            for row in self.captured_data:
                peak = max(row) if max(row) > 0 else 1.0
                norm = [round(v / peak, 6) for v in row]
                cur.execute(
                    "INSERT INTO muestras (espectro_raw, espectro_normalizado) VALUES (?, ?)",
                    (str(row), str(norm))
                )
                saved += 1
            conn.commit()
            conn.close()
            ts = datetime.now().strftime('%H:%M:%S')
            self.lbl_last_save.setText(f"Guardado en DB {ts} ({saved} filas)")
            self._set_status("Guardado en DB")
        except sqlite3.Error as e:
            if not silent:
                QMessageBox.critical(self, "Error de base de datos", str(e))
            else:
                self._set_status("Error al guardar en DB")

    def _set_status(self, text: str):
        self.lbl_sys_status.setText(text)

    def closeEvent(self, event):
        self._stop_acquisition()
        if self.reader:
            self.reader.disconnect()
        event.accept()
        
    def getData(self):

        directorio_actual = Path(__file__).parent
        ruta_bd = directorio_actual.parent / "data"/ "data.db"
        
        conn = sqlite3.connect(ruta_bd)
        cursor = conn.execute('''
                              SELECT * 
                              FROM analisis''')
        datos = cursor.fetchall()
        cabeceras = list(map(lambda x: x[0], cursor.description))
        conn.close()
        
        table = QTableWidget()
        table.setColumnCount(len(cabeceras))
        table.setRowCount(len(datos))
        
        table.setHorizontalHeaderLabels(cabeceras)
        
        
        for i, fila in enumerate(datos):
            for j,valor in enumerate(fila):
                item = QTableWidgetItem(str(valor))
                table.setItem(i, j, item)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                
        return table

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectroControlUI()
    window.show()
    sys.exit(app.exec())
