import sqlite3
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute("SELECT id, username, file_name, job_role, ats_score FROM resumes")
print(c.fetchall())
conn.close()