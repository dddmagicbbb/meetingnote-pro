# auth Specification

## Purpose

팀 회의록 앱에 들어오는 관문으로, 이메일과 비밀번호로 가입하고 로그인해 24시간짜리 토큰을 받으며 내 이름과 비밀번호를 고칠 수 있게 한다.

## Requirements

### Requirement: 회원가입
<!-- 근거: B-05 회원가입 초기 · login.html (signup) -->
시스템은 `POST /api/auth/signup` 으로 이메일 · 비밀번호 · 이름을 받아 계정을 만들고 201 과 `{token, user}` 를 돌려줘야 한다(SHALL). 비밀번호는 bcrypt 해시로만 저장한다. signup 은 초대코드를 받지 않는다. `user` 는 id · name · email · role 을 담고, 소속 팀이 없으면 role 은 null 이다.

#### Scenario: 가입 성공
- **WHEN** 처음 쓰는 이메일 `hong@example.com`, 8자 이상 비밀번호, 이름 `홍길동` 으로 가입하면
- **THEN** 201 과 `{token, user}` 를 받고, DB 에는 평문이 아닌 bcrypt 해시가 저장된다

#### Scenario: 초대코드를 같이 넣은 가입
- **WHEN** 가입 화면에서 초대코드 칸에 `MN-7K2D` 를 넣고 가입하면
- **THEN** 화면은 signup 201 을 받은 뒤 `POST /api/teams/join` 을 따로 호출한다

### Requirement: 가입 입력 검증
<!-- 근거: B-06 입력 중 · B-08 에러 - 형식 · B-10 에러 - 약한 비밀번호 · login.html (signup-typing, signup-err-format, signup-err-weak) -->
화면은 제출 전에는 오류를 띄우지 않고, 제출 때 이메일 형식과 비밀번호 8자 이상을 먼저 검사해 어긋나면 서버를 부르지 않아야 한다(SHALL). 서버도 같은 검사를 해 400 `EMAIL_INVALID` 또는 400 `PASSWORD_TOO_WEAK` 를 돌려준다.

#### Scenario: 입력 중에는 오류 없음
- **WHEN** 이메일 칸에 `hong@exam` 까지만 친 상태로 아직 제출하지 않으면
- **THEN** 오류 문구가 보이지 않는다

#### Scenario: 형식 오류
- **WHEN** 이메일 `hong@example` 로 가입하기를 누르면
- **THEN** 화면이 「이메일 형식이 올바르지 않음」 을 띄우고 서버를 호출하지 않는다

#### Scenario: 약한 비밀번호를 서버로 직접 보냄
- **WHEN** 5자 비밀번호로 `POST /api/auth/signup` 을 직접 호출하면
- **THEN** 400 `{code:"PASSWORD_TOO_WEAK", msg}` 를 받는다

### Requirement: 이메일 중복 거부
<!-- 근거: B-09 에러 - 중복 · login.html (signup-err-dup) -->
이미 가입된 이메일로 가입하면 시스템은 409 `EMAIL_DUPLICATED` 를 돌려줘야 한다(SHALL).

#### Scenario: 중복 이메일
- **WHEN** 이미 있는 `kim@example.com` 으로 가입하면
- **THEN** 409 `EMAIL_DUPLICATED` 를 받고 화면은 이메일 칸 아래 「이미 가입된 이메일」 을 띄운다

### Requirement: 가입 뒤 초대코드 실패
<!-- 근거: B-11 에러 - 초대코드 · login.html (signup-err-invite) -->
가입은 성공했는데 뒤이은 합류가 404 `INVITE_NOT_FOUND` 로 실패하면, 화면은 계정을 그대로 두고 team.html 로 보내야 한다(SHALL).

#### Scenario: 없는 초대코드
- **WHEN** 초대코드 `MN-0000` 으로 가입하면
- **THEN** signup 은 201, join 은 404 이고 화면은 team.html 로 이동한다

### Requirement: 로그인
<!-- 근거: B-01 로그인 · B-04 로그인 성공 · login.html (login, login-ok) -->
시스템은 `POST /api/auth/login` 으로 이메일과 비밀번호를 확인해 200 `{token, user}` 를 돌려줘야 한다(SHALL). 화면은 토큰을 localStorage 에 저장하고 `GET /api/teams` 로 소속을 확인해 팀이 있으면 meetings.html, 없으면 team.html 로 보낸다.

#### Scenario: 팀이 있는 사용자
- **WHEN** 팀 소속인 `kim@example.com` 이 맞는 비밀번호로 로그인하면
- **THEN** 200 `{token, user}` 를 받고 meetings.html 로 이동한다

#### Scenario: 팀이 없는 사용자
- **WHEN** 소속 팀이 없는 계정이 로그인하면
- **THEN** team.html 로 이동한다

### Requirement: 로그인 실패 메시지 통일
<!-- 근거: B-02 로그인 실패 · login.html (login-fail) -->
이메일이 없거나 비밀번호가 틀리면 시스템은 둘을 구분하지 않고 401 `INVALID_CREDENTIALS` 하나로 돌려줘야 한다(SHALL).

