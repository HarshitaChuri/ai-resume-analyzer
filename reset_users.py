import sqlite3
import bcrypt
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def reset_users():
    try:
        # Connect to database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Drop and recreate users table
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT
            )
        ''')
        
        # Define users to insert (lowercase usernames, correct roles)
        users = [
            ('ganu', 'password123', 'job_seeker'),
            ('jobseeker1', 'password123', 'job_seeker'),
            ('bappa', '1', 'job_seeker'),
            ('recruiter1', 'password123', 'recruiter'),
            ('bhavisha', 'password123', 'job_seeker')
        ]
        
        # Insert users with hashed passwords
        for username, password, role in users:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                     (username, hashed, role))
            logger.debug(f"Added user: {username} as {role}")
        
        conn.commit()
        logger.debug("Users table reset successfully")
        
        # Verify contents
        c.execute('SELECT username, role FROM users')
        logger.debug(f"Users in database: {c.fetchall()}")
        
    except Exception as e:
        logger.error(f"Failed to reset users: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_users()