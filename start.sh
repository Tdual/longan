#!/bin/bash

# .envファイルが存在しない場合は.env.exampleをコピー
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo ".env.exampleを.envにコピーしています..."
        cp .env.example .env
        echo "✓ .envファイルを作成しました"
    else
        echo "エラー: .env.exampleファイルが見つかりません"
        exit 1
    fi
fi

# Docker Composeを起動
echo "Docker Composeを起動しています..."
docker-compose up "$@"