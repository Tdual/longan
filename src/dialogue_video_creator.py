from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips, concatenate_videoclips
from moviepy.audio.AudioClip import AudioClip
import numpy as np
from pathlib import Path
from scipy.io import wavfile
from scipy import signal
import tempfile
import os

class DialogueVideoCreator:
    def __init__(self):
        self.temp_files = []  # 一時ファイルのリスト
    
    def create_silence(self, duration, fps=22050):
        """効率的な無音クリップを作成"""
        # 純粋な無音データを作成（ノイズを含まない）
        def make_frame(t):
            # 完全な無音（ステレオ）
            return np.zeros((2,))
        
        # サンプリングレートは音声ファイルと同じにする
        return AudioClip(make_frame, duration=duration, fps=fps)
    
    def crossfade_audio(self, audio1, audio2, fade_duration=0.05):
        """2つの音声クリップをクロスフェードで結合"""
        if audio1.duration <= fade_duration or audio2.duration <= fade_duration:
            # フェード時間が短すぎる場合は通常の結合
            return concatenate_audioclips([audio1, audio2])
        
        # audio1の最後をフェードアウト
        from moviepy.audio.fx.audio_fadeout import audio_fadeout
        audio1_faded = audio_fadeout(audio1, fade_duration)
        
        # audio2の最初をフェードイン
        from moviepy.audio.fx.audio_fadein import audio_fadein
        audio2_faded = audio_fadein(audio2, fade_duration)
        
        # オーバーラップさせて結合
        # audio1の終了時間からfade_duration分戻った位置でaudio2を開始
        audio2_faded = audio2_faded.set_start(audio1.duration - fade_duration)
        
        # CompositeAudioClipで結合
        from moviepy.audio.AudioClip import CompositeAudioClip
        return CompositeAudioClip([audio1_faded, audio2_faded]).set_duration(
            audio1.duration + audio2.duration - fade_duration
        )
    
    def apply_highfreq_filter(self, audio_path):
        """音声ファイルに高周波フィルタを適用してビープ音を除去"""
        try:
            # 音声ファイルを読み込み
            sample_rate, data = wavfile.read(audio_path)
            
            # ステレオの場合は各チャンネルを処理
            if len(data.shape) > 1:
                filtered_data = np.zeros_like(data)
                for channel in range(data.shape[1]):
                    filtered_data[:, channel] = self._apply_aggressive_lowpass_filter(
                        data[:, channel], sample_rate
                    )
            else:
                filtered_data = self._apply_aggressive_lowpass_filter(data, sample_rate)
            
            # 一時ファイルを作成
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # フィルタリングした音声を保存
            wavfile.write(temp_path, sample_rate, filtered_data.astype(data.dtype))
            
            # 一時ファイルを記録
            self.temp_files.append(temp_path)
            return temp_path
            
        except Exception as e:
            print(f"高周波フィルタエラー: {e}")
            return audio_path  # エラーの場合は元のファイルを返す
    
    def _apply_aggressive_lowpass_filter(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """より積極的なローパスフィルタでビープ音を除去"""
        # カットオフ周波数をさらに低く設定：6kHz
        cutoff_freq = 6000
        nyquist_freq = sample_rate / 2
        
        if cutoff_freq >= nyquist_freq:
            return audio_data
        
        # ナイキスト周波数で正規化
        normalized_cutoff = cutoff_freq / nyquist_freq
        
        # より急峻なButterwortフィルタ（次数を8に増加）
        b, a = signal.butter(8, normalized_cutoff, btype='low')
        
        # フィルタを適用
        filtered_audio = signal.filtfilt(b, a, audio_data.astype(np.float64))
        
        # ノッチフィルタを追加で適用（特定のビープ周波数を狙い撃ち）
        # 10-12kHzのビープ音を狙い撃ち
        if sample_rate > 24000:
            notch_freq1 = 10000
            notch_freq2 = 12000
            quality_factor = 30  # Q因子（高いほど狭帯域）
            
            for notch_freq in [notch_freq1, notch_freq2]:
                if notch_freq < nyquist_freq:
                    normalized_notch = notch_freq / nyquist_freq
                    b_notch, a_notch = signal.iirnotch(normalized_notch, quality_factor)
                    filtered_audio = signal.filtfilt(b_notch, a_notch, filtered_audio)
        
        return filtered_audio
    
    def cleanup_temp_files(self):
        """一時ファイルを削除"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                print(f"一時ファイル削除エラー: {e}")
        self.temp_files.clear()
    
    def apply_aggressive_end_processing(self, audio_clip):
        """音声の終わりを積極的に処理してクリック音を除去"""
        try:
            if audio_clip.duration <= 0.1:
                return audio_clip
            
            # 1. 音声の最初と最後に短いフェードを適用（クリック音防止）
            fade_in_duration = min(0.01, audio_clip.duration * 0.05)  # 10ms または 5%
            fade_out_duration = min(0.02, audio_clip.duration * 0.1)  # 20ms または 10%
            
            if audio_clip.duration > fade_in_duration + fade_out_duration:
                # MoviePy 1.0.3では audio_fadein/audio_fadeout を使用
                from moviepy.audio.fx.audio_fadein import audio_fadein
                from moviepy.audio.fx.audio_fadeout import audio_fadeout
                audio_clip = audio_fadein(audio_clip, fade_in_duration)
                audio_clip = audio_fadeout(audio_clip, fade_out_duration)
            
            # 2. 音量を正規化（クリップ防止）
            audio_clip = audio_clip.volumex(0.9)
            
            return audio_clip
            
        except Exception as e:
            print(f"音声処理エラー: {e}")
            return audio_clip
    
    def create_dialogue_slide(self, image_path, audio_infos):
        """対話形式の音声を持つスライドから動画クリップを作成"""
        # 画像クリップを作成
        image_clip = ImageClip(image_path)
        
        if audio_infos and any(info.get("audio_path") for info in audio_infos):
            audio_clips = []
            
            for i, info in enumerate(audio_infos):
                if info.get("audio_path") and Path(info["audio_path"]).exists():
                    # 音声ファイルに高周波フィルタを適用
                    filtered_audio_path = self.apply_highfreq_filter(info["audio_path"])
                    
                    # 音声クリップを読み込み
                    audio_clip = AudioFileClip(filtered_audio_path)
                    
                    # 積極的な音声処理でクリック音を完全除去
                    audio_clip = self.apply_aggressive_end_processing(audio_clip)
                    
                    # 音声クリップ間により長い無音時間を追加（完全分離）
                    if i < len(audio_infos) - 1:  # 最後の音声以外
                        silence_duration = 0.5  # 500ms の無音に延長
                        silence = self.create_silence(silence_duration)
                        # 音声と無音をクロスフェードで結合
                        if audio_clips:
                            combined = self.crossfade_audio(audio_clips[-1], audio_clip)
                            audio_clips = audio_clips[:-1] + [combined]
                            audio_clips.append(silence)
                        else:
                            audio_clips.append(audio_clip)
                            audio_clips.append(silence)
                    else:
                        # 最後の音声
                        if audio_clips:
                            combined = self.crossfade_audio(audio_clips[-1], audio_clip)
                            audio_clips = audio_clips[:-1] + [combined]
                        else:
                            audio_clips.append(audio_clip)
            
            if audio_clips:
                # 音声クリップを連結（既にクロスフェード済み）
                if len(audio_clips) == 1:
                    combined_audio = audio_clips[0]
                else:
                    combined_audio = audio_clips[0]
                    for clip in audio_clips[1:]:
                        if isinstance(clip, AudioClip) and clip.duration > 0:
                            combined_audio = concatenate_audioclips([combined_audio, clip])
                
                # 全体の最後に短い余白を追加
                final_silence_duration = 1.0  # 1秒に短縮
                final_silence = self.create_silence(final_silence_duration)
                combined_audio = self.crossfade_audio(combined_audio, final_silence)
                
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
            preset='faster',  # 処理速度を優先しつつ品質も維持
            threads=16,  # スレッド数を増やして並列処理を強化
            bitrate='1500k',  # ビットレートを少し下げて処理速度改善
            audio_bitrate='192k',  # 音声品質は維持
            temp_audiofile=None,
            remove_temp=True,
            verbose=False,
            logger='bar',
            write_logfile=False,
            ffmpeg_params=[
                '-max_muxing_queue_size', '1024',  # メモリ不足対策
                '-pix_fmt', 'yuv420p'  # QuickTime互換のピクセルフォーマット
            ]
        )
        
        # リソースを解放
        final_video.close()
        for clip in clips:
            clip.close()
        
        # 一時ファイルをクリーンアップ
        self.cleanup_temp_files()
        
        return output_path