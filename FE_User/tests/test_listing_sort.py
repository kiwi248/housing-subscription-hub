# test_listing_sort.py
"""청약정보 정렬 기준 이름 테스트.

실제 정렬은 백엔드가 하므로, 여기서는 화면 이름과 보낼 값이
제대로 짝지어져 있는지만 확인합니다.

FE_User 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.listing_sort import (
    DEFAULT_LABEL,
    SORT_OPTIONS,
    default_index,
    sort_key,
    sort_label,
    sort_labels,
)


class SortOptionsTest(unittest.TestCase):
    def test_요청받은_기준이_모두_있다(self):
        """사용자가 고를 수 있어야 하는 기준입니다."""
        labels = sort_labels()

        for name in (
            "면적 넓은 순",
            "면적 좁은 순",
            "모집인원 많은 순",
            "모집인원 적은 순",
            "보증금 높은 순",
            "보증금 낮은 순",
            "월세 높은순",
            "월세 낮은순",
            "신청 종료일 빠른순",
        ):
            with self.subTest(name=name):
                self.assertIn(name, labels)

    def test_이름이_겹치지_않는다(self):
        labels = sort_labels()
        self.assertEqual(len(labels), len(set(labels)))

    def test_보낼_값도_겹치지_않는다(self):
        keys = [key for _, key in SORT_OPTIONS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_화면_순서가_정해진_순서를_따른다(self):
        self.assertEqual(sort_labels()[0], "등록 최신순")
        self.assertEqual(sort_labels()[1], "신청 종료일 빠른순")


class DefaultTest(unittest.TestCase):
    def test_사용자_화면의_기본은_마감이_가까운_순이다(self):
        """지금까지 보여 주던 순서를 그대로 유지합니다."""
        self.assertEqual(DEFAULT_LABEL, "신청 종료일 빠른순")

    def test_기본값의_자리를_알려_준다(self):
        self.assertEqual(sort_labels()[default_index()], DEFAULT_LABEL)


class SortKeyTest(unittest.TestCase):
    def test_이름을_보낼_값으로_바꾼다(self):
        self.assertEqual(sort_key("면적 넓은 순"), "area_desc")
        self.assertEqual(sort_key("면적 좁은 순"), "area_asc")
        self.assertEqual(sort_key("보증금 높은 순"), "deposit_desc")
        self.assertEqual(sort_key("월세 낮은순"), "rent_asc")
        self.assertEqual(sort_key("모집인원 많은 순"), "recruitment_desc")
        self.assertEqual(sort_key("신청 종료일 빠른순"), "end_date_asc")

    def test_모르는_이름이면_기본값으로_돌려준다(self):
        """화면에 없는 값이 들어와도 목록이 비지 않아야 합니다."""
        self.assertEqual(sort_key("없는 기준"), sort_key(DEFAULT_LABEL))
        self.assertEqual(sort_key(None), sort_key(DEFAULT_LABEL))
        self.assertEqual(sort_key(""), sort_key(DEFAULT_LABEL))

    def test_모든_이름이_값을_가진다(self):
        for label in sort_labels():
            with self.subTest(label=label):
                self.assertTrue(sort_key(label))


class SortLabelTest(unittest.TestCase):
    def test_보낼_값을_다시_이름으로_바꾼다(self):
        self.assertEqual(sort_label("area_desc"), "면적 넓은 순")
        self.assertEqual(sort_label("rent_desc"), "월세 높은순")

    def test_모르는_값이면_기본_이름이다(self):
        self.assertEqual(sort_label("없는값"), DEFAULT_LABEL)
        self.assertEqual(sort_label(None), DEFAULT_LABEL)

    def test_이름과_값을_오갈_수_있다(self):
        for label in sort_labels():
            with self.subTest(label=label):
                self.assertEqual(sort_label(sort_key(label)), label)


if __name__ == "__main__":
    unittest.main()
