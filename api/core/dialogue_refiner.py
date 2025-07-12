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
        """三段階処理で対話スクリプトを完全に調整"""
        
        print("第一段階：全体の一貫性調整を開始...")
        stage1_result = self._stage1_consistency_adjustment(dialogue_data, speaker_info, adjustment_prompt)
        
        print("第二段階：カタカナ変換（後半重点）を開始...")
        stage2_result = self._stage2_katakana_conversion(stage1_result, speaker_info)
        
        print("第三段階：表記揺れ修正を開始...")
        stage3_result = self._stage3_notation_consistency(stage2_result, speaker_info)
        
        return stage3_result
    
    def _stage1_consistency_adjustment(
        self, 
        dialogue_data: Dict[str, List[Dict]], 
        speaker_info: Optional[Dict] = None,
        adjustment_prompt: Optional[str] = None
    ) -> Dict[str, List[Dict]]:
        """第一段階：全体の一貫性調整"""
        
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
        system_prompt = f"""あなたは日本語の対話スクリプトの一貫性調整の専門家です。
以下の指示に従って対話スクリプトの全体的な流れを調整してください：

1. 全体の流れと一貫性をチェックし、必要に応じて調整
2. 話者のキャラクター性を保持
3. 各発話は簡潔に（一文あたり40文字以内を目安）
4. 対話の自然さと教育的価値を向上

話者情報：
- {speaker1_name}: speaker1として表示される話者
- {speaker2_name}: speaker2として表示される話者

出力形式は元の形式を保持してください。"""

        user_prompt = f"以下の対話スクリプトの全体的な一貫性を調整してください。"
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
    
    def _stage2_katakana_conversion(
        self, 
        dialogue_data: Dict[str, List[Dict]], 
        speaker_info: Optional[Dict] = None
    ) -> Dict[str, List[Dict]]:
        """第二段階：カタカナ変換（後半重点）"""
        
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
        
        # カタカナ変換専用プロンプト
        system_prompt = f"""あなたは英語→カタカナ変換の専門家です。
【最重要任務】対話スクリプト内のすべての英語・ローマ字を漏れなくカタカナに変換してください。

【特に重要】後半のスライドほど注意深く確認してください。最後のスライドまで必ず英語が残っていないか確認すること。

変換例（これらは一例で、他の英語もすべて変換してください）：
- AI → エーアイ、API → エーピーアイ、PDF → ピーディーエフ
- Claude → クロード、ChatGPT → チャットジーピーティー
- Anthropic → アンソロピック、Constitutional AI → コンスティテューショナル エーアイ
- OpenAI → オープンエーアイ、GPT → ジーピーティー
- LLM → エルエルエム、NLP → エヌエルピー
- Machine Learning → マシーンラーニング、Deep Learning → ディープラーニング
- PowerPoint → パワーポイント、Excel → エクセル
- JavaScript → ジャバスクリプト、Python → パイソン
- TypeScript → タイプスクリプト、React → リアクト
- Node.js → ノードジェイエス、Vue.js → ビュージェイエス
- GitHub → ギットハブ、Docker → ドッカー
- Kubernetes → クーベルネティス、DevOps → デブオプス
- HTML → エイチティーエムエル、CSS → シーエスエス
- JSON → ジェイソン、XML → エックスエムエル
- HTTP → エイチティーティーピー、HTTPS → エイチティーティーピーエス
- REST → レスト、GraphQL → グラフキューエル
- USB → ユーエスビー、CLI → シーエルアイ
- SQL → エスキューエル、NoSQL → ノーエスキューエル
- MongoDB → モンゴディービー、PostgreSQL → ポストグレエスキューエル
- AWS → エーダブリューエス、Azure → アジュール
- Google → グーグル、Microsoft → マイクロソフト
- Windows → ウィンドウズ、Mac → マック、Linux → リナックス
- iOS → アイオーエス、Android → アンドロイド
- Swift → スウィフト、Kotlin → コトリン
- Firebase → ファイアベース、Stripe → ストライプ
- WordPress → ワードプレス、Drupal → ドルーパル
- Bootstrap → ブートストラップ、Tailwind → テイルウィンド
- Figma → フィグマ、Sketch → スケッチ
- Slack → スラック、Discord → ディスコード
- Zoom → ズーム、Teams → チームズ
- md/MD → エムディー、yaml/YAML/yml/YML → ヤムル
- IDE → アイディーイー、SDK → エスディーケー、Framework → フレームワーク

【処理手順】
1. 最初から最後のスライドまで順番に確認
2. 各発話で英語・ローマ字を発見したら即座にカタカナに変換
3. 特に後半のスライドは二重チェック
4. 変換後、全体を再度確認して英語が残っていないことを確認

話者情報：
- {speaker1_name}: speaker1として表示される話者
- {speaker2_name}: speaker2として表示される話者

出力形式は元の形式を保持してください。内容は変更せず、英語のカタカナ変換のみ行ってください。"""

        user_prompt = f"以下の対話スクリプト内のすべての英語・ローマ字をカタカナに変換してください。後半のスライドまで漏れなく確認してください。\n\n対話スクリプト:\n{dialogue_text}"
        
        # GPTでカタカナ変換
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # より確実な変換のため低温度
            max_tokens=4000
        )
        
        refined_text = response.choices[0].message.content
        
        # 調整されたテキストを元の形式に戻す
        refined_dialogue = self._parse_refined_dialogue(refined_text, dialogue_data)
        
        return refined_dialogue
    
    def _stage3_notation_consistency(
        self, 
        dialogue_data: Dict[str, List[Dict]], 
        speaker_info: Optional[Dict] = None
    ) -> Dict[str, List[Dict]]:
        """第三段階：表記揺れ修正"""
        
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
        
        # 表記揺れ修正専用プロンプト
        system_prompt = f"""あなたは表記統一の専門家です。
対話スクリプト全体で表記の一貫性を確保してください。

【修正対象】
1. 同じ技術用語・製品名の表記揺れを統一
2. カタカナ表記の統一（例：「エーアイ」「A.I.」→「エーアイ」に統一）
3. 数字・記号の表記統一
4. 助詞・語尾の統一

【重要】内容は変更せず、表記の統一のみ行ってください。

話者情報：
- {speaker1_name}: speaker1として表示される話者
- {speaker2_name}: speaker2として表示される話者

出力形式は元の形式を保持してください。"""

        user_prompt = f"以下の対話スクリプトの表記揺れを修正し、全体で一貫した表記に統一してください。\n\n対話スクリプト:\n{dialogue_text}"
        
        # GPTで表記統一
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # より確実な統一のため低温度
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
    
