import sys
from pathlib import Path
import json
import re
from typing import Dict, List

# srcディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from english_to_katakana import create_katakana_dictionary, convert_text_to_katakana

class KatakanaConverter:
    def __init__(self):
        self.katakana_dict = create_katakana_dictionary()
        
    def convert_dialogue_to_katakana(self, dialogue_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """対話データ内の英単語をカタカナに変換"""
        converted_data = {}
        
        for slide_key, dialogues in dialogue_data.items():
            converted_dialogues = []
            
            for dialogue in dialogues:
                speaker = dialogue["speaker"]
                text = dialogue["text"]
                
                # 英単語をカタカナに変換
                converted_text = convert_text_to_katakana(text, self.katakana_dict)
                
                converted_dialogues.append({
                    "speaker": speaker,
                    "text": converted_text
                })
            
            converted_data[slide_key] = converted_dialogues
        
        return converted_data
    
    def save_english_words_detected(self, output_path: str):
        """検出された英単語を保存"""
        english_words = {}
        
        # 辞書から英単語リストを取得
        for word, katakana in self.katakana_dict.items():
            english_words[word] = katakana
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(english_words, f, ensure_ascii=False, indent=2)