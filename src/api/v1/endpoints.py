from fastapi import APIRouter, HTTPException
from src.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisUsage,
    AsyncAnalyzeEnqueueResponse,
    AsyncAnalyzeStatusResponse,
)
from src.services.llm import llm_service, LLMUpstreamError
from src.services.prompts import PromptManager
from src.services.queue import analysis_queue_service, QueueUnavailableError
from src.core.config import settings
import time
import logging

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    """시스템 상태 확인 엔드포인트"""
    prompt_status = PromptManager.get_prompt_status()
    queue_status = await analysis_queue_service.get_health()
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "llm": {
            "main_endpoint": settings.LLM_BASE_URL,
            "main_model": settings.LLM_MODEL_NAME,
            "backup_enabled": bool(settings.LLM_BACKUP_MODEL_NAME),
            "backup_model": settings.LLM_BACKUP_MODEL_NAME,
            "runtime": llm_service.get_runtime_health(),
        },
        "prompt_config": prompt_status,
        "queue": queue_status,
    }

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_text(request: AnalysisRequest):
    """
    텍스트 분석 엔드포인트
    1. 요청 데이터 검증 (상담원/고객 구분 포함)
    2. 화자별 프롬프트 자동 조립
    3. 로컬(Ollama) 또는 상용(vLLM) 엔진 호출
    4. 분석 결과(JSON) 반환
    """
    start_time = time.time()
    
    try:
        # Trace-ID와 함께 로그 기록 (운영성 가시성)
        logger.info(f"Analysis Request Received: {request.request_id}", extra={"trace_id": request.request_id})
        
        # 실제 LLM 서비스를 호출하여 분석 수행
        llm_response = await llm_service.analyze(
            text=request.text,
            tasks=request.tasks,
            target_speakers=request.target_speakers,
            request_id=request.request_id,
            prompt_version=request.options.prompt_version if request.options else None,
        )
        
        latency = int((time.time() - start_time) * 1000)
        
        logger.info(f"Analysis Completed: {request.request_id} (Fallback: {llm_response['is_fallback']})", 
                    extra={"trace_id": request.request_id, "latency": latency})
        
        return AnalysisResponse(
            request_id=request.request_id,
            status="success",
            results=llm_response["results"],
            usage=AnalysisUsage(
                total_tokens=llm_response["usage"]["total_tokens"],
                latency_ms=latency
            )
        )

    except LLMUpstreamError as e:
        logger.error(
            f"LLM Upstream Error: {str(e)}",
            extra={"trace_id": request.request_id},
        )
        raise HTTPException(status_code=502, detail="LLM 추론 엔진 호출에 실패했습니다.")
    except Exception as e:
        logger.exception(
            f"Analysis Error: {str(e)}",
            extra={"trace_id": request.request_id},
        )
        raise HTTPException(status_code=500, detail="LLM 분석 중 내부 오류가 발생했습니다.")


@router.post("/analyze/async", response_model=AsyncAnalyzeEnqueueResponse, status_code=202)
async def analyze_text_async(request: AnalysisRequest):
    """Redis queue 기반 비동기 분석 요청 접수"""
    try:
        job_id = await analysis_queue_service.enqueue(request)
    except QueueUnavailableError as exc:
        logger.warning(
            f"Async analyze unavailable: {exc}",
            extra={"trace_id": request.request_id},
        )
        raise HTTPException(status_code=503, detail="비동기 분석 큐를 사용할 수 없습니다.")
    except Exception as exc:
        logger.exception(
            f"Async analyze enqueue error: {exc}",
            extra={"trace_id": request.request_id},
        )
        raise HTTPException(status_code=500, detail="비동기 분석 요청 접수 중 오류가 발생했습니다.")

    return AsyncAnalyzeEnqueueResponse(job_id=job_id)


@router.get("/analyze/async/{job_id}", response_model=AsyncAnalyzeStatusResponse)
async def get_async_analysis_status(job_id: str):
    """비동기 분석 작업 상태 조회"""
    try:
        job = await analysis_queue_service.get_job(job_id)
    except QueueUnavailableError:
        raise HTTPException(status_code=503, detail="비동기 분석 큐를 사용할 수 없습니다.")

    if not job:
        raise HTTPException(status_code=404, detail="해당 job_id를 찾을 수 없습니다.")

    return AsyncAnalyzeStatusResponse(**job)
