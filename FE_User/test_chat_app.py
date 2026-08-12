"""실제 app.py 구조에 AI 상담 페이지만 추가한 통합 테스트 앱입니다.

기존 app.py는 수정하지 않습니다. 기존 API와 챗봇 API는 모두 8010번의
test_chat_main.py를 사용하도록 이 테스트 프로세스 안에서만 주소를 바꿉니다.
"""

import os

import streamlit as st
st.set_page_config(
    page_title="청약 정보 안내 - AI 통합 테스트",
    page_icon="🏘️",
    layout="wide",
)

from streamlit_session_browser_storage import SessionStorage

import core.api_client as api_client
from core.auth import init_state, is_logged_in, logout, restore_login
from core.session_restore import ACCESS_TOKEN_NAME, REFRESH_TOKEN_NAME, STORAGE_KEY


TEST_BACKEND_URL = "http://127.0.0.1:8010"

# 기존 core/api_client.py 파일은 수정하지 않고 테스트 실행 중인 메모리 값만 바꿉니다.
api_client.BACKEND_URL = TEST_BACKEND_URL
os.environ["CHAT_BACKEND_URL"] = TEST_BACKEND_URL
os.environ["GUIDE_BACKEND_URL"] = TEST_BACKEND_URL


home_page = st.Page("app_pages/02_home.py", title="홈", icon="🏠", default=True)
login_page = st.Page("app_pages/00_login.py", title="로그인", icon="🔐")
signup_page = st.Page("app_pages/01_signup.py", title="회원가입", icon="📝")
listings_page = st.Page("app_pages/03_listings.py", title="청약정보 조회", icon="📋")
mypage_page = st.Page("app_pages/04_mypage.py", title="My Page", icon="⭐")
favorite_page = st.Page("app_pages/05_favorite.py", title="즐겨찾기", icon="❤️")

# 실제 app.py에는 아직 없는 AI 상담 페이지만 추가합니다.
ai_chat_page = st.Page("app_pages/05_ai_chat.py", title="AI 채팅 상담", icon="🤖")
ai_guide_page = st.Page("app_pages/06_ai_guide.py", title="AI 안내원", icon="🧭")


# 실제 앱의 새로고침 복원 구조와 동일하게 모든 페이지를 항상 등록합니다.
pages = [
    home_page,
    login_page,
    signup_page,
    listings_page,
    mypage_page,
    favorite_page,
    ai_chat_page,
    ai_guide_page,
]
navigation = st.navigation(pages, position="hidden")

storage = SessionStorage(key=STORAGE_KEY)
stored_values = storage.getAll()

init_state()

if stored_values is None:
    st.caption("로그인 상태를 확인하는 중입니다...")
    st.stop()

restore_status = restore_login(stored_values)

stored_access_token = (stored_values.get(ACCESS_TOKEN_NAME) or "").strip()
stored_refresh_token = (stored_values.get(REFRESH_TOKEN_NAME) or "").strip()

if is_logged_in():
    if stored_access_token != st.session_state.access_token:
        storage.setItem(
            ACCESS_TOKEN_NAME,
            st.session_state.access_token,
            key="save_access_token",
        )
    if stored_refresh_token != st.session_state.refresh_token:
        storage.setItem(
            REFRESH_TOKEN_NAME,
            st.session_state.refresh_token,
            key="save_refresh_token",
        )
elif stored_access_token or stored_refresh_token:
    storage.deleteAll(key="clear_user_session")

if restore_status == "invalid":
    st.warning("로그인 정보가 만료되었습니다. 다시 로그인해 주세요.")

with st.sidebar:
    st.title("메뉴")
    st.caption("AI 통합 테스트")
    st.page_link(home_page)
    st.page_link(listings_page)

    if is_logged_in():
        st.page_link(favorite_page)
        st.page_link(mypage_page)
        st.page_link(ai_chat_page)
        st.page_link(ai_guide_page)
        st.divider()
        st.caption(f"{st.session_state.email} 님")
        st.button("LOGOUT", on_click=logout, use_container_width=True)
    else:
        st.page_link(login_page)


navigation.run()
