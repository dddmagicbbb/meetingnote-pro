# Spec Delta

## Purpose

녹취 파일을 받아쓴 본문 한 덩어리를 회의록으로 저장하면서 요약 · 결정사항 · 할 일 세 갈래로 나누고, 팀이 목록 · 검색 · 상세에서 지난 결정을 찾아 읽고 고치게 한다.

## ADDED Requirements

### Requirement: 회의록 목록
<!-- 근거: C-01 목록 · meetings.html (list) -->
`GET /api/teams/{id}/meetings` 는 id · title · met_at · attendees · summary · created_at 에 todo_done_count · todo_total_count · decision_count 를 더해 met_at 내림차순으로 돌려줘야 한다(SHALL). body 와 딸린 할 일은 목록에 싣지 않는다. 화면은 카드에 제목 · 시각 · 참석자 · 요약 한 줄 · 「결정 N」 · 「할 일 완료/전체」 를 그리고, 카드 띠색은 목록 순서대로 blue · green · orange · purple · red 를 돌려 쓴다.

#### Scenario: 목록 응답
- **WHEN** 회의록 3건이 있는 팀의 목록을 부르면
- **THEN** met_at 최신순 3건을 받고 각 항목에 body 필드가 없다

#### Scenario: 카드 띠 순환
- **WHEN** 회의록 6건을 그리면
- **THEN** 띠색은 blue · green · orange · purple · red · blue 순서다

### Requirement: 빈 목록
<!-- 근거: C-02 빈 상태 · meetings.html (empty) -->
회의록이 없으면 시스템은 200 과 빈 배열을 돌려주고, 화면은 「아직 회의록이 없음」 과 다음 행동 안내를 보여야 한다(SHALL).

#### Scenario: 팀 합류 직후
- **WHEN** 회의록이 0건인 팀의 목록을 열면
- **THEN** 200 빈 배열을 받고 「새 회의록 버튼으로 첫 회의를 올려 보기」 가 보인다

### Requirement: 검색과 기간
<!-- 근거: C-03 검색 · C-04 검색 0건 · meetings.html (search, search-none) -->
목록은 `?q=` 로 제목과 참석자만 부분 일치 검색하고 `?from=&to=` (ISO 날짜) 로 met_at 기간을 거를 수 있어야 한다(SHALL). 본문과 요약은 검색 대상이 아니다. 결과가 없으면 404 가 아니라 200 빈 배열이다.

#### Scenario: 제목 일치
- **WHEN** `q=배포` 로 검색하면
- **THEN** 제목에 「배포」 가 들어간 「배포 환경 점검」 만 나온다

#### Scenario: 본문만 일치
- **WHEN** 본문에만 있는 단어로 검색하면
- **THEN** 200 빈 배열을 받고 화면에 「검색 결과 없음」 이 보인다

#### Scenario: 기간
- **WHEN** `from=2026-09-01&to=2026-09-15` 로 부르면
- **THEN** met_at 이 그 기간 안인 회의록만 나온다

### Requirement: 녹취 업로드와 받아쓰기
<!-- 근거: C-05 새 회의록 · C-06 올리는 중 · C-07 받아쓰기 완료 · meetings.html (new, upload, upload-done) -->
`POST /api/upload` 는 mp3 · wav 파일을 받아 Gemini 로 받아쓴 본문을 200 `{body}` 로 돌려줘야 한다(SHALL). 이 단계에서는 저장하지 않는다. 20MB 를 넘는 파일은 Files API 경로로 보내고 크기로 거부하지 않는다. 화면은 업로드하는 동안 진행률을 보이고, 끝나면 본문 칸을 채운다.

#### Scenario: wav 받아쓰기
- **WHEN** `회의_녹음.wav` 를 새 회의록 팝업에 끌어다 놓으면
- **THEN** 진행 표시 뒤 200 `{body}` 를 받고 본문 칸에 받아쓴 글이 채워지며 회의록은 아직 저장되지 않는다

