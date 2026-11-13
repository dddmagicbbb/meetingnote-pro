# Spec Delta

## MODIFIED Requirements

### Requirement: 결정사항과 할 일 저장 모양
<!-- 근거: 정의서 7-2 decisions 저장 · 7-3 저장 모양 · modify-todo-due-date (지시) -->
결정사항은 줄바꿈으로 구분한 TEXT 한 칸으로 저장하고 decision_count 는 빈 줄을 뺀 줄 수여야 한다(SHALL). 할 일은 「내용 | 담당자 | 기한」 으로 뽑아 todos 에 OPEN 상태로 넣는다. 담당자는 팀 멤버 이름과 공백 · 존칭(님)을 무시하고 대조하고, 맞는 멤버가 없으면 미정(null)이다. due_text 는 들은 글자 그대로 두고, due_date 는 회의 날짜를 기준일로 바꿔 넣는다(todo 의 기한 날짜 변환 규칙).

#### Scenario: 담당자 대조
- **WHEN** 본문에 「김대리님이 다음 주 금요일까지 목록 화면 하겠습니다」 가 있고 팀에 `김대리` 가 있으면
- **THEN** 할 일의 담당자는 김대리, due_text 는 「다음 주 금요일」 이다

#### Scenario: 없는 사람
- **WHEN** 멤버에 없는 이름이 담당자로 나오면
- **THEN** 할 일의 담당자는 미정이다

#### Scenario: 회의 날짜 기준 기한
- **GIVEN** 회의 시각이 2026-09-24 14:00 (한국 시각)
- **WHEN** 뽑힌 할 일의 기한 글자가 「다음 주 금요일」 이면
- **THEN** 저장된 할 일의 due_date 는 2026-10-02, due_text 는 「다음 주 금요일」 이다
