import sqlite3
import os

DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'data.db')
)

def seed_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS muestras (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            espectro_raw         TEXT,
            espectro_normalizado TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predicciones (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            clase_miel           VARCHAR(255),
            vector_probabilidades TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analisis (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_analisis  VARCHAR(255),
            timestamp        DATETIME,
            id_muestra       INTEGER,
            id_prediccion    INTEGER,
            FOREIGN KEY (id_muestra)    REFERENCES muestras(id),
            FOREIGN KEY (id_prediccion) REFERENCES predicciones(id)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"Base de datos inicializada en: {DB_PATH}")


if __name__ == "__main__":
    seed_database()