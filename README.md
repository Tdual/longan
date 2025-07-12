# Longan - AI動画ナレーションジェネレーター

PDFスライドを日本語音声付きの動画に変換するツールです。VOICEVOXを使用して、選択可能なキャラクターによる対話形式のナレーションを生成できます。

## 特徴

- PDFページをスライド画像に変換
- VOICEVOXを使用した高品質な日本語音声合成
- 四国めたんとずんだもんによる対話形式のナレーション
- スライドと音声を同期した動画生成
- カスタマイズ可能な対話内容

## 必要な環境

- Python 3.8+
- VOICEVOX（音声合成エンジン）
- conda環境推奨（NumPy互換性のため）

### Docker環境での実行も可能

Dockerを使用すれば、VOICEVOXの環境構築が不要になります。
詳細は[README_DOCKER.md](README_DOCKER.md)を参照してください。

## インストール

1. VOICEVOXをダウンロード・インストールし、起動してください
2. 必要なPythonパッケージをインストール：

```bash
pip install moviepy pdf2image pillow requests numpy<2
```

3. NumPy互換性のため、NumPy 1.xを使用してください：

```bash
pip install "numpy<2"
```

## 使用方法

### 基本的な使い方

1. PDFファイルをプロジェクトディレクトリに配置
2. VOICEVOXを起動（デフォルト: http://localhost:50021）
3. 音声を生成：
   ```bash
   python scripts/generate_audio.py
   ```
4. 動画を生成：
   ```bash
   python scripts/create_video.py
   ```

### プロジェクト構成

#### ディレクトリ構造
```
gen_movie/
├── src/                    # コアライブラリ
│   ├── dialogue_video_creator.py           # 高品質動画作成
│   ├── voicevox_generator.py               # VOICEVOX音声生成
│   ├── pdf_converter.py                    # PDF→画像変換
│   └── english_to_katakana.py              # 英語→カタカナ変換
├── scripts/                # 実行スクリプト
│   ├── create_video.py                     # 動画作成
│   ├── generate_audio.py                   # 音声生成（抑揚1.2）
│   └── generate_katakana_audio.py          # カタカナ音声生成
├── data/                   # 設定・データファイル
│   └── dialogue_narration_katakana.json    # カタカナ対応対話内容
├── output/                 # 動画出力
├── slides/                 # スライド画像
└── audio/                  # 音声ファイル
```

#### 実行方法
```bash
python scripts/create_video.py
```

## 対話内容のカスタマイズ

`data/dialogue_narration_katakana.json`ファイルで対話内容をカスタマイズできます：

```json
{
  "slide_1": [
    {"speaker": "metan", "text": "四国めたんのセリフ"},
    {"speaker": "zundamon", "text": "ずんだもんのセリフ"}
  ],
  "slide_2": [
    {"speaker": "metan", "text": "次のスライドの内容"},
    {"speaker": "zundamon", "text": "ずんだもんの返答"}
  ]
}
```

### 音声品質の特徴

- 抑揚を1.2に設定して表現豊かな音声を実現
- 各音声の終わりに50msのフェードアウトを適用
- 話者間の間隔を0.8秒に最適化
- 音量レベルを90%に調整
- 英語単語のカタカナ変換に対応
- ポップノイズの除去

## 音声キャラクター

- **四国めたん** (speaker ID: 2) - AI専門家役
- **ずんだもん** (speaker ID: 3) - 聞き役・ツッコミ役

## トラブルシューティング

### NumPy互換性エラー
```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.0.2
```
**解決策**: NumPy 1.xにダウングレード
```bash
pip install "numpy<2"
```

### 動画が開けない（moov atom not found）
**原因**: NumPy 2.xとの互換性問題
**解決策**: NumPy 1.xを使用し、成功したコードを再実行

### VOICEVOX接続エラー
**確認事項**:
1. VOICEVOXが起動していること
2. ポート50021でアクセス可能なこと
3. ファイアウォールでブロックされていないこと

## 出力

- 生成された動画ファイル（output/ディレクトリ）
- スライド画像（slides/ディレクトリ）
- 音声ファイル（audio/ディレクトリ）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 謝辞

- VOICEVOX: 高品質な日本語音声合成エンジン
- 四国めたん・ずんだもん: 魅力的な音声キャラクター