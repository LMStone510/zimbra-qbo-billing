# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Database initialization and migration utilities."""

import logging
from pathlib import Path
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional

from .models import Base, Exclusion, Customer
from ..config import get_config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections, initialization, and migrations."""

    def __init__(self, database_path: Optional[str] = None):
        """Initialize database manager.

        Args:
            database_path: Optional path to database file. If None, uses config.
        """
        config = get_config()
        self.database_path = database_path or config.get('database.path')
        self.engine = create_engine(f'sqlite:///{self.database_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()

    def initialize_database(self) -> None:
        """Initialize database schema and load default data."""
        logger.info(f"Initializing database at {self.database_path}")

        # Create all tables
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created")

        # Load default data
        self._load_default_exclusions()
        logger.info("Default data loaded")

    def database_exists(self) -> bool:
        """Check if database file exists and has tables.

        Returns:
            True if database is initialized, False otherwise
        """
        db_path = Path(self.database_path)
        if not db_path.exists():
            return False

        # Check if tables exist
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        return len(tables) > 0

    def _load_default_exclusions(self) -> None:
        """Load default exclusion patterns from configuration."""
        config = get_config()
        session = self.get_session()

        try:
            # Check if exclusions already exist
            existing_count = session.query(Exclusion).count()
            if existing_count > 0:
                logger.info(f"Exclusions already exist ({existing_count} records), skipping defaults")
                return

            # Load domain exclusions
            domain_patterns = config.get('exclusions.domains', [])
            for pattern in domain_patterns:
                exclusion = Exclusion(
                    exclusion_type='domain',
                    pattern=pattern,
                    reason='Default exclusion from configuration',
                    active=True
                )
                session.add(exclusion)

            # Load CoS exclusions
            cos_patterns = config.get('exclusions.cos_patterns', [])
            for pattern in cos_patterns:
                exclusion = Exclusion(
                    exclusion_type='cos',
                    pattern=pattern,
                    reason='Default exclusion from configuration',
                    active=True
                )
                session.add(exclusion)

            session.commit()
            logger.info(f"Loaded {len(domain_patterns)} domain and {len(cos_patterns)} CoS exclusion patterns")

        except Exception as e:
            session.rollback()
            logger.error(f"Error loading default exclusions: {e}")
            raise
        finally:
            session.close()

    def reset_database(self) -> None:
        """Drop all tables and reinitialize database.

        WARNING: This will delete all data!
        """
        logger.warning("Resetting database - all data will be lost!")
        Base.metadata.drop_all(self.engine)
        self.initialize_database()

    def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the database file.

        Args:
            backup_path: Optional path for backup. If None, creates timestamped backup.

        Returns:
            Path to backup file
        """
        import shutil
        from datetime import datetime

        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            db_path = Path(self.database_path)
            backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"

        shutil.copy2(self.database_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
        return str(backup_path)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(database_path: Optional[str] = None) -> DatabaseManager:
    """Get the global database manager instance.

    Args:
        database_path: Optional path to database. Only used on first call.

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_path)
    return _db_manager


def init_database(database_path: Optional[str] = None) -> DatabaseManager:
    """Initialize the database if it doesn't exist.

    Args:
        database_path: Optional path to database file

    Returns:
        DatabaseManager instance
    """
    db_manager = get_db_manager(database_path)

    if not db_manager.database_exists():
        logger.info("Database does not exist, initializing...")
        db_manager.initialize_database()
    else:
        logger.info("Database already exists")

    return db_manager
