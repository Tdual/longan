#!/usr/bin/env python3
"""
より表現豊かな音声でカタカナ対話音声を生成するスクリプト
抑揚を1.2に設定して自然な会話を実現
"""
import json
import sys
from pathlib import Path
import requests

# srcディレクトリをパスに追加
sys.path.append('src')

from voicevox_generator import VoicevoxGenerator

def generate_expressive_audio():
    """表現豊かな音声パラメータで対話音声を生成"""
    print("=== 表現豊かな音声での対話音声生成 ===")
    
    # VOICEVOXの状態確認
    voicevox = VoicevoxGenerator(output_dir="audio")
    if not voicevox.check_voicevox_status():
        print("❌ VOICEVOXが起動していません。先にVOICEVOXを起動してください。")
        return
    
    print("✅ VOICEVOX接続確認済み")
    
    # カタカナ版対話データを読み込み
    with open("data/dialogue_narration_katakana.json", "r", encoding="utf-8") as f:
        dialogue_data = json.load(f)
    
    # 出力ディレクトリ
    output_dir = Path("audio")
    output_dir.mkdir(exist_ok=True)
    
    # スピーカー設定
    speakers = {
        "metan": 2,    # 四国めたん
        "zundamon": 3  # ずんだもん
    }
    
    print("\n=== 表現豊かなパラメータ設定 ===")
    print("- 話速: 1.0（標準）")
    print("- 音高: 0.0（標準）")
    print("- 抑揚: 1.2（より表現豊かに）")
    print("- 音量: 1.0（標準）")
    
    # 各スライドの音声を生成
    for slide_key, dialogues in dialogue_data.items():
        if not dialogues:
            continue
            
        print(f"\n{slide_key} の音声生成中...")
        
        for idx, dialogue in enumerate(dialogues):
            speaker = dialogue["speaker"]
            text = dialogue["text"]
            
            if not text.strip():
                continue
            
            # スピーカーを特定
            if speaker == "metan":
                speaker_id = speakers["metan"]
                speaker_name = "metan"
            elif speaker == "zundamon":
                speaker_id = speakers["zundamon"]
                speaker_name = "zundamon"
            else:
                continue
            
            # ファイル名を生成（slide_001_001_metan.wav形式）
            slide_num = slide_key.replace("slide_", "")
            audio_filename = f"slide_{slide_num:0>3}_{idx+1:0>3}_{speaker_name}.wav"
            
            try:
                print(f"  生成中: {audio_filename} ({speaker_name})")
                
                # 音声クエリの作成
                query_data = {
                    "text": text,
                    "speaker": speaker_id
                }
                
                query_response = requests.post(
                    f"{voicevox.voicevox_url}/audio_query",
                    params=query_data
                )
                
                if query_response.status_code != 200:
                    raise Exception(f"音声クエリの作成に失敗: {query_response.status_code}")
                
                # 音声合成パラメータを調整（more_expressive設定）
                synthesis_data = query_response.json()
                synthesis_data["speedScale"] = 1.0         # 標準速度
                synthesis_data["pitchScale"] = 0.0         # 標準音高
                synthesis_data["intonationScale"] = 1.2    # 表現豊かな抑揚
                synthesis_data["volumeScale"] = 1.0        # 標準音量
                
                synthesis_response = requests.post(
                    f"{voicevox.voicevox_url}/synthesis",
                    params={"speaker": speaker_id},
                    json=synthesis_data
                )
                
                if synthesis_response.status_code != 200:
                    raise Exception(f"音声合成に失敗: {synthesis_response.status_code}")
                
                # ファイルに保存
                output_path = output_dir / audio_filename
                with open(output_path, "wb") as f:
                    f.write(synthesis_response.content)
                
                print(f"    ✅ 完了")
                
            except Exception as e:
                print(f"    ❌ エラー: {e}")
    
    print(f"\n✅ 表現豊かな音声生成が完了しました")
    print(f"出力ディレクトリ: {output_dir}")
    print("これらの音声ファイルで動画を作成すると、より自然で表現豊かな会話になります。")

def main():
    """メイン処理"""
    generate_expressive_audio()

if __name__ == "__main__":
    main()