#!/usr/bin/env python3
import json
import re

def extract_english_words(text):
    """テキストから英語単語を抽出する"""
    # 英語の単語・フレーズを検出するパターン
    patterns = [
        r'\b[A-Za-z]+\.[A-Za-z]+\b',  # node.js のようなドット付き
        r'\b[A-Z][a-z]*[A-Z][a-zA-Z]*\b',  # CamelCase
        r'\b[A-Z]{2,}\b',  # 全部大文字（API, AWS, etc.）
        r'\b[A-Za-z]+\b',  # 通常の英単語
    ]
    
    english_words = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        english_words.update(matches)
    
    return english_words

def main():
    # 対話データを読み込み
    with open("dialogue_narration_synced.json", 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    all_english_words = set()
    word_locations = {}  # 単語がどこに出現するかを記録
    
    for slide_key, conversations in dialogue_data.items():
        for conv in conversations:
            text = conv['text']
            words = extract_english_words(text)
            
            for word in words:
                all_english_words.add(word)
                if word not in word_locations:
                    word_locations[word] = []
                word_locations[word].append({
                    'slide': slide_key,
                    'speaker': conv['speaker'],
                    'text': text
                })
    
    # 結果を保存
    result = {
        'total_words': len(all_english_words),
        'words': sorted(list(all_english_words)),
        'locations': word_locations
    }
    
    with open('english_words_detected.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"検出された英語単語数: {len(all_english_words)}")
    print("英語単語一覧:")
    for word in sorted(all_english_words):
        print(f"  - {word}")

if __name__ == "__main__":
    main()