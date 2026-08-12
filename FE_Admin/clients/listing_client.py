from typing import Any

from core.api_client import UPLOAD_TIMEOUT, request


def create_listing(listing: dict[str, Any]):
    return request("POST", "/admin/listings/create", json=listing)


def upload_listing_image(image: Any):
    files = {
        "image": (
            image.name,
            image.getvalue(),
            image.type or "application/octet-stream",
        )
    }
    return request("POST", "/admin/listings/images", files=files)


def upload_listing_images(images: list[Any]):
    """사진 여러 장을 한 번에 올립니다.

    한 장씩 여러 번 부르지 않는 이유가 있습니다.
    도중에 실패하면 이미 올라간 파일을 도로 지워야 하는데,
    한 번에 보내면 그 정리를 백엔드가 맡아 줍니다.

    같은 이름("images")으로 여러 개를 보내야 해서 목록으로 만듭니다.
    """

    files = [
        (
            "images",
            (image.name, image.getvalue(), image.type or "application/octet-stream"),
        )
        for image in images
    ]
    return request(
        "POST", "/admin/listings/images/bulk", files=files, timeout=UPLOAD_TIMEOUT
    )


def replace_listing_images(listing_id: int, kept_image_urls: list[str], images: list[Any]):
    """공고의 사진 목록을 새로 씁니다.

    공고 수정과 따로 부릅니다. 관리자가 입력만 해 두고 아직 저장하지 않은
    제목·금액 같은 값이 사진을 정리할 때 함께 저장되지 않게 하려는 것입니다.
    """

    files = [
        (
            "images",
            (image.name, image.getvalue(), image.type or "application/octet-stream"),
        )
        for image in images
    ]
    # 같은 이름으로 여러 개를 보낼 때는 사전에 목록을 담아야 합니다.
    # [("kept_image_urls", url), ...] 처럼 목록으로 넘기면 httpx가 이것을
    # 폼 값이 아니라 본문 그 자체로 보아, 서버에 값이 하나도 가지 않습니다.
    # 그러면 서버는 "남길 사진 없음"으로 알아듣고 사진을 전부 지웁니다.
    # 몇 장을 남길 셈인지 함께 보냅니다. 서버가 도착한 개수와 맞춰 보고,
    # 다르면 아무것도 지우지 않습니다.
    data = {
        "kept_image_urls": list(kept_image_urls),
        "keep_count": len(kept_image_urls),
    }
    return request(
        "PUT",
        f"/admin/listings/{listing_id}/images",
        data=data,
        files=files or None,
        timeout=UPLOAD_TIMEOUT,
    )


def get_listings():
    return request("GET", "/listings/getall")


def get_listings_page(page: int, page_size: int = 10, sort: str | None = None):
    # 전체를 받아 오지 않고 필요한 페이지만 가져옵니다.
    # 정렬도 백엔드에 맡깁니다. 받은 10건만 다시 늘어놓으면
    # 전체 기준의 순서가 아니라 그 페이지 안에서만 뒤바뀌기 때문입니다.
    params = {"page": page, "page_size": page_size}
    if sort:
        params["sort"] = sort
    return request("GET", "/listings/page", params=params)


def get_listing(listing_id: int):
    return request("GET", f"/listings/get/{listing_id}")


def search_listings(params: dict[str, Any]):
    return request("GET", "/listings/search", params=params)


def update_listing(listing_id: int, listing: dict[str, Any], image: Any = None):
    # 이미지가 함께 갈 수 있어 등록과 달리 multipart 방식으로 보냅니다.
    files = None
    if image is not None:
        files = {
            "image": (
                image.name,
                image.getvalue(),
                image.type or "application/octet-stream",
            )
        }
    return request(
        "PUT",
        f"/admin/listings/update/{listing_id}",
        data=listing,
        files=files,
    )


def delete_listing(listing_id: int):
    return request("DELETE", f"/admin/listings/delete/{listing_id}")


def delete_listing_image(listing_id: int):
    # 공고 id만 보냅니다. 수정 폼에 입력해 둔 값은 함께 보내지 않습니다.
    return request("DELETE", f"/admin/listings/{listing_id}/image")
