"""환경 설정 - 루트 .env 를 읽는다 (정의서 7-5).

.env 에는 GEMINI_API_KEY · GEMINI_MODEL 두 줄만 둔다.
JWT_SECRET · DATABASE_URL 은 환경변수가 없으면 코드 기본값을 쓴다.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

FRONTEND_DIR = ROOT / "frontend"

JWT_SECRET = os.getenv("JWT_SECRET", "meetingnote-local-dev-secret-change-on-deploy")
JWT_ALGORITHM = "HS256"
JWT_HOURS = 24

DEFAULT_SQLITE_URL = f"sqlite:///{(ROOT / 'meetingnote.db').as_posix()}"
GEMINI_DEFAULT_MODEL = "gemini-3.1-flash-lite"


def database_url() -> str:
    """DATABASE_URL 이 있으면 그것(Neon Postgres), 없으면 로컬 SQLite."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return DEFAULT_SQLITE_URL
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "").strip() or GEMINI_DEFAULT_MODEL
