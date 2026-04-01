"""
DuckDB Connection Manager (Singleton Pattern)
Replaces MySQL — uses a local DuckDB file for all job tracking.
"""

import duckdb
import os
import logging
from sqlalchemy.orm import declarative_base
from config.settings import settings

logger = logging.getLogger(__name__)

# Keep Base here so models that import it still work
Base = declarative_base()


class DuckDBConnection:
    """Singleton DuckDB connection manager"""
    _instance = None
    _conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DuckDBConnection, cls).__new__(cls)
        return cls._instance

    def _initialize(self):
        """Initialize DuckDB connection"""
        if self._conn is not None:
            return
        try:
            db_path = settings.DUCKDB_PATH
            if db_path.startswith("md:"):
                # Connect to MotherDuck Cloud
                logger.info("Connecting to MotherDuck Cloud...")
                token_suffix = f"?motherduck_token={settings.MOTHERDUCK_TOKEN}" if settings.MOTHERDUCK_TOKEN else ""
                self._conn = duckdb.connect(f"{db_path}{token_suffix}")
            else:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
                self._conn = duckdb.connect(db_path)
            logger.info(f"DuckDB connection initialized: {db_path}")
        except Exception as e:
            logger.critical(f"Failed to initialize DuckDB connection: {e}")
            raise

    def get_connection(self):
        """Get the DuckDB connection"""
        if self._conn is None:
            self._initialize()
        return self._conn

    def get_session(self):
        """Compatibility alias — returns raw DuckDB connection"""
        return self.get_connection()

    def execute(self, query, params=None):
        """Execute a raw query"""
        conn = self.get_connection()
        if params:
            return conn.execute(query, params)
        return conn.execute(query)

    def test_connection(self):
        """Test database connection"""
        try:
            conn = self.get_connection()
            conn.execute("SELECT 1")
            logger.info("DuckDB connection test successful")
            return True
        except Exception as e:
            logger.error(f"DuckDB connection test failed: {e}")
            return False


# Singleton instance
db = DuckDBConnection()
