"""기한 글자 → 날짜 (modify-todo-due-date, design.md 변환표).

같은 글자 · 같은 기준일이면 언제나 같은 날짜. 정해지지 않으면 None.
주는 월요일에 시작한다. 기준일은 한국 날짜(UTC+9, 서머타임 없음).
"""
import calendar
import re
from datetime import date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
WEEKDAYS = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
FRIDAY = 4
TAIL = re.compile(r"(까지|안에|안|중|내|이내|에|전)+$")


def kst_date(dt: datetime | None) -> date:
    """UTC naive(또는 aware) datetime → 한국 날짜. None 이면 오늘."""
    if dt is None:
        return datetime.now(KST).date()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST).date()


def _week_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _safe(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _add_months(base: date, n: int) -> tuple[int, int]:
    m = base.month - 1 + n
    return base.year + m // 12, m % 12 + 1


def _month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def parse_due(text: str | None, base: date) -> date | None:
    if not text:
        return None
    raw = "".join(str(text).split())
    if not raw:
        return None

    # N일 뒤 · 후 · 안 · 이내 → 상대 날짜 (「15일까지」 와 구분하려고 먼저 본다)
    m = re.fullmatch(r"(\d{1,3})일(뒤|후|안|안에|이내|내)(까지|에)?", raw)
    if m:
        return base + timedelta(days=int(m.group(1)))

    s = TAIL.sub("", raw)
    if not s:
        return None

    simple = {"오늘": 0, "당일": 0, "내일": 1, "모레": 2, "어제": -1}
    if s in simple:
        return base + timedelta(days=simple[s])

    # YYYY-MM-DD
    m = re.fullmatch(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})", s)
    if m:
        return _safe(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # (이번|다음|다다음) 주 (X요일)?
    m = re.fullmatch(r"(이번|금|다음|다다음)주(?:([월화수목금토일])요일)?", s)
    if m:
        offset = {"이번": 0, "금": 0, "다음": 1, "다다음": 2}[m.group(1)]
        day = m.group(2)
        if day is None:
            if offset == 0:
                return _week_monday(base) + timedelta(days=FRIDAY)   # 이번 주 안 → 그 주 금요일
            if offset == 1:
                return base + timedelta(days=7)                      # 다음 주까지 → 7일 뒤
            return None                                              # 다다음 주 (요일 없음) → 정하지 않음
        return _week_monday(base) + timedelta(days=7 * offset + WEEKDAYS[day])

    # X요일 (주 표시 없음) → 기준일 다음 날부터 가장 가까운 X요일
    m = re.fullmatch(r"([월화수목금토일])요일", s)
    if m:
        ahead = (WEEKDAYS[m.group(1)] - base.weekday()) % 7 or 7
        return base + timedelta(days=ahead)

    # M월 D일 · M/D
    m = re.fullmatch(r"(\d{1,2})월(\d{1,2})일", s) or re.fullmatch(r"(\d{1,2})/(\d{1,2})", s)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        cand = _safe(base.year, mo, d)
        if cand is None:
            return None
        return cand if cand >= base else _safe(base.year + 1, mo, d)

    # 이번 달 · 다음 달 (말 | D일)
    m = re.fullmatch(r"(이번|다음)달(말|(\d{1,2})일)", s) or re.fullmatch(r"(월)(말)", s)
    if m:
        y, mo = _add_months(base, 1 if m.group(1) == "다음" else 0)
        if m.group(2) == "말":
            return _month_end(y, mo)
        return _safe(y, mo, int(m.group(3)))

    # D일 (달 표시 없음) → 이번 달, 지났으면 다음 달
    m = re.fullmatch(r"(\d{1,2})일", s)
    if m:
        d = int(m.group(1))
        cand = _safe(base.year, base.month, d)
        if cand is not None and cand >= base:
            return cand
        y, mo = _add_months(base, 1)
        return _safe(y, mo, d)

    return None
