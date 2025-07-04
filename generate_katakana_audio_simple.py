#!/usr/bin/env python3
import json
import requests
import os
from pathlib import Path
import time

def generate_audio_for_slides(start_slide=1, end_slide=5):
    """指定した範囲のスライドの音声を生成"""
    
    # 出力ディレクトリを作成
    output_dir = Path("audio_katakana")
    output_dir.mkdir(exist_ok=True)
    
    # カタカナ変換済みの対話データを読み込み
    with open("dialogue_narration_katakana.json", 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    voicevox_url = "http://localhost:50021"
    speaker_ids = {"metan": 2, "zundamon": 3}
    
    success_count = 0
    total_count = 0
    
    for slide_num in range(start_slide, end_slide + 1):
        slide_key = f"slide_{slide_num}"
        
        if slide_key not in dialogue_data:
            print(f"⚠️  {slide_key} はデータにありません")
            continue
        
        conversations = dialogue_data[slide_key]
        print(f"\n--- {slide_key} の音声生成 ---")
        
        for i, conv in enumerate(conversations):
            speaker = conv['speaker']
            text = conv['text']
            speaker_id = speaker_ids[speaker]
            
            # 音声ファイル名を生成
            output_filename = f"slide_{slide_num:03d}_{i+1:03d}_{speaker}.wav"
            output_path = output_dir / output_filename
            
            print(f"  生成中: {output_filename}")
            
            try:
                # 音声合成クエリを作成
                query_response = requests.post(
                    f"{voicevox_url}/audio_query",
                    params={'text': text, 'speaker': speaker_id},
                    timeout=10
                )
                
                if query_response.status_code == 200:
                    # 音声合成
                    synthesis_response = requests.post(
                        f"{voicevox_url}/synthesis",
                        headers={'Content-Type': 'application/json'},
                        params={'speaker': speaker_id},
                        data=query_response.content,
                        timeout=10
                    )
                    
                    if synthesis_response.status_code == 200:
                        # 音声ファイルを保存
                        with open(output_path, 'wb') as f:
                            f.write(synthesis_response.content)
                        
                        print(f"    ✅ 成功")
                        success_count += 1
                    else:
                        print(f"    ❌ 合成エラー: {synthesis_response.status_code}")
                else:
                    print(f"    ❌ クエリエラー: {query_response.status_code}")
                
            except Exception as e:
                print(f"    ❌ エラー: {e}")
            
            total_count += 1
            time.sleep(0.3)  # 短い待機時間
    
    print(f"\n=== 結果 ===")
    print(f"成功: {success_count}/{total_count}")
    
    return success_count, total_count

if __name__ == "__main__":
    print("=== カタカナ変換版音声生成（簡易版） ===")
    print("最初の5スライドのみ生成します...")
    
    success, total = generate_audio_for_slides(1, 5)
    
    if success > 0:
        print(f"\n✅ {success}個の音声ファイルが生成されました")
    else:
        print("\n❌ 音声生成に失敗しました")