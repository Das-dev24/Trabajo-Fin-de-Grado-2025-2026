import sqlite3
import pytest

_SCHEMA_STMTS = [
    """CREATE TABLE IF NOT EXISTS muestras (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        espectro_raw         TEXT    NOT NULL,
        espectro_normalizado TEXT    NOT NULL,
        modo_medicion        VARCHAR(32) NOT NULL DEFAULT 'reflectancia',
        calibracion_aplicada INTEGER    NOT NULL DEFAULT 0,
        notas                TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS predicciones (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        clase_miel            VARCHAR(255),
        vector_probabilidades TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS analisis (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre_analisis VARCHAR(255) NOT NULL,
        timestamp       DATETIME    NOT NULL,
        id_muestra      INTEGER     NOT NULL,
        id_prediccion   INTEGER,
        FOREIGN KEY (id_muestra)    REFERENCES muestras(id)     ON DELETE CASCADE,
        FOREIGN KEY (id_prediccion) REFERENCES predicciones(id) ON DELETE SET NULL
    )""",
    """CREATE TABLE IF NOT EXISTS calibraciones (
        tipo          VARCHAR(16) NOT NULL,
        modo_medicion VARCHAR(32) NOT NULL DEFAULT 'reflectancia',
        valores       TEXT        NOT NULL,
        timestamp     DATETIME    NOT NULL,
        PRIMARY KEY (tipo, modo_medicion),
        CHECK (tipo          IN ('blanco', 'oscuro')),
        CHECK (modo_medicion IN ('reflectancia', 'transmitancia'))
    )""",
]


def _apply_schema(conn):
    for stmt in _SCHEMA_STMTS:
        conn.execute(stmt)
    conn.commit()


@pytest.fixture
def mem_db():
    conn = sqlite3.connect(":memory:")
    _apply_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def test_db_path(tmp_path):
    """Bare path pointing to an empty (not yet seeded) DB file location."""
    return str(tmp_path / "test.db")


@pytest.fixture
def test_db(tmp_path):
    """Path to a fully-seeded test DB (tables created, no data)."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    _apply_schema(conn)
    conn.close()
    return db_path


@pytest.fixture
def mock_serial(mocker):
    """Patches serial.Serial globally; returns the mock instance."""
    mock_cls = mocker.patch("serial.Serial")
    instance = mock_cls.return_value
    instance.is_open = True
    instance.readline.return_value = b""
    instance.write.return_value = None
    instance.reset_input_buffer.return_value = None
    return instance


@pytest.fixture
def mock_reader(mock_serial):
    """SerialReader with serial_connection already set to the mock."""
    from hives.core.sensor import SerialReader
    reader = SerialReader("COM_TEST", 115200)
    reader.serial_connection = mock_serial
    return reader


@pytest.fixture
def mock_model():
    """Keras-like MagicMock returning uniform 12-class probabilities."""
    from unittest.mock import MagicMock
    import numpy as np
    from hives.reports.pdf_report import HONEY_CLASSES

    model = MagicMock()
    probs = [1.0 / 12] * 12
    model.predict.return_value = np.array([probs])
    model.output_names = list(HONEY_CLASSES)
    return model


@pytest.fixture
def window(qtbot, test_db, mocker):
    """SpectroControlUI with DB, load_model, and serial ports patched."""
    mocker.patch("hives.gui.main_window.DB_PATH", test_db)
    mocker.patch("hives.gui.main_window.load_model", return_value=None)
    mocker.patch("serial.tools.list_ports.comports", return_value=[])

    from hives.gui.main_window import SpectroControlUI
    win = SpectroControlUI()
    qtbot.addWidget(win)
    yield win
