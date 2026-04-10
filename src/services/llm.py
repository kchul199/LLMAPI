import json
import logging
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.core.config import settings
from src.services.prompts import PromptManager
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        # 메인 클라이언트 초기화
        self.main_client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY or "not-needed",
            timeout=60.0
        )
        # 백업 클라이언트 초기화 (Fail-over 용)
        self.backup_client = AsyncOpenAI(
            base_url=settings.LLM_BACKUP_BASE_URL,
            api_key="not-needed",
            timeout=60.0
        )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _call_inference(self, client: AsyncOpenAI, model: str, system_prompt: str, user_message: str):
        """실제 LLM 호출 (Retry 로직 포함)"""
        return await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            response_format={"type": "json_object"} if "llama3" in model.lower() else None
        )

    async def analyze(self, text: str, tasks: List[str], target_speakers: str) -> Dict[str, Any]:
        """
        안정성 강화된 텍스트 분석 로직:
        1. 메인 모델로 시도 (실패 시 2회 재시도)
        2. 최종 실패 시 백업 모델(Fail-over)로 전환
        """
        system_prompt = PromptManager.get_analysis_system_prompt(tasks, target_speakers)
        user_message = PromptManager.get_analysis_user_message(text)
        
        current_model = settings.LLM_MODEL_NAME
        used_client = self.main_client
        is_fallback = False

        try:
            # 1. 메인 엔진 호출
            logger.info(f"LLM Call [Main]: {current_model}")
            response = await self._call_inference(used_client, current_model, system_prompt, user_message)
        except Exception as e:
            # 2. 장애 극복 (Fail-over) 발동
            logger.warning(f"Main Engine Failed: {str(e)}. Triggering Fail-over to Backup.")
            is_fallback = True
            current_model = settings.LLM_BACKUP_MODEL_NAME
            used_client = self.backup_client
            
            try:
                response = await self._call_inference(used_client, current_model, system_prompt, user_message)
            except Exception as e2:
                logger.error(f"Critical Error: Both Main and Backup Engines failed. {str(e2)}")
                raise e2

        content = response.choices[0].message.content
        
        try:
            results = json.loads(content)
        except json.JSONDecodeError:
            results = {"error": "JSON 파싱 실패", "raw_content": content}

        return {
            "results": results,
            "is_fallback": is_fallback,
            "usage": {
                "total_tokens": response.usage.total_tokens,
                "model": current_model
            }
        }

llm_service = LLMService()
