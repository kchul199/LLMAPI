import tempfile
import unittest
from pathlib import Path

from src.core.config import settings
from src.services.prompts import PromptManager


class TestPromptManagerVersionRouting(unittest.TestCase):
    def setUp(self):
        self._original_prompt_file = settings.PROMPT_CONFIG_FILE
        self._original_prompts = PromptManager._prompts
        self._original_mtime = PromptManager._last_loaded_mtime

        self.temp_dir = tempfile.TemporaryDirectory()
        self.prompt_file = Path(self.temp_dir.name) / "prompts.yaml"

        self.prompt_file.write_text(
            """
analysis_system_prompt_v1: |
  v1 template {target_desc} {tasks_str}
analysis_user_message_v1: |
  v1 user {text}
analysis_system_prompt_v1_1: |
  v1_1 template {target_desc} {tasks_str}
analysis_user_message_v1_1: |
  v1_1 user {text}
""".strip(),
            encoding="utf-8",
        )

        settings.PROMPT_CONFIG_FILE = str(self.prompt_file)
        PromptManager._prompts = {}
        PromptManager._last_loaded_mtime = None

    def tearDown(self):
        settings.PROMPT_CONFIG_FILE = self._original_prompt_file
        PromptManager._prompts = self._original_prompts
        PromptManager._last_loaded_mtime = self._original_mtime
        self.temp_dir.cleanup()

    def test_prompt_version_specific_template(self):
        system_prompt = PromptManager.get_analysis_system_prompt(
            tasks=["summary"],
            target_speakers="customer",
            prompt_version="v1.1",
        )
        user_prompt = PromptManager.get_analysis_user_message(
            text="고객: 배송이 늦어요.",
            prompt_version="v1.1",
        )

        self.assertIn("v1_1 template", system_prompt)
        self.assertIn("v1_1 user", user_prompt)

    def test_prompt_version_fallback_to_v1(self):
        system_prompt = PromptManager.get_analysis_system_prompt(
            tasks=["summary"],
            target_speakers="customer",
            prompt_version="v9.9",
        )
        self.assertIn("v1 template", system_prompt)


if __name__ == "__main__":
    unittest.main()
