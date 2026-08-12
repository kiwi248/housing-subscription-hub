"""관리자용 Streamlit 멀티페이지 앱입니다.

브라우저를 새로고침하면 st.session_state가 비기 때문에, 로그인 상태를
브라우저 Session Storage에 두었다가 다시 읽어 옵니다.

주의: Session Storage 기반 로그인 복원은 화면 상태를 되살리는 편의 기능이며
실제 관리자 인증 수단이 아닙니다. 저장된 값은 사용자가 브라우저 개발자
도구에서 바꿀 수 있습니다. 외부 배포 환경에서는 백엔드 관리자 API에
만료되는 서명 토큰 인증과 서버 검증을 적용해야 합니다.
"""

import streamlit as st

# set_page_config()는 이 앱에서 가장 먼저 실행되는 Streamlit 명령이어야 합니다.
# 그래서 다른 import보다 위에 둡니다. 보통은 import를 파일 맨 위에 모으지만
# 여기서는 순서가 곧 동작이라 예외로 둡니다.
#
# core.auth를 먼저 불러오면 core.api_client가 딸려 오는데,
# 그 모듈은 읽히는 순간 st.secrets를 확인합니다.
# 로컬에는 secrets.toml이 없어서, Streamlit 버전에 따라 이때
# "No secrets found" 안내를 화면에 그려 버립니다.
# 그러면 아래 set_page_config()가 첫 번째 명령이 아니게 되어
# StreamlitSetPageConfigMustBeFirstCommandError로 앱이 뜨지 않습니다.
st.set_page_config(
    page_title="관리자 페이지",
    page_icon="🛠️",
    layout="wide",
)

from streamlit_session_browser_storage import SessionStorage  # noqa: E402

from core.auth import init_state, is_logged_in, logout  # noqa: E402

home_page = st.Page("app_pages/01_home.py", title="홈", icon="🏠", default=True)
login_page = st.Page("app_pages/00_login.py", title="로그인", icon="🔐")
listing_create_page = st.Page(
    "app_pages/02_listing_create.py", title="청약정보 등록(수동)", icon="📝"
)
listing_auto_create_page = st.Page(
    "app_pages/08_listing_auto_create.py", title="청약정보 등록(자동)", icon="🤖"
)
listing_manage_page = st.Page("app_pages/03_listing_manage.py", title="청약정보 조회/삭제", icon="📋")
favorite_ranking_page = st.Page("app_pages/04_favorite_ranking.py", title="즐겨찾기 순위", icon="⭐")
favorite_detail_page = st.Page("app_pages/05_favorite_detail.py", title="즐겨찾기 상세", icon="🔍")
log_dashboard_page = st.Page("app_pages/06_log_dashboard.py", title="로그 대시보드", icon="📊")
log_history_page = st.Page("app_pages/07_log_history.py", title="로그 이력 조회", icon="🗂️")


# 페이지는 로그인 여부와 상관없이 모두 등록합니다.
# 로그인 상태에 따라 목록을 바꾸면, 브라우저를 새로고침했을 때
# st.session_state가 비어 있어 지금 보고 있던 주소가 목록에서 사라지고
# "Page not found"가 뜹니다.
# 등록은 항상 하되, 아래에서 로그인 여부를 검사합니다.
pages = [
    home_page,
    login_page,
    listing_create_page,
    listing_auto_create_page,
    listing_manage_page,
    favorite_ranking_page,
    favorite_detail_page,
    log_dashboard_page,
    log_history_page,
]

# 경로 등록을 먼저 합니다. 아래에서 잠시 멈추더라도 지금 보고 있는 주소가
# 유지되어, 새로고침 후 원래 페이지로 돌아올 수 있습니다.
navigation = st.navigation(pages, position="hidden")

# 탭을 닫으면 사라지는 Session Storage를 씁니다. Local Storage는 쓰지 않습니다.
storage = SessionStorage(key="admin_session_storage")
stored_values = storage.getAll()

# 첫 실행에서는 브라우저에서 값이 아직 오지 않아 None이 옵니다.
# 이때 로그아웃으로 단정하면 보호 페이지에서 로그인 화면으로 튕겨
# 보고 있던 페이지를 잃어버립니다. 값이 도착할 때까지 기다립니다.
# 값이 도착하면 컴포넌트가 화면을 다시 실행시킵니다.
if stored_values is None:
    st.caption("로그인 상태를 확인하는 중입니다...")
    st.stop()

stored_loginout = stored_values.get("loginout") or "logout"
stored_admin_username = stored_values.get("admin_username") or ""

# 새로고침 직후에는 여기서 브라우저에 저장해 둔 값으로 상태를 되살립니다.
init_state(stored_loginout, stored_admin_username)

# 화면에서 로그인/로그아웃한 결과를 브라우저 쪽에도 반영합니다.
# 값이 이미 같으면 쓰지 않으므로 저장이 되풀이되지 않습니다.
if st.session_state.loginout == "login":
    if stored_loginout != "login":
        storage.setItem("loginout", "login", key="save_loginout")
    if stored_admin_username != st.session_state.admin_username:
        storage.setItem(
            "admin_username",
            st.session_state.admin_username,
            key="save_admin_username",
        )
elif stored_loginout != "logout":
    # 로그아웃했으면 브라우저에 남은 로그인 정보를 지웁니다.
    storage.deleteAll(key="clear_admin_session")

# 로그인 없이 볼 수 있는 페이지입니다. 나머지는 모두 보호 페이지입니다.
public_url_paths = {home_page.url_path, login_page.url_path}

# 보호 페이지에 로그인 없이 들어오면 오류 화면 대신 로그인 화면으로 보냅니다.
# 주소를 직접 입력해도 여기서 걸리므로 관리자 기능에 접근할 수 없습니다.
if navigation.url_path not in public_url_paths and not is_logged_in():
    st.switch_page("app_pages/00_login.py")

with st.sidebar:
    st.title("관리자 메뉴")
    st.page_link(home_page)

    if is_logged_in():
        st.page_link(listing_create_page)
        st.page_link(listing_auto_create_page)

        # 조회 화면은 보고 있던 페이지와 수정 중인 공고를 주소창에 담아 둡니다.
        # query_params를 주면 메뉴를 누를 때 그 값으로 주소가 정리되므로,
        # 이미 이 화면에 있어도 edit_id가 사라지고 목록 1페이지로 돌아갑니다.
        st.page_link(listing_manage_page, query_params={"page": "1"})

        st.page_link(favorite_ranking_page)
        st.page_link(favorite_detail_page)
        st.page_link(log_dashboard_page)
        st.page_link(log_history_page)

        st.divider()
        st.caption(f"{st.session_state.admin_username} 님 로그인 중")
        st.button("LOGOUT", on_click=logout, use_container_width=True)
    else:
        st.page_link(login_page)

navigation.run()
