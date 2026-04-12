import sqlite3

def seed_database():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS muestras (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   espectro_raw TEXT,
                   espectro_normalizado TEXT)
                   ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predicciones (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   clase_miel varchar(255),
                   vector_probabilidades TEXT)
                   ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analisis (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   enombre_analisis varchar(255),
                   timestamp DATETIME,
                   id_muestra INTEGER,
                   id_prediccion INTEGER,
                   FOREIGN KEY (id_muestra) REFERENCES muestras(id),
                   FOREIGN KEY (id_prediccion) REFERENCES predicciones(id))
                   ''')
    
    conn.commit()
    conn.close()

    if __name__ == "__main__":
        seed_database()
