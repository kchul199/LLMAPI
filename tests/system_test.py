import requests
import json
import time
import sys

BASE_URL = "http://localhost:8001/v1"

def test_health():
    print("\n[TC-01] Health Check Test")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Content: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_analysis_integration():
    print("\n[TC-02] Analysis Integration Test (Summary + Sentiment)")
    payload = {
        "request_id": "test_tc02",
        "text": "상담원: 안녕하세요. 무엇을 도와드릴까요? 고객: 상품이 파손되어 배송되었어요. 너무 속상하네요.",
        "tasks": ["summary", "sentiment"],
        "target_speakers": "both"
    }
    try:
        response = requests.post(f"{BASE_URL}/analyze", json=payload)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 7종 감정 카테고리에 포함되는지 확인
        sentiment = result["results"].get("sentiment")
        valid_sentiments = ["매우 만족", "만족", "중립", "당황", "불만", "분노", "기대"]
        print(f"Detected Sentiment: {sentiment} (Valid: {sentiment in valid_sentiments})")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_speaker_context():
    print("\n[TC-03] Speaker Context Test (Customer Only)")
    payload = {
        "request_id": "test_tc03",
        "text": "상담원: 교환해 드릴까요? 고객: 아니요, 당장 환불해 주세요!!",
        "tasks": ["sentiment"],
        "target_speakers": "customer"
    }
    try:
        response = requests.post(f"{BASE_URL}/analyze", json=payload)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Result (Customer Sentiment): {result['results'].get('sentiment')}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=== LLMAPI System Integration Test ===")
    results = []
    results.append(test_health())
    results.append(test_analysis_integration())
    results.append(test_speaker_context())
    
    print("\n=== Final Test Summary ===")
    if all(results):
        print("ALL TESTS PASSED! 🎉")
    else:
        print("SOME TESTS FAILED. ❌")
        sys.exit(1)
