import requests
import json
from pathlib import Path
import time

class VoicevoxGenerator:
    def __init__(self, output_dir="audio", voicevox_url=None):
        if voicevox_url is None:
            # 環境変数から取得、なければデフォルト
            import os
            voicevox_url = os.getenv("VOICEVOX_URL", "http://localhost:50021")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.voicevox_url = voicevox_url
        self.speaker_id = 3  # ずんだもんのスピーカーID
    
    def check_voicevox_status(self):
        """VOICEVOXが起動しているか確認"""
        try:
            response = requests.get(f"{self.voicevox_url}/version")
            return response.status_code == 200
        except:
            return False
    
    def generate_audio(self, text, output_filename, speaker_id=None):
        """VOICEVOXでテキストから音声ファイルを生成"""
        if speaker_id is None:
            speaker_id = self.speaker_id
        
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
        
        # 音声合成
        synthesis_data = query_response.json()
        synthesis_response = requests.post(
            f"{self.voicevox_url}/synthesis",
            params={"speaker": speaker_id},
            json=synthesis_data
        )
        
        if synthesis_response.status_code != 200:
            raise Exception(f"音声合成に失敗: {synthesis_response.status_code}")
        
        # ファイルに保存
        output_path = self.output_dir / output_filename
        with open(output_path, "wb") as f:
            f.write(synthesis_response.content)
        
        return str(output_path)
    
    def generate_audio_for_slides(self, slide_texts):
        """各スライドのテキストから音声ファイルを生成"""
        if not self.check_voicevox_status():
            raise Exception("VOICEVOXが起動していません。VOICEVOXを起動してください。")
        
        audio_paths = []
        
        for i, text in enumerate(slide_texts):
            if text.strip():  # 空でないテキストの場合のみ
                audio_filename = f"slide_{i+1:03d}.wav"
                print(f"音声生成中: スライド {i+1} (ずんだもん)")
                try:
                    audio_path = self.generate_audio(text, audio_filename)
                    audio_paths.append(audio_path)
                    time.sleep(0.5)  # API負荷軽減のため少し待機
                except Exception as e:
                    print(f"  エラー: {e}")
                    audio_paths.append(None)
            else:
                audio_paths.append(None)
        
        return audio_paths