# image_matching.py
"""공고에서 꺼낸 사진을 어느 공고건에 붙일지 미리 정해 둡니다.

여기서 정한 것은 어디까지나 초안입니다. 관리자가 화면에서 바꿀 수 있고,
바꾼 값이 우선입니다. 자동으로 다 맞히려 하지 않습니다.

짝짓는 근거는 두 가지입니다.
  * 쪽 번호 - Gemini가 "이 주택 위치도는 28쪽"이라고 알려 줍니다.
  * 주택명  - 같은 주택의 여러 주택형은 같은 사진을 씁니다.
              방화동원룸 13㎡형과 17㎡형은 같은 건물이라 위치도가 하나입니다.

Streamlit에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""


def house_key(housing_name: object) -> str:
    """주택형을 뗀 주택 이름을 돌려줍니다.

    "방화동원룸(유니트로) 13㎡형" 과 "방화동원룸(유니트로) 17㎡형" 은
    같은 건물이므로 같은 값이 나와야 합니다.
    """

    text = ("" if housing_name is None else str(housing_name)).strip()
    if not text:
        return ""

    # "13㎡형" 처럼 면적이 붙은 마지막 조각을 떼어 냅니다.
    parts = text.split()
    while parts and ("㎡" in parts[-1] or parts[-1].endswith("형")):
        parts.pop()

    return " ".join(parts) or text


def images_on_page(images: list, page: object) -> list[int]:
    """그 쪽에서 나온 사진의 자리 번호를 돌려줍니다."""

    if page is None:
        return []

    try:
        wanted = int(page)
    except (TypeError, ValueError):
        return []

    return [
        index
        for index, image in enumerate(images)
        if isinstance(image, dict) and image.get("page") == wanted
    ]


def simplify(name: object) -> str:
    """이름을 견주기 좋게 다듬습니다.

    "방화동원룸(유니트로)" 와 "방화동원룸" 이 같은 것으로 보이도록
    괄호 안과 띄어쓰기를 걷어냅니다.
    """

    text = ("" if name is None else str(name)).strip()
    if not text:
        return ""

    out = []
    depth = 0
    for ch in text:
        if ch in "([{（":
            depth += 1
        elif ch in ")]}）":
            depth = max(0, depth - 1)
        elif depth == 0 and not ch.isspace():
            out.append(ch)
    return "".join(out)


def images_of_house(housing_name: object, labels: list) -> list[int]:
    """사진에 적힌 주택 이름으로 그 주택의 사진을 찾습니다.

    지도에는 주택명이 글자로 찍혀 있어, 쪽 번호보다 훨씬 정확합니다.
    한 쪽에 지도가 두 장 있어도 제대로 갈라집니다.
    """

    wanted = simplify(house_key(housing_name))
    if not wanted:
        return []

    found = []
    for index, label in enumerate(labels or []):
        if not isinstance(label, dict):
            continue
        found_name = simplify(label.get("house_name"))
        if not found_name:
            continue
        # 한쪽이 다른 쪽을 품고 있으면 같은 주택으로 봅니다.
        # "강일2준주거2" 와 "강일2준주거2리엔타운" 같은 경우입니다.
        if wanted in found_name or found_name in wanted:
            found.append(index)

    return found


def suggest_matches(results: list, images: list, labels: list | None = None) -> dict[int, list[int]]:
    """공고건마다 붙일 사진을 미리 골라 둡니다.

    돌려주는 값은 {공고건 자리: [사진 자리, ...]} 입니다.

    먼저 사진에 적힌 주택 이름으로 찾습니다. 이게 가장 정확합니다.
    이름을 못 읽었을 때만 쪽 번호로 찾습니다.
    둘 다 안 되면 빈 목록입니다. 엉뚱한 사진을 붙이느니
    아무것도 고르지 않고 사람이 고르게 하는 편이 안전합니다.
    """

    if not results or not images:
        return {}

    # 같은 주택이면 한 번만 찾아 나눠 씁니다.
    by_house: dict[str, list[int]] = {}
    suggestions: dict[int, list[int]] = {}

    for result in results:
        if not isinstance(result, dict):
            continue
        index = result.get("index")
        source = result.get("source") or {}
        if index is None:
            continue

        key = house_key(source.get("housing_name"))
        if key in by_house:
            suggestions[index] = list(by_house[key])
            continue

        picked = images_of_house(source.get("housing_name"), labels or [])
        if not picked:
            picked = images_on_page(images, source.get("page"))

        by_house[key] = picked
        suggestions[index] = list(picked)

    return suggestions


def one_house_only(results: list) -> bool:
    """공고에 나오는 주택이 한 곳뿐인지 봅니다.

    한 곳뿐이면 사진을 나눌 필요가 없어 전부 붙이면 됩니다.
    금천구 예술인주택처럼 건물 하나에 여러 세대를 모집하는 공고가 그렇습니다.
    """

    keys = {
        house_key((result.get("source") or {}).get("housing_name"))
        for result in results or []
        if isinstance(result, dict)
    }
    keys.discard("")
    return len(keys) == 1
