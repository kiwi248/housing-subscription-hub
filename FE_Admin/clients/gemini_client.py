# gemini_client.py
"""Gemini에 공고 PDF를 보내 청약정보를 뽑아냅니다.

주의: 이 파일은 실제 Gemini API 키가 없어 아직 실행 검증을 하지 못했습니다.
키를 넣고 처음 쓸 때는 결과를 반드시 사람이 확인해 주세요.
호출부를 이 함수 하나로 모아 두었으므로, SDK 사용법이 다르면 여기만 고치면 됩니다.
"""

import json
import mimetypes
import time
from pathlib import Path

from core.gemini_config import get_api_key, get_model_name


class GeminiError(RuntimeError):
    """Gemini 호출이 실패했을 때 화면에 보여 줄 오류입니다."""


# 서버가 붐빌 때 다시 시도하는 횟수와 기다리는 시간(초)입니다.
# 무료로 쓰는 모델은 사람이 몰리면 503을 자주 돌려줍니다.
# 조금 기다리면 대개 풀리므로, 사람이 버튼을 여러 번 누르지 않게 여기서 기다립니다.
RETRY_WAITS = (5, 15, 30)

# 다시 시도해 볼 만한 오류입니다. 잘못된 요청은 다시 보내도 같은 결과입니다.
RETRYABLE_CODES = (429, 500, 502, 503, 504)

IMAGE_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


def describe_call_error(error: Exception, api_key: str = "") -> str:
    """호출 실패를 사람이 읽을 수 있는 문구로 바꿉니다.

    키 값이 오류 문구에 섞여 나올 수 있어 반드시 가려 냅니다.
    """

    text = str(error)
    if api_key and api_key in text:
        text = text.replace(api_key, "***")

    if "503" in text or "UNAVAILABLE" in text:
        return (
            "Gemini 서버가 지금 붐빕니다. 잠시 뒤 다시 눌러 주세요. "
            "(모델 사용량이 몰릴 때 생기며 곧 풀립니다)"
        )
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return (
            "Gemini 호출 한도를 넘었습니다. 조금 기다렸다가 다시 눌러 주세요."
        )
    if "401" in text or "403" in text or "API key" in text:
        return (
            "Gemini API 키가 올바르지 않습니다. "
            "FE_Admin/.env의 GEMINI_API_KEY를 확인해 주세요."
        )
    if "404" in text or "NOT_FOUND" in text:
        return (
            f"모델 '{get_model_name()}'을(를) 찾을 수 없습니다. "
            "FE_Admin/.env의 GEMINI_MODEL을 확인해 주세요."
        )
    if "400" in text or "INVALID_ARGUMENT" in text:
        return (
            "Gemini가 이 파일을 읽지 못했습니다. "
            "PDF 또는 HWPX 파일인지, 파일이 깨지지 않았는지 확인해 주세요. "
            "다시 눌러도 같은 결과가 나옵니다."
        )

    return f"Gemini 호출에 실패했습니다. ({type(error).__name__})"


def _should_retry(error: Exception) -> bool:
    text = str(error)
    return any(str(code) in text for code in RETRYABLE_CODES)


