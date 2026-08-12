# test_gemini_config.py
"""Gemini 설정 읽기 테스트.

실제 키를 쓰지 않고, 가짜 .env 파일로만 확인합니다.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import gemini_config
from core.gemini_config import DEFAULT_MODEL, read_env_file


class ReadEnvFileTest(unittest.TestCase):
    def _write(self, text: str) -> Path:
        directory = tempfile.mkdtemp()
        path = Path(directory) / ".env"
        path.write_text(text, encoding="utf-8")
        return path

    def test_이름과_값을_읽는다(self):
        path = self._write("GEMINI_API_KEY=가짜키\nGEMINI_MODEL=gemini-test\n")

        values = read_env_file(path)

        self.assertEqual(values["GEMINI_API_KEY"], "가짜키")
        self.assertEqual(values["GEMINI_MODEL"], "gemini-test")

    def test_주석과_빈_줄은_건너뛴다(self):
        path = self._write("# 설명\n\nGEMINI_API_KEY=가짜키\n")

        self.assertEqual(read_env_file(path), {"GEMINI_API_KEY": "가짜키"})

    def test_따옴표를_벗겨_낸다(self):
        path = self._write('GEMINI_API_KEY="가짜키"\n')

        self.assertEqual(read_env_file(path)["GEMINI_API_KEY"], "가짜키")

    def test_파일이_없으면_빈_사전이다(self):
        self.assertEqual(read_env_file(Path("없는파일.env")), {})


class GetSettingTest(unittest.TestCase):
    def test_환경_변수를_먼저_본다(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": "환경변수모델"}):
            self.assertEqual(gemini_config.get_model_name(), "환경변수모델")

    def test_값이_없으면_기본_모델을_쓴다(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": ""}), \
             patch.object(gemini_config, "read_env_file", return_value={}):
            self.assertEqual(gemini_config.get_model_name(), DEFAULT_MODEL)

    def test_키가_없으면_준비되지_않은_것으로_본다(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), \
             patch.object(gemini_config, "read_env_file", return_value={}):
            self.assertFalse(gemini_config.has_api_key())

    def test_키가_있으면_준비된_것으로_본다(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "가짜키"}):
            self.assertTrue(gemini_config.has_api_key())

    def test_키_확인은_값을_돌려주지_않는다(self):
        """has_api_key는 참·거짓만 알려 줘야 합니다."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "가짜키"}):
            self.assertIsInstance(gemini_config.has_api_key(), bool)


if __name__ == "__main__":
    unittest.main()
