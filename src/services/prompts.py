import os
import logging
import re
from typing import Any, Dict, List, Optional

import yaml

from src.core.config import settings

logger = logging.getLogger(__name__)

class PromptManager:
    _prompts: Dict[str, str] = {}
    _last_loaded_mtime: Optional[float] = None

    @staticmethod
    def _default_prompts() -> Dict[str, str]:
        return {
            "analysis_system_prompt_v1": "분석 전문가로서 {tasks_str} 태스크를 수행하세요.",
            "analysis_user_message_v1": "{text}",
        }

    @classmethod
    def _prompt_file_mtime(cls) -> Optional[float]:
        prompt_path = settings.PROMPT_CONFIG_FILE
        if not os.path.exists(prompt_path):
            return None
        return os.path.getmtime(prompt_path)

    @classmethod
    def load_prompts(cls, force: bool = False):
        """YAML 파일에서 프롬프트를 로드합니다."""
        prompt_path = settings.PROMPT_CONFIG_FILE
        current_mtime = cls._prompt_file_mtime()

        if not force and cls._prompts and current_mtime == cls._last_loaded_mtime:
            return

        if current_mtime is None:
            logger.warning("Prompt file not found. Using default prompts.", extra={"trace_id": "startup"})
            cls._prompts = cls._default_prompts()
            cls._last_loaded_mtime = None
            return

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}

            if not isinstance(loaded, dict):
                raise ValueError("Prompt YAML root must be an object.")

            cls._prompts = {k: v for k, v in loaded.items() if isinstance(v, str)}
            if not cls._prompts:
                logger.warning(
                    "Prompt file has no usable string templates. Using defaults.",
                    extra={"trace_id": "startup"},
                )
                cls._prompts = cls._default_prompts()
            cls._last_loaded_mtime = current_mtime
            logger.info(
                "Prompt file loaded",
                extra={"trace_id": "startup", "prompt_path": prompt_path},
            )
        except Exception as exc:
            logger.error(
                f"Failed to load prompt file ({prompt_path}): {exc}. Using defaults.",
                extra={"trace_id": "startup"},
            )
            cls._prompts = cls._default_prompts()
            cls._last_loaded_mtime = None

    @classmethod
    def _ensure_loaded(cls):
        if not cls._prompts:
            cls.load_prompts(force=True)
            return

        # Auto-reload when prompt file changes on disk.
        if cls._prompt_file_mtime() != cls._last_loaded_mtime:
            cls.load_prompts(force=True)

    @classmethod
    def _normalize_version(cls, prompt_version: Optional[str]) -> Optional[str]:
        if not prompt_version:
            return None
        normalized = re.sub(r"[^a-zA-Z0-9]+", "_", prompt_version.strip().lower())
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        return normalized or None

    @classmethod
    def _candidate_keys(cls, base_key: str, prompt_version: Optional[str]) -> List[str]:
        candidates: List[str] = []
        normalized = cls._normalize_version(prompt_version)
        if normalized:
            candidates.append(f"{base_key}_{normalized}")
            major = normalized.split("_")[0]
            if major and major != normalized:
                candidates.append(f"{base_key}_{major}")

        candidates.append(f"{base_key}_v1")
        return candidates

    @classmethod
    def _get_template(cls, base_key: str, prompt_version: Optional[str]) -> str:
        cls._ensure_loaded()
        for key in cls._candidate_keys(base_key, prompt_version):
            if key in cls._prompts:
                return cls._prompts[key]

        if cls._prompts:
            return next(iter(cls._prompts.values()))
        return ""

    @classmethod
    def get_analysis_system_prompt(cls, tasks: List[str], target_speakers: str, prompt_version: Optional[str] = None) -> str:
        speaker_map = {
            "agent": "상담원(Agent)",
            "customer": "고객(Customer)",
            "both": "상담원과 고객 전체"
        }
        target_desc = speaker_map.get(target_speakers, "전체")

        template = cls._get_template("analysis_system_prompt", prompt_version)
        return template.format(
            target_desc=target_desc,
            tasks_str=', '.join(tasks)
        )

    @classmethod
    def get_analysis_user_message(cls, text: str, prompt_version: Optional[str] = None) -> str:
        template = cls._get_template("analysis_user_message", prompt_version)
        return template.format(text=text)

    @classmethod
    def get_prompt_status(cls) -> Dict[str, Any]:
        cls._ensure_loaded()
        available_versions = sorted(
            key.replace("analysis_system_prompt_", "")
            for key in cls._prompts.keys()
            if key.startswith("analysis_system_prompt_")
        )
        return {
            "path": settings.PROMPT_CONFIG_FILE,
            "exists": os.path.exists(settings.PROMPT_CONFIG_FILE),
            "loaded": bool(cls._prompts),
            "available_versions": available_versions,
        }

# 앱 구동 시 초기 로딩
PromptManager.load_prompts()
