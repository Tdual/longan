import sys
from pathlib import Path
import json
import requests
import os
import numpy as np
from scipy.io import wavfile
from scipy import signal

# srcディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from voicevox_generator import VoicevoxGenerator

class AudioGenerator:
    def __init__(self, job_id: str, base_dir: Path):
        self.job_id = job_id
        self.base_dir = base_dir
        self.audio_dir = base_dir / "audio" / job_id
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.voicevox_url = os.getenv("VOICEVOX_URL", "http://localhost:50021")
        
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
                
                synthesis_data["speedScale"] = current_speed_scale
                synthesis_data["pitchScale"] = pitch_scale
                synthesis_data["intonationScale"] = intonation_scale
                synthesis_data["volumeScale"] = volume_scale
                
                # 音声の前後に短い無音を追加（クリック音防止）
                synthesis_data["prePhonemeLength"] = 0.1  # 音声前の無音（秒）
                synthesis_data["postPhonemeLength"] = 0.1  # 音声後の無音（秒）
                
                synthesis_response = requests.post(
                    f"{self.voicevox_url}/synthesis",
                    params={"speaker": speaker_id},
                    json=synthesis_data
                )
                
                if synthesis_response.status_code != 200:
                    raise Exception(f"音声合成に失敗: {synthesis_response.status_code}")
                
                # ファイルに保存
                output_path = self.audio_dir / audio_filename
                with open(output_path, "wb") as f:
                    f.write(synthesis_response.content)
                
                # 高周波ノイズをフィルタリングで除去
                self.apply_noise_reduction(output_path)
                
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
        # カットオフ周波数：8kHz（人音の基本周波数を保持）
        cutoff_freq = 8000
        nyquist_freq = sample_rate / 2
        
        # ナイキスト周波数で正規化
        normalized_cutoff = cutoff_freq / nyquist_freq
        
        # Butterworthフィルタを作成（次数は6で急峻なカットオフ）
        b, a = signal.butter(6, normalized_cutoff, btype='low')
        
        # フィルタを適用
        filtered_audio = signal.filtfilt(b, a, audio_data.astype(np.float64))
        
        # データ型を元に戻す
        return filtered_audio