### Requirement: 업로드 형식 제한
<!-- 근거: C-08 에러 - 형식 · meetings.html (err-type) -->
업로드는 확장자가 아니라 파일 내용 형식으로 mp3 · wav 를 판정해야 하고, 그 밖의 형식은 415 `UNSUPPORTED_MEDIA_TYPE` 으로 거부해야 한다(SHALL).

#### Scenario: mp4 업로드
- **WHEN** `회의_녹화.mp4` 를 올리면
- **THEN** 415 `UNSUPPORTED_MEDIA_TYPE` 을 받고 「mp3 또는 wav 만 올릴 수 있음」 이 보인다

#### Scenario: 확장자만 바꾼 파일
- **WHEN** mp4 내용에 이름만 `.wav` 로 바꾼 파일을 올리면
- **THEN** 415 `UNSUPPORTED_MEDIA_TYPE` 을 받는다

### Requirement: 받아쓰기 실패
<!-- 근거: C-09 에러 - 받아쓰기 · meetings.html (err-stt), 정의서 9 받아쓰기 -->
Gemini 가 5xx 를 주면 한 번 재시도하고, 그래도 실패하거나 `GEMINI_API_KEY` 가 없으면 502 `VALIDATION_ERROR` 를 돌려줘야 한다(SHALL). 화면은 본문 칸에 메모를 직접 붙여 넣어 저장할 수 있게 둔다.

#### Scenario: 키 없음
- **WHEN** `GEMINI_API_KEY` 가 비어 있는 채로 업로드하면
- **THEN** 502 `{code:"VALIDATION_ERROR", msg}` 를 받고 본문 칸은 입력 가능하다

### Requirement: 회의록 저장과 세 갈래 구분
<!-- 근거: C-10 정리 중 · C-11 저장 완료 · meetings.html (saving, saved), 정의서 7-3 -->
`POST /api/teams/{id}/meetings` 는 제목 · 회의시각 · 본문(필수)과 참석자를 받아, 저장하면서 본문에서 요약(3~5줄) · 결정사항(합의된 것만) · 할 일(담당자와 기한이 드러난 것만)을 뽑아 201 로 돌려줘야 한다(SHALL). 본문은 지우지 않는다. `meeting_add` 활동을 남기고, 담당자가 붙은 할 일마다 `todo_assign` 활동을 남긴다.

#### Scenario: 저장 성공
- **WHEN** 받아쓴 본문으로 「정리하기」 를 누르면
- **THEN** 버튼이 「정리 중...」 으로 잠기고, 201 뒤 팝업이 닫히고 입력칸이 비며 새 회의록이 목록 맨 위에 보인다

#### Scenario: 필수값 누락
- **WHEN** 본문 없이 저장하면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 결정사항과 할 일 저장 모양
<!-- 근거: 정의서 7-2 decisions 저장 · 7-3 저장 모양 -->
결정사항은 줄바꿈으로 구분한 TEXT 한 칸으로 저장하고 decision_count 는 빈 줄을 뺀 줄 수여야 한다(SHALL). 할 일은 「내용 | 담당자 | 기한」 으로 뽑아 todos 에 OPEN 상태로 넣는다. 담당자는 팀 멤버 이름과 공백 · 존칭(님)을 무시하고 대조하고, 맞는 멤버가 없으면 미정(null)이다. due_text 는 들은 글자 그대로 둔다.

#### Scenario: 담당자 대조
- **WHEN** 본문에 「김대리님이 다음 주 금요일까지 목록 화면 하겠습니다」 가 있고 팀에 `김대리` 가 있으면
- **THEN** 할 일의 담당자는 김대리, due_text 는 「다음 주 금요일」 이다

#### Scenario: 없는 사람
- **WHEN** 멤버에 없는 이름이 담당자로 나오면
- **THEN** 할 일의 담당자는 미정이다

