# listing_view.py
"""청약정보를 화면에 보여줄 때 쓰는 문구를 만듭니다.

관리자 목록에서 씁니다. 사용자 화면과 같은 내용이지만,
두 앱은 각자 폴더에서 실행되어 모듈을 공유할 수 없어 따로 둡니다.

같은 공고 안에 주택형이 여러 개라 공고명이 전부 같습니다.
그래서 목록에서는 주택명을 앞세우고, 나머지 정보는 짧게 끊어 보여 줍니다.

Streamlit에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

from core.area_format import format_area


def card_title(listing: dict) -> str:
    """카드 제목입니다. 주택명이 없으면 공고명을 대신 씁니다."""

    housing_name = (listing.get("housing_name") or "").strip()
    if housing_name:
        return housing_name

    title = (listing.get("title") or "").strip()
    return title or "제목 없음"


def format_won(value: object) -> str:
    """금액에 세 자리마다 쉼표를 넣습니다."""

    try:
        return f"{int(value):,}원"
    except (TypeError, ValueError):
        return "-"


def summary_line(listing: dict) -> str:
    """자치구·전용면적·모집 인원을 한 줄로 묶습니다.

    값이 없는 항목은 빼서 "-  ·  -" 같은 문구가 나오지 않게 합니다.
    """

    parts = []

    location = (listing.get("location") or "").strip()
    if location:
        parts.append(location)

    area = listing.get("area_sqm")
    if area not in (None, ""):
        parts.append(f"전용 {format_area(area)}")

    count = listing.get("recruitment_count")
    if count not in (None, ""):
        parts.append(f"{count}호 모집")

    return "  ·  ".join(parts)


def address_line(listing: dict) -> str:
    """상세주소 줄입니다. 주소가 없으면 빈 문구입니다."""

    address = (listing.get("detail_address") or "").strip()
    return f"📍 {address}" if address else ""


def period_line(listing: dict) -> str:
    """신청 기간을 한 줄로 만듭니다."""

    start = listing.get("application_start_date") or "-"
    end = listing.get("application_end_date") or "-"
    return f"신청 {start} ~ {end}"


def description_preview(listing: dict, limit: int = 60) -> str:
    """상세 설명의 첫 줄만 짧게 보여 줍니다.

    설명이 길어 목록이 늘어지므로, 자세한 내용은 펼쳐 보게 합니다.
    """

    description = (listing.get("description") or "").strip()
    if not description:
        return ""

    first_line = description.splitlines()[0].strip()
    if len(first_line) <= limit:
        return first_line

    return first_line[:limit].rstrip() + "…"


def description_lines(listing: dict) -> list[str]:
    """상세 설명을 줄 단위로 나눕니다.

    설명은 "신청자격 : ...", "소득기준 : ..." 처럼 줄로 나뉘어 저장돼 있습니다.
    그런데 마크다운은 줄바꿈 하나를 공백으로 바꿔 버려, 그대로 넘기면
    모든 항목이 한 줄에 붙어 나옵니다. 그래서 줄로 잘라 따로 그립니다.
    빈 줄은 버립니다.
    """

    description = (listing.get("description") or "").strip()
    if not description:
        return []

    return [line.strip() for line in description.splitlines() if line.strip()]


def format_description_line(line: object) -> str:
    """"신청자격 : 값" 을 "**신청자격** : 값" 으로 바꿉니다.

    항목 이름을 굵게 해서 눈으로 훑기 쉽게 합니다.
    콜론이 없는 줄은 그대로 둡니다.
    """

    text = ("" if line is None else str(line)).strip()
    if not text:
        return ""

    for separator in (" : ", ": ", " :", ":"):
        if separator in text:
            label, _, value = text.partition(separator)
            label = label.strip()
            value = value.strip()
            if label and value:
                return f"**{label}** : {value}"
            break

    return text
