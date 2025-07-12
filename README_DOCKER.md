# Docker環境での実行方法

VOICEVOXをDocker環境で実行する方法を説明します。

## 方法1: 公式VOICEVOXイメージを使用（推奨）

VOICEVOX公式のDockerイメージを使用する最も簡単な方法です。

### 起動方法

1. Docker Composeで起動：
   ```bash
   docker-compose -f docker-compose.simple.yml up -d
   ```

2. アプリケーションコンテナに入る：
   ```bash
   docker-compose -f docker-compose.simple.yml exec longan bash
   ```

3. コンテナ内で音声生成と動画作成：
   ```bash
   # 音声を生成
   python scripts/generate_audio.py
   
   # 動画を作成
   python scripts/create_video.py
   ```

4. 終了：
   ```bash
   docker-compose -f docker-compose.simple.yml down
   ```

### 利点
- VOICEVOX公式イメージを使用するため、安定性が高い
- セットアップが簡単
- ホストマシンにVOICEVOXをインストール不要

## 方法2: カスタムDockerイメージ（上級者向け）

VOICEVOXを含む単一のDockerイメージを作成する方法です。

### ビルドと起動

1. イメージをビルド：
   ```bash
   docker build -t longan_voicevox .
   ```

2. Docker Composeで起動：
   ```bash
   docker-compose up -d
   ```

3. コンテナに入って作業：
   ```bash
   docker-compose exec gen_movie bash
   ```

## トラブルシューティング

### VOICEVOXに接続できない場合

1. コンテナが起動しているか確認：
   ```bash
   docker ps
   ```

2. VOICEVOXのログを確認：
   ```bash
   docker-compose -f docker-compose.simple.yml logs voicevox-engine
   ```

3. ポート50021が使用されていないか確認：
   ```bash
   lsof -i :50021
   ```

### メモリ不足エラー

Dockerのメモリ割り当てを増やしてください：
- Docker Desktop: Preferences → Resources → Memory を4GB以上に設定

## 注意事項

- 初回起動時はVOICEVOXのモデルダウンロードに時間がかかります
- CPU版を使用するため、GPU版より処理が遅い場合があります
- 生成されたファイルはホストマシンのディレクトリに保存されます