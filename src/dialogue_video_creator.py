from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips, concatenate_videoclips
from pathlib import Path

class DialogueVideoCreator:
    def __init__(self):
        pass
    
    def apply_end_fade(self, audio_clip):
        """音声の終わりに短いフェードアウトを適用"""
        try:
            fade_duration = 0.05  # 50ms のフェードアウト
            
            if audio_clip.duration > fade_duration:
                # 終わりにのみフェードアウトを適用
                audio_clip = audio_clip.audio_fadeout(fade_duration)
            
            return audio_clip
            
        except Exception as e:
            print(f"フェードアウト適用エラー: {e}")
            return audio_clip
    
    def create_dialogue_slide(self, image_path, audio_infos):
        """対話形式の音声を持つスライドから動画クリップを作成"""
        # 画像クリップを作成
        image_clip = ImageClip(image_path)
        
        if audio_infos and any(info.get("audio_path") for info in audio_infos):
            audio_clips = []
            
            for i, info in enumerate(audio_infos):
                if info.get("audio_path") and Path(info["audio_path"]).exists():
                    # 音声クリップを読み込み
                    audio_clip = AudioFileClip(info["audio_path"])
                    
                    # 音量を少し下げる
                    audio_clip = audio_clip.volumex(0.9)
                    
                    # 終わりにフェードアウトを適用（ブチッ音対策）
                    audio_clip = self.apply_end_fade(audio_clip)
                    
                    audio_clips.append(audio_clip)
                    
                    # 最後の音声でなければ、短めの無音を追加
                    if i < len(audio_infos) - 1:
                        silence_duration = 0.8  # 0.8秒に短縮
                        # シンプルな無音作成
                        silence = AudioFileClip(info["audio_path"]).subclip(0, 0.02).volumex(0).set_duration(silence_duration)
                        audio_clips.append(silence)
            
            if audio_clips:
                # すべての音声を連結
                combined_audio = concatenate_audioclips(audio_clips)
                
                # 全体の最後に短い余白を追加
                final_silence_duration = 1.0  # 1秒に短縮
                final_silence = AudioFileClip(audio_infos[0]["audio_path"]).subclip(0, 0.02).volumex(0).set_duration(final_silence_duration)
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
        """対話形式の動画を作成"""
        clips = []
        
        # 各スライドのクリップを作成
        for i, image_path in enumerate(image_paths):
            slide_key = f"slide_{i+1}"
            audio_infos = dialogue_audio_info.get(slide_key, [])
            
            print(f"スライド {i+1} の動画クリップを作成中...")
            clip = self.create_dialogue_slide(image_path, audio_infos)
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
            audio_codec='pcm_s16le',  # PCMコーデック
            temp_audiofile='temp-audio.wav',
            remove_temp=True,
            verbose=False,
            logger='bar'
        )
        
        # リソースを解放
        final_video.close()
        for clip in clips:
            clip.close()
        
        return output_path