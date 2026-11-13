# Spec Delta

## ADDED Requirements

### Requirement: 기한 날짜 변환
<!-- 근거: 정의서 7-2 기한 지남 판정 · E-08 기한 지남 · todos.html (late) · modify-todo-due-date (지시) -->
시스템은 할 일의 기한 글자(due_text)를 기준일에 맞춰 날짜(due_date, `YYYY-MM-DD`)로 바꿔 함께 저장해야 한다(SHALL). 기준일은 회의록에서 뽑힌 할 일이면 회의 날짜(met_at 의 한국 날짜), 직접 등록한 할 일이면 등록한 날이다. 주는 월요일에 시작한다. 뜻이 하나로 정해지지 않는 글자는 due_date 를 비우고, due_text 는 어느 경우든 받은 글자 그대로 남긴다.

#### Scenario: 다음 주 금요일
- **GIVEN** 회의 날짜가 2026-09-24(목)
- **WHEN** 기한 글자가 「다음 주 금요일」 이면
- **THEN** due_date 는 2026-10-02 이고 due_text 는 「다음 주 금요일」 그대로다

#### Scenario: 다음 주까지
- **GIVEN** 회의 날짜가 2026-09-24(목)
- **WHEN** 기한 글자가 「다음 주까지」 이면
- **THEN** due_date 는 7일 뒤인 2026-10-01 이다

#### Scenario: 이번 주 안
- **GIVEN** 회의 날짜가 2026-09-24(목)
- **WHEN** 기한 글자가 「이번 주 안」 또는 「이번 주까지」 이면
- **THEN** due_date 는 그 주 금요일인 2026-09-25 이다

#### Scenario: 못 정하는 글자
- **WHEN** 기한 글자가 「다음 분기」 · 「곧」 처럼 날짜 하나로 정해지지 않거나 비어 있으면
- **THEN** due_date 는 null 이고 due_text 는 받은 글자 그대로다

#### Scenario: 직접 등록은 등록한 날 기준
- **GIVEN** 오늘이 2026-11-13(금)
- **WHEN** 칸반에서 기한 「내일」 로 할 일을 직접 등록하면
- **THEN** due_date 는 2026-11-14 이다

### Requirement: 기한 표시
<!-- 근거: E-01 내 할 일 · E-02 전체 · D-01 기본 · J-01 내 정보 · todos.html, detail.html, profile.html · modify-todo-due-date (지시) -->
칸반 카드 · 회의록 상세의 할 일 · 내 정보의 내 할 일은 due_date 가 있으면 날짜를 「10월 2일 (금)」 꼴로 보이고 원래 글자(due_text)도 함께 보여야 한다(SHALL). due_date 가 없으면 원래 글자만, 둘 다 없으면 「미정」 을 보인다.

#### Scenario: 날짜와 원래 글자
- **WHEN** due_date 가 2026-10-02 이고 due_text 가 「다음 주 금요일」 인 카드를 그리면
- **THEN** 「10월 2일 (금)」 과 「다음 주 금요일」 이 함께 보인다

#### Scenario: 날짜를 못 정한 기한
- **WHEN** due_date 가 null 이고 due_text 가 「다음 분기」 인 카드를 그리면
- **THEN** 「다음 분기」 만 보인다

## MODIFIED Requirements

### Requirement: 팀 할 일 목록
<!-- 근거: E-02 전체 · todos.html (all) · modify-todo-due-date (지시) -->
`GET /api/teams/{id}/todos` 는 id · what · assignee_id · assignee_name · due_text · due_date · status 에 meeting_title 과 can_delete 를 더해 status 다음 due_date(빈 값은 뒤) 다음 due_text 순으로 돌려줘야 한다(SHALL). 직접 등록한 할 일은 meeting_title 이 null 이고 화면은 출처를 「직접 등록」 으로 그린다.

#### Scenario: 회의록 제목
- **WHEN** 「2차 스프린트 계획 회의」 에서 뽑힌 할 일이 있는 팀의 전체 탭을 열면
- **THEN** 카드 아래에 회의록 제목 「2차 스프린트 계획 회의」 가 보인다

