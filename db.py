import sqlite3

def initialize_database():
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (username TEXT PRIMARY KEY, hashed_password TEXT, role TEXT)''')
        conn.commit()
        conn.close()
    except Exception as e:
        raise Exception(f"Failed to initialize database: {e}")

def add_user(username, hashed_password, role):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)",
                  (username, hashed_password, role))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        raise ValueError("Username already exists")
    except Exception as e:
        raise Exception(f"Failed to add user: {e}")