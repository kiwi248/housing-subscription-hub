# 07_log_history.py

import pandas as pd
import streamlit as st

from clients.log_client import get_log_history
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.timezone import to_kst_display
from core.ui import page_header


page_header("🗂️", "로그 이력 조회", "Supabase에 저장된 warning/error 로그를 조회합니다. (info는 DB에 저장하지 않습니다)")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

level = st.selectbox("level 필터", ["all", "warning", "error"])
limit = st.slider("조회 건수", min_value=10, max_value=200, value=50, step=10)

try:
    with st.spinner("불러오는 중..."):
        response = get_log_history(level=level, limit=limit)
    logs = response.get("data") or []

    if not logs:
        st.info("저장된 로그 이력이 없습니다.")
    else:
        st.caption(f"총 {len(logs)}건 · 시각은 한국시간(KST) 기준")
        df = pd.DataFrame(logs)
        df["time"] = df["time"].apply(to_kst_display)
        if "created_at" in df.columns:
            df["created_at"] = df["created_at"].apply(to_kst_display)
        df = df.rename(
            columns={
                "id": "ID",
                "time": "시각",
                "level": "레벨",
                "screen": "화면",
                "message": "메시지",
                "latency_ms": "지연시간(ms)",
                "created_at": "DB 저장 시각",
            }
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
except BackendAPIError as error:
    st.error(str(error))
