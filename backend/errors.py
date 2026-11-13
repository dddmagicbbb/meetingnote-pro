"""오류 응답 - 본문은 언제나 {code, msg}. 코드는 정의서 7-2 의 13종만 쓴다."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

CODES = {
    "EMAIL_INVALID", "PASSWORD_TOO_WEAK", "TOKEN_EXPIRED", "INVITE_NOT_FOUND",
    "MEETING_NOT_FOUND", "EMAIL_DUPLICATED", "TEAM_FULL", "UNSUPPORTED_MEDIA_TYPE",
    "INVALID_CREDENTIALS", "FORBIDDEN", "OWNER_ONLY", "VALIDATION_ERROR", "NOT_FOUND",
}

DEFAULT_MSG = {
    "EMAIL_INVALID": "이메일 형식이 올바르지 않음",
    "PASSWORD_TOO_WEAK": "비밀번호는 8자 이상",
    "TOKEN_EXPIRED": "다시 로그인 필요",
    "INVITE_NOT_FOUND": "없는 초대코드",
    "MEETING_NOT_FOUND": "회의록을 찾을 수 없음",
    "EMAIL_DUPLICATED": "이미 가입된 이메일",
    "TEAM_FULL": "팀 정원이 찼음",
    "UNSUPPORTED_MEDIA_TYPE": "mp3 또는 wav 만 올릴 수 있음",
    "INVALID_CREDENTIALS": "이메일 또는 비밀번호가 올바르지 않음",
    "FORBIDDEN": "권한이 없음",
    "OWNER_ONLY": "owner 만 할 수 있음",
    "VALIDATION_ERROR": "입력값이 올바르지 않음",
    "NOT_FOUND": "찾을 수 없음",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, msg: str | None = None):
        assert code in CODES, code
        self.status = status
        self.code = code
        self.msg = msg or DEFAULT_MSG[code]


def _body(code: str, msg: str) -> dict:
    return {"code": code, "msg": msg}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(_body(exc.code, exc.msg), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        msg = f"{where}: {first.get('msg', '')}" if where else DEFAULT_MSG["VALIDATION_ERROR"]
        return JSONResponse(_body("VALIDATION_ERROR", msg), status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return JSONResponse(_body("NOT_FOUND", DEFAULT_MSG["NOT_FOUND"]), status_code=404)
        return JSONResponse(_body("VALIDATION_ERROR", str(exc.detail)), status_code=exc.status_code)
