import os
import json
import re
from typing import List, Dict, Optional
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
    
    def analyze_regeneration_request(self, user_instruction: str, total_slides: int) -> List[int]:
        """ユーザーの指示から再生成するスライド番号を判断"""
        
        system_prompt = """あなたはユーザーの指示を分析して、どのスライドを再生成すべきか判断するアシスタントです。

ユーザーの指示を分析して、以下のルールに従ってスライド番号のリストを返してください：
1. 「1枚目」「最初のスライド」「スライド1」などの表現は slide_numbers: [1] 
2. 「2枚目と3枚目」「スライド2-3」などの表現は slide_numbers: [2, 3]
3. 「全部」「全体」「すべて」などの表現は slide_numbers: [1, 2, ..., total_slides]
4. 「最後」「最終」などの表現は slide_numbers: [total_slides]
5. 「前半」は slide_numbers: [1, 2, ..., total_slides/2]
6. 「後半」は slide_numbers: [total_slides/2+1, ..., total_slides]

必ず以下のJSON形式で返してください：
{
  "slide_numbers": [1, 2, 3],
  "reason": "なぜこれらのスライドを選んだか"
}"""
        
        user_prompt = f"""全体で{total_slides}枚のスライドがあります。

ユーザーの指示: {user_instruction}

どのスライドを再生成すべきか判断してください。"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 軽量なモデルで十分
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # 確実性を高める
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                # デフォルトは全スライド
                return list(range(1, total_slides + 1))
            
            try:
                result = json.loads(content)
                slide_numbers = result.get("slide_numbers", [])
                # 有効なスライド番号のみを返す
                valid_numbers = [n for n in slide_numbers if 1 <= n <= total_slides]
                
                if not valid_numbers:
                    # 判断できない場合は全スライド
                    return list(range(1, total_slides + 1))
                
                print(f"再生成対象スライド: {valid_numbers} (理由: {result.get('reason', '不明')})")
                return valid_numbers
                
            except json.JSONDecodeError:
                return list(range(1, total_slides + 1))
                
        except Exception as e:
            print(f"スライド判断エラー: {e}")
            # エラー時は全スライド
            return list(range(1, total_slides + 1))
        
    def analyze_user_importance_adjustments(self, user_instruction: str, slide_count: int) -> Dict[int, float]:
        """ユーザーの指示から重要度の調整を分析"""
        
        system_prompt = """あなたはユーザーの指示を分析して、スライドの重要度調整を判断するアシスタントです。

ユーザーの指示から以下のパターンを識別してください：
1. 「1枚目を詳しく」「最初のスライドをもっと充実」→ そのスライドの重要度を上げる (×1.5)
2. 「3枚目は簡潔に」「スライド5を短く」→ そのスライドの重要度を下げる (×0.5)
3. 「技術的な部分を詳しく」→ 該当するスライドの重要度を上げる
4. 「概要部分は簡潔に」→ 該当するスライドの重要度を下げる
5. 「全体的に詳しく」→ すべてのスライドの重要度を少し上げる (×1.2)
6. 「全体的に簡潔に」→ すべてのスライドの重要度を少し下げる (×0.8)

JSON形式で調整係数を返してください。調整が必要ないスライドは含めないでください。
例: {"1": 1.5, "3": 0.5}"""
        
        user_prompt = f"""全体で{slide_count}枚のスライドがあります。

ユーザーの指示: {user_instruction}

