# 03_listing_manage.py

from datetime import date

import streamlit as st
from streamlit.components.v1 import html as components_html

from clients.listing_client import (
    delete_listing,
    get_listing,
    get_listings_page,
    replace_listing_images,
    search_listings,
    update_listing,
)
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.constants import SEOUL_DISTRICTS
from core.bulk_delete import (
    can_delete,
    checkbox_key,
    names_of,
    picked_ids,
    set_all,
    summarize_deletes,
)
from core.image_delete import summarize_result
from core.image_gallery import (
    MAX_IMAGE_COUNT,
    check_upload,
    count_label,
    image_list,
    rows_of,
)
from core.listing_view import (
    address_line,
    card_title,
    description_preview,
    description_lines,
    format_description_line,
    format_won,
    period_line,
    summary_line,
)
from core.listing_sort import (
    DEFAULT_LABEL,
    default_index,
    sort_key,
    sort_labels,
)
from core.page_params import (
    SEARCH_KEYS,
    build_params,
    parse_edit_id,
    parse_page,
    parse_search,
)
from core.ui import page_header


# 이미지 크기 제한입니다. 백엔드에서도 같은 값으로 다시 검사합니다.
MAX_IMAGE_SIZE = 5 * 1024 * 1024

# 한 페이지에 보여줄 공고 수입니다.
PAGE_SIZE = 10

# 고른 정렬 기준을 담아 둘 자리입니다.
SORT_STATE_KEY = "admin-listing-sort"

page_header("📋", "청약정보 조회 / 삭제", "등록된 공고를 검색하고 대량 삭제할 수 있습니다.")

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

if message := st.session_state.pop("listing_message", None):
    st.success(message)

# 지금 보고 있는 페이지와 수정 중인 공고는 주소창(query parameter)에 둡니다.
# st.session_state에 두면 브라우저를 새로고침할 때 사라지기 때문입니다.
# 로그인 정보는 여기 넣지 않습니다. 그건 Session Storage가 따로 맡습니다.
current_page = parse_page(st.query_params.get_all("page"))
current_edit_id = parse_edit_id(st.query_params.get_all("edit_id"))
# 조건검색도 주소창에 둡니다. 수정 화면에 다녀와도 보던 검색 결과가 남습니다.
current_search = parse_search(
    {name: st.query_params.get_all(name) for name in SEARCH_KEYS}
)

# "page=abc"나 "edit_id=-1"처럼 이상한 값이 들어오면 위에서 안전한 값으로 바꿉니다.
# 주소창도 그 값으로 정리해 두어야 다시 새로고침해도 같은 화면이 나옵니다.
# 한 번 정리하면 값이 같아지므로 화면이 반복해서 다시 실행되지 않습니다.
# 브라우저 뒤로가기는 주소만 바꿀 뿐, Streamlit이 스스로 화면을 다시 그리지 않습니다.
# 그래서 주소는 목록인데 화면은 수정 화면에 그대로 남습니다.
# 주소가 바뀌면(popstate) 화면을 다시 읽어 오도록 한 번만 알려 둡니다.
# 다시 읽어 오므로 저장하지 않은 수정 입력값은 남지 않습니다.
components_html(
    """
    <script>
    (function () {
      const page = window.parent;
      if (page.__listingHistorySyncReady) return;
      page.__listingHistorySyncReady = true;
      page.addEventListener("popstate", function () {
        page.location.reload();
      });
    })();
    </script>
    """,
    height=0,
)

_canonical_params = build_params(current_page, current_edit_id, current_search)

# 값이 이미 같으면 절대로 다시 쓰지 않습니다.
# st.query_params.from_dict()는 같은 값을 써도 브라우저 방문 기록을 새로 쌓습니다.
# 화면이 다시 그려질 때마다 쓰면 같은 주소가 기록에 여러 번 남아,
# 뒤로가기를 눌러도 똑같은 수정 화면으로 되돌아와 제자리에 멈춘 것처럼 보입니다.
if st.query_params.to_dict() != _canonical_params:
    st.query_params.from_dict(_canonical_params)
    st.rerun()


def to_date(value: str | None) -> date:
    """API가 돌려준 "2026-08-01" 문자열을 날짜로 바꿉니다."""
    if not value:
        return date.today()
    return date.fromisoformat(value)


def go_to_page(page: int) -> None:
    """페이지를 옮깁니다. 열려 있던 수정 폼은 닫고, 검색 조건은 유지합니다."""
    st.query_params.from_dict(build_params(page, None, current_search))
    st.rerun()


