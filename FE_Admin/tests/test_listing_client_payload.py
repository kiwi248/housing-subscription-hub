# test_listing_client_payload.py
"""사진 요청이 실제로 어떤 모양으로 나가는지 확인합니다.

이 테스트가 없어서 사진 열 장이 한 번에 지워진 적이 있습니다.
서버 쪽 테스트는 통과했지만, 화면이 보내는 형식이 틀려
kept_image_urls가 서버에 하나도 도착하지 않았기 때문입니다.

그래서 여기서는 httpx가 본문을 실제로 만들 수 있는지까지 확인합니다.
값을 넘겨 보는 것만으로는 이 문제를 잡을 수 없습니다.

FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

import httpx

from clients import listing_client


PHOTO_A = "https://example.com/a.jpg"
PHOTO_B = "https://example.com/b.jpg"


class FakeUpload:
    """st.file_uploader가 돌려주는 파일을 흉내 냅니다."""

    def __init__(self, name="new.jpg"):
        self.name = name
        self.type = "image/jpeg"

    def getvalue(self):
        return b"\xff\xd8\xff" + b"0" * 32


class RecordedRequest:
    """httpx.request 대신 불려, 실제로 만들어진 본문을 기록합니다."""

    def __init__(self):
        self.body = b""
        self.content_type = ""

    def __call__(self, method, url, **kwargs):
        kwargs.pop("timeout", None)
        # 여기서 예외가 나면 실제 화면에서도 요청을 보내지 못합니다.
        built = httpx.Client().build_request(method, url, **kwargs)
        self.body = built.read()
        self.content_type = built.headers.get("content-type") or ""
        return httpx.Response(
            200, json={"success": True, "message": "ok", "data": {}}
        )


class ReplaceListingImagesPayloadTest(unittest.TestCase):
    def setUp(self):
        self.recorded = RecordedRequest()
        self.original = httpx.request
        httpx.request = self.recorded

    def tearDown(self):
        httpx.request = self.original

    def test_남길_사진이_본문에_담긴다(self):
        """이 확인이 없으면 서버가 남길 사진을 못 받아 전부 지웁니다."""
        listing_client.replace_listing_images(1, [PHOTO_A, PHOTO_B], [])

        self.assertIn(b"kept_image_urls", self.recorded.body)
        self.assertIn(b"a.jpg", self.recorded.body)
        self.assertIn(b"b.jpg", self.recorded.body)

    def test_남길_장수도_함께_보낸다(self):
        listing_client.replace_listing_images(1, [PHOTO_A, PHOTO_B], [])

        self.assertIn(b"keep_count", self.recorded.body)
        self.assertIn(b"2", self.recorded.body)

    def test_사진을_모두_지울_때도_장수를_보낸다(self):
        listing_client.replace_listing_images(1, [], [])

        self.assertIn(b"keep_count", self.recorded.body)

    def test_새_사진을_함께_보낼_때도_남길_사진이_담긴다(self):
        """파일이 붙으면 본문 형식이 바뀌므로 따로 확인합니다."""
        listing_client.replace_listing_images(1, [PHOTO_A], [FakeUpload()])

        self.assertIn("multipart/form-data", self.recorded.content_type)
        self.assertIn(b"kept_image_urls", self.recorded.body)
        self.assertIn(b"a.jpg", self.recorded.body)
        self.assertIn(b"new.jpg", self.recorded.body)

    def test_본문을_만들_수_있어야_한다(self):
        """목록 형태로 보내면 httpx가 본문을 만들지 못했습니다."""
        listing_client.replace_listing_images(1, [PHOTO_A, PHOTO_B], [])

        self.assertTrue(self.recorded.body)


class UploadListingImagesPayloadTest(unittest.TestCase):
    def setUp(self):
        self.recorded = RecordedRequest()
        self.original = httpx.request
        httpx.request = self.recorded

    def tearDown(self):
        httpx.request = self.original

    def test_사진_여러_장이_같은_이름으로_담긴다(self):
        listing_client.upload_listing_images([FakeUpload("a.jpg"), FakeUpload("b.jpg")])

        self.assertIn("multipart/form-data", self.recorded.content_type)
        self.assertEqual(self.recorded.body.count(b'name="images"'), 2)
        self.assertIn(b"a.jpg", self.recorded.body)
        self.assertIn(b"b.jpg", self.recorded.body)

    def test_스무_장도_모두_담긴다(self):
        files = [FakeUpload(f"photo-{index}.jpg") for index in range(20)]

        listing_client.upload_listing_images(files)

        self.assertEqual(self.recorded.body.count(b'name="images"'), 20)


if __name__ == "__main__":
    unittest.main()
