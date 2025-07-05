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
        
    def extract_text_from_slides(self, slide_texts: List[str], additional_prompt: str = None, progress_callback=None) -> Dict[str, List[Dict]]:
        """スライドのテキストから対話形式のナレーションを生成（スライドごとに個別生成）"""
        
        dialogue_data = {}
        
        # 各スライドについて個別に対話を生成
        for i, slide_text in enumerate(slide_texts):
            slide_key = f"slide_{i+1}"
            
            # 進捗を通知
            if progress_callback:
                progress_callback(f"スライド{i+1}/{len(slide_texts)}の対話を生成中...", (i / len(slide_texts)) * 100)
            
            slide_dialogue = self.generate_dialogue_for_single_slide(
                slide_number=i+1,
                slide_text=slide_text,
                total_slides=len(slide_texts),
                additional_prompt=additional_prompt
            )
            dialogue_data[slide_key] = slide_dialogue
        
        return dialogue_data
    
    def generate_dialogue_for_single_slide(self, slide_number: int, slide_text: str, total_slides: int, additional_prompt: str = None) -> List[Dict]:
        """単一スライドの対話を生成"""
        
        system_prompt = """あなたは魅力的な教育動画を作成するプロの脚本家です。四国めたんとずんだもんによる楽しい対話を書いてください。

キャラクター設定：
- 四国めたん（metan）: AI・プログラミングの専門家だが、親しみやすく説明が上手。時々専門的な知識を披露する。
- ずんだもん（zundamon）: 好奇心旺盛で率直な質問をする。「〜なのだ」という語尾が特徴。驚きや興味を素直に表現する。

対話のルール：
1. 自然で生き生きとした会話にしてください
2. ずんだもんは「〜なのだ」「〜だぞ」という語尾を使う
3. めたんは専門知識を分かりやすく、時には例え話で説明する
4. 1つの発話は2〜4文程度（内容を充実させるため、短すぎないように）
5. 感嘆詞（「へえ〜」「すごい！」「なるほど」など）を自然に入れる
6. 新しい発見や驚きがある展開にする
7. 聞き手（視聴者）が「もっと知りたい」と思うような会話にする
8. 具体的な数字、事例、メリット・デメリットなどを積極的に話題に含める
9. 技術的な内容も分かりやすい例え話で説明する

出力形式：
必ず以下のような有効なJSON形式で出力してください。コードブロックや余計な文字は含めないでください。
{
  "dialogue": [
    {"speaker": "metan", "text": "今日はClaude Codeの魅力について話すよ！"},
    {"speaker": "zundamon", "text": "おお、楽しみなのだ！Claude Codeって何がすごいのだ？"}
  ]
}"""
        
        user_prompt = f"""スライド{slide_number}/{total_slides}の内容について、めたんとずんだもんの魅力的な対話を作成してください。

スライド内容：
{slide_text}

重要な要望：
- このスライドについて8〜12回の会話のやり取りを作成（最低でも8回以上）
- 会話は具体的で内容が濃いものにする（単なる相槌ではなく、情報を含む発話）
- ずんだもんは「〜なのだ」語尾を必ず使用し、具体的な質問や感想を述べる
- めたんは専門知識を噛み砕いて、例え話や具体例を交えて丁寧に説明
- 以下の要素を必ず含める：
  * スライドの主要なポイントの詳細な説明
  * 具体的な例や応用例の紹介
  * ずんだもんからの掘り下げた質問
  * めたんによる分かりやすい回答
  * 関連する豆知識や補足情報
- 単純な「なるほど」「そうなのだ」だけの返答は避ける
- 視聴者が理解を深められるよう、段階的に説明を展開

必ず有効なJSON形式（{"dialogue": [...]}の形式）で出力してください。"""
        
        # 追加プロンプトがある場合は付加
        if additional_prompt:
            user_prompt += f"\n\n追加の指示：\n{additional_prompt}"

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=3000,  # 単一スライドなので少なめでOK
                response_format={"type": "json_object"}
            )
            
            # レスポンスをパース
            content = response.choices[0].message.content
            if not content:
                print(f"スライド{slide_number}の応答が空です")
                return self._get_default_slide_dialogue(slide_number)
            
            # JSONとして解析（配列として返されるはずだが、オブジェクトで返される場合の対処）
            try:
                parsed_content = json.loads(content)
                
                # もし配列でなくオブジェクトで返された場合、配列を取り出す
                if isinstance(parsed_content, dict):
                    # "dialogue"キーなどがある場合
                    if "dialogue" in parsed_content:
                        dialogue_list = parsed_content["dialogue"]
                    # "slide_1"のようなキーがある場合
                    elif f"slide_{slide_number}" in parsed_content:
                        dialogue_list = parsed_content[f"slide_{slide_number}"]
                    else:
                        # 最初の値を取得
                        dialogue_list = list(parsed_content.values())[0]
                else:
                    dialogue_list = parsed_content
                
                if isinstance(dialogue_list, list) and len(dialogue_list) >= 8:
                    return dialogue_list
                else:
                    print(f"スライド{slide_number}の対話が不十分です（{len(dialogue_list)}件）")
                    return self._get_default_slide_dialogue(slide_number)
                    
            except json.JSONDecodeError as e:
                print(f"スライド{slide_number}のJSON解析エラー: {e}")
                print(f"レスポンス内容: {content[:500]}...")
                return self._get_default_slide_dialogue(slide_number)
            
        except Exception as e:
            print(f"スライド{slide_number}の対話生成エラー: {e}")
            return self._get_default_slide_dialogue(slide_number)
    
    def _get_default_slide_dialogue(self, slide_number: int) -> List[Dict]:
        """単一スライドのデフォルト対話を生成"""
        return [
            {"speaker": "metan", "text": f"スライド{slide_number}の内容を説明します"},
            {"speaker": "zundamon", "text": "どんな内容なのだ？"},
            {"speaker": "metan", "text": "このスライドでは重要なポイントを扱っています"},
            {"speaker": "zundamon", "text": "もっと詳しく教えてほしいのだ！"},
            {"speaker": "metan", "text": "わかりました。順を追って説明しますね"},
            {"speaker": "zundamon", "text": "楽しみなのだ！"},
            {"speaker": "metan", "text": "まず最初のポイントから始めましょう"},
            {"speaker": "zundamon", "text": "しっかり聞くのだ！"}
        ]
    
    def extract_text_from_slides_batch(self, slide_texts: List[str], additional_prompt: str = None) -> Dict[str, List[Dict]]:
        """スライドのテキストから対話形式のナレーションを生成"""
        
        system_prompt = """あなたは魅力的な教育動画を作成するプロの脚本家です。四国めたんとずんだもんによる楽しい対話を書いてください。

キャラクター設定：
- 四国めたん（metan）: AI・プログラミングの専門家だが、親しみやすく説明が上手。時々専門的な知識を披露する。
- ずんだもん（zundamon）: 好奇心旺盛で率直な質問をする。「〜なのだ」という語尾が特徴。驚きや興味を素直に表現する。

対話のルール：
1. 自然で生き生きとした会話にしてください
2. ずんだもんは「〜なのだ」「〜だぞ」という語尾を使う
3. めたんは専門知識を分かりやすく、時には例え話で説明する
4. 1つの発話は2〜4文程度（内容を充実させるため、短すぎないように）
5. 感嘆詞（「へえ〜」「すごい！」「なるほど」など）を自然に入れる
6. 各スライドで新しい発見や驚きがある展開にする
7. 聞き手（視聴者）が「もっと知りたい」と思うような会話にする
8. 具体的な数字、事例、メリット・デメリットなどを積極的に話題に含める
9. 技術的な内容も分かりやすい例え話で説明する

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

重要な要望：
- 各スライドごとに必ず8〜12回の会話のやり取りを作成（最低でも8回以上）
- 会話は具体的で内容が濃いものにする（単なる相槌ではなく、情報を含む発話）
- ずんだもんは「〜なのだ」語尾を必ず使用し、具体的な質問や感想を述べる
- めたんは専門知識を噛み砕いて、例え話や具体例を交えて丁寧に説明
- 以下の要素を必ず含める：
  * スライドの主要なポイントの詳細な説明
  * 具体的な例や応用例の紹介
  * ずんだもんからの掘り下げた質問
  * めたんによる分かりやすい回答
  * 関連する豆知識や補足情報
- 単純な「なるほど」「そうなのだ」だけの返答は避ける
- 視聴者が理解を深められるよう、段階的に説明を展開

必ず有効なJSON形式で出力してください。"""
        
        # 追加プロンプトがある場合は付加
        if additional_prompt:
            user_prompt += f"\n\n追加の指示：\n{additional_prompt}"

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,  # より創造的な会話のために少し上げる
                max_tokens=8000,  # より長い会話を許可
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