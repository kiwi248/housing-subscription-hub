# image_gallery.py
"""공고 사진을 여러 장 보여 줄 때 쓰는 규칙입니다.

관리자 화면과 같은 내용이지만 앱마다 모듈이 따로 있어 각자 둡니다.

사진이 스무 장까지 올 수 있어, 한 줄에 몇 장씩 끊어 놓을지 정합니다.
사진이 한 장뿐이면 굳이 나누지 않고 크게 보여 줍니다.

Streamlit에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

# 공고 하나에 붙일 수 있는 사진 수입니다. 백엔드에서도 같은 값으로 다시 검사합니다.
MAX_IMAGE_COUNT = 20

# 한 장에 5MB, 한 번에 60MB까지입니다. 역시 백엔드에서 다시 검사합니다.
MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_TOTAL_UPLOAD_SIZE = 60 * 1024 * 1024


def image_list(listing: dict) -> list[str]:
    """공고에 붙은 사진 URL을 순서대로 꺼냅니다.

    새 테이블을 만들기 전에 등록된 공고는 images가 비어 있고
    대표 이미지만 있습니다. 그런 공고도 한 장짜리 목록으로 돌려주어
    사진이 아예 없는 것처럼 보이지 않게 합니다.
    """

    images = listing.get("images")
    urls = [str(url) for url in images if url] if isinstance(images, list) else []

    if not urls and listing.get("image_url"):
        urls = [str(listing["image_url"])]

    return urls


def rows_of(images: list[str], per_row: int = 4) -> list[list[str]]:
    """사진을 한 줄에 몇 장씩 끊어 놓습니다.

    사진이 한 장이면 나누지 않습니다. 한 칸짜리 줄을 만들면
    화면 폭의 4분의 1만 쓰게 되어 오히려 작게 보입니다.
    """

    if not images:
        return []

    if len(images) == 1:
        return [[images[0]]]

    per_row = max(1, per_row)
    return [images[start : start + per_row] for start in range(0, len(images), per_row)]


def count_label(images: list[str]) -> str:
    """사진이 몇 장인지 알려 주는 문구입니다."""

    return f"사진 {len(images)}장" if images else ""


def describe_size(total_bytes: int) -> str:
    """올린 파일의 전체 크기를 읽기 쉽게 바꿉니다."""

    return f"{total_bytes / 1024 / 1024:.1f}MB"


def check_upload(files: list, already: int = 0) -> str:
    """올려도 되는지 확인하고, 안 되면 그 이유를 돌려줍니다.

    문제가 없으면 빈 문구입니다.
    백엔드에서도 같은 값으로 다시 검사하지만, 여기서 먼저 막아 주면
    수십 MB를 다 보낸 뒤에 거절당하는 일을 줄일 수 있습니다.
    """

    if not files:
        return ""

    total_count = already + len(files)
    if total_count > MAX_IMAGE_COUNT:
        return (
            f"사진은 최대 {MAX_IMAGE_COUNT}장까지입니다. "
            f"(이미 {already}장 + 새로 {len(files)}장 = {total_count}장)"
        )

    too_big = [file.name for file in files if getattr(file, "size", 0) > MAX_IMAGE_SIZE]
    if too_big:
        return f"한 장에 5MB를 넘을 수 없습니다. ({', '.join(too_big[:3])})"

    total_size = sum(getattr(file, "size", 0) for file in files)
    if total_size > MAX_TOTAL_UPLOAD_SIZE:
        return (
            f"한 번에 올릴 수 있는 전체 크기는 "
            f"{MAX_TOTAL_UPLOAD_SIZE // 1024 // 1024}MB입니다. "
            f"(선택한 파일: {describe_size(total_size)}) 나눠서 올려 주세요."
        )

    return ""
