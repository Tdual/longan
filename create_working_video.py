#!/usr/bin/env python3
import json
from pathlib import Path
from dialogue_video_creator_fixed import DialogueVideoCreatorFixed

def main():
    print("=== 成功した時と同じ方法で動画を作成 ===")
    
    # スライド画像のパスを取得
    slides_dir = Path("slides")
    image_paths = sorted([str(p) for p in slides_dir.glob("slide_*.png")])
    
    # 音声ファイル情報を構築（成功時と同じaudioディレクトリを使用）
    dialogue_audio_info = {}
    audio_dir = Path("audio")
    
    # 対話形式のナレーションを読み込み（成功時と同じファイルを使用）
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
    
    # 動画を作成（成功時と同じファイル名）
    print("\n=== 成功版と同じ方法で動画作成中 ===")
    video_creator = DialogueVideoCreatorFixed()
    output_path = video_creator.create_dialogue_video(
        image_paths,
        dialogue_audio_info,
        "claude_code_working_video.mp4"
    )
    
    print(f"\n✅ 動画の作成が完了しました: {output_path}")

if __name__ == "__main__":
    main()