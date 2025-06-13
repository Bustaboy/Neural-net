from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from cryptography.fernet import Fernet  # For encryption (install later)

Base = declarative_base()
metadata = MetaData()

# Encryption key (generate and store securely)
key = Fernet.generate_key()
cipher_suite = Fernet(key)

class DatabaseManager:
    def __init__(self):
        # Placeholder: Use environment variable for DB path
        db_path = os.environ.get("DB_PATH", "neuralnet.db")
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def get_db(self):
        """Provide a database session."""
        session = self.Session()
        try:
            yield session
        finally:
            session.close()

    def encrypt_data(self, data):
        """Encrypt sensitive data (placeholder)."""
        return cipher_suite.encrypt(data.encode()) if data else data

    def decrypt_data(self, encrypted_data):
        """Decrypt sensitive data (placeholder)."""
        return cipher_suite.decrypt(encrypted_data).decode() if encrypted_data else None
