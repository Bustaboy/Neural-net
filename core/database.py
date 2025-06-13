import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use SQLite database file (neuralnet.db in the app directory)
DATABASE_URL = "sqlite:///neuralnet.db"

# Create SQLAlchemy engine with SQLite settings
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create session factory for database interactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Provide a database session for FastAPI routes."""
    logger.info("Opening database session")
    db = SessionLocal()
    try:
      yield db
    finally:
        logger.info("Closing database session")
        db.close()
