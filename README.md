# Longan - AI動画ナレーションジェネレーター

PDFスライドを日本語音声付きの動画に変換するツールです。VOICEVOXを使用して、選択可能なキャラクターによる対話形式のナレーションを生成できます。

## 特徴

- 📄 PDFページをスライド画像に変換
- 🎙️ VOICEVOXを使用した高品質な日本語音声合成（18種類のキャラクター）
- 💬 OpenAI GPT-4による自然な対話形式のナレーション自動生成
- 🎬 スライドと音声を同期した動画生成
- ✏️ Webアプリで対話内容を編集・再生成可能
- 🔄 三段階のカタカナ変換システムで英語用語も正しく音声化

## 必要な環境

- Python 3.8+
- VOICEVOX（音声合成エンジン）
- OpenAI APIキー（対話生成用）
- Node.js 18+（Webアプリ用）

### 推奨：Docker環境での実行

Dockerを使用すれば、VOICEVOXやNode.jsの環境構築が不要になります。
詳細は[README_DOCKER.md](README_DOCKER.md)を参照してください。

## インストール

### 1. リポジトリのクローン
```bash
git clone https://github.com/Tdual/longan.git
cd longan
```

### 2. 環境変数の設定
`.env`ファイルを作成し、OpenAI APIキーを設定：
```bash
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

### 3. Docker Composeでの起動（推奨）
```bash
docker-compose up -d
```
これで以下のサービスが起動します：
- Webアプリ: http://localhost:3000
- API: http://localhost:8000
- VOICEVOX: http://localhost:50021

### 4. ローカル環境での起動（代替方法）

#### Backend (API)の起動
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend (Webアプリ)の起動
```bash
cd frontend
npm install
npm run dev
```

#### VOICEVOXの起動
VOICEVOXを別途ダウンロードして起動してください。

## 使用方法

### Webアプリでの使い方（推奨）

1. ブラウザで http://localhost:3000 にアクセス
2. PDFファイルをアップロード
3. 以下の設定を行う：
   - 目安時間（分）
   - スピーカー1（デフォルト：四国めたん）
   - スピーカー2（デフォルト：ずんだもん）
   - 会話スタイル（友達風、ビジネス風など）
4. 「動画を生成」ボタンをクリック
5. 生成された対話を確認・編集
6. 動画をダウンロード

### スクリプトでの使い方（上級者向け）

1. PDFファイルを`uploads/`ディレクトリに配置
2. VOICEVOXを起動（デフォルト: http://localhost:50021）
3. 対話と音声を生成：
   ```bash
   python scripts/generate_audio.py
   ```
4. 動画を生成：
   ```bash
   python scripts/create_video.py
   ```

## プロジェクト構成

```
longan/
├── api/                    # FastAPI Backend
│   ├── core/              # コア機能
│   │   ├── dialogue_generator.py    # GPT-4による対話生成
│   │   ├── dialogue_refiner.py      # 三段階カタカナ変換
│   │   ├── audio_generator.py       # VOICEVOX音声生成
│   │   ├── video_creator.py         # 動画作成
│   │   └── pdf_processor.py         # PDF処理
│   └── main.py            # APIエンドポイント
├── frontend/              # SvelteKit Frontend
│   ├── src/              
│   │   └── routes/       # Webアプリ画面
│   └── package.json      
├── src/                   # 共通ライブラリ
│   ├── dialogue_video_creator.py    # 高品質動画作成
│   └── voicevox_generator.py        # VOICEVOX制御
├── docker-compose.yml     # Docker設定
├── uploads/              # アップロードされたPDF
├── output/               # 生成された動画
├── slides/               # 抽出されたスライド画像
└── audio/                # 生成された音声ファイル
```

## API仕様

### エンドポイント

#### POST /api/jobs/upload
PDFをアップロードしてジョブを作成
- Parameters:
  - file: PDFファイル
  - target_duration: 目安時間（分）
  - speaker1_id, speaker2_id: VOICEVOX話者ID
  - conversation_style: 会話スタイル

#### GET /api/jobs/{job_id}/status
ジョブの進行状況を確認

#### POST /api/jobs/{job_id}/regenerate-dialogue
特定のスライドの対話を再生成

#### POST /api/jobs/{job_id}/create-video
最終動画を生成

### VOICEVOX話者ID
- 2: 四国めたん（ノーマル）
- 3: ずんだもん（ノーマル）
- 8: 春日部つむぎ（ノーマル）
- 10: 波音リツ（ノーマル）
- 13: 青山龍星（ノーマル）
- 16: 九州そら（ノーマル）
- 20: もち子さん（ノーマル）

## 主な機能

### 対話生成機能
- GPT-4を使用した自然な対話生成
- スライドの重要度を自動判定し、時間配分を最適化
- スライド間の文脈を保持した一貫性のある対話

### カタカナ変換システム
三段階処理により、英語用語を確実にカタカナに変換：
1. **第一段階**: 全体の一貫性調整
2. **第二段階**: カタカナ変換（後半重点）
3. **第三段階**: 表記揺れ修正

例：
- Anthropic → アンソロピック
- Constitutional AI → コンスティテューショナル エーアイ
- Machine Learning → マシーンラーニング

### 音声品質
- 抑揚を1.2に設定して表現豊かな音声を実現
- 各音声の終わりに50msのフェードアウトを適用
- 話者間の間隔を0.8秒に最適化
- キャラクターごとの話速調整

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