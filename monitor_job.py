#!/usr/bin/env python3
"""
ジョブの進行状況を監視
"""
import requests
import time
import sys

job_id = "987eb81e-ab30-4c4e-b366-751b2b9ac680"
BASE_URL = "http://localhost:8000"

print(f"ジョブ {job_id} を監視中...")

while True:
    response = requests.get(f"{BASE_URL}/api/jobs/{job_id}/status")
    if response.status_code != 200:
        print(f"エラー: {response.status_code}")
        sys.exit(1)
    
    status = response.json()
    print(f"\rステータス: {status['status']} - {status.get('status_code', '')} ", end="", flush=True)
    
    if status["status"] == "completed":
        print(f"\n✅ 完了! 動画URL: {status.get('video_url', 'N/A')}")
        break
    elif status["status"] == "failed":
        print(f"\n❌ エラー: {status.get('error', 'Unknown error')}")
        break
    
    time.sleep(2)