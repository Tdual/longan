#!/usr/bin/env python3
"""
Docker内でVOICEVOXエンジンを起動するスクリプト
"""
import subprocess
import time
import requests
import sys
import os

def start_voicevox_engine():
    """VOICEVOXエンジンをバックグラウンドで起動"""
    print("VOICEVOXエンジンを起動中...")
    
    # 環境変数を設定
    env = os.environ.copy()
    env['VOICEVOX_CORE_VERSION'] = '0.14.4'
    env['OMP_NUM_THREADS'] = '1'  # Docker環境での安定性のため
    
    # VOICEVOXエンジンを起動
    cmd = [
        "python", "-m", "voicevox_engine",
        "--host", "0.0.0.0",
        "--port", "50021",
        "--voicevox_dir", "/app/voicevox_core",
        "--runtime_dir", "/app/voicevox_core",
        "--disable_gpu"  # Docker環境ではCPUモードを使用
    ]
    
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # エンジンが起動するまで待機
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:50021/version")
            if response.status_code == 200:
                print("✅ VOICEVOXエンジンが正常に起動しました")
                return process
        except:
            pass
        
        # プロセスが終了していないかチェック
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"❌ VOICEVOXエンジンの起動に失敗しました")
            print(f"stdout: {stdout.decode()}")
            print(f"stderr: {stderr.decode()}")
            sys.exit(1)
        
        time.sleep(1)
        if i % 5 == 0:
            print(f"  起動待機中... ({i}/{max_retries})")
    
    print("❌ VOICEVOXエンジンの起動がタイムアウトしました")
    process.terminate()
    sys.exit(1)

if __name__ == "__main__":
    process = start_voicevox_engine()
    
    # プロセスが終了するまで待機
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n終了します...")
        process.terminate()
        sys.exit(0)