def open_edit(listing_id: int) -> None:
    """수정 화면을 엽니다. 보고 있던 페이지 번호와 검색 조건은 그대로 둡니다."""
    st.query_params.from_dict(build_params(current_page, listing_id, current_search))
    st.rerun()


def close_edit() -> None:
    """수정 화면을 닫고 목록으로 돌아갑니다. 페이지 번호와 검색 조건은 유지합니다."""
    st.query_params.from_dict(build_params(current_page, None, current_search))
    st.rerun()


@st.dialog("사진 삭제 확인")
def confirm_one_image_delete(listing_id: int, images: list[str], target: str) -> None:
    """사진 한 장을 지우기 전에 한 번 더 묻는 경고창입니다.

    남길 사진 목록을 서버에 보내는 방식이라, 여기서 삭제를 고르기 전까지는
    아무것도 보내지 않습니다.
    """

    st.image(target, width=240)
    st.write("이 사진을 삭제하시겠습니까?")
    st.warning("삭제된 사진은 복구할 수 없습니다.")
    st.caption("공고의 다른 수정 내용은 저장되지 않으며 이 사진만 삭제됩니다.")

    cancel_column, delete_column = st.columns(2)

    with cancel_column:
        if st.button("취소", use_container_width=True, key="one-image-cancel"):
            st.rerun()

    with delete_column:
        if st.button(
            "삭제", type="primary", use_container_width=True, key="one-image-confirm"
        ):
            kept = [url for url in images if url != target]
            try:
                response = replace_listing_images(listing_id, kept, [])
            except BackendAPIError as error:
                st.error(str(error))
                return

            succeeded, message = summarize_result(response)
            if not succeeded:
                st.error(message)
                return

            st.session_state.image_delete_message = message
            st.rerun()


@st.dialog("선택한 공고 삭제 확인")
def confirm_bulk_delete(chosen: list[int], listings: list) -> None:
    """고른 공고를 지우기 전에 무엇을 지우는지 보여 줍니다.

    지우는 일은 되돌릴 수 없어, 이름을 하나씩 늘어놓고 다시 묻습니다.
    여기서 삭제를 고르기 전까지는 서버에 아무것도 보내지 않습니다.
    """

    st.write(f"아래 {len(chosen)}건을 삭제하시겠습니까?")
    st.warning("삭제한 청약정보와 사진은 복구할 수 없습니다.")

    with st.container(height=220, border=True):
        for line in names_of(chosen, listings):
            st.caption(line)

    cancel_column, delete_column = st.columns(2)

    with cancel_column:
        if st.button("취소", use_container_width=True, key="bulk-delete-cancel"):
            st.rerun()

    with delete_column:
        if st.button(
            "삭제", type="primary", use_container_width=True, key="bulk-delete-confirm"
        ):
            succeeded, failed = [], []
            progress = st.progress(0.0, text="삭제하는 중...")

            for done, listing_id in enumerate(chosen, start=1):
                try:
                    response = delete_listing(listing_id)
                    ok, _ = summarize_result(response)
                    (succeeded if ok else failed).append(listing_id)
                except BackendAPIError:
                    failed.append(listing_id)
                progress.progress(done / len(chosen), text=f"{done}/{len(chosen)}건 처리")

            # 지운 공고는 선택에서 뺍니다. 실패한 것만 남겨 다시 시도할 수 있게 합니다.
            # 지운 공고의 선택칸을 끕니다. 실패한 것은 켜 두어 다시 시도할 수 있게 합니다.
            for listing_id in succeeded:
                st.session_state[checkbox_key(listing_id)] = False
            st.session_state.listing_message = summarize_deletes(succeeded, failed)
            st.rerun()


