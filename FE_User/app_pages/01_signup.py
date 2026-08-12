"""약관 동의와 사용자 정보를 입력받아 회원가입을 처리하는 화면입니다."""

from datetime import date
import streamlit as st

from core.auth import is_logged_in, sign_up
from core.ui import page_header


EMAIL_DOMAINS = [
    "naver.com",
    "gmail.com",
    "daum.net",
    "kakao.com",
    "직접 입력",
]

INTEREST_OPTIONS = [
    "입찰공고",
    "분양주택",
    "임대주택",
    "토지분양",
    "상가공장",
    "장기전세",
    "보상이주",
    "채용공고",
    "주택관리",
]

def is_valid_birth_date(year: int, month: int, day: int) -> bool:
    """선택한 생년월일이 실제로 존재하는 날짜인지 확인합니다."""
    try:
        date(year, month, day)
    except ValueError:
        return False

    return True

def initialize_signup_state():
    """회원가입 화면에서 사용할 약관 동의 상태를 준비합니다."""
    st.session_state.setdefault("signup_agree_all", False)
    st.session_state.setdefault("signup_agree_terms", False)
    st.session_state.setdefault("signup_agree_privacy", False)


def change_all_agreements():
    """전체 동의 상태를 두 개의 필수 약관에 반영합니다."""
    agree_all = st.session_state.signup_agree_all

    st.session_state.signup_agree_terms = agree_all
    st.session_state.signup_agree_privacy = agree_all


def update_all_agreement():
    """개별 약관 상태에 따라 전체 동의 상태를 변경합니다."""
    st.session_state.signup_agree_all = (
        st.session_state.signup_agree_terms
        and st.session_state.signup_agree_privacy
    )


initialize_signup_state()


if is_logged_in():
    st.success("이미 로그인되어 있습니다.")
    st.stop()


page_header("📝", "회원가입", "필수 약관에 동의한 후 회원 정보를 입력해 주세요.")

# 진행 상태를 표시합니다.
required_agreement_count = sum(
    [
        st.session_state.signup_agree_terms,
        st.session_state.signup_agree_privacy,
    ]
)

if required_agreement_count < 2:
    st.progress(50, text="1단계: 약관 동의")
else:
    st.progress(100, text="2단계: 회원 정보 입력")


st.subheader("1. 약관 동의")
st.info("회원가입을 진행하려면 아래 필수 약관에 모두 동의해야 합니다.")

st.checkbox(
    "약관 전체 동의",
    key="signup_agree_all",
    on_change=change_all_agreements,
)

st.divider()

with st.expander("필수 · 회원가입 약관", expanded=True):
    st.write(
        """
        본 서비스의 회원으로 가입하면 서비스 이용 규칙을 준수해야 합니다.

        - 다른 사람의 개인정보를 도용할 수 없습니다.
        - 서비스를 부정한 목적으로 이용할 수 없습니다.
        - 회원 정보는 정확하게 입력해야 합니다.
        """
    )

    st.checkbox(
        "회원가입 약관에 동의합니다.",
        key="signup_agree_terms",
        on_change=update_all_agreement,
    )

with st.expander("필수 · 개인정보 수집 및 이용", expanded=True):
    st.write(
        """
        회원가입과 서비스 제공을 위해 다음 개인정보를 수집합니다.

        - 수집 항목: 이메일, 성함, 휴대번호, 생년월일, 관심분야
        - 이용 목적: 사용자 확인 및 서비스 제공
        - 보유 기간: 회원 탈퇴 시까지

        필수 개인정보 수집에 동의하지 않으면 회원가입을 진행할 수 없습니다.
        """
    )

    st.checkbox(
        "개인정보 수집 및 이용에 동의합니다.",
        key="signup_agree_privacy",
        on_change=update_all_agreement,
    )


st.divider()
st.subheader("2. 회원 정보 입력")

email_col, domain_col = st.columns([2, 1])

with email_col:
    email_id = st.text_input(
        "이메일",
        placeholder="이메일 아이디",
        key="signup_email_id",
    )

with domain_col:
    selected_domain = st.selectbox(
        "이메일 주소",
        EMAIL_DOMAINS,
        key="signup_selected_domain",
    )

    if selected_domain == "직접 입력":
        email_domain = st.text_input(
            "도메인 직접 입력",
            placeholder="example.com",
            key="signup_custom_domain",
            label_visibility="collapsed",
        )
    else:
        email_domain = selected_domain

password = st.text_input(
    "비밀번호",
    type="password",
    placeholder="6자 이상 입력해 주세요.",
    key="signup_password",
)

password_confirm = st.text_input(
    "비밀번호 확인",
    type="password",
    placeholder="비밀번호를 다시 입력해 주세요.",
    key="signup_password_confirm",
)

nickname = st.text_input(
    "성함",
    placeholder="성함을 입력해 주세요.",
    key="signup_nickname",
)

