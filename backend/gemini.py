"""Gemini 연동 - 받아쓰기와 세 갈래 구분 (정의서 7-3 · 9).

외부 호출은 이 파일에만 있다. 테스트는 transcribe · classify 를 바꿔 끼운다.
공급자 5xx 는 1회 재시도 후 502, 키 없음도 502 VALIDATION_ERROR.
"""
import io
import json
import logging

from . import config
from .errors import ApiError

log = logging.getLogger("meetingnote.gemini")

INLINE_LIMIT = 20 * 1024 * 1024  # 20MB 초과는 Files API

CLASSIFY_PROMPT = """다음은 회의 녹취를 받아쓴 본문이다. 본문에 있는 내용만으로 세 갈래를 뽑아 JSON 으로 답하라.
없는 사실을 보태지 않는다.

- summary: 회의 전체를 3~5개의 짧은 문장 배열로
- decisions: 합의가 끝난 것만 (「하기로 했다 · 확정 · 승인」). 논의만 한 것은 넣지 않는다. 없으면 빈 배열
- todos: 담당자와 기한이 드러난 것만. 각 항목은 what(할 일) · assignee(본문에 나온 담당자 이름, 없으면 빈 문자열) · due(본문에 나온 기한 글자 그대로, 없으면 빈 문자열). 없으면 빈 배열

팀 멤버 이름: {members}

본문:
{body}
"""

CLASSIFY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "ARRAY", "items": {"type": "STRING"}},
        "decisions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "todos": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "what": {"type": "STRING"},
                    "assignee": {"type": "STRING"},
                    "due": {"type": "STRING"},
                },
                "required": ["what", "assignee", "due"],
            },
        },
    },
    "required": ["summary", "decisions", "todos"],
}


def _client():
    key = config.gemini_api_key()
    if not key:
        raise ApiError(502, "VALIDATION_ERROR", "GEMINI_API_KEY 가 설정되지 않음")
    from google import genai
    return genai.Client(api_key=key)


def _with_retry(call, what: str):
    from google.genai import errors as gerr
    for attempt in (1, 2):
        try:
            return call()
        except gerr.ServerError as e:  # 5xx
            log.warning("%s 5xx (시도 %d): %s", what, attempt, e)
            if attempt == 2:
                raise ApiError(502, "VALIDATION_ERROR", f"{what} 실패 - 공급자 오류")
        except gerr.APIError as e:
            log.warning("%s 실패: %s", what, e)
            raise ApiError(502, "VALIDATION_ERROR", f"{what} 실패")


def transcribe(data: bytes, mime: str) -> str:
    """녹취 → 받아쓴 본문 한 덩어리."""
    from google.genai import types
    client = _client()
    model = config.gemini_model()
    prompt = "이 회의 녹음을 한국어로 그대로 받아써라. 요약하지 말고 들린 말을 모두 적는다. 화자는 구분하지 않는다."

    def call():
        if len(data) > INLINE_LIMIT:
            f = client.files.upload(file=io.BytesIO(data), config={"mime_type": mime})
            part = f
        else:
            part = types.Part.from_bytes(data=data, mime_type=mime)
        return client.models.generate_content(model=model, contents=[prompt, part])

    resp = _with_retry(call, "받아쓰기")
    text = (getattr(resp, "text", None) or "").strip()
    if not text:
        raise ApiError(502, "VALIDATION_ERROR", "받아쓰기 결과가 비어 있음")
    return text


def classify(body: str, member_names: list[str]) -> dict:
    """본문 → {summary: str, decisions: [str], todos: [{what, assignee, due}]}.

    응답을 읽지 못하면 502 (저장하지 않음).
    """
    from google.genai import types
    client = _client()
    model = config.gemini_model()
    prompt = CLASSIFY_PROMPT.format(members=", ".join(member_names) or "(없음)", body=body)

    def call():
        return client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", response_schema=CLASSIFY_SCHEMA
            ),
        )

    resp = _with_retry(call, "세 항목 구분")
    return parse_classification(getattr(resp, "text", "") or "")


def parse_classification(text: str) -> dict:
    try:
        data = json.loads(text)
        raw = data["summary"]
        lines = raw if isinstance(raw, list) else str(raw).splitlines()
        summary = "\n".join(str(x).strip() for x in lines if str(x).strip())
        decisions = [str(d).strip() for d in data["decisions"] if str(d).strip()]
        todos = []
        for t in data["todos"]:
            what = str(t["what"]).strip()
            if what:
                todos.append({"what": what, "assignee": str(t.get("assignee") or "").strip(),
                              "due": str(t.get("due") or "").strip()})
    except (ValueError, KeyError, TypeError):
        raise ApiError(502, "VALIDATION_ERROR", "세 항목 구분 응답을 읽지 못함 - 본문은 그대로 다시 저장 가능")
    return {"summary": summary, "decisions": decisions, "todos": todos}
