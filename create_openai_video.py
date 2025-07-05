#!/usr/bin/env python3
"""OpenAI APIを使った完全な動画生成ワークフロー"""

import sys
from pathlib import Path
import json
import os
from dotenv import load_dotenv

# srcディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent / "src"))

from pdf_converter import PDFConverter
from api.core.text_extractor import TextExtractor
from api.core.dialogue_generator import DialogueGenerator
from api.core.katakana_converter import KatakanaConverter
from voicevox_generator import VoicevoxGenerator
from dialogue_video_creator import DialogueVideoCreator

# 環境変数を読み込み
load_dotenv()

def main():
    print("=== OpenAI APIを使った動画生成 ===")
    
    pdf_path = "Claude Code セミナー.pdf"
    
    # 1. PDFをスライドに変換
    print("\n1. PDFをスライド画像に変換中...")
    converter = PDFConverter("slides")
    slide_paths = converter.convert_pdf_to_images(pdf_path)
    print(f"   {len(slide_paths)}枚のスライドを生成しました")
    
    # 2. PDFからテキストを抽出
    print("\n2. PDFからテキストを抽出中...")
    extractor = TextExtractor()
    slide_texts = extractor.extract_text_from_pdf(pdf_path)
    print(f"   {len(slide_texts)}スライドのテキストを抽出しました")
    
    # 3. OpenAI APIで対話を生成
    print("\n3. OpenAI APIで対話を生成中...")
    dialogue_generator = DialogueGenerator()
    dialogue_data = dialogue_generator.extract_text_from_slides(slide_texts)
    print("   対話生成が完了しました")
    
    # 4. 英単語をカタカナに変換
    print("\n4. 英単語をカタカナに変換中...")
    katakana_converter = KatakanaConverter()
    dialogue_data_katakana = katakana_converter.convert_dialogue_to_katakana(dialogue_data)
    
    # 5. 対話データを保存
    print("\n5. 対話データを保存中...")
    with open("data/dialogue_narration_katakana.json", "w", encoding="utf-8") as f:
        json.dump(dialogue_data_katakana, f, ensure_ascii=False, indent=2)
    
    with open("data/dialogue_narration_original.json", "w", encoding="utf-8") as f:
        json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
    
    print("   対話データを保存しました")
    
    # 6. VOICEVOX で音声生成
    print("\n6. VOICEVOX で音声生成中...")
    audio_generator = VoicevoxGenerator()
    audio_generator.generate_dialogue_audio(
        dialogue_data_katakana,
        "audio",
        speed_scale=1.0,
        pitch_scale=0.0,
        intonation_scale=1.2,  # 表現豊か
        volume_scale=1.0
    )
    print("   音声生成が完了しました")
    
    # 7. 動画作成
    print("\n7. 動画を作成中...")
    
    # 音声ファイル情報を構築
    dialogue_audio_info = {}
    for i, slide_path in enumerate(slide_paths):
        slide_num = i + 1
        slide_key = f"slide_{slide_num}"
        dialogue_audio_info[slide_key] = []
        
        if slide_key in dialogue_data_katakana:
            for j, dialogue in enumerate(dialogue_data_katakana[slide_key]):
                speaker = dialogue["speaker"]
                audio_file = f"audio/slide_{slide_num:03d}_{j+1:03d}_{speaker}.wav"
                if Path(audio_file).exists():
                    dialogue_audio_info[slide_key].append({
                        "speaker": speaker,
                        "audio_path": audio_file
                    })
    
    # 動画作成
    video_creator = DialogueVideoCreator()
    output_path = "output/openai_generated_video.mp4"
    
    video_creator.create_dialogue_video(
        slide_paths,
        dialogue_audio_info,
        output_path
    )
    
    print(f"\n✅ 完成！動画を保存しました: {output_path}")
    
    # ファイルサイズを表示
    if Path(output_path).exists():
        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"   ファイルサイズ: {size_mb:.1f}MB")

if __name__ == "__main__":
    main()