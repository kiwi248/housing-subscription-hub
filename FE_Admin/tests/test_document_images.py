# test_document_images.py
"""공고 파일에서 사진을 꺼내는 규칙 테스트.

실제 파일을 읽는 부분은 라이브러리가 맡으므로, 여기서는
"무엇을 사진으로 볼지" 정하는 규칙을 확인합니다.

FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import io
import unittest
import zipfile

from core.document_images import (
    MIN_BYTES,
    MIN_HEIGHT,
    MIN_WIDTH,
    _hwpx_order,
    extract_from_hwpx,
    extract_images,
    is_hwpx,
    is_pdf,
    looks_like_photo,
    normalize_for_upload,
)


def make_png(width: int, height: int, color=(200, 120, 40)) -> bytes:
    """시험용 그림을 만듭니다."""
    from PIL import Image

    buffer = io.BytesIO()
    # 단색이면 용량이 너무 작아 걸러지므로 얼룩을 넣습니다.
    image = Image.new("RGB", (width, height), color)
    pixels = image.load()
    for x in range(0, width, 3):
        for y in range(0, height, 3):
            pixels[x, y] = ((x * 7) % 256, (y * 11) % 256, (x + y) % 256)
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_jpeg(width: int, height: int, color=(200, 120, 40)) -> bytes:
    """시험용 JPEG 그림을 만듭니다."""

    from PIL import Image

    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), color)
    pixels = image.load()
    for x in range(0, width, 3):
        for y in range(0, height, 3):
            pixels[x, y] = ((x * 7) % 256, (y * 11) % 256, (x + y) % 256)
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def make_image(width: int, height: int, image_format: str) -> bytes:
    """BMP와 GIF 변환 시험에 쓸 그림을 만듭니다."""

    from PIL import Image

    buffer = io.BytesIO()
    image = Image.new("RGB", (width, height), (200, 120, 40))
    pixels = image.load()
    for x in range(0, width, 3):
        for y in range(0, height, 3):
            pixels[x, y] = ((x * 7) % 256, (y * 11) % 256, (x + y) % 256)
    image.save(buffer, format=image_format)
    return buffer.getvalue()


def make_hwpx(files: dict) -> bytes:
    """BinData에 그림이 든 HWPX(=ZIP)를 흉내 냅니다."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Contents/section0.xml", "<xml/>")
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


class FileKindTest(unittest.TestCase):
    def test_확장자로_형식을_가른다(self):
        self.assertTrue(is_hwpx("공고.hwpx"))
        self.assertTrue(is_hwpx("공고.HWPX"))
        self.assertFalse(is_hwpx("공고.pdf"))

        self.assertTrue(is_pdf("공고.pdf"))
        self.assertTrue(is_pdf("공고.PDF"))
        self.assertFalse(is_pdf("공고.hwpx"))

    def test_모르는_형식은_거절한다(self):
        with self.assertRaises(ValueError):
            extract_images(b"...", "공고.docx")

    def test_이름이_없어도_안전하다(self):
        self.assertFalse(is_pdf(""))
        self.assertFalse(is_hwpx(None))


class LooksLikePhotoTest(unittest.TestCase):
    def test_충분히_크면_사진으로_본다(self):
        self.assertTrue(looks_like_photo(1096, 872, 80 * 1024, "RGB"))

    def test_투명도_마스크는_거른다(self):
        """실제 그림이 아니라 어디를 비출지 적어 둔 흑백 판입니다."""
        self.assertFalse(looks_like_photo(2160, 1543, 2 * 1024, "1"))

    def test_작은_그림은_거른다(self):
        """로고나 아이콘입니다."""
        self.assertFalse(looks_like_photo(100, 100, 50 * 1024, "RGB"))
        self.assertFalse(looks_like_photo(1696, 20, 50 * 1024, "RGB"))

    def test_용량이_너무_작으면_거른다(self):
        """거의 단색이라 사진일 수 없습니다."""
        self.assertFalse(looks_like_photo(800, 600, 1024, "RGB"))

    def test_경계값은_통과시킨다(self):
        self.assertTrue(looks_like_photo(MIN_WIDTH, MIN_HEIGHT, MIN_BYTES, "RGB"))

    def test_크기를_모르면_거른다(self):
        """그림을 열 수 없으면 0으로 옵니다. 올렸다가 깨지느니 빼는 게 낫습니다."""
        self.assertFalse(looks_like_photo(0, 0, 100 * 1024, ""))


