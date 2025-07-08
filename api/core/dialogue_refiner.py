"""
対話スクリプトの全体調整と英語→カタカナ変換
"""
from typing import Dict, List, Optional
from openai import OpenAI
import os
import re

class DialogueRefiner:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def refine_and_convert_to_katakana(
        self, 
        dialogue_data: Dict[str, List[Dict]], 
        speaker_info: Optional[Dict] = None,
        adjustment_prompt: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """対話スクリプト全体を調整し、英語をカタカナに変換"""
        
        # 話者名を取得
        speaker1_name = "speaker1"
        speaker2_name = "speaker2"
        if speaker_info:
            speaker1_name = speaker_info.get("speaker1", {}).get("name", "speaker1")
            speaker2_name = speaker_info.get("speaker2", {}).get("name", "speaker2")
        
        # 全対話を一つのテキストにまとめる
        full_dialogue = []
        for slide_key in sorted(dialogue_data.keys(), key=lambda x: int(x.split('_')[1])):
            dialogues = dialogue_data[slide_key]
            if dialogues:
                full_dialogue.append(f"[{slide_key}]")
                for d in dialogues:
                    speaker_display = speaker1_name if d['speaker'] == 'speaker1' else speaker2_name
                    full_dialogue.append(f"{speaker_display}: {d['text']}")
                full_dialogue.append("")
        
        dialogue_text = "\n".join(full_dialogue)
        
        # 調整用のプロンプト
        system_prompt = f"""あなたは日本語の対話スクリプトを調整する専門家です。
以下の指示に従って対話スクリプトを改善してください：

1. 全体の流れと一貫性をチェックし、必要に応じて調整
2. 【最重要】英語やローマ字が含まれている場合は、必ずすべてカタカナに変換してください
   - 例: AI → エーアイ、PDF → ピーディーエフ、Claude → クロード
   - 例: PowerPoint → パワーポイント、Excel → エクセル
   - 例: md/MD → エムディー、yaml/YAML/yml/YML → ヤムル
   - 例: JavaScript → ジャバスクリプト、Python → パイソン
   - 例: GitHub → ギットハブ、Docker → ドッカー
   - 技術用語、製品名、サービス名、プログラミング言語名など、すべての英語をカタカナに変換
3. 話者のキャラクター性を保持
4. 各発話は簡潔に（一文あたり40文字以内を目安）
5. 変換後、英語が一切残っていないことを確認してください

話者情報：
- {speaker1_name}: speaker1として表示される話者
- {speaker2_name}: speaker2として表示される話者

出力形式は元の形式を保持してください。"""

        user_prompt = f"以下の対話スクリプトを調整してください。"
        if adjustment_prompt:
            user_prompt += f"\n\n追加の指示: {adjustment_prompt}"
        user_prompt += f"\n\n対話スクリプト:\n{dialogue_text}"
        
        # GPTで調整
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )
        
        refined_text = response.choices[0].message.content
        
        # 調整されたテキストを元の形式に戻す
        refined_dialogue = self._parse_refined_dialogue(refined_text, dialogue_data)
        
        return refined_dialogue
    
    def _parse_refined_dialogue(self, refined_text: str, original_data: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """調整されたテキストを元の形式に戻す"""
        result = {}
        current_slide = None
        
        lines = refined_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # スライド番号の検出
            if line.strip().startswith('[slide_') and line.strip().endswith(']'):
                current_slide = line.strip()[1:-1]  # Remove [ and ]
                result[current_slide] = []
                continue
            
            # 対話の検出
            dialogue_match = re.match(r'(.+?):\s*(.+)', line)
            if dialogue_match and current_slide:
                speaker_display = dialogue_match.group(1)
                text = dialogue_match.group(2)
                
                # より確実な判定方法
                if current_slide in original_data and len(result[current_slide]) < len(original_data[current_slide]):
                    # 元のデータの順番に基づいて判定
                    original_speaker = original_data[current_slide][len(result[current_slide])]['speaker']
                    speaker = original_speaker
                else:
                    # デフォルトの判定
                    speaker = 'speaker1' if len(result[current_slide]) % 2 == 0 else 'speaker2'
                
                result[current_slide].append({
                    "speaker": speaker,
                    "text": text
                })
        
        # 元のデータ構造に存在しないスライドは追加しない
        final_result = {}
        for slide_key in original_data.keys():
            if slide_key in result:
                final_result[slide_key] = result[slide_key]
            else:
                final_result[slide_key] = original_data[slide_key]
        
        return final_result
    
