#!/usr/bin/env python3
import json
from pathlib import Path
from dialogue_voicevox_generator import DialogueVoicevoxGenerator

def main():
    # 対話形式のナレーションを読み込み
    print("=== スライド14-18の音声を生成 ===")
    with open("dialogue_narration_synced.json", 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # スライド14-18のみ抽出
    remaining_data = {}
    for i in range(14, 19):  # 14から18まで
        slide_key = f"slide_{i}"
        if slide_key in dialogue_data:
            remaining_data[slide_key] = dialogue_data[slide_key]
    
    # VOICEVOXで音声を生成
    print("\n=== VOICEVOX音声を生成中（スライド14-18） ===")
    voicevox_generator = DialogueVoicevoxGenerator(output_dir="audio_synced")
    
    try:
        dialogue_audio_info = voicevox_generator.generate_dialogue_audio(remaining_data)
        print("\n✅ スライド14-18の音声生成が完了しました！")
    except Exception as e:
        print(f"\nエラー: {e}")
        print("VOICEVOXが起動していることを確認してください。")
        return

if __name__ == "__main__":
    main()