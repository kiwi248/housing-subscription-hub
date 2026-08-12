"""로그인 사용자의 프로필과 비밀번호를 조회·수정하는 화면입니다."""

import streamlit as st

from clients.profile_client import get_profile, update_profile
from core.api_client import BackendAPIError
from core.auth import change_password, is_logged_in
from core.ui import page_header

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

page_header("🗂️", "회원정보수정", "닉네임과 비밀번호, 관심분야를 관리하세요.")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

try:
    profile_response = get_profile(st.session_state.user_id)
    profile = profile_response.get("data") or {}

    saved_name = profile.get("nickname") or ""
    saved_phone = profile.get("phone") or ""
    saved_interests = profile.get("interests") or []

    with st.form("profile_form"):
        st.text_input(
            "ID",
            value=st.session_state.email,
            disabled=True,
        )

        name = st.text_input(
            "성함",
            value=saved_name,
        )

        phone = st.text_input(
            "휴대번호",
            value=saved_phone,
            placeholder="010-1234-5678",
        )

        st.write("관심 분야")

        interests = []
        interest_columns = st.columns(3)

        for index, option in enumerate(INTEREST_OPTIONS):
            with interest_columns[index % 3]:
                checked = st.checkbox(
                    option,
                    value=option in saved_interests,
                )

                if checked:
                    interests.append(option)

        new_password = st.text_input(
            "새 비밀번호",
            type="password",
            placeholder="6자 이상 입력해 주세요.",
            help="변경하지 않으려면 비워 두세요.",
        )

        password_confirm = st.text_input(
            "새 비밀번호 확인",
            type="password",
            placeholder="새 비밀번호를 다시 입력해 주세요.",
        )

        submitted = st.form_submit_button(
            "수정 완료",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        name = name.strip()
        phone = phone.strip()

        profile_changed = (
            name != saved_name
            or phone != saved_phone
            or interests != saved_interests
        )
        password_changed = bool(new_password or password_confirm)

        if not profile_changed and not password_changed:
            st.warning("변경된 내용이 없습니다.")

        elif profile_changed and not name:
            st.warning("성함을 입력해 주세요.")

        elif profile_changed and not phone:
            st.warning("휴대번호를 입력해 주세요.")

        elif profile_changed and not interests:
            st.warning("관심 분야를 하나 이상 선택해 주세요.")

        elif password_changed and len(new_password) < 6:
            st.warning("비밀번호는 6자 이상 입력해 주세요.")

        elif password_changed and new_password != password_confirm:
            st.warning("비밀번호가 일치하지 않습니다.")

        else:
            messages = []

            if profile_changed:
                update_profile(
                    st.session_state.user_id,
                    name,
                    phone,
                    interests,
                )
                messages.append("프로필")

            if password_changed:
                if not change_password(new_password):
                    st.stop()

                messages.append("비밀번호")

            changed_items = "과 ".join(messages)
            st.session_state.mypage_message = f"{changed_items}를 수정했습니다."
            st.rerun()
    if message := st.session_state.pop("mypage_message", None):
        st.info(message)
except BackendAPIError as error:
    st.error(str(error))
