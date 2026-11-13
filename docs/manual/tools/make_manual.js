// MeetingNote Pro 사용자 매뉴얼 (docx) 생성
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, AlignmentType,
  HeadingLevel, LevelFormat, WidthType, ShadingType, BorderStyle, PageBreak, Footer, PageNumber,
  TableOfContents, Header,
} = require("docx");

const ROOT = process.argv[2];                       // D:/meetingnote-pro
const IMG = path.join(ROOT, "docs/manual/images");
const OUT = path.join(ROOT, "docs/manual/MeetingNote_Pro_사용자매뉴얼.docx");
const URL = "https://meetingnote-pro-amber.vercel.app";
const FONT = "Malgun Gothic";
const CONTENT_W = 9026;                              // A4 1인치 여백 본문 폭 (DXA)

// ── 도우미 ─────────────────────────────────────────────
const t = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const p = (runs, o = {}) => new Paragraph({ children: (Array.isArray(runs) ? runs : [typeof runs === "string" ? t(runs) : runs]), spacing: { after: 120, line: 300 }, ...o });
const h1 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [t(s)] });
const h2 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(s)] });
const bullet = (runs) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60, line: 288 }, children: Array.isArray(runs) ? runs : [t(runs)] });
const step = (runs, ref) => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 288 }, children: Array.isArray(runs) ? runs : [t(runs)] });
const b = (s) => t(s, { bold: true });
const code = (s) => new TextRun({ text: s, font: "Consolas", size: 19, color: "1565B0" });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

function pngSize(file) {
  const buf = fs.readFileSync(file);
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20), buf };
}
// 그림 + 설명. maxW/maxH 는 픽셀(96dpi) 기준
function figure(name, caption, maxW = 600, maxH = 760) {
  const { w, h, buf } = pngSize(path.join(IMG, name + ".png"));
  const scale = Math.min(maxW / w, maxH / h);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(w * scale), height: Math.round(h * scale) },
        altText: { title: caption, description: caption, name } })],
    }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
      children: [t(caption, { size: 18, color: "55595F", italics: true })] }),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "E4E6E9" };
const borders = { top: border, bottom: border, left: border, right: border };
function table(head, rows, widths) {
  const cell = (text, i, isHead) => new TableCell({
    borders, width: { size: widths[i], type: WidthType.DXA },
    shading: isHead ? { fill: "F4F5F6", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [t(String(text), { size: 19, bold: isHead })] })],
  });
  return new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: head.map((x, i) => cell(x, i, true)) }),
           ...rows.map(r => new TableRow({ children: r.map((x, i) => cell(x, i, false)) }))],
  });
}
const gap = () => new Paragraph({ spacing: { after: 120 }, children: [] });
const note = (label, text, color = "1565B0") => new Paragraph({
  spacing: { before: 60, after: 160, line: 288 },
  border: { left: { style: BorderStyle.SINGLE, size: 24, color, space: 8 } },
  indent: { left: 240 },
  children: [t(label + "  ", { bold: true, color }), t(text)],
});

// ── 본문 ──────────────────────────────────────────────
const nums = [];
let numSeq = 0;
const steps = (items) => { const ref = "steps" + (++numSeq); nums.push(ref); return items.map(x => step(x, ref)); };

