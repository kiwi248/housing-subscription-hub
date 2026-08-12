# document_text.py
"""공고 파일에서 글자를 꺼냅니다.

HWPX 때문에 필요합니다.
Gemini는 PDF를 그대로 읽을 수 있지만 HWPX는 모릅니다.
PDF인 척 보내면 400 INVALID_ARGUMENT 로 거절합니다.
그래서 HWPX는 글자를 먼저 꺼내 글로 보냅니다.

HWPX는 이름만 다른 ZIP 파일이라 표준 라이브러리만 있으면 됩니다.

Streamlit이나 Gemini에 기대지 않아 테스트하기 쉽습니다.
"""

import io
import re
import zipfile

# HWPX 본문이 들어 있는 자리입니다.
HWPX_CONTENT_DIR = "Contents/"

# 본문 글자는 <hp:t> 태그 안에 들어 있습니다.
_TEXT_TAG = re.compile(r"<hp:t[^>]*>(.*?)</hp:t>", re.S)
_ANY_TAG = re.compile(r"<[^>]+>")

# 한글 문서에서 자주 나오는 특수 문자입니다. 글자로 바꿔 둡니다.
_ENTITIES = {
    "&lt;": "<",
    "&gt;": ">",
    "&amp;": "&",
    "&quot;": '"',
    "&apos;": "'",
    "&#13;": "\n",
}


def unescape(text: str) -> str:
    """XML에서 문자로 바꿔 둔 기호를 되돌립니다."""

    for mark, real in _ENTITIES.items():
        text = text.replace(mark, real)
    return text


def extract_text_from_hwpx(data: bytes) -> str:
    """HWPX에서 본문 글자를 꺼냅니다.

    문단이 나뉘는 자리를 줄바꿈으로 바꿔, 표의 칸이 서로 붙지 않게 합니다.
    붙어 버리면 어디까지가 한 칸인지 알 수 없어 값을 잘못 읽습니다.
    """

    parts: list[str] = []

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.startswith(HWPX_CONTENT_DIR) and name.endswith(".xml")
        )
        for name in names:
            raw = archive.read(name).decode("utf-8", "ignore")
            for chunk in _TEXT_TAG.findall(raw):
                text = unescape(_ANY_TAG.sub("", chunk)).strip()
                if text:
                    parts.append(text)

    return "\n".join(parts)


def extract_text(data: bytes, filename: str) -> str:
    """파일에서 글자를 꺼냅니다. HWPX만 지원합니다.

    PDF는 글자를 꺼내지 않습니다. Gemini에 파일을 그대로 보내는 편이
    표 모양까지 함께 볼 수 있어 더 정확하고 토큰도 적게 듭니다.
    실제로 재 보니 PDF 28,001 토큰, 글자만 40,226 토큰이었습니다.
    """

    from core.document_images import is_hwpx

    if is_hwpx(filename):
        return extract_text_from_hwpx(data)
    raise ValueError("글자를 꺼낼 수 있는 형식이 아닙니다.")
