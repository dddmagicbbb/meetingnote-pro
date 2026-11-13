# Tasks

## 1. 준비

- [x] 1.1 `requirements.txt` (fastapi · uvicorn · sqlalchemy · psycopg[binary] · pyjwt · bcrypt · python-multipart · python-dotenv · google-genai · pytest · httpx) 작성 후 `pip install -r requirements.txt` 가 성공하는지 확인
- [x] 1.2 `.gitignore` 에 `.env` · `meetingnote.db` · `__pycache__/` · `.pytest_cache/` 를 넣고, 루트 `.env` · `.env.example` 이 GEMINI_API_KEY · GEMINI_MODEL 두 줄뿐인지 확인
- [x] 1.3 `backend/` · `backend/routers/` · `backend/tests/` · `frontend/` 뼈대를 만들고 `publish/theme.js` 를 `frontend/theme.js` 로 복사한 뒤 두 파일 해시가 같은지 확인

## 2. 백엔드 구현

- [x] 2.1 `config.py` · `db.py` - 루트 `.env` 읽기, `DATABASE_URL` 유무로 Postgres / SQLite 분기. `python -c "import backend.db"` 가 `sqlite:///meetingnote.db` 를 고르는지 확인
- [x] 2.2 `models.py` 7테이블(users · teams · memberships · meetings · todos · comments · activities)과 시작 때 `create_all`. 서버를 띄운 뒤 `meetingnote.db` 에 7테이블이 생겼는지 확인
- [x] 2.3 `errors.py` - `{code, msg}` 오류 모양, 422 → 400 `VALIDATION_ERROR`, 없는 경로 → 404 `NOT_FOUND`. 빈 본문으로 signup 을 불러 400 `{code,msg}` 가 오는지 확인
- [x] 2.4 `main.py` - `/api` 라우터, Swagger UI `/docs` (HTTPBearer · 태그 6개), `frontend/` StaticFiles. `/docs` 에 27개 엔드포인트가 태그별로 보이고 `/login.html` 이 열리는지 확인
- [x] 2.5 Auth 5개 (signup · login · me GET/PUT · logout) - bcrypt · JWT 24h · 401 `TOKEN_EXPIRED` · 401 `INVALID_CREDENTIALS` · 409 `EMAIL_DUPLICATED` · 400 `EMAIL_INVALID` / `PASSWORD_TOO_WEAK`. Swagger UI 에서 가입 → Authorize → `GET /api/auth/me` 가 200 인지 확인
- [x] 2.6 Team 6개 - 팀 생성(owner · `MN-XXXX`) · 목록 · 합류(`member_join`) · 멤버(todo_count) · 코드 재발급 · 이름 변경, 한 사람 한 팀 400, 정원 6명 409 `TEAM_FULL`, owner 전용 403 `OWNER_ONLY`. Swagger UI 로 두 계정 생성 → 합류 → member 로 이름 변경 403 확인
- [x] 2.7 `gemini.py` - 받아쓰기(20MB 초과는 Files API) · 세 갈래 구분(JSON) · 5xx 1회 재시도 · 키 없음 502. 키가 빈 상태로 `POST /api/upload` 가 502 `VALIDATION_ERROR` 를 주는지 확인
- [x] 2.8 Meeting 6개 - 업로드(앞 바이트로 mp3 · wav 판정, 그 밖 415) · 저장(세 갈래 구분 · 담당자 대조 · `meeting_add` · `todo_assign`) · 목록(집계 3종 · body 없음 · `q` · `from/to` · met_at 내림차순) · 단건(body · todos · can_edit) · 수정(재구분 없음) · 삭제(할 일 · 댓글 함께). Swagger UI 로 본문 직접 넣어 저장 · 검색 · 삭제가 되는지 확인
- [x] 2.9 Todo 5개 - 팀 목록(meeting_title · can_delete · status 다음 due_text 순) · 직접 등록 · 상태 · 담당자 · 기한 변경(`todo_done` · `todo_assign`) · 내 할 일 · 삭제 권한(만든 사람 · 담당자 · owner). Swagger UI 로 등록 → DONE → 활동기록에 `todo_done` 이 남는지 확인
- [x] 2.10 Comment 3개 - 등록(1~500자 · `comment_add`) · 목록(created_at 오름차순 · can_delete) · 삭제(쓴 사람 · owner). Swagger UI 로 501자가 400 인지 확인
- [x] 2.11 Activity 2개 - 팀 · 내 활동기록(최근순 50건 · 서버가 만든 text). Swagger UI 로 앞 단계 활동이 최근순으로 나오는지 확인

## 3. 백엔드 테스트

