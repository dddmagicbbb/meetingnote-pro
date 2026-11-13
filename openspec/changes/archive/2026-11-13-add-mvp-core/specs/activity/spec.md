# Spec Delta

## Purpose

팀 안에서 일어난 회의록 등록 · 할 일 배정과 완료 · 댓글 · 합류를 행위자와 시점과 함께 남겨, 리더와 신규 합류자가 팀 흐름과 내 활동을 한눈에 보게 한다.

## ADDED Requirements

### Requirement: 활동 종류 5종
<!-- 근거: 정의서 6 activities.kind -->
활동 kind 는 `meeting_add` · `todo_assign` · `todo_done` · `comment_add` · `member_join` 다섯 값뿐이어야 한다(SHALL). 팀 생성 · 계정 변경 · 삭제는 활동으로 남기지 않는다. 회의록 저장 때 담당자가 붙은 할 일도 `todo_assign` 으로 남긴다.

#### Scenario: 팀 생성은 남지 않음
- **WHEN** 사용자가 팀을 만들고 바로 `GET /api/me/activities` 를 부르면
- **THEN** 200 빈 배열을 받는다

#### Scenario: 회의록 저장
- **WHEN** 담당자가 붙은 할 일 2건이 나온 회의록을 저장하면
- **THEN** `meeting_add` 1건과 `todo_assign` 2건이 생긴다

### Requirement: 팀 활동기록
<!-- 근거: F-01 팀 설정 · team.html (team) -->
`GET /api/teams/{id}/activities` 는 id · kind · actor_name · text · created_at 을 최근순으로 최대 50건 돌려줘야 한다(SHALL). text 는 서버가 만든 완성 문장이고 화면은 그대로 그린다. 다른 팀 id 는 403 `FORBIDDEN` 이다.

#### Scenario: 완성 문장
- **WHEN** 김대리가 회의록 「2차 스프린트 계획 회의」 를 등록한 뒤 팀 활동기록을 부르면
- **THEN** text 가 「김대리 회의록 「2차 스프린트 계획 회의」 등록」 인 항목이 맨 위에 있다

#### Scenario: 50건 상한
- **WHEN** 활동이 60건인 팀의 활동기록을 부르면
- **THEN** 최근 50건만 받는다

### Requirement: 활동 띠색
<!-- 근거: 정의서 7-2 활동기록 띠색 · team.html (team), profile.html (view) -->
화면은 활동 항목의 띠색을 kind 로 골라야 한다(SHALL). `meeting_add`=blue · `todo_assign`=orange · `todo_done`=green · `comment_add` 과 `member_join`=purple 이며 팔레트 5색 밖의 색을 쓰지 않는다.

#### Scenario: 완료 활동
- **WHEN** `todo_done` 활동을 그리면
- **THEN** 좌측 띠가 green 이다

### Requirement: 내 활동기록
<!-- 근거: J-01 내 정보 · J-07 활동 없음 · profile.html (view, no-activity) -->
`GET /api/me/activities` 는 로그인한 사람이 행위자인 활동을 팀 활동기록과 같은 필드 · 정렬 · 상한으로 돌려줘야 한다(SHALL). 없으면 200 빈 배열이고 화면은 활동 없음 안내를 보인다.

#### Scenario: 막 팀을 만든 owner
- **WHEN** 팀만 만들고 아무것도 하지 않은 owner 가 profile.html 을 열면
- **THEN** 200 빈 배열을 받고 활동 없음 안내가 보인다
