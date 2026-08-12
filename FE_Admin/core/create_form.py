# create_form.py
"""청약정보 등록 폼의 입력값을 다루는 함수들입니다.

비슷한 공고를 이어서 여러 건 넣는 일이 많아, 등록한 뒤에도 입력값을 지우지 않고
그대로 둡니다. 아예 새 공고를 넣을 때는 `입력 초기화` 버튼으로 한 번에 비웁니다.

초기화는 값을 지우는 것만으로는 되지 않습니다. 폼 입력칸은 브라우저 쪽에도
입력값을 들고 있어서, 서버의 session_state만 지우면 화면에는 그대로 남습니다.
그래서 폼과 입력칸 이름에 번호를 붙여 두고, 초기화할 때 번호를 올려
아예 새 입력칸을 만들어 버립니다.

Streamlit에 기대지 않는 함수만 두어 테스트하기 쉽습니다.
"""

# 등록 폼 입력칸의 이름입니다. 초기화할 때 이 이름들만 지웁니다.
CREATE_FORM_FIELDS = (
    "title",
    "housing-name",
    "area-sqm",
    "recruitment-count",
    "location",
    "detail-address",
    "deposit",
    "monthly-rent",
    "start-date",
    "end-date",
    "description",
    "image",
    "source-url",
)

# 지금 폼이 몇 번째인지 기억하는 이름입니다.
NONCE_KEY = "create-form-nonce"


def current_nonce(state) -> int:
    """지금 폼 번호를 읽습니다. 없으면 0부터 시작합니다."""

    try:
        return int(state.get(NONCE_KEY, 0))
    except (TypeError, ValueError):
        return 0


def field_key(field: str, nonce: int) -> str:
    """입력칸 이름을 만듭니다. 폼 번호가 바뀌면 이름도 바뀝니다."""

    return f"create-{field}-{nonce}"


def form_key(nonce: int) -> str:
    """폼 자체의 이름입니다."""

    return f"listing_create_form_{nonce}"


def reset_form_state(state) -> int:
    """등록 폼 입력값을 지우고 새 폼 번호를 돌려줍니다.

    값만 지우면 브라우저에 남은 입력이 그대로 보이므로, 폼 번호를 올려
    입력칸을 새로 만들게 합니다.
    등록 폼과 상관없는 값(로그인 정보 등)은 건드리지 않습니다.
    """

    nonce = current_nonce(state)

    for field in CREATE_FORM_FIELDS:
        state.pop(field_key(field, nonce), None)

    new_nonce = nonce + 1
    state[NONCE_KEY] = new_nonce
    return new_nonce