この指示から、どのスライドの重要度を調整すべきか判断してください。
調整が必要なスライドのみを返してください。"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                adjustments = json.loads(content)
                # 文字列キーを整数に変換
                return {int(k): float(v) for k, v in adjustments.items()}
            else:
                return {}
                
        except Exception as e:
            print(f"重要度調整分析エラー: {e}")
            return {}
    
    def analyze_slide_importance(self, slide_texts: List[str], user_instruction: str = None) -> Dict[int, float]:
        """各スライドの重要度を分析して時間配分の重みを返す"""
        
        system_prompt = """あなたはプレゼンテーション分析の専門家です。
各スライドの内容を分析し、視聴者にとっての重要度を判断してください。

重要度の基準：
- タイトル/表紙スライド: 0.5 (簡潔に)
- まとめ/終了スライド: 0.5 (簡潔に)
- 概要/目次スライド: 0.7 (やや簡潔に)
- 核心的な技術説明: 1.5 (詳しく)
- 実装例/コード例: 1.3 (詳しく)
- 一般的な説明: 1.0 (標準)
- 補足情報: 0.8 (やや簡潔に)

JSON形式で各スライドの重要度係数を返してください。
例: {"1": 0.5, "2": 1.0, "3": 1.5, ...}"""
        
        slides_summary = "\n".join([
            f"スライド{i+1}: {text[:200]}..." if len(text) > 200 else f"スライド{i+1}: {text}"
            for i, text in enumerate(slide_texts)
        ])
        
        user_prompt = f"""以下のスライド内容を分析し、各スライドの重要度係数を返してください：

{slides_summary}

各スライドについて、内容の重要性に基づいて0.5〜1.5の係数を割り当ててください。"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                importance_map = json.loads(content)
                # 文字列キーを整数に変換
                base_importance = {int(k): float(v) for k, v in importance_map.items()}
            else:
                # デフォルト値を返す
                base_importance = {i+1: 1.0 for i in range(len(slide_texts))}
                
        except Exception as e:
            print(f"重要度分析エラー: {e}")
            # エラー時はすべて標準の重要度
            base_importance = {i+1: 1.0 for i in range(len(slide_texts))}
        
        # ユーザー指示による調整を適用
        if user_instruction:
            adjustments = self.analyze_user_importance_adjustments(user_instruction, len(slide_texts))
            print(f"ユーザー指示による重要度調整: {adjustments}")
            
            for slide_num, adjustment in adjustments.items():
                if slide_num in base_importance:
                    base_importance[slide_num] *= adjustment
                    print(f"スライド{slide_num}の重要度を{adjustment}倍に調整: {base_importance[slide_num]}")
        
        return base_importance
    
    def extract_text_from_slides(self, slide_texts: List[str], additional_prompt: str = None, progress_callback=None, target_duration: int = 10, speaker_info: dict = None) -> Dict[str, List[Dict]]:
        """スライドのテキストから対話形式のナレーションを生成（スライドごとに個別生成）"""
        
        dialogue_data = {}
        
        # まず各スライドの重要度を分析（ユーザー指示も考慮）
        importance_map = self.analyze_slide_importance(slide_texts, additional_prompt)
        
        # 重要度の合計を計算
        total_importance = sum(importance_map.get(i+1, 1.0) for i in range(len(slide_texts)))
        
        # 各スライドの目安時間を重要度に基づいて配分（秒に変換）
        target_seconds = target_duration * 60
        slide_time_allocation = {}
        for i in range(len(slide_texts)):
            slide_num = i + 1
            importance = importance_map.get(slide_num, 1.0)
            slide_time_allocation[slide_num] = (target_seconds * importance) / total_importance
            
        print(f"スライド時間配分: {slide_time_allocation}")
        
        # 各スライドについて個別に対話を生成
        for i, slide_text in enumerate(slide_texts):
            slide_key = f"slide_{i+1}"
            slide_num = i + 1
            
            # 進捗を通知
            if progress_callback:
                try:
                    progress_callback(f"スライド{i+1}/{len(slide_texts)}の対話を生成中...", (i / len(slide_texts)) * 100)
                except Exception as e:
                    print(f"進捗コールバックエラー: {e}")
            
            # 過去のスライドの対話を収集
            previous_dialogues = {}
            for j in range(i):
                prev_key = f"slide_{j+1}"
                if prev_key in dialogue_data:
                    previous_dialogues[prev_key] = dialogue_data[prev_key]
            
            # このスライドの割り当て時間を取得
            allocated_seconds = slide_time_allocation.get(slide_num, target_seconds / len(slide_texts))
            
            # 重要度情報を追加プロンプトに含める
            slide_importance = importance_map.get(slide_num, 1.0)
            if slide_importance < 0.7:
                importance_note = "【重要】このトピックは概要的な内容なので、簡潔にまとめてください。"
            elif slide_importance > 1.3:
                importance_note = "【重要】このトピックは核心的な内容なので、しっかりと詳しく説明してください。"
            else:
                importance_note = ""
            
            # 追加プロンプトと重要度情報を組み合わせる
            if additional_prompt:
                combined_additional_prompt = f"{additional_prompt}\n\n{importance_note}".strip()
            else:
                combined_additional_prompt = importance_note
            
            slide_dialogue = self.generate_dialogue_for_single_slide(
                slide_number=i+1,
                slide_text=slide_text,
                total_slides=len(slide_texts),
                previous_dialogues=previous_dialogues,
                additional_prompt=combined_additional_prompt,
                target_seconds_per_slide=allocated_seconds,
                speaker_info=speaker_info
            )
            dialogue_data[slide_key] = slide_dialogue
        
        return dialogue_data
    
    def regenerate_specific_slides(self, slide_texts: List[str], existing_dialogues: Dict[str, List[Dict]], slide_numbers: List[int], additional_prompt: str = None, progress_callback=None, instruction_history=None, target_duration: int = 10, speaker_info: dict = None) -> Dict[str, List[Dict]]:
        """特定のスライドのみ再生成"""
        
        # 既存の対話データをコピー
        dialogue_data = existing_dialogues.copy()
        
        # 各スライドの重要度を分析（ユーザー指示も考慮）
        importance_map = self.analyze_slide_importance(slide_texts, additional_prompt)
        
        # 重要度の合計を計算
        total_importance = sum(importance_map.get(i+1, 1.0) for i in range(len(slide_texts)))
        
        # 各スライドの目安時間を重要度に基づいて配分（秒に変換）
        target_seconds = target_duration * 60
        slide_time_allocation = {}
        for i in range(len(slide_texts)):
            slide_num = i + 1
            importance = importance_map.get(slide_num, 1.0)
            slide_time_allocation[slide_num] = (target_seconds * importance) / total_importance
        
        # 指定されたスライドのみ再生成
        for slide_num in slide_numbers:
            if slide_num < 1 or slide_num > len(slide_texts):
                continue
                
            i = slide_num - 1  # 0ベースのインデックスに変換
            slide_key = f"slide_{slide_num}"
            
            # 進捗を通知
            if progress_callback:
                try:
                    progress_msg = f"スライド{slide_num}の対話を再生成中... ({slide_numbers.index(slide_num)+1}/{len(slide_numbers)})"
                    progress = (slide_numbers.index(slide_num) / len(slide_numbers)) * 100
                    progress_callback(progress_msg, progress)
                except Exception as e:
                    print(f"進捗コールバックエラー: {e}")
            
            # 過去のスライドの対話を収集（再生成対象を除く）
            previous_dialogues = {}
            for j in range(i):
                prev_key = f"slide_{j+1}"
                if prev_key in dialogue_data:
                    previous_dialogues[prev_key] = dialogue_data[prev_key]
            
            # 履歴がある場合は、過去の指示と組み合わせる
            if instruction_history:
                combined_prompt = instruction_history.get_combined_instruction(slide_num, additional_prompt)
            else:
                combined_prompt = additional_prompt
            
            # 重要度情報を追加プロンプトに含める
            slide_importance = importance_map.get(slide_num, 1.0)
            if slide_importance < 0.7:
                importance_note = "\n\n【重要】このトピックは概要的な内容なので、簡潔にまとめてください。"
            elif slide_importance > 1.3:
                importance_note = "\n\n【重要】このトピックは核心的な内容なので、しっかりと詳しく説明してください。"
            else:
                importance_note = ""
            
            if combined_prompt:
                combined_prompt += importance_note
            else:
                combined_prompt = importance_note.strip()
            
            # このスライドの割り当て時間を取得
            allocated_seconds = slide_time_allocation.get(slide_num, target_seconds / len(slide_texts))
            
            slide_dialogue = self.generate_dialogue_for_single_slide(
                slide_number=slide_num,
                slide_text=slide_texts[i],
                total_slides=len(slide_texts),
                previous_dialogues=previous_dialogues,
                additional_prompt=combined_prompt,
                target_seconds_per_slide=allocated_seconds,
                speaker_info=speaker_info
            )
            dialogue_data[slide_key] = slide_dialogue
        
        return dialogue_data
    
    def generate_dialogue_for_single_slide(self, slide_number: int, slide_text: str, total_slides: int, previous_dialogues: Dict = None, additional_prompt: str = None, target_seconds_per_slide: float = 30, max_retries: int = 3, speaker_info: dict = None) -> List[Dict]:
        """単一スライドの対話を生成"""
        
        # スライドの種類を早めに判定（表紙・表題スライドかどうか）
        is_title_slide = False
        min_dialogues_for_this_slide = 8  # デフォルト値
        
        # スピーカー情報から名前と設定を取得
        if speaker_info:
            speaker1_name = speaker_info.get('speaker1', {}).get('name', '四国めたん')
            speaker2_name = speaker_info.get('speaker2', {}).get('name', 'ずんだもん')
        else:
            speaker1_name = '四国めたん'
            speaker2_name = 'ずんだもん'
        
        # キャラクター固有の話し方を定義
        character_styles = {
            'ずんだもん': '【重要】必ず「〜なのだ」「〜だぞ」という語尾を使用。驚きや興味を素直に表現する。',
            '四国めたん': '親しみやすく丁寧な話し方。標準語で話す。',
            '春日部つむぎ': '元気で明るい話し方。「〜ですよ」「〜ですね」を使う。',
            '波音リツ': 'クールで知的な話し方。落ち着いたトーンで標準語を使う。',
            '九州そら': '落ち着いた優しい話し方。丁寧で聞き取りやすい標準語を使う。「〜ですね」「〜でしょう」など。',
            '中国うさぎ': '「〜あるよ」「〜ね」など独特な話し方。',
            'WhiteCUL': '感情豊かで「〜だよ！」「〜かな？」を使う。',
            'さとうささら': '優しく柔らかい話し方。「〜ですわ」を使うことも。',
            '小夜/SAYO': 'ミステリアスで落ち着いた話し方。',
            '雨晴はう': 'のんびりとした話し方。「〜だねぇ」を使う。',
            '玄野武宏': '落ち着いた男性的な話し方。ビジネスライクで信頼感がある。',
            '白上虎太郎': '若々しく活発な男性の話し方。親しみやすい。',
            '青山龍星': 'プロフェッショナルで知的な男性の話し方。説得力がある。',
            '冥鳴ひまり': '明るく元気な話し方。若々しい印象。'
        }
        
        speaker1_style = character_styles.get(speaker1_name, '親しみやすく丁寧な話し方。')
        speaker2_style = character_styles.get(speaker2_name, '好奇心旺盛で率直な質問をする。')
        
        # 会話スタイルが追加プロンプトに含まれているかチェック
        conversation_style_applied = ""
        if additional_prompt:
            # 会話スタイルのキーワードをチェック
            style_keywords = ['ラジオ', 'ビジネス', '友達', '教育番組', 'ニュース', 'ポッドキャスト', 'バラエティ', '実況解説']
            for keyword in style_keywords:
                if keyword in additional_prompt:
                    conversation_style_applied = f"\n\n【会話スタイル】{additional_prompt}"
                    break
        
        # f-stringで中括弧がある場合のエラーを防ぐため、format()を使用
        system_prompt = """あなたは魅力的な教育動画を作成するプロの脚本家です。{speaker1_name}と{speaker2_name}による楽しい対話を書いてください。

