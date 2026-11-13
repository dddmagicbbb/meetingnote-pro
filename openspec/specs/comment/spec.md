# comment Specification

## Purpose

회의록 상세 화면에서 팀원이 결정사항에 대한 의견을 500자 이내 댓글로 남기고 읽으며, 쓴 사람과 owner 가 지울 수 있게 한다.

## Requirements

### Requirement: 댓글 목록
<!-- 근거: D-01 기본 · D-11 댓글 없음 · detail.html (view, comment-none) -->
`GET /api/meetings/{id}/comments` 는 id · user_id · user_name · content · created_at 에 can_delete 를 더해 created_at 오름차순으로 돌려줘야 한다(SHALL). 없으면 200 빈 배열이고 화면은 「아직 댓글이 없음 - 결정에 의견이 있으면 여기에」 를 보인다.

#### Scenario: 오래된 순
- **WHEN** 댓글 2건이 있는 회의록을 열면
- **THEN** 먼저 쓴 댓글이 위에 있고 머리에 「댓글 2건」 이 보인다

#### Scenario: 댓글 없음
- **WHEN** 댓글이 없는 회의록을 열면
- **THEN** 200 빈 배열을 받고 안내 문구가 보인다

### Requirement: 댓글 등록
<!-- 근거: D-09 댓글 입력 · D-10 댓글 등록 · detail.html (comment, comment-added) -->
`POST /api/meetings/{id}/comments` 는 팀원 누구나 1~500자 내용을 등록하고 201 을 돌려줘야 한다(SHALL). `comment_add` 활동을 남긴다. 화면은 입력 중 「N / 500」 을 보이고, 201 뒤 입력칸을 비우고 목록 끝에 붙인다.

#### Scenario: 등록
- **WHEN** 「기한은 금요일로 확정했으면 함」 을 등록하면
- **THEN** 201 을 받고 입력칸이 비며 댓글 수가 3건으로 늘고 `comment_add` 활동이 생긴다

#### Scenario: 500자 초과
- **WHEN** 501자 댓글을 보내면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 댓글 삭제
<!-- 근거: D-12 댓글 삭제 · detail.html (comment-del) -->
`DELETE /api/comments/{id}` 는 쓴 사람과 owner 만 부를 수 있고 204 를 돌려줘야 한다(SHALL). 화면은 확인 팝업을 먼저 띄우고, can_delete 가 false 면 삭제 버튼을 비활성으로 보인다. 그 밖의 사람이 부르면 403 `FORBIDDEN` 이다.

#### Scenario: owner 가 삭제
- **WHEN** owner 가 박과장의 댓글을 지우면
- **THEN** 204 를 받는다

#### Scenario: 남의 댓글
- **WHEN** member 가 다른 사람 댓글 삭제를 부르면
- **THEN** 403 `FORBIDDEN` 을 받는다
