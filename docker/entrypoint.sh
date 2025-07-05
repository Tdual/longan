#!/bin/bash
set -e

# VOICEVOXエンジンをバックグラウンドで起動
python /app/start_voicevox.py &
VOICEVOX_PID=$!

# VOICEVOXが起動するまで待機
echo "VOICEVOXエンジンの起動を待っています..."
for i in {1..30}; do
    if curl -s http://localhost:50021/version > /dev/null; then
        echo "✅ VOICEVOXエンジンが起動しました"
        break
    fi
    sleep 1
done

# コマンドが指定されていれば実行
if [ $# -gt 0 ]; then
    exec "$@"
else
    # デフォルトはbashを起動
    exec /bin/bash
fi

# 終了時にVOICEVOXも終了
trap "kill $VOICEVOX_PID" EXIT