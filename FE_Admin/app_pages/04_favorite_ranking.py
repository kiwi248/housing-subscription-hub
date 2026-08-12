# 04_favorite_ranking.py

import pandas as pd
import streamlit as st

from clients.favorite_client import get_favorite_ranking
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.ui import page_header


page_header("⭐", "즐겨찾기 많은 순 조회", "유저가 즐겨찾기한 청약정보를 많은 순으로 보여줍니다.")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

try:
    with st.spinner("불러오는 중..."):
        response = get_favorite_ranking()
    ranking = response.get("data") or []

    if not ranking:
        st.info("즐겨찾기 데이터가 없습니다.")
    else:
        st.caption(f"총 {len(ranking)}건")
        df = pd.DataFrame(ranking).rename(
            columns={
                "listing_id": "청약 ID",
                "title": "공고명",
                "favorite_count": "즐겨찾기 수",
            }
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
except BackendAPIError as error:
    st.error(str(error))
