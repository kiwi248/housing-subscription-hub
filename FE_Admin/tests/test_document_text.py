"""HWPX 공고문에서 본문 글자를 꺼내는 규칙 테스트.

실제 파일이나 Gemini를 사용하지 않고, 메모리에서 HWPX와 같은 ZIP 파일을
만들어 본문 XML만 올바른 순서로 읽는지 확인합니다.

FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import io
import unittest
import zipfile

from core.document_text import extract_text, extract_text_from_hwpx, unescape


def make_hwpx(files: dict[str, str | bytes]) -> bytes:
    """시험에 필요한 파일만 담은 간단한 HWPX(=ZIP)를 만듭니다."""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class UnescapeTest(unittest.TestCase):
    def test_XML_특수문자를_원래_글자로_되돌린다(self):
        text = "&lt;공고&gt; &amp; &quot;확인&quot; &apos;필수&apos;&#13;다음 줄"

        self.assertEqual(unescape(text), '<공고> & "확인" \'필수\'\n다음 줄')


class ExtractTextFromHwpxTest(unittest.TestCase):
    def test_본문_태그의_한글을_꺼낸다(self):
        data = make_hwpx(
            {
                "Contents/section0.xml": (
                    '<hs:section xmlns:hs="urn:section" xmlns:hp="urn:paragraph">'
                    "<hp:p><hp:run><hp:t>서울시 청년안심주택</hp:t></hp:run></hp:p>"
                    "<hp:p><hp:run><hp:t>보증금 1,000만원</hp:t></hp:run></hp:p>"
                    "</hs:section>"
                )
            }
        )

        self.assertEqual(
            extract_text_from_hwpx(data),
            "서울시 청년안심주택\n보증금 1,000만원",
        )

    def test_여러_본문_XML을_파일명_순서대로_읽는다(self):
        data = make_hwpx(
            {
                "Contents/section1.xml": "<hp:t>두 번째 구역</hp:t>",
                "Contents/section0.xml": "<hp:t>첫 번째 구역</hp:t>",
            }
        )

        self.assertEqual(
            extract_text_from_hwpx(data),
            "첫 번째 구역\n두 번째 구역",
        )

    def test_본문이_아닌_XML과_이미지는_무시한다(self):
        data = make_hwpx(
            {
                "Contents/section0.xml": "<hp:t>본문만 남는다</hp:t>",
                "META-INF/manifest.xml": "<hp:t>메타데이터</hp:t>",
                "Preview/PrvText.txt": "미리보기 글자",
                "BinData/image1.png": b"not-a-real-image",
            }
        )

        self.assertEqual(extract_text_from_hwpx(data), "본문만 남는다")

    def test_빈_태그와_앞뒤_공백은_결과에서_뺀다(self):
        data = make_hwpx(
            {
                "Contents/section0.xml": (
                    "<hp:t>   </hp:t>"
                    "<hp:t>  유효한 글자  </hp:t>"
                    "<hp:t></hp:t>"
                )
            }
        )

        self.assertEqual(extract_text_from_hwpx(data), "유효한 글자")

    def test_태그_안의_태그를_제거하고_XML_기호를_복원한다(self):
        data = make_hwpx(
            {
                "Contents/section0.xml": (
                    "<hp:t>임대료 <hp:mark/> &lt; 10만원 &amp; 관리비</hp:t>"
                )
            }
        )

        self.assertEqual(extract_text_from_hwpx(data), "임대료  < 10만원 & 관리비")

    def test_본문_글자가_없으면_빈_문자열을_돌려준다(self):
        data = make_hwpx({"Contents/section0.xml": "<hp:p/>"})

        self.assertEqual(extract_text_from_hwpx(data), "")

    def test_깨진_ZIP은_명확한_오류를_낸다(self):
        with self.assertRaises(zipfile.BadZipFile):
            extract_text_from_hwpx(b"not-a-zip")


class ExtractTextTest(unittest.TestCase):
    def test_HWPX_확장자는_대소문자와_관계없이_처리한다(self):
        data = make_hwpx({"Contents/section0.xml": "<hp:t>공고 본문</hp:t>"})

        self.assertEqual(extract_text(data, "공고.HWPX"), "공고 본문")

    def test_PDF는_본문_추출_대상이_아니다(self):
        with self.assertRaisesRegex(ValueError, "형식이 아닙니다"):
            extract_text(b"%PDF-1.4", "공고.pdf")


if __name__ == "__main__":
    unittest.main()