### Requirement: 구분 실패
<!-- 근거: 정의서 7-3 구분 실패 -->
세 갈래 구분 응답을 읽지 못하면 시스템은 회의록을 저장하지 않고 502 `VALIDATION_ERROR` 를 돌려줘야 한다(SHALL). 화면은 본문을 그대로 남겨 다시 저장할 수 있게 한다.

#### Scenario: 엉뚱한 응답
- **WHEN** Gemini 가 형식에 맞지 않는 응답을 주면
- **THEN** 502 를 받고 DB 에 회의록이 생기지 않으며 본문 칸은 그대로다

### Requirement: 회의록 상세
<!-- 근거: D-01 기본 · D-05 결정사항 없음 · D-06 할 일 없음 · D-07 본문 펼침 · detail.html (view, no-decision, no-todo, body-open) -->
`GET /api/meetings/{id}` 는 목록 필드에 body · todos · can_edit 를 더해 돌려줘야 한다(SHALL). 화면은 요약 · 결정사항(번호) · 할 일 3단을 먼저 보이고 본문은 접어 둔다. 결정사항 · 할 일이 없으면 「결정사항 없음」 · 「할 일 없음」 을 보이고 억지로 채우지 않는다.

#### Scenario: 본문 접힘
- **WHEN** detail.html?id=3 을 열면
- **THEN** 3단이 보이고 본문은 「본문 펼치기」 를 눌러야 보인다

#### Scenario: 결정사항 없음
- **WHEN** decisions 가 빈 회의록을 열면
- **THEN** 결정사항 칸에 「결정사항 없음」 이 보인다

### Requirement: 회의록 수정
<!-- 근거: D-02 수정 · detail.html (edit), 정의서 7-3 본문 수정 -->
`PUT /api/meetings/{id}` 는 제목 · 회의시각 · 참석자 · 본문을 고쳐야 한다(SHALL). 본문을 고쳐도 받아쓰기와 세 갈래 구분을 다시 돌리지 않고 뽑아 둔 요약 · 결정사항 · 할 일은 그대로 둔다.

#### Scenario: 본문 수정
- **WHEN** 작성자가 본문을 고쳐 저장하면
- **THEN** 200 을 받고 summary · decisions · todos 는 바뀌지 않는다

### Requirement: 회의록 삭제
<!-- 근거: D-08 삭제 확인 · detail.html (delete) -->
`DELETE /api/meetings/{id}` 는 회의록과 딸린 할 일 · 댓글을 함께 지우고 204 를 돌려줘야 한다(SHALL). 화면은 「딸린 할 일 N건도 함께 삭제됨. 되돌릴 수 없음」 확인 팝업을 먼저 띄운다.

#### Scenario: 딸린 할 일 함께 삭제
- **WHEN** 할 일 3건이 딸린 회의록을 삭제하면
- **THEN** 204 를 받고 그 할 일 3건도 칸반에서 사라진다

### Requirement: 회의록 수정 · 삭제 권한
<!-- 근거: 정의서 7-4 회의록 · 댓글 · detail.html (view) -->
회의록은 올린 사람과 owner 만 고치고 지울 수 있어야 한다(SHALL). can_edit 가 false 면 화면은 수정 · 삭제 버튼을 비활성으로 보이고, 다른 멤버가 API 를 부르면 403 `FORBIDDEN` 이다.

#### Scenario: 다른 member
- **WHEN** 작성자도 owner 도 아닌 member 가 `PUT /api/meetings/{id}` 를 부르면
- **THEN** 403 `FORBIDDEN` 을 받는다

### Requirement: 없는 회의록
<!-- 근거: D-13 없는 회의록 · detail.html (not-found) -->
없거나 다른 팀의 회의록을 부르면 시스템은 404 `MEETING_NOT_FOUND` 를 돌려주고, 화면은 「회의록을 찾을 수 없음」 팝업과 목록으로 가는 버튼을 보여야 한다(SHALL).

#### Scenario: 없는 id
- **WHEN** detail.html?id=99 를 열면
- **THEN** 404 `MEETING_NOT_FOUND` 를 받고 「목록으로」 를 누르면 meetings.html 로 간다
