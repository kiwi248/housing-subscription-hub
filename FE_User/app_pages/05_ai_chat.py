"""로그인 사용자를 위한 AI 채팅 상담 화면입니다."""

import streamlit as st

from clients.chat_client import (
    ChatAPIError,
    delete_chat_history,
    delete_chat_summary,
    get_chat_profile,
    get_chat_summaries,
    save_chat_summary,
    send_chat_message,
)
from core.auth import is_logged_in
from core.ui import page_header


MESSAGE_KEY = "ai_chat_messages"
OWNER_KEY = "ai_chat_owner_id"
NICKNAME_KEY = "ai_chat_nickname"
END_CONFIRM_KEY = "ai_chat_end_confirm"
FLASH_KEY = "ai_chat_flash"
ERROR_KEY = "ai_chat_error"
SUMMARY_SELECTED_KEY = "ai_chat_selected_summary"
SUMMARY_DELETE_CONFIRM_KEY = "ai_chat_summary_delete_confirm"
SUMMARY_RESET_KEY = "ai_chat_summary_reset"


def clear_current_chat() -> None:
    st.session_state[MESSAGE_KEY] = []
    st.session_state[END_CONFIRM_KEY] = False


def initialize_chat_state() -> None:
    current_user_id = st.session_state.user_id
    if st.session_state.get(OWNER_KEY) != current_user_id:
        st.session_state[OWNER_KEY] = current_user_id
        st.session_state[MESSAGE_KEY] = []
        st.session_state[NICKNAME_KEY] = "회원"
        st.session_state[END_CONFIRM_KEY] = False
        st.session_state[SUMMARY_SELECTED_KEY] = None
        st.session_state[SUMMARY_DELETE_CONFIRM_KEY] = None
        st.session_state[SUMMARY_RESET_KEY] = False
    else:
        st.session_state.setdefault(MESSAGE_KEY, [])
        st.session_state.setdefault(NICKNAME_KEY, "회원")
        st.session_state.setdefault(END_CONFIRM_KEY, False)
        st.session_state.setdefault(SUMMARY_SELECTED_KEY, None)
        st.session_state.setdefault(SUMMARY_DELETE_CONFIRM_KEY, None)
        st.session_state.setdefault(SUMMARY_RESET_KEY, False)


def load_nickname() -> None:
    if st.session_state.get(NICKNAME_KEY) != "회원":
        return
    response = get_chat_profile(st.session_state.access_token)
    profile = response.get("data") or {}
    st.session_state[NICKNAME_KEY] = profile.get("nickname") or "회원"


def show_saved_summaries() -> None:
    # Streamlit 위젯이 생성되기 전에 이전 실행에서 예약한 초기화를 처리합니다.
    if st.session_state.get(SUMMARY_RESET_KEY):
        st.session_state[SUMMARY_SELECTED_KEY] = None
        st.session_state[SUMMARY_RESET_KEY] = False

    with st.container(border=True):
        st.markdown("#### 저장된 상담")
        try:
            response = get_chat_summaries(st.session_state.access_token)
            summaries = response.get("data") or []
        except ChatAPIError as error:
            st.warning(f"저장된 상담을 불러오지 못했습니다: {error}")
            return

        if not summaries:
            st.caption("저장된 상담 요약이 없습니다.")
            return

        summary_by_id = {str(item.get("id")): item for item in summaries}
        select_col, delete_col = st.columns([9, 1], vertical_alignment="bottom")
        with select_col:
            selected_id = st.selectbox(
                "확인할 상담",
                options=list(summary_by_id),
                index=None,
                placeholder="상담을 선택하세요",
                key=SUMMARY_SELECTED_KEY,
                format_func=lambda item_id: (
                    f"{summary_by_id[item_id].get('title') or '제목 없는 상담'} · "
                    f"{str(summary_by_id[item_id].get('created_at') or '').replace('T', ' ')[:19]}"
                ),
            )
        with delete_col:
            if st.button(
                "✕",
                key="delete_selected_summary",
                help="선택한 상담 삭제",
                disabled=not selected_id,
                use_container_width=True,
            ):
                st.session_state[SUMMARY_DELETE_CONFIRM_KEY] = selected_id
                st.rerun()

        delete_target = st.session_state.get(SUMMARY_DELETE_CONFIRM_KEY)
        if delete_target and delete_target in summary_by_id:
            st.warning("선택한 상담 요약을 삭제할까요? 삭제한 내용은 복구할 수 없습니다.")
            cancel_col, confirm_col = st.columns(2)
            with cancel_col:
                if st.button("삭제 취소", use_container_width=True):
                    st.session_state[SUMMARY_DELETE_CONFIRM_KEY] = None
                    st.rerun()
            with confirm_col:
                if st.button("삭제 확인", type="primary", use_container_width=True):
                    try:
                        response = delete_chat_summary(
                            delete_target,
                            st.session_state.access_token,
                        )
                        st.session_state[SUMMARY_DELETE_CONFIRM_KEY] = None
                        st.session_state[SUMMARY_RESET_KEY] = True
                        st.session_state[FLASH_KEY] = response.get(
                            "message", "저장된 상담을 삭제했습니다."
                        )
                        st.rerun()
                    except ChatAPIError as error:
                        st.error(str(error))

        if selected_id:
            item = summary_by_id[selected_id]
            st.write(item.get("summary") or "요약 내용이 없습니다.")
            st.caption(
                f"메시지 {item.get('message_count', 0)}개 · model={item.get('model', '-') }"
            )


