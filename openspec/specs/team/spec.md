# team Specification

## Purpose

한 사람이 한 팀에만 속하는 구조에서, 팀을 만들고 초대코드 하나로 최대 6명이 합류하며 owner 와 member 두 권한으로 팀 설정을 나눠 관리하게 한다.

## Requirements

### Requirement: 팀 생성
<!-- 근거: F-02 소속 팀 없음 · team.html (onboard) -->
시스템은 `POST /api/teams` 로 팀 이름을 받아 팀을 만들고, 만든 사람을 owner 로 등록하고 초대코드를 하나 발급해야 한다(SHALL). 초대코드는 `MN-` 뒤에 영문 대문자와 숫자 4자리 꼴(예: `MN-7K2D`)이며 전체에서 겹치지 않는다. 팀 생성은 활동기록에 남기지 않는다.

#### Scenario: 팀 만들기
- **WHEN** 소속 팀이 없는 사용자가 이름 `기획팀` 으로 팀을 만들면
- **THEN** 201 과 팀 정보를 받고, 그 사용자의 role 은 `owner`, 팀에는 `MN-XXXX` 꼴 초대코드가 생긴다

### Requirement: 한 사람 한 팀
<!-- 근거: 정의서 7-4 소속 팀 수 -->
한 사람은 한 팀에만 속해야 한다(SHALL). 이미 소속이 있는 사람이 팀을 만들거나 합류하면 400 `VALIDATION_ERROR` 를 돌려준다.

#### Scenario: 소속이 있는데 팀 생성
- **WHEN** 이미 팀에 속한 사용자가 `POST /api/teams` 를 부르면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

#### Scenario: 소속이 있는데 합류
- **WHEN** 이미 팀에 속한 사용자가 다른 팀 초대코드로 `POST /api/teams/join` 을 부르면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 소속 팀 조회
<!-- 근거: B-04 로그인 성공 · F-02 소속 팀 없음 · login.html (login-ok), team.html (onboard) -->
`GET /api/teams` 는 로그인한 사람이 속한 팀을 배열로 돌려줘야 한다(SHALL). 소속이 없으면 빈 배열이다. 소속 팀이 없는 사람이 meetings.html · todos.html · detail.html 에 들어오면 화면은 team.html 로 보낸다.

#### Scenario: 소속 없음
- **WHEN** 팀이 없는 사용자가 `GET /api/teams` 를 부르면
- **THEN** 200 과 빈 배열을 받고, team.html 에 「소속 팀 없음」 과 팀 만들기 · 초대코드로 합류 두 칸이 보인다

### Requirement: 초대코드로 합류
<!-- 근거: F-02 소속 팀 없음 · F-03 초대코드 오류 · team.html (onboard, join-err) -->
시스템은 `POST /api/teams/join` 으로 초대코드를 받아 그 팀의 member 로 등록하고 `member_join` 활동을 남겨야 한다(SHALL). 없는 코드면 404 `INVITE_NOT_FOUND` 를 돌려주고 계정은 그대로 둔다.

#### Scenario: 합류 성공
- **WHEN** 소속 없는 사용자가 `MN-7K2D` 로 합류하면
- **THEN** 200 을 받고 role 은 `member`, 팀 활동기록에 「박과장 초대코드로 합류」 같은 `member_join` 항목이 생긴다

#### Scenario: 없는 코드
- **WHEN** `MN-0000` 으로 합류하면
- **THEN** 404 `INVITE_NOT_FOUND` 를 받고 계정과 로그인 상태는 유지된다

### Requirement: 팀 정원 6명
<!-- 근거: F-06 정원 초과 · team.html (full) -->
팀 인원은 6명을 넘을 수 없다(SHALL). 6명인 팀에 합류하면 409 `TEAM_FULL` 을 돌려준다.

#### Scenario: 정원 초과
- **WHEN** 이미 6명인 기획팀 코드로 합류하면
- **THEN** 409 `TEAM_FULL` 을 받고 화면에 「팀 정원이 찼음」 팝업이 뜬다

### Requirement: 멤버 목록
<!-- 근거: F-01 팀 설정 · D-03 담당자 배정 · team.html (team), detail.html (assign) -->
`GET /api/teams/{id}/members` 는 id · name · email · role · todo_count 를 돌려줘야 한다(SHALL). todo_count 는 그 사람에게 배정된 할 일 전부(완료 포함)다. 담당자 고르기 후보도 이 목록을 쓴다. 다른 팀 id 를 부르면 403 `FORBIDDEN` 이다.

#### Scenario: 멤버와 할 일 수
- **WHEN** 김대리에게 할 일 3건(완료 1건 포함)이 배정된 팀의 멤버 목록을 부르면
- **THEN** 김대리의 todo_count 는 3 이다

#### Scenario: 다른 팀
- **WHEN** 소속이 아닌 팀 id 로 멤버 목록을 부르면
- **THEN** 403 `FORBIDDEN` 을 받는다

### Requirement: 초대코드 복사
<!-- 근거: F-04 코드 복사 · F-08 member 권한 · team.html (copied, member-view) -->
팀 설정 화면은 owner 와 member 모두 초대코드를 클립보드로 복사할 수 있어야 한다(SHALL). 팀당 코드는 하나이고 사람마다 따로 발급하지 않는다.

#### Scenario: 복사
- **WHEN** member 가 코드 복사를 누르면
- **THEN** 클립보드에 `MN-7K2D` 가 들어가고 「초대코드를 복사함 - MN-7K2D」 알림이 뜬다

### Requirement: 초대코드 재발급
<!-- 근거: F-05 코드 재발급 · team.html (recode) -->
`PUT /api/teams/{id}/code` 는 owner 만 부를 수 있고, 새 코드를 발급해 이전 코드를 폐기해야 한다(SHALL). 이미 합류한 멤버는 그대로다.

#### Scenario: 재발급 후 옛 코드
- **WHEN** owner 가 코드를 재발급한 뒤 누군가 옛 코드로 합류하면
- **THEN** 404 `INVITE_NOT_FOUND` 를 받고, 새 코드로는 합류된다

### Requirement: 팀 이름 변경
<!-- 근거: F-07 팀 이름 저장 · team.html (save-name) -->
`PUT /api/teams/{id}` 는 owner 만 팀 이름을 바꿀 수 있어야 한다(SHALL).

#### Scenario: owner 가 변경
- **WHEN** owner 가 팀 이름을 `기획1팀` 으로 저장하면
- **THEN** 200 을 받고 상단 바의 팀 이름도 바뀐다

### Requirement: owner 전용 기능 잠금
<!-- 근거: F-08 member 권한 · team.html (member-view) -->
member 화면에서는 팀 이름 저장과 코드 재발급 버튼을 비활성으로 보여야 하고, member 가 그 API 를 부르면 403 `OWNER_ONLY` 를 돌려줘야 한다(SHALL).

#### Scenario: member 의 직접 호출
- **WHEN** member 가 `PUT /api/teams/{id}` 를 직접 부르면
- **THEN** 403 `OWNER_ONLY` 를 받는다

#### Scenario: member 화면
- **WHEN** member 가 team.html 을 열면
- **THEN** 팀 이름 저장 · 코드 재발급 버튼은 비활성이고 코드 복사는 눌린다
