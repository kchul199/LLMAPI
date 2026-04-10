from fastapi import APIRouter, HTTPException
from src.schemas.analysis import AnalysisRequest, AnalysisResponse, AnalysisUsage
from src.services.llm import llm_service
from src.core.config import settings
import time
import logging

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    """시스템 상태 확인 엔드포인트"""
    return {
        "status": "healthy",
        "llm_main_endpoint": settings.LLM_BASE_URL,
        "backup_enabled": bool(settings.LLM_BACKUP_MODEL_NAME)
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
            target_speakers=request.target_speakers
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
        
    except Exception as e:
        logger.error(f"Analysis Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM 분석 중 오류가 발생했습니다: {str(e)}")
