# image_service.py
"""청약정보 이미지를 Supabase Storage에 저장합니다."""

import uuid

from fastapi import HTTPException, UploadFile

from app.core.log_store import add_log
from app.core.supabase_config import get_supabase
from app.core.upload_config import (
    ALLOWED_IMAGE_TYPES,
    EXTENSION_BY_IMAGE_TYPE,
    MAX_IMAGE_COUNT,
    MAX_IMAGE_SIZE,
    MAX_TOTAL_UPLOAD_SIZE,
    STORAGE_BUCKET,
)


def detect_image_type(content: bytes) -> str | None:
    """파일 앞부분(매직 넘버)을 보고 실제 이미지 종류를 알아냅니다.

    확장자나 MIME 타입은 이름만 바꿔도 속일 수 있습니다.
    실제 이미지 파일은 정해진 바이트로 시작하므로 그 값을 직접 확인합니다.
    """

    # JPEG는 FF D8 FF로 시작합니다.
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PNG는 89 50 4E 47 0D 0A 1A 0A로 시작합니다.
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # WEBP는 RIFF로 시작하고 9~12번째 바이트가 WEBP입니다.
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"

    return None


async def upload_listing_image(image: UploadFile) -> str:
    """이미지를 검사한 뒤 Storage에 올리고 공개 URL을 반환합니다."""

    if image is None or not image.filename:
        raise HTTPException(status_code=400, detail="이미지 파일을 선택해 주세요.")

    content = await image.read()

    # 1. 크기 검사
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")

    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"이미지 크기는 5MB를 넘을 수 없습니다. (선택한 파일: {len(content) / 1024 / 1024:.1f}MB)",
        )

    # 2. 브라우저가 보낸 MIME 타입 검사
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="JPG, PNG, WEBP 형식의 이미지만 업로드할 수 있습니다.",
        )

    # 3. 실제 파일 내용 검사 (확장자만 바꾼 파일을 걸러냅니다)
    actual_image_type = detect_image_type(content)
    if actual_image_type is None:
        raise HTTPException(
            status_code=400,
            detail="이미지 파일이 아닙니다. 확장자만 바꾼 파일은 업로드할 수 없습니다.",
        )

    # 4. 겹치지 않는 파일 이름을 만듭니다. 확장자는 실제 종류를 따릅니다.
    extension = EXTENSION_BY_IMAGE_TYPE[actual_image_type]
    storage_path = f"{uuid.uuid4().hex}{extension}"

    # 5. Storage에 올립니다.
    supabase = get_supabase()
    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            content,
            {"content-type": actual_image_type},
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"이미지 저장에 실패했습니다. ({error})",
        ) from error

    # 6. 화면에서 바로 열 수 있는 공개 URL을 돌려줍니다.
    #    supabase-py는 URL 끝에 빈 물음표를 붙이므로 떼어내고 저장합니다.
    public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
    return public_url.rstrip("?")


async def upload_listing_images(images: list[UploadFile]) -> list[str]:
    """사진 여러 장을 올리고 공개 URL을 순서대로 돌려줍니다.

    한 장이라도 실패하면 이미 올라간 파일을 도로 지웁니다.
    5장 중 4장을 올리고 실패하면, 그냥 두었을 때 주인 없는 파일 4개가
    Storage에 영영 남기 때문입니다.

    되돌리다가 또 실패해도 원래 오류를 그대로 올려보냅니다.
    화면에는 "왜 등록이 안 됐는지"가 더 중요합니다.
    """

    selected = [image for image in (images or []) if image is not None and image.filename]

    if not selected:
        return []

    if len(selected) > MAX_IMAGE_COUNT:
        raise HTTPException(
            status_code=400,
            detail=f"사진은 최대 {MAX_IMAGE_COUNT}장까지 올릴 수 있습니다. "
            f"(선택한 파일: {len(selected)}장)",
        )

    # 한 장씩은 5MB를 넘지 않아도, 여러 장을 합치면 요청이 너무 커질 수 있습니다.
    # 올리기 시작하기 전에 미리 막아, 중간에 끊기는 일을 줄입니다.
    # size를 알 수 없는 경우가 있어 아는 것만 더합니다.
    total_size = sum(image.size or 0 for image in selected)
    if total_size > MAX_TOTAL_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"한 번에 올릴 수 있는 전체 크기는 "
            f"{MAX_TOTAL_UPLOAD_SIZE // 1024 // 1024}MB입니다. "
            f"(선택한 파일: {total_size / 1024 / 1024:.1f}MB) "
            f"나눠서 올려 주세요.",
        )

    uploaded: list[str] = []
    try:
        for image in selected:
            uploaded.append(await upload_listing_image(image))
    except Exception:
        # 이미 올라간 파일을 되돌립니다.
        # 아직 DB에 넣기 전이라 다른 공고가 쓸 수 없는 파일들입니다.
        for image_url in uploaded:
            delete_listing_image(image_url)
        raise

    return uploaded


