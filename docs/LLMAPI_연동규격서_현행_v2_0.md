# [연동규격서] LLMAPI API Integration Spec (현행 v2.0)

작성일: 2026-04-12  
적용 범위: LLMAPI 서버(v1 API)

---

## 1. 공통 규격

- 프로토콜: HTTP/HTTPS
- Content-Type: `application/json`
- Base URL 예시: `http://localhost:8001`
- API Prefix: `/v1`
- 인코딩: UTF-8

---

## 2. 엔드포인트 목록

| 구분 | Method | Path | 설명 |
| :--- | :--- | :--- | :--- |
| Health | GET | `/v1/health` | 서버/LLM/프롬프트/큐 상태 조회 |
| Analyze Sync | POST | `/v1/analyze` | 동기 분석 |
| Analyze Async Enqueue | POST | `/v1/analyze/async` | 비동기 분석 작업 등록 |
| Analyze Async Poll | GET | `/v1/analyze/async/{job_id}` | 비동기 작업 상태 조회 |

---

## 3. 요청/응답 모델

### 3.1 AnalyzeRequest

| 필드 | 타입 | 필수 | 제약 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| `request_id` | string | O | 공백 제외 1~100자 | 요청 추적 ID |
| `text` | string | O | 공백 제외 1자 이상 | 분석 대상 텍스트 |
| `tasks` | array[string] | O | 최소 1개, 허용값만 | `summary`, `sentiment`, `category` |
| `target_speakers` | string | X | `agent/customer/both` | 분석 대상 화자 (기본 `both`) |
| `options` | object | X | - | 추가 옵션 |
| `options.language` | string | X | - | 언어(기본 `ko`) |
| `options.prompt_version` | string | X | - | 프롬프트 버전 (예: `v1.1`) |

### 3.2 AnalyzeResponse (동기)

| 필드 | 타입 | 설명 |
| :--- | :--- | :--- |
| `request_id` | string | 요청 ID |
| `status` | string | `success` |
| `results` | object | task별 결과 |
| `usage.total_tokens` | int | 토큰 사용량 |
| `usage.latency_ms` | int | 응답 지연(ms) |
| `error` | string/null | 오류 메시지(기본 null) |

### 3.3 Async Enqueue Response

| 필드 | 타입 | 설명 |
| :--- | :--- | :--- |
| `job_id` | string | 작업 ID |
| `status` | string | `queued` |

### 3.4 Async Poll Response

| 필드 | 타입 | 설명 |
| :--- | :--- | :--- |
| `job_id` | string | 작업 ID |
| `request_id` | string | 원 요청 ID |
| `status` | string | `pending/processing/completed/failed` |
| `created_at` | string | 생성 시각(UTC ISO8601) |
| `updated_at` | string | 갱신 시각(UTC ISO8601) |
| `response` | object/null | 완료 시 결과 |
| `error` | string/null | 실패 시 오류 |

---

## 4. API 상세

## 4.1 GET /v1/health

### 목적
- 서비스 상태 확인
- 운영 정책(재시도/타임아웃/회로차단) 확인
- 프롬프트 버전 목록 확인
- 큐 상태 확인

### 응답 예시

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
      "retry": {
        "attempts": 2,
        "min_wait_seconds": 1,
        "max_wait_seconds": 4
      },
      "timeout_policy": {
        "summary_seconds": 45,
        "sentiment_seconds": 25,
        "category_seconds": 25
      },
      "circuit_breaker": {
        "main": {"state": "closed"},
        "backup": {"state": "closed"}
      }
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
    "queue_depth": null
  }
}
```

---

## 4.2 POST /v1/analyze

### 요청 예시

```json
{
  "request_id": "req_sync_001",
  "text": "고객: 배송이 늦어요. 상담원: 확인하겠습니다.",
  "tasks": ["summary", "sentiment", "category"],
  "target_speakers": "customer",
  "options": {
    "language": "ko",
    "prompt_version": "v1.1"
  }
}
```

### 성공 응답 예시

```json
{
  "request_id": "req_sync_001",
  "status": "success",
  "results": {
    "summary": "배송 지연에 대한 고객 문의",
    "sentiment": "불만",
    "category": "배송/물류"
  },
  "usage": {
    "total_tokens": 120,
    "latency_ms": 860
  },
  "error": null
}
```

---

## 4.3 POST /v1/analyze/async

### 요청 예시

```json
{
  "request_id": "req_async_001",
  "text": "고객: 환불하고 싶습니다.",
  "tasks": ["summary"],
  "target_speakers": "customer"
}
```

### 응답 예시 (`202 Accepted`)

```json
{
  "job_id": "req_async_001-a2d34f91be",
  "status": "queued"
}
```

---

## 4.4 GET /v1/analyze/async/{job_id}

### 응답 예시 (처리중)

```json
{
  "job_id": "req_async_001-a2d34f91be",
  "request_id": "req_async_001",
  "status": "processing",
  "created_at": "2026-04-12T09:00:00.000000+00:00",
  "updated_at": "2026-04-12T09:00:01.000000+00:00",
  "response": null,
  "error": null
}
```

### 응답 예시 (완료)

```json
{
  "job_id": "req_async_001-a2d34f91be",
  "request_id": "req_async_001",
  "status": "completed",
  "created_at": "2026-04-12T09:00:00.000000+00:00",
  "updated_at": "2026-04-12T09:00:03.000000+00:00",
  "response": {
    "results": {
      "summary": "환불 요청 문의"
    },
    "usage": {
      "total_tokens": 40
    },
    "is_fallback": false
  },
  "error": null
}
```

---

## 5. 오류 규격

| HTTP | 조건 | detail |
| :--- | :--- | :--- |
| `422` | 요청 검증 실패 | FastAPI validation payload |
| `502` | 메인/백업 LLM 호출 실패 | `LLM 추론 엔진 호출에 실패했습니다.` |
| `503` | 비동기 큐 비활성/연결 실패 | `비동기 분석 큐를 사용할 수 없습니다.` |
| `404` | 존재하지 않는 `job_id` | `해당 job_id를 찾을 수 없습니다.` |
| `500` | 내부 예외 | `LLM 분석 중 내부 오류가 발생했습니다.` |

---

## 6. 연동 체크리스트 (초보자용)

1. 먼저 `GET /v1/health`가 `200`인지 확인한다.
2. 동기 분석부터 붙인 후, 필요하면 비동기 큐를 활성화한다.
3. `request_id`는 로그 추적을 위해 항상 고유값을 사용한다.
4. `tasks`는 필요한 항목만 넣어 비용/지연을 줄인다.
5. 장애 자동재시도는 `502` 기준으로 구현한다.

---

## 7. 변경 이력

- v2.0 (2026-04-12)
  - async queue API 반영
  - prompt_version 라우팅 반영
  - circuit breaker/timeout 정책 반영
