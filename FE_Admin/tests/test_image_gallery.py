# test_image_gallery.py
"""공고 사진을 여러 장 다룰 때 쓰는 규칙 테스트.

Streamlit이나 백엔드에 연결하지 않는 순수 함수만 확인합니다.

FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.image_gallery import (
    MAX_IMAGE_COUNT,
    MAX_IMAGE_SIZE,
    MAX_TOTAL_UPLOAD_SIZE,
    check_upload,
    count_label,
    describe_size,
    image_list,
    rows_of,
)


class FakeFile:
    """st.file_uploader가 돌려주는 파일을 흉내 냅니다."""

    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


def urls(count: int) -> list[str]:
    return [f"https://example.com/photo-{index}.jpg" for index in range(count)]


class ImageListTest(unittest.TestCase):
    def test_사진_목록을_순서대로_꺼낸다(self):
        listing = {"images": urls(3), "image_url": urls(3)[0]}

        self.assertEqual(image_list(listing), urls(3))

    def test_사진이_없고_대표_이미지만_있으면_한_장으로_본다(self):
        """새 테이블을 만들기 전에 등록된 공고입니다.

        빈 목록으로 두면 상세보기에서 사진이 없는 것처럼 보입니다.
        """
        listing = {"images": [], "image_url": "https://example.com/old.jpg"}

        self.assertEqual(image_list(listing), ["https://example.com/old.jpg"])

    def test_둘_다_없으면_빈_목록이다(self):
        self.assertEqual(image_list({"images": [], "image_url": None}), [])
        self.assertEqual(image_list({}), [])

    def test_빈_값은_걸러_낸다(self):
        listing = {"images": ["https://a.jpg", "", None, "https://b.jpg"]}

        self.assertEqual(image_list(listing), ["https://a.jpg", "https://b.jpg"])

    def test_images가_목록이_아니어도_안전하다(self):
        self.assertEqual(image_list({"images": "이상한 값"}), [])

    def test_원래_공고를_바꾸지_않는다(self):
        listing = {"images": urls(2), "image_url": urls(2)[0]}
        original = list(listing["images"])

        image_list(listing)

        self.assertEqual(listing["images"], original)


class RowsOfTest(unittest.TestCase):
    def test_한_줄에_넷씩_끊는다(self):
        rows = rows_of(urls(9))

        self.assertEqual([len(row) for row in rows], [4, 4, 1])

    def test_스무_장도_나눈다(self):
        rows = rows_of(urls(20))

        self.assertEqual([len(row) for row in rows], [4, 4, 4, 4, 4])

    def test_한_장이면_나누지_않는다(self):
        """한 칸짜리 줄을 만들면 화면 폭의 4분의 1만 써서 작게 보입니다."""
        self.assertEqual(rows_of(urls(1)), [urls(1)])

    def test_사진이_없으면_빈_목록이다(self):
        self.assertEqual(rows_of([]), [])

    def test_모든_사진이_빠짐없이_들어간다(self):
        images = urls(13)

        flat = [url for row in rows_of(images) for url in row]

        self.assertEqual(flat, images)

    def test_한_줄에_넣을_수를_바꿀_수_있다(self):
        self.assertEqual([len(row) for row in rows_of(urls(5), per_row=2)], [2, 2, 1])

    def test_0이하로_주어도_안전하다(self):
        self.assertEqual([len(row) for row in rows_of(urls(3), per_row=0)], [1, 1, 1])


class CountLabelTest(unittest.TestCase):
    def test_장수를_알려_준다(self):
        self.assertEqual(count_label(urls(5)), "사진 5장")

    def test_사진이_없으면_빈_문구다(self):
        self.assertEqual(count_label([]), "")


class DescribeSizeTest(unittest.TestCase):
    def test_메가바이트로_바꾼다(self):
        self.assertEqual(describe_size(5 * 1024 * 1024), "5.0MB")
        self.assertEqual(describe_size(1536 * 1024), "1.5MB")


class CheckUploadTest(unittest.TestCase):
    def test_문제가_없으면_빈_문구다(self):
        files = [FakeFile("a.jpg", 1024), FakeFile("b.jpg", 2048)]

        self.assertEqual(check_upload(files), "")

    def test_고른_파일이_없으면_빈_문구다(self):
        self.assertEqual(check_upload([]), "")

    def test_장수를_넘기면_막는다(self):
        files = [FakeFile(f"{i}.jpg", 1024) for i in range(MAX_IMAGE_COUNT + 1)]

        self.assertIn(str(MAX_IMAGE_COUNT), check_upload(files))

    def test_이미_있는_사진까지_합쳐서_센다(self):
        """수정 화면에서 이미 붙어 있는 사진에 더하는 경우입니다."""
        files = [FakeFile(f"{i}.jpg", 1024) for i in range(3)]

        self.assertEqual(check_upload(files, already=MAX_IMAGE_COUNT - 3), "")
        self.assertIn(str(MAX_IMAGE_COUNT), check_upload(files, already=MAX_IMAGE_COUNT - 2))

    def test_한_장이_5MB를_넘으면_막는다(self):
        files = [FakeFile("작은.jpg", 1024), FakeFile("너무큰.jpg", MAX_IMAGE_SIZE + 1)]

        problem = check_upload(files)

        self.assertIn("5MB", problem)
        self.assertIn("너무큰.jpg", problem)

    def test_딱_5MB는_통과한다(self):
        self.assertEqual(check_upload([FakeFile("a.jpg", MAX_IMAGE_SIZE)]), "")

    def test_전체_크기를_넘기면_막는다(self):
        """한 장씩은 괜찮아도 합치면 요청이 너무 커질 수 있습니다."""
        # 4MB짜리 20장이면 80MB입니다.
        files = [FakeFile(f"{i}.jpg", 4 * 1024 * 1024) for i in range(20)]

        problem = check_upload(files)

        self.assertIn("60MB", problem)
        self.assertIn("나눠서", problem)

    def test_전체_크기_상한_안이면_통과한다(self):
        files = [FakeFile(f"{i}.jpg", 2 * 1024 * 1024) for i in range(20)]

        self.assertLessEqual(sum(f.size for f in files), MAX_TOTAL_UPLOAD_SIZE)
        self.assertEqual(check_upload(files), "")

    def test_크기를_모르는_파일도_안전하다(self):
        class NoSize:
            name = "a.jpg"

        self.assertEqual(check_upload([NoSize()]), "")


if __name__ == "__main__":
    unittest.main()
