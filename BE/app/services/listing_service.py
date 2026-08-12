# listing_service.py
from datetime import date

from app.core.supabase_config import get_supabase
from app.schemas.listing_schema import ListingCreate, ListingPage, ListingPublic

# 목록을 페이지로 나눌 때 쓰는 값입니다.
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# 화면에서 고를 수 있는 정렬 기준입니다.
# 이름 -> (정렬에 쓸 컬럼, 내림차순 여부)
# 정렬을 화면에서 하지 않고 여기서 하는 이유가 있습니다.
# 관리자 목록은 한 번에 한 페이지(10건)만 받아 가는데,
# 받은 10건만 다시 늘어놓으면 전체 기준의 순서가 아니기 때문입니다.
SORT_COLUMNS = {
    "created_desc": ("created_at", True),
    "end_date_asc": ("application_end_date", False),
    "area_desc": ("area_sqm", True),
    "area_asc": ("area_sqm", False),
    "recruitment_desc": ("recruitment_count", True),
    "recruitment_asc": ("recruitment_count", False),
    "deposit_desc": ("deposit", True),
    "deposit_asc": ("deposit", False),
    "rent_desc": ("monthly_rent", True),
    "rent_asc": ("monthly_rent", False),
}


def apply_sort(query, sort: str | None):
    """고른 기준으로 정렬을 붙입니다.

    값이 비어 있는 공고는 어떤 기준이든 맨 뒤로 보냅니다(nullsfirst=False).
    같은 값끼리는 나중에 등록한 공고를 앞에 두어 순서가 흔들리지 않게 합니다.
    """

    column, desc = SORT_COLUMNS[sort]
    return query.order(column, desc=desc, nullsfirst=False).order("id", desc=True)


def is_known_sort(sort: str | None) -> bool:
    """화면이 보낸 정렬 기준을 아는지 확인합니다."""

    return sort in SORT_COLUMNS


# 사진은 listing_images 테이블에 따로 있어 조회할 때 함께 읽어 옵니다.
# favorite_service의 "*, listing:listings(*)"와 같은 방식입니다.
LISTING_SELECT = "*, listing_images(image_url, sort_order)"


def to_listing(row: dict) -> ListingPublic:
    """DB에서 읽은 한 줄을 화면용 값으로 바꿉니다.

    함께 읽어 온 사진을 sort_order 순으로 늘어놓아 images에 담습니다.

    사진 테이블이 비어 있고 대표 이미지만 있는 공고가 있습니다.
    새 테이블을 만들기 전에 등록된 공고들입니다.
    그런 공고는 대표 이미지 한 장을 목록으로 만들어, 상세보기에서
    사진이 아예 없는 것처럼 보이지 않게 합니다.
    """

    # 원본을 건드리지 않도록 복사해서 씁니다.
    data = dict(row)
    rows = data.pop("listing_images", None) or []

    rows.sort(key=lambda item: item.get("sort_order") or 0)
    images = [item["image_url"] for item in rows if item.get("image_url")]

    if not images and data.get("image_url"):
        images = [data["image_url"]]

    data["images"] = images
    return ListingPublic.model_validate(data)


def listing_images_get(listing_id: int) -> list[str]:
    """공고에 붙은 사진 URL을 순서대로 돌려줍니다."""

    result = (
        get_supabase()
        .table("listing_images")
        .select("image_url, sort_order")
        .eq("listing_id", listing_id)
        .order("sort_order")
        .execute()
    )
    return [row["image_url"] for row in result.data if row.get("image_url")]


def listing_images_replace(listing_id: int, image_urls: list[str]) -> None:
    """공고의 사진 목록을 통째로 새로 씁니다.

    기존 행을 지우고 받은 순서대로 다시 넣습니다.
    sort_order 0이 대표 이미지이며 listings.image_url과 같은 값입니다.

    Storage 파일은 여기서 지우지 않습니다. 어떤 파일을 지워도 되는지는
    다른 공고가 쓰고 있는지 확인한 뒤에 정해야 하기 때문입니다.
    """

    supabase = get_supabase()
    supabase.table("listing_images").delete().eq("listing_id", listing_id).execute()

    if not image_urls:
        return

    supabase.table("listing_images").insert(
        [
            {"listing_id": listing_id, "image_url": url, "sort_order": order}
            for order, url in enumerate(image_urls)
        ]
    ).execute()


