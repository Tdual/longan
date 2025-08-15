import sys
from pathlib import Path
import json
import requests
import os
import numpy as np
from scipy.io import wavfile
from scipy import signal
import librosa
import soundfile as sf
import noisereduce as nr

# srcディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from voicevox_generator import VoicevoxGenerator

class ImprovedAudioProcessor:
    """ビーン音除去とクリック音除去の改善されたプロセッサー"""
    
    def __init__(self, sample_rate=24000):
        self.sample_rate = sample_rate
        # ビーン音の周波数帯域（分析結果に基づく）
        self.beep_freq_range = (800, 3500)
        
    def remove_click_noise(self, audio_data):
        """VOICEVOXのクリック音を除去（テンポ維持）"""
        if len(audio_data) == 0:
            return audio_data
            
        # 1. 急激な振幅変化を検出
        audio_diff = np.diff(audio_data)
        if len(audio_diff) > 0:
            sudden_changes = np.abs(audio_diff) > np.std(audio_diff) * 5
            
            # 2. 急激な変化部分をスムージング
            for i in np.where(sudden_changes)[0]:
                if i > 5 and i < len(audio_data) - 5:
                    # 前後5サンプルの平均で補間
                    audio_data[i] = np.mean(audio_data[i-5:i+5])
        
        return audio_data
    
    def apply_spectral_gating(self, audio_data, sr=None):
        """スペクトルゲーティングによるビープ音除去（改善版）"""
        if len(audio_data) == 0:
            return audio_data
            
        if sr is None:
            sr = self.sample_rate
            
        try:
            # 2段階処理で強いビープ音にも対応
            
            # ステップ1: 300-400Hz帯域の強いビープ音を重点的に除去
            # より強い設定でビープ音帯域を処理
            reduced_noise_step1 = nr.reduce_noise(
                y=audio_data, 
                sr=sr,
                stationary=True,  # 定常ノイズ（ビープ音）に最適
                prop_decrease=0.85,  # ノイズを85%減衰（より強め）
                freq_mask_smooth_hz=200,  # 周波数マスクを狭めて精密に
                time_mask_smooth_ms=50,  # 時間マスクも狭めて応答性向上
                y_noise=None,  # 自動でノイズプロファイルを学習
                n_fft=2048  # FFTサイズを指定（周波数分解能向上）
            )
            
            # ステップ2: 全体的な微調整（音質保持）
            reduced_noise = nr.reduce_noise(
                y=reduced_noise_step1,  # ステップ1の結果を入力
                sr=sr,
                stationary=False,  # 非定常ノイズも考慮
                prop_decrease=0.5,  # 控えめに微調整
                freq_mask_smooth_hz=800,  # 広めのスムージングで自然さを保持
                time_mask_smooth_ms=150,  # 時間的な滑らかさを確保
                n_fft=2048
            )
            
            print("スペクトルゲーティング適用完了（2段階処理・改善版）")
            return reduced_noise.astype(np.float32)
            
        except Exception as e:
            print(f"スペクトルゲーティングエラー: {e}")
            # エラー時は元データをそのまま返す
            return audio_data
    
    def apply_beep_notch_filter_fallback(self, audio_data):
        """フォールバック用の簡易ノッチフィルタ"""
        if len(audio_data) == 0:
            return audio_data
            
        # 低周波ビープ音をターゲット（300-500Hz）
        target_freqs = [300, 350, 400, 450, 500]
        
        for freq in target_freqs:
            try:
                # 低周波用に調整したQ値
                Q = 20.0  # 低周波では少し広めに
                w = freq / (self.sample_rate / 2)
                
                if w >= 1.0:
                    continue
                    
                b, a = signal.iirnotch(w, Q)
                audio_data = signal.filtfilt(b, a, audio_data.astype(np.float64))
            except Exception as e:
                print(f"ノッチフィルタエラー（{freq}Hz）: {e}")
                continue
        
        return audio_data.astype(np.float32)
    
    def smart_fade(self, audio_data, fade_in_ms=50, fade_out_ms=50):
        """スマートフェード：音声の特性に応じて最適化"""
        if len(audio_data) == 0:
            return audio_data
            
        fade_in_samples = int(fade_in_ms * self.sample_rate / 1000)
        fade_out_samples = int(fade_out_ms * self.sample_rate / 1000)
        
        # サンプル数がフェード長より短い場合は調整
        fade_in_samples = min(fade_in_samples, len(audio_data) // 4)
        fade_out_samples = min(fade_out_samples, len(audio_data) // 4)
        
        # フェードイン：コサイン関数で自然な立ち上がり
        if fade_in_samples > 0:
            fade_in_curve = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_in_samples)))
            audio_data[:fade_in_samples] *= fade_in_curve
            
        # フェードアウト：コサイン関数で自然な終了
        if fade_out_samples > 0:
            fade_out_curve = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_out_samples)))
            audio_data[-fade_out_samples:] *= fade_out_curve
            
        return audio_data
    
    def process_voicevox_audio(self, input_path, output_path=None):
        """VOICEVOXの音声を後処理（noisereduceのみ使用）"""
        try:
            # 音声を読み込み（元のサンプリングレートを維持）
            audio_data, sr = librosa.load(input_path, sr=None, mono=True)
            
            if len(audio_data) == 0:
                print(f"警告: 空の音声ファイル {input_path}")
                return input_path
            
            # noisereduceのみでビープ音除去
            audio_data = self.apply_spectral_gating(audio_data, sr)
            
            # 音量正規化（クリッピング防止）
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data * 0.95 / max_val
            
            # 保存
            if output_path is None:
                output_path = input_path  # 上書き
                
            # soundfileで保存（元のサンプリングレート維持）
            sf.write(output_path, audio_data, sr)
            print(f"音声後処理完了: {output_path} (SR: {sr}Hz)")
            
            return output_path
            
        except Exception as e:
            print(f"音声後処理エラー {input_path}: {e}")
            return input_path  # エラー時は元ファイルを返す

