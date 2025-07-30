from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips, concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from scipy import signal
import os
import tempfile

class DialogueVideoCreator:
    def __init__(self):
        self.temp_files = []
    
    def create_silence(self, duration):
        """無音クリップを作成"""
        # サンプリングレート 24000 Hz (VOICEVOXと統一)
        sample_rate = 24000
        # 完全な無音（振幅0）の配列を作成
        silence_array = np.zeros((int(sample_rate * duration), 2))  # ステレオ
        
        # AudioArrayClipとして作成
        from moviepy.audio.AudioClip import AudioArrayClip
        return AudioArrayClip(silence_array, fps=sample_rate)
    
    def apply_highfreq_filter(self, audio_path):
        """音声ファイルに高周波フィルタを適用してビープ音を除去"""
        # フィルタ処理を無効化（audio_generator.pyで既に処理済み）
        return audio_path
    
    
    def cleanup_temp_files(self):
        """一時ファイルを削除"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"一時ファイル削除エラー: {e}")
        self.temp_files.clear()
    
    def create_dialogue_slide(self, image_path, audio_infos):
        """対話形式の音声を持つスライドから動画クリップを作成（改善版）"""
        # 画像クリップを作成
        image_clip = ImageClip(image_path)
        
        # H.264エンコーディングのため、幅と高さを偶数にする
        if image_clip.w % 2 != 0 or image_clip.h % 2 != 0:
            # PILのANTIALIAS互換性問題を回避するため、リサイズではなくクロップを使用
            new_width = image_clip.w if image_clip.w % 2 == 0 else image_clip.w - 1
            new_height = image_clip.h if image_clip.h % 2 == 0 else image_clip.h - 1
            image_clip = image_clip.crop(x1=0, y1=0, x2=new_width, y2=new_height)
        
        if audio_infos and any(info.get("audio_path") for info in audio_infos):
            audio_clips = []
            
            for i, info in enumerate(audio_infos):
                if info.get("audio_path") and Path(info["audio_path"]).exists():
                    # 音声ファイルに高周波フィルタを適用
                    filtered_audio_path = self.apply_highfreq_filter(info["audio_path"])
                    
                    # 音声クリップを読み込み（24kHzに統一）
                    audio_clip = AudioFileClip(filtered_audio_path, fps=24000)
                    
                    # 音声の開始と終了に非常に短いフェードを適用（クリック音防止）
                    fade_duration = 0.02  # 20ms（より自然に）
                    if audio_clip.duration > fade_duration * 2:
                        from moviepy.audio.fx.audio_fadein import audio_fadein
                        from moviepy.audio.fx.audio_fadeout import audio_fadeout
                        audio_clip = audio_fadein(audio_clip, fade_duration)
                        audio_clip = audio_fadeout(audio_clip, fade_duration)
                    
                    # 音量を正規化（クリッピング防止）
                    audio_clip = audio_clip.volumex(0.95)
                    
                    # 音声をリストに追加
                    audio_clips.append(audio_clip)
                    
                    # 話者交代の間を追加（最後の音声以外）
                    if i < len(audio_infos) - 1:
                        silence_duration = 0.3  # 300msの自然な間
                        silence = self.create_silence(silence_duration)
                        audio_clips.append(silence)
            
            if audio_clips:
                # 全ての音声クリップを単純に連結
                combined_audio = concatenate_audioclips(audio_clips)
                
                # 全体の最後に短い余白を追加
                final_silence_duration = 0.5  # 0.5秒
                final_silence = self.create_silence(final_silence_duration)
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
        final_video = concatenate_videoclips(clips)
        
        # 動画全体の最後に長めのフェードアウトを追加（完全にブチっという音を防ぐ）
        fade_duration = 1.0  # 1.0秒のフェードアウトに延長
        if final_video.duration > fade_duration:
            # MoviePy 1.0.3では fx.fadeout を使用
            from moviepy.video.fx.fadeout import fadeout
            final_video = fadeout(final_video, fade_duration)
        
        # 動画を出力
        print(f"動画を出力中: {output_path}")
        # Docker環境での最適化（高画質版・QuickTime互換）
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',
            audio_fps=24000,  # 音声サンプリングレートを24kHzに統一
            preset='faster',  # 処理速度を優先しつつ品質も維持
            threads=16,  # スレッド数を増やして並列処理を強化
            bitrate='1500k',  # ビットレートを少し下げて処理速度改善
            audio_bitrate='192k',  # 音声品質は維持
            temp_audiofile=None,
            remove_temp=True,
            ffmpeg_params=[
                '-max_muxing_queue_size', '1024',  # メモリ不足対策
                '-pix_fmt', 'yuv420p'  # QuickTime互換のピクセルフォーマット
            ]
        )
        
        # 一時ファイルのクリーンアップ
        self.cleanup_temp_files()
        
        print(f"動画出力完了: {output_path}")