page_header("💬", "AI 채팅 상담", "청약 자격이나 신청 방법을 편하게 물어보세요.")

if not is_logged_in():
    st.warning("AI 채팅 상담을 이용하려면 로그인이 필요합니다.")
    st.stop()

if not st.session_state.access_token:
    st.warning("로그인 토큰을 확인할 수 없습니다. 다시 로그인해 주세요.")
    st.stop()

initialize_chat_state()

try:
    load_nickname()
except ChatAPIError as error:
    st.warning(f"닉네임을 불러오지 못했습니다: {error}")

if flash_message := st.session_state.pop(FLASH_KEY, None):
    st.success(flash_message)
if error_message := st.session_state.pop(ERROR_KEY, None):
    st.error(error_message)

st.subheader(f"{st.session_state[NICKNAME_KEY]}님, 무엇을 도와드릴까요?")
st.caption("현재 대화는 Redis에 1시간 동안 임시 보관됩니다. 대화 저장 시 요약본으로 저장됩니다.")
st.warning("AI 답변은 검증된 데이터가 아닐 수 있습니다. 중요한 내용은 공식 공고와 담당 기관에서 확인해 주세요.")

show_saved_summaries()
st.divider()

for chat_message in st.session_state[MESSAGE_KEY]:
    with st.chat_message(chat_message["role"]):
        st.write(chat_message["content"])

prompt = st.chat_input("상담 질문을 입력하세요")
if prompt:
    try:
        with st.spinner("AI 상담 답변을 생성하고 있습니다..."):
            response = send_chat_message(
                question=prompt,
                access_token=st.session_state.access_token,
            )
        data = response.get("data") or {}
        st.session_state[MESSAGE_KEY].extend(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": data.get("answer") or "답변이 비어 있습니다."},
            ]
        )
    except ChatAPIError as error:
        st.session_state[ERROR_KEY] = str(error)
    st.rerun()

end_col, save_col = st.columns(2)

with end_col:
    if st.button("대화 종료", use_container_width=True):
        st.session_state[END_CONFIRM_KEY] = True

with save_col:
    save_clicked = st.button(
        "대화 저장",
        type="primary",
        use_container_width=True,
        disabled=len(st.session_state[MESSAGE_KEY]) < 2,
    )

if st.session_state[END_CONFIRM_KEY]:
    st.warning("현재 상담 내용을 모두 삭제하시겠습니까? 저장하지 않은 대화는 복구할 수 없습니다.")
    cancel_col, confirm_col = st.columns(2)
    with cancel_col:
        if st.button("취소", use_container_width=True):
            st.session_state[END_CONFIRM_KEY] = False
            st.rerun()
    with confirm_col:
        if st.button("종료하기", type="primary", use_container_width=True):
            try:
                delete_chat_history(st.session_state.access_token)
                clear_current_chat()
                st.rerun()
            except ChatAPIError as error:
                st.error(str(error))

if save_clicked:
    try:
        with st.spinner("상담 내용을 핵심만 요약하고 있습니다..."):
            response = save_chat_summary(st.session_state.access_token)
        clear_current_chat()
        st.session_state[FLASH_KEY] = response.get(
            "message", "상담 요약 미리보기를 저장했습니다."
        )
        st.rerun()
    except ChatAPIError as error:
        st.error(str(error))