キャラクター設定：
- {speaker1_name}（speaker1）: AI・プログラミングの専門家だが、親しみやすく説明が上手。時々専門的な知識を披露する。{speaker1_style}
- {speaker2_name}（speaker2）: 好奇心旺盛で率直な質問をする。{speaker2_style}{conversation_style}""".format(
            speaker1_name=speaker1_name,
            speaker2_name=speaker2_name,
            speaker1_style=speaker1_style,
            speaker2_style=speaker2_style,
            conversation_style=conversation_style_applied
        )
        
        system_prompt += """

対話のルール：
1. 自然で生き生きとした会話にしてください
2. 【超重要】各キャラクターの話し方の特徴を必ず守ってください。キャラクター設定に書かれた話し方や語尾を使用すること
3. speaker1は専門知識を分かりやすく、時には例え話で説明する
4. 1つの発話は2〜3文程度にまとめる（内容は充実させつつ、簡潔に）
5. 感嘆詞（「へえ〜」「すごい！」「なるほど」など）を自然に入れる
6. 新しい発見や驚きがある展開にする
7. 聞き手（視聴者）が「もっと知りたい」と思うような会話にする
8. 具体的な数字、事例、メリット・デメリットなどを積極的に話題に含める
9. 技術的な内容も分かりやすい例え話で説明する