# 모델에게 요구하는 출력 형태입니다. 등록 API가 받는 항목과 이름을 맞춥니다.
EXTRACT_PROMPT = """당신은 공공임대 청약 공고 PDF에서 등록용 정보를 뽑아내는 도구입니다.

아래 규칙을 지켜 JSON 배열만 출력하세요. 설명 문장은 쓰지 마세요.

- 배열의 각 원소는 '주택 1개 + 주택형(신청유형) 1개'입니다.
  주택형은 표에 "13㎡", "29㎡" 처럼 적힌 신청 단위입니다.
  주택이나 주택형이 다르면 원소를 나눕니다.
- 한 주택형 안에 면적이 여러 줄로 적혀 있고 임대보증금과 월임대료가 같다면,
  그것은 같은 주택형의 세대별 차이일 뿐이므로 원소를 나누지 마세요.
  이때 area_sqm은 첫 줄의 면적(대표면적)을 쓰고,
  recruitment_count는 그 주택형의 모집 호수 전체를 씁니다.
  그리고 description 끝에 아래 한 줄을 덧붙이세요.
  "세대별 면적 : 유형 내 세대에 따라 OO㎡ ~ OO㎡ 로 다를 수 있으며 임대료는 동일합니다"
- 각 원소는 다음 항목을 가집니다.
  title: 공고명
  housing_name: 주택명과 주택형 (예: "방화동원룸(유니트로) 13㎡형")
  area_sqm: 전용면적 숫자만 (예: 13.98)
  recruitment_count: 모집 호수 숫자만
  location: 서울 자치구 이름 (예: "강서구")
  detail_address: 그 주택의 도로명 주소 (예: "강서구 개화동로21길 49")
  deposit: 임대보증금 원 단위 숫자만
  monthly_rent: 월 임대료 원 단위 숫자만
  application_start_date: 신청 시작일 YYYY-MM-DD
  application_end_date: 신청 종료일 YYYY-MM-DD
  description: 신청자격, 소득기준, 자산기준, 공급 구성, 주의사항을 줄바꿈으로 나눈 항목형 설명
  source_url: 공고 원문 주소 (PDF에서 찾을 수 없으면 빈 문자열)
  page: 이 주택의 위치도(지도 그림)가 실린 쪽 번호. 없으면 null
- 값을 찾을 수 없으면 지어내지 말고 빈 문자열이나 null을 넣으세요.
- 금액에 쉼표나 '원'을 붙이지 마세요.
- 표에서 주택형 이름 칸이 비어 있어도 면적과 금액이 다르면 별개의 원소로 만드세요.
  칸이 병합되어 이름이 생략된 줄을 빠뜨리지 마세요.
"""

# 모델이 돌려줄 형태를 못 박아 둡니다.
# 형식을 지정하지 않으면 항목 이름이나 자료형이 조금씩 달라져
# 아래 확인 단계에서 걸리는 일이 생깁니다.
EXTRACT_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "housing_name": {"type": "STRING"},
            "area_sqm": {"type": "NUMBER", "nullable": True},
            "recruitment_count": {"type": "INTEGER", "nullable": True},
            "location": {"type": "STRING"},
            "detail_address": {"type": "STRING", "nullable": True},
            "deposit": {"type": "INTEGER", "nullable": True},
            "monthly_rent": {"type": "INTEGER", "nullable": True},
            "application_start_date": {"type": "STRING", "nullable": True},
            "application_end_date": {"type": "STRING", "nullable": True},
            "description": {"type": "STRING"},
            "source_url": {"type": "STRING", "nullable": True},
            "page": {"type": "INTEGER", "nullable": True},
        },
        "required": ["title", "housing_name", "location", "description"],
    },
}


def extract_listings_from_pdf(pdf_bytes: bytes, filename: str = "notice.pdf") -> list:
    """공고 PDF에서 청약정보 목록을 뽑아냅니다.

    돌려주는 값은 사전들의 목록입니다. 확인은 core.listing_extract가 맡습니다.
    """

    api_key = get_api_key()
    if not api_key:
        raise GeminiError(
            "Gemini API 키가 없습니다. FE_Admin/.env에 GEMINI_API_KEY를 넣어 주세요."
        )

    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise GeminiError(
            "google-genai 패키지가 설치되어 있지 않습니다. "
            "FE_Admin/requirements.txt를 설치해 주세요."
        ) from error

    client = genai.Client(api_key=api_key)

    # 파일 형식에 따라 보내는 방법이 다릅니다.
    #   PDF  - 파일을 그대로 보냅니다. 표 모양까지 함께 보아 더 정확하고,
    #          토큰도 적게 듭니다(재 보니 PDF 28,001 / 글자만 40,226).
    #   HWPX - Gemini가 모르는 형식이라 그대로 보내면 400으로 거절합니다.
    #          글자를 먼저 꺼내 글로 보냅니다.
    from core.document_images import is_hwpx
    from core.document_text import extract_text

    if is_hwpx(filename):
        try:
            text = extract_text(pdf_bytes, filename)
        except Exception as error:
            raise GeminiError(
                f"HWPX 파일에서 글자를 꺼내지 못했습니다. ({type(error).__name__})"
            ) from error
        if not text.strip():
            raise GeminiError("HWPX 파일에서 읽을 수 있는 글자를 찾지 못했습니다.")
        part = f"아래는 공고문 전체 글입니다.\n\n{text}"
    else:
        part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

    last_error: Exception | None = None

    # 서버가 붐비면 잠깐 기다렸다가 다시 시도합니다.
    for attempt, wait in enumerate((0,) + RETRY_WAITS):
        if wait:
            time.sleep(wait)
        try:
            response = client.models.generate_content(
                model=get_model_name(),
                contents=[part, EXTRACT_PROMPT],
                config={
                    "response_mime_type": "application/json",
                    "response_schema": EXTRACT_SCHEMA,
                },
            )
            return parse_extract_response((response.text or "").strip())
        except Exception as error:
            last_error = error
            if not _should_retry(error):
                break

    raise GeminiError(describe_call_error(last_error, api_key)) from last_error


