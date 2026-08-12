# 05_favorite_detail.py

import pandas as pd
import streamlit as st

from clients.favorite_client import get_favorite_detail
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.ui import page_header


page_header("🔍", "즐겨찾기 상세 조회", "어떤 유저가 어떤 청약정보를 즐겨찾기했는지 확인합니다.")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

listing_id_input = st.text_input("청약정보 ID로 필터 (비워두면 전체 조회)")

listing_id = None
if listing_id_input.strip():
    try:
        listing_id = int(listing_id_input.strip())
    except ValueError:
        st.error("청약정보 ID는 숫자로 입력해 주세요.")
        st.stop()

try:
    with st.spinner("불러오는 중..."):
        response = get_favorite_detail(listing_id)
    details = response.get("data") or []

    if not details:
        st.info("즐겨찾기 데이터가 없습니다.")
    else:
        st.caption(f"총 {len(details)}건")
        df = pd.DataFrame(details).rename(
            columns={
                "favorite_id": "즐겨찾기 ID",
                "user_id": "유저 ID",
                "nickname": "닉네임",
                "listing_id": "청약 ID",
                "title": "공고명",
                "created_at": "즐겨찾기 등록일",
            }
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
except BackendAPIError as error:
    st.error(str(error))
