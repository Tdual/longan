from gtts import gTTS
import os
from pathlib import Path

class AudioGenerator:
    def __init__(self, output_dir="audio", lang="ja"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.lang = lang
    
    def generate_audio(self, text, output_filename, slow=False):
        """テキストから音声ファイルを生成"""
        tts = gTTS(text=text, lang=self.lang, slow=slow)
        output_path = self.output_dir / output_filename
        tts.save(str(output_path))
        return str(output_path)
    
    def generate_audio_for_slides(self, slide_texts):
        """各スライドのテキストから音声ファイルを生成"""
        audio_paths = []
        
        for i, text in enumerate(slide_texts):
            if text.strip():  # 空でないテキストの場合のみ
                audio_filename = f"slide_{i+1:03d}.mp3"
                print(f"音声生成中: スライド {i+1}")
                audio_path = self.generate_audio(text, audio_filename)
                audio_paths.append(audio_path)
            else:
                audio_paths.append(None)
        
        return audio_paths