# todo Specification

## Purpose

회의록에서 뽑히거나 직접 등록된 할 일을 대기 · 진행 · 완료 세 칸 칸반으로 추적하고, 담당자를 배정하며 내게 배정된 일만 따로 볼 수 있게 한다.

## Requirements

### Requirement: 팀 할 일 목록
<!-- 근거: E-02 전체 · todos.html (all) -->
`GET /api/teams/{id}/todos` 는 id · what · assignee_id · assignee_name · due_text · status 에 meeting_title 과 can_delete 를 더해 status 다음 due_text 순으로 돌려줘야 한다(SHALL). 직접 등록한 할 일은 meeting_title 이 null 이고 화면은 출처를 「직접 등록」 으로 그린다.

#### Scenario: 회의록 제목
- **WHEN** 「2차 스프린트 계획 회의」 에서 뽑힌 할 일이 있는 팀의 전체 탭을 열면
- **THEN** 카드 아래에 회의록 제목 「2차 스프린트 계획 회의」 가 보인다

### Requirement: 내 할 일
<!-- 근거: E-01 내 할 일 · J-01 내 정보 · todos.html (mine), profile.html (view) -->
`GET /api/me/todos` 는 로그인한 사람에게 배정된 할 일만 같은 필드로 돌려줘야 한다(SHALL). 칸반의 「내 할 일」 탭과 내 정보 화면의 내 할 일이 이것을 쓴다.

#### Scenario: 내 것만
- **WHEN** 김대리가 「내 할 일」 탭을 열면
- **THEN** 김대리에게 배정된 할 일만 칸반에 보인다

### Requirement: 칸반 세 칸
<!-- 근거: E 할 일 칸반 · D-04 상태 변경 · todos.html, detail.html (progress) -->
할 일 상태는 OPEN(대기) · DOING(진행) · DONE(완료) 세 값뿐이어야 하고(SHALL), 어느 방향으로든 바꿀 수 있다(되돌림 허용). 상태는 `PUT /api/todos/{id}` 의 status 로 바꾸며 팀원 누구나 바꿀 수 있다. DONE 으로 바꾸면 `todo_done` 활동을 남긴다.

#### Scenario: 완료 처리
- **WHEN** 팀원이 할 일을 DONE 으로 바꾸면
- **THEN** 200 을 받고 팀 활동기록에 「최선임 할 일 「배포 키 환경변수 이전」 완료」 같은 `todo_done` 항목이 생긴다

#### Scenario: 되돌림
- **WHEN** DONE 인 할 일을 OPEN 으로 바꾸면
- **THEN** 200 을 받고 대기 칸으로 돌아간다

#### Scenario: 없는 상태값
- **WHEN** status 에 `CLOSED` 를 보내면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 끌어서 옮기기
<!-- 근거: E-03 끌어 옮기는 중 · E-04 이동 완료 · todos.html (drag, moved) -->
칸반은 포인터 이벤트로 카드를 끌어 칸을 옮겨야 하고(SHALL) HTML5 네이티브 드래그는 쓰지 않는다. 끄는 동안 반투명 사본이 따라붙고 놓을 칸은 점선으로 바뀐다. 놓는 순간 한 번만 `PUT` 을 부르고, 칸의 빈자리에 놓아도 이동한다. 실패하면 카드는 원래 칸으로 돌아간다.

#### Scenario: 이동 실패
- **WHEN** 카드를 진행 칸에 놓았는데 `PUT` 이 실패하면
- **THEN** 카드는 원래 칸으로 돌아간다

### Requirement: 눌러서 칸 고르기
<!-- 근거: E-05 눌러서 칸 고르기 · N-01 360px 반응형 · todos.html (pick) -->
좁은 화면에서는 칸이 세로로 쌓이고, 카드를 누르면 대기 · 진행 · 완료 버튼이 떠서 칸을 고를 수 있어야 한다(SHALL). 360px 폭에서 가로 스크롤이 생기지 않는다.

#### Scenario: 360px
- **WHEN** 360px 폭에서 카드를 누르고 「완료」 를 고르면
- **THEN** `PUT` 200 뒤 카드가 완료 칸으로 가고 가로 스크롤은 없다

