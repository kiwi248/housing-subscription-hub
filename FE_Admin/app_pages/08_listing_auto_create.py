# 08_listing_auto_create.py
"""공고 PDF를 Gemini에 보내 청약정보를 뽑아내고, 확인한 뒤 등록합니다.

뽑아낸 값을 바로 저장하지 않습니다. 관리자가 화면에서 확인하고 고른 건만
기존 청약정보 등록 API로 보냅니다.
"""

from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from clients.gemini_client import (
    GeminiError,
    extract_listings_from_pdf,
    identify_images,
)
from clients.listing_client import create_listing, upload_listing_images
from core.api_client import BackendAPIError
from core.auth import is_logged_in
from core.constants import SEOUL_DISTRICTS
from core.document_images import extract_images
from core.gemini_config import get_model_name, has_api_key
from core.image_gallery import rows_of
from core.image_matching import one_house_only, suggest_matches
from core.listing_extract import (
    FIXABLE_DATE_FIELDS,
    FIXABLE_NUMBER_FIELDS,
    SHARED_TEXT_FIELDS,
    missing_shared_fields,
    summarize,
    unreadable_fields,
    validate_all,
)
from core.ui import page_header


# 공고 파일 크기 제한입니다. 너무 큰 파일은 모델이 처리하지 못합니다.
MAX_PDF_SIZE = 20 * 1024 * 1024


class _UploadedImage:
    """공고에서 꺼낸 사진을 업로드 함수가 받는 모양으로 맞춥니다.

    화면에서 고른 파일(st.file_uploader가 주는 값)과 같은 자리를 갖도록
    name, type, getvalue()만 흉내 냅니다. 그래야 사진을 올리는 코드를
    수동 등록과 똑같이 쓸 수 있습니다.
    """

    def __init__(self, image: dict):
        self.name = image["name"]
        self._data = image["data"]
        suffix = self.name.rsplit(".", 1)[-1].lower() if "." in self.name else "png"
        fallback_type = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{suffix}"
        self.type = image.get("mime_type") or fallback_type

    def getvalue(self) -> bytes:
        return self._data

page_header(
    "🤖",
    "청약정보 등록(자동)",
    "PDF 또는 HWPX 공고에서 등록 정보를 추출하고 검토하세요.",
)

if not is_logged_in():
    st.warning("로그인이 필요합니다.")
    st.stop()

st.caption(
    "공고 PDF를 올리면 Gemini가 청약정보를 뽑아냅니다. "
    "뽑아낸 값은 바로 저장되지 않으며, 확인하고 고른 건만 등록합니다."
)

if not has_api_key():
    st.error(
        "Gemini API 키가 없어 자동 추출을 쓸 수 없습니다.\n\n"
        "`FE_Admin/.env` 파일에 `GEMINI_API_KEY=발급받은키` 를 넣고 화면을 새로고침해 주세요."
    )
    st.info("키를 넣기 전까지는 `청약정보 등록(수동)` 화면을 이용해 주세요.")
    st.stop()

st.caption(f"사용 모델: {get_model_name()}")

pdf_file = st.file_uploader("공고 파일 (PDF 또는 HWPX)", type=["pdf", "hwpx"], key="auto-pdf")

