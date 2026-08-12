# 06_log_dashboard.py

import pandas as pd
import streamlit as st

from clients.log_client import get_logs
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.timezone import to_kst_display
from core.ui import page_header


page_header("📊", "실시간 로그 대시보드", "서비스 로그를 5초마다 자동으로 새로고침해서 보여줍니다.")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()


@st.fragment(run_every="5s")
def show_logs():
    level = st.selectbox("level 필터", ["all", "info", "warning", "error"])

    try:
        response = get_logs(level=level, limit=50)
        logs = response.get("data") or []
    except BackendAPIError as error:
        st.error(str(error))
        return

    if not logs:
        st.info("아직 로그가 없습니다.")
        return

    df = pd.DataFrame(logs)
    df["time"] = df["time"].apply(to_kst_display)

    st.caption(f"최근 {len(df)}건 (5초마다 자동 갱신) · 시각은 한국시간(KST) 기준")
    st.dataframe(
        df.rename(
            columns={
                "time": "시각",
                "level": "레벨",
                "screen": "화면",
                "message": "메시지",
                "latency_ms": "지연시간(ms)",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.bar_chart(df["level"].value_counts())


show_logs()
