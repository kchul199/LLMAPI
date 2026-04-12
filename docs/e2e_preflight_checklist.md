# Web → Client Gateway → LLM API E2E Preflight Checklist

## 1) 환경 준비

1. Python 의존성 설치
```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -r client_gateway/requirements.txt
```

2. 필수 서비스 확인
- MySQL (client_gateway DB 접근 가능)
- Redis (LLM API async 모드 사용 시)
- LLM 엔진 endpoint (`LLM_BASE_URL`, 필요 시 `LLM_BACKUP_BASE_URL`)

3. 환경 변수 확인
- `LLM_BASE_URL`, `LLM_MODEL_NAME`
- `LLM_BACKUP_BASE_URL`, `LLM_BACKUP_MODEL_NAME`, `LLM_BACKUP_API_KEY`(필요 시)
- `REDIS_QUEUE_ENABLED` (async E2E 시 `true`)
- `MYSQL_DSN`

## 2) 코드/단위 사전 검증

1. 문법 검증
```bash
python3 -m compileall src client_gateway/app tests client_gateway/tests
```

2. LLM API 계약 테스트
```bash
python3 -m pytest -q tests/test_api_contract.py
```

3. Client Gateway smoke/UI smoke
```bash
python3 -m pytest -q client_gateway/tests/test_smoke.py client_gateway/tests/test_ui_smoke.py
```

4. 최소 통합 세트(권장)
```bash
python3 -m pytest -q \
  tests/test_prompt_manager.py \
  tests/test_api_contract.py \
  client_gateway/tests/test_smoke.py \
  client_gateway/tests/test_ui_smoke.py
```

## 3) 런타임 헬스 게이트

1. LLM API 기동 후 헬스체크
```bash
curl -s http://127.0.0.1:8001/v1/health | jq
```

합격 기준:
- `status`가 `healthy` 또는 `degraded`
- `llm.runtime.client_available=true`
- `llm.runtime.serving_available=true`
- `llm.runtime.upstream_probe.any_reachable=true`

2. Client Gateway 기동 후 헬스체크
```bash
curl -s http://127.0.0.1:8000/ui/api/health | jq
```

합격 기준:
- `status`가 `healthy` 또는 `degraded`
- `checks.mysql=ok`
- `checks.llmapi=ok`
- `checks.redis`는 queue 설정에 따라 `ok` 또는 `skip`

## 4) E2E 시나리오 (필수)

1. Web UI 로드 확인
- `/ui`
- `/ui/test`
- `/ui/history`

합격 기준:
- 페이지 로드 에러 없음
- `/ui/test`에서 콘솔 에러 없이 버튼 바인딩 완료

2. Sync E2E
- `/ui/test`에서 sync 실행

합격 기준:
- HTTP 200
- 상태 `COMPLETED`
- JSON에 `request_uid`, `trace_id`, `result` 존재

3. Async E2E
- `/ui/test`에서 async 실행 후 폴링 완료까지 대기

합격 기준:
- enqueue: HTTP 202 + `job_id`
- poll 최종 상태가 `COMPLETED` 또는 명시적 실패(`FAILED`/`TIMEOUT`)
- 상류 404/4xx 발생 시 stale 상태가 아니라 명시 상태로 종료

4. History/Detail/Re-test E2E
- `/ui/history`에서 생성된 요청 확인
- 상세 진입(`/ui/history/{request_uid}`)
- 재테스트 링크 클릭 후 `/ui/test?request_uid=...` prefill 확인

합격 기준:
- 상세 로드 시 XSS/렌더링 에러 없음
- 재테스트 시 `client_request_id`가 길이 제한(100) 내로 자동 생성
- 긴 text라도 URL 과다 길이(414) 없이 동작

## 5) 실패 판정 규칙

아래 중 하나라도 발생하면 E2E 중지 후 수정:

1. LLM failover 비동작 (main 초기화 실패 시 즉시 502)
2. Async 완료 건이 상류 404로 `NOT_FOUND`로 회귀
3. 비정상 LLM 응답(non-JSON/필수 task 누락)이 성공(200) 처리
4. Client Gateway 오류 응답 형식 불일치로 소비자 파싱 실패
5. UI `/ui/test` 초기화 크래시 또는 재테스트 길이 초과(422)

## 6) 운영 전 추가 권장

1. CI에 `client_gateway/tests/*` 추가
2. 계약 테스트에 `is_fallback`, `usage.model`, async 비정상 응답 케이스 추가
3. DB 마이그레이션 경로에서 `uk_source_client_request` 보장 여부 점검
