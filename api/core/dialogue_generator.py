import os
import json
from typing import List, Dict
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

class DialogueGenerator:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY が設定されていません")
        
        self.client = OpenAI(api_key=self.api_key)
        
    def extract_text_from_slides(self, slide_texts: List[str]) -> Dict[str, List[Dict]]:
        """スライドのテキストから対話形式のナレーションを生成"""
        
        system_prompt = """あなたは教育的なプレゼンテーションを対話形式で説明するスクリプトライターです。
        
        登場人物：
        - 四国めたん（metan）: AIやプログラミングの専門家。説明役。
        - ずんだもん（zundamon）: 学習者。質問や相槌を打つ役。

        ルール：
        1. 各スライドについて、自然な対話形式で内容を説明してください
        2. めたんが主に説明し、ずんだもんが質問や感想を述べます
        3. 1つの発話は1〜2文程度に収めてください
        4. 専門用語は分かりやすく説明してください
        5. 会話は親しみやすく、教育的なトーンで
        
        出力形式：
        {
            "slide_1": [
                {"speaker": "metan", "text": "今日はClaude Codeについて説明するね"},
                {"speaker": "zundamon", "text": "Claude Codeって何なのだ？"},
                ...
            ],
            "slide_2": [...],
            ...
        }
        """
        
        # スライドテキストを結合
        slides_content = "\n\n".join([
            f"スライド{i+1}:\n{text}" 
            for i, text in enumerate(slide_texts)
        ])
        
        user_prompt = f"""以下のスライドの内容を、四国めたんとずんだもんの対話形式で説明してください。

{slides_content}

各スライドごとに3〜5回程度の会話のやり取りを生成してください。
JSON形式で出力してください。"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # より高速で安価なモデル
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            # レスポンスをパース
            dialogue_data = json.loads(response.choices[0].message.content)
            
            return dialogue_data
            
        except Exception as e:
            print(f"対話生成エラー: {e}")
            import traceback
            traceback.print_exc()
            # エラー時はデフォルトの対話を返す
            return self._get_default_dialogue(len(slide_texts))
    
    def _get_default_dialogue(self, num_slides: int) -> Dict[str, List[Dict]]:
        """デフォルトの対話データを生成"""
        dialogue_data = {}
        
        for i in range(num_slides):
            slide_key = f"slide_{i+1}"
            dialogue_data[slide_key] = [
                {"speaker": "metan", "text": f"スライド{i+1}の内容を説明します"},
                {"speaker": "zundamon", "text": "なるほどなのだ"},
            ]
        
        return dialogue_data
    
    def save_dialogue_data(self, dialogue_data: Dict, output_path: str):
        """対話データを保存"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_data, f, ensure_ascii=False, indent=2)