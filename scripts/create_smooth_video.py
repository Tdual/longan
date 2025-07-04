#!/usr/bin/env python3
"""
滑らかな音声遷移版の動画作成スクリプト
話者切り替わり時のノイズを軽減
"""
import json
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.append('src')

from dialogue_video_creator_smooth import DialogueVideoCreatorSmooth

def create_smooth_video():
    """滑らかな音声遷移版の動画を作成"""
    print("=== 滑らかな音声遷移版動画作成 ===")
    
    # スライド画像のパスを取得（最初の5スライドでテスト）
    slides_dir = Path("slides")
    image_paths = []
    for i in range(1, 6):  # テスト用に5スライドのみ
        slide_path = slides_dir / f"slide_{i:03d}.png"
        if slide_path.exists():
            image_paths.append(str(slide_path))
    
    print(f"使用するスライド数: {len(image_paths)}")
    
    # カタカナ版音声ファイル情報を構築
    dialogue_audio_info = {}
    audio_dir = Path("audio_katakana")
    
    for i in range(1, 6):  # テスト用に5スライドのみ
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
    
    # 滑らか版動画作成器を使用
    print("\n=== 滑らかな音声遷移版動画作成中 ===")
    print("改善点:")
    print("- 音声の開始・終了にフェードイン・フェードアウト")
    print("- 滑らかな無音の生成")
    print("- AACコーデックによる高品質音声")
    print("- ポップノイズの軽減")
    
    video_creator = DialogueVideoCreatorSmooth()
    output_path = video_creator.create_dialogue_video(
        image_paths,
        dialogue_audio_info,
        "output/claude_code_smooth_test.mp4"
    )
    
    print(f"\n✅ 滑らかな音声遷移版動画が作成されました: {output_path}")
    print("話者切り替わり時のノイズが軽減されているか確認してください！")

def main():
    """メイン処理"""
    create_smooth_video()

if __name__ == "__main__":
    main()