def is_image_still_used(image_url: str) -> bool:
    """다른 공고가 아직 이 이미지를 쓰고 있는지 확인합니다.

    이 함수는 DB에서 참조를 지운 뒤에 호출됩니다. 그래도 행이 남아 있다면
    다른 공고가 같은 파일을 함께 쓰고 있다는 뜻이므로 파일을 지우면 안 됩니다.

    참조는 두 곳에 있습니다.
      * listings.image_url        - 목록 카드에 보여 줄 대표 이미지
      * listing_images.image_url  - 공고에 붙은 사진 전부

    두 곳을 모두 확인해야 합니다. 한 곳만 보면, 공고 A의 추가 사진이
    공고 B의 대표 사진과 같은 파일일 때 아직 쓰이는 파일을 지워 버립니다.
    Storage에서 지운 파일은 되돌릴 수 없습니다.

    확인하다가 오류가 나면 "쓰이고 있다"로 봅니다. 잘못 지워 되돌릴 수 없는 것보다
    쓰이지 않는 파일이 남는 편이 안전하기 때문입니다.
    """

    supabase = get_supabase()

    for table, column in (("listings", "image_url"), ("listing_images", "image_url")):
        try:
            result = (
                supabase.table(table)
                .select("id")
                .eq(column, image_url)
                .limit(1)
                .execute()
            )
        except Exception as error:
            add_log(
                "warning",
                "image_service",
                f"{table} 이미지 참조 확인에 실패해 삭제하지 않았습니다. "
                f"({type(error).__name__})",
                0,
            )
            return True

        if result.data:
            return True

    return False


def delete_listing_image(image_url: str | None) -> None:
    """Storage에 올린 이미지를 지웁니다.

    공고를 지우거나 이미지를 바꿀 때 예전 파일이 남지 않게 합니다.
    반드시 DB에서 참조를 지운 뒤에 호출해야 합니다.
    """

    if not image_url:
        return

    # 우리 버킷에 올린 이미지가 아니면 건드리지 않습니다.
    # 나중에 다른 사이트의 이미지 주소를 그대로 저장하는 경우를 대비한 안전장치입니다.
    bucket_marker = f"/{STORAGE_BUCKET}/"
    if bucket_marker not in image_url:
        return

    # URL 뒤쪽에서 파일 이름만 잘라냅니다.
    # .../listing-images/abc123.png -> abc123.png
    storage_path = image_url.split(bucket_marker, 1)[1].split("?")[0]
    if not storage_path:
        return

    # 같은 파일을 다른 공고도 쓰고 있으면 지우지 않습니다.
    if is_image_still_used(image_url):
        return

    # 이미 DB에서 지운 뒤에 호출되므로, 파일 삭제가 실패해도 요청은 실패시키지 않습니다.
    # 다만 조용히 넘기면 DB와 Storage가 어긋난 것을 아무도 모르게 되므로,
    # 서버 로그와 관리자 로그 화면에 모두 남깁니다.
    try:
        get_supabase().storage.from_(STORAGE_BUCKET).remove([storage_path])
    except Exception as error:
        message = f"이미지 삭제 실패: {storage_path} ({type(error).__name__}: {error})"
        print(f"[image_service] {message}")
        add_log("error", "image_service", message, 0)
