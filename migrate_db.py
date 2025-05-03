import sqlite3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add file_hash column to resumes table if it doesn't exist."""
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Check if file_hash column exists
        c.execute("PRAGMA table_info(resumes)")
        columns = [info[1] for info in c.fetchall()]
        if 'file_hash' not in columns:
            c.execute('ALTER TABLE resumes ADD COLUMN file_hash TEXT')
            conn.commit()
            logger.info("Added file_hash column to resumes table")
        else:
            logger.info("file_hash column already exists in resumes table")
        
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()