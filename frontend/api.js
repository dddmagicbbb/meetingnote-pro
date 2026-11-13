// MeetingNote Pro 화면 공통 - API 호출 · 토큰 · 401 처리 · 소속 팀 확인 · 시각 형식
// theme.js 다음에 읽는다. 색 · 클래스는 theme.js 의 UI · STRIPE · LABEL 만 쓴다
(function () {
  const TOKEN_KEY = "mnp_token";
  const EXPIRED_KEY = "mnp_expired";

  class ApiError extends Error {
    constructor(status, code, msg) {
      super(msg || code);
      this.status = status;
      this.code = code;
      this.msg = msg || code;
    }
  }

  const token = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
  const setToken = (t) => { try { localStorage.setItem(TOKEN_KEY, t); } catch {} };
  const clearToken = () => { try { localStorage.removeItem(TOKEN_KEY); } catch {} };

  // 토큰 없음 · 위조 · 만료 = 401 TOKEN_EXPIRED → 토큰을 지우고 로그인 화면 (스토리보드 B-03)
  function expire() {
    clearToken();
    try { sessionStorage.setItem(EXPIRED_KEY, "1"); } catch {}
    location.replace("/login.html");
  }

  async function parse(res) {
    if (res.status === 204) return null;
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = null; }
    if (!res.ok) {
      const code = (data && data.code) || "VALIDATION_ERROR";
      const msg = (data && data.msg) || `요청 실패 (${res.status})`;
      if (res.status === 401 && code === "TOKEN_EXPIRED") expire();
      throw new ApiError(res.status, code, msg);
    }
    return data;
  }

  async function call(method, path, body) {
    const headers = {};
    const t = token();
    if (t) headers.Authorization = `Bearer ${t}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let res;
    try {
      res = await fetch(`/api${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch {
      throw new ApiError(0, "VALIDATION_ERROR", "서버에 연결할 수 없음");
    }
    return parse(res);
  }

  // 녹취 업로드 - 진행률을 받으려고 XHR 사용. onProgress(0~100)
  function upload(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/upload");
      const t = token();
      if (t) xhr.setRequestHeader("Authorization", `Bearer ${t}`);
      xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100)); };
      xhr.onload = () => {
        let data = null;
        try { data = JSON.parse(xhr.responseText); } catch {}
        if (xhr.status >= 200 && xhr.status < 300) return resolve(data);
        const code = (data && data.code) || "VALIDATION_ERROR";
        if (xhr.status === 401 && code === "TOKEN_EXPIRED") expire();
        reject(new ApiError(xhr.status, code, (data && data.msg) || `업로드 실패 (${xhr.status})`));
      };
      xhr.onerror = () => reject(new ApiError(0, "VALIDATION_ERROR", "서버에 연결할 수 없음"));
      const fd = new FormData();
      fd.append("file", file);
      xhr.send(fd);
    });
  }

  // 로그인 · 소속 팀 확인. needTeam 이면 팀이 없을 때 team.html 로 보냄 (F-02)
  async function boot({ needTeam = true } = {}) {
    if (!token()) { location.replace("/login.html"); return new Promise(() => {}); }
    const [user, teams] = await Promise.all([call("GET", "/auth/me"), call("GET", "/teams")]);
    const team = teams[0] || null;
    if (needTeam && !team) { location.replace("/team.html"); return new Promise(() => {}); }
    return { user, team };
  }

  // ── 시각 - 저장은 UTC ISO, 화면은 현지 시간 ──────────────────
  const pad = (n) => String(n).padStart(2, "0");
  const toDate = (iso) => (iso ? new Date(iso) : null);
  function fmtDateTime(iso) {           // 2026-09-24 14:00
    const d = toDate(iso); if (!d) return "";
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  function fmtDate(iso) {               // 2026-09-24
    const d = toDate(iso); if (!d) return "";
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }
  function fmtRelative(iso) {           // 방금 · 오늘 15:02 · 어제 17:40 · 9월 18일
    const d = toDate(iso); if (!d) return "";
    const now = new Date();
    if (now - d < 60 * 1000) return "방금";
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 86400000);
    if (diff === 0) return `오늘 ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    if (diff === 1) return `어제 ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}월 ${d.getDate()}일`;
    return fmtDate(iso);
  }
  // <input type="datetime-local"> 값(현지) → UTC ISO
  function localInputToIso(value) {
    if (!value) return "";
    const d = new Date(value);
    return isNaN(d) ? "" : d.toISOString();
  }
  function isoToLocalInput(iso) {        // 2026-09-24T14:00
    const d = toDate(iso); if (!d) return "";
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  // HTML 이스케이프 - 사용자 입력은 언제나 이걸 거쳐 innerHTML 에 넣는다
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  // 상태 · 활동 · 기한 → 팔레트 색 이름 (theme.js STRIPE / LABEL 키)
  const STATUS_COLOR = { OPEN: "orange", DOING: "blue", DONE: "green" };
  const STATUS_LABEL = { OPEN: "대기", DOING: "진행", DONE: "완료" };
  const KIND_COLOR = { meeting_add: "blue", todo_assign: "orange", todo_done: "green", comment_add: "purple", member_join: "purple" };
  const CARD_CYCLE = ["blue", "green", "orange", "purple", "red"];
  // 기한 지남 - due_date 가 보는 사람의 오늘보다 앞이고 완료가 아님. 날짜가 없으면 판정하지 않음 (modify-todo-due-date)
  const todayStr = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
  const isLate = (todo) => todo.status !== "DONE" && !!todo.due_date && todo.due_date < todayStr();

  window.API = {
    ApiError, call, upload, boot, token, setToken, clearToken,
    get: (p) => call("GET", p), post: (p, b) => call("POST", p, b ?? {}),
    put: (p, b) => call("PUT", p, b ?? {}), del: (p) => call("DELETE", p),
    takeExpiredFlag() {
      try { const v = sessionStorage.getItem(EXPIRED_KEY); sessionStorage.removeItem(EXPIRED_KEY); return !!v; }
      catch { return false; }
    },
    logout: async () => { try { await call("POST", "/auth/logout"); } catch {} clearToken(); location.replace("/login.html"); },
  };
  // 기한 - 「10월 2일 (금)」 + 원래 글자. 날짜가 없으면 글자, 둘 다 없으면 「미정」
  const WD = ["일", "월", "화", "수", "목", "금", "토"];
  function fmtDueDate(ymd) {
    if (!ymd) return "";
    const [y, m, d] = ymd.split("-").map(Number);
    return `${m}월 ${d}일 (${WD[new Date(y, m - 1, d).getDay()]})`;
  }
  function dueLabel(todo) {
    const date = fmtDueDate(todo.due_date);
    const text = String(todo.due_text || "").trim();
    if (date) return { main: date, sub: text };
    return { main: text || "미정", sub: "" };
  }
  window.FMT = { dateTime: fmtDateTime, date: fmtDate, relative: fmtRelative, localInputToIso, isoToLocalInput,
                 dueDate: fmtDueDate, due: dueLabel };
  window.esc = esc;
  window.EMAIL_RE = EMAIL_RE;
  window.PAL = { STATUS_COLOR, STATUS_LABEL, KIND_COLOR, CARD_CYCLE, isLate };
})();
