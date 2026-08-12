# dday.py
"""신청 종료일까지 며칠 남았는지 보여 주는 문구를 만듭니다.

마감이 임박한 공고를 한눈에 알아보게 하려고 목록에 함께 적습니다.
날짜 계산만 하므로 Streamlit 없이도 확인할 수 있습니다.
"""

from datetime import date


def days_left(end_date: object, today: date | None = None) -> int | None:
    """오늘부터 신청 종료일까지 남은 날수를 셉니다.

    종료일이 오늘이면 0, 이미 지났으면 음수입니다.
    날짜로 읽을 수 없으면 None을 돌려줍니다.
    """

    if today is None:
        today = date.today()

    if isinstance(end_date, date):
        parsed = end_date
    else:
        try:
            parsed = date.fromisoformat(str(end_date))
        except (TypeError, ValueError):
            return None

    return (parsed - today).days


def dday_label(end_date: object, today: date | None = None) -> str | None:
    """남은 날수를 "D-3", "D-DAY", "마감" 같은 문구로 바꿉니다.

    날짜를 읽을 수 없으면 None을 돌려줍니다. 이때는 아무것도 보여 주지 않습니다.
    """

    remaining = days_left(end_date, today)
    if remaining is None:
        return None

    if remaining > 0:
        return f"D-{remaining}"

    if remaining == 0:
        return "D-DAY"

    return "마감"


def is_closed(end_date: object, today: date | None = None) -> bool:
    """신청이 이미 끝났는지 알려 줍니다. 날짜를 모르면 끝나지 않은 것으로 봅니다."""

    remaining = days_left(end_date, today)
    if remaining is None:
        return False

    return remaining < 0


def dim_if_closed(text: object, closed: bool) -> str:
    """신청이 끝난 공고의 글자를 흐린 회색으로 바꿉니다.

    Streamlit의 색 표기는 대괄호를 쓰기 때문에, 글 안에 닫는 대괄호가 있으면
    표기가 깨집니다. 공고 제목에 "[테스트데이터]" 같은 값이 들어올 수 있어
    대괄호를 비슷한 모양의 다른 글자로 바꿔 두고 색을 입힙니다.
    """

    body = "" if text is None else str(text)

    if not closed:
        return body

    safe = body.replace("[", "［").replace("]", "］")
    return f":gray[{safe}]"
