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


def create_all(retries: int = 3):
    """테이블 생성 + 이관. 서버리스에서 인스턴스 여럿이 동시에 시작하면 같은 테이블을 동시에
    만들다 한쪽이 「이미 있음」 오류를 낸다 - 잠깐 기다렸다 다시 하면 checkfirst 로 지나간다."""
    import time

    from sqlalchemy.exc import IntegrityError, ProgrammingError

    from . import models  # noqa: F401 - 테이블 등록
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(engine)
            migrate()
            return
        except (ProgrammingError, IntegrityError):
            if attempt == retries:
                raise
            time.sleep(0.5 * attempt)


def migrate(bind=None) -> int:
    """기존 DB 이관 - todos.due_date 열이 없으면 더하고, 빈 due_date 를 기한 글자로 채운다.

    여러 번 돌려도 결과가 같다. 채운 행 수를 돌려준다 (modify-todo-due-date).
    """
    from sqlalchemy import inspect, select, text
    from sqlalchemy.orm import Session

    from .duedate import kst_date, parse_due
    from .models import Meeting, Todo

    bind = bind or engine
    cols = {c["name"] for c in inspect(bind).get_columns("todos")}
    if "due_date" not in cols:
        with bind.begin() as conn:
            conn.execute(text("ALTER TABLE todos ADD COLUMN due_date DATE"))
    filled = 0
    with Session(bind) as db:
        rows = db.execute(
            select(Todo, Meeting.met_at).outerjoin(Meeting, Meeting.id == Todo.meeting_id)
            .where(Todo.due_date.is_(None), Todo.due_text != "")
        ).all()
        for todo, met_at in rows:
            d = parse_due(todo.due_text, kst_date(met_at or todo.created_at))
            if d is not None:
                todo.due_date = d
                filled += 1
        db.commit()
    return filled
