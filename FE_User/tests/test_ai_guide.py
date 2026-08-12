"""AI 안내원 화면의 순수 표시 로직 테스트입니다."""

import unittest

from app_pages._guide_view import format_answer


class GuideViewTest(unittest.TestCase):
    def test_단계별_안내를_번호_목록으로_표시한다(self):
        text = format_answer(
            {
                "title": "내 정보 조회 방법",
                "steps": ["로그인합니다.", "My Page를 선택합니다."],
                "answer": None,
                "notice": None,
            }
        )

        self.assertIn("### 내 정보 조회 방법", text)
        self.assertIn("1. 로그인합니다.", text)
        self.assertIn("2. My Page를 선택합니다.", text)

    def test_추가_안내를_인용문으로_표시한다(self):
        text = format_answer(
            {
                "title": "공고 상세",
                "steps": [],
                "answer": "상세 내용을 확인하세요.",
                "notice": "원문 공고를 확인해 주세요.",
            }
        )

        self.assertIn("상세 내용을 확인하세요.", text)
        self.assertIn("> 원문 공고를 확인해 주세요.", text)


if __name__ == "__main__":
    unittest.main()