【非常に重要】会話形式について：
10. 質問・答えの単調なパターンを避けてください
11. 以下のような多様な会話パターンを使い分けてください：
    - 一緒に考える：「そういえば、これって〜とも関係してるよね」
    - 追加情報を提供：「あ、それで思い出したけど〜」
    - 体験談を共有：「実は前に〜したことがあって」
    - 別の視点を提示：「でも、こういう見方もできるよね」
    - 具体例を挙げる：「たとえば〜の場合は〜」
    - 共感を示す：「それは私も同じこと思ってた！」
    - 話を広げる：「それに関連して、〜も面白いよね」
12. 「どうして？」「なぜ？」のような直接的な質問ばかりでなく、感想や意見を交えた会話に
13. 両者が情報を持ち寄り、共に学び合うような会話に

重要な制約：
10. キャラクターは絶対に「スライド」という言葉を使わないでください
11. 「次のページ」「この図」「ここに書いてある」など、プレゼン資料への直接的な言及も避けてください
12. あくまで二人が知識を共有する自然な会話として展開してください
13. 最初のトピック以外では「こんにちは」「今日は」「今回は」などの挨拶は使わないでください

音声合成用の重要なルール：
14. 英単語は必ずカタカナで表記してください（音声合成エンジンが正しく読み上げるため）
15. 例：
    - Claude Code → クロードコード
    - AI → エーアイ
    - ChatGPT → チャットジーピーティー
    - Anthropic → アンソロピック
    - Constitutional AI → コンスティテューショナル エーアイ
    - OpenAI → オープンエーアイ
    - GPT → ジーピーティー
    - LLM → エルエルエム
    - Machine Learning → マシーンラーニング
    - Deep Learning → ディープラーニング
    - Google → グーグル
    - Microsoft → マイクロソフト
    - API → エーピーアイ
    - GitHub → ギットハブ
    - Python → パイソン
    - JavaScript → ジャバスクリプト
    - TypeScript → タイプスクリプト
    - React → リアクト
    - Node.js → ノードジェイエス
    - Docker → ドッカー
    - Kubernetes → クーベルネティス
    - AWS → エーダブリューエス
    - Azure → アジュール
    - Firebase → ファイアベース
    - md/MD → エムディー
    - yaml/YAML/yml/YML → ヤムル
    - JSON → ジェイソン
    - HTML → エイチティーエムエル
    - CSS → シーエスエス
    - SQL → エスキューエル
    - NoSQL → ノーエスキューエル
    - REST → レスト
    - GraphQL → グラフキューエル