### Requirement: 담당자 배정
<!-- 근거: D-03 담당자 배정 · E-06 담당자 배정 · E-09 담당자 미정 · detail.html (assign), todos.html (assign, unassigned) -->
팀원 누구나 `PUT /api/todos/{id}` 로 담당자(멤버 목록 중 하나 또는 미정)와 기한 글자를 바꿀 수 있어야 한다(SHALL). 담당자를 사람으로 정하면 `todo_assign` 활동을 남긴다. 회의에서 정해지지 않은 담당자는 「미정」 으로 두고 지어내지 않는다.

#### Scenario: 미정에서 배정
- **WHEN** 상세 화면에서 미정인 할 일의 배지를 눌러 메뉴에서 이주임을 고르면
- **THEN** 200 을 받고 배지가 「이주임」 으로 바뀌며 `todo_assign` 활동이 생긴다

#### Scenario: 팀 밖 사람
- **WHEN** 다른 팀 사용자의 id 를 assignee_id 로 보내면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 담당자 필터
<!-- 근거: E-07 담당자 필터 · todos.html (filter) -->
「담당자: 전체」 필터는 화면에서만 거르고 서버를 다시 부르지 않아야 한다(SHALL).

#### Scenario: 필터
- **WHEN** 전체 탭에서 담당자 필터를 박과장으로 고르면
- **THEN** 추가 요청 없이 박과장 카드만 남는다

### Requirement: 기한 지남 표시
<!-- 근거: E-08 기한 지남 · todos.html (late), 정의서 7-2 기한 지남 판정 -->
서버는 기한 지남을 판정하지 않는다. 화면은 due_text 가 「어제」 · 「지난주」 · 「지난달」 셋 중 하나이고 DONE 이 아닌 카드에만 붉은 띠를 그려야 한다(SHALL). 그 밖의 글자는 판정하지 않는다.

#### Scenario: 지난주
- **WHEN** due_text 가 「지난주」 이고 status 가 OPEN 이면
- **THEN** 카드 띠가 red 다

#### Scenario: 완료는 제외
- **WHEN** due_text 가 「어제」 이고 status 가 DONE 이면
- **THEN** 붉은 띠를 그리지 않는다

### Requirement: 완료 보존
<!-- 근거: E-10 완료만 · todos.html (done) -->
DONE 이 된 할 일은 자동으로 지우지 않고 완료 칸에 남겨야 한다(SHALL).

#### Scenario: 완료 칸
- **WHEN** 완료된 할 일이 있는 칸반을 열면
- **THEN** 완료 칸에 그 카드가 보인다

### Requirement: 할 일 삭제
<!-- 근거: E-11 할 일 삭제 · todos.html (del), 정의서 7-4 할 일 -->
`DELETE /api/todos/{id}` 는 만든 사람(회의록을 올린 사람 또는 직접 등록한 사람) · 담당자 · owner 만 부를 수 있고 204 를 돌려줘야 한다(SHALL). 목록의 can_delete 가 false 면 화면은 삭제 버튼을 비활성으로 보이고, 그 밖의 사람이 부르면 403 `FORBIDDEN` 이다.

#### Scenario: 권한 없음
- **WHEN** 만든 사람도 담당자도 owner 도 아닌 member 가 삭제를 부르면
- **THEN** 403 `FORBIDDEN` 을 받는다

#### Scenario: 담당자가 삭제
- **WHEN** 담당자가 자기 할 일을 지우면
- **THEN** 204 를 받는다

### Requirement: 빈 칸반
<!-- 근거: E-12 빈 상태 · todos.html (empty) -->
할 일이 없으면 시스템은 200 빈 배열을 돌려주고 화면은 빈 상태 안내를 보여야 한다(SHALL).

#### Scenario: 배정 0건
- **WHEN** 배정된 할 일이 없는 사람이 「내 할 일」 을 열면
- **THEN** 200 빈 배열을 받고 빈 상태 문구가 보인다

### Requirement: 직접 등록
<!-- 근거: E-13 직접 등록 · todos.html (create) -->
`POST /api/teams/{id}/todos` 는 회의록 없이 내용(필수) · 담당자 · 기한을 받아 OPEN 상태로 만들고 201 을 돌려줘야 한다(SHALL). 담당자가 있으면 `todo_assign` 활동을 남긴다.

#### Scenario: 직접 등록
- **WHEN** 새 할 일 팝업에 「회의실 예약 규칙 정리」 · 이주임 · 「이번 주 안」 을 넣고 등록하면
- **THEN** 201 을 받고 대기 칸에 출처 「직접 등록」 카드가 생긴다

#### Scenario: 내용 없음
- **WHEN** 내용 없이 등록하면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다
