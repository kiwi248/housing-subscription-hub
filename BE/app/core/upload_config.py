# upload_config.py
"""청약정보 이미지 업로드에 사용하는 설정값입니다."""

# Supabase Storage에 만들어 둔 버킷 이름입니다.
# Public 버킷이라 저장된 이미지 URL을 화면에서 바로 열 수 있습니다.
STORAGE_BUCKET = "listing-images"

# 최대 이미지 크기입니다. 5MB를 넘으면 업로드를 막습니다.
MAX_IMAGE_SIZE = 5 * 1024 * 1024

# 공고 하나에 붙일 수 있는 사진 수입니다.
# 실제 공고를 보면 주택 내부와 주변 시설까지 20장 가까이 됩니다.
MAX_IMAGE_COUNT = 20

# 한 번에 올릴 수 있는 전체 크기입니다.
#
# 장수만 막으면 20장 × 5MB = 100MB가 한 요청에 실립니다.
# 그만한 요청은 올리다 끊기거나 시간이 초과되기 쉽고,
# 끊기면 이미 올라간 파일만 남습니다.
# 사진 20장을 올리더라도 보통 한 장에 2~3MB이므로 60MB면 넉넉합니다.
MAX_TOTAL_UPLOAD_SIZE = 60 * 1024 * 1024

# 허용하는 이미지 종류입니다. 버킷에 설정한 MIME 목록과 같게 맞춥니다.
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

# 파일 이름을 만들 때 사용할 확장자입니다.
EXTENSION_BY_IMAGE_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
