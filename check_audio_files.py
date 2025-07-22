#!/usr/bin/env python3
"""
生成された音声ファイルをチェック
"""
import os
from pathlib import Path
import subprocess
import json

# 最新のジョブIDを使用
job_id = "6d51cba9-b520-4f74-bd53-ec61e4949934"
audio_dir = Path(f"audio/{job_id}")

# Dockerコンテナ内の音声ファイルを確認
cmd = f"docker exec longan-api-1 ls -la /app/audio/{job_id}/ | head -10"
print("=== 音声ファイル一覧 ===")
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout)

# 最初の数個の音声ファイルの情報を取得
print("\n=== 音声ファイル情報 ===")
for i in range(1, 4):
    for j in range(1, 3):
        filename = f"slide_{i:03d}_{j:03d}_speaker*.wav"
        cmd = f"docker exec longan-api-1 sh -c 'cd /app/audio/{job_id} && ls {filename} 2>/dev/null | head -1'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        audio_file = result.stdout.strip()
        
        if audio_file:
            # ファイル情報を取得
            info_cmd = f"docker exec longan-api-1 ffprobe -v quiet -print_format json -show_format /app/audio/{job_id}/{audio_file}"
            info_result = subprocess.run(info_cmd, shell=True, capture_output=True, text=True)
            
            try:
                info = json.loads(info_result.stdout)
                duration = float(info['format']['duration'])
                size = int(info['format']['size'])
                print(f"\n{audio_file}:")
                print(f"  時間: {duration:.2f}秒")
                print(f"  サイズ: {size:,} bytes")
            except:
                print(f"\n{audio_file}: 情報取得エラー")