def split_image_urls(listing: ListingCreate) -> tuple[dict, list[str]]:
    """저장할 값에서 사진 목록을 떼어 냅니다.

    image_urls는 listings 테이블에 없는 칸입니다. 그대로 보내면
    "그런 컬럼이 없다"며 저장이 실패하므로 따로 빼서 돌려줍니다.

    mode="json"으로 바꾸면 date는 "2026-08-07", Decimal은 "39.72" 같은
    문자열이 되어 Supabase가 그대로 받을 수 있습니다.
    """

    listing_data = listing.model_dump(mode="json")
    image_urls = listing_data.pop("image_urls", None) or []
    return listing_data, image_urls


def listing_create(listing: ListingCreate) -> ListingPublic | None:
    supabase = get_supabase()

    listing_data, image_urls = split_image_urls(listing)

    result = (
        supabase.table("listings")
        .insert(listing_data)
        .execute()
    )
    if not result.data:
        return None

    created = result.data[0]
    # 공고가 만들어진 뒤에야 id를 알 수 있어, 사진은 그다음에 넣습니다.
    listing_images_replace(created["id"], image_urls)
    created["listing_images"] = [
        {"image_url": url, "sort_order": order} for order, url in enumerate(image_urls)
    ]
    return to_listing(created)


def listing_update(listing_id: int, listing: ListingCreate) -> ListingPublic | None:
    supabase = get_supabase()

    listing_data, image_urls = split_image_urls(listing)

    result = (
        supabase.table("listings")
        .update(listing_data)
        .eq("id", listing_id)
        .execute()
    )
    if not result.data:
        return None

    updated = result.data[0]
    listing_images_replace(listing_id, image_urls)
    updated["listing_images"] = [
        {"image_url": url, "sort_order": order} for order, url in enumerate(image_urls)
    ]
    return to_listing(updated)


def listing_clear_image(listing_id: int) -> ListingPublic | None:
    """공고에서 이미지 참조만 지웁니다.

    image_url 한 칸만 건드립니다. 제목이나 금액 같은 다른 값은 보내지 않으므로,
    관리자가 화면에 입력만 해 두고 아직 저장하지 않은 값이 함께 저장될 일이 없습니다.

    Storage 파일 삭제는 여기서 하지 않습니다. DB가 먼저 바뀐 것을 확인한 뒤에
    호출한 쪽에서 image_service로 지웁니다.
    """

    supabase = get_supabase()
    result = (
        supabase.table("listings")
        .update({"image_url": None})
        .eq("id", listing_id)
        .execute()
    )
    if not result.data:
        return None
    return ListingPublic.model_validate(result.data[0])


def move_closed_to_end(
    listings: list[ListingPublic],
    today: date | None = None,
    recent_closed_first: bool = True,
) -> list[ListingPublic]:
    """신청이 끝난 공고를 목록 맨 뒤로 보냅니다.

    아직 신청할 수 있는 공고를 먼저 보여 주려는 것입니다.
    끝난 공고끼리의 순서는 무엇으로 정렬했는지에 따라 다릅니다.

    마감일 순으로 받았다면 뒤집어야 최근에 끝난 것부터가 됩니다.
    면적이나 보증금 순으로 받았다면 그 순서를 그대로 두어야 하므로,
    그때는 recent_closed_first를 False로 넘깁니다.
    """

    if today is None:
        today = date.today()

    still_open: list[ListingPublic] = []
    closed: list[ListingPublic] = []

    for listing in listings:
        end_date = listing.application_end_date
        if end_date is not None and end_date < today:
            closed.append(listing)
        else:
            still_open.append(listing)

    if recent_closed_first:
        # 들어온 순서가 마감일 오름차순이므로, 뒤집으면 최근에 끝난 것부터가 됩니다.
        closed.reverse()
    return still_open + closed


