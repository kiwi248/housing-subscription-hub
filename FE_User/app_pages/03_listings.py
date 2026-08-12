# 03_listings.py

import streamlit as st

from clients.favorite_client import create_favorite
from clients.listing_client import get_listings, search_listings
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.constants import SEOUL_DISTRICTS
from core.dday import dday_label, dim_if_closed, is_closed
from core.listing_view import (
    address_line,
    card_title,
    dday_badge,
    description_preview,
    description_lines,
    format_description_line,
    format_won,
    period_line,
    summary_line,
)
from core.image_gallery import count_label, image_list, rows_of
from core.listing_sort import (
    DEFAULT_LABEL,
    default_index,
    sort_key,
    sort_labels,
)
from core.pagination import (
    PAGE_SIZE,
    build_params,
    clamp_page,
    parse_page,
    slice_page,
    total_pages,
)
from core.ui import page_header


page_header("📋", "청약정보 조회", "조건을 검색해서 원하는 공고를 찾아보세요.")

if message := st.session_state.pop("listing_message", None):
    st.success(message)

# 지금 보고 있는 페이지는 주소창에 둡니다.
# 새로고침해도 보던 페이지가 그대로 나오게 하려는 것입니다.
current_page = parse_page(st.query_params.get_all("page"))


def go_to_page(page: int) -> None:
    """페이지를 옮깁니다. 값이 같으면 주소를 다시 쓰지 않습니다."""
    target = build_params(page)
    if st.query_params.to_dict() != target:
        st.query_params.from_dict(target)
    st.rerun()

SORT_STATE_KEY = "user-listing-sort"

with st.expander("조건검색"):
    with st.form("listing_search_form"):
        search_location = st.selectbox("서울 자치구", ("전체",) + SEOUL_DISTRICTS)
        search_max_deposit = st.number_input("최대 보증금", min_value=0, step=10000, value=0)
        search_max_monthly_rent = st.number_input("최대 월세", min_value=0, step=10000, value=0)
        st.selectbox(
            "정렬 기준",
            sort_labels(),
            index=default_index(),
            key=SORT_STATE_KEY,
            help="검색을 누르면 고른 순서로 다시 정렬합니다.",
        )
        search_submitted = st.form_submit_button("검색")

# 고른 정렬 기준은 st.session_state에 남습니다.
# 페이지를 넘기거나 즐겨찾기를 눌러 화면이 다시 그려져도 순서가 유지됩니다.
current_sort_label = st.session_state.get(SORT_STATE_KEY, DEFAULT_LABEL)
current_sort = sort_key(current_sort_label)

