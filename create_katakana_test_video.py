#!/usr/bin/env python3
import json
from pathlib import Path
from dialogue_video_creator_fixed import DialogueVideoCreatorFixed

def main():
    print("=== カタカナ版テスト動画作成 ===")
    
    # 最初の5スライドのみ使用
    slides_dir = Path("slides")
    image_paths = []
    for i in range(1, 6):  # スライド1-5
        slide_path = slides_dir / f"slide_{i:03d}.png"
        if slide_path.exists():
            image_paths.append(str(slide_path))
    
    print(f"使用するスライド数: {len(image_paths)}")
    
    # カタカナ版音声ファイル情報を構築
    dialogue_audio_info = {}
    audio_dir = Path("audio_katakana")
    
    for i in range(1, 6):  # スライド1-5
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
    
    # 動画を作成
    print("\n=== カタカナ版動画作成中 ===")
    video_creator = DialogueVideoCreatorFixed()
    output_path = video_creator.create_dialogue_video(
        image_paths,
        dialogue_audio_info,
        "claude_code_katakana_test.mp4"
    )
    
    print(f"\n✅ カタカナ版テスト動画が作成されました: {output_path}")
    print("英語の読み上げが改善されているか確認してください！")

if __name__ == "__main__":
    main()