# Proposal

## Why

로그인한 팀이 함께 쓰는 회의록 앱이 없어, 녹취에서 나온 결정사항과 할 일이 회의 뒤 흩어진다. 프로그램정의서 · 스토리보드 · 퍼블리싱이 모두 확정됐으므로 1회차 change 하나로 기능 6종(인증 · 팀 · 회의록 · 할 일 · 댓글 · 활동기록)을 한 번에 구현한다.

## What Changes

- FastAPI 백엔드 신설 - `/api/` 아래 엔드포인트 27개 (Auth 5 · Team 6 · Meeting 6 · Todo 5 · Comment 3 · Activity 2), DB 7테이블 (users · teams · memberships · meetings · todos · comments · activities)
- 녹취 업로드(mp3 · wav) → Gemini 받아쓰기 → 저장 때 요약 · 결정사항 · 할 일 세 갈래 구분
- Vanilla JS 프론트엔드 신설 - `publish/` 의 화면 6종(login · meetings · detail · todos · team · profile)을 `frontend/` 로 옮겨 API 에 연결. 스토리보드 상태 63종을 그대로 재현
- 디자인은 `publish/` 가 정답. 화면 뼈대는 publish 마크업을 클래스까지 그대로 쓰고, JS 로 그리는 반복 요소는 `theme.js` 의 `UI` · `STRIPE` · `LABEL` 이름으로 가져다 씀. `theme.js` 는 고치지 않음
- Swagger UI(`/docs`) 를 켜서 브라우저에서 API 를 직접 호출해 볼 수 있게 함
- 루트 `.env` · `.env.example` (GEMINI_API_KEY · GEMINI_MODEL 두 줄)
- pytest 백엔드 테스트 (Gemini 호출은 가짜 응답으로 대체)

범위 밖 (Out of Scope):
- 실시간 녹음 (파일 업로드만), 화자 자동 구분, 캘린더 · 메일 등 외부 연동, owner / member 외 권한 등급, 푸시 알림
- Vercel + Neon 배포 - 다음 change 로 넘김. 단 `DATABASE_URL` 이 있으면 Postgres 를 쓰는 한 줄 분기는 이번에 넣어 둠
- 업로드 크기 상한 - 정의서대로 20MB 초과는 Files API 로 처리하고 따로 거부하지 않음
- `publish/index.html` · `publish/components.html` 은 퍼블리싱 확인용이라 옮기지 않음

## Capabilities

### New Capabilities

- `auth`: 회원가입 · 로그인 · JWT 발급 · 내 정보 조회와 수정 · 로그아웃 (login.html · profile.html)
- `team`: 팀 생성 · 초대코드 발급과 재발급 · 합류 · 멤버 목록 · 팀 이름 변경, owner / member 권한 (team.html)
- `meeting`: 녹취 업로드와 받아쓰기, 세 갈래 구분, 회의록 CRUD · 검색 · 기간 조회 (meetings.html · detail.html)
- `todo`: 할 일 칸반 3열(OPEN · DOING · DONE), 직접 등록 · 상태 변경 · 담당자 배정 · 삭제, 내 할 일 (todos.html · detail.html · profile.html)
- `comment`: 회의록 댓글 등록 · 목록 · 삭제 (detail.html)
- `activity`: 팀 활동기록과 내 활동기록 (team.html · profile.html)

### Modified Capabilities

(없음 - 첫 change)

## Impact

- 새 폴더: `backend/` (FastAPI · SQLAlchemy · pytest), `frontend/` (화면 6종 + `theme.js` 복사본)
- 새 파일: 루트 `.env` · `.env.example` · `.gitignore` · `requirements.txt`
- 외부 의존: Gemini API (`GEMINI_API_KEY`, 모델은 `GEMINI_MODEL`), Tailwind CDN
- 로컬 실행: `uvicorn backend.main:app --reload` → http://127.0.0.1:8000 (화면) · http://127.0.0.1:8000/docs (Swagger UI)
