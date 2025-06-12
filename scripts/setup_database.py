# scripts/setup_database.py
from core.database import EnhancedDatabaseManager

def setup_database():
    db_manager = EnhancedDatabaseManager()
    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE,
                    password TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Add other tables from project-structure.txt
            conn.commit()
