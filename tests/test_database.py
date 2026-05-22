import sqlite3
import pytest


def _seed(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core import database as _db_mod
    import importlib
    importlib.reload(_db_mod)
    _db_mod.seed_database()
    return sqlite3.connect(test_db_path)


# ── Table existence ───────────────────────────────────────────────────────────

def test_seed_creates_muestras_table(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    info = conn.execute("PRAGMA table_info(muestras)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_creates_predicciones_table(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    info = conn.execute("PRAGMA table_info(predicciones)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_creates_analisis_table(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    info = conn.execute("PRAGMA table_info(analisis)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_creates_calibraciones_table(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    info = conn.execute("PRAGMA table_info(calibraciones)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_idempotent(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    seed_database()  # second call must not raise
    conn = sqlite3.connect(test_db_path)
    info = conn.execute("PRAGMA table_info(muestras)").fetchall()
    conn.close()
    assert len(info) > 0


# ── Column names ──────────────────────────────────────────────────────────────

def test_muestras_columns(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(muestras)").fetchall()]
    conn.close()
    expected = {"id", "espectro_raw", "espectro_normalizado",
                "modo_medicion", "calibracion_aplicada", "notas"}
    assert set(cols) == expected


def test_calibraciones_columns(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(calibraciones)").fetchall()]
    conn.close()
    assert set(cols) == {"tipo", "modo_medicion", "valores", "timestamp"}


# ── Constraints ───────────────────────────────────────────────────────────────

def test_analisis_foreign_key(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO analisis (nombre_analisis, timestamp, id_muestra) "
            "VALUES ('test', '2025-01-01 00:00:00', 9999)"
        )
        conn.commit()
    conn.close()


def test_calibraciones_check_tipo_invalido(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO calibraciones (tipo, modo_medicion, valores, timestamp) "
            "VALUES ('invalido', 'reflectancia', '[1.0]', '2025-01-01 00:00:00')"
        )
        conn.commit()
    conn.close()


def test_calibraciones_check_modo_invalido(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO calibraciones (tipo, modo_medicion, valores, timestamp) "
            "VALUES ('blanco', 'fotometria', '[1.0]', '2025-01-01 00:00:00')"
        )
        conn.commit()
    conn.close()


def test_calibraciones_primary_key_unique(mocker, test_db_path):
    mocker.patch("hives.core.database.DB_PATH", test_db_path)
    from hives.core.database import seed_database
    seed_database()
    conn = sqlite3.connect(test_db_path)
    conn.execute(
        "INSERT INTO calibraciones (tipo, modo_medicion, valores, timestamp) "
        "VALUES ('blanco', 'reflectancia', '[1.0]', '2025-01-01 00:00:00')"
    )
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO calibraciones (tipo, modo_medicion, valores, timestamp) "
            "VALUES ('blanco', 'reflectancia', '[2.0]', '2025-01-02 00:00:00')"
        )
        conn.commit()
    conn.close()
