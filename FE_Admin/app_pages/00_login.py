# 00_login.py

import streamlit as st

from core.auth import is_logged_in, login
from core.ui import page_header


if is_logged_in():
    st.success("로그인에 성공했습니다.")
    st.stop()

page_header("🔐", "관리자 로그인", "관리자 계정으로 로그인해 주세요.")

with st.form("admin_login_form"):
    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")
    submitted = st.form_submit_button("로그인", type="primary")

if submitted:
    if not username.strip() or not password.strip():
        st.error("아이디와 비밀번호를 입력해 주세요.")
    else:
        with st.spinner("로그인 진행 중..."):
            login(username.strip(), password.strip())
