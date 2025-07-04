#!/usr/bin/env python3
import json
import requests
import os
from pathlib import Path
import time

class VOICEVOXAudioGenerator:
    def __init__(self, voicevox_url="http://localhost:50021"):
        self.voicevox_url = voicevox_url
        self.speaker_ids = {
            "metan": 2,    # 四国めたん
            "zundamon": 3  # ずんだもん
        }
    
    def generate_audio(self, text, speaker_id, output_path):
        """VOICEVOXを使って音声を生成"""
        try:
            # 音声合成クエリを作成
            params = {
                'text': text,
                'speaker': speaker_id
            }
            
            # クエリ作成
            query_response = requests.post(
                f"{self.voicevox_url}/audio_query",
                params=params,
                timeout=30
            )
            
            if query_response.status_code != 200:
                print(f"クエリ作成エラー: {query_response.status_code}")
                return False
            
            # 音声合成
            synthesis_response = requests.post(
                f"{self.voicevox_url}/synthesis",
                headers={'Content-Type': 'application/json'},
                params={'speaker': speaker_id},
                data=query_response.content,
                timeout=30
            )
            
            if synthesis_response.status_code != 200:
                print(f"音声合成エラー: {synthesis_response.status_code}")
                return False
            
            # 音声ファイルを保存
            with open(output_path, 'wb') as f:
                f.write(synthesis_response.content)
            
            print(f"✅ 音声生成完了: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ 音声生成エラー: {e}")
            return False

def main():
    print("=== カタカナ変換版音声生成 ===")
    
    # 出力ディレクトリを作成
    output_dir = Path("audio_katakana")
    output_dir.mkdir(exist_ok=True)
    
    # カタカナ変換済みの対話データを読み込み
    with open("dialogue_narration_katakana.json", 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # VOICEVOX音声生成器を初期化
    generator = VOICEVOXAudioGenerator()
    
    # 各スライドの音声を生成
    total_files = 0
    success_files = 0
    
    for slide_key, conversations in dialogue_data.items():
        slide_num = int(slide_key.split("_")[1])
        
        print(f"\n--- {slide_key} の音声生成 ---")
        
        for i, conv in enumerate(conversations):
            speaker = conv['speaker']
            text = conv['text']
            speaker_id = generator.speaker_ids[speaker]
            
            # 音声ファイル名を生成
            output_filename = f"slide_{slide_num:03d}_{i+1:03d}_{speaker}.wav"
            output_path = output_dir / output_filename
            
            print(f"生成中: {output_filename}")
            print(f"  話者: {speaker} (ID: {speaker_id})")
            print(f"  テキスト: {text}")
            
            # 音声生成
            if generator.generate_audio(text, speaker_id, str(output_path)):
                success_files += 1
            
            total_files += 1
            
            # 少し待機（APIへの負荷軽減）
            time.sleep(0.5)
    
    print(f"\n=== 音声生成完了 ===")
    print(f"総ファイル数: {total_files}")
    print(f"成功: {success_files}")
    print(f"失敗: {total_files - success_files}")
    print(f"出力ディレクトリ: {output_dir}")

if __name__ == "__main__":
    main()