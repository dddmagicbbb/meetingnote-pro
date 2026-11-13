# Design

## Context

- 저장소에는 코드가 없다. 있는 것은 `docs/` 설계문서 3종, `publish/` 확정 퍼블리싱(화면 6종 + `theme.js` + 확인용 `index.html` · `components.html`), 샘플 녹취 `회의_녹음.wav` 뿐이다
- 자료 우선순위는 정의서 > 스토리보드 > 퍼블리싱. 단 색 · 클래스 · 레이아웃은 퍼블리싱이 정답이다
- 퍼블리싱 화면은 `stateBar` 로 상태 63종을 바꿔 보는 정적 HTML 이고, 클래스 문자열을 직접 풀어 쓴다. `UI.*` 이름은 detail · todos 에서 2번씩만 쓴다
- 동기는 proposal.md - Why, 요구사항은 `specs/` 6개를 본다

## Goals / Non-Goals

**Goals:**
- 로컬 한 프로세스(`uvicorn`)로 API · 화면 · Swagger UI 를 함께 띄운다
- 화면에 그려지는 결과가 퍼블리싱과 같다 (색 · 클래스 · 간격)
- Gemini 없이도 테스트가 돈다

**Non-Goals:**
- Vercel · Neon 배포 설정 (`vercel.json` · `.vercelignore` · `pyproject.toml [tool.vercel]`) - 다음 change
- 프론트엔드 빌드 도구 · 번들러 · npm
- 마이그레이션 도구(Alembic). 이번에는 시작 때 `create_all` 로 테이블을 만든다

## Decisions

### 1. 폴더 구조

```
meetingnote-pro/
  .env  .env.example  .gitignore  requirements.txt  requirements-dev.txt (+ playwright)
  backend/
    main.py          FastAPI 앱 · /api 라우터 · StaticFiles(frontend) · /docs
    config.py        루트 .env 읽기 (GEMINI_API_KEY · GEMINI_MODEL), JWT_SECRET · DATABASE_URL 기본값
    db.py            엔진 · 세션. DATABASE_URL 있으면 Postgres, 없으면 sqlite:///meetingnote.db
    models.py        7테이블
    security.py      bcrypt 해시 · JWT 발급과 검증
    errors.py        ApiError(code, status, msg) + 예외 처리기
    deps.py          현재 사용자 · 소속 팀 · owner 확인
    gemini.py        받아쓰기 · 세 갈래 구분 (여기만 외부 호출)
    routers/         auth · teams · meetings · todos · comments · activities (요청 모양은 각 라우터 안 pydantic 모델)
    tests/           pytest (서버)
    tests/e2e/       브라우저 확인 스크립트 (실제 서버 + Chrome, run_all.py)
  frontend/
    login.html meetings.html detail.html todos.html team.html profile.html
    theme.js         publish/theme.js 그대로 복사
    api.js           fetch 래퍼 · 토큰 · 401 처리 · 소속 팀 확인
```

- 요청 모양은 `schemas.py` 한 곳 대신 쓰는 라우터 안에 둔다 - 라우터마다 2~4개뿐이라 옆에 있는 편이 읽기 쉽다
- 대안: `backend/app/...` 패키지 깊이를 더 두는 구조 → 화면 6 · 라우터 6 규모에서 얻는 게 없어 평평하게 둔다
- `.env` 는 루트에 둔다(정의서 7-5). `config.py` 는 `Path(__file__).parent.parent / ".env"` 를 읽어 실행 위치와 상관없이 찾는다

### 2. 화면 클래스 - publish 마크업 복사 + 반복 요소는 이름 사용 (A안)

- 각 화면의 고정 뼈대(상단 바 · 탭 · 패널 · 폼 · 팝업 틀)는 `publish/*.html` 마크업을 클래스까지 그대로 옮긴다
- JS 로 반복해 그리는 것(회의록 카드 · 할 일 카드 · 댓글 · 활동 항목 · 배지 · 알림 · 팝업 · 메뉴)은 `UI` · `STRIPE` · `LABEL` · `notice` · `toast` 를 이름으로 가져다 쓴다. 이름이 없는 조합은 publish 에 쓰인 문자열을 그대로 옮긴다
- `theme.js` 는 고치지 않는다. `stateBar` 호출과 더미 데이터 배열만 지우고 API 결과로 바꾼다
- 금지: 새 색 · 새 모서리 값 · 인라인 style(진행 막대 width 만 예외) · `!important`
- 대안 B(전부 이름으로 바꾸고 theme.js 에 새 조합 등록)는 확정본 theme.js 를 고쳐야 해서, 대안 C(통째 복사)는 정의서의 이름 규칙과 어긋나서 버림

