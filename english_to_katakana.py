#!/usr/bin/env python3
import json
import re

def create_katakana_dictionary():
    """英語をカタカナに変換する辞書を作成"""
    return {
        # 基本的な英語単語
        "Claude": "クロード",
        "Code": "コード", 
        "claude": "クロード",
        "code": "コード",
        
        # 技術用語
        "AWS": "エーダブリューエス",
        "Bedrock": "ベッドロック",
        "Node": "ノード",
        "npm": "エヌピーエム",
        "install": "インストール",
        "g": "ジー",
        
        # 複合語
        "Node.js": "ノードジェイエス",
        "Claude Code": "クロード コード",
        "AWS Bedrock": "エーダブリューエス ベッドロック",
        "npm install": "エヌピーエム インストール",
        "claude-code": "クロード コード",
        "VSCode": "ブイエスコード",
        "GitHub": "ギットハブ",
        "CLI": "シーエルアイ",
        "API": "エーピーアイ",
        "WSL": "ダブリューエスエル",
        "Web": "ウェブ",
        "MatrixFlow": "マトリックスフロー",
        "Opus": "オーパス",
        "Think": "シンク",
        "verbose": "バーボーズ",
        "session": "セッション",
        "reset": "リセット",
        "debug": "デバッグ"
    }

def convert_text_to_katakana(text, katakana_dict):
    """テキスト内の英語をカタカナに変換"""
    # 複合語から長い順に変換（部分一致を避けるため）
    sorted_keys = sorted(katakana_dict.keys(), key=len, reverse=True)
    
    result = text
    for english_word in sorted_keys:
        # 大文字小文字を区別しない置換
        pattern = re.compile(re.escape(english_word), re.IGNORECASE)
        result = pattern.sub(katakana_dict[english_word], result)
    
    return result

def main():
    # 対話データを読み込み
    with open("dialogue_narration_synced.json", 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # カタカナ辞書を作成
    katakana_dict = create_katakana_dictionary()
    
    # 変換後のデータを作成
    converted_data = {}
    
    for slide_key, conversations in dialogue_data.items():
        converted_data[slide_key] = []
        
        for conv in conversations:
            original_text = conv['text']
            converted_text = convert_text_to_katakana(original_text, katakana_dict)
            
            converted_data[slide_key].append({
                'speaker': conv['speaker'],
                'text': converted_text,
                'original_text': original_text  # 元のテキストも保存
            })
            
            # 変換があった場合は表示
            if original_text != converted_text:
                print(f"[{slide_key}] {conv['speaker']}:")
                print(f"  変換前: {original_text}")
                print(f"  変換後: {converted_text}")
                print()
    
    # 変換後のデータを保存
    with open('dialogue_narration_katakana.json', 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    
    print("カタカナ変換完了！dialogue_narration_katakana.json に保存しました。")

if __name__ == "__main__":
    main()