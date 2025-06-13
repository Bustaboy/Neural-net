# core/database.py
import psycopg2
from psycopg2 import pool
import logging
from config import ConfigManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite database file (neuralnet.db in the app directory)
DATABASE_URL = "sqlite:///neuralnet.db"

# Create SQLAlchemy engine with SQLite settings
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory for database interactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Provide a database session for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
class EnhancedDatabaseManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager.get_config("database.main")
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=self.config.get("pool_size", 20),
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["name"],
                user=self.config["user"],
                password=self.config["password"]
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {e}")
            raise

    def get_connection(self):
        try:
            return self.pool.getconn()
        except Exception as e:
            self.logger.error(f"Failed to get connection: {e}")
            raise

    def execute(self, query: str, params: tuple = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    return cur.fetchall()
                conn.commit()
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            conn.rollback()
            raise
        finally:
            self.pool.putconn(conn)

    def fetch_one(self, query: str, params: tuple = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()
        except Exception as e:
            self.logger.error(f"Fetch one failed: {e}")
            raise
        finally:
            self.pool.putconn(conn)

    def fetch_all(self, query: str, params: tuple = None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except Exception as e:
            self.logger.error(f"Fetch all failed: {e}")
            raise
        finally:
            self.pool.putconn(conn)