def show_listing_images(listing_id: int, listing: dict) -> None:
    """공고 사진을 보여 주고 더하거나 지웁니다.

    아래 수정 폼과 따로 둡니다. 사진을 정리할 때 폼에 입력만 해 두고
    아직 저장하지 않은 제목·금액 같은 값이 함께 저장되지 않게 하려는 것입니다.
    """

    images = image_list(listing)

    st.caption(f"현재 사진  ·  {count_label(images) or '없음'}")

    if images:
        for row in rows_of(images):
            columns = st.columns(len(row))
            for column, url in zip(columns, row):
                column.image(url, use_container_width=True)
                # 맨 앞 사진이 목록 카드에 보이는 대표 이미지입니다.
                if url == images[0]:
                    column.caption("대표 이미지")
                if column.button(
                    "삭제",
                    use_container_width=True,
                    key=f"image-remove-{listing_id}-{images.index(url)}",
                ):
                    confirm_one_image_delete(listing_id, images, url)
    else:
        st.caption("등록된 사진이 없습니다.")

    remaining = MAX_IMAGE_COUNT - len(images)
    if remaining <= 0:
        st.info(f"사진은 최대 {MAX_IMAGE_COUNT}장까지입니다. 더 넣으려면 먼저 지워 주세요.")
        return

    new_files = st.file_uploader(
        f"사진 추가 (최대 {remaining}장 더)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=f"edit-image-add-{listing_id}",
    )
    new_files = new_files or []

    problem = check_upload(new_files, already=len(images))
    if problem:
        st.error(problem)

    if st.button(
        "사진 저장",
        disabled=not new_files or bool(problem),
        key=f"image-add-save-{listing_id}",
    ):
        try:
            with st.spinner(f"사진 {len(new_files)}장을 업로드하는 중..."):
                response = replace_listing_images(listing_id, images, new_files)
        except BackendAPIError as error:
            st.error(str(error))
            return

        succeeded, message = summarize_result(response)
        if not succeeded:
            st.error(message)
            return

        st.session_state.image_delete_message = message
        st.rerun()


