# amount_format.py
"""금액을 읽기 쉬운 문구로 바꿉니다.

입력칸에는 숫자만 들어가서 0이 몇 개인지 세기 어렵습니다.
그래서 옆에 쉼표를 넣은 금액과 만·억 단위 읽기를 함께 보여 줍니다.

Streamlit에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

EOK = 100_000_000
MAN = 10_000


def to_won(value: object) -> int | None:
    """입력값을 원 단위 정수로 바꿉니다. 숫자가 아니면 None입니다."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def format_won(value: object) -> str:
    """1026000을 "1,026,000원"으로 바꿉니다."""

    won = to_won(value)
    if won is None:
        return "-"

    return f"{won:,}원"


def to_korean_amount(value: object) -> str:
    """10260000을 "1,026만 원"처럼 읽어 줍니다.

    억과 만 단위로 끊어 읽어, 0의 개수를 세지 않아도 크기를 알 수 있게 합니다.
    """

    won = to_won(value)
    if won is None:
        return "-"

    if won == 0:
        return "0원"

    negative = won < 0
    left = abs(won)

    parts = []
    if left >= EOK:
        parts.append(f"{left // EOK:,}억")
        left %= EOK
    if left >= MAN:
        parts.append(f"{left // MAN:,}만")
        left %= MAN
    if left:
        parts.append(f"{left:,}")

    # 마지막이 억/만으로 끝나면 "1,026만 원"처럼 띄어 씁니다.
    text = " ".join(parts)
    text = text + "원" if text[-1].isdigit() else text + " 원"
    return f"-{text}" if negative else text


def describe_amount(value: object) -> str:
    """입력칸 아래에 보여 줄 안내 문구를 만듭니다.

    예: "1,026,000원 (102만 6,000원)"
    만 단위가 없어 읽기가 같아지면 한 번만 보여 줍니다.
    """

    won = to_won(value)
    if won is None:
        return "-"

    with_commas = format_won(won)
    korean = to_korean_amount(won)
    if korean in (with_commas, "-"):
        return with_commas

    return f"{with_commas} ({korean})"
