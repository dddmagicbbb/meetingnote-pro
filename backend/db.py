"""DB 엔진과 세션. 코드는 한 벌 - DATABASE_URL 유무로 Postgres / SQLite 를 고른다."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config

DATABASE_URL = config.database_url()

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all():
    from . import models  # noqa: F401 - 테이블 등록
    Base.metadata.create_all(engine)
