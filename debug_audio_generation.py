#!/usr/bin/env python3
"""
音声生成段階でのビープ音調査
"""
import requests
import time
import subprocess
import os
import numpy as np
from scipy.io import wavfile

# 最新のジョブIDを取得
def get_latest_job():
    response = requests.get("http://localhost:8000/api/jobs")
    if response.status_code == 200:
        jobs = response.json()
        if jobs:
            return jobs[0]["job_id"]  # 最新のジョブ
    return None

job_id = get_latest_job()
if not job_id:
    print("ジョブが見つかりません")
    exit(1)

print(f"調査対象ジョブID: {job_id}")

# 個別の音声ファイルを確認
print("\n=== 個別音声ファイルの確認 ===")
audio_dir = f"audio/{job_id}"

# Dockerコンテナ内の音声ファイル一覧を取得
result = subprocess.run(
    f"docker exec longan-api-1 ls -la /app/{audio_dir}/ | head -10", 
    shell=True, capture_output=True, text=True
)
print("最初の10個の音声ファイル:")
print(result.stdout)

# 最初の数個の音声ファイルを分析
for i in range(1, 4):  # スライド1-3
    for j in range(1, 3):  # 音声1-2
        # ファイル名パターンを探す
        patterns = [
            f"slide_{i:03d}_{j:03d}_metan.wav",
            f"slide_{i:03d}_{j:03d}_zundamon.wav", 
            f"slide_{i:03d}_{j:03d}_speaker*.wav"
        ]
        
        for pattern in patterns:
            cmd = f"docker exec longan-api-1 sh -c 'cd /app/{audio_dir} && ls {pattern} 2>/dev/null | head -1'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            audio_file = result.stdout.strip()
            
            if audio_file:
                print(f"\n--- {audio_file} ---")
                
                # ファイルをローカルにコピー
                local_file = f"debug_{audio_file}"
                copy_cmd = f"docker cp longan-api-1:/app/{audio_dir}/{audio_file} {local_file}"
                subprocess.run(copy_cmd, shell=True)
                
                if os.path.exists(local_file):
                    # 音声ファイルを分析
                    try:
                        sample_rate, data = wavfile.read(local_file)
                        if len(data.shape) > 1:
                            data = data[:, 0]
                        data = data / 32768.0
                        
                        duration = len(data) / sample_rate
                        max_amp = np.max(np.abs(data))
                        
                        print(f"  時間: {duration:.3f}秒")
                        print(f"  最大振幅: {max_amp:.3f}")
                        
                        # 急激な変化を検出
                        diff = np.diff(data)
                        sudden_changes = np.where(np.abs(diff) > 0.1)[0]
                        print(f"  急激な変化: {len(sudden_changes)}個")
                        
                        if len(sudden_changes) > 0:
                            for idx in sudden_changes[:3]:
                                time_pos = idx / sample_rate
                                change_val = diff[idx]
                                print(f"    - {time_pos:.3f}秒: {change_val:.3f}")
                        
                        # 高周波成分チェック
                        fft = np.fft.fft(data)
                        freqs = np.fft.fftfreq(len(data), 1/sample_rate)
                        magnitude = np.abs(fft)
                        
                        high_freq_indices = np.where(np.abs(freqs) > 8000)[0]
                        high_freq_energy = np.sum(magnitude[high_freq_indices])
                        total_energy = np.sum(magnitude)
                        high_freq_ratio = high_freq_energy / total_energy
                        
                        print(f"  高周波比率: {high_freq_ratio:.4f}")
                        if high_freq_ratio > 0.02:
                            print("    ⚠️ 高周波ノイズあり")
                        
                        # ファイルを削除
                        os.remove(local_file)
                        
                    except Exception as e:
                        print(f"  エラー: {e}")
                        if os.path.exists(local_file):
                            os.remove(local_file)
                
                break  # 最初に見つかったファイルで処理を終了

print("\n=== VOICEVOX直接テスト ===")
# VOICEVOXに直接リクエストしてビープ音の有無を確認
test_text = "こんにちは、テストです。"
voicevox_url = "http://localhost:50021"

try:
    # 音声クエリを生成
    query_response = requests.post(
        f"{voicevox_url}/audio_query",
        params={"text": test_text, "speaker": 2}
    )
    
    if query_response.status_code == 200:
        audio_query = query_response.json()
        
        # 音声を合成
        synthesis_response = requests.post(
            f"{voicevox_url}/synthesis",
            headers={"Content-Type": "application/json"},
            params={"speaker": 2},
            json=audio_query
        )
        
        if synthesis_response.status_code == 200:
            # 音声ファイルを保存
            with open("voicevox_direct_test.wav", "wb") as f:
                f.write(synthesis_response.content)
            
            print("VOICEVOXから直接音声を生成しました: voicevox_direct_test.wav")
            
            # 分析
            sample_rate, data = wavfile.read("voicevox_direct_test.wav")
            if len(data.shape) > 1:
                data = data[:, 0]
            data = data / 32768.0
            
            diff = np.diff(data)
            sudden_changes = np.where(np.abs(diff) > 0.1)[0]
            print(f"VOICEVOXダイレクト - 急激な変化: {len(sudden_changes)}個")
            
            if len(sudden_changes) > 0:
                print("⚠️ VOICEVOX自体にビープ音の原因がある可能性")
            else:
                print("✅ VOICEVOX自体は正常")
        else:
            print(f"音声合成エラー: {synthesis_response.status_code}")
    else:
        print(f"音声クエリエラー: {query_response.status_code}")
        
except Exception as e:
    print(f"VOICEVOXテストエラー: {e}")

print("\n=== 結論 ===")
print("1. 個別音声ファイルに高周波ノイズがある場合 → VOICEVOX設定の問題")
print("2. VOICEVOXダイレクトテストで問題がある場合 → VOICEVOX環境の問題") 
print("3. 結合処理でのみ問題がある場合 → DialogueVideoCreatorの問題")