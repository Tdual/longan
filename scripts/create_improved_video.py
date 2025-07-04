#!/usr/bin/env python3
import json
from pathlib import Path
from dialogue_video_creator_improved import DialogueVideoCreatorImproved

def main():
    print("=== 音声途切れ改善版で動画を作成 ===")
    
    # スライド画像のパスを取得
    slides_dir = Path("slides")
    image_paths = sorted([str(p) for p in slides_dir.glob("slide_*.png")])
    
    # 音声ファイル情報を構築（audio_syncedディレクトリを使用）
    dialogue_audio_info = {}
    audio_dir = Path("audio_synced")
    
    # 面白い対話形式のナレーションを読み込み
    with open("dialogue_narration_synced.json", 'r', encoding='utf-8') as f:
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
    
    # 改善版で動画を作成
    print("\n=== 音声途切れ改善版で動画作成中 ===")
    print("改善点:")
    print("- 各音声の後に0.2秒の余白を追加")
    print("- 対話間の無音時間を0.8秒に延長")
    print("- 全体の最後に1.5秒の余白を追加")
    
    video_creator = DialogueVideoCreatorImproved()
    output_path = video_creator.create_dialogue_video(
        image_paths,
        dialogue_audio_info,
        "claude_code_improved_final.mp4"
    )
    
    print(f"\n✅ 音声途切れ改善版動画の作成が完了しました: {output_path}")
    print("   より自然な間隔で対話が再生されます！")

if __name__ == "__main__":
    main()