class HwpxOrderTest(unittest.TestCase):
    def test_숫자_순서로_늘어놓는다(self):
        names = ["BinData/image10.png", "BinData/image2.png", "BinData/image1.png"]

        ordered = sorted(names, key=_hwpx_order)

        self.assertEqual(
            ordered,
            ["BinData/image1.png", "BinData/image2.png", "BinData/image10.png"],
        )

    def test_숫자가_없어도_안전하다(self):
        self.assertEqual(_hwpx_order("BinData/logo.png")[0], 0)


class ExtractFromHwpxTest(unittest.TestCase):
    def test_BinData의_그림을_꺼낸다(self):
        data = make_hwpx(
            {
                "BinData/image1.png": make_png(800, 600),
                "BinData/image2.png": make_png(900, 700),
            }
        )

        images = extract_from_hwpx(data)

        self.assertEqual(len(images), 2)
        self.assertEqual([x["name"] for x in images], ["image1.png", "image2.png"])

    def test_작은_그림은_빼고_꺼낸다(self):
        data = make_hwpx(
            {
                "BinData/image1.png": make_png(800, 600),
                "BinData/image2.png": make_png(40, 40),
            }
        )

        images = extract_from_hwpx(data)

        self.assertEqual([x["name"] for x in images], ["image1.png"])

    def test_그림이_아닌_파일은_건너뛴다(self):
        data = make_hwpx(
            {
                "BinData/image1.png": make_png(800, 600),
                "BinData/note.txt": b"hello",
            }
        )

        self.assertEqual(len(extract_from_hwpx(data)), 1)

    def test_숫자_순서대로_돌려준다(self):
        data = make_hwpx(
            {
                "BinData/image10.png": make_png(800, 600),
                "BinData/image2.png": make_png(800, 600),
            }
        )

        images = extract_from_hwpx(data)

        self.assertEqual([x["name"] for x in images], ["image2.png", "image10.png"])

    def test_그림이_없어도_안전하다(self):
        self.assertEqual(extract_from_hwpx(make_hwpx({})), [])

    def test_HWPX는_쪽_번호가_없다(self):
        """ZIP 안에는 쪽 개념이 없어 문서에 담긴 순서만 씁니다."""
        data = make_hwpx({"BinData/image1.png": make_png(800, 600)})

        self.assertIsNone(extract_from_hwpx(data)[0]["page"])

    def test_실제_그림의_MIME_형식을_함께_돌려준다(self):
        data = make_hwpx({"BinData/image1.png": make_png(800, 600)})

        self.assertEqual(extract_from_hwpx(data)[0]["mime_type"], "image/png")

    def test_파일명이_틀려도_실제_JPEG_형식을_알아낸다(self):
        data = make_hwpx({"BinData/image1.png": make_jpeg(800, 600)})

        self.assertEqual(extract_from_hwpx(data)[0]["mime_type"], "image/jpeg")

    def test_BMP는_JPEG로_바꿔_돌려준다(self):
        data = make_hwpx({"BinData/image1.bmp": make_image(800, 600, "BMP")})

        image = extract_from_hwpx(data)[0]

        self.assertEqual(image["name"], "image1.jpg")
        self.assertEqual(image["mime_type"], "image/jpeg")
        self.assertTrue(image["data"].startswith(b"\xff\xd8\xff"))

    def test_GIF는_첫_프레임을_PNG로_바꿔_돌려준다(self):
        data = make_hwpx({"BinData/image1.gif": make_image(800, 600, "GIF")})

        image = extract_from_hwpx(data)[0]

        self.assertEqual(image["name"], "image1.png")
        self.assertEqual(image["mime_type"], "image/png")
        self.assertTrue(image["data"].startswith(b"\x89PNG\r\n\x1a\n"))

    def test_확장자로_형식을_골라_꺼낸다(self):
        data = make_hwpx({"BinData/image1.png": make_png(800, 600)})

        self.assertEqual(len(extract_images(data, "공고.hwpx")), 1)


class NormalizeForUploadTest(unittest.TestCase):
    def test_백엔드가_받는_형식은_그대로_둔다(self):
        original = make_png(800, 600)

        data, name, mime_type = normalize_for_upload(
            original,
            "원본.png",
            "image/png",
        )

        self.assertIs(data, original)
        self.assertEqual(name, "원본.png")
        self.assertEqual(mime_type, "image/png")

if __name__ == "__main__":
    unittest.main()
