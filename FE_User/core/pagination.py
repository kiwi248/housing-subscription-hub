# pagination.py
"""청약정보 목록을 페이지로 나눠 보여줄 때 쓰는 함수들입니다.

서버가 이미 마감이 가까운 순으로 정렬해서 목록 전체를 돌려주므로,
그 순서를 그대로 지키기 위해 화면에서 잘라 보여 줍니다.
서버에 페이지를 맡기면 마감된 공고를 뒤로 보내는 순서가 흐트러집니다.

지금 보고 있는 페이지 번호는 주소창에 둡니다.
새로고침해도 보던 페이지가 유지되게 하려는 것입니다.

Streamlit에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

# 한 페이지에 보여줄 공고 수입니다. 관리자 화면과 같은 값을 씁니다.
PAGE_SIZE = 10


def _first_value(raw: object) -> str | None:
    """주소에 같은 이름이 여러 번 들어와도 첫 값만 씁니다."""
    if isinstance(raw, (list, tuple)):
        return str(raw[0]) if raw else None
    if raw is None:
        return None
    return str(raw)


def parse_page(raw: object) -> int:
    """주소의 page 값을 페이지 번호로 바꿉니다.

    비어 있거나 숫자가 아니거나 1보다 작으면 1페이지로 봅니다.
    """
    value = _first_value(raw)
    if value is None:
        return 1

    try:
        page = int(value.strip())
    except ValueError:
        return 1

    return page if page >= 1 else 1


def total_pages(total_count: int, page_size: int = PAGE_SIZE) -> int:
    """전체 건수로 마지막 페이지 번호를 셉니다. 최소 1페이지입니다."""
    if page_size < 1:
        page_size = 1
    if total_count < 1:
        return 1

    return -(-total_count // page_size)  # 올림 나눗셈


def clamp_page(page: int, total_count: int, page_size: int = PAGE_SIZE) -> int:
    """마지막 페이지를 넘는 번호가 들어오면 마지막 페이지로 맞춥니다.

    공고가 지워져 페이지가 줄어든 경우에 빈 화면이 나오지 않게 합니다.
    """
    last = total_pages(total_count, page_size)
    if page < 1:
        return 1

    return min(page, last)


def slice_page(items: object, page: int, page_size: int = PAGE_SIZE) -> list:
    """그 페이지에 보여줄 만큼만 잘라 냅니다.

    원래 목록은 바꾸지 않고, 서버가 준 순서를 그대로 지킵니다.
    """
    if not isinstance(items, list):
        return []

    if page_size < 1:
        page_size = 1

    safe_page = clamp_page(page, len(items), page_size)
    start = (safe_page - 1) * page_size
    return items[start : start + page_size]


def build_params(page: int) -> dict[str, str]:
    """주소창에 넣을 값을 만듭니다. 페이지 번호만 담습니다."""
    return {"page": str(max(1, page))}
