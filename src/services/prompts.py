import yaml
import os
from typing import List
from src.core.config import settings

class PromptManager:
    _prompts = {}

    @classmethod
    def load_prompts(cls):
        """YAML 파일에서 프롬프트를 로드합니다."""
        if not os.path.exists(settings.PROMPT_CONFIG_FILE):
            # 기본 프롬프트 (파일이 없을 경우 대비)
            cls._prompts = {
                "analysis_system_prompt_v1": "분석 전문가로서 {tasks_str} 태스크를 수행하세요.",
                "analysis_user_message_v1": "{text}"
            }
            return
            
        with open(settings.PROMPT_CONFIG_FILE, 'r', encoding='utf-8') as f:
            cls._prompts = yaml.safe_load(f)

    @classmethod
    def get_analysis_system_prompt(cls, tasks: List[str], target_speakers: str) -> str:
        if not cls._prompts:
            cls.load_prompts()
            
        speaker_map = {
            "agent": "상담원(Agent)",
            "customer": "고객(Customer)",
            "both": "상담원과 고객 전체"
        }
        target_desc = speaker_map.get(target_speakers, "전체")
        
        template = cls._prompts.get("analysis_system_prompt_v1", "")
        return template.format(
            target_desc=target_desc,
            tasks_str=', '.join(tasks)
        )

    @classmethod
    def get_analysis_user_message(cls, text: str) -> str:
        if not cls._prompts:
            cls.load_prompts()
            
        template = cls._prompts.get("analysis_user_message_v1", "")
        return template.format(text=text)

# 앱 구동 시 초기 로딩
PromptManager.load_prompts()
