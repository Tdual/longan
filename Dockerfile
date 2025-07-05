# VOICEVOX付きPython環境
FROM python:3.10-slim

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# VOICEVOXをダウンロードしてインストール
RUN wget https://github.com/VOICEVOX/voicevox_core/releases/download/0.14.4/voicevox_core-0.14.4+cpu-cp38-abi3-linux_x86_64.whl \
    && pip install voicevox_core-0.14.4+cpu-cp38-abi3-linux_x86_64.whl \
    && rm voicevox_core-0.14.4+cpu-cp38-abi3-linux_x86_64.whl

# Open JTalkの辞書をダウンロード
RUN mkdir -p /app/open_jtalk_dic \
    && wget https://jaist.dl.sourceforge.net/project/open-jtalk/Dictionary/open_jtalk_dic-1.11/open_jtalk_dic_utf_8-1.11.tar.gz \
    && tar -xzf open_jtalk_dic_utf_8-1.11.tar.gz -C /app/open_jtalk_dic --strip-components=1 \
    && rm open_jtalk_dic_utf_8-1.11.tar.gz

# Python依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . /app

# VOICEVOXエンジンを起動するスクリプト
COPY docker/start_voicevox.py /app/start_voicevox.py

# ポートを公開
EXPOSE 50021

# エントリーポイントスクリプト
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]