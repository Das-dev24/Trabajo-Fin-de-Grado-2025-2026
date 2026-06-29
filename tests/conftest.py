import sqlite3
import pytest

from hives.core.database import SCHEMA_STATEMENTS


def _apply_schema(conn):
    for stmt in SCHEMA_STATEMENTS:
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
    """Directorio para la bd de test"""
    return str(tmp_path / "test.db")


@pytest.fixture
def seeded_db(test_db_path, mocker):
    """Cambia la ruta de la bd par hacer los test"""
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    return test_db_path


@pytest.fixture
def test_db(tmp_path):
    """Crea las tablas de la bd de test"""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    _apply_schema(conn)
    conn.close()
    return db_path


@pytest.fixture
def mock_serial(mocker):
    """Cambia el puerto serie para poder hacer los test sin arduino"""
    mock_cls = mocker.patch("serial.Serial")
    instance = mock_cls.return_value
    instance.is_open = True
    instance.readline.return_value = b""
    instance.write.return_value = None
    instance.reset_input_buffer.return_value = None
    return instance


@pytest.fixture
def mock_reader(mock_serial):
    """Cmabia el puerto serie por un mock para los test"""
    from hives.core.sensor import SerialReader
    reader = SerialReader("COM_TEST", 115200)
    reader.serial_connection = mock_serial
    return reader


@pytest.fixture
def window(qtbot, test_db, mocker):
    """Cambai en la vista principal las rutas para los test"""
    mocker.patch("hives.gui.main_window.DB_PATH", test_db)
    mocker.patch("hives.core.database.DB_PATH", test_db)
    mocker.patch("hives.gui.main_window.load_model", return_value=None)
    mocker.patch("serial.tools.list_ports.comports", return_value=[])

    from hives.gui.main_window import SpectroControlUI
    win = SpectroControlUI()
    qtbot.addWidget(win)
    yield win
