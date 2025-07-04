#!/usr/bin/env python3
"""
全18スライドのカタカナ版動画作成スクリプト
整理後のファイル構造に対応
"""
import json
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.append('src')

from dialogue_video_creator_fixed import DialogueVideoCreatorFixed
from smart_video_creator import SmartVideoCreator

def generate_all_katakana_audio():
    """全スライドのカタカナ音声を生成"""
    import requests
    import time
    
    print("=== 全スライドのカタカナ音声生成 ===")
    
    # 出力ディレクトリを作成
    output_dir = Path("audio_katakana")
    output_dir.mkdir(exist_ok=True)
    
    # カタカナ変換済みの対話データを読み込み
    with open("data/dialogue_narration_katakana.json", 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    voicevox_url = "http://localhost:50021"
    speaker_ids = {"metan": 2, "zundamon": 3}
    
    success_count = 0
    total_count = 0
    
    for slide_key, conversations in dialogue_data.items():
        slide_num = int(slide_key.split("_")[1])
        print(f"\n--- {slide_key} の音声生成 ---")
        
        for i, conv in enumerate(conversations):
            speaker = conv['speaker']
            text = conv['text']
            speaker_id = speaker_ids[speaker]
            
            # 音声ファイル名を生成
            output_filename = f"slide_{slide_num:03d}_{i+1:03d}_{speaker}.wav"
            output_path = output_dir / output_filename
            
            # 既に存在する場合はスキップ
            if output_path.exists():
                print(f"  スキップ: {output_filename} (既存)")
                success_count += 1
                total_count += 1
                continue
            
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
    
    print(f"\n=== 音声生成結果 ===")
    print(f"成功: {success_count}/{total_count}")
    
    return success_count == total_count

def create_full_video():
    """全18スライドの動画を作成"""
    print("=== 全18スライド動画作成 ===")
    
    # スライド画像のパスを取得
    slides_dir = Path("slides")
    image_paths = []
    for i in range(1, 19):  # スライド1-18
        slide_path = slides_dir / f"slide_{i:03d}.png"
        if slide_path.exists():
            image_paths.append(str(slide_path))
    
    print(f"使用するスライド数: {len(image_paths)}")
    
    # カタカナ版音声ファイル情報を構築
    dialogue_audio_info = {}
    audio_dir = Path("audio_katakana")
    
    for i in range(1, 19):  # スライド1-18
        slide_key = f"slide_{i}"
        dialogue_audio_info[slide_key] = []
        
        # 該当するスライドの音声ファイルを探す
        audio_files = sorted(audio_dir.glob(f"slide_{i:03d}_*_*.wav"))
        
        for audio_file in audio_files:
            # ファイル名から話者を特定
            parts = audio_file.stem.split("_")
            if len(parts) >= 4:
                speaker = parts[3]
                dialogue_audio_info[slide_key].append({
                    "speaker": speaker,
                    "audio_path": str(audio_file)
                })
        
        print(f"  {slide_key}: {len(dialogue_audio_info[slide_key])} 音声ファイル")
    
    # スマート動画作成器を使用（自動フォールバック機能付き）
    print("\n=== スマート動画作成中 ===")
    creator = SmartVideoCreator()
    result = creator.create_video_with_fallback(
        image_paths, 
        dialogue_audio_info, 
        "output/claude_code_full_katakana"
    )
    
    if result:
        print(f"\n✅ 全18スライド動画が作成されました: {result}")
        return result
    else:
        print("\n❌ 動画作成に失敗しました")
        return None

def main():
    """メイン処理"""
    print("=== 全18スライド カタカナ版動画作成 ===")
    
    # 1. 音声生成
    print("\nステップ1: 音声生成")
    if not generate_all_katakana_audio():
        print("❌ 音声生成に失敗しました")
        return
    
    # 2. 動画作成
    print("\nステップ2: 動画作成")
    result = create_full_video()
    
    if result:
        print(f"\n🎉 完了！")
        print(f"作成された動画: {result}")
        print(f"英語の読み上げが適切にカタカナ化されています。")
    else:
        print("\n😞 動画作成に失敗しました")

if __name__ == "__main__":
    main()