import sqlite3

def init_db():
    conn = sqlite3.connect('printflow3d.db')
    cursor = conn.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS orders')
    cursor.execute('DROP TABLE IF EXISTS users')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            filename TXT NOT NULL,
            status TEXT DEFAULT 'Pendiente',
            print_time_est INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor.execute("ALTER TABLE orders ADD COLUMN price REAL DEFAULT 0.0")
    cursor.execute("ALTER TABLE orders ADD COLUMN admin_notes TEXT DEFAULT ''")

    # cursor.execute("ALTER TABLE orders ADD COLUMN image_filename TEXT DEFAULT NULL")
    
    conn.commit()
    conn.close()
    print("BD lista")

if __name__ == "__main__":
    init_db()