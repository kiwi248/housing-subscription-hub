# listing_extract.py
"""Gemini가 공고 PDF에서 뽑아낸 값을 등록용 값으로 바꿉니다.

모델이 돌려준 값은 그대로 믿지 않습니다. 필수 항목이 있는지, 숫자와 날짜가
말이 되는지 여기서 한 번 더 확인하고, 이상하면 이유를 알려 줍니다.
확인을 통과한 값만 기존 등록 API로 보냅니다.

Streamlit이나 Gemini에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

from datetime import date

# 등록 API가 요구하는 항목입니다. 화면의 수동 등록과 같은 기준입니다.
REQUIRED_TEXT_FIELDS = ("title", "housing_name", "location", "description", "source_url")


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_int(value: object) -> int | None:
    """"10,260,000원" 같은 표기도 숫자로 바꿉니다."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = _clean_text(value)
    if not text:
        return None
    for mark in (",", "원", " ", " "):
        text = text.replace(mark, "")
    try:
        return int(float(text))
    except ValueError:
        return None


def _to_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    text = _clean_text(value).replace("㎡", "").replace("m2", "").replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _to_date(value: object) -> date | None:
    text = _clean_text(value).replace(".", "-").replace("/", "-")
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def validate_extracted(item: object, districts: tuple[str, ...]) -> tuple[dict | None, list[str]]:
    """추출한 값 하나를 등록용 값으로 바꿉니다.

    (등록용 값, 문제 목록)을 돌려줍니다. 문제가 하나라도 있으면 등록용 값은 None입니다.
    """

    problems: list[str] = []
    if not isinstance(item, dict):
        return None, ["추출 결과가 올바른 형태가 아닙니다."]

    payload: dict = {}

    for field in REQUIRED_TEXT_FIELDS:
        text = _clean_text(item.get(field))
        if not text:
            problems.append(f"{field} 값이 없습니다.")
        payload[field] = text

    if payload.get("location") and payload["location"] not in districts:
        problems.append(f"자치구 '{payload['location']}'은 서울 25개 자치구가 아닙니다.")

    area = _to_float(item.get("area_sqm"))
    if area is None or area <= 0:
        problems.append("면적을 숫자로 읽을 수 없습니다.")
    payload["area_sqm"] = area

    count = _to_int(item.get("recruitment_count"))
    if count is None or count <= 0:
        problems.append("모집 인원을 숫자로 읽을 수 없습니다.")
    payload["recruitment_count"] = count

    for field, label in (("deposit", "보증금"), ("monthly_rent", "월세")):
        amount = _to_int(item.get(field))
        if amount is None or amount < 0:
            problems.append(f"{label}을(를) 숫자로 읽을 수 없습니다.")
        payload[field] = amount

    start = _to_date(item.get("application_start_date"))
    end = _to_date(item.get("application_end_date"))
    if start is None:
        problems.append("신청 시작일을 날짜로 읽을 수 없습니다.")
    if end is None:
        problems.append("신청 종료일을 날짜로 읽을 수 없습니다.")
    if start and end and end < start:
        problems.append("신청 종료일이 시작일보다 빠릅니다.")
    payload["application_start_date"] = start.isoformat() if start else None
    payload["application_end_date"] = end.isoformat() if end else None

    # 상세주소는 없어도 등록할 수 있습니다. 있으면 담고, 없으면 빈 값으로 둡니다.
    payload["detail_address"] = _clean_text(item.get("detail_address")) or None

    # 사진은 PDF에서 따로 뽑아 나중에 붙입니다.
    payload["image_url"] = None
    payload["image_urls"] = []

    # 쪽 번호는 등록 API가 받는 항목이 아니라 payload에 넣지 않습니다.
    # 위치도와 짝지을 때만 쓰므로 원본(source)에서 읽어 씁니다.

    if problems:
        return None, problems

    return payload, []


# 화면에서 손으로 채울 수 있는 항목입니다.
# 모델이 못 읽은 값을 관리자가 직접 넣고 등록할 수 있게 합니다.
FIXABLE_NUMBER_FIELDS = (
    ("area_sqm", "면적(㎡)"),
    ("recruitment_count", "모집 인원"),
    ("deposit", "보증금"),
    ("monthly_rent", "월세"),
)

FIXABLE_DATE_FIELDS = (
    ("application_start_date", "신청 시작일"),
    ("application_end_date", "신청 종료일"),
)

# 공고 전체에 한 번만 넣으면 되는 값입니다.
# 원문 주소는 공고 하나에 하나뿐이라, 건마다 따로 넣게 하면 번거롭습니다.
SHARED_TEXT_FIELDS = (("source_url", "공고 원문 URL"),)


def missing_shared_fields(items: object) -> list[str]:
    """공고 전체에서 비어 있는 공통 항목을 알려 줍니다.

    금천구 공고처럼 문서 안에 원문 주소가 적혀 있지 않은 경우가 있습니다.
    그때는 관리자가 공고 페이지 주소를 한 번만 넣으면 됩니다.
    """

    bad: list[str] = []
    for field, _ in SHARED_TEXT_FIELDS:
        for item in items or []:
            if isinstance(item, dict) and _clean_text(item.get(field)):
                break
        else:
            bad.append(field)
    return bad


def unreadable_fields(item: object) -> list[str]:
    """모델이 뽑은 값 중 숫자나 날짜로 읽을 수 없는 항목의 이름을 돌려줍니다.

    화면은 이 목록을 보고 어떤 칸을 손으로 채우게 할지 정합니다.
    """

    if not isinstance(item, dict):
        return []

    bad: list[str] = []

    area = _to_float(item.get("area_sqm"))
    if area is None or area <= 0:
        bad.append("area_sqm")

    count = _to_int(item.get("recruitment_count"))
    if count is None or count <= 0:
        bad.append("recruitment_count")

    for field in ("deposit", "monthly_rent"):
        amount = _to_int(item.get(field))
        if amount is None or amount < 0:
            bad.append(field)

    for field, _ in FIXABLE_DATE_FIELDS:
        if _to_date(item.get(field)) is None:
            bad.append(field)

    return bad


def validate_all(items: object, districts: tuple[str, ...]) -> list[dict]:
    """추출 목록 전체를 확인합니다.

    각 항목마다 {"index", "payload", "problems", "source"}를 돌려줍니다.
    """

    if not isinstance(items, list):
        return []

    results = []
    for index, item in enumerate(items):
        payload, problems = validate_extracted(item, districts)
        results.append(
            {
                "index": index,
                "payload": payload,
                "problems": problems,
                "source": item if isinstance(item, dict) else {},
            }
        )

    return results


def summarize(results: list[dict]) -> dict:
    """확인 결과를 세어 화면에 보여 줄 값으로 만듭니다."""

    ready = [r for r in results if not r["problems"]]
    return {
        "total": len(results),
        "ready": len(ready),
        "blocked": len(results) - len(ready),
    }
