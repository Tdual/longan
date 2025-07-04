#!/usr/bin/env python3
import json
import subprocess
import os
from pathlib import Path
from dialogue_video_creator_fixed import DialogueVideoCreatorFixed

class SmartVideoCreator:
    def __init__(self):
        self.fallback_strategies = [
            ("基本版", self.create_basic_video),
            ("簡単な音声結合版", self.create_simple_concat_video),
            ("個別スライド版", self.create_individual_slide_video)
        ]
    
    def check_video_integrity(self, video_path):
        """動画ファイルの健全性をチェック"""
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-show_format', '-show_streams', video_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and 'moov atom not found' not in result.stderr:
                print(f"✅ 動画ファイル {video_path} は正常です")
                return True
            else:
                print(f"❌ 動画ファイル {video_path} に問題があります: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 動画チェック中にエラー: {e}")
            return False
    
    def create_basic_video(self, image_paths, dialogue_audio_info, output_path):
        """基本的な動画作成方法"""
        print("📹 基本版で動画作成中...")
        video_creator = DialogueVideoCreatorFixed()
        return video_creator.create_dialogue_video(image_paths, dialogue_audio_info, output_path)
    
    def create_simple_concat_video(self, image_paths, dialogue_audio_info, output_path):
        """シンプルな音声結合での動画作成"""
        print("📹 簡単な音声結合版で動画作成中...")
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips, concatenate_videoclips
        
        clips = []
        for i, image_path in enumerate(image_paths):
            slide_key = f"slide_{i+1}"
            audio_infos = dialogue_audio_info.get(slide_key, [])
            
            # 画像クリップを作成
            image_clip = ImageClip(image_path)
            
            if audio_infos:
                # すべての音声を単純に結合（無音なし）
                audio_clips = []
                for info in audio_infos:
                    if info.get("audio_path") and Path(info["audio_path"]).exists():
                        audio_clip = AudioFileClip(info["audio_path"])
                        audio_clips.append(audio_clip)
                
                if audio_clips:
                    combined_audio = concatenate_audioclips(audio_clips)
                    duration = combined_audio.duration + 0.5  # 0.5秒の余白のみ
                    image_clip = image_clip.set_duration(duration).set_audio(combined_audio)
                else:
                    image_clip = image_clip.set_duration(3.0)
            else:
                image_clip = image_clip.set_duration(3.0)
            
            clips.append(image_clip)
        
        # 動画を結合
        final_video = concatenate_videoclips(clips, method="compose")
        
        # 出力設定を最小限に
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',  # AACコーデックを使用
            verbose=False,
            logger=None
        )
        
        # リソース解放
        final_video.close()
        for clip in clips:
            clip.close()
        
        return output_path
    
    def create_individual_slide_video(self, image_paths, dialogue_audio_info, output_path):
        """個別スライドで動画作成してから結合"""
        print("📹 個別スライド版で動画作成中...")
        temp_videos = []
        
        try:
            for i, image_path in enumerate(image_paths):
                slide_key = f"slide_{i+1}"
                audio_infos = dialogue_audio_info.get(slide_key, [])
                temp_video = f"temp_slide_{i+1}.mp4"
                
                # 各スライドを個別に作成
                self.create_single_slide_video(image_path, audio_infos, temp_video)
                if self.check_video_integrity(temp_video):
                    temp_videos.append(temp_video)
                else:
                    print(f"⚠️  スライド {i+1} の動画作成に失敗")
            
            if temp_videos:
                # ffmpegで結合
                self.concat_videos_with_ffmpeg(temp_videos, output_path)
                return output_path
            else:
                raise Exception("すべてのスライド動画の作成に失敗")
        
        finally:
            # 一時ファイルを削除
            for temp_video in temp_videos:
                if os.path.exists(temp_video):
                    os.remove(temp_video)
    
    def create_single_slide_video(self, image_path, audio_infos, output_path):
        """単一スライドの動画を作成"""
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips
        
        image_clip = ImageClip(image_path)
        
        if audio_infos:
            audio_clips = []
            for info in audio_infos:
                if info.get("audio_path") and Path(info["audio_path"]).exists():
                    audio_clip = AudioFileClip(info["audio_path"])
                    audio_clips.append(audio_clip)
            
            if audio_clips:
                combined_audio = concatenate_audioclips(audio_clips)
                duration = combined_audio.duration + 0.5
                image_clip = image_clip.set_duration(duration).set_audio(combined_audio)
            else:
                image_clip = image_clip.set_duration(3.0)
        else:
            image_clip = image_clip.set_duration(3.0)
        
        image_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None
        )
        
        image_clip.close()
    
    def concat_videos_with_ffmpeg(self, video_paths, output_path):
        """ffmpegで動画を結合"""
        # 結合リストファイルを作成
        list_file = "concat_list.txt"
        with open(list_file, 'w') as f:
            for video_path in video_paths:
                f.write(f"file '{video_path}'\n")
        
        try:
            subprocess.run([
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_file, 
                '-c', 'copy', output_path, '-y'
            ], check=True, capture_output=True)
        finally:
            if os.path.exists(list_file):
                os.remove(list_file)
    
    def create_video_with_fallback(self, image_paths, dialogue_audio_info, base_output_path="smart_video"):
        """フォールバック機能付きで動画を作成"""
        for i, (strategy_name, strategy_func) in enumerate(self.fallback_strategies):
            output_path = f"{base_output_path}_{i+1}.mp4"
            
            try:
                print(f"\n🎬 戦略 {i+1}: {strategy_name}")
                strategy_func(image_paths, dialogue_audio_info, output_path)
                
                # 動画の健全性をチェック
                if self.check_video_integrity(output_path):
                    print(f"🎉 成功！動画が作成されました: {output_path}")
                    return output_path
                else:
                    print(f"⚠️  {strategy_name}で作成された動画に問題があります")
                    if os.path.exists(output_path):
                        os.remove(output_path)
            
            except Exception as e:
                print(f"❌ {strategy_name}でエラー: {e}")
                if os.path.exists(output_path):
                    os.remove(output_path)
        
        print("😞 すべての戦略が失敗しました")
        return None

def main():
    print("=== スマート動画作成（自動フォールバック機能付き） ===")
    
    # スライド画像のパスを取得
    slides_dir = Path("slides")
    image_paths = sorted([str(p) for p in slides_dir.glob("slide_*.png")])
    
    # 音声ファイル情報を構築
    dialogue_audio_info = {}
    audio_dir = Path("audio_synced")
    
    # 対話形式のナレーションを読み込み
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
    
    # スマート動画作成
    creator = SmartVideoCreator()
    result = creator.create_video_with_fallback(
        image_paths, 
        dialogue_audio_info, 
        "claude_code_smart"
    )
    
    if result:
        print(f"\n✅ 最終的に成功した動画: {result}")
    else:
        print("\n❌ 動画作成に失敗しました")

if __name__ == "__main__":
    main()