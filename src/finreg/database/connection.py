"""SQLAlchemy database connection and session management infrastructure."""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from finreg.config.settings import get_settings


def get_engine(database_url: str | None = None) -> Engine:
    """Create and return a SQLAlchemy database Engine.

    Args:
        database_url: Optional explicit connection string. Defaults to settings.database_url.
    """
    url = database_url or get_settings().database_url
    return create_engine(
        url,
        pool_pre_ping=True,
        echo=False,
    )


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Create and return a SQLAlchemy sessionmaker factory.

    Args:
        engine: Optional Engine instance. Creates default engine if omitted.
    """
    db_engine = engine or get_engine()
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


def get_db_session(
    factory: sessionmaker[Session] | None = None,
) -> Generator[Session, None, None]:
    """Yield a database session context, ensuring proper cleanup.

    Args:
        factory: Optional sessionmaker factory.
    """
    session_factory = factory or get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