class AudioGenerator:
    def __init__(self, job_id: str, base_dir: Path):
        self.job_id = job_id
        self.base_dir = base_dir
        self.audio_dir = base_dir / "audio" / job_id
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.voicevox_url = os.getenv("VOICEVOX_URL", "http://localhost:50021")
        # 改善されたオーディオプロセッサーを初期化
        self.audio_processor = ImprovedAudioProcessor()
        
    def check_voicevox_status(self) -> bool:
        """VOICEVOXが起動しているか確認"""
        try:
            response = requests.get(f"{self.voicevox_url}/version")
            return response.status_code == 200
        except:
            return False
    
    def generate_audio_files(
        self,
        speed_scale: float = 1.0,
        pitch_scale: float = 0.0,
        intonation_scale: float = 1.2,
        volume_scale: float = 1.0
    ) -> int:
        """対話音声を生成"""
        
        # VOICEVOXチェック
        if not self.check_voicevox_status():
            raise Exception("VOICEVOXが起動していません")
        
        # 対話データを読み込み
        # まずジョブ固有のデータを探す
        job_dialogue_path = self.base_dir / "data" / self.job_id / "dialogue_narration_katakana.json"
        if job_dialogue_path.exists():
            dialogue_data_path = job_dialogue_path
        else:
            # 見つからない場合はデフォルトを使用
            dialogue_data_path = Path(__file__).parent.parent.parent / "data" / "dialogue_narration_katakana.json"
        
        with open(dialogue_data_path, "r", encoding="utf-8") as f:
            dialogue_data = json.load(f)
        
        print(f"音声生成: 対話データを読み込みました - {dialogue_data_path}")
        print(f"音声生成: スライド数 = {len(dialogue_data)}")
        
        # メタデータからスピーカー設定を読み込む
        metadata_path = self.base_dir / "uploads" / self.job_id / "metadata.json"
        speaker_info = {}
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            speakers = {
                "speaker1": metadata.get("speaker1", {}).get("id", 2),
                "speaker2": metadata.get("speaker2", {}).get("id", 3)
            }
            speaker_info = {
                "speaker1": metadata.get("speaker1", {}),
                "speaker2": metadata.get("speaker2", {})
            }
        else:
            # デフォルト設定
            speakers = {
                "speaker1": 2,    # 四国めたん
                "speaker2": 3     # ずんだもん
            }
        
        audio_count = 0
        
        # 各スライドの音声を生成
        for slide_key, dialogues in dialogue_data.items():
            if not dialogues:
                continue
            
            for idx, dialogue in enumerate(dialogues):
                speaker = dialogue["speaker"]
                text = dialogue["text"]
                
                if not text.strip():
                    continue
                
                # スピーカーIDを取得
                speaker_id = speakers.get(speaker, 3)
                speaker_name = speaker
                
                # ファイル名を生成
                slide_num = slide_key.replace("slide_", "")
                try:
                    slide_num_int = int(slide_num)
                    audio_filename = f"slide_{slide_num_int:03d}_{idx+1:03d}_{speaker_name}.wav"
                except ValueError:
                    # 数値に変換できない場合はそのまま使用
                    audio_filename = f"slide_{slide_num}_{idx+1:03d}_{speaker_name}.wav"
                
                # 音声クエリの作成
                query_data = {
                    "text": text,
                    "speaker": speaker_id
                }
                
                query_response = requests.post(
                    f"{self.voicevox_url}/audio_query",
                    params=query_data
                )
                
                if query_response.status_code != 200:
                    raise Exception(f"音声クエリの作成に失敗: {query_response.status_code}")
                
                # 音声合成パラメータを調整
                synthesis_data = query_response.json()
                
                # キャラクターごとの速度調整
                current_speaker_info = speaker_info.get(speaker, {})
                # メタデータに速度が設定されている場合はそれを使用
                if current_speaker_info.get("speed"):
                    current_speed_scale = speed_scale * current_speaker_info.get("speed", 1.0)
                else:
                    # 速度が設定されていない場合、九州そらはデフォルトで1.2倍速
                    current_speed_scale = speed_scale
                    if current_speaker_info.get("name") == "九州そら":
                        current_speed_scale = speed_scale * 1.2
                
                # 標準パラメータ（noisereduceに任せる）
                synthesis_data["speedScale"] = current_speed_scale
                synthesis_data["pitchScale"] = pitch_scale
                synthesis_data["intonationScale"] = intonation_scale
                synthesis_data["volumeScale"] = volume_scale
                
                # 音声の前後に短い無音を追加（クリック音防止）
                synthesis_data["prePhonemeLength"] = 0.1  # 音声前の無音（秒）
                synthesis_data["postPhonemeLength"] = 0.1  # 音声後の無音（秒）
                
                synthesis_response = requests.post(
                    f"{self.voicevox_url}/synthesis",
                    params={
                        "speaker": speaker_id,
                        "outputSamplingRate": 24000  # 24kHzに統一
                    },
                    json=synthesis_data
                )
                
                if synthesis_response.status_code != 200:
                    raise Exception(f"音声合成に失敗: {synthesis_response.status_code}")
                
                # ファイルに保存
                output_path = self.audio_dir / audio_filename
                with open(output_path, "wb") as f:
                    f.write(synthesis_response.content)
                
                # 改善されたオーディオ処理を適用（ビーン音除去）
                self.audio_processor.process_voicevox_audio(output_path)
                
                audio_count += 1
        
        return audio_count
    
    def apply_noise_reduction(self, audio_path: Path):
        """高周波ノイズをフィルタリングで除去"""
        try:
            # 音声ファイルを読み込み
            sample_rate, data = wavfile.read(audio_path)
            
            # ステレオの場合は各チャンネルを処理
            if len(data.shape) > 1:
                # ステレオの場合
                filtered_data = np.zeros_like(data)
                for channel in range(data.shape[1]):
                    filtered_data[:, channel] = self._apply_lowpass_filter(
                        data[:, channel], sample_rate
                    )
            else:
                # モノラルの場合
                filtered_data = self._apply_lowpass_filter(data, sample_rate)
            
            # フィルタリングした音声を保存
            wavfile.write(audio_path, sample_rate, filtered_data.astype(data.dtype))
            
        except Exception as e:
            print(f"音声フィルタリングエラー: {e}")
            # エラーが発生しても処理を継続
    
    def _apply_lowpass_filter(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """ローパスフィルタを適用して高周波ノイズを除去"""
        # カットオフ周波数：10kHz（音声の高域成分も保持）
        cutoff_freq = 10000
        nyquist_freq = sample_rate / 2
        
        # ナイキスト周波数で正規化
        normalized_cutoff = cutoff_freq / nyquist_freq
        
        # Butterworthフィルタを作成（次数を4に下げて自然な音質を維持）
        b, a = signal.butter(4, normalized_cutoff, btype='low')
        
        # フィルタを適用（lfilterを使用して境界処理を改善）
        filtered_audio = signal.lfilter(b, a, audio_data.astype(np.float64))
        
        # データ型を元に戻す
        return filtered_audio