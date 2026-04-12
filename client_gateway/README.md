# Client Gateway (Scaffold)

LLMAPI와 연동하는 별도 Client 서버 스캐폴딩입니다.

## 포함 기능 (초기)
- `POST /client/v1/analyze` (동기)
- `POST /client/v1/analyze/async` (비동기 등록)
- `GET /client/v1/analyze/async/{job_id}` (비동기 상태 조회)
- `GET /client/v1/requests/{request_uid}` (요청 상세 조회)
- `GET /client/v1/requests` (요청 목록 조회)
- `GET /client/v1/health` (헬스체크)
- Web UI (로그인 없음)
  - `/ui` (대시보드)
  - `/ui/test` (동기/비동기 테스트)
  - `/ui/history` (요청 이력)
  - `/ui/history/{request_uid}` (상세)

## 실행
```bash
cd client_gateway
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

## 테스트 (스모크)
```bash
cd client_gateway
PYTHONPATH=. python3 -m pytest tests/test_smoke.py tests/test_ui_smoke.py -q
```

## OpenAPI
- `openapi/client_gateway_openapi.yaml`

## DB 초기화
1. MySQL에 데이터베이스 생성
2. `sql/001_init.sql` 실행
3. `.env`의 `MYSQL_DSN` 설정

## 참고
- `source_system + client_request_id`는 멱등키로 사용됩니다.
- 중복 요청은 `409 DUPLICATE_CLIENT_REQUEST_ID`를 반환합니다.
- `QUEUE_ENABLED=false`이면 health check의 Redis 상태는 `skip`으로 표시됩니다.
- Web UI는 내부 운영 목적이며 로그인 기능을 포함하지 않습니다.
- 재시도 정책/워커 분리/DLQ는 후속 구현 항목입니다.
