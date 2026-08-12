# bulk_delete.py
"""여러 공고를 골라 한 번에 지울 때 쓰는 규칙입니다.

지우는 일은 되돌릴 수 없습니다. 그래서 무엇을 지우는지 사람이
분명히 확인할 수 있도록, 고른 목록을 이름까지 보여 주고 나서 지웁니다.

고른 상태는 화면의 선택칸 한 곳에만 둡니다.
목록을 따로 만들어 두면 두 곳이 어긋나, 하나를 풀었는데 다른 것까지
줄줄이 풀리는 일이 생깁니다.

선택은 지금 보고 있는 페이지에만 해당합니다.
페이지를 넘기면 선택이 풀립니다. 눈에 보이지 않는 공고가 함께 지워지면
사고가 되기 때문입니다.

Streamlit이나 백엔드에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

# 한 번에 지울 수 있는 최대 건수입니다.
# 한 페이지가 열 건이라 넉넉하지만, 실수로 많은 공고를 지우는 일을 막습니다.
MAX_DELETE_COUNT = 50


def checkbox_key(listing_id: object) -> str:
    """공고마다 다른 선택칸 이름을 만듭니다."""

    return f"listing-select-{listing_id}"


def picked_ids(state: object, page_ids: object) -> list[int]:
    """이 페이지에서 고른 공고 번호를 목록 순서대로 돌려줍니다.

    선택칸의 상태만 보고 셉니다. 다른 곳에 따로 적어 두지 않습니다.
    """

    out: list[int] = []
    for listing_id in page_ids or []:
        try:
            number = int(listing_id)
        except (TypeError, ValueError):
            continue
        try:
            if state.get(checkbox_key(number)):
                out.append(number)
        except AttributeError:
            return []
    return out


def set_all(state: object, page_ids: object, picked: bool) -> int:
    """이 페이지 선택칸을 한꺼번에 켜거나 끕니다.

    값을 직접 넣습니다. 지우기만 해서는 켜지지 않습니다.
    Streamlit이 저장된 값을 먼저 보기 때문입니다.

    바꾼 개수를 돌려줍니다.
    """

    changed = 0
    for listing_id in page_ids or []:
        try:
            number = int(listing_id)
        except (TypeError, ValueError):
            continue
        state[checkbox_key(number)] = picked
        changed += 1
    return changed


def names_of(chosen: object, listings: object) -> list[str]:
    """고른 공고의 이름을 화면에 보여 줄 문구로 만듭니다.

    지우기 전에 무엇을 지우는지 확인시키기 위한 것입니다.
    """

    by_id = {}
    for listing in listings or []:
        if not isinstance(listing, dict):
            continue
        try:
            by_id[int(listing.get("id"))] = listing
        except (TypeError, ValueError):
            continue

    out = []
    for listing_id in chosen or []:
        listing = by_id.get(listing_id)
        if listing is None:
            out.append(f"#{listing_id}")
            continue
        name = (listing.get("housing_name") or listing.get("title") or "").strip()
        out.append(f"#{listing_id}  {name}" if name else f"#{listing_id}")
    return out


def can_delete(chosen: object) -> tuple[bool, str]:
    """지워도 되는 상태인지 봅니다.

    (지울 수 있는지, 안 되는 이유)를 돌려줍니다.
    """

    count = len(chosen or [])
    if count == 0:
        return False, "지울 공고를 먼저 골라 주세요."
    if count > MAX_DELETE_COUNT:
        return (
            False,
            f"한 번에 {MAX_DELETE_COUNT}건까지 지울 수 있습니다. (고른 건수: {count}건)",
        )
    return True, ""


def summarize_deletes(succeeded: list, failed: list) -> str:
    """지운 결과를 한 줄로 알려 줍니다."""

    if succeeded and not failed:
        return f"{len(succeeded)}건을 삭제했습니다."
    if succeeded and failed:
        return f"{len(succeeded)}건을 삭제했고 {len(failed)}건은 실패했습니다."
    if failed:
        return f"{len(failed)}건을 삭제하지 못했습니다."
    return "삭제한 공고가 없습니다."
