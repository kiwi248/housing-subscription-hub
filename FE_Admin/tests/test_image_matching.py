# test_image_matching.py
"""사진을 공고건에 미리 짝지어 두는 규칙 테스트.

FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.image_matching import (
    house_key,
    images_of_house,
    images_on_page,
    one_house_only,
    simplify,
    suggest_matches,
)


def label(house_name: str = "", kind: str = "위치도") -> dict:
    return {"house_name": house_name, "kind": kind}


def result(index: int, housing_name: str, page=None) -> dict:
    return {
        "index": index,
        "payload": {"housing_name": housing_name},
        "problems": [],
        "source": {"housing_name": housing_name, "page": page},
    }


def image(page=None) -> dict:
    return {"name": "x.jpg", "data": b"", "width": 800, "height": 600, "page": page}


class HouseKeyTest(unittest.TestCase):
    def test_주택형을_뗀다(self):
        """같은 건물의 여러 주택형은 위치도가 하나입니다."""
        self.assertEqual(
            house_key("방화동원룸(유니트로) 13㎡형"), "방화동원룸(유니트로)"
        )
        self.assertEqual(
            house_key("방화동원룸(유니트로) 17㎡형"), "방화동원룸(유니트로)"
        )

    def test_같은_주택의_다른_주택형은_같은_값이다(self):
        self.assertEqual(
            house_key("강일2준주거2(리엔타운) 19㎡형"),
            house_key("강일2준주거2(리엔타운) 33㎡형"),
        )

    def test_다른_주택은_다른_값이다(self):
        self.assertNotEqual(house_key("문정동원룸 14㎡형"), house_key("역삼동원룸 12㎡형"))

    def test_주택형이_없으면_그대로_둔다(self):
        self.assertEqual(house_key("천왕여성안심주택"), "천왕여성안심주택")

    def test_빈_값도_안전하다(self):
        self.assertEqual(house_key(""), "")
        self.assertEqual(house_key(None), "")

    def test_주택형만_있으면_통째로_남긴다(self):
        """다 떼면 이름이 사라지므로 원래 값을 돌려줍니다."""
        self.assertEqual(house_key("13㎡형"), "13㎡형")


class ImagesOnPageTest(unittest.TestCase):
    def setUp(self):
        self.images = [image(7), image(28), image(28), image(29)]

    def test_그_쪽의_사진만_고른다(self):
        self.assertEqual(images_on_page(self.images, 28), [1, 2])

    def test_없는_쪽이면_빈_목록이다(self):
        self.assertEqual(images_on_page(self.images, 99), [])

    def test_쪽을_모르면_빈_목록이다(self):
        """엉뚱한 사진을 붙이느니 아무것도 고르지 않습니다."""
        self.assertEqual(images_on_page(self.images, None), [])
        self.assertEqual(images_on_page(self.images, "몇쪽"), [])

    def test_쪽이_문자로_와도_읽는다(self):
        self.assertEqual(images_on_page(self.images, "29"), [3])

    def test_사진이_없어도_안전하다(self):
        self.assertEqual(images_on_page([], 28), [])


class SuggestMatchesTest(unittest.TestCase):
    def setUp(self):
        self.images = [image(7), image(28), image(28), image(29), image(30)]

    def test_쪽_번호로_사진을_고른다(self):
        results = [result(0, "방화동원룸 13㎡형", page=28)]

        self.assertEqual(suggest_matches(results, self.images), {0: [1, 2]})

    def test_같은_주택의_다른_주택형에_같은_사진을_준다(self):
        """방화동원룸 13㎡형과 17㎡형은 같은 건물입니다."""
        results = [
            result(0, "방화동원룸 13㎡형", page=28),
            result(1, "방화동원룸 17㎡형", page=None),
        ]

        matches = suggest_matches(results, self.images)

        self.assertEqual(matches[0], [1, 2])
        self.assertEqual(matches[1], [1, 2])

    def test_다른_주택은_다른_사진을_받는다(self):
        results = [
            result(0, "방화동원룸 13㎡형", page=28),
            result(1, "역삼동원룸 12㎡형", page=29),
        ]

        matches = suggest_matches(results, self.images)

        self.assertEqual(matches[0], [1, 2])
        self.assertEqual(matches[1], [3])

    def test_쪽을_모르면_아무것도_고르지_않는다(self):
        results = [result(0, "어느주택 10㎡형", page=None)]

        self.assertEqual(suggest_matches(results, self.images), {0: []})

    def test_사진이_없으면_빈_값이다(self):
        self.assertEqual(suggest_matches([result(0, "가 10㎡형", 28)], []), {})

    def test_공고건이_없어도_안전하다(self):
        self.assertEqual(suggest_matches([], self.images), {})

    def test_이상한_값이_섞여도_안전하다(self):
        results = [None, "이상한 값", result(0, "가 10㎡형", 28)]

        self.assertEqual(suggest_matches(results, self.images), {0: [1, 2]})


class SimplifyTest(unittest.TestCase):
    def test_괄호_안과_띄어쓰기를_걷어낸다(self):
        self.assertEqual(simplify("방화동원룸(유니트로)"), "방화동원룸")
        self.assertEqual(simplify("강일2준주거2 (리엔타운)"), "강일2준주거2")

    def test_빈_값도_안전하다(self):
        self.assertEqual(simplify(""), "")
        self.assertEqual(simplify(None), "")


class ImagesOfHouseTest(unittest.TestCase):
    """사진에 적힌 주택 이름으로 찾습니다. 쪽 번호보다 정확합니다."""

    def setUp(self):
        # 실제 공고에서 28쪽에 지도가 두 장 있었습니다.
        self.labels = [
            label("", "안내그림"),
            label("문정동원룸"),
            label("방화동원룸"),
            label("역삼동원룸"),
            label("", "로고"),
        ]

    def test_같은_쪽에_지도가_둘_있어도_갈라낸다(self):
        """쪽 번호만 보면 둘 다 붙어 버립니다."""
        self.assertEqual(images_of_house("방화동원룸(유니트로) 13㎡형", self.labels), [2])
        self.assertEqual(images_of_house("문정동원룸 14㎡형", self.labels), [1])

    def test_괄호가_붙어_있어도_찾는다(self):
        labels = [label("강일2준주거2(리엔타운)")]

        self.assertEqual(images_of_house("강일2준주거2 19㎡형", labels), [0])

    def test_이름을_못_읽은_사진은_건너뛴다(self):
        self.assertEqual(images_of_house("없는주택 10㎡형", self.labels), [])

    def test_이름표가_없으면_빈_목록이다(self):
        self.assertEqual(images_of_house("방화동원룸 13㎡형", []), [])
        self.assertEqual(images_of_house("방화동원룸 13㎡형", None), [])


class SuggestMatchesWithLabelsTest(unittest.TestCase):
    def setUp(self):
        self.images = [image(28), image(28)]
        self.labels = [label("문정동원룸"), label("방화동원룸")]

    def test_이름표가_있으면_이름으로_고른다(self):
        """이 확인이 없으면 28쪽 두 장이 양쪽에 모두 붙습니다."""
        results = [
            result(0, "방화동원룸(유니트로) 13㎡형", page=28),
            result(1, "문정동원룸 14㎡형", page=28),
        ]

        matches = suggest_matches(results, self.images, self.labels)

        self.assertEqual(matches[0], [1])
        self.assertEqual(matches[1], [0])

    def test_이름을_못_읽으면_쪽_번호로_돌아간다(self):
        results = [result(0, "어느주택 10㎡형", page=28)]

        matches = suggest_matches(results, self.images, [label(""), label("")])

        self.assertEqual(matches[0], [0, 1])

    def test_이름표가_없어도_예전처럼_동작한다(self):
        results = [result(0, "어느주택 10㎡형", page=28)]

        self.assertEqual(suggest_matches(results, self.images)[0], [0, 1])


class OneHouseOnlyTest(unittest.TestCase):
    def test_주택이_한_곳이면_참이다(self):
        """건물 하나에 여러 세대를 모집하는 공고입니다."""
        results = [
            result(0, "금천구 예술인주택 가동 301호"),
            result(1, "금천구 예술인주택 가동 301호"),
        ]

        self.assertTrue(one_house_only(results))

    def test_주택이_여러_곳이면_거짓이다(self):
        results = [result(0, "방화동원룸 13㎡형"), result(1, "문정동원룸 14㎡형")]

        self.assertFalse(one_house_only(results))

    def test_비어_있으면_거짓이다(self):
        self.assertFalse(one_house_only([]))


if __name__ == "__main__":
    unittest.main()