try:
    if search_submitted:
        params = {"sort": current_sort}
        if search_location != "전체":
            params["location"] = search_location
        if int(search_max_deposit) > 0:
            params["max_deposit"] = int(search_max_deposit)
        if int(search_max_monthly_rent) > 0:
            params["max_monthly_rent"] = int(search_max_monthly_rent)
        with st.spinner("검색 중..."):
            response = search_listings(params)
    else:
        with st.spinner("불러오는 중..."):
            response = get_listings(current_sort)

    listings = response.get("data") or []

    if not listings:
        st.info("조회된 청약정보가 없습니다.")
    else:
        total_count = len(listings)

        if search_submitted:
            # 검색 결과는 관리자 화면과 같이 한 번에 모두 보여 줍니다.
            page = last_page = None
            page_items = listings
            st.caption(f"검색 결과 {total_count}건 ({current_sort_label})")
        else:
            last_page = total_pages(total_count, PAGE_SIZE)
            page = clamp_page(current_page, total_count, PAGE_SIZE)
            page_items = slice_page(listings, page, PAGE_SIZE)

            # 공고가 줄어 페이지가 사라진 경우 주소창도 함께 맞춰 둡니다.
            if page != current_page:
                go_to_page(page)

            st.caption(
                f"총 {total_count}건  |  {page} / {last_page} 페이지 ({current_sort_label})"
            )

        for listing in page_items:
            end_date = listing.get("application_end_date")
            closed = is_closed(end_date)
            remaining = dday_label(end_date)

            # 신청이 끝난 공고는 글자를 흐린 회색으로 두어 한눈에 구분되게 합니다.
            def dim(text: object) -> str:
                return dim_if_closed(text, closed)

            with st.container(border=True):
                # 공고명은 주택형마다 같아서 구분이 안 됩니다.
                # 주택명을 앞세우고 공고명은 작게 둡니다.
                text_column, image_column = st.columns([3, 1], vertical_alignment="top")

                with text_column:
                    st.markdown(f"#### {dim(card_title(listing))}")
                    st.caption(listing.get("title") or "")

                    summary = summary_line(listing)
                    if summary:
                        st.markdown(dim(summary))

                    address = address_line(listing)
                    if address:
                        st.markdown(dim(address))

                with image_column:
                    if listing.get("image_url"):
                        st.image(listing["image_url"], use_container_width=True)

                # 금액은 가장 먼저 보게 되는 값이라 한 줄에 나란히 크게 둡니다.
                deposit_column, rent_column = st.columns(2)
                deposit_column.caption("보증금")
                deposit_column.markdown(
                    dim(f"**{format_won(listing.get('deposit'))}**")
                )
                rent_column.caption("월세")
                rent_column.markdown(
                    dim(f"**{format_won(listing.get('monthly_rent'))}**")
                )

                # 신청 기간과 남은 날짜를 한 줄에 붙여 둡니다.
                period_column, dday_column = st.columns([3, 1], vertical_alignment="center")
                period_column.caption(period_line(listing))
                badge = dday_badge(remaining, closed)
                if badge:
                    dday_column.markdown(badge)

                # 설명이 길어 목록이 늘어지므로 첫 줄만 보여 주고 접어 둡니다.
                # 사진도 여기 안에 둡니다. 카드마다 사진을 여러 장 펼쳐 놓으면
                # 목록이 사진으로 뒤덮여 오히려 훑기 어려워집니다.
                preview = description_preview(listing)
                images = image_list(listing)
                summary = preview or count_label(images)

                if summary:
                    with st.expander(f"상세 정보  ·  {summary}"):
                        if images:
                            st.caption(count_label(images))
                            # 스무 장까지 올 수 있어 한 줄에 넷씩 끊어 놓습니다.
                            for row in rows_of(images):
                                columns = st.columns(len(row))
                                for column, url in zip(columns, row):
                                    column.image(url, use_container_width=True)
                            st.divider()

                        # 줄바꿈 하나는 마크다운에서 공백이 되어 항목이 한 줄로 붙습니다.
                        # 줄마다 따로 그려 항목이 구분되게 합니다.
                        for line in description_lines(listing):
                            st.markdown(format_description_line(line))

                link_column, favorite_column = st.columns(2)

                with link_column:
                    if listing.get("source_url"):
                        st.link_button(
                            "공고 원문 보기",
                            listing["source_url"],
                            use_container_width=True,
                        )

                with favorite_column:
                    if is_logged_in():
                        if st.button(
                            "즐겨찾기 추가",
                            use_container_width=True,
                            key=f"favorite-add-{listing['id']}",
                        ):
                            result = create_favorite(
                                st.session_state.user_id, listing["id"]
                            )
                            st.session_state.listing_message = result.get(
                                "message", "즐겨찾기에 등록되었습니다."
                            )
                            st.rerun()
                    else:
                        st.caption("로그인하면 즐겨찾기에 담을 수 있습니다.")

        # 검색 결과일 때는 페이지 이동 버튼을 두지 않습니다.
        if last_page is not None:
            st.divider()
            previous_column, input_column, go_column, next_column, info_column = st.columns(
                [1, 1.2, 1, 1, 2]
            )

            with previous_column:
                if st.button(
                    "이전", disabled=page <= 1, use_container_width=True, key="user-page-prev"
                ):
                    go_to_page(page - 1)

            with input_column:
                # key에 현재 페이지를 넣어 두면 페이지가 바뀔 때마다 입력창이 새로 만들어집니다.
                target_page = st.number_input(
                    "페이지 번호",
                    min_value=1,
                    max_value=last_page,
                    value=page,
                    step=1,
                    label_visibility="collapsed",
                    key=f"user-page-input-{page}-{last_page}",
                )

            with go_column:
                if st.button("이동", use_container_width=True, key="user-page-go"):
                    go_to_page(int(target_page))

            with next_column:
                if st.button(
                    "다음",
                    disabled=page >= last_page,
                    use_container_width=True,
                    key="user-page-next",
                ):
                    go_to_page(page + 1)

            with info_column:
                st.caption(f"현재 {page} / {last_page} 페이지")
except BackendAPIError as error:
    st.error(str(error))
