import streamlit as st

from app_pages.favorite_map import render_favorite_map
from clients.favorite_client import delete_favorite, get_mypage_favorites
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.ui import page_header


page_header("⭐", "즐겨찾기 목록", "담아둔 청약정보를 한눈에 확인하세요.")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

try:
    if message := st.session_state.pop("favorite_message", None):
        st.info(message)

    favorites_response = get_mypage_favorites(st.session_state.user_id)
    favorites = favorites_response.get("data") or []

    if not favorites:
        st.info("즐겨찾기한 청약정보가 없습니다.")
    else:
        st.caption(f"총 {len(favorites)}건")

        list_column, map_column = st.columns(2)

        with list_column:
            for favorite in favorites:
                listing = favorite.get("listing") or {}
                address = (
                    listing.get("detail_address")
                    or listing.get("location")
                    or "-"
                )

                with st.container(border=True):
                    st.write(f"**{listing.get('title') or '제목 없음'}**")
                    st.write(
                        f"대상: {listing.get('type') or '-'}  |  "
                        f"위치: {address}  |  "
                        f"금액: {int(listing.get('price') or 0):,}원"
                    )

                    if st.button(
                        "즐겨찾기 삭제",
                        key=f"favorite-delete-{favorite['listing_id']}",
                    ):
                        result = delete_favorite(
                            st.session_state.user_id,
                            favorite["listing_id"],
                        )
                        st.session_state.favorite_message = result.get(
                            "message",
                            "즐겨찾기를 삭제했습니다.",
                        )
                        st.rerun()

        with map_column:
            render_favorite_map(favorites)

except BackendAPIError as error:
    st.error(str(error))
