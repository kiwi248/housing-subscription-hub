# test_gemini_client.py
"""Gemini 응답 해석 테스트.

실제 Gemini를 호출하지 않습니다. 모델이 돌려줄 법한 문자열만 흉내 냅니다.
API 키는 쓰지 않고, 키가 없을 때 안전하게 멈추는지도 확인합니다.
"""

import unittest
from unittest.mock import patch

from clients import gemini_client
from clients.gemini_client import GeminiError, image_mime_type, parse_extract_response


SAMPLE = '[{"housing_name": "방화동원룸 13㎡형", "deposit": 10260000}]'


class ParseExtractResponseTest(unittest.TestCase):
    def test_JSON_배열을_읽는다(self):
        parsed = parse_extract_response(SAMPLE)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["housing_name"], "방화동원룸 13㎡형")

    def test_코드_블록_표시를_걷어낸다(self):
        parsed = parse_extract_response(f"```json\n{SAMPLE}\n```")
        self.assertEqual(parsed[0]["deposit"], 10260000)

    def test_앞뒤_공백을_걷어낸다(self):
        parsed = parse_extract_response(f"\n\n{SAMPLE}\n  ")
        self.assertEqual(len(parsed), 1)

    def test_배열을_감싼_사전도_읽는다(self):
        parsed = parse_extract_response('{"listings": ' + SAMPLE + "}")
        self.assertEqual(len(parsed), 1)

    def test_사전_하나만_와도_목록으로_만든다(self):
        parsed = parse_extract_response('{"housing_name": "단독 항목"}')
        self.assertEqual(len(parsed), 1)

    def test_빈_응답은_오류다(self):
        with self.assertRaises(GeminiError):
            parse_extract_response("")

    def test_JSON이_아니면_오류다(self):
        with self.assertRaises(GeminiError):
            parse_extract_response("죄송합니다. 읽을 수 없습니다.")

    def test_목록도_사전도_아니면_오류다(self):
        with self.assertRaises(GeminiError):
            parse_extract_response("123")


class ApiKeyGuardTest(unittest.TestCase):
    def test_키가_없으면_호출하지_않고_멈춘다(self):
        with patch.object(gemini_client, "get_api_key", return_value=""):
            with self.assertRaises(GeminiError) as caught:
                gemini_client.extract_listings_from_pdf(b"%PDF-1.4")

        self.assertIn("GEMINI_API_KEY", str(caught.exception))

    def test_오류_문구에_키_값이_섞이지_않는다(self):
        """키가 화면이나 로그에 노출되면 안 됩니다."""
        with patch.object(gemini_client, "get_api_key", return_value=""):
            with self.assertRaises(GeminiError) as caught:
                gemini_client.extract_listings_from_pdf(b"%PDF-1.4")

        message = str(caught.exception)
        self.assertNotIn("AIza", message)


class PromptTest(unittest.TestCase):
    def test_등록_API_항목_이름을_모두_요구한다(self):
        for field in (
            "title", "housing_name", "area_sqm", "recruitment_count", "location",
            "deposit", "monthly_rent", "application_start_date",
            "application_end_date", "description", "source_url",
        ):
            self.assertIn(field, gemini_client.EXTRACT_PROMPT)

    def test_값을_지어내지_말라고_알린다(self):
        self.assertIn("지어내지", gemini_client.EXTRACT_PROMPT)


class ImageMimeTypeTest(unittest.TestCase):
    def test_추출_단계가_확인한_형식을_우선한다(self):
        image = {"name": "잘못된이름.png", "mime_type": "image/jpeg"}

        self.assertEqual(image_mime_type(image), "image/jpeg")

    def test_형식이_없으면_파일_확장자로_추정한다(self):
        self.assertEqual(image_mime_type({"name": "사진.webp"}), "image/webp")

    def test_아무_정보도_없으면_PNG로_처리한다(self):
        self.assertEqual(image_mime_type({}), "image/png")


if __name__ == "__main__":
    unittest.main()