if st.button("공고에서 청약정보 뽑아내기", type="primary", disabled=pdf_file is None):
    if pdf_file.size > MAX_PDF_SIZE:
        st.error(
            f"공고 파일 크기는 20MB를 넘을 수 없습니다. "
            f"(선택한 파일: {pdf_file.size / 1024 / 1024:.1f}MB)"
        )
    else:
        raw = pdf_file.getvalue()

        # 사진은 파일에서 직접 꺼냅니다. AI가 필요 없는 일입니다.
        # 실패해도 청약정보 추출은 계속합니다. 사진은 나중에 손으로 올릴 수 있습니다.
        try:
            found_images = extract_images(raw, pdf_file.name)
        except Exception as error:
            found_images = []
            st.warning(f"사진을 꺼내지 못했습니다. 청약정보만 뽑습니다. ({type(error).__name__})")

        try:
            # 두 가지를 동시에 물어봅니다. 서로 기다릴 필요가 없어 시간이 절반쯤 줄어듭니다.
            #   1) 공고 파일에서 청약정보 뽑기
            #   2) 꺼낸 사진마다 어느 주택 것인지 알아내기
            with st.spinner("Gemini가 공고와 사진을 읽는 중입니다..."):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    listing_job = pool.submit(extract_listings_from_pdf, raw, pdf_file.name)
                    label_job = pool.submit(identify_images, found_images)
                    extracted = listing_job.result()
                    image_labels_found = label_job.result()

            st.session_state.auto_extracted = extracted
            st.session_state.auto_source_name = pdf_file.name
            st.session_state.auto_images = found_images
            st.session_state.auto_image_labels = image_labels_found
            st.session_state.auto_fixes = {}
            st.session_state.auto_shared = {}
            # 파일을 새로 올리면 이전에 고른 사진 선택은 지웁니다.
            for key in [k for k in st.session_state if str(k).startswith("auto-img-")]:
                del st.session_state[key]
        except GeminiError as error:
            st.error(str(error))

extracted = st.session_state.get("auto_extracted")

if not extracted:
    st.stop()

# 화면에서 손으로 채운 값이 있으면 덮어씁니다.
# 모델이 못 읽은 칸을 관리자가 채우면 그 값으로 다시 확인합니다.
fixes = st.session_state.get("auto_fixes") or {}
patched = []
for index, item in enumerate(extracted):
    merged = dict(item) if isinstance(item, dict) else item
    if isinstance(merged, dict) and index in fixes:
        merged.update(fixes[index])
    patched.append(merged)

# 공고 전체에 하나뿐인 값은 여기서 한 번만 받습니다.
# 원문 주소가 문서에 없는 공고가 있어, 건마다 넣게 하면 번거롭습니다.
shared = st.session_state.get("auto_shared") or {}
if shared:
    for merged in patched:
        if isinstance(merged, dict):
            for field, value in shared.items():
                if value:
                    merged[field] = value

results = validate_all(patched, SEOUL_DISTRICTS)
counts = summarize(results)

st.divider()
st.subheader(f"추출 결과 {counts['total']}건")

ready_column, blocked_column = st.columns(2)
ready_column.metric("등록 가능", f"{counts['ready']}건")
blocked_column.metric("확인 필요", f"{counts['blocked']}건")

if counts["blocked"]:
    st.warning(
        "값이 비어 있거나 형식이 맞지 않는 건이 있습니다. "
        "공고문 표에서 칸이 병합되어 있으면 값을 읽지 못하는 일이 있습니다. "
        "아래에서 그 값을 직접 채우면 함께 등록할 수 있습니다."
    )

missing_shared = missing_shared_fields(patched)
if missing_shared:
    with st.container(border=True):
        st.markdown("**공고 전체에 넣을 값**")
        st.caption(
            "문서에서 찾지 못한 값입니다. 한 번만 넣으면 모든 건에 함께 들어갑니다."
        )
        entered_shared = {}
        for field, title in SHARED_TEXT_FIELDS:
            if field not in missing_shared:
                continue
            entered_shared[field] = st.text_input(
                title,
                placeholder="예: https://www.geumcheon.go.kr/...",
                key=f"auto-shared-{field}",
            )

        if st.button("모든 건에 적용", key="auto-shared-apply"):
            saved = dict(st.session_state.get("auto_shared") or {})
            saved.update({k: v.strip() for k, v in entered_shared.items()})
            st.session_state.auto_shared = saved
            st.rerun()

found_images = st.session_state.get("auto_images") or []

