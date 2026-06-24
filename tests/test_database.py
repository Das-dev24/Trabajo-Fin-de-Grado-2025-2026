import sqlite3
import pytest


def _conn(seeded_db):
    return sqlite3.connect(seeded_db)


 # -------------------------------------------------------------------- #
#                   Existencia de tablas                                #
# -------------------------------------------------------------------- #

def test_seed_creates_muestras_table(seeded_db):
    conn = _conn(seeded_db)
    info = conn.execute("PRAGMA table_info(muestras)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_creates_predicciones_table(seeded_db):
    conn = _conn(seeded_db)
    info = conn.execute("PRAGMA table_info(predicciones)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_creates_analisis_table(seeded_db):
    conn = _conn(seeded_db)
    info = conn.execute("PRAGMA table_info(analisis)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_creates_calibraciones_table(seeded_db):
    conn = _conn(seeded_db)
    info = conn.execute("PRAGMA table_info(calibraciones)").fetchall()
    conn.close()
    assert len(info) > 0


def test_seed_idempotent(seeded_db):
    from hives.core.database import seed_database
    seed_database()  # second call must not raise
    conn = _conn(seeded_db)
    info = conn.execute("PRAGMA table_info(muestras)").fetchall()
    conn.close()
    assert len(info) > 0


# -------------------------------------------------------------------- #
#                   Nombres de las columnas                            #
# -------------------------------------------------------------------- #

def test_muestras_columns(seeded_db):
    conn = _conn(seeded_db)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(muestras)").fetchall()]
    conn.close()
    expected = {"id", "espectro_raw", "espectro_normalizado",
                "modo_medicion", "calibracion_aplicada", "notas"}
    assert set(cols) == expected


def test_calibraciones_columns(seeded_db):
    conn = _conn(seeded_db)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(calibraciones)").fetchall()]
    conn.close()
    assert set(cols) == {"tipo", "modo_medicion", "valores", "timestamp"}


# -------------------------------------------------------------------- #
#                         Restricciones                                #
# -------------------------------------------------------------------- #

def test_analisis_foreign_key(seeded_db):
    conn = _conn(seeded_db)
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO analisis (nombre_analisis, timestamp, id_muestra) "
            "VALUES ('test', '2025-01-01 00:00:00', 9999)"
        )
        conn.commit()
    conn.close()


def test_calibraciones_check_tipo_invalido(seeded_db):
    conn = _conn(seeded_db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO calibraciones (tipo, modo_medicion, valores, timestamp) "
            "VALUES ('invalido', 'reflectancia', '[1.0]', '2025-01-01 00:00:00')"
        )
        conn.commit()
    conn.close()


def test_calibraciones_check_modo_invalido(seeded_db):
    conn = _conn(seeded_db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO calibraciones (tipo, modo_medicion, valores, timestamp) "
            "VALUES ('blanco', 'fotometria', '[1.0]', '2025-01-01 00:00:00')"
        )
        conn.commit()
    conn.close()


def test_calibraciones_primary_key_unique(seeded_db):
    conn = _conn(seeded_db)
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

# -------------------------------------------------------------------- #
#             Probamos el gestor de contexto                           #
# -------------------------------------------------------------------- #

def test_db_connection_rollback_on_exception(seeded_db, mocker):
    import hives.core.database as db_mod
    original_db = db_mod.DB_PATH
    db_mod.DB_PATH = seeded_db
    try:
        with pytest.raises(RuntimeError):
            with db_mod.db_connection():
                raise RuntimeError("something went wrong")
        conn = sqlite3.connect(seeded_db)
        cur = conn.execute("SELECT COUNT(*) FROM muestras")
        assert cur.fetchone()[0] == 0
        conn.close()
    finally:
        db_mod.DB_PATH = original_db


def test_db_connection_commit_on_success(seeded_db, mocker):
    import hives.core.database as db_mod
    original_db = db_mod.DB_PATH
    db_mod.DB_PATH = seeded_db
    try:
        with db_mod.db_connection() as conn:
            conn.execute(
                "INSERT INTO muestras (espectro_raw, espectro_normalizado) "
                "VALUES ('[1.0]', '[1.0]')"
            )
        conn2 = sqlite3.connect(seeded_db)
        cur = conn2.execute("SELECT COUNT(*) FROM muestras")
        assert cur.fetchone()[0] == 1
        conn2.close()
    finally:
        db_mod.DB_PATH = original_db

# -------------------------------------------------------------------- #
#              Inicialización de la base de datos                      #
# -------------------------------------------------------------------- #

def test_database_if_main_guard():
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, "-c", "from hives.core.database import seed_database"],
        capture_output=True, text=True, timeout=10,
        cwd=r"C:\Users\Victus-LP\SynologyDrive\Uni\2025-2026\zTFG\Repo\Trabajo-Fin-de-Grado-2025-2026\src",
    )
    assert "Base de datos" not in result.stdout
