# listing_sort.py
"""관리자 청약정보 목록의 정렬 기준 이름을 다룹니다.

실제 정렬은 백엔드가 합니다. 여기서는 화면에 보여 줄 이름과
백엔드에 보낼 값을 짝지어 두기만 합니다.

정렬을 화면에서 하지 않는 이유가 있습니다.
관리자 목록은 한 번에 한 페이지(10건)만 받아 가는데,
받은 10건만 다시 늘어놓으면 전체 기준의 순서가 아니기 때문입니다.

사용자 화면과 같은 내용이지만 앱마다 모듈이 따로 있어 각자 둡니다.

Streamlit에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

# 화면에 보여 줄 이름과 백엔드에 보낼 값입니다. 순서가 곧 화면 순서입니다.
SORT_OPTIONS = (
    ("등록 최신순", "created_desc"),
    ("신청 종료일 빠른순", "end_date_asc"),
    ("면적 넓은 순", "area_desc"),
    ("면적 좁은 순", "area_asc"),
    ("모집인원 많은 순", "recruitment_desc"),
    ("모집인원 적은 순", "recruitment_asc"),
    ("보증금 높은 순", "deposit_desc"),
    ("보증금 낮은 순", "deposit_asc"),
    ("월세 높은순", "rent_desc"),
    ("월세 낮은순", "rent_asc"),
)

# 관리자 화면은 방금 등록한 공고를 먼저 확인하는 일이 많아 등록 최신순이 기본입니다.
DEFAULT_LABEL = "등록 최신순"

_KEYS = dict(SORT_OPTIONS)


def sort_labels() -> tuple[str, ...]:
    """선택 상자에 넣을 이름 목록입니다."""

    return tuple(label for label, _ in SORT_OPTIONS)


def default_index() -> int:
    """선택 상자가 처음에 가리킬 자리입니다."""

    return sort_labels().index(DEFAULT_LABEL)


def sort_key(label: object) -> str:
    """화면에서 고른 이름을 백엔드에 보낼 값으로 바꿉니다.

    모르는 이름이 들어오면 기본 기준으로 돌려보냅니다.
    """

    return _KEYS.get(label, _KEYS[DEFAULT_LABEL])


def sort_label(key: object) -> str:
    """백엔드에 보낸 값을 다시 화면 이름으로 바꿉니다."""

    for label, value in SORT_OPTIONS:
        if value == key:
            return label
    return DEFAULT_LABEL