# 사진에 붙일 이름표입니다. 아래 공고건마다 이 이름으로 고릅니다.
def _image_label(index: int, image: dict) -> str:
    """사진 고르는 칸에 보여 줄 이름입니다.

    Gemini가 알아낸 주택명이 있으면 함께 적어, 무엇을 고르는지 알 수 있게 합니다.
    """
    where = f"{image['page']}쪽" if image.get("page") else f"{index + 1}번째"
    labels = st.session_state.get("auto_image_labels") or []
    found = labels[index] if index < len(labels) else {}
    name = (found.get("house_name") or "").strip()
    kind = (found.get("kind") or "").strip()
    tail = f" — {name}" if name else (f" — {kind}" if kind else "")
    return f"{index + 1}. {where}{tail}"


image_labels = [_image_label(i, im) for i, im in enumerate(found_images)]

if found_images:
    st.divider()
    st.subheader(f"공고에서 꺼낸 사진 {len(found_images)}장")
    st.caption(
        "아래 공고건마다 붙일 사진을 고릅니다. "
        "여기서는 어떤 사진이 몇 번인지만 확인하세요."
    )

    for row in rows_of([str(i) for i in range(len(found_images))]):
        columns = st.columns(len(row))
        for column, key in zip(columns, row):
            index = int(key)
            image = found_images[index]
            column.image(image["data"], use_container_width=True)
            column.caption(image_labels[index])

# 공고건마다 붙일 사진을 미리 골라 둡니다. 화면에서 바꿀 수 있습니다.
found_labels = st.session_state.get("auto_image_labels") or []
suggested = suggest_matches(results, found_images, found_labels)
single_house = one_house_only(results)

st.divider()
st.subheader("등록할 청약정보")

if found_images:
    if single_house:
        st.caption(
            "이 공고는 주택이 한 곳이라 꺼낸 사진을 모두 붙여 두었습니다."
        )
    else:
        st.caption(
            "주택이 여러 곳이라, 사진에 적힌 주택 이름을 읽어 미리 골라 두었습니다. "
            "맞지 않으면 바꿔 주세요."
        )

selected_indexes = []
# 공고건마다 고른 사진의 자리 번호를 담습니다.
picked_by_index: dict[int, list[int]] = {}

for result in results:
    source = result["source"]
    label = source.get("housing_name") or source.get("title") or f"{result['index'] + 1}번째 항목"

    with st.container(border=True):
        if result["problems"]:
            st.markdown(f"**{label}** — 확인 필요")
            for problem in result["problems"]:
                st.caption(f"• {problem}")

            # 모델이 못 읽은 칸만 보여 주고 직접 채우게 합니다.
            # 공고문 표에서 칸이 병합되어 있으면 값을 읽지 못하는 일이 생깁니다.
            bad = unreadable_fields(result["source"])
            if bad:
                st.caption(":gray[공고문을 보고 아래 값을 채우면 등록할 수 있습니다.]")
                entered = {}
                for field, title in FIXABLE_NUMBER_FIELDS:
                    if field not in bad:
                        continue
                    step = 0.01 if field == "area_sqm" else 1
                    entered[field] = st.number_input(
                        title,
                        min_value=0.0 if field == "area_sqm" else 0,
                        step=step,
                        key=f"auto-fix-{result['index']}-{field}",
                    )
                for field, title in FIXABLE_DATE_FIELDS:
                    if field not in bad:
                        continue
                    entered[field] = st.date_input(
                        title, key=f"auto-fix-{result['index']}-{field}"
                    ).isoformat()

                if st.button("이 값으로 다시 확인", key=f"auto-fixgo-{result['index']}"):
                    saved = dict(st.session_state.get("auto_fixes") or {})
                    saved[result["index"]] = entered
                    st.session_state.auto_fixes = saved
                    st.rerun()
        else:
            payload = result["payload"]
            checked = st.checkbox(
                f"{label}", value=True, key=f"auto-pick-{result['index']}"
            )
            if checked:
                selected_indexes.append(result["index"])
            st.caption(
                f"{payload['location']}  ·  전용 {payload['area_sqm']}㎡  ·  "
                f"{payload['recruitment_count']}호 모집"
            )
            st.caption(
                f"보증금 {payload['deposit']:,}원  |  월세 {payload['monthly_rent']:,}원  |  "
                f"신청 {payload['application_start_date']} ~ {payload['application_end_date']}"
            )

            if found_images:
                # 주택이 한 곳뿐이면 꺼낸 사진을 모두 붙입니다.
                # 여러 곳이면 쪽 번호로 미리 골라 둔 것을 처음 값으로 씁니다.
                default = (
                    list(range(len(found_images)))
                    if single_house
                    else suggested.get(result["index"], [])
                )
                chosen = st.multiselect(
                    "붙일 사진",
                    options=list(range(len(found_images))),
                    default=default,
                    format_func=lambda i: image_labels[i],
                    key=f"auto-imgpick-{result['index']}",
                )
                picked_by_index[result["index"]] = chosen
                if not chosen:
                    st.caption(":gray[사진 없이 등록됩니다.]")

        with st.expander("뽑아낸 원본 값 보기"):
            st.json(source)

