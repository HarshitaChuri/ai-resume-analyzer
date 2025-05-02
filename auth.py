import bcrypt
import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def hash_password(password):
    """Hash a password using bcrypt"""
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        logger.debug("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise

def check_password(password, hashed):
    """Check if a password matches the hashed password"""
    try:
        result = bcrypt.checkpw(password.encode('utf-8'), hashed)
        logger.debug("Password check completed")
        return result
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        return False

def login(username, password):
    """Authenticate a user by checking username and password"""
    try:
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT username, password, role FROM users WHERE username = ?", (username.lower(),))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password(password, user['password']):
            logger.debug(f"User {username} authenticated successfully")
            return True, user['username'], user['role']
        else:
            logger.warning(f"Authentication failed for user {username}")
            return False, None, None
    except Exception as e:
        logger.error(f"Error authenticating user: {e}")
        return False, None, None

def signup(username, password, role):
    """Register a new user with a hashed password"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE username = ?", (username.lower(),))
        if cursor.fetchone():
            conn.close()
            logger.warning(f"Registration failed: Username {username} already exists")
            raise Exception("Username already exists")
        
        hashed_password = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username.lower(), hashed_password, role)
        )
        conn.commit()
        conn.close()
        logger.debug(f"User {username} registered successfully")
        return True
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise