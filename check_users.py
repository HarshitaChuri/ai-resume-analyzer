# check_users.py
import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT username, role FROM users")
print(c.fetchall())
conn.close()