#!/bin/bash

echo "📦 PDFから動画生成ツール - セットアップ"
echo "======================================="

# OSの検出
OS="Unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
fi

echo "🖥️  検出されたOS: $OS"

# popplerのインストール確認
echo ""
echo "📋 popplerのインストールを確認中..."
if ! command -v pdfinfo &> /dev/null; then
    echo "⚠️  popplerがインストールされていません。"
    
    if [[ "$OS" == "macOS" ]]; then
        echo "Homebrewでインストールします："
        echo "brew install poppler"
    elif [[ "$OS" == "Linux" ]]; then
        echo "apt-getでインストールします："
        echo "sudo apt-get install poppler-utils"
    fi
    echo ""
    read -p "インストールを続行しますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ "$OS" == "macOS" ]]; then
            brew install poppler
        elif [[ "$OS" == "Linux" ]]; then
            sudo apt-get update && sudo apt-get install -y poppler-utils
        fi
    else
        echo "⚠️  popplerのインストールをスキップしました。pdf2imageが動作しない可能性があります。"
    fi
else
    echo "✅ popplerは既にインストールされています。"
fi

# Pythonパッケージのインストール
echo ""
echo "📦 Pythonパッケージをインストール中..."
pip install -r requirements.txt

echo ""
echo "✅ セットアップが完了しました！"
echo ""
echo "🚀 使い方："
echo "1. サンプルデモを実行: ./run_demo.sh"
echo "2. 独自のPDFを変換: python main.py your_file.pdf --narration your_narration.json"