#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

def organize_files():
    """ファイル構造を整理する"""
    
    # 新しいディレクトリ構造を作成
    directories = {
        'src': 'ソースコード',
        'data': 'データファイル',
        'output': '出力ファイル',
        'scripts': 'スクリプト',
        'temp': '一時ファイル'
    }
    
    # ディレクトリを作成
    for dir_name in directories.keys():
        Path(dir_name).mkdir(exist_ok=True)
    
    # ファイル移動計画
    move_plan = {
        # ソースコード
        'src': [
            'pdf_converter.py',
            'audio_generator.py', 
            'video_creator.py',
            'voicevox_generator.py',
            'dialogue_video_creator_fixed.py',
            'dialogue_video_creator_improved.py',
            'smart_video_creator.py',
            'english_to_katakana.py',
            'extract_english_words.py'
        ],
        
        # データファイル
        'data': [
            'dialogue_narration_katakana.json',
            'dialogue_narration_synced.json',
            'english_words_detected.json',
            'requirements.txt'
        ],
        
        # 出力ファイル（既存のoutputディレクトリと統合）
        'output': [
            'claude_code_katakana_test.mp4',
            'claude_code_dialogue_fixed.mp4',
            'claude_code_smart_1.mp4'
        ],
        
        # スクリプト
        'scripts': [
            'generate_katakana_audio_simple.py',
            'create_katakana_test_video.py',
            'create_improved_video.py',
            'install.sh',
            'run_demo.sh'
        ]
    }
    
    # 削除するファイル（古いバージョンや不要なファイル）
    files_to_remove = [
        # 古いバージョンのファイル
        'create_dialogue_video.py',
        'create_dialogue_video_avatars.py',
        'create_dialogue_video_avatars_simple.py',
        'create_funny_dialogue_video.py',
        'create_funny_video_from_audio.py',
        'create_synced_dialogue_video.py',
        'create_synced_funny_video_clean.py',
        'create_synced_video_from_audio.py',
        'create_synced_video_simple.py',
        'create_partial_synced_video.py',
        'create_sample_pdf.py',
        'create_simple_animated_avatars.py',
        'create_avatar_placeholders.py',
        'create_animated_test.py',
        'create_final_funny_video.py',
        'create_working_video.py',
        'test_minimal_video.py',
        'test_video_creation.py',
        'generate_video_only.py',
        'replace_audio_with_funny.py',
        'generate_remaining_audio.py',
        'add_avatars_to_existing.py',
        
        # 古いダイアログクリエーター
        'dialogue_video_creator.py',
        'dialogue_video_creator_animated.py',
        'dialogue_video_creator_avatars_simple.py',
        'dialogue_video_creator_with_avatars.py',
        'dialogue_voicevox_generator.py',
        
        # 古いナレーションファイル
        'claude_code_narration.json',
        'claude_code_narration_v2.json',
        'dialogue_narration.json',
        'dialogue_narration_funny.json',
        'sample_narration.json',
        
        # 古いスクリプト
        'check_and_generate.sh',
        'generate_without_voicevox.sh',
        'generate_zundamon_fixed.sh',
        'start_voicevox_and_generate.sh',
        
        # 古いメインファイル
        'main.py',
        'main_voicevox.py',
        
        # 一時ファイル
        'temp-audio-improved.wav',
        
        # 古い動画ファイル
        'claude_code_dialogue.mp4',
        'claude_code_dialogue_funny_clean.mp4',
        'claude_code_dialogue_with_avatarsTEMP_MPY_wvf_snd.mp4',
        'claude_code_funny_final.mp4',
        'claude_code_improved_final.mp4',
        'claude_code_seminar.mp4',
        'claude_code_seminar_v2.mp4',
        'claude_code_working_video.mp4',
        'claude_code_zundamon.mp4',
        'test_minimal.mp4',
        'test_synced_video.mp4'
    ]
    
    return move_plan, files_to_remove

def execute_organization():
    """実際にファイル整理を実行"""
    move_plan, files_to_remove = organize_files()
    
    print("=== ファイル構造整理開始 ===")
    
    # ディレクトリ作成
    for dir_name in move_plan.keys():
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ ディレクトリ作成: {dir_name}/")
    
    # ファイル移動
    moved_count = 0
    for target_dir, files in move_plan.items():
        for file_name in files:
            if Path(file_name).exists():
                try:
                    shutil.move(file_name, f"{target_dir}/{file_name}")
                    print(f"📁 移動: {file_name} → {target_dir}/")
                    moved_count += 1
                except Exception as e:
                    print(f"❌ 移動失敗: {file_name} - {e}")
    
    # 不要ファイル削除
    removed_count = 0
    for file_name in files_to_remove:
        if Path(file_name).exists():
            try:
                os.remove(file_name)
                print(f"🗑️  削除: {file_name}")
                removed_count += 1
            except Exception as e:
                print(f"❌ 削除失敗: {file_name} - {e}")
    
    print(f"\n=== 整理完了 ===")
    print(f"移動したファイル: {moved_count}")
    print(f"削除したファイル: {removed_count}")
    
    # 整理後の構造を表示
    print(f"\n=== 新しい構造 ===")
    for dir_name in ['src', 'data', 'scripts', 'output']:
        if Path(dir_name).exists():
            files = list(Path(dir_name).glob('*'))
            print(f"{dir_name}/ ({len(files)} files)")
            for f in sorted(files):
                print(f"  - {f.name}")

if __name__ == "__main__":
    execute_organization()