16. 固有名詞や製品名も日本語の音声として自然に聞こえるようカタカナ表記にしてください

出力形式：
必ず以下のような有効なJSON形式で出力してください。コードブロックや余計な文字は含めないでください。
speakerは必ず"speaker1"か"speaker2"を使用してください。
{
  "dialogue": [
    {"speaker": "speaker1", "text": "今日はクロードコードの魅力について話すよ！"},
    {"speaker": "speaker2", "text": "おお、楽しみ！クロードコードって何がすごいの？"}
  ]
}"""
        
        user_prompt = """トピック{slide_number}/{total_slides}の内容について、{speaker1_name}と{speaker2_name}の魅力的な対話を作成してください。

""".format(
            slide_number=slide_number,
            total_slides=total_slides,
            speaker1_name=speaker1_name,
            speaker2_name=speaker2_name
        )
        
        # 過去の対話がある場合は追加（直近2スライド分のみ）
        if previous_dialogues:
            user_prompt += "これまでの対話内容:\n"
            # 直近の2スライド分のみを取得
            recent_slides = sorted(previous_dialogues.keys())[-2:]
            for prev_slide in recent_slides:
                prev_dialogue = previous_dialogues[prev_slide]
                user_prompt += "\n{}:\n".format(prev_slide)
                for dialogue in prev_dialogue:
                    user_prompt += "- {}: {}\n".format(dialogue['speaker'], dialogue['text'])
            user_prompt += "\n"
        
        user_prompt += """現在扱うトピック（{}番目）の内容：

