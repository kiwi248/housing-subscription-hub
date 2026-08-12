# test_amount_format.py
"""금액 표시 문구 테스트."""

import unittest

from core.amount_format import (
    describe_amount,
    format_won,
    to_korean_amount,
    to_won,
)


class ToWonTest(unittest.TestCase):
    def test_숫자를_그대로_읽는다(self):
        self.assertEqual(to_won(10260000), 10260000)
        self.assertEqual(to_won("10260000"), 10260000)

    def test_숫자가_아니면_None이다(self):
        for bad in (None, "", "abc", [], {}):
            self.assertIsNone(to_won(bad), f"입력값 {bad!r}")


class FormatWonTest(unittest.TestCase):
    def test_세_자리마다_쉼표를_넣는다(self):
        self.assertEqual(format_won(10260000), "10,260,000원")
        self.assertEqual(format_won(125500), "125,500원")

    def test_0도_그대로_보여_준다(self):
        self.assertEqual(format_won(0), "0원")

    def test_숫자가_아니면_대시다(self):
        self.assertEqual(format_won("abc"), "-")


class ToKoreanAmountTest(unittest.TestCase):
    def test_만_단위로_읽는다(self):
        self.assertEqual(to_korean_amount(10260000), "1,026만 원")
        self.assertEqual(to_korean_amount(300000), "30만 원")

    def test_억_단위로_읽는다(self):
        self.assertEqual(to_korean_amount(350000000), "3억 5,000만 원")

    def test_만_단위_아래_금액도_읽는다(self):
        self.assertEqual(to_korean_amount(125500), "12만 5,500원")

    def test_만_원_미만은_그대로_읽는다(self):
        self.assertEqual(to_korean_amount(5000), "5,000원")

    def test_0은_0원이다(self):
        self.assertEqual(to_korean_amount(0), "0원")

    def test_숫자가_아니면_대시다(self):
        self.assertEqual(to_korean_amount(None), "-")


class DescribeAmountTest(unittest.TestCase):
    def test_쉼표_금액과_읽기를_함께_보여_준다(self):
        self.assertEqual(describe_amount(10260000), "10,260,000원 (1,026만 원)")

    def test_읽기가_같으면_한_번만_보여_준다(self):
        """5,000원처럼 읽기가 같으면 괄호를 붙이지 않습니다."""
        self.assertEqual(describe_amount(5000), "5,000원")
        self.assertEqual(describe_amount(0), "0원")

    def test_숫자가_아니면_대시다(self):
        self.assertEqual(describe_amount("abc"), "-")

    def test_실제_공고_금액을_읽는다(self):
        self.assertEqual(describe_amount(10260000), "10,260,000원 (1,026만 원)")
        self.assertEqual(describe_amount(125500), "125,500원 (12만 5,500원)")

    def test_저장값을_바꾸지_않는다(self):
        """보여 주기만 하고 실제 전송값은 정수 그대로여야 합니다."""
        self.assertEqual(to_won(10260000), 10260000)


if __name__ == "__main__":
    unittest.main()
