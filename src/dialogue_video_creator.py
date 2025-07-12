from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips, concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip
import numpy as np
from pathlib import Path

class DialogueVideoCreator:
    def __init__(self):
        pass
    
    def create_silence(self, duration, fps=22050):
        """効率的な無音クリップを作成"""
        # 実際の音声ファイルからテンプレートを作って無音を生成（より確実）
        from moviepy.editor import AudioFileClip
        
        # 最初の音声ファイルをテンプレートとして使用
        template_files = list(Path("audio").glob("**/*.wav"))
        if template_files:
            template_audio = AudioFileClip(str(template_files[0]))
            silence = template_audio.subclip(0, min(0.1, template_audio.duration)).volumex(0).set_duration(duration)
            template_audio.close()
            return silence
        else:
            # フォールバック: 直接作成
            def make_frame(t):
                return np.array([0.0, 0.0])
            return AudioClip(make_frame, duration=duration, fps=fps)
    
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
                    
                    # パフォーマンス向上のため無音処理をスキップ
                    # 各音声クリップ間の無音は除去し、連続再生する
            
            if audio_clips:
                # すべての音声を連結
                combined_audio = concatenate_audioclips(audio_clips)
                
                # 全体の最後に短い余白を追加
                final_silence_duration = 1.0  # 1秒に短縮
                # 最後の音声クリップを使って無音を作成
                if audio_clips:
                    last_audio = audio_clips[0]  # 最初の音声を使用
                    final_silence = last_audio.subclip(0, min(0.1, last_audio.duration)).volumex(0).set_duration(final_silence_duration)
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
        # Docker環境での最適化（高画質版）
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            preset='faster',  # 処理速度を優先しつつ品質も維持
            threads=16,  # スレッド数を増やして並列処理を強化
            bitrate='1500k',  # ビットレートを少し下げて処理速度改善
            audio_bitrate='192k',  # 音声品質は維持
            temp_audiofile=None,
            remove_temp=True,
            verbose=False,
            logger='bar',
            write_logfile=False,
            ffmpeg_params=['-max_muxing_queue_size', '1024']  # メモリ不足対策
        )
        
        # リソースを解放
        final_video.close()
        for clip in clips:
            clip.close()
        
        return output_path