- [x] 3.1 `tests/conftest.py` - 임시 SQLite · TestClient · 가입/팀 만들기 도우미 · `gemini.py` 가짜 응답(monkeypatch). `pytest --collect-only` 가 오류 없이 도는지 확인
- [x] 3.2 `test_auth.py` - specs/auth 의 서버 시나리오(가입 · 해시 저장 · 형식 · 약한 비번 · 중복 · 로그인 실패 통일 · 토큰 없음 · 만료 · 이름만 변경 · 로그아웃). `pytest backend/tests/test_auth.py` 통과
- [x] 3.3 `test_team.py` - 생성 · 한 사람 한 팀 · 합류 · 없는 코드 · 정원 6명 · todo_count · 재발급 후 옛 코드 · owner 전용 403 · 다른 팀 403. `pytest backend/tests/test_team.py` 통과
- [x] 3.4 `test_meeting.py` - 업로드 wav 통과 · mp4 와 확장자만 바꾼 파일 415 · 키 없음 502 · 5xx 재시도 후 502 · 저장과 세 갈래 · 담당자 대조(존칭 · 없는 사람) · 구분 실패 시 미저장 · 목록 필드 · 검색 · 기간 · 수정 시 재구분 없음 · 삭제 연쇄 · 수정 권한 403 · 없는 회의록 404. `pytest backend/tests/test_meeting.py` 통과
- [x] 3.5 `test_todo.py` - 목록 필드와 정렬 · 내 할 일 · 상태 3값과 되돌림 · 없는 상태값 400 · 팀 밖 담당자 400 · 삭제 권한 · 직접 등록. `pytest backend/tests/test_todo.py` 통과
- [x] 3.6 `test_comment.py` · `test_activity.py` - 오름차순 · 500자 · 삭제 권한 · kind 5종만 · 팀 생성 미기록 · 50건 상한 · 내 활동. 두 파일 통과
- [x] 3.7 `pytest -q` 전체 실행 결과(통과 · 실패 수)를 사용자에게 보고

## 4. 프론트엔드

- [x] 4.1 `frontend/api.js` - 토큰 저장 · Bearer 헤더 · 401 이면 토큰 삭제 후 `/login.html` · 소속 팀 없으면 `/team.html` · `{code,msg}` 를 화면 오류로 넘김. 만료 토큰을 넣고 meetings.html 을 열어 로그인 화면으로 가는지 확인
- [x] 4.2 `login.html` - publish 마크업 이식, stateBar · 더미 제거, B-01~B-11 동작(제출 전 오류 없음 · 화면 검사 · 버튼 잠금 · 가입 뒤 join · 로그인 뒤 분기). 11개 상태를 실제 조작으로 재현
- [x] 4.3 `meetings.html` - 목록 카드(STRIPE 순환) · 빈 상태 · 검색 · 기간 · 새 회의록 팝업 · 업로드 진행 · 415 / 502 표시 · 정리 중 잠금 · 저장 뒤 비움. C-01~C-11 재현
- [x] 4.4 `detail.html` - 3단 · 본문 접기 · 수정 / 삭제 팝업과 can_edit 잠금 · 담당자 메뉴(UI.menu) · 상태 변경 · 댓글 입력 카운터 · 등록 · 삭제 · 없는 회의록. D-01~D-13 재현
- [x] 4.5 `todos.html` - 내 할 일 / 전체 · 포인터 끌기(실패 시 원위치) · 좁은 화면 눌러서 칸 고르기 · 담당자 배정 · 화면 필터 · 「어제 · 지난주 · 지난달」 붉은 띠(완료 제외) · can_delete 잠금 · 빈 상태 · 직접 등록. E-01~E-13 재현
- [x] 4.6 `team.html` - 소속 없음(만들기 · 합류) · 코드 복사 · 재발급 · 정원 초과 팝업 · 이름 저장 · member 잠금 · 활동기록(kind 별 띠색). F-01~F-08 재현
- [x] 4.7 `profile.html` - 내 정보 · 이름 / 비밀번호 변경(불일치 화면 차단 · 8자) · 저장 중 잠금 · 내 할 일 · 내 활동 · 활동 없음 · 로그아웃. J-01~J-07 재현
- [x] 4.8 디자인 규칙 점검 - `frontend/*.html` 에 hex 색 · `!important` · `style=`(진행 막대 width 제외) · `stateBar` 가 없고, `rounded-*` 종류가 publish 와 같은지 grep 으로 확인

## 5. 사람 수락

- [x] 5.1 사람이 눈으로 확인: `.env` 에 실제 GEMINI_API_KEY 를 넣고 `uvicorn backend.main:app --reload` → http://127.0.0.1:8000/login.html 에서 가입 · 팀 생성 → `회의_녹음.wav` 업로드 · 저장 → 상세에서 요약 · 결정사항 · 할 일이 나오고 담당자 배정 → 칸반에서 끌어 완료 → 팀 활동기록에 남음. 각 화면을 `publish/` 같은 파일과 나란히 띄워 색 · 간격이 같고, 360px 폭에서 가로 스크롤이 없으며, http://127.0.0.1:8000/docs 에서 API 를 호출할 수 있음