【重要】以下の内容すべてについて網羅的に話してください。最初の部分だけでなく、リストや図表、結論など、すべての要素を取り上げてください。
""".format(slide_number)
        user_prompt += slide_text
        
        # スライドの種類を判定（表紙・表題スライド・アジェンダかどうか）
        is_title_slide = False
        is_agenda_slide = False
        
        # アジェンダ/目次スライドの検出
        agenda_keywords = ['アジェンダ', '目次', 'Agenda', 'Contents', '内容', '今日の内容', '本日の内容']
        if any(keyword in slide_text for keyword in agenda_keywords):
            is_agenda_slide = True
        
        if slide_number == 1:  # 最初のスライド
            is_title_slide = True
        elif slide_number == total_slides:  # 最後のスライド（まとめや終了スライドの可能性）
            # テキストに「ありがとう」「終」「まとめ」「おわり」などが含まれるかチェック
            end_keywords = ['ありがとう', '終', 'まとめ', 'おわり', 'Thank', 'End', 'Summary', 'Conclusion']
            if any(keyword in slide_text for keyword in end_keywords):
                is_title_slide = True
        elif len(slide_text.strip()) < 100:  # テキストが短い（タイトルのみの可能性）
            is_title_slide = True
        
        # 対話回数の設定（目安時間から逆算）
        # 日本語の読み上げ速度を約330文字/分として計算
        chars_per_second = 5.5
        # 各発話の平均文字数を実際的な値に設定（GPT-4は2-4文で80-100文字程度生成する傾向）
        avg_chars_per_utterance = 90
        # スライド間の間隔0.5秒、発話間の間隔0.3秒を考慮
        # 各スライドの発話数を推定（例：10発話なら3秒の間隔）
        estimated_utterances_raw = (target_seconds_per_slide * chars_per_second) / avg_chars_per_utterance
        pause_time = 0.5 + (estimated_utterances_raw * 0.3)  # スライド間隔 + 発話間隔
        
        # 利用可能な秒数から発話数を再計算
        available_seconds = target_seconds_per_slide - pause_time
        estimated_utterances = max(2, int((available_seconds * chars_per_second) / avg_chars_per_utterance))
        
        # 最小値と最大値を設定（時間制約を厳守）
        if is_title_slide:
            # タイトルスライドは短めに
            min_utterances = min(4, estimated_utterances)
            max_utterances = min(6, estimated_utterances)
            dialogue_count_instruction = f"{min_utterances}〜{max_utterances}個の発話で簡潔に"
            min_dialogues_for_this_slide = min_utterances
        elif is_agenda_slide:
            # アジェンダスライドは特に短く（3〜4回の対話）
            min_utterances = 3
            max_utterances = 4
            dialogue_count_instruction = "3〜4個の発話で簡潔に（speaker1が項目を読み上げ、speaker2が最後に期待感を示すだけ）"
            min_dialogues_for_this_slide = min_utterances
        else:
            # 通常スライドは計算値を尊重（最低値の強制をしない）
            min_utterances = max(2, int(estimated_utterances * 0.8))
            max_utterances = int(estimated_utterances * 1.2)
            # 各発話の目安文字数も明示
            chars_per_utterance_instruction = int(avg_chars_per_utterance * 0.8)
            dialogue_count_instruction = "{}〜{}個の発話を作成（各発話は{}文字程度、目安時間約{}秒）".format(min_utterances, max_utterances, chars_per_utterance_instruction, int(target_seconds_per_slide))
            min_dialogues_for_this_slide = min_utterances
            
        # 追加プロンプトで対話回数が明示的に指定されている場合は上書き
        if additional_prompt and any(word in additional_prompt for word in ['短く', '少なく', '2回', '3回', '4回']):
            match = re.search(r'(\d+)回', additional_prompt)
            if match:
                count = int(match.group(1))
                dialogue_count_instruction = "{}回の掛け合い（{}個の発話）を作成".format(count, count*2)
                min_dialogues_for_this_slide = count * 2
            else:
                dialogue_count_instruction = "4〜6回の会話のやり取りを作成"
                min_dialogues_for_this_slide = 4
        
        # アジェンダスライドの場合の特別な指示
        if is_agenda_slide:
            agenda_instruction = '''【アジェンダスライド専用の指示】
このスライドはアジェンダ（目次）スライドです。以下のルールを厳守してください：

1. speaker1（{}）の役割：
   - アジェンダの項目を一つ一つ、省略せずに読み上げる
   - 「今日は〜について、まず〇〇、次に△△、そして□□について見ていきます」のような形式で
   - 各項目を読む際、深い内容には踏み込まない（項目名の紹介に留める）
   - 全ての項目を漏れなく紹介する

2. speaker2（{}）の役割：
   - speaker1が全ての項目を読み上げるまで待つ
   - 最後に「楽しみだね！」「面白そうだ！」などの短い期待感を表現するだけ
   - 質問や深い感想は言わない

3. 対話の流れ：
   - speaker1がアジェンダを網羅的に紹介
   - speaker2が最後に短く期待感を示す
   - 3〜4回程度の短い対話で終了'''.format(speaker1_name, speaker2_name)
        else:
            agenda_instruction = ""

        user_prompt += """