def show_listing_list() -> None:
    """공고 목록과 검색, 수정/삭제 버튼을 보여줍니다."""

    # 입력칸의 처음 값은 주소창에 담긴 검색 조건을 따릅니다.
    # 그래야 수정 화면에 다녀오거나 새로고침해도 조건이 그대로 보입니다.
    district_options = ("전체",) + SEOUL_DISTRICTS
    saved_location = current_search.get("location", "전체")
    location_index = (
        district_options.index(saved_location) if saved_location in district_options else 0
    )

    with st.expander("조건검색", expanded=bool(current_search)):
        with st.form("listing_search_form"):
            search_location = st.selectbox("자치구", district_options, index=location_index)
            search_max_deposit = st.number_input(
                "최대 보증금",
                min_value=0,
                step=10000,
                value=int(current_search.get("max_deposit", 0)),
            )
            search_max_monthly_rent = st.number_input(
                "최대 월세",
                min_value=0,
                step=10000,
                value=int(current_search.get("max_monthly_rent", 0)),
            )
            st.selectbox(
                "정렬 기준",
                sort_labels(),
                index=default_index(),
                key=SORT_STATE_KEY,
                help="검색을 누르면 고른 순서로 다시 정렬합니다.",
            )
            search_submitted = st.form_submit_button("검색")

    # 고른 정렬 기준은 st.session_state에 남습니다.
    # 페이지를 넘기거나 수정 화면에 다녀와도 순서가 유지됩니다.
    current_sort_label = st.session_state.get(SORT_STATE_KEY, DEFAULT_LABEL)
    current_sort = sort_key(current_sort_label)

    if search_submitted:
        # 검색 조건을 주소창에 적어 두고 다시 그립니다.
        # 조건을 화면 변수에만 두면 수정 화면에 다녀왔을 때 사라집니다.
        new_search = {}
        if search_location != "전체":
            new_search["location"] = search_location
        if int(search_max_deposit) > 0:
            new_search["max_deposit"] = str(int(search_max_deposit))
        if int(search_max_monthly_rent) > 0:
            new_search["max_monthly_rent"] = str(int(search_max_monthly_rent))
        # 조건이 그대로면 주소를 다시 쓰지 않습니다.
        # 같은 값을 써도 방문 기록이 쌓여 뒤로가기가 헛돌기 때문입니다.
        target_params = build_params(1, None, new_search)
        if st.query_params.to_dict() != target_params:
            st.query_params.from_dict(target_params)
            st.rerun()

    if current_search:
        params = {"location": current_search["location"]} if "location" in current_search else {}
        for name in ("max_deposit", "max_monthly_rent"):
            if name in current_search:
                params[name] = int(current_search[name])
        params["sort"] = current_sort
        with st.spinner("검색 중..."):
            response = search_listings(params)

        listings = response.get("data") or []
        if not listings:
            st.info("조회된 청약정보가 없습니다.")
            return
        st.caption(f"검색 결과 {len(listings)}건 ({current_sort_label})")
        page = total_pages = total_count = None
    else:
        with st.spinner("불러오는 중..."):
            response = get_listings_page(current_page, PAGE_SIZE, current_sort)

        page_data = response.get("data") or {}
        listings = page_data.get("items") or []
        page = page_data.get("page", 1)
        total_pages = page_data.get("total_pages", 1)
        total_count = page_data.get("total_count", 0)

        # 공고를 지워서 페이지가 줄어든 경우처럼, 백엔드가 맞춰 준 페이지를 따라갑니다.
        # 주소창도 함께 정리해 두면 다시 새로고침해도 같은 화면이 나옵니다.
        # 값이 같아지면 더 이상 고치지 않으므로 화면이 반복해서 다시 실행되지 않습니다.
        if page != current_page:
            # 검색 조건은 그대로 두고 페이지 번호만 맞춥니다.
            # 조건을 빼먹으면 주소가 바뀌면서 검색이 풀립니다.
            st.query_params.from_dict(build_params(page, None, current_search))
            st.rerun()

        if not listings:
            st.info("조회된 청약정보가 없습니다.")
            return

        st.caption(
            f"총 {total_count}건  |  {page} / {total_pages} 페이지 ({current_sort_label})"
        )

    page_ids = [listing["id"] for listing in listings]

    # 고른 상태는 선택칸에서만 읽습니다. 따로 적어 두지 않아 어긋날 일이 없습니다.
    chosen = picked_ids(st.session_state, page_ids)
    allowed, reason = can_delete(chosen)

    select_column, clear_column, delete_column = st.columns([1, 1, 1])

    if select_column.button("전체 선택", use_container_width=True, key="bulk-select-all"):
        set_all(st.session_state, page_ids, True)
        st.rerun()

    if clear_column.button("선택 해제", use_container_width=True, key="bulk-clear"):
        set_all(st.session_state, page_ids, False)
        st.rerun()

    if delete_column.button(
        f"선택 삭제 ({len(chosen)})",
        type="primary",
        use_container_width=True,
        disabled=not allowed,
        key="bulk-delete-open",
    ):
        # 누르면 확인 창만 뜹니다. 이 버튼만으로는 아무것도 지워지지 않습니다.
        confirm_bulk_delete(chosen, listings)

    if chosen:
        st.caption(f":gray[{len(chosen)}건 선택됨 · 이 페이지에서 고른 공고만 지웁니다.]")

    for listing in listings:
        with st.container(border=True):
            # 같은 공고 안에 주택형이 여러 개라 공고명이 전부 같습니다.
            # 주택명을 앞세우고 공고명은 작게 둡니다.
            text_column, image_column = st.columns([3, 1], vertical_alignment="top")

            with text_column:
                # 선택칸이 상태를 직접 들고 있습니다.
                # 여기서 화면을 다시 그리라고 하지 않습니다.
                # 중간에 멈추면 아직 안 그린 아래 카드들의 선택이 사라져,
                # 하나를 풀었는데 나머지까지 줄줄이 풀립니다.
                st.checkbox("선택", key=checkbox_key(listing["id"]))

                st.markdown(f"#### {card_title(listing)}")
                st.caption(f"#{listing['id']}  ·  {listing.get('title') or ''}")

                summary = summary_line(listing)
                if summary:
                    st.write(summary)

                address = address_line(listing)
                if address:
                    st.write(address)

            with image_column:
                if listing.get("image_url"):
                    st.image(listing["image_url"], use_container_width=True)

            # 금액은 가장 먼저 확인하는 값이라 나란히 크게 둡니다.
            deposit_column, rent_column = st.columns(2)
            deposit_column.caption("보증금")
            deposit_column.markdown(f"**{format_won(listing.get('deposit'))}**")
            rent_column.caption("월세")
            rent_column.markdown(f"**{format_won(listing.get('monthly_rent'))}**")

            st.caption(period_line(listing))

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

            link_column, edit_column = st.columns(2)

            with link_column:
                if listing.get("source_url"):
                    st.link_button(
                        "공고 원문 보기",
                        listing["source_url"],
                        use_container_width=True,
                    )

            with edit_column:
                # 수정 버튼을 누르면 이 공고 하나만 수정 화면으로 보여줍니다.
                if st.button(
                    "수정",
                    use_container_width=True,
                    key=f"edit-listing-{listing['id']}",
                ):
                    open_edit(listing["id"])

            with st.expander("이 공고 삭제"):
                st.warning("삭제한 청약정보는 복구할 수 없습니다.")
                delete_confirmed = st.checkbox(
                    "삭제에 동의합니다.",
                    key=f"delete-confirm-{listing['id']}",
                )
                if st.button(
                    "삭제",
                    type="primary",
                    disabled=not delete_confirmed,
                    use_container_width=True,
                    key=f"delete-listing-{listing['id']}",
                ):
                    result = delete_listing(listing["id"])
                    st.session_state.listing_message = result.get(
                        "message", "청약정보를 삭제했습니다."
                    )
                    st.rerun()

    # 검색 결과일 때는 페이지 이동 버튼을 두지 않습니다.
    if total_pages is None:
        return

    st.divider()
    previous_column, input_column, go_column, next_column, info_column = st.columns(
        [1, 1.2, 1, 1, 2]
    )

    with previous_column:
        if st.button("이전", disabled=page <= 1, use_container_width=True, key="listing-page-prev"):
            go_to_page(page - 1)

    with input_column:
        # key에 현재 페이지를 넣어 두면 페이지가 바뀔 때마다 입력창이 새로 만들어집니다.
        # 그래서 이미 만들어진 위젯의 session_state를 건드리지 않아도
        # 입력창 번호가 항상 현재 페이지와 같아집니다.
        target_page = st.number_input(
            "페이지 번호",
            min_value=1,
            max_value=total_pages,
            value=page,
            step=1,
            label_visibility="collapsed",
            key=f"listing-page-input-{page}-{total_pages}",
        )

    with go_column:
        if st.button("이동", use_container_width=True, key="listing-page-go"):
            go_to_page(int(target_page))

    with next_column:
        if st.button("다음", disabled=page >= total_pages, use_container_width=True, key="listing-page-next"):
            go_to_page(page + 1)

    with info_column:
        st.markdown(
            f"<div style='padding-top:0.4rem'>현재 {page} / {total_pages} 페이지</div>",
            unsafe_allow_html=True,
        )