IDENTIFY_PROMPT = """각 사진을 보고 아래를 알려 주세요. 사진 순서대로 배열로 답하세요.

- house_name: 사진에 글자로 적혀 있는 주택 이름.
  지도라면 지도 위에 표시된 주택명입니다.
  적혀 있지 않으면 null 로 두세요. 추측하지 마세요.
- kind: 사진 종류. "위치도" "평면도" "외관" "실내" "주차장" "안내그림" "로고" 중 하나.

사진에 적힌 글자만 근거로 삼으세요. 사진에 없는 이름을 지어내지 마세요."""

IDENTIFY_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "house_name": {"type": "STRING", "nullable": True},
            "kind": {"type": "STRING"},
        },
        "required": ["kind"],
    },
}


def image_mime_type(image: dict) -> str:
    """추출 단계가 확인한 실제 MIME 형식을 Gemini 요청에 사용합니다.

    이전 실행에서 세션에 남은 이미지처럼 mime_type이 없는 경우에는
    파일 확장자로 추정하고, 그것도 알 수 없을 때만 PNG로 처리합니다.
    """

    detected = str(image.get("mime_type") or "").strip().lower()
    if detected.startswith("image/"):
        return detected

    name = str(image.get("name") or "")
    known = IMAGE_MIME_TYPES.get(Path(name).suffix.lower())
    if known:
        return known

    guessed, _ = mimetypes.guess_type(name)
    if guessed and guessed.startswith("image/"):
        return guessed
    return "image/png"


def identify_images(images: list) -> list[dict]:
    """사진마다 어느 주택 것인지, 무슨 사진인지 알아냅니다.

    지도에는 주택명이 글자로 찍혀 있습니다. 쪽 번호만으로는
    한 쪽에 지도가 두 장 있을 때 구분할 수 없어, 사진 속 글자를 읽게 합니다.

    돌려주는 값은 사진과 같은 순서의 목록입니다.
      house_name - 사진에 적힌 주택 이름 (없으면 빈 문자열)
      kind       - 사진 종류

    실패해도 오류를 내지 않고 빈 값을 돌려줍니다.
    사진 짝짓기는 없어도 등록할 수 있는 편의 기능이라,
    이것 때문에 자동 추출 전체가 멈추면 안 됩니다.
    """

    blank = [{"house_name": "", "kind": ""} for _ in images or []]
    if not images:
        return []

    api_key = get_api_key()
    if not api_key:
        return blank

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return blank

    try:
        client = genai.Client(api_key=api_key)
        parts = [
            types.Part.from_bytes(
                data=image["data"],
                mime_type=image_mime_type(image),
            )
            for image in images
        ]
        response = client.models.generate_content(
            model=get_model_name(),
            contents=parts + [IDENTIFY_PROMPT],
            config={
                "response_mime_type": "application/json",
                "response_schema": IDENTIFY_SCHEMA,
            },
        )
        parsed = parse_extract_response((response.text or "").strip())
    except Exception:
        return blank

    result = []
    for index in range(len(images)):
        item = parsed[index] if index < len(parsed) and isinstance(parsed[index], dict) else {}
        result.append(
            {
                "house_name": (item.get("house_name") or "").strip(),
                "kind": (item.get("kind") or "").strip(),
            }
        )
    return result




def parse_extract_response(text: str) -> list:
    """모델이 돌려준 문자열에서 JSON 배열을 꺼냅니다.

    앞뒤에 코드 블록 표시가 붙어 오는 경우가 있어 걷어냅니다.
    """

    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3]
        cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    if not cleaned:
        raise GeminiError("Gemini가 빈 응답을 돌려주었습니다.")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise GeminiError("Gemini 응답을 JSON으로 읽을 수 없습니다.") from error

    if isinstance(parsed, dict):
        # {"listings": [...]} 형태로 올 수도 있어 배열을 찾아 씁니다.
        for value in parsed.values():
            if isinstance(value, list):
                return value
        return [parsed]

    if not isinstance(parsed, list):
        raise GeminiError("Gemini 응답이 목록 형태가 아닙니다.")

    return parsed
