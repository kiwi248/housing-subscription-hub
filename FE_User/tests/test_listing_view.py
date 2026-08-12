# test_listing_view.py
"""청약정보 목록 표시 문구 테스트."""

import unittest

from core.listing_view import (
    address_line,
    card_title,
    dday_badge,
    description_lines,
    description_preview,
    format_description_line,
    format_won,
    period_line,
    summary_line,
)


def sample_listing(**overrides) -> dict:
    listing = {
        "title": "2026년 1~2인가구를 위한 도시형생활주택 잔여세대 입주자 모집공고",
        "housing_name": "방화동원룸(유니트로) 13㎡형",
        "location": "강서구",
        "area_sqm": "13.98",
        "recruitment_count": 14,
        "deposit": 10260000,
        "monthly_rent": 125500,
        "application_start_date": "2026-08-18",
        "application_end_date": "2026-08-20",
        "detail_address": "서울시 강서구 개화동로21길 49 (방화동 847)",
        "description": "신청자격 : 서울 거주 1인 무주택세대구성원\n소득기준 : 70% 이하",
    }
    listing.update(overrides)
    return listing


class CardTitleTest(unittest.TestCase):
    def test_주택명을_제목으로_쓴다(self):
        """공고명은 주택형마다 같아서 구분이 안 됩니다."""
        self.assertEqual(card_title(sample_listing()), "방화동원룸(유니트로) 13㎡형")

    def test_주택명이_없으면_공고명을_쓴다(self):
        listing = sample_listing(housing_name="")
        self.assertTrue(card_title(listing).startswith("2026년"))

    def test_둘_다_없으면_기본_문구를_쓴다(self):
        self.assertEqual(card_title({}), "제목 없음")

    def test_공백만_있으면_비어_있는_것으로_본다(self):
        listing = sample_listing(housing_name="   ")
        self.assertNotEqual(card_title(listing), "   ")


class SummaryLineTest(unittest.TestCase):
    def test_자치구_면적_모집_인원을_한_줄로_묶는다(self):
        self.assertEqual(
            summary_line(sample_listing()),
            "강서구  ·  전용 13.98㎡ (약 4.2평)  ·  14호 모집",
        )

    def test_면적에_평수가_함께_나온다(self):
        """평수 표시(#41)가 새 카드에서도 유지되어야 합니다."""
        self.assertIn("약 4.2평", summary_line(sample_listing()))

    def test_값이_없는_항목은_빼고_보여_준다(self):
        listing = sample_listing(area_sqm=None, recruitment_count=None)
        self.assertEqual(summary_line(listing), "강서구")

    def test_아무_값도_없으면_빈_문구다(self):
        self.assertEqual(summary_line({}), "")

    def test_대시가_그대로_보이지_않는다(self):
        self.assertNotIn("-  ·", summary_line(sample_listing(location="")))


class FormatWonTest(unittest.TestCase):
    def test_쉼표를_넣는다(self):
        self.assertEqual(format_won(10260000), "10,260,000원")

    def test_숫자가_아니면_대시다(self):
        self.assertEqual(format_won(None), "-")
        self.assertEqual(format_won("abc"), "-")


class PeriodLineTest(unittest.TestCase):
    def test_신청_기간을_한_줄로_만든다(self):
        self.assertEqual(period_line(sample_listing()), "신청 2026-08-18 ~ 2026-08-20")

    def test_값이_없으면_대시로_채운다(self):
        self.assertEqual(period_line({}), "신청 - ~ -")


class DescriptionPreviewTest(unittest.TestCase):
    def test_첫_줄만_보여_준다(self):
        preview = description_preview(sample_listing())
        self.assertEqual(preview, "신청자격 : 서울 거주 1인 무주택세대구성원")
        self.assertNotIn("소득기준", preview)

    def test_너무_길면_줄임표를_붙인다(self):
        listing = sample_listing(description="가" * 100)
        preview = description_preview(listing, limit=10)
        self.assertTrue(preview.endswith("…"))
        self.assertLessEqual(len(preview), 11)

    def test_설명이_없으면_빈_문구다(self):
        self.assertEqual(description_preview(sample_listing(description="")), "")
        self.assertEqual(description_preview({}), "")

    def test_원래_설명을_바꾸지_않는다(self):
        listing = sample_listing()
        original = listing["description"]
        description_preview(listing)
        self.assertEqual(listing["description"], original)


