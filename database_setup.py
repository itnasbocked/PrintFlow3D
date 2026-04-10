import sqlite3

def init_db():
    conexion = sqlite3.connect('printflow3d.db')
    cursor = conexion.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER,
                   status TEXT DEFAULT 'Pendiente',
                   print_time_est INTEGER,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (user_id) REFERENCES users (id) )
                   ''')
    conexion.commit()
    conexion.close()
    print("BD conectada")

if __name__ == "__main__":
    init_db()