### 3. 인증 - JWT HS256 · bcrypt

- `python-jose` 대신 `PyJWT`, 해시는 `bcrypt` 직접 사용 (`passlib` 은 최신 bcrypt 와 경고 충돌)
- 토큰 `exp` = 발급 + 24h, 갱신 없음. 실패는 모두 401 `TOKEN_EXPIRED`
- `JWT_SECRET` 은 환경변수 없으면 코드 기본값(로컬 전용 문자열)

### 4. 오류 응답 하나의 모양

- 모든 오류 본문은 `{code, msg}`. 코드는 정의서 13종만 쓴다
- FastAPI 기본 422 는 처리기로 400 `VALIDATION_ERROR` 로 바꾼다. 404 경로 없음은 `NOT_FOUND`
- 권한: 다른 팀 자원 접근은 403 `FORBIDDEN`, 단 없는 회의록 · 다른 팀 회의록 단건은 404 `MEETING_NOT_FOUND`(스토리보드 D-13)

### 5. Swagger UI

- FastAPI 기본 `/docs` 를 켜 두고, `HTTPBearer` 보안 스키마를 걸어 「Authorize」 에 토큰을 넣으면 보호된 API 를 바로 부를 수 있게 한다
- 라우터마다 `tags` (Auth · Team · Meeting · Todo · Comment · Activity) 로 27개를 묶는다
- `/docs` 는 정적 파일 마운트보다 먼저 등록해 `frontend/` 에 가리지 않게 한다

### 6. Gemini 연동

- `google-genai` SDK, 모델은 `GEMINI_MODEL` (기본 `gemini-3.1-flash-lite`)
- 받아쓰기: 20MB 이하는 인라인 바이트, 초과는 Files API 업로드 뒤 참조
- 세 갈래 구분: JSON 응답(summary · decisions[] · todos[{what, assignee, due}])을 요구하고, 파싱 실패면 저장하지 않고 502
- 공급자 5xx 는 1회 재시도 후 502 `VALIDATION_ERROR`. 키 없음도 502
- 업로드 형식 판정은 파일 앞 바이트로 한다: wav = `RIFF....WAVE`, mp3 = `ID3` 또는 프레임 동기 `0xFFE`. 그 밖은 415
- 대안: `filetype` 라이브러리 → 두 형식뿐이라 직접 판정

### 7. 담당자 대조

- 멤버 이름과 할 일의 담당자 글자에서 공백과 끝의 「님」 을 지우고 같으면 그 멤버. 없으면 null(미정)

### 8. 칸반 끌기 - 포인터 이벤트

- `pointerdown` → 반투명 사본 · `pointermove` 로 칸 판정 · `pointerup` 에서 `PUT` 한 번. `draggable` 쓰지 않음
- 좁은 화면(칸이 세로로 쌓이는 폭)에서는 끌기를 끄고 카드 누름 → 대기 · 진행 · 완료 버튼

### 9. 테스트

- pytest + FastAPI `TestClient`, DB 는 테스트마다 임시 SQLite
- `gemini.py` 의 두 함수를 `monkeypatch` 로 바꿔 받아쓰기 · 구분 · 5xx · 파싱 실패를 흉내 낸다. 실제 Gemini 는 부르지 않는다
- 시나리오(specs 의 `#### Scenario`) 중 서버 쪽 것을 테스트로 옮긴다
- 화면 쪽 시나리오는 `backend/tests/e2e/` 의 playwright 스크립트로 확인한다. 실제 서버와 Gemini 를 쓰므로 pytest 기본 실행에는 넣지 않는다 (`python backend/tests/e2e/run_all.py`). 마지막 눈 확인은 맨 아래 사람 수락 항목

## Risks / Trade-offs

- [Gemini 응답이 JSON 형식을 어김] → 응답 스키마 지정 + 파싱 실패면 502 로 저장하지 않음. 본문은 화면에 남아 다시 저장 가능
- [`gemini-3.1-flash-lite` 이름이 바뀌거나 쓸 수 없음] → 모델명은 `GEMINI_MODEL` 로만 바꾸게 둠
- [publish 마크업을 옮기다 클래스가 어긋남] → 수락 항목에서 publish 와 나란히 띄워 비교
- [시작 때 `create_all` 만 씀] → 스키마를 바꾸면 로컬 `meetingnote.db` 를 지워야 함. 다음 change 에서 배포와 함께 정리
- [Tailwind CDN 은 런타임 컴파일] → publish 와 같은 방식이라 결과가 같음. 운영 성능은 이번 범위 밖

## Migration Plan

- 새 프로젝트라 옮길 데이터가 없다. 되돌리기는 `backend/` · `frontend/` 를 지우면 된다

## Open Questions

- 없음