def show_listing_edit(listing_id: int) -> None:
    """선택한 공고 하나만 수정 화면으로 보여줍니다.

    새로고침으로 들어온 경우에도 공고를 다시 조회해서 채웁니다.
    """

    # 주소창에 남은 ID가 이미 지워진 공고를 가리킬 수 있습니다.
    # 이때는 오류 화면 대신 안내를 띄우고 목록으로 되돌립니다.
    try:
        response = get_listing(listing_id)
    except BackendAPIError as error:
        st.warning(f"수정할 청약정보를 불러오지 못했습니다. 목록으로 돌아갑니다. ({error})")
        st.query_params.from_dict(build_params(current_page))
        if st.button("목록으로 돌아가기", key="edit-back-after-error"):
            st.rerun()
        return

    listing = response.get("data") or {}
    if not listing:
        st.warning("수정할 청약정보를 찾을 수 없습니다. 이미 삭제된 공고일 수 있습니다.")
        st.query_params.from_dict(build_params(current_page))
        if st.button("목록으로 돌아가기", key="edit-back-when-missing"):
            st.rerun()
        return

    st.subheader("청약정보 수정")

    # 자치구 목록에 없는 예전 값(예: "서울")이면 선택되지 않은 상태로 둡니다.
    current_location = listing.get("location")
    location_index = (
        SEOUL_DISTRICTS.index(current_location)
        if current_location in SEOUL_DISTRICTS
        else None
    )
    if location_index is None:
        st.warning(
            f"현재 자치구 값 '{current_location}'은 서울 25개 자치구 목록에 없습니다. "
            "저장하려면 자치구를 다시 골라 주세요."
        )

    if message := st.session_state.pop("image_delete_message", None):
        st.success(message)

    # 사진은 아래 수정 폼과 따로 다룹니다.
    # 사진을 만져도 폼에 입력해 둔 값은 그대로 남고,
    # 폼을 저장해도 사진은 건드리지 않습니다.
    show_listing_images(listing_id, listing)

    st.divider()

    with st.form("listing_edit_form"):
        title = st.text_input("공고 제목", value=listing.get("title") or "", key=f"edit-title-{listing_id}")
        housing_name = st.text_input(
            "주택명", value=listing.get("housing_name") or "", key=f"edit-housing-name-{listing_id}"
        )
        area_sqm = st.number_input(
            "면적(㎡)",
            min_value=0.01,
            value=float(listing.get("area_sqm") or 0.01),
            key=f"edit-area-sqm-{listing_id}",
        )
        recruitment_count = st.number_input(
            "모집 인원",
            min_value=1,
            step=1,
            value=int(listing.get("recruitment_count") or 1),
            key=f"edit-recruitment-count-{listing_id}",
        )
        location = st.selectbox(
            "지역(서울 자치구)",
            SEOUL_DISTRICTS,
            index=location_index,
            placeholder="자치구를 선택해 주세요",
            key=f"edit-location-{listing_id}",
        )
        detail_address = st.text_input(
            "상세주소 (선택)",
            value=listing.get("detail_address") or "",
            placeholder="예: 서울 강남구 도곡로 464",
            key=f"edit-detail-address-{listing_id}",
        )
        deposit = st.number_input(
            "보증금",
            min_value=0,
            step=10000,
            value=int(listing.get("deposit") or 0),
            key=f"edit-deposit-{listing_id}",
        )
        monthly_rent = st.number_input(
            "월세",
            min_value=0,
            step=10000,
            value=int(listing.get("monthly_rent") or 0),
            key=f"edit-monthly-rent-{listing_id}",
        )
        application_start_date = st.date_input(
            "신청 시작일",
            value=to_date(listing.get("application_start_date")),
            key=f"edit-start-date-{listing_id}",
        )
        application_end_date = st.date_input(
            "신청 종료일",
            value=to_date(listing.get("application_end_date")),
            key=f"edit-end-date-{listing_id}",
        )
        description = st.text_area(
            "상세 설명", value=listing.get("description") or "", key=f"edit-description-{listing_id}"
        )
        image_file = st.file_uploader(
            "새 이미지 (선택, 최대 5MB) - 고르지 않으면 기존 이미지를 그대로 둡니다",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"edit-image-{listing_id}",
        )

        source_url = st.text_input(
            "원문 URL", value=listing.get("source_url") or "", key=f"edit-source-url-{listing_id}"
        )

        # 두 버튼을 그냥 두면 세로로 쌓이므로, 목록 화면의 페이지 이동 버튼처럼
        # 컬럼으로 나누어 같은 줄에 놓습니다.
        save_column, cancel_column = st.columns(2)

        with save_column:
            saved = st.form_submit_button("저장", type="primary", use_container_width=True)

        with cancel_column:
            canceled = st.form_submit_button("취소", use_container_width=True)

    if canceled:
        close_edit()

    if not saved:
        return

    if not (
        title.strip()
        and housing_name.strip()
        and location
        and description.strip()
        and source_url.strip()
    ):
        st.error("공고 제목, 주택명, 자치구, 상세 설명, 원문 URL을 모두 입력해 주세요.")
        return

    if application_end_date < application_start_date:
        st.error("신청 종료일은 신청 시작일보다 빠를 수 없습니다.")
        return

    if image_file is not None and image_file.size > MAX_IMAGE_SIZE:
        st.error(
            f"이미지 크기는 5MB를 넘을 수 없습니다. "
            f"(선택한 파일: {image_file.size / 1024 / 1024:.1f}MB) "
            f"크기를 줄이거나 이미지를 빼고 저장해 주세요."
        )
        return

    payload = {
        "title": title.strip(),
        "housing_name": housing_name.strip(),
        "area_sqm": str(area_sqm),
        "recruitment_count": str(int(recruitment_count)),
        "location": location,
        "detail_address": detail_address.strip(),
        "deposit": str(int(deposit)),
        "monthly_rent": str(int(monthly_rent)),
        "application_start_date": application_start_date.isoformat(),
        "application_end_date": application_end_date.isoformat(),
        "description": description.strip(),
        "source_url": source_url.strip(),
    }

    with st.spinner("수정하는 중..."):
        result = update_listing(listing_id, payload, image_file)

    if result.get("success"):
        st.session_state.listing_message = result.get(
            "message", "청약정보가 수정되었습니다."
        )
        close_edit()
    else:
        # 실패했는데 목록으로 나가면 성공한 것처럼 보이므로 수정 화면에 머뭅니다.
        st.error(result.get("message", "청약정보 수정에 실패했습니다."))


try:
    edit_listing_id = current_edit_id
    if edit_listing_id is None:
        show_listing_list()
    else:
        show_listing_edit(edit_listing_id)
except BackendAPIError as error:
    st.error(str(error))
