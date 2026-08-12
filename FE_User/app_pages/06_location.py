"""등록된 청약 공고를 검색하고 주변 생활권을 지도에 표시하는 화면입니다."""

import unicodedata

import streamlit as st
from clients.listing_client import get_listings
from clients.location_client import (
    geocode_location,
    get_nearby_facilities,
)
from core.api_client import BackendAPIError
from core.location_map import build_location_deck
from core.ui import page_header
from core.listing_view import (
    address_line,
    description_lines,
    format_description_line,
    format_won,
    period_line,
    summary_line,
)

DEFAULT_RADIUS_M = 2000
DEFAULT_FACILITY_LIMIT = 3

RADIUS_OPTIONS = {
    "1km": 1000,
    "2km": 2000,
    "3km": 3000,
}


def normalize_search_text(value: object) -> str:
    """검색어의 대소문자·공백·특수문자 표기를 통일합니다."""

    normalized = unicodedata.normalize(
        "NFKC",
        str(value or ""),
    ).casefold()

    return "".join(normalized.split())


def listing_search_text(listing: dict) -> str:
    """공고명·주택명·주소를 하나의 검색 문자열로 만듭니다."""

    values = [
        listing.get("title"),
        listing.get("housing_name"),
        listing.get("location"),
        listing.get("detail_address"),
    ]

    return normalize_search_text(
        " ".join(str(value or "") for value in values)
    )


def find_matching_listings(
    listings: list[dict],
    query: str,
) -> list[dict]:
    """입력한 문구가 공고명 또는 공고주소에 들어 있는 공고만 찾습니다."""

    normalized_query = normalize_search_text(query)

    if not normalized_query:
        return []

    return [
        listing
        for listing in listings
        if normalized_query in listing_search_text(listing)
    ]


def listing_label(listing: dict) -> str:
    """검색된 공고를 선택 목록에 표시할 문자열을 만듭니다."""

    title = str(listing.get("title") or "공고명 없음")
    housing_name = str(listing.get("housing_name") or "")
    detail_address = str(
        listing.get("detail_address") or "상세주소 없음"
    )

    display_name = housing_name or title

    return f"{display_name} | {detail_address}"


@st.dialog("공고 상세정보", width="large")
def show_listing_detail(listing: dict) -> None:
    """선택한 청약 공고의 상세정보를 팝업으로 표시합니다."""

    housing_name = str(
        listing.get("housing_name") or "주택명 없음"
    )
    title = str(
        listing.get("title") or "공고명 없음"
    )

    st.subheader(housing_name)
    st.caption(title)

    summary = summary_line(listing)
    if summary:
        st.write(summary)

    address = address_line(listing)
    if address:
        st.write(address)

    deposit_column, rent_column = st.columns(2)

    with deposit_column:
        st.caption("보증금")
        st.markdown(
            f"**{format_won(listing.get('deposit'))}**"
        )

    with rent_column:
        st.caption("월 임대료")
        st.markdown(
            f"**{format_won(listing.get('monthly_rent'))}**"
        )

    st.caption(period_line(listing))

    description = description_lines(listing)
    if description:
        st.divider()
        st.markdown("#### 상세 내용")

        for line in description:
            st.markdown(format_description_line(line))

    source_url = listing.get("source_url")
    if source_url:
        st.link_button(
            "공고 원문 보기",
            source_url,
            use_container_width=True,
        )


page_header(
    "🚇",
    "주변생활권 분석",
    "청약정보에 등록된 공고명 또는 공고주소를 검색하면 "
    "주변 지하철역·마트·병원 정보를 알려드립니다.",
)


with st.form("location-search-form"):
    query = st.text_input(
        "공고명 또는 공고주소",
        placeholder="예: 행복주택 입주자 모집공고",
    )

    selected_radius = st.selectbox(
        "생활권 검색 반경",
        options=list(RADIUS_OPTIONS),
        index=1,
    )

    submitted = st.form_submit_button(
        "주변생활권 탐색",
        type="primary",
        use_container_width=True,
    )


if submitted:
    query = query.strip()

    if not query:
        st.warning("공고명 또는 공고주소를 입력해 주세요.")
        st.stop()

    try:
        with st.spinner("청약정보에서 공고를 검색하는 중입니다..."):
            listing_response = get_listings()
            all_listings = listing_response.get("data") or []
    except BackendAPIError as error:
        st.error(str(error))
        st.stop()

    matching_listings = find_matching_listings(
        listings=all_listings,
        query=query,
    )

    if not matching_listings:
        st.session_state.pop("location-search-matches", None)
        st.error(
            "청약정보 내에서 일치하는 공고를 찾을 수 없습니다. "
            "공고명 또는 공고주소를 다시 확인해 주세요."
        )
        st.stop()

    st.session_state["location-search-matches"] = matching_listings
    st.session_state["location-search-radius"] = RADIUS_OPTIONS.get(
        selected_radius,
        DEFAULT_RADIUS_M,
    )
    st.session_state["location-search-radius-label"] = selected_radius


matching_listings = st.session_state.get(
    "location-search-matches",
    [],
)

if matching_listings:
    selected_listing = st.selectbox(
        "분석할 공고 선택",
        options=matching_listings,
        format_func=listing_label,
    )

    listing_address = str(
        selected_listing.get("detail_address") or ""
    ).strip()

    if not listing_address:
        st.error(
            "선택한 공고에 상세주소가 등록되어 있지 않아 "
            "생활권을 분석할 수 없습니다."
        )
        st.stop()

    radius_m = st.session_state.get(
        "location-search-radius",
        DEFAULT_RADIUS_M,
    )

    try:
        with st.spinner("공고 주소와 주변 생활권을 검색하는 중입니다..."):
            location_response = geocode_location(listing_address)
            location = location_response.get("data") or {}

            latitude = location.get("latitude")
            longitude = location.get("longitude")

            if latitude is None or longitude is None:
                st.error("공고 주소의 좌표를 확인할 수 없습니다.")
                st.stop()

            facility_response = get_nearby_facilities(
                latitude=latitude,
                longitude=longitude,
                radius_m=radius_m,
                limit=DEFAULT_FACILITY_LIMIT,
            )
            facilities = facility_response.get("data") or {}

            stations = facilities.get("subways") or []
            marts = facilities.get("marts") or []
            hospitals = facilities.get("hospitals") or []
    except BackendAPIError as error:
        st.error(str(error))
        st.stop()

    listing_title = str(
        selected_listing.get("title") or "공고명 없음"
    )

    st.subheader("선택한 공고")

    if st.button(
        listing_title,
        key=f"location-listing-detail-{selected_listing.get('id')}",
    ):
        show_listing_detail(selected_listing)

    st.caption(location.get("address") or listing_address)

    st.subheader("주변 생활권 지도")

    location_deck = build_location_deck(
        title=listing_title,
        latitude=float(latitude),
        longitude=float(longitude),
        stations=stations,
        marts=marts,
        hospitals=hospitals,
        radius_m=radius_m,
    )

    st.pydeck_chart(
        location_deck,
        use_container_width=True,
    )

    st.caption(
        "🏠 공고 위치 · 🚇 지하철역 · "
        "🛒 마트 · 🏥 병원"
    )
