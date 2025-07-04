# PDF to Video Converter with Japanese Voice

PDFスライドを日本語音声付きの動画に変換するツールです。VOICEVOXを使用して、四国めたんとずんだもんによる対話形式のナレーションを生成できます。

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
3. 対話内容を設定（`dialogue_narration_synced.json`参照）
4. 動画を生成：

```bash
python create_final_funny_video.py
```

### 主要なファイル

#### コアファイル
- `create_final_funny_video.py` - 最終的な面白い対話動画を生成
- `dialogue_video_creator_fixed.py` - 動画作成エンジン（音声途切れ修正版）
- `dialogue_voicevox_generator.py` - VOICEVOX音声生成
- `pdf_converter.py` - PDF→画像変換

#### 設定ファイル
- `dialogue_narration_synced.json` - 面白い対話内容（スライドと同期）
- `requirements.txt` - Python依存パッケージ

#### ユーティリティ
- `create_working_video.py` - 基本動画作成（動作確認用）
- `generate_remaining_audio.py` - 追加音声生成

## 対話内容のカスタマイズ

`dialogue_narration_synced.json`ファイルで対話内容をカスタマイズできます：

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

- 生成された動画ファイル（.mp4）
- スライド画像（slides/ディレクトリ）
- 音声ファイル（audio_synced/ディレクトリ）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 謝辞

- VOICEVOX: 高品質な日本語音声合成エンジン
- 四国めたん・ずんだもん: 魅力的な音声キャラクター