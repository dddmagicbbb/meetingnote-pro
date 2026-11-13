# Tasks

## 1. 백엔드 구현

- [x] 1.1 `backend/duedate.py` - `parse_due(text, base)` 를 design.md 변환표대로 구현하고 `kst_date(dt)` (UTC → UTC+9 날짜) 를 둔다. `python -c` 로 「다음 주 금요일」 + 2026-09-24 → 2026-10-02 가 나오는지 확인
- [x] 1.2 `models.py` 에 `Todo.due_date` (Date, NULL) 추가, `db.py` 에 `migrate()` (열 없으면 ALTER TABLE 후 빈 due_date 채우기) 를 두고 시작 시 `create_all` 다음에 부른다. 기존 `meetingnote.db` 로 서버를 띄워 `todos` 에 `due_date` 열이 생기고 값이 채워지는지 sqlite 로 확인
- [x] 1.3 `routers/meetings.py` - 회의록 저장 때 회의 날짜 기준 `due_date` 저장. `routers/todos.py` - 직접 등록은 등록한 날 기준, `PUT` 의 `due_text` 변경 시 원래 기준일로 재계산, 응답에 `due_date`, 정렬을 status → due_date(빈 값 뒤) → due_text 로. Swagger UI 로 「다음 주까지」 직접 등록 시 7일 뒤 날짜가 오는지 확인

## 2. 백엔드 테스트

- [x] 2.1 `tests/test_duedate.py` - 변환표 각 행(오늘 · 내일 · 모레 · 어제 · N일 뒤 · 다음 주 · 이번 주 안 · 이번 주/다음 주/다다음 주 X요일 · X요일 · M월 D일(해 넘김 포함) · D일까지 · 다음 달 D일 · 월말 · YYYY-MM-DD · 못 정함 · 없는 날짜)과 UTC+9 경계(UTC 15:00 = 한국 다음 날) 테스트. `pytest backend/tests/test_duedate.py` 통과
- [x] 2.2 `test_meeting.py` · `test_todo.py` - 회의 날짜 기준 저장, 직접 등록 기준일, 기한 글자 수정 시 회의 날짜 기준 재계산, 응답 `due_date` 필드, 날짜 순 정렬(빈 값 뒤), 이관 함수(열 없는 DB → 열 추가 · 채움 · 두 번 돌려도 같음) 테스트. `pytest -q` 전체 통과
- [x] 2.3 `pytest -q` 전체 결과(통과 · 실패 수)를 사용자에게 보고

## 3. 프론트엔드

- [x] 3.1 `frontend/api.js` - `isLate` 를 due_date 와 오늘 날짜 비교로 바꾸고 `LATE_WORDS` 제거, `FMT.due(todo)` 추가(「10월 2일 (금)」 + 원래 글자, 없으면 「미정」). 브라우저 콘솔에서 `PAL.isLate({status:"OPEN",due_date:"2000-01-01"})` 가 true 인지 확인
- [x] 3.2 `todos.html` · `profile.html` 기한 칩을 날짜 + 원래 글자로, `todos.html` 화면 정렬을 서버와 같게. `detail.html` 기한 입력칸 옆에 변환된 날짜 표시. publish 에 있는 클래스만 쓰는지 grep(hex · `!important` · `style=`) 으로 확인
- [x] 3.3 `backend/tests/e2e/` - 기한 지남(날짜가 어제인 할 일 붉은 띠, 오늘은 아님, 날짜 없는 「지난주」 는 아님) · 날짜 표시 · 직접 등록 날짜 확인으로 e2e 갱신 후 임시 DB 서버에서 `run_all.py` 전체 통과

## 4. 사람 수락

- [x] 4.1 사람이 눈으로 확인: `회의_녹음.wav` 로 회의록을 저장하면 할 일 기한이 회의 날짜 기준 날짜(예: 「다음 주 금요일」 → 그 금요일)와 원래 글자로 함께 보이고, 칸반에서 날짜가 지난 할 일만 붉은 띠다
