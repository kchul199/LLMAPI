# LLMAPI 서비스 연동 규격서 (v1.1)

## 1. 개요

본 문서는 LLMAPI와 클라이언트 시스템 간의 HTTP 연동 규격을 정의합니다.  
기준 버전은 `APP_VERSION=1.2.0`이며, API prefix는 `/v1`입니다.

## 2. 공통 정보

- 프로토콜: HTTP/HTTPS
- Content-Type: `application/json`
- Base Path: `/v1`

## 3. 엔드포인트

### 3.1 Health Check

- Method/Path: `GET /v1/health`
- 목적: 서비스 기동 상태, 모델 구성, 프롬프트 로드 상태, 큐 상태 확인

응답 예시:

```json
{
  "status": "healthy",
  "version": "1.2.0",
  "llm": {
    "main_endpoint": "http://host.docker.internal:11434/v1",
    "main_model": "llama3.2:3b",
    "backup_enabled": true,
    "backup_model": "llama3.2:1b",
    "runtime": {
      "retry": {},
      "timeout_policy": {},
      "circuit_breaker": {}
    }
  },
  "prompt_config": {
    "path": "src/core/prompts.yaml",
    "exists": true,
    "loaded": true,
    "available_versions": ["v1", "v1_1"]
  },
  "queue": {
    "enabled": false,
    "ready": false,
    "queue_key": "llmapi:analysis:queue",
    "worker_concurrency": 1,
    "queue_depth": null
  }
}
```

### 3.2 Analyze

- Method/Path: `POST /v1/analyze`
- 목적: 상담 대화 텍스트 분석

요청 필드:

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| `request_id` | String | O | 요청 고유 식별자 (공백 제외 1~100자) |
| `text` | String | O | 분석 대상 대화 텍스트 (공백 제외 최소 1자) |
| `tasks` | Array[String] | O | 분석 태스크 목록 (`summary`, `sentiment`, `category`) |
| `target_speakers` | String | X | 분석 대상 화자 (`agent`, `customer`, `both`) 기본값 `both` |
| `options` | Object | X | 확장 옵션 (`language`, `prompt_version`) |

요청 예시:

```json
{
  "request_id": "req_20260412_001",
  "text": "고객: 배송이 지연되고 있습니다. 상담원: 확인 후 연락드리겠습니다.",
  "tasks": ["summary", "sentiment", "category"],
  "target_speakers": "customer",
  "options": {
    "language": "ko",
    "prompt_version": "v1.0"
  }
}
```

성공 응답 예시 (`200 OK`):

```json
{
  "request_id": "req_20260412_001",
  "status": "success",
  "results": {
    "summary": "배송 지연에 대해 고객이 문의했다.",
    "sentiment": "불만",
    "category": "배송/물류"
  },
  "usage": {
    "total_tokens": 128,
    "latency_ms": 850
  },
  "error": null
}
```

### 3.3 Async Analyze (Redis Queue)

- Method/Path: `POST /v1/analyze/async`
- 목적: 분석 작업을 큐에 적재하고 `job_id`를 발급

성공 응답 예시 (`202 Accepted`):

```json
{
  "job_id": "req_20260412_001-4f5a9d12ab",
  "status": "queued"
}
```

- Method/Path: `GET /v1/analyze/async/{job_id}`
- 목적: 큐 작업 상태 조회

조회 응답 예시:

```json
{
  "job_id": "req_20260412_001-4f5a9d12ab",
  "request_id": "req_20260412_001",
  "status": "completed",
  "created_at": "2026-04-12T08:01:12.123456+00:00",
  "updated_at": "2026-04-12T08:01:13.543210+00:00",
  "response": {
    "results": {
      "summary": "배송 지연에 대해 고객이 문의했다."
    },
    "usage": {
      "total_tokens": 87
    },
    "is_fallback": false
  },
  "error": null
}
```

## 4. 오류 규격

| HTTP Status | 발생 조건 | 응답 detail |
| :--- | :--- | :--- |
| `422` | 요청 스키마 검증 실패 (필수값 누락, 허용되지 않은 task 등) | FastAPI validation error 객체 |
| `502` | 메인/백업 LLM 호출 실패 | `LLM 추론 엔진 호출에 실패했습니다.` |
| `503` | Redis 큐 비활성화 또는 연결 실패(비동기 API) | `비동기 분석 큐를 사용할 수 없습니다.` |
| `404` | 존재하지 않는 `job_id` 조회 | `해당 job_id를 찾을 수 없습니다.` |
| `500` | 서버 내부 오류 | `LLM 분석 중 내부 오류가 발생했습니다.` |

## 5. 연동 시 권장사항

1. `request_id`를 트랜잭션 단위로 고유 생성해 추적성을 확보합니다.
2. `tasks`에는 필요한 항목만 전달해 latency와 비용을 최소화합니다.
3. 개인정보(PII)는 요청 전 단계에서 반드시 마스킹합니다.
4. 장애 시 `502`를 재시도 정책의 기준 상태 코드로 활용합니다.

---
작성일: 2026-04-12
