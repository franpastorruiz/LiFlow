from functools import lru_cache
from typing import Generator

from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import ConfigurationError, Settings


@lru_cache
def session_factory() -> sessionmaker[Session]:
    database_url = Settings.from_environment().database_url
    if not database_url:
        raise ConfigurationError("DATABASE_URL is required for persistence.")
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    try:
        session = session_factory()()
    except ConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The database is not configured.",
        ) from error
    try:
        yield session
    finally:
        session.close()