#### Scenario: 틀린 비밀번호
- **WHEN** 있는 이메일에 틀린 비밀번호로 로그인하면
- **THEN** 401 `INVALID_CREDENTIALS` 를 받고 화면은 「이메일 또는 비밀번호가 올바르지 않음」 을 띄운다

#### Scenario: 없는 이메일
- **WHEN** 가입되지 않은 이메일로 로그인하면
- **THEN** 틀린 비밀번호와 같은 401 `INVALID_CREDENTIALS` 를 받는다

### Requirement: 토큰 인증과 만료
<!-- 근거: B-03 세션 만료 · login.html (session-expired), 정의서 7-2 -->
`/api/auth/signup` · `/api/auth/login` 을 뺀 모든 API 는 `Authorization: Bearer` 토큰을 요구해야 한다(SHALL). 토큰은 발급 뒤 24시간 유효하고 갱신하지 않는다. 토큰이 없거나 위조됐거나 만료되면 401 `TOKEN_EXPIRED` 를 돌려주고, 화면은 토큰을 지운 뒤 login.html 로 보낸다.

#### Scenario: 만료 토큰
- **WHEN** 발급 24시간이 지난 토큰으로 `GET /api/teams/{id}/meetings` 를 부르면
- **THEN** 401 `TOKEN_EXPIRED` 를 받고 화면은 토큰을 지우고 login.html 에 「다시 로그인 필요 - 24시간 지남」 을 띄운다

#### Scenario: 토큰 없음
- **WHEN** Authorization 헤더 없이 보호된 API 를 부르면
- **THEN** 401 `TOKEN_EXPIRED` 를 받는다

### Requirement: 처리 중 버튼 잠금
<!-- 근거: B-07 처리 중 · login.html (signup-loading) -->
가입 · 로그인 요청이 끝나기 전까지 화면은 제출 버튼을 잠그고 문구를 「가입 중...」 · 「로그인 중...」 으로 바꿔야 한다(SHALL).

#### Scenario: 두 번 누름 방지
- **WHEN** 가입하기를 누르고 응답을 기다리는 동안 다시 누르면
- **THEN** 요청은 한 번만 나간다

### Requirement: 내 정보 조회
<!-- 근거: J-01 내 정보 · profile.html (view) -->
시스템은 `GET /api/auth/me` 로 id · name · email · role 을 돌려줘야 한다(SHALL). 화면에서 이메일은 고칠 수 없다.

#### Scenario: owner 배지
- **WHEN** 팀 owner 가 profile.html 을 열면
- **THEN** role `owner` 를 받고 owner 배지가 보인다

### Requirement: 이름과 비밀번호 변경
<!-- 근거: J-02 이름 변경 · J-05 저장 중 · J-06 저장 완료 · profile.html (edit-name, saving, saved) -->
시스템은 `PUT /api/auth/me` 로 로그인한 본인의 이름 또는 새 비밀번호를 바꿔야 한다(SHALL). 이름만 보내면 비밀번호는 그대로다. 현재 비밀번호는 받지 않는다. 계정 변경은 활동기록에 남기지 않는다.

#### Scenario: 이름만 변경
- **WHEN** 이름만 `김과장` 으로 보내면
- **THEN** 200 을 받고 이름만 바뀌며 기존 비밀번호로 계속 로그인된다

#### Scenario: 활동기록에 남지 않음
- **WHEN** 이름을 바꾼 뒤 `GET /api/me/activities` 를 부르면
- **THEN** 계정 변경 항목이 없다

### Requirement: 비밀번호 변경 검증
<!-- 근거: J-03 비밀번호 불일치 · J-04 약한 비밀번호 · profile.html (pw-mismatch, pw-weak) -->
화면은 새 비밀번호와 확인 두 칸이 다르면 서버로 보내지 않아야 한다(SHALL). 8자 미만이면 서버는 400 `PASSWORD_TOO_WEAK` 를 돌려준다.

#### Scenario: 확인 불일치
- **WHEN** 새 비밀번호와 확인 칸을 다르게 넣고 저장하면
- **THEN** 화면이 불일치를 띄우고 요청을 보내지 않는다

#### Scenario: 8자 미만
- **WHEN** 7자 비밀번호로 `PUT /api/auth/me` 를 부르면
- **THEN** 400 `PASSWORD_TOO_WEAK` 를 받는다

### Requirement: 로그아웃
<!-- 근거: 정의서 7-2 로그아웃 · profile.html -->
`POST /api/auth/logout` 은 서버 블랙리스트 없이 200 만 돌려줘야 한다(SHALL). 화면은 토큰을 지우고 login.html 로 보낸다.

#### Scenario: 로그아웃
- **WHEN** profile.html 에서 로그아웃을 누르면
- **THEN** 200 을 받고 localStorage 의 토큰이 지워진 채 login.html 로 이동한다