#### Scenario: 날짜 순 정렬
- **WHEN** 같은 상태의 할 일 due_date 가 2026-10-02 · null · 2026-09-25 이면
- **THEN** 2026-09-25 · 2026-10-02 · null 순서로 온다

### Requirement: 담당자 배정
<!-- 근거: D-03 담당자 배정 · E-06 담당자 배정 · E-09 담당자 미정 · detail.html (assign), todos.html (assign, unassigned) · modify-todo-due-date (지시) -->
팀원 누구나 `PUT /api/todos/{id}` 로 담당자(멤버 목록 중 하나 또는 미정)와 기한 글자를 바꿀 수 있어야 한다(SHALL). 기한 글자를 바꾸면 원래 기준일(회의 날짜 또는 등록한 날)로 due_date 를 다시 계산한다. 담당자를 사람으로 정하면 `todo_assign` 활동을 남긴다. 회의에서 정해지지 않은 담당자는 「미정」 으로 두고 지어내지 않는다.

#### Scenario: 미정에서 배정
- **WHEN** 상세 화면에서 미정인 할 일의 배지를 눌러 메뉴에서 이주임을 고르면
- **THEN** 200 을 받고 배지가 「이주임」 으로 바뀌며 `todo_assign` 활동이 생긴다

#### Scenario: 팀 밖 사람
- **WHEN** 다른 팀 사용자의 id 를 assignee_id 로 보내면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

#### Scenario: 기한 글자 수정
- **GIVEN** 2026-09-24(목) 회의에서 뽑힌 할 일
- **WHEN** 기한 글자를 「다음 주까지」 로 바꾸면
- **THEN** due_date 는 오늘이 아니라 회의 날짜 기준인 2026-10-01 이 된다

### Requirement: 기한 지남 표시
<!-- 근거: E-08 기한 지남 · todos.html (late), 정의서 7-2 기한 지남 판정 · modify-todo-due-date (지시) -->
서버는 기한 지남을 판정하지 않는다. 화면은 due_date 가 보는 사람의 오늘 날짜보다 앞이고 DONE 이 아닌 카드에만 붉은 띠를 그려야 한다(SHALL). due_date 가 없으면 글자와 상관없이 판정하지 않는다.

#### Scenario: 날짜가 지남
- **GIVEN** 오늘이 2026-11-13
- **WHEN** due_date 가 2026-11-12 이고 status 가 OPEN 이면
- **THEN** 카드 띠가 red 다

#### Scenario: 오늘이 기한
- **GIVEN** 오늘이 2026-11-13
- **WHEN** due_date 가 2026-11-13 이면
- **THEN** 붉은 띠를 그리지 않는다

#### Scenario: 완료는 제외
- **WHEN** due_date 가 지났지만 status 가 DONE 이면
- **THEN** 붉은 띠를 그리지 않는다

#### Scenario: 지난주
- **WHEN** due_text 가 「지난주」 처럼 날짜 하나로 정해지지 않아 due_date 가 null 이면
- **THEN** 글자와 상관없이 붉은 띠를 그리지 않는다

### Requirement: 직접 등록
<!-- 근거: E-13 직접 등록 · todos.html (create) · modify-todo-due-date (지시) -->
`POST /api/teams/{id}/todos` 는 회의록 없이 내용(필수) · 담당자 · 기한 글자를 받아 OPEN 상태로 만들고 201 을 돌려줘야 한다(SHALL). 기한 글자는 등록한 날 기준으로 due_date 로 바꿔 함께 저장한다. 담당자가 있으면 `todo_assign` 활동을 남긴다.

#### Scenario: 직접 등록
- **WHEN** 새 할 일 팝업에 「회의실 예약 규칙 정리」 · 이주임 · 「이번 주 안」 을 넣고 등록하면
- **THEN** 201 을 받고 대기 칸에 출처 「직접 등록」 카드가 생기며 due_date 는 등록한 주의 금요일이다

#### Scenario: 내용 없음
- **WHEN** 내용 없이 등록하면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다
