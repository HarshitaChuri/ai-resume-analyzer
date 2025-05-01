import sqlite3
import bcrypt
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def signup(username, password, role):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        # Store username in lowercase to avoid case sensitivity
        username_lower = username.lower()
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username_lower, hashed, role))
        conn.commit()
        logger.debug(f"User {username_lower} signed up successfully")
    except sqlite3.IntegrityError:
        logger.error(f"Signup failed: Username {username_lower} already exists")
        raise Exception(f"Username {username_lower} already exists")
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise Exception(f"Signup failed: {e}")
    finally:
        conn.close()

def login(username, password):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        # Query with lowercase username
        username_lower = username.lower()
        c.execute('SELECT password, role FROM users WHERE username = ?', (username_lower,))
        result = c.fetchone()
        if result:
            stored_password, role = result
            # Ensure password is bytes
            if isinstance(stored_password, str):
                stored_password = stored_password.encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                logger.debug(f"User {username_lower} authenticated successfully")
                return True, username_lower, role
            else:
                logger.error("Login failed: incorrect password")
                return False, None, None
        else:
            logger.error(f"Login failed: username {username_lower} not found")
            return False, None, None
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise Exception(f"Login failed: {e}")
    finally:
        conn.close()