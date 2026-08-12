# test_area_format.py
"""면적 평 환산 표시 테스트.

Streamlit이나 서버에 연결하지 않는 순수 함수만 확인합니다.
"""

import unittest

from core.area_format import SQM_PER_PYEONG, format_area, to_pyeong


class ToPyeongTest(unittest.TestCase):
    def test_1평은_약_3_3058제곱미터다(self):
        self.assertAlmostEqual(SQM_PER_PYEONG, 3.3058, places=4)
        self.assertEqual(to_pyeong(SQM_PER_PYEONG), 1.0)

    def test_실제_공고_면적을_환산한다(self):
        # 등록된 공고 면적으로 확인합니다.
        self.assertEqual(to_pyeong(19.08), 5.8)
        self.assertEqual(to_pyeong(13.98), 4.2)
        self.assertEqual(to_pyeong(33.83), 10.2)

    def test_문자열_숫자도_환산한다(self):
        """API가 Decimal을 문자열로 돌려주는 경우가 있습니다."""
        self.assertEqual(to_pyeong("19.08"), 5.8)

    def test_소수_첫째_자리까지만_보여_준다(self):
        value = to_pyeong(19.08)
        self.assertEqual(round(value, 1), value)

    def test_숫자가_아니면_환산하지_않는다(self):
        for bad in (None, "", "abc", [], {}):
            self.assertIsNone(to_pyeong(bad), f"입력값 {bad!r}")

    def test_0이나_음수는_환산하지_않는다(self):
        self.assertIsNone(to_pyeong(0))
        self.assertIsNone(to_pyeong(-5))


class FormatAreaTest(unittest.TestCase):
    def test_제곱미터와_평을_함께_보여_준다(self):
        self.assertEqual(format_area(19.08), "19.08㎡ (약 5.8평)")

    def test_문자열_값도_그대로_보여_준다(self):
        self.assertEqual(format_area("13.98"), "13.98㎡ (약 4.2평)")

    def test_값이_없으면_대시를_보여_준다(self):
        self.assertEqual(format_area(None), "-")
        self.assertEqual(format_area(""), "-")

    def test_환산할_수_없으면_평수_없이_보여_준다(self):
        self.assertEqual(format_area("abc"), "abc㎡")
        self.assertEqual(format_area(0), "0㎡")

    def test_원래_면적_값을_바꾸지_않는다(self):
        """보여 주기만 하고 저장값은 그대로여야 합니다."""
        self.assertIn("19.08", format_area(19.08))

    def test_대략적인_값임을_알린다(self):
        self.assertIn("약", format_area(19.08))


if __name__ == "__main__":
    unittest.main()
