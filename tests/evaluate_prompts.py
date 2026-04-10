import requests
import json
import os

BASE_URL = "http://localhost:8001/v1"
SAMPLES_FILE = "tests/samples.json"

def evaluate():
    if not os.path.exists(SAMPLES_FILE):
        print(f"Error: {SAMPLES_FILE} not found.")
        return

    with open(SAMPLES_FILE, 'r', encoding='utf-8') as f:
        samples = json.load(f)

    print(f"=== LLMAPI Prompt Quality Evaluation ===")
    print(f"Total Samples: {len(samples)}\n")

    for sample in samples:
        print(f"[{sample['id']}] {sample['case_name']}")
        print(f"Target: {sample['target_speakers']}")
        
        payload = {
            "request_id": f"eval_{sample['id']}",
            "text": sample['text'],
            "tasks": ["summary", "sentiment"],
            "target_speakers": sample['target_speakers']
        }
        
        try:
            response = requests.post(f"{BASE_URL}/analyze", json=payload)
            if response.status_code == 200:
                result = response.json()
                analysis = result['results']
                print(f"  - Summary: {analysis.get('summary')}")
                print(f"  - Sentiment: {analysis.get('sentiment')} (Expected: {sample['expected_sentiment']})")
                print(f"  - Usage: {result['usage']}")
            else:
                print(f"  - Error: API returned {response.status_code}")
        except Exception as e:
            print(f"  - Error: {e}")
        print("-" * 50)

if __name__ == "__main__":
    evaluate()