st.write("휴대번호")

phone_col1, phone_col2, phone_col3 = st.columns([1, 2, 2])

with phone_col1:
    phone_first = st.text_input(
        "휴대번호 앞자리",
        value="010",
        disabled=True,
        key="signup_phone_first",
        label_visibility="collapsed",
    )

with phone_col2:
    phone_middle = st.text_input(
        "휴대번호 가운데 번호",
        placeholder="1234",
        max_chars=4,
        key="signup_phone_middle",
        label_visibility="collapsed",
    )

with phone_col3:
    phone_last = st.text_input(
        "휴대번호 끝 번호",
        placeholder="5678",
        max_chars=4,
        key="signup_phone_last",
        label_visibility="collapsed",
    )


birth_col1, birth_col2, birth_col3 = st.columns(3)

with birth_col1:
    birth_year = st.selectbox(
        "생년",
        ["연도"] + list(range(2026, 1899, -1)),
        key="signup_birth_year",
    )

with birth_col2:
    birth_month = st.selectbox(
        "월",
        ["월"] + list(range(1, 13)),
        key="signup_birth_month",
    )

with birth_col3:
    birth_day = st.selectbox(
        "일",
        ["일"] + list(range(1, 32)),
        key="signup_birth_day",
    )


st.write("관심분야")

selected_interest_count = sum(
    st.session_state.get(f"signup_interest_{index}", False)
    for index in range(len(INTEREST_OPTIONS))
)

selected_interests = []
interest_columns = st.columns(3)

for index, interest in enumerate(INTEREST_OPTIONS):
    checkbox_key = f"signup_interest_{index}"
    is_selected = st.session_state.get(checkbox_key, False)

    with interest_columns[index % 3]:
        selected = st.checkbox(
            interest,
            key=checkbox_key,
            disabled=selected_interest_count >= 4 and not is_selected,
        )

    if selected:
        selected_interests.append(interest)

st.caption("※ 관심분야는 최대 4개까지 선택할 수 있습니다.")


st.markdown(
    """
    <style>
    [data-testid="stMain"] a[data-testid="stPageLink-NavLink"] {
        background-color: var(--secondary-background-color, #f0f2f6);
        border-radius: 0.5rem;
        justify-content: center;
        min-height: 2.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

button_col1, button_col2 = st.columns(2)

with button_col1:
    submitted = st.button(
        "회원가입",
        type="primary",
        use_container_width=True,
    )

with button_col2:
    st.page_link(
        "app_pages/00_login.py",
        label="로그인으로 돌아가기",
        use_container_width=True,
    )


if submitted:
    clean_email_id = email_id.strip()
    clean_domain = email_domain.strip()
    clean_nickname = nickname.strip()
    clean_phone_middle = phone_middle.strip()
    clean_phone_last = phone_last.strip()

    if not st.session_state.signup_agree_terms:
        st.error("회원가입 약관에 동의해 주세요.")
    elif not st.session_state.signup_agree_privacy:
        st.error("개인정보 수집 및 이용에 동의해 주세요.")
    elif not clean_email_id:
        st.error("이메일 아이디를 입력해 주세요.")
    elif "@" in clean_email_id:
        st.error("이메일 아이디에는 @ 앞부분만 입력해 주세요.")
    elif not clean_domain:
        st.error("이메일 주소를 입력해 주세요.")
    elif "@" in clean_domain:
        st.error("이메일 주소에는 @를 제외하고 입력해 주세요.")
    elif not password:
        st.error("비밀번호를 입력해 주세요.")
    elif len(password) < 6:
        st.error("비밀번호는 6자 이상 입력해 주세요.")
    elif password != password_confirm:
        st.error("비밀번호가 일치하지 않습니다.")
    elif not clean_nickname:
        st.error("성함을 입력해 주세요.")
    elif not clean_phone_middle or not clean_phone_last:
        st.error("휴대번호를 모두 입력해 주세요.")
    elif not clean_phone_middle.isdigit() or not clean_phone_last.isdigit():
        st.error("휴대번호에는 숫자만 입력해 주세요.")
    elif len(clean_phone_middle) != 4 or len(clean_phone_last) != 4:
        st.error("휴대번호 가운데 번호와 끝 번호를 각각 4자리로 입력해 주세요.")
    elif birth_year == "연도" or birth_month == "월" or birth_day == "일":
        st.error("생년월일을 모두 선택해 주세요.")
    elif not is_valid_birth_date(birth_year, birth_month, birth_day):
        st.error("올바른 생년월일을 선택해 주세요.")
    else:
        full_email = f"{clean_email_id}@{clean_domain}"
        full_phone = f"010-{clean_phone_middle}-{clean_phone_last}"
        birth_date = f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}"

        with st.spinner("회원가입 진행 중..."):
            sign_up(
                full_email,
                password,
                clean_nickname,
                full_phone,
                birth_date,
                selected_interests,
            )
