"""공통 로그인 상태와 Supabase Auth 인증 동작을 관리합니다."""

import streamlit as st
from supabase import AuthApiError

from core.session_restore import read_tokens, restore_session, should_restore
from core.supabase_client import get_supabase


def init_state(
    stored_loginout: str = "logout",
    stored_user_id: str = "",
    stored_email: str = "",
) -> None:
    """로그인 정보와 토큰을 Streamlit 세션에 기본값으로 준비합니다."""

    st.session_state.setdefault("loginout", stored_loginout)
    st.session_state.setdefault("user_id", stored_user_id)
    st.session_state.setdefault("email", stored_email)
    st.session_state.setdefault("access_token", "")
    st.session_state.setdefault("refresh_token", "")
    # 이번 Streamlit 세션에서 복원을 이미 시도했는지 기억합니다.
    # 화면이 다시 그려질 때마다 Supabase에 다시 묻지 않기 위해서입니다.
    st.session_state.setdefault("session_restore_tried", False)


def restore_login(stored_values: object) -> str:
    """브라우저에 저장해 둔 토큰으로 로그인 상태를 되살립니다.

    새로고침 직후에만 한 번 동작하며, 돌려주는 값은
    "skipped" / "empty" / "restored" / "invalid" 중 하나입니다.
    """

    access_token, refresh_token = read_tokens(stored_values)

    if not should_restore(
        is_logged_in=is_logged_in(),
        already_tried=st.session_state.session_restore_tried,
        has_tokens=bool(access_token and refresh_token),
    ):
        return "skipped"

    # 결과와 상관없이 이번 세션에서는 다시 시도하지 않습니다.
    st.session_state.session_restore_tried = True

    result = restore_session(
        access_token,
        refresh_token,
        get_supabase().auth.set_session,
    )

    if result["status"] != "restored":
        return result["status"]

    st.session_state.loginout = "login"
    st.session_state.user_id = result["user_id"]
    st.session_state.email = result["email"]
    # 세션이 갱신됐을 수 있으므로 돌려받은 토큰으로 바꿔 둡니다.
    st.session_state.access_token = result["access_token"]
    st.session_state.refresh_token = result["refresh_token"]

    return "restored"


def sign_up(
    email: str,
    password: str,
    nickname: str,
    phone: str,
    birth_date: str,
    interests: list[str],
) -> None:
    """Supabase Auth에 사용자를 등록하고 부가정보를 메타데이터로 저장합니다."""

    supabase = get_supabase()

    try:
        result = supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "nickname": nickname,
                        "phone": phone,
                        "birth_date": birth_date,
                        "interests": interests,
                    }
                },
            }
        )
    except AuthApiError as error:
        st.error(f"회원가입에 실패했습니다: {error.message}")
        return

    if result.session is None:
        st.success("회원가입이 완료되었습니다. 이메일 인증 후 로그인해 주세요.")
    else:
        st.success("회원가입이 완료되었습니다. 로그인해 주세요.")


def login(email: str, password: str) -> bool:
    """이메일로 로그인하고 사용자 정보와 인증 토큰을 세션에 저장합니다."""

    supabase = get_supabase()

    try:
        result = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )

    except AuthApiError:
        return False

    st.session_state.loginout = "login"
    st.session_state.user_id = result.user.id
    st.session_state.email = result.user.email or ""
    st.session_state.access_token = result.session.access_token
    st.session_state.refresh_token = result.session.refresh_token
    st.rerun()


def logout() -> None:
    """세션의 로그인 정보와 토큰을 지우고 자동 복원을 차단합니다."""

    st.session_state.loginout = "logout"
    st.session_state.user_id = ""
    st.session_state.email = ""
    st.session_state.access_token = ""
    st.session_state.refresh_token = ""
    # 로그아웃한 뒤 새로고침했을 때 다시 복원되지 않도록 막습니다.
    # 브라우저에 저장된 토큰은 app.py에서 지웁니다.
    st.session_state.session_restore_tried = True


def is_logged_in() -> bool:
    """현재 Streamlit 세션이 로그인 상태인지 반환합니다."""

    return st.session_state.loginout == "login"


def change_password(new_password: str) -> bool:
    """현재 인증 토큰으로 Supabase 세션을 복원한 뒤 비밀번호를 변경합니다."""

    supabase = get_supabase()

    try:
        supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token,
        )

        supabase.auth.update_user(
            {"password": new_password}
        )

    except AuthApiError as error:
        st.error(f"비밀번호 변경에 실패했습니다: {error.message}")
        return False

    return True