const children = [
  // 표지
  new Paragraph({ spacing: { before: 2400, after: 200 }, alignment: AlignmentType.LEFT, children: [t("MEETINGNOTE PRO", { size: 22, bold: true, color: "8B9097", characterSpacing: 60 })] }),
  new Paragraph({ heading: HeadingLevel.TITLE, children: [t("사용자 매뉴얼")] }),
  p([t("녹취를 올리면 요약 · 결정사항 · 할 일로 정리되는 팀 회의록", { size: 24, color: "55595F" })], { spacing: { after: 600 } }),
  table(["항목", "내용"], [
    ["접속 주소", URL],
    ["대상", "MeetingNote Pro 를 쓰는 팀 리더 · 팀원 · 신규 합류자"],
    ["버전", "1.0 (add-mvp-core · fix-meeting-save-hint · modify-todo-due-date)"],
    ["작성일", "2026-11-13"],
    ["화면 캡처", "운영 사이트에서 Playwright 로 자동 촬영 (라이트 테마)"],
  ], [2200, CONTENT_W - 2200]),

  new Paragraph({ pageBreakBefore: true, spacing: { after: 160 }, children: [t("목차", { size: 34, bold: true })] }),
  new TableOfContents("목차", { hyperlink: true, headingStyleRange: "1-2" }),
  p([t("목차가 비어 보이면 Word 에서 목차를 누르고 「필드 업데이트」 를 고르십시오.", { size: 18, color: "8B9097" })]),

  // 1
  h1("1. 시작하기"),
  p("MeetingNote Pro 는 로그인한 팀이 함께 쓰는 회의록입니다. 회의 녹음 파일을 올리면 본문을 받아쓰고, 저장할 때 요약 · 결정사항 · 할 일 세 갈래로 나눕니다. 할 일은 칸반에서 담당자와 기한으로 추적하고, 댓글과 활동기록이 남습니다."),
  h2("1.1 접속과 환경"),
  bullet([b("주소: "), t(URL)]),
  bullet("브라우저: 최신 Chrome 또는 Safari. 휴대폰(가로 360px 이상)에서도 쓸 수 있습니다"),
  bullet("화면 오른쪽 위 달 / 해 아이콘으로 라이트 · 다크 테마를 바꿉니다. 고른 테마는 그 브라우저에 기억됩니다"),
  bullet("로그인은 24시간 유지됩니다. 지나면 로그인 화면으로 돌아가 「다시 로그인 필요」 가 뜹니다"),
  h2("1.2 화면 구성"),
  table(["메뉴", "하는 일"], [
    ["회의록", "회의록 목록 · 검색 · 새 회의록 올리기"],
    ["할 일", "대기 · 진행 · 완료 칸반, 담당자 배정, 기한 확인"],
    ["팀", "팀 이름 · 초대코드 · 멤버 · 팀 활동기록"],
    ["내 정보", "이름 · 비밀번호 변경, 내 할 일, 내 활동, 로그아웃"],
  ], [2200, CONTENT_W - 2200]),
  gap(),
  h2("1.3 체험용 계정"),
  p("운영 사이트에 체험용 계정이 준비되어 있습니다. 비밀번호는 모두 password1 입니다. 실제 업무에 쓰기 전에 지우거나 비밀번호를 바꾸십시오."),
  table(["이메일", "이름", "역할"], [
    ["kim@example.com", "김대리", "기획팀 owner"],
    ["park@example.com", "박과장", "기획팀 member"],
    ["lee@example.com", "이주임", "기획팀 member"],
    ["choi@example.com", "최선임", "소속 팀 없음 (합류 체험용)"],
  ], [3800, 2000, CONTENT_W - 5800]),

  // 2
  h1("2. 로그인과 회원가입"),
  h2("2.1 로그인"),
  ...steps(["이메일과 비밀번호를 넣고 「로그인」 을 누릅니다", "소속 팀이 있으면 회의록 화면으로, 없으면 팀 화면으로 이동합니다"]),
  ...figure("01_login", "그림 1. 로그인 화면"),
  note("참고", "이메일이 없거나 비밀번호가 틀리면 둘 다 「이메일 또는 비밀번호가 올바르지 않음」 한 문구로 알립니다."),
  h2("2.2 회원가입"),
  ...steps([
    "로그인 화면 아래 「회원가입」 을 누릅니다",
    "이메일 · 비밀번호(8자 이상) · 이름을 넣습니다",
    "팀장에게 받은 초대코드가 있으면 넣습니다. 비워 두면 가입 뒤 팀을 새로 만듭니다",
    "「가입하기」 를 누르면 가입과 동시에 팀에 합류합니다",
  ]),
  ...figure("02_signup", "그림 2. 회원가입 - 초대코드를 넣으면 가입 뒤 바로 합류"),
  table(["안내 문구", "이유와 해결"], [
    ["이메일 형식이 올바르지 않음", "user@example.com 꼴로 다시 넣습니다"],
    ["비밀번호는 8자 이상", "8자 이상으로 넣습니다"],
    ["이미 가입된 이메일", "로그인하거나 다른 이메일을 씁니다"],
    ["없는 초대코드", "가입은 됩니다. 팀 화면에서 올바른 코드로 다시 합류합니다"],
  ], [3400, CONTENT_W - 3400]),

  // 3
  h1("3. 팀 만들기와 합류"),
  p("한 사람은 한 팀에만 속합니다. 팀이 없으면 회의록 · 할 일 화면에 들어갈 수 없고 팀 화면이 먼저 열립니다."),
  ...figure("03_team_onboard", "그림 3. 소속 팀 없음 - 팀 만들기 또는 초대코드로 합류"),
  bullet([b("팀 만들기: "), t("팀 이름을 넣고 「만들기」. 만든 사람이 owner 가 되고 초대코드가 발급됩니다")]),
  bullet([b("초대코드로 합류: "), t("owner 에게 받은 MN-XXXX 코드를 넣고 「합류」. 합류하면 회의록 화면으로 이동합니다")]),
  bullet([b("정원: "), t("팀당 6명까지입니다. 6명인 팀에 합류하면 「팀 정원이 찼음」 이 뜹니다")]),

  // 4
  h1("4. 회의록 올리기"),
  h2("4.1 회의록 목록"),
  p("회의록 화면은 회의 시각 최신순 카드 목록입니다. 카드에는 제목 · 시각 · 참석자 · 요약 · 결정 수 · 할 일 완료 수가 나옵니다."),
  bullet("검색 칸은 제목과 참석자만 찾습니다. 본문 내용은 검색되지 않습니다"),
  bullet("날짜 두 칸으로 회의 기간을 거릅니다"),
  ...figure("04_meetings_empty", "그림 4. 회의록이 없을 때 - 「새 회의록」 으로 시작"),
  h2("4.2 녹음 파일로 새 회의록 만들기"),
  ...steps([
    "「새 회의록」 을 누릅니다. 회의 시각은 지금 시각으로 채워져 있습니다",
    "녹음 파일(mp3 · wav)을 점선 칸에 끌어 놓거나 눌러서 고릅니다",
    "업로드 % 다음 「받아쓰는 중」 이 지나면 본문 칸이 자동으로 채워집니다 (보통 10~20초)",
    "제목을 넣습니다. 제목 · 회의 시각 · 본문 세 칸이 차야 「정리하기」 가 켜집니다",
    "「정리하기」 를 누르면 요약 · 결정사항 · 할 일로 나눠 저장합니다 (보통 2~15초)",
  ]),
  ...figure("05_new_meeting", "그림 5. 새 회의록 팝업 - 빠진 필수 칸이 버튼 옆에 표시됨"),
  ...figure("06_uploading", "그림 6. 업로드 · 받아쓰기 진행"),
  ...figure("07_transcribed_title_required", "그림 7. 받아쓰기 완료 - 제목이 비어 「제목 필수」, 커서가 제목 칸으로 이동"),
  note("팁", "「정리하기」 가 회색이면 버튼 왼쪽 안내 줄에 빠진 칸 이름이 나옵니다. 녹음만 올리면 제목이 비어 있으니 제목부터 넣으십시오."),
  ...figure("08_ready_to_save", "그림 8. 세 칸이 모두 차서 「정리하기」 가 켜진 상태"),
  ...figure("09_meetings_list", "그림 9. 저장 완료 - 목록 맨 위에 새 회의록"),
  note("녹음 없이", "녹음 파일 없이 메모를 본문 칸에 붙여 넣어도 똑같이 정리됩니다.", "007A42"),
  h2("4.3 올릴 때 알아 둘 것"),
  table(["상황", "화면", "해결"], [
    ["mp3 · wav 가 아닌 파일", "mp3 또는 wav 만 올릴 수 있음", "녹음을 mp3 · wav 로 바꿔 올립니다 (확장자가 아니라 파일 내용으로 판정)"],
    ["받아쓰기 실패", "받아쓰기 실패 - 본문 칸에 메모를 직접 붙여넣기", "잠시 뒤 다시 올리거나 메모를 붙여 넣고 저장합니다"],
    ["정리 실패", "정리 실패 - 본문은 그대로", "본문이 남아 있으니 「정리하기」 를 다시 누릅니다"],
    ["파일이 4.5MB 초과", "업로드 실패", "운영 서버 한도입니다. 녹음을 나누거나 압축(mp3)해 올립니다"],
  ], [2200, 3100, CONTENT_W - 5300]),

  // 5
  h1("5. 회의록 상세"),
  p("목록에서 카드를 누르면 상세 화면이 열립니다. 요약 · 결정사항 · 할 일 3단을 먼저 보이고, 받아쓴 본문은 「본문 펼치기」 로 엽니다."),
  ...figure("10_detail", "그림 10. 회의록 상세 - 요약 · 결정사항 · 할 일 · 댓글", 600, 820),
  bullet("결정사항은 합의가 끝난 것만 뽑습니다. 없으면 「결정사항 없음」 으로 비워 둡니다"),
  bullet("할 일은 담당자와 기한이 드러난 것만 뽑습니다. 이름이 팀 멤버와 맞으면 담당자가 자동으로 정해지고, 없으면 「미정」 입니다"),
  bullet("기한 칸에는 들은 글자 그대로가 들어가고, 옆에 회의 날짜 기준으로 계산한 날짜가 나옵니다 (6.3 참고)"),
  h2("5.1 담당자 · 상태 바꾸기"),
  p("담당자 배지를 누르면 팀 멤버 목록이 열립니다. 상태 배지로 대기 · 진행 · 완료를 고르며, 되돌리기도 됩니다."),
  ...figure("11_detail_assign", "그림 11. 담당자 고르기"),
  h2("5.2 댓글"),
  p("결정에 의견이 있으면 아래 입력칸에 500자 이내로 남깁니다. 오래된 순으로 쌓이고 팀 활동기록에도 남습니다."),
  ...figure("12_detail_comment", "그림 12. 본문 펼침과 댓글 입력", 600, 820),
  h2("5.3 권한"),
  table(["동작", "할 수 있는 사람"], [
    ["회의록 수정 · 삭제", "올린 사람, owner (다른 멤버는 버튼이 꺼짐)"],
    ["댓글 쓰기", "팀원 누구나"],
    ["댓글 삭제", "쓴 사람, owner"],
    ["할 일 담당자 · 상태 · 기한 변경", "팀원 누구나"],
    ["할 일 삭제", "만든 사람, 담당자, owner"],
  ], [3800, CONTENT_W - 3800]),
  note("주의", "회의록을 지우면 딸린 할 일과 댓글도 함께 지워지며 되돌릴 수 없습니다.", "C21620"),

  // 6
  h1("6. 할 일 칸반"),
  p("할 일 화면은 대기 · 진행 · 완료 세 칸입니다. 「내 할 일」 은 나에게 배정된 것만, 「전체」 는 팀 전체를 보입니다."),
  ...figure("13_kanban_all", "그림 13. 칸반 전체 - 기한이 지난 카드는 붉은 띠"),
  h2("6.1 옮기기"),
  bullet([b("넓은 화면: "), t("카드를 끌어 다른 칸에 놓습니다. 저장에 실패하면 카드가 원래 칸으로 돌아갑니다")]),
  bullet([b("휴대폰 · 좁은 화면: "), t("카드를 누르면 대기 · 진행 · 완료 버튼이 뜹니다")]),
  ...figure("15_kanban_mobile_pick", "그림 14. 휴대폰 화면에서 눌러서 칸 고르기", 300, 620),
  h2("6.2 새 할 일 · 담당자 필터"),
  p("「새 할 일」 로 회의록 없이 직접 등록합니다. 출처는 「직접 등록」 으로 표시됩니다. 「담당자 전체」 목록으로 특정 사람의 카드만 볼 수 있습니다."),
  ...figure("14_kanban_new", "그림 15. 새 할 일 직접 등록"),
  h2("6.3 기한 날짜와 기한 지남"),
  p("기한은 받아쓴 글자(예: 「다음 주 금요일」)를 그대로 남기고, 회의 날짜를 기준으로 날짜를 계산해 함께 보여 줍니다. 직접 등록한 할 일은 등록한 날이 기준입니다. 한 주는 월요일에 시작합니다."),
  table(["기한 글자", "날짜 (회의 2026-09-24 목요일 기준)"], [
    ["다음 주 금요일", "회의 다음 주의 그 금요일 → 10월 2일"],
    ["다음 주까지", "7일 뒤 → 10월 1일"],
    ["이번 주 안 · 이번 주까지", "그 주 금요일 → 9월 25일"],
    ["내일 · 모레 · 3일 뒤", "9월 25일 · 9월 26일 · 9월 27일"],
    ["11월 21일 · 다음 달 10일 · 월말", "11월 21일 · 10월 10일 · 9월 30일"],
    ["다음 분기 · 곧 · 지난주", "날짜를 정하지 않음 (글자만 표시)"],
  ], [3400, CONTENT_W - 3400]),
  gap(),
  bullet("날짜가 오늘보다 앞이고 완료가 아니면 카드에 붉은 띠가 생깁니다. 오늘이 기한인 카드는 붉지 않습니다"),
  bullet("날짜를 정하지 못한 기한은 붉은 띠 판정에서 빠집니다"),
  bullet("기한 배지를 눌러 글자를 고치면 처음 기준일로 날짜를 다시 계산합니다"),

  // 7
  h1("7. 팀 설정"),
  ...figure("16_team", "그림 16. 팀 설정 - 팀 이름 · 초대코드 · 멤버 · 활동기록", 600, 820),
  table(["기능", "owner", "member"], [
    ["팀 이름 변경", "가능", "버튼 꺼짐"],
    ["초대코드 복사", "가능", "가능"],
    ["초대코드 재발급 (옛 코드 폐기)", "가능", "버튼 꺼짐"],
    ["멤버 · 활동기록 보기", "가능", "가능"],
  ], [4400, 2300, CONTENT_W - 6700]),
  gap(),
  p("활동기록은 최근 50건을 보이며 띠 색으로 종류를 구분합니다: 회의록 등록 파랑 · 할 일 배정 주황 · 할 일 완료 초록 · 댓글과 합류 보라. 팀 생성과 계정 변경은 남지 않습니다."),

  // 8
  h1("8. 내 정보"),
  ...figure("17_profile", "그림 17. 내 정보 - 이름 · 비밀번호, 내 할 일, 내 활동", 600, 820),
  bullet("이메일은 바꿀 수 없습니다"),
  bullet("이름만 바꾸면 비밀번호는 그대로입니다"),
  bullet("비밀번호는 새 비밀번호와 확인 두 칸만 넣습니다. 두 칸이 다르거나 8자 미만이면 저장되지 않습니다"),
  bullet("「로그아웃」 을 누르면 이 브라우저의 로그인 정보가 지워집니다"),

  // 9
  h1("9. 문제 해결"),
  table(["증상", "원인과 해결"], [
    ["「정리하기」 가 눌리지 않음", "제목 · 회의 시각 · 본문 중 빈 칸이 있습니다. 버튼 옆 「OO 필수」 를 보고 채웁니다"],
    ["회의록 · 할 일 메뉴로 못 들어감", "소속 팀이 없습니다. 팀 화면에서 만들거나 합류합니다"],
    ["갑자기 로그인 화면으로 돌아감", "로그인 24시간이 지났습니다. 다시 로그인합니다"],
    ["수정 · 삭제 버튼이 꺼져 있음", "올린 사람 또는 owner 만 할 수 있습니다 (5.3 권한)"],
    ["팀 합류가 안 됨", "없는 코드(재발급된 옛 코드 포함)이거나 정원 6명이 찼거나 이미 다른 팀 소속입니다"],
    ["기한에 날짜가 안 나옴", "「다음 분기」 처럼 날짜 하나로 정할 수 없는 글자입니다. 기한 배지를 눌러 「다음 주 금요일」 · 「11월 21일」 처럼 고칩니다"],
    ["큰 녹음 파일이 안 올라감", "운영 서버 요청 한도 4.5MB 입니다. 나누거나 mp3 로 압축합니다"],
  ], [3000, CONTENT_W - 3000]),

  // 부록
  h1("부록 A. 개발자용 API 화면"),
  p([t("API 를 직접 호출해 볼 수 있는 Swagger UI 가 "), code(URL + "/docs"), t(" 에 있습니다. 로그인 응답의 token 을 오른쪽 위 「Authorize」 에 넣으면 보호된 API 도 호출됩니다. 오류 응답은 언제나 {code, msg} 꼴입니다.")]),
  ...figure("18_swagger", "그림 18. Swagger UI - API 27개를 6묶음으로"),
  h1("부록 B. 사용자 테스트 결과"),
  p("2026-11-13, 운영 사이트에서 Playwright(Chrome)로 스토리보드 상태를 실제 조작해 확인했습니다. 실제 녹음 파일(회의_녹음.wav, 4.2MB) 업로드와 Gemini 받아쓰기 · 정리를 포함합니다."),
  table(["화면", "확인 항목", "결과"], [
    ["로그인 · 회원가입", "10", "10 통과"],
    ["회의록 목록 · 새 회의록", "21", "21 통과"],
    ["회의록 상세", "20", "20 통과"],
    ["할 일 칸반", "25", "25 통과"],
    ["팀 설정", "13", "13 통과"],
    ["내 정보", "13", "13 통과"],
    ["합계", "102", "102 통과"],
  ], [4000, 2400, CONTENT_W - 6400]),
  gap(),
  p([t("첫 실행에서 2건(저장 직후 목록 갱신 · 빈 칸반 표시)이 운영 응답 지연으로 화면이 다시 그려지기 전에 검사되어 실패했고, 그려질 때까지 기다리도록 테스트를 고친 뒤 통과했습니다. 기능 결함은 없었습니다.", { size: 19, color: "55595F" })]),
];

const doc = new Document({
  creator: "MeetingNote Pro",
  title: "MeetingNote Pro 사용자 매뉴얼",
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 56, bold: true, color: "141414" }, paragraph: { spacing: { before: 0, after: 160 }, keepNext: true } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 34, bold: true, color: "141414" },
        paragraph: { spacing: { before: 240, after: 160 }, keepNext: true, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "4CA0E5", space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 26, bold: true, color: "1565B0" },
        paragraph: { spacing: { before: 240, after: 100 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
      ...nums.map(ref => ({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 540, hanging: 320 } } } }] })),
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [t("MeetingNote Pro 사용자 매뉴얼", { size: 16, color: "8B9097" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [t("", { size: 16 }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "8B9097" })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("written", OUT, buf.length); });
