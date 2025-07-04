#!/bin/bash

echo "📦 PDFスライドから動画生成デモ"
echo "================================"

# conda環境のアクティベートを試みる
if command -v conda &> /dev/null; then
    echo "🔧 conda環境をアクティベート中..."
    eval "$(conda shell.bash hook)"
    conda activate py3.12 2>/dev/null || echo "⚠️  py3.12環境が見つかりません。現在の環境で続行します。"
fi

# 必要なパッケージの確認
echo ""
echo "📋 必要なパッケージを確認中..."
python -c "import pdf2image" 2>/dev/null || {
    echo "⚠️  必要なパッケージがインストールされていません。"
    echo "以下のコマンドでインストールしてください："
    echo "pip install -r requirements.txt"
    exit 1
}

# サンプルPDFの作成
if [ ! -f "sample_presentation.pdf" ]; then
    echo ""
    echo "📄 サンプルPDFを作成中..."
    python create_sample_pdf.py
fi

# 動画の生成
echo ""
echo "🎬 動画を生成中..."
echo "コマンド: python main.py sample_presentation.pdf --narration sample_narration.json --output demo_output.mp4"
python main.py sample_presentation.pdf --narration sample_narration.json --output demo_output.mp4

echo ""
echo "✅ 完了！demo_output.mp4 が作成されました。"