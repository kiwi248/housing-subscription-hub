# 01_home.py

import streamlit as st

from core.auth import is_logged_in


st.markdown(
    """
    <style>
    .admin-hero {
        background: linear-gradient(135deg, #37474f 0%, #263238 55%, #1a2327 100%);
        border-radius: 20px;
        padding: 2.5rem 2.2rem;
        margin-bottom: 1.8rem;
        color: white;
        box-shadow: 0 8px 24px rgba(38, 50, 56, 0.35);
    }
    .admin-hero .emoji-row {
        font-size: 2.6rem;
        margin-bottom: 0.4rem;
        letter-spacing: 0.3rem;
    }
    .admin-hero h1 {
        color: white;
        margin: 0 0 0.5rem 0;
        font-size: 1.9rem;
    }
    .admin-hero p {
        color: rgba(255, 255, 255, 0.85);
        margin: 0;
        font-size: 1.02rem;
    }
    .admin-card {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 16px;
        padding: 1.3rem 1.1rem;
        height: 100%;
    }
    .admin-card .admin-icon {
        font-size: 2.1rem;
        margin-bottom: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if is_logged_in():
    welcome_line = f"{st.session_state.admin_username} 님, 환영합니다 👋"
    sub_line = "청약정보 관리부터 실시간 로그 모니터링까지 한 곳에서 처리하세요."
else:
    welcome_line = "관리자 페이지에 오신 것을 환영합니다"
    sub_line = "왼쪽 메뉴에서 로그인하면 모든 관리 기능을 이용할 수 있습니다."

st.markdown(
    f"""
    <div class="admin-hero">
        <div class="emoji-row">🛠️ 📋 📊 🔐</div>
        <h1>관리자 홈</h1>
        <p>{welcome_line}</p>
        <p>{sub_line}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not is_logged_in():
    st.warning("왼쪽 메뉴에서 로그인해 주세요.")
    st.stop()

st.subheader("바로가기")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown('<div class="admin-icon">📝</div>', unsafe_allow_html=True)
        st.markdown("**청약정보 등록**")
        st.caption("새 공고를 등록하고 사진을 첨부하세요.")
        st.page_link("app_pages/02_listing_create.py", label="등록하기", icon="➡️")

with col2:
    with st.container(border=True):
        st.markdown('<div class="admin-icon">📋</div>', unsafe_allow_html=True)
        st.markdown("**청약정보 조회/삭제**")
        st.caption("등록된 공고를 검색하고 대량 삭제할 수 있습니다.")
        st.page_link("app_pages/03_listing_manage.py", label="관리하기", icon="➡️")

with col3:
    with st.container(border=True):
        st.markdown('<div class="admin-icon">⭐</div>', unsafe_allow_html=True)
        st.markdown("**즐겨찾기 현황**")
        st.caption("유저들이 많이 찜한 공고 순위를 확인하세요.")
        st.page_link("app_pages/04_favorite_ranking.py", label="순위 보기", icon="➡️")

with col4:
    with st.container(border=True):
        st.markdown('<div class="admin-icon">📊</div>', unsafe_allow_html=True)
        st.markdown("**실시간 로그**")
        st.caption("서비스 요청 로그를 5초마다 자동으로 확인하세요.")
        st.page_link("app_pages/06_log_dashboard.py", label="대시보드 보기", icon="➡️")
