# 02_listing_create.py

import streamlit as st

from clients.listing_client import create_listing, upload_listing_images
from core.amount_format import describe_amount
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.constants import SEOUL_DISTRICTS
from core.create_form import current_nonce, field_key, reset_form_state
from core.image_gallery import (
    MAX_IMAGE_COUNT,
    check_upload,
    describe_size,
    rows_of,
)
from core.ui import page_header

page_header("📝", "청약정보 등록", "새 공고를 등록하고 사진을 첨부하세요.")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

# 지금 폼 번호입니다. 초기화를 누르면 번호가 올라가 입력칸이 새로 만들어집니다.
nonce = current_nonce(st.session_state)

st.caption("등록해도 입력한 내용이 그대로 남습니다. 비슷한 공고를 이어서 넣을 때 편합니다.")

# st.form으로 묶지 않습니다.
# 폼 안에서는 등록을 누르기 전까지 화면이 다시 그려지지 않아,
# 보증금과 월세를 입력하는 동안 얼마인지 확인할 수 없기 때문입니다.
title = st.text_input("공고 제목", key=field_key("title", nonce))
housing_name = st.text_input("주택명", key=field_key("housing-name", nonce))
area_sqm = st.number_input("면적(㎡)", min_value=0.01, key=field_key("area-sqm", nonce))
recruitment_count = st.number_input(
    "모집 인원", min_value=1, step=1, key=field_key("recruitment-count", nonce)
)
location = st.selectbox(
    "지역(서울 자치구)",
    SEOUL_DISTRICTS,
    index=None,
    placeholder="자치구를 선택해 주세요",
    key=field_key("location", nonce),
)
detail_address = st.text_input(
    "상세주소 (선택)",
    placeholder="예: 서울 강남구 도곡로 464",
    key=field_key("detail-address", nonce),
)

deposit = st.number_input(
    "보증금", min_value=0, step=10000, key=field_key("deposit", nonce)
)
# 0이 몇 개인지 세지 않아도 되도록 쉼표와 만·억 단위 읽기를 함께 보여 줍니다.
st.caption(describe_amount(deposit))

monthly_rent = st.number_input(
    "월세", min_value=0, step=10000, key=field_key("monthly-rent", nonce)
)
st.caption(describe_amount(monthly_rent))

application_start_date = st.date_input("신청 시작일", key=field_key("start-date", nonce))
application_end_date = st.date_input("신청 종료일", key=field_key("end-date", nonce))
description = st.text_area("상세 설명", key=field_key("description", nonce))
image_files = st.file_uploader(
    f"사진 (선택, 최대 {MAX_IMAGE_COUNT}장 · 한 장 5MB)",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    key=field_key("image", nonce),
)
image_files = image_files or []

# 고른 사진을 바로 보여 줍니다. 스무 장까지 올 수 있어 줄로 끊어 놓습니다.
if image_files:
    total_size = sum(getattr(file, "size", 0) for file in image_files)
    st.caption(
        f"{len(image_files)}장 선택 ({describe_size(total_size)})"
        "  ·  맨 앞 사진이 목록 카드에 보입니다."
    )

    for row in rows_of([file.name for file in image_files]):
        columns = st.columns(len(row))
        for column, name in zip(columns, row):
            file = next(f for f in image_files if f.name == name)
            column.image(file, use_container_width=True)

    # 보내기 전에 먼저 막아 줍니다. 수십 MB를 다 보낸 뒤 거절당하면 오래 기다리게 됩니다.
    upload_problem = check_upload(image_files)
    if upload_problem:
        st.error(upload_problem)
source_url = st.text_input(
    "원문 URL",
    placeholder="예: https://apply.lh.or.kr/...",
    key=field_key("source-url", nonce),
)

# 두 버튼을 나란히 둡니다.
submit_column, reset_column = st.columns(2)

with submit_column:
    submitted = st.button("등록", type="primary", use_container_width=True, key="create-submit")

with reset_column:
    reset_clicked = st.button("입력 초기화", use_container_width=True, key="create-reset")

if reset_clicked:
    # 값을 지우고 폼 번호를 올려 입력칸을 새로 만듭니다.
    reset_form_state(st.session_state)
    st.rerun()

if submitted:
    if not (
        title.strip()
        and housing_name.strip()
        and location
        and description.strip()
        and source_url.strip()
    ):
        st.error("공고 제목, 주택명, 자치구, 상세 설명, 원문 URL을 모두 입력해 주세요.")
    elif application_end_date < application_start_date:
        st.error("신청 종료일은 신청 시작일보다 빠를 수 없습니다.")
    elif check_upload(image_files):
        st.error(check_upload(image_files))
    else:
        payload = {
            "title": title.strip(),
            "housing_name": housing_name.strip(),
            "area_sqm": float(area_sqm),
            "recruitment_count": int(recruitment_count),
            "location": location,
            "detail_address": detail_address.strip() or None,
            "deposit": int(deposit),
            "monthly_rent": int(monthly_rent),
            "application_start_date": application_start_date.isoformat(),
            "application_end_date": application_end_date.isoformat(),
            "description": description.strip(),
            "image_url": None,
            "image_urls": [],
            "source_url": source_url.strip(),
        }
        try:
            # 사진을 고른 경우에만 먼저 올리고, 받은 URL을 payload에 넣습니다.
            # 한 번에 보내므로 도중에 실패하면 백엔드가 올라간 파일을 도로 지웁니다.
            if image_files:
                with st.spinner(f"사진 {len(image_files)}장을 업로드하는 중..."):
                    upload_result = upload_listing_images(image_files)
                image_urls = (upload_result.get("data") or {}).get("image_urls") or []
                payload["image_urls"] = image_urls
                # 맨 앞 사진이 목록 카드에 보일 대표 이미지가 됩니다.
                payload["image_url"] = image_urls[0] if image_urls else None

            result = create_listing(payload)
            if result.get("success"):
                st.success(result.get("message", "청약정보가 등록되었습니다."))
            else:
                st.error(result.get("message", "청약정보 등록에 실패했습니다."))
        except BackendAPIError as error:
            st.error(str(error))
