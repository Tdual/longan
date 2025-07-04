from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips, concatenate_videoclips, CompositeVideoClip, CompositeAudioClip
from pathlib import Path
import numpy as np

class DialogueVideoCreatorImproved:
    def __init__(self):
        pass
    
    def create_dialogue_slide(self, image_path, audio_infos):
        """対話形式の音声を持つスライドから動画クリップを作成（音声途切れ改善版）"""
        # 画像クリップを作成
        image_clip = ImageClip(image_path)
        
        if audio_infos and any(info.get("audio_path") for info in audio_infos):
            # 音声クリップと無音部分を交互に配置
            audio_clips = []
            for i, info in enumerate(audio_infos):
                if info.get("audio_path") and Path(info["audio_path"]).exists():
                    audio_clip = AudioFileClip(info["audio_path"])
                    
                    # 音声の最後に0.2秒の余白を追加（音声途切れ防止）
                    silence_after = AudioFileClip(info["audio_path"]).subclip(0, 0.01).volumex(0).set_duration(0.2)
                    audio_with_padding = concatenate_audioclips([audio_clip, silence_after])
                    audio_clips.append(audio_with_padding)
                    
                    # 最後の音声でなければ、0.8秒の無音を追加（対話間の間を長く）
                    if i < len(audio_infos) - 1:
                        silence_duration = 0.8
                        silence = AudioFileClip(info["audio_path"]).subclip(0, 0.01).volumex(0).set_duration(silence_duration)
                        audio_clips.append(silence)
            
            if audio_clips:
                # すべての音声を連結
                combined_audio = concatenate_audioclips(audio_clips)
                # 全体の最後に1.5秒の余白を追加
                final_silence = AudioFileClip(audio_infos[0]["audio_path"]).subclip(0, 0.01).volumex(0).set_duration(1.5)
                combined_audio = concatenate_audioclips([combined_audio, final_silence])
                
                duration = combined_audio.duration
                image_clip = image_clip.set_duration(duration)
                image_clip = image_clip.set_audio(combined_audio)
            else:
                # 音声がない場合
                image_clip = image_clip.set_duration(5.0)
        else:
            # 音声情報がない場合
            image_clip = image_clip.set_duration(5.0)
        
        return image_clip
    
    def create_dialogue_video(self, image_paths, dialogue_audio_info, output_path="dialogue_output.mp4", fps=24):
        """対話形式の動画を作成（音声途切れ改善版）"""
        clips = []
        
        # 各スライドのクリップを作成
        for i, image_path in enumerate(image_paths):
            slide_key = f"slide_{i+1}"
            audio_infos = dialogue_audio_info.get(slide_key, [])
            
            print(f"スライド {i+1} の動画クリップを作成中（改善版）...")
            clip = self.create_dialogue_slide(image_path, audio_infos)
            clips.append(clip)
        
        # すべてのクリップを連結
        print("動画を連結中...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        # 動画を出力（音声コーデックをPCMに設定）
        print(f"改善版動画を出力中: {output_path}")
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio_codec='pcm_s16le',  # WAVファイルに適したコーデック
            temp_audiofile='temp-audio-improved.wav',
            remove_temp=True,
            verbose=False,  # ログを簡潔に
            logger='bar'
        )
        
        # リソースを解放
        final_video.close()
        for clip in clips:
            clip.close()
        
        return output_path