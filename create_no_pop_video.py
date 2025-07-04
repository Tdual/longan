#!/usr/bin/env python3
"""
ポップノイズ軽減版の動画作成スクリプト
話者切り替わり時のブチッという音を軽減
"""
import json
import sys
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.append('src')

from dialogue_video_creator_no_pop import DialogueVideoCreatorNoPop

def create_no_pop_video():
    """ポップノイズ軽減版の動画を作成"""
    print("=== ポップノイズ軽減版動画作成 ===")
    
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
    
    # ポップノイズ軽減版動画作成器を使用
    print("\n=== ポップノイズ軽減版動画作成中 ===")
    print("改善点:")
    print("- 各音声に20msのフェードイン・フェードアウト")
    print("- 話者間の間隔を1秒に延長")
    print("- PCMコーデックによる安定した音声処理")
    print("- シンプルで確実な処理")
    
    video_creator = DialogueVideoCreatorNoPop()
    output_path = video_creator.create_dialogue_video(
        image_paths,
        dialogue_audio_info,
        "output/claude_code_no_pop_test.mp4"
    )
    
    print(f"\n✅ ポップノイズ軽減版動画が作成されました: {output_path}")
    print("話者切り替わり時のブチッという音が軽減されているか確認してください！")

def main():
    """メイン処理"""
    create_no_pop_video()

if __name__ == "__main__":
    main()