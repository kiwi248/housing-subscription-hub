"""유저용 Streamlit 멀티페이지 앱입니다.

브라우저를 새로고침하면 st.session_state가 비기 때문에, 로그인 세션을
브라우저 Session Storage에 둔 토큰으로 다시 되살립니다.

주의: 토큰은 브라우저 개발자 도구에서 볼 수 있습니다. 탭을 닫으면 사라지도록
Local Storage가 아니라 Session Storage를 사용합니다. 비밀번호는 저장하지 않습니다.
"""

import streamlit as st

# set_page_config()는 이 앱에서 가장 먼저 실행되는 Streamlit 명령이어야 합니다.
# 그래서 다른 import보다 위에 둡니다. 보통은 import를 파일 맨 위에 모으지만
# 여기서는 순서가 곧 동작이라 예외로 둡니다.
#
# core.auth를 먼저 불러오면 core.api_client와 core.supabase_client가 딸려 오는데,
# 그 모듈들은 읽히는 순간 st.secrets를 확인합니다.
# 로컬에 secrets.toml이 없으면 Streamlit 버전에 따라 이때
# "No secrets found" 안내를 화면에 그려 버립니다.
# 그러면 아래 set_page_config()가 첫 번째 명령이 아니게 되어
# StreamlitSetPageConfigMustBeFirstCommandError로 앱이 뜨지 않습니다.
st.set_page_config(
    page_title="청약 정보 안내",
    page_icon="🏘️",
    layout="wide",
)

from streamlit_session_browser_storage import SessionStorage  # noqa: E402

from core.auth import (  # noqa: E402
    init_state,
    is_logged_in,
    logout,
    restore_login,
)
from core.session_restore import (  # noqa: E402
    ACCESS_TOKEN_NAME,
    REFRESH_TOKEN_NAME,
    STORAGE_KEY,
)


home_page = st.Page("app_pages/02_home.py", title="홈", icon="🏠", default=True)
login_page = st.Page("app_pages/00_login.py", title="로그인", icon="🔐")
signup_page = st.Page("app_pages/01_signup.py", title="회원가입", icon="📝")
listings_page = st.Page("app_pages/03_listings.py", title="청약정보 조회", icon="📋")
location_page = st.Page("app_pages/06_location.py",title="주변생활권 분석",icon="🚇")
mypage_page = st.Page("app_pages/04_mypage.py", title="My Page", icon="⭐")
favorite_page = st.Page("app_pages/05_favorite.py", title="즐겨찾기", icon="❤️")
ai_chat_page = st.Page("app_pages/05_ai_chat.py", title="AI 상담", icon="💬")
ai_guide_page = st.Page("app_pages/06_ai_guide.py", title="AI 안내원", icon="🤖")


# 페이지는 로그인 여부와 상관없이 모두 등록합니다.
# 로그인 상태에 따라 목록을 바꾸면, 새로고침 직후에는 아직 로그인 상태를 모르기 때문에
# 지금 보고 있던 주소가 목록에서 빠져 "Page not found"가 뜰 수 있습니다.
# 각 화면이 이미 로그인 여부를 스스로 확인하므로 등록은 항상 합니다.
pages = [
    home_page,
    login_page,
    signup_page,
    listings_page,
    location_page,
    mypage_page,
    favorite_page,
    ai_chat_page,
    ai_guide_page,
]

# 경로 등록을 먼저 합니다. 아래에서 잠시 멈추더라도 보고 있던 주소가 유지됩니다.
navigation = st.navigation(pages, position="hidden")

# 탭을 닫으면 사라지는 Session Storage를 씁니다. Local Storage는 쓰지 않습니다.
storage = SessionStorage(key=STORAGE_KEY)
stored_values = storage.getAll()

init_state()

# 첫 실행에서는 브라우저에서 값이 아직 오지 않아 None이 옵니다.
# 이때 로그아웃으로 단정하면 로그인 상태인데도 로그인 화면이 잠깐 스쳐 지나갑니다.
# 값이 도착할 때까지 기다립니다. 값이 도착하면 컴포넌트가 화면을 다시 실행시킵니다.
if stored_values is None:
    st.caption("로그인 상태를 확인하는 중입니다...")
    st.stop()

# 로그인 여부를 판단하기 전에 먼저 되살립니다.
# 한 세션에서 한 번만 시도하므로 요청이 되풀이되지 않습니다.
restore_status = restore_login(stored_values)

stored_access_token = (stored_values.get(ACCESS_TOKEN_NAME) or "").strip()
stored_refresh_token = (stored_values.get(REFRESH_TOKEN_NAME) or "").strip()

if is_logged_in():
    # 로그인했거나 세션이 갱신됐으면 브라우저 쪽 토큰도 맞춰 둡니다.
    # 값이 이미 같으면 쓰지 않으므로 저장이 되풀이되지 않습니다.
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
    # 로그아웃했거나(logout) 되살릴 수 없는 토큰이면(invalid) 브라우저에서도 지웁니다.
    # 이렇게 해야 로그아웃 후 새로고침했을 때 다시 로그인 상태가 되지 않습니다.
    storage.deleteAll(key="clear_user_session")

if restore_status == "invalid":
    st.warning("로그인 정보가 만료되었습니다. 다시 로그인해 주세요.")

with st.sidebar:
    st.title("메뉴")
    st.page_link(home_page, icon="🏠")
    st.page_link(listings_page, icon="📋")
    st.page_link(location_page, icon="🚇")

    if is_logged_in():
        st.page_link(favorite_page, icon="⭐")
        st.page_link(mypage_page, icon="🗂️")
        st.page_link(ai_chat_page, icon="💬")
        st.page_link(ai_guide_page, icon="🤖")
        st.divider()
        st.caption(f"{st.session_state.email} 님")
        st.button("LOGOUT", on_click=logout, use_container_width=True)
    else:
        st.page_link(login_page, icon="🔐")


navigation.run()

