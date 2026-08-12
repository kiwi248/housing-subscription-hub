# area_format.py
"""면적을 화면에 보여줄 문구로 바꿉니다.

제곱미터만 보면 크기가 잘 와닿지 않아서, 옆에 대략적인 평수를 함께 적습니다.
1평은 정확히 400/121 제곱미터(약 3.3058㎡)입니다.

Streamlit에 기대지 않는 순수 함수라 테스트하기 쉽습니다.
"""

# 1평의 제곱미터 값입니다. 400/121을 그대로 씁니다.
SQM_PER_PYEONG = 400 / 121


def to_pyeong(area_sqm: object) -> float | None:
    """제곱미터를 평으로 바꿉니다. 소수 첫째 자리까지 둡니다.

    숫자가 아니거나 0 이하면 None을 돌려줍니다. 환산할 수 없다는 뜻입니다.
    """

    try:
        sqm = float(area_sqm)
    except (TypeError, ValueError):
        return None

    if sqm <= 0:
        return None

    return round(sqm / SQM_PER_PYEONG, 1)


def format_area(area_sqm: object) -> str:
    """면적을 "19.08㎡ (약 5.8평)" 같은 문구로 만듭니다.

    환산할 수 없으면 평수 없이 원래 값만 보여 주고, 값 자체가 없으면 "-"입니다.
    """

    if area_sqm is None or area_sqm == "":
        return "-"

    pyeong = to_pyeong(area_sqm)
    if pyeong is None:
        return f"{area_sqm}㎡"

    return f"{area_sqm}㎡ (약 {pyeong}평)"
