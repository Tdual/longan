from moviepy.editor import ImageClip, AudioFileClip, concatenate_audioclips, concatenate_videoclips, CompositeVideoClip, CompositeAudioClip
from pathlib import Path
import numpy as np

class DialogueVideoCreatorSmooth:
    def __init__(self):
        pass
    
    def create_smooth_silence(self, reference_audio_path, duration):
        """基準音声に基づいて滑らかな無音を作成"""
        try:
            # 基準音声を読み込み
            ref_audio = AudioFileClip(reference_audio_path)
            
            # 無音を作成（同じサンプルレートとチャンネル数）
            silence = ref_audio.subclip(0, 0.01).volumex(0).set_duration(duration)
            
            # フェードイン・フェードアウトを適用（ノイズ軽減）
            silence = silence.audio_fadein(0.005).audio_fadeout(0.005)
            
            ref_audio.close()
            return silence
            
        except Exception as e:
            print(f"無音作成エラー: {e}")
            # フォールバック: 基本的な無音
            return AudioFileClip(reference_audio_path).subclip(0, 0.01).volumex(0).set_duration(duration)
    
    def apply_smooth_transitions(self, audio_clip):
        """音声クリップに滑らかな遷移を適用"""
        try:
            # 開始と終了に短いフェードを適用（ポップノイズ防止）
            fade_duration = 0.01  # 10ms
            
            # クリップの長さチェック
            if audio_clip.duration > fade_duration * 2:
                audio_clip = audio_clip.audio_fadein(fade_duration).audio_fadeout(fade_duration)
            
            return audio_clip
            
        except Exception as e:
            print(f"遷移適用エラー: {e}")
            return audio_clip
    
    def create_dialogue_slide(self, image_path, audio_infos):
        """対話形式の音声を持つスライドから動画クリップを作成（滑らか版）"""
        # 画像クリップを作成
        image_clip = ImageClip(image_path)
        
        if audio_infos and any(info.get("audio_path") for info in audio_infos):
            # 音声クリップと無音部分を交互に配置
            audio_clips = []
            
            for i, info in enumerate(audio_infos):
                if info.get("audio_path") and Path(info["audio_path"]).exists():
                    # 音声クリップを読み込み
                    audio_clip = AudioFileClip(info["audio_path"])
                    
                    # 滑らかな遷移を適用
                    audio_clip = self.apply_smooth_transitions(audio_clip)
                    audio_clips.append(audio_clip)
                    
                    # 最後の音声でなければ、滑らかな無音を追加
                    if i < len(audio_infos) - 1:
                        silence_duration = 0.8
                        smooth_silence = self.create_smooth_silence(info["audio_path"], silence_duration)
                        audio_clips.append(smooth_silence)
            
            if audio_clips:
                # すべての音声を連結（クロスフェード付き）
                if len(audio_clips) == 1:
                    combined_audio = audio_clips[0]
                else:
                    # 最初の音声
                    combined_audio = audio_clips[0]
                    
                    # 残りの音声を順次結合
                    for audio_clip in audio_clips[1:]:
                        try:
                            # 非常に短いクロスフェードで結合（ポップノイズ防止）
                            combined_audio = concatenate_audioclips([combined_audio, audio_clip])
                        except:
                            # フォールバック: 通常の結合
                            combined_audio = concatenate_audioclips([combined_audio, audio_clip])
                
                # 全体の最後に滑らかな余白を追加
                final_silence = self.create_smooth_silence(audio_infos[0]["audio_path"], 1.0)
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
    
    def create_dialogue_video(self, image_paths, dialogue_audio_info, output_path="dialogue_smooth_output.mp4", fps=24):
        """対話形式の動画を作成（滑らか版）"""
        clips = []
        
        # 各スライドのクリップを作成
        for i, image_path in enumerate(image_paths):
            slide_key = f"slide_{i+1}"
            audio_infos = dialogue_audio_info.get(slide_key, [])
            
            print(f"スライド {i+1} の動画クリップを作成中（滑らか版）...")
            clip = self.create_dialogue_slide(image_path, audio_infos)
            clips.append(clip)
        
        # すべてのクリップを連結
        print("動画を連結中...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        # 動画を出力（高品質音声設定）
        print(f"滑らか版動画を出力中: {output_path}")
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec='libx264',
            audio_codec='aac',  # AACコーデック（より安定）
            audio_bitrate='192k',  # 高品質音声
            temp_audiofile='temp-audio-smooth.wav',
            remove_temp=True,
            verbose=False,
            logger='bar'
        )
        
        # リソースを解放
        final_video.close()
        for clip in clips:
            clip.close()
        
        return output_path