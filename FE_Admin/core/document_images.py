# document_images.py
"""공고 파일에서 사진을 꺼냅니다.

AI를 쓰지 않습니다. 파일 안에 이미 들어 있는 그림 파일을 그대로 꺼내는 일입니다.
어떤 사진인지 알아보는 일은 Gemini가 따로 맡습니다.

형식마다 꺼내는 방법이 다릅니다.
  PDF  - pypdf 로 쪽마다 그림을 읽습니다.
  HWPX - 사실 ZIP 파일이라 BinData 폴더를 그대로 꺼내면 됩니다.
         표준 라이브러리만 있으면 되고 화질도 원본 그대로입니다.

Streamlit에 기대지 않아 테스트하기 쉽습니다.
"""

import io
import zipfile
from pathlib import Path

# 사진으로 볼 최소 크기입니다.
# 이보다 작은 그림은 로고, 아이콘, 표 장식선 같은 것들입니다.
MIN_WIDTH = 200
MIN_HEIGHT = 150
MIN_BYTES = 8 * 1024

# 한 파일에서 꺼낼 최대 장수입니다. 공고 하나에 붙일 수 있는 수와 맞춥니다.
MAX_IMAGES = 20

# HWPX 안에서 그림이 들어 있는 폴더입니다.
HWPX_IMAGE_DIR = "BinData/"

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")

# 백엔드 이미지 업로드 API가 받는 형식과 맞춥니다.
UPLOAD_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


def is_hwpx(filename: str) -> bool:
    return Path(filename or "").suffix.lower() == ".hwpx"


def is_pdf(filename: str) -> bool:
    return Path(filename or "").suffix.lower() == ".pdf"


def looks_like_photo(width: int, height: int, size_bytes: int, mode: str = "") -> bool:
    """공고 사진으로 쓸 만한 그림인지 봅니다.

    걸러 내는 것은 세 가지입니다.
      * 투명도 마스크 - 실제 그림이 아니라 어디를 비출지 적어 둔 흑백 판입니다.
      * 너무 작은 그림 - 로고, 아이콘, 표 장식선입니다.
      * 용량이 너무 작은 그림 - 거의 단색이라 사진일 수 없습니다.

    여기서는 넉넉하게 걸러 냅니다. 무엇을 찍은 사진인지는 Gemini가 보고 정하고,
    마지막에는 사람이 고릅니다. 여기서 너무 깐깐하게 걸러 내면
    정작 필요한 사진이 후보에 오르지도 못합니다.
    """

    if mode == "1":
        return False
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        return False
    return size_bytes >= MIN_BYTES


def _describe(data: bytes) -> tuple[int, int, str, str]:
    """그림의 크기·색 방식·MIME 형식을 알아냅니다."""

    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as image:
            return image.width, image.height, image.mode, image.get_format_mimetype()
    except Exception:
        return 0, 0, "", ""


def normalize_for_upload(data: bytes, name: str, mime_type: str) -> tuple[bytes, str, str]:
    """백엔드가 받지 않는 그림을 JPEG 또는 PNG로 바꿉니다.

    GIF는 움직이는 여러 장 중 첫 장만 공고 사진 후보로 사용하고 PNG로 저장합니다.
    BMP 등 불투명 그림은 용량을 줄이기 위해 JPEG로 저장합니다. 투명도가 있으면
    배경이 사라지지 않도록 PNG를 사용합니다.
    """

    if mime_type in UPLOAD_IMAGE_TYPES:
        return data, name, mime_type

    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        image.seek(0)
        output = io.BytesIO()
        has_alpha = "A" in image.mode or "transparency" in image.info

        if mime_type == "image/gif" or has_alpha:
            converted = image.convert("RGBA" if has_alpha else "RGB")
            converted.save(output, format="PNG", optimize=True)
            return output.getvalue(), str(Path(name).with_suffix(".png")), "image/png"

        converted = image.convert("RGB")
        converted.save(output, format="JPEG", quality=90, optimize=True)
        return output.getvalue(), str(Path(name).with_suffix(".jpg")), "image/jpeg"


def extract_from_pdf(data: bytes) -> list[dict]:
    """PDF에서 사진을 꺼냅니다. 몇 쪽에서 나왔는지도 함께 남깁니다."""

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    found: list[dict] = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            images = list(page.images)
        except Exception:
            # 한 쪽을 못 읽어도 나머지는 계속 꺼냅니다.
            continue

        for order, item in enumerate(images, start=1):
            raw = item.data
            width, height, mode, mime_type = _describe(raw)
            if not looks_like_photo(width, height, len(raw), mode):
                continue
            name = f"p{page_number:03d}_{order}{Path(item.name or '').suffix or '.png'}"
            raw, name, mime_type = normalize_for_upload(raw, name, mime_type)
            found.append(
                {
                    "name": name,
                    "data": raw,
                    "width": width,
                    "height": height,
                    "page": page_number,
                    "mime_type": mime_type,
                }
            )

    return found[:MAX_IMAGES]


def extract_from_hwpx(data: bytes) -> list[dict]:
    """HWPX에서 사진을 꺼냅니다.

    HWPX는 이름만 다른 ZIP 파일입니다. BinData 폴더에 그림이 그대로 들어 있어
    따로 해석할 것이 없습니다. 쪽 번호는 알 수 없어 문서에 담긴 순서를 씁니다.
    """

    found: list[dict] = []

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [
            name
            for name in archive.namelist()
            if name.startswith(HWPX_IMAGE_DIR)
            and name.lower().endswith(IMAGE_SUFFIXES)
        ]

        # image2 가 image10 보다 앞에 오도록 이름 속 숫자로 늘어놓습니다.
        names.sort(key=_hwpx_order)

        for order, name in enumerate(names, start=1):
            raw = archive.read(name)
            width, height, mode, mime_type = _describe(raw)
            if not looks_like_photo(width, height, len(raw), mode):
                continue
            raw, upload_name, mime_type = normalize_for_upload(
                raw,
                Path(name).name,
                mime_type,
            )
            found.append(
                {
                    "name": upload_name,
                    "data": raw,
                    "width": width,
                    "height": height,
                    "page": None,
                    "order": order,
                    "mime_type": mime_type,
                }
            )

    return found[:MAX_IMAGES]


def _hwpx_order(name: str) -> tuple:
    """"image10" 이 "image2" 보다 뒤에 오도록 숫자를 떼어 냅니다."""

    stem = Path(name).stem
    digits = "".join(ch for ch in stem if ch.isdigit())
    return (int(digits) if digits else 0, stem)


def extract_images(data: bytes, filename: str) -> list[dict]:
    """파일 형식에 맞게 사진을 꺼냅니다.

    돌려주는 값은 사전들의 목록입니다.
      name   - 올릴 때 쓸 파일 이름
      data   - 그림 내용
      width  - 가로 픽셀
      height - 세로 픽셀
      page   - 몇 쪽에서 나왔는지 (HWPX는 None)
      mime_type - 실제 그림 형식 (예: image/jpeg)
    """

    if is_hwpx(filename):
        return extract_from_hwpx(data)
    if is_pdf(filename):
        return extract_from_pdf(data)
    raise ValueError("PDF와 HWPX 파일만 읽을 수 있습니다.")