def listing_get_all(sort: str | None = None) -> list[ListingPublic]:
    """기본은 마감이 가까운 순으로 돌려줍니다.

    같은 날 마감이면 나중에 등록한 공고를 앞에 둡니다.
    이미 신청이 끝난 공고는 어떤 기준으로 정렬하든 맨 뒤로 보냅니다.
    """
    supabase = get_supabase()
    query = supabase.table("listings").select(LISTING_SELECT)

    # 마감일 순은 등록 시각까지 함께 보므로 따로 둡니다.
    if sort is None or sort == "end_date_asc":
        result = (
            query.order("application_end_date")
            .order("created_at", desc=True)
            .order("id", desc=True)
            .execute()
        )
        recent_closed_first = True
    else:
        result = apply_sort(query, sort).execute()
        # 고른 기준의 순서를 흐트러뜨리지 않도록 끝난 공고도 그대로 둡니다.
        recent_closed_first = False

    listings = [to_listing(item) for item in result.data]
    return move_closed_to_end(listings, recent_closed_first=recent_closed_first)


def listing_get_page(
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort: str | None = None,
) -> ListingPage:
    """고른 기준으로 한 페이지 분량만 가져옵니다. 기본은 등록이 최신인 순서입니다.

    전체를 받아 와서 자르지 않고, Supabase에 정렬과 범위를 맡깁니다.
    정렬을 서버에 맡겨야 페이지를 넘겨도 전체 기준의 순서가 이어집니다.
    """

    supabase = get_supabase()

    # 값이 이상하게 들어와도 안전한 범위로 맞춥니다.
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    page = max(1, page)

    # 전체 개수를 먼저 셉니다.
    # 범위를 넘는 페이지를 요청하면 Supabase가 오류를 내기 때문에,
    # 개수를 알고 나서 안전한 페이지로 맞춘 뒤 목록을 가져옵니다.
    count_result = (
        supabase.table("listings")
        .select("id", count="exact")
        .limit(1)
        .execute()
    )
    total_count = count_result.count or 0
    total_pages = max(1, -(-total_count // page_size))  # 올림 나눗셈

    # 마지막 공고를 지운 뒤처럼 페이지가 범위를 넘으면 마지막 페이지를 보여줍니다.
    page = min(page, total_pages)

    if total_count == 0:
        return ListingPage(
            items=[],
            page=page,
            page_size=page_size,
            total_count=0,
            total_pages=total_pages,
        )

    # 등록 시각이 같은 공고가 있어도 순서가 흔들리지 않도록 id로 한 번 더 정렬합니다.
    start = (page - 1) * page_size
    query = supabase.table("listings").select(LISTING_SELECT)
    result = (
        apply_sort(query, sort or "created_desc")
        .range(start, start + page_size - 1)
        .execute()
    )

    return ListingPage(
        items=[to_listing(item) for item in result.data],
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
    )


def listing_get(listing_id: int) -> ListingPublic | None:
    supabase = get_supabase()
    result = (
        supabase.table("listings")
        .select(LISTING_SELECT)
        .eq("id", listing_id)
        .execute()
    )
    if not result.data:
        return None
    return to_listing(result.data[0])


def listing_search(
    location: str | None,
    max_deposit: int | None,
    max_monthly_rent: int | None,
    sort: str | None = None,
) -> list[ListingPublic]:
    supabase = get_supabase()
    query = supabase.table("listings").select(LISTING_SELECT)

    if location:
        query = query.ilike("location", f"%{location}%")
    if max_deposit is not None:
        query = query.lte("deposit", max_deposit)
    if max_monthly_rent is not None:
        query = query.lte("monthly_rent", max_monthly_rent)

    # 목록과 같은 기준입니다. 기본은 마감이 가까운 순, 같으면 등록이 최신인 순입니다.
    if sort is None or sort == "end_date_asc":
        result = (
            query.order("application_end_date")
            .order("created_at", desc=True)
            .order("id", desc=True)
            .execute()
        )
        recent_closed_first = True
    else:
        result = apply_sort(query, sort).execute()
        recent_closed_first = False

    listings = [to_listing(item) for item in result.data]
    return move_closed_to_end(listings, recent_closed_first=recent_closed_first)


def listing_delete(listing_id: int) -> ListingPublic | None:
    supabase = get_supabase()
    result = (
        supabase.table("listings")
        .delete()
        .eq("id", listing_id)
        .execute()
    )
    if not result.data:
        return None
    return ListingPublic.model_validate(result.data[0])
