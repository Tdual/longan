import requests
import json
from pathlib import Path
import time

class DialogueVoicevoxGenerator:
    def __init__(self, output_dir="audio", voicevox_url="http://localhost:50021"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.voicevox_url = voicevox_url
        self.speakers = {
            "metan": 2,    # 四国めたん（あまあま）
            "zundamon": 3  # ずんだもん
        }
    
    def check_voicevox_status(self):
        """VOICEVOXが起動しているか確認"""
        try:
            response = requests.get(f"{self.voicevox_url}/version")
            return response.status_code == 200
        except:
            return False
    
    def generate_audio(self, text, speaker_name, output_filename):
        """VOICEVOXでテキストから音声ファイルを生成"""
        speaker_id = self.speakers.get(speaker_name, 3)
        
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
    
    def generate_dialogue_audio(self, dialogue_data):
        """対話形式のナレーションから音声ファイルを生成"""
        if not self.check_voicevox_status():
            raise Exception("VOICEVOXが起動していません。VOICEVOXを起動してください。")
        
        audio_info = {}  # スライドごとの音声情報
        
        for slide_key, dialogues in dialogue_data.items():
            slide_num = slide_key.split("_")[1]
            audio_info[slide_key] = []
            
            for i, dialogue in enumerate(dialogues):
                speaker = dialogue["speaker"]
                text = dialogue["text"]
                
                # ファイル名: slide_XX_YY_speaker.wav
                audio_filename = f"slide_{int(slide_num):03d}_{i+1:02d}_{speaker}.wav"
                
                speaker_name = "四国めたん" if speaker == "metan" else "ずんだもん"
                print(f"音声生成中: スライド {slide_num} - {speaker_name}: {text[:20]}...")
                
                try:
                    audio_path = self.generate_audio(text, speaker, audio_filename)
                    audio_info[slide_key].append({
                        "speaker": speaker,
                        "text": text,
                        "audio_path": audio_path
                    })
                    time.sleep(0.5)  # API負荷軽減
                except Exception as e:
                    print(f"  エラー: {e}")
                    audio_info[slide_key].append({
                        "speaker": speaker,
                        "text": text,
                        "audio_path": None
                    })
        
        return audio_info