class AddressLineTest(unittest.TestCase):
    def test_주소가_있으면_보여_준다(self):
        self.assertEqual(
            address_line(sample_listing()),
            "📍 서울시 강서구 개화동로21길 49 (방화동 847)",
        )

    def test_주소가_없으면_빈_문구다(self):
        self.assertEqual(address_line(sample_listing(detail_address=None)), "")
        self.assertEqual(address_line(sample_listing(detail_address="   ")), "")
        self.assertEqual(address_line({}), "")


class DdayBadgeTest(unittest.TestCase):
    """마감이 코앞이면 붉게, 여유가 있으면 푸르게 보여 줍니다."""

    def test_마감이_코앞이면_붉게_보여_준다(self):
        self.assertEqual(dday_badge("D-3", closed=False), ":red[**D-3**]")
        self.assertEqual(dday_badge("D-1", closed=False), ":red[**D-1**]")

    def test_오늘_마감은_붉게_보여_준다(self):
        self.assertEqual(dday_badge("D-DAY", closed=False), ":red[**D-DAY**]")

    def test_여유가_있으면_푸르게_보여_준다(self):
        self.assertEqual(dday_badge("D-10", closed=False), ":blue[**D-10**]")

    def test_마감된_공고는_흐리게_보여_준다(self):
        self.assertEqual(dday_badge("마감", closed=True), ":gray[마감]")

    def test_남은_날수를_모르면_빈_문구다(self):
        self.assertEqual(dday_badge(None, closed=False), "")
        self.assertEqual(dday_badge("", closed=False), "")

    def test_알_수_없는_문구도_안전하게_처리한다(self):
        self.assertEqual(dday_badge("D-알수없음", closed=False), ":blue[**D-알수없음**]")


class DescriptionLinesTest(unittest.TestCase):
    """설명이 한 줄로 붙어 나오지 않도록 줄 단위로 나눕니다."""

    def test_줄_단위로_나눈다(self):
        lines = description_lines(sample_listing())

        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], "신청자격 : 서울 거주 1인 무주택세대구성원")
        self.assertEqual(lines[1], "소득기준 : 70% 이하")

    def test_빈_줄은_버린다(self):
        listing = sample_listing(description="가 : 1\n\n\n나 : 2")

        self.assertEqual(description_lines(listing), ["가 : 1", "나 : 2"])

    def test_앞뒤_공백을_없앤다(self):
        listing = sample_listing(description="  가 : 1  \n  나 : 2  ")

        self.assertEqual(description_lines(listing), ["가 : 1", "나 : 2"])

    def test_설명이_없으면_빈_목록이다(self):
        self.assertEqual(description_lines(sample_listing(description="")), [])
        self.assertEqual(description_lines({}), [])

    def test_원래_설명을_바꾸지_않는다(self):
        listing = sample_listing()
        original = listing["description"]

        description_lines(listing)

        self.assertEqual(listing["description"], original)


class FormatDescriptionLineTest(unittest.TestCase):
    def test_항목_이름을_굵게_만든다(self):
        self.assertEqual(
            format_description_line("신청자격 : 서울 거주 1인 무주택세대구성원"),
            "**신청자격** : 서울 거주 1인 무주택세대구성원",
        )

    def test_콜론_앞에_공백이_없어도_나눈다(self):
        self.assertEqual(format_description_line("소득기준: 70% 이하"), "**소득기준** : 70% 이하")

    def test_콜론이_없으면_그대로_둔다(self):
        self.assertEqual(format_description_line("안내 문구입니다"), "안내 문구입니다")

    def test_값에_콜론이_또_있어도_첫_번째만_나눈다(self):
        self.assertEqual(
            format_description_line("문의 : 전화 : 1600-3456"),
            "**문의** : 전화 : 1600-3456",
        )

    def test_값이_비어_있으면_그대로_둔다(self):
        self.assertEqual(format_description_line("신청자격 :"), "신청자격 :")

    def test_빈_값도_안전하다(self):
        self.assertEqual(format_description_line(""), "")
        self.assertEqual(format_description_line(None), "")


if __name__ == "__main__":
    unittest.main()
