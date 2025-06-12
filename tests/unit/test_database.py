# tests/unit/test_database.py
import unittest
from core.database import EnhancedDatabaseManager
from unittest.mock import Mock

class TestDatabase(unittest.TestCase):
    def test_execute(self):
        db_manager = EnhancedDatabaseManager()
        db_manager.pool.getconn = Mock()
        db_manager.execute("SELECT 1")
        db_manager.pool.getconn.assert_called_once()
