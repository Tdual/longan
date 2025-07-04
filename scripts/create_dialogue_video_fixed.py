#!/usr/bin/env python3
import json
from pathlib import Path
from pdf_converter import PDFConverter
from dialogue_voicevox_generator import DialogueVoicevoxGenerator
from dialogue_video_creator_fixed import DialogueVideoCreatorFixed

def main():
    # 既存の音声ファイルを使用
    print("=== 既存の音声ファイルを使用して動画を再作成 ===")
    
    # スライド画像のパスを取得
    slides_dir = Path("slides")
    image_paths = sorted([str(p) for p in slides_dir.glob("slide_*.png")])
    
    # 音声ファイル情報を構築
    dialogue_audio_info = {}
    audio_dir = Path("audio")
    
    # 対話形式のナレーションを読み込み
    with open("dialogue_narration.json", 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # 各スライドの音声情報を構築
    for slide_key in dialogue_data.keys():
        slide_num = int(slide_key.split("_")[1])
        dialogue_audio_info[slide_key] = []
        
        # 該当するスライドの音声ファイルを探す
        audio_files = sorted(audio_dir.glob(f"slide_{slide_num:03d}_*_*.wav"))
        
        for audio_file in audio_files:
            # ファイル名から話者を特定
            parts = audio_file.stem.split("_")
            if len(parts) >= 4:
                speaker = parts[3]
                dialogue_audio_info[slide_key].append({
                    "speaker": speaker,
                    "audio_path": str(audio_file)
                })
    
    # 動画を作成
    print("\n=== 改善版の対話動画を作成中 ===")
    video_creator = DialogueVideoCreatorFixed()
    output_path = video_creator.create_dialogue_video(
        image_paths,
        dialogue_audio_info,
        "claude_code_dialogue_fixed.mp4"
    )
    
    print(f"\n✅ 動画の作成が完了しました: {output_path}")
    print("   音声の途切れを改善し、より自然な掛け合いになりました！")

if __name__ == "__main__":
    main()