# 02_home.py

import streamlit as st

from core.auth import is_logged_in


st.markdown(
    """
    <style>
    .home-hero {
        background: linear-gradient(135deg, #ff8a65 0%, #ff5252 45%, #ff7043 100%);
        border-radius: 20px;
        padding: 2.5rem 2.2rem;
        margin-bottom: 1.8rem;
        color: white;
        box-shadow: 0 8px 24px rgba(255, 82, 82, 0.25);
    }
    .home-hero .emoji-row {
        font-size: 2.6rem;
        margin-bottom: 0.4rem;
        letter-spacing: 0.3rem;
    }
    .home-hero h1 {
        color: white;
        margin: 0 0 0.5rem 0;
        font-size: 1.9rem;
    }
    .home-hero p {
        color: rgba(255, 255, 255, 0.92);
        margin: 0;
        font-size: 1.02rem;
    }
    .feature-card {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 16px;
        padding: 1.3rem 1.1rem;
        height: 100%;
    }
    .feature-card .feature-icon {
        font-size: 2.1rem;
        margin-bottom: 0.4rem;
    }
    .feature-card h4 {
        margin: 0 0 0.35rem 0;
    }
    .feature-card p {
        font-size: 0.88rem;
        opacity: 0.8;
        margin-bottom: 0.8rem;
        min-height: 2.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if is_logged_in():
    welcome_line = f"{st.session_state.email} 님, 환영합니다 👋"
    sub_line = "My Page에서 즐겨찾기한 청약정보를 확인하고, AI 상담으로 궁금한 점을 바로 물어보세요."
else:
    welcome_line = "공공임대 · 분양 청약, 한 곳에서 확인하세요"
    sub_line = "로그인하면 즐겨찾기 관리와 AI 상담 기능을 이용할 수 있습니다."

st.markdown(
    f"""
    <div class="home-hero">
        <div class="emoji-row">🏠 🏢 🏘️ 🔑</div>
        <h1>공공임대 및 분양 청약 통합 안내</h1>
        <p>{welcome_line}</p>
        <p>{sub_line}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("무엇을 도와드릴까요?")

col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container(border=True):
        st.markdown('<div class="feature-icon">📋</div>', unsafe_allow_html=True)
        st.markdown("**청약정보 조회**")
        st.caption("지역·보증금·월세 조건으로 공고를 검색해 보세요.")
        st.page_link("app_pages/03_listings.py", label="조회하기", icon="➡️")

with col2:
    with st.container(border=True):
        st.markdown('<div class="feature-icon">🚇</div>', unsafe_allow_html=True)
        st.markdown("**주변생활권 분석**")
        st.caption("공고 주변 지하철·마트·병원까지 지도로 확인하세요.")
        st.page_link("app_pages/06_location.py", label="분석하기", icon="➡️")

with col3:
    with st.container(border=True):
        st.markdown('<div class="feature-icon">⭐</div>', unsafe_allow_html=True)
        st.markdown("**즐겨찾기**")
        st.caption("관심 있는 공고를 담아두고 한눈에 비교해 보세요.")
        if is_logged_in():
            st.page_link("app_pages/05_favorite.py", label="즐겨찾기 보기", icon="➡️")
        else:
            st.page_link("app_pages/00_login.py", label="로그인하고 이용하기", icon="🔐")

with col4:
    with st.container(border=True):
        st.markdown('<div class="feature-icon">💬</div>', unsafe_allow_html=True)
        st.markdown("**AI 상담**")
        st.caption("청약 자격, 신청 방법을 AI에게 편하게 물어보세요.")
        if is_logged_in():
            st.page_link("app_pages/05_ai_chat.py", label="상담 시작하기", icon="➡️")
        else:
            st.page_link("app_pages/00_login.py", label="로그인하고 이용하기", icon="🔐")
