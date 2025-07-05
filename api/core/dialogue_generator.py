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
        
        system_prompt = """あなたは魅力的な教育動画を作成するプロの脚本家です。四国めたんとずんだもんによる楽しい対話を書いてください。

キャラクター設定：
- 四国めたん（metan）: AI・プログラミングの専門家だが、親しみやすく説明が上手。時々専門的な知識を披露する。
- ずんだもん（zundamon）: 好奇心旺盛で率直な質問をする。「〜なのだ」という語尾が特徴。驚きや興味を素直に表現する。

対話のルール：
1. 自然で生き生きとした会話にしてください
2. ずんだもんは「〜なのだ」「〜だぞ」という語尾を使う
3. めたんは専門知識を分かりやすく、時には例え話で説明する
4. 1つの発話は1〜2文、長くても3文以内
5. 感嘆詞（「へえ〜」「すごい！」「なるほど」など）を自然に入れる
6. 各スライドで新しい発見や驚きがある展開にする
7. 聞き手（視聴者）が「もっと知りたい」と思うような会話にする

出力形式：
必ず以下のような有効なJSON形式で出力してください。コードブロックや余計な文字は含めないでください。
{
  "slide_1": [
    {"speaker": "metan", "text": "今日はClaude Codeの魅力について話すよ！"},
    {"speaker": "zundamon", "text": "おお、楽しみなのだ！Claude Codeって何がすごいのだ？"}
  ],
  "slide_2": [...]
}"""
        
        # スライドテキストを結合
        slides_content = "\n\n".join([
            f"スライド{i+1}:\n{text}" 
            for i, text in enumerate(slide_texts)
        ])
        
        user_prompt = f"""以下のスライド内容を、めたんとずんだもんの魅力的な対話で解説してください。

{slides_content}

要望：
- 各スライドごとに4〜6回の会話のやり取りを作成
- ずんだもんは「〜なのだ」語尾を必ず使用
- めたんは専門知識を噛み砕いて説明
- 驚きや発見のある自然な流れで
- 視聴者が最後まで飽きない工夫を

必ず有効なJSON形式で出力してください。"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                response_format={"type": "json_object"}  # JSON形式を強制
            )
            
            # レスポンスをパース
            content = response.choices[0].message.content
            if not content:
                print("OpenAIからの応答が空です")
                return self._get_default_dialogue(len(slide_texts))
            
            try:
                dialogue_data = json.loads(content)
                # 必要なキーが存在するか確認
                expected_keys = [f"slide_{i+1}" for i in range(len(slide_texts))]
                if all(key in dialogue_data for key in expected_keys):
                    return dialogue_data
                else:
                    print("対話データのキーが不足しています")
                    return self._get_default_dialogue(len(slide_texts))
            except json.JSONDecodeError as e:
                print(f"JSON解析エラー: {e}")
                print(f"レスポンス内容: {content[:500]}...")  # 最初の500文字を表示
                return self._get_default_dialogue(len(slide_texts))
            
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