st.divider()

if st.button(
    f"선택한 {len(selected_indexes)}건 등록",
    type="primary",
    disabled=not selected_indexes,
):
    by_index = {result["index"]: result for result in results}
    succeeded, failed = [], []

    # 등록할 건들이 실제로 쓰는 사진만 한 번씩 올립니다.
    # 공고건마다 올리면 같은 파일이 여러 벌 쌓입니다.
    # 여러 공고가 같은 사진을 가리켜도 파일은 하나입니다.
    needed = sorted(
        {
            image_index
            for index in selected_indexes
            for image_index in picked_by_index.get(index, [])
        }
    )

    # 사진 자리 번호 -> 올리고 받은 주소
    url_by_image: dict[int, str] = {}

    if needed:
        try:
            with st.spinner(f"사진 {len(needed)}장을 올리는 중..."):
                response = upload_listing_images(
                    [_UploadedImage(found_images[i]) for i in needed]
                )
            uploaded = (response.get("data") or {}).get("image_urls") or []
            url_by_image = dict(zip(needed, uploaded))
        except BackendAPIError as error:
            st.error(f"사진을 올리지 못했습니다. 사진 없이 등록합니다. ({error})")

    with st.spinner("등록하는 중..."):
        for index in selected_indexes:
            payload = dict(by_index[index]["payload"])

            # 이 공고건이 고른 사진만 붙입니다. 첫 장이 대표 이미지가 됩니다.
            urls = [
                url_by_image[i]
                for i in picked_by_index.get(index, [])
                if i in url_by_image
            ]
            payload["image_urls"] = urls
            payload["image_url"] = urls[0] if urls else None
            label = payload["housing_name"]
            try:
                response = create_listing(payload)
                if response.get("success"):
                    succeeded.append(label)
                else:
                    failed.append((label, response.get("message", "등록에 실패했습니다.")))
            except BackendAPIError as error:
                failed.append((label, str(error)))
                # 한 건이라도 실패하면 멈춥니다. 남은 건은 원인을 확인한 뒤 다시 시도합니다.
                break

    if succeeded:
        st.success(f"{len(succeeded)}건을 등록했습니다.")
        for name in succeeded:
            st.caption(f"• {name}")

    if failed:
        st.error(f"{len(failed)}건을 등록하지 못했습니다.")
        for name, reason in failed:
            st.caption(f"• {name}: {reason}")

    if succeeded and not failed:
        # 같은 PDF를 두 번 등록하지 않도록 결과를 비웁니다.
        st.session_state.pop("auto_extracted", None)

if st.button("추출 결과 지우기", key="auto-clear"):
    st.session_state.pop("auto_extracted", None)
    st.session_state.pop("auto_source_name", None)
    st.rerun()
