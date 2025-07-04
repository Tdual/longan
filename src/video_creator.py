from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
from pathlib import Path
import numpy as np

class VideoCreator:
    def __init__(self):
        pass
    
    def create_slide_video(self, image_path, audio_path=None, duration=5.0):
        """単一のスライドから動画クリップを作成"""
        # 画像クリップを作成
        image_clip = ImageClip(image_path)
        
        if audio_path and Path(audio_path).exists():
            # 音声がある場合は音声の長さに合わせる
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration + 0.5  # 0.5秒の余白を追加
            image_clip = image_clip.set_duration(duration)
            image_clip = image_clip.set_audio(audio_clip)
        else:
            # 音声がない場合は指定された時間
            image_clip = image_clip.set_duration(duration)
        
        return image_clip
    
    def create_video_from_slides(self, image_paths, audio_paths=None, output_path="output.mp4", fps=24):
        """複数のスライドから動画を作成"""
        clips = []
        
        # 音声パスが指定されていない場合は空のリストを作成
        if audio_paths is None:
            audio_paths = [None] * len(image_paths)
        
        # 各スライドのクリップを作成
        for i, (image_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
            print(f"スライド {i+1} の動画クリップを作成中...")
            clip = self.create_slide_video(image_path, audio_path)
            clips.append(clip)
        
        # すべてのクリップを連結
        print("動画を連結中...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        # 動画を出力
        print(f"動画を出力中: {output_path}")
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac'
        )
        
        # リソースを解放
        final_video.close()
        for clip in clips:
            clip.close()
        
        return output_path