重要な要望：
- このトピックについて{}
- 会話は具体的で内容が濃いものにする（単なる相槌ではなく、情報を含む発話）
- speaker1は設定された話し方で専門知識を噛み砕いて、例え話や具体例を交えて丁寧に説明
- speaker2は設定された話し方で具体的な質問や感想を述べる
- 過去の対話内容がある場合は、その文脈を踏まえて自然な流れで会話を続ける
- 前の話題で説明した内容は「さっき話した〜」のように参照する
- 話題の重複を避け、新しい情報や視点を提供する
- 以下の要素を必ず含める：
  * トピックの主要なポイントの詳細な説明
  * スライド内のすべての要素（リスト、図表、グラフ、結論など）の説明
  * 具体的な例や応用例の紹介
  * 多様な会話パターン（質問だけでなく、意見、感想、体験談など）
  * 関連する豆知識や補足情報
- 単純な「なるほど」「そうね」だけの返答は避ける
- 視聴者が理解を深められるよう、段階的に説明を展開

{}

必ず有効なJSON形式（{{"dialogue": [...]}}の形式）で出力してください。""".format(
            dialogue_count_instruction,
            agenda_instruction if is_agenda_slide else ('''特別な注意：
これは表紙・タイトルページなので、簡潔に導入してください：
- 挨拶と今日のテーマの紹介に焦点を当てる
- 詳細は後で説明することを示唆する（「後のスライド」とは言わない）
- 期待感を高める内容にする''' if is_title_slide else '''特別な注意：
これは{}番目のトピックです：
- 「こんにちは」「今日は」「今回は」などの挨拶は絶対に使わないでください
- 前のトピックから自然に話を続けてください
- いきなり本題から入って構いません'''.format(slide_number))
        )
        
        # 追加プロンプトがある場合は付加
        if additional_prompt:
            user_prompt += "\n\n追加の指示：\n{}".format(additional_prompt)

        # リトライループ
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
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
                    print(f"スライド{slide_number}の応答が空です（試行{attempt+1}/{max_retries}）")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        raise Exception(f"スライド{slide_number}の対話生成に失敗しました：応答が空です")
                
                # JSONとして解析
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
                    
                    # 上で設定した最小対話数を使用
                    if isinstance(dialogue_list, list) and len(dialogue_list) >= min_dialogues_for_this_slide:
                        print(f"スライド{slide_number}の対話生成成功（{len(dialogue_list)}件の対話）")
                        return dialogue_list
                    else:
                        print(f"スライド{slide_number}の対話が不十分です（{len(dialogue_list)}件、最小{min_dialogues_for_this_slide}件必要）（試行{attempt+1}/{max_retries}）")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            raise Exception(f"スライド{slide_number}の対話生成に失敗しました：対話数が不十分（{len(dialogue_list)}件、最小{min_dialogues_for_this_slide}件必要）")
                        
                except json.JSONDecodeError as e:
                    print(f"スライド{slide_number}のJSON解析エラー: {e}（試行{attempt+1}/{max_retries}）")
                    print(f"レスポンス内容: {content[:500]}...")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        raise Exception(f"スライド{slide_number}の対話生成に失敗しました：JSON解析エラー - {str(e)}")
                
            except Exception as e:
                import traceback
                print(f"スライド{slide_number}の対話生成エラー: {e}（試行{attempt+1}/{max_retries}）")
                print(f"エラー詳細: {traceback.format_exc()}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2)  # リトライ前に2秒待機
                    continue
                else:
                    raise Exception(f"スライド{slide_number}の対話生成に失敗しました：{str(e)}")
    
    
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
6. 各トピックで新しい発見や驚きがある展開にする
7. 聞き手（視聴者）が「もっと知りたい」と思うような会話にする
8. 具体的な数字、事例、メリット・デメリットなどを積極的に話題に含める
9. 技術的な内容も分かりやすい例え話で説明する

重要な制約：
10. キャラクターは絶対に「スライド」という言葉を使わないでください
11. 「次のページ」「この図」「ここに書いてある」など、プレゼン資料への直接的な言及も避けてください
12. あくまで二人が知識を共有する自然な会話として展開してください
13. 最初のトピック以外では「こんにちは」「今日は」「今回は」などの挨拶は使わないでください

音声合成用の重要なルール：
14. 英単語は必ずカタカナで表記してください（音声合成エンジンが正しく読み上げるため）
15. 例：Claude Code → クロードコード、AI → エーアイ、ChatGPT → チャットジーピーティー、Google → グーグル、API → エーピーアイ
16. 固有名詞や製品名も日本語の音声として自然に聞こえるようカタカナ表記にしてください

出力形式：
必ず以下のような有効なJSON形式で出力してください。コードブロックや余計な文字は含めないでください。
{
  "slide_1": [
    {"speaker": "metan", "text": "今日はクロードコードの魅力について話すよ！"},
    {"speaker": "zundamon", "text": "おお、楽しみなのだ！クロードコードって何がすごいのだ？"}
  ],
  "slide_2": [...]
}"""
        
        # スライドテキストを結合
        slides_content = "\n\n".join([
            f"スライド{i+1}:\n" + text
            for i, text in enumerate(slide_texts)
        ])
        
        user_prompt = """以下のトピック内容を、めたんとずんだもんの魅力的な対話で解説してください。

"""
        user_prompt += slides_content
        user_prompt += """

重要な要望：
- 各トピックごとに必ず8〜12回の会話のやり取りを作成（最低でも8回以上）
- 会話は具体的で内容が濃いものにする（単なる相槌ではなく、情報を含む発話）
- ずんだもんは「〜なのだ」語尾を必ず使用し、具体的な質問や感想を述べる
- めたんは専門知識を噛み砕いて、例え話や具体例を交えて丁寧に説明
- 以下の要素を必ず含める：
  * トピックの主要なポイントの詳細な説明
  * 具体的な例や応用例の紹介
  * ずんだもんからの掘り下げた質問
  * めたんによる分かりやすい回答
  * 関連する豆知識や補足情報
- 単純な「なるほど」「そうなのだ」だけの返答は避ける
- 視聴者が理解を深められるよう、段階的に説明を展開

必ず有効なJSON形式で出力してください。"""
        
        # 追加プロンプトがある場合は付加
        if additional_prompt:
            user_prompt += "\n\n追加の指示：\n{}".format(additional_prompt)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
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
                raise Exception("OpenAIからの応答が空です")
            
            try:
                dialogue_data = json.loads(content)
                # 必要なキーが存在するか確認
                expected_keys = [f"slide_{i+1}" for i in range(len(slide_texts))]
                if all(key in dialogue_data for key in expected_keys):
                    return dialogue_data
                else:
                    missing_keys = [key for key in expected_keys if key not in dialogue_data]
                    raise Exception(f"対話データのキーが不足しています。不足キー: {missing_keys}")
            except json.JSONDecodeError as e:
                print(f"JSON解析エラー: {e}")
                print(f"レスポンス内容: {repr(content[:500])}...")  # 最初の500文字を表示
                raise Exception(f"対話生成に失敗しました：JSON解析エラー - {str(e)}")
            
        except Exception as e:
            print(f"対話生成エラー: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"対話生成に失敗しました：{str(e)}")
    
    
    def save_dialogue_data(self, dialogue_data: Dict, output_path: str):
        """対話データを保存"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_data, f, ensure_ascii=False, indent=2)