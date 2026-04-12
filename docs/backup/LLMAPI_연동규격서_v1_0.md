# LLMAPI 서비스 연동 규격서 (v1.0)

## 1. 개요
본 문서는 상담 분석 AI 융합 엔진인 LLMAPI와 클라이언트 시스템 간의 연동 규격을 다룹니다.

## 2. API 정보
- **프로토콜**: HTTP/HTTPS
- **데이터 포맷**: JSON
- **엔드포인트**: `POST /v1/analyze`

## 3. 요청 규격 (Request)

### Parameters
| 필드명 | 타입 | 필수 | 설명 | 예시 |
| :--- | :--- | :--- | :--- | :--- |
| `request_id` | String | O | 요청 고유 ID (트래킹용) | `req_20240410_001` |
| `text` | String | O | 분석 대상 전체 대화록 (PII 마스킹 필수) | `상담원: ... 고객: ...` |
| `tasks` | List | O | 수행할 작업 리스트 (`summary`, `category`, `sentiment`) | `["summary", "sentiment"]` |
| `target_speakers` | String | X | 분석 타겟 화자 (`agent`, `customer`, `both`) | `customer` (기본값: both) |

---

## 4. 응답 규격 (Response)

### Response Body
- `status`: 성공 여부 (`success`, `error`)
- `results`: 각 태스크별 분석 결과 객체
  - `summary`: 분석 내용 요약 (String)
  - `sentiment`: 7대 감정 지표 중 하나 (String)
- `usage`: 토큰 사용량 및 성능 지표

#### 감정 지표 정의 (7종)
> 매우 만족, 만족, 중립, 당황, 불만, 분노, 기대

---

## 5. 연동 샘플 코드

### cURL
```bash
curl -X POST http://localhost:8001/v1/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "request_id": "req_001",
       "text": "상담원: 불편을 드려 죄송합니다. 고객: 아 네, 친절하게 안내해주셔서 감사합니다.",
       "tasks": ["summary", "sentiment"],
       "target_speakers": "customer"
     }'
```

### Python
```python
import requests

def analyze_consultation():
    url = "http://localhost:8001/v1/analyze"
    payload = {
        "request_id": "req_001",
        "text": "상담원: ... 고객: ...",
        "tasks": ["summary", "sentiment"],
        "target_speakers": "both"
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("분석 결과:", response.json()["results"])
    else:
        print("에러 발생:", response.text)

analyze_consultation()
```
