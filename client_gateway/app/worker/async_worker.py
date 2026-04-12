"""
Client Gateway async worker placeholder.

현재 스캐폴딩은 LLMAPI의 async queue를 직접 사용한다.
향후 요구사항(FR-017)에 따라 실패건 재처리 워커를 이 모듈에 구현한다.
"""


def run_worker() -> None:
    raise NotImplementedError("TODO: implement retry/DLQ worker")
