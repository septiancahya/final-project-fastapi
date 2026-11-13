from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.infrastructure.config import get_settings

settings = get_settings()

DB_URL = settings.database_url
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()