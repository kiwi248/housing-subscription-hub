"""페이지 상단에 공통으로 쓰는 그라디언트 헤더입니다."""

import streamlit as st

_STYLE_INJECTED_KEY = "_ui_page_header_style_injected"

_STYLE = """
<style>
.page-header {
    background: linear-gradient(135deg, #37474f 0%, #263238 55%, #1a2327 100%);
    border-radius: 16px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.5rem;
    color: white;
    box-shadow: 0 6px 18px rgba(38, 50, 56, 0.3);
}
.page-header h1 {
    color: white;
    margin: 0;
    font-size: 1.55rem;
    display: flex;
    align-items: center;
    gap: 0.55rem;
}
.page-header p {
    color: rgba(255, 255, 255, 0.85);
    margin: 0.35rem 0 0 0;
    font-size: 0.95rem;
}
</style>
"""


def page_header(icon: str, title: str, subtitle: str | None = None) -> None:
    """다크 슬레이트 그라디언트 배너로 페이지 제목을 그립니다."""

    if not st.session_state.get(_STYLE_INJECTED_KEY):
        st.markdown(_STYLE, unsafe_allow_html=True)
        st.session_state[_STYLE_INJECTED_KEY] = True

    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="page-header">
            <h1>{icon} {title}</h1>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
