"""기한 글자 → 날짜 변환표 (modify-todo-due-date design.md)."""
from datetime import date, datetime

import pytest

from backend.duedate import kst_date, parse_due

THU = date(2026, 9, 24)  # 목요일 회의


@pytest.mark.parametrize("text, expected", [
    ("다음 주 금요일", date(2026, 10, 2)),
    ("다음주 금요일까지", date(2026, 10, 2)),
    ("다음 주까지", date(2026, 10, 1)),
    ("다음 주 안", date(2026, 10, 1)),
    ("이번 주 안", date(2026, 9, 25)),
    ("이번 주까지", date(2026, 9, 25)),
    ("금주 중", date(2026, 9, 25)),
    ("이번 주 월요일", date(2026, 9, 21)),
    ("다다음 주 월요일", date(2026, 10, 5)),
    ("오늘", THU), ("오늘 중", THU), ("당일", THU),
    ("내일", date(2026, 9, 25)), ("내일까지", date(2026, 9, 25)),
    ("모레", date(2026, 9, 26)), ("어제", date(2026, 9, 23)),
    ("3일 뒤", date(2026, 9, 27)), ("3일 안", date(2026, 9, 27)), ("10일 이내", date(2026, 10, 4)),
    ("금요일", date(2026, 9, 25)),
    ("목요일", date(2026, 10, 1)),  # 같은 요일이면 다음 주
    ("11월 21일", date(2026, 11, 21)),
    ("9월 1일", date(2027, 9, 1)),  # 지난 날이면 다음 해
    ("15일까지", date(2026, 10, 15)),  # 지난 날이면 다음 달
    ("30일", date(2026, 9, 30)),
    ("다음 달 10일", date(2026, 10, 10)),
    ("이번 달 말까지", date(2026, 9, 30)), ("월말", date(2026, 9, 30)), ("다음 달 말", date(2026, 10, 31)),
    ("2026-10-02", date(2026, 10, 2)), ("10/2", date(2026, 10, 2)),
])
def test_table(text, expected):
    assert parse_due(text, THU) == expected


@pytest.mark.parametrize("text", ["", None, "   ", "다음 분기", "곧", "지난주", "지난달", "미정",
                                  "2월 30일", "다다음 주", "금"])
def test_undecidable_is_none(text):
    assert parse_due(text, THU) is None


def test_month_end_year_wrap():
    assert parse_due("다음 달 말", date(2026, 12, 3)) == date(2027, 1, 31)
    assert parse_due("다음 달 10일", date(2026, 12, 3)) == date(2027, 1, 10)


def test_sunday_meeting_this_week_friday_already_passed():
    # 주는 월요일 시작 - 일요일 회의의 「이번 주 안」 은 그 주(지난) 금요일
    assert parse_due("이번 주 안", date(2026, 9, 27)) == date(2026, 9, 25)
    assert parse_due("다음 주 금요일", date(2026, 9, 27)) == date(2026, 10, 2)


def test_kst_boundary():
    assert kst_date(datetime(2026, 9, 24, 14, 59)) == date(2026, 9, 24)
    assert kst_date(datetime(2026, 9, 24, 15, 0)) == date(2026, 9, 25)  # UTC 15:00 = 한국 다음 날 0시
