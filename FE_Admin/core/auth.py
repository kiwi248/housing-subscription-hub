"""공통 로그인 상태와 인증 동작을 관리합니다."""

import streamlit as st

from clients.admin_client import login_process
from core.api_client import BackendAPIError


def init_state(
    stored_loginout: str = "logout",
    stored_admin_username: str = "",
) -> None:
    st.session_state.setdefault("loginout", stored_loginout)
    st.session_state.setdefault("admin_username", stored_admin_username)


def login(username: str, password: str) -> None:
    try:
        result = login_process(username, password)
        if result.get("success"):
            st.session_state.loginout = "login"
            st.session_state.admin_username = result["data"]["username"]
            st.rerun()
        else:
            st.error(result.get("message", "로그인에 실패했습니다."))
    except BackendAPIError as error:
        st.error(str(error))


def logout() -> None:
    st.session_state.loginout = "logout"
    st.session_state.admin_username = ""


def is_logged_in() -> bool:
    return st.session_state.loginout == "login"
