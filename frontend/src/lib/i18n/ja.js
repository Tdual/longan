// 日本語翻訳
export const ja = {
  status: {
    // ジョブステータス
    pending: "待機中",
    processing: "処理中",
    completed: "完了",
    failed: "失敗",
    
    // 処理ステージ
    PENDING: "待機中",
    PROCESSING: "処理中",
    COMPLETED: "完了",
    FAILED: "失敗",
    PDF_UPLOADING: "PDFをアップロード中...",
    PDF_PROCESSING: "PDFを処理中...",
    PDF_EXTRACTING_TEXT: "PDFからテキストを抽出中...",
    PDF_GENERATING_SLIDES: "スライド画像を生成中...",
    DIALOGUE_GENERATING: "対話スクリプトを生成中...",
    DIALOGUE_PROCESSING: "対話内容を処理中...",
    AUDIO_GENERATING: "音声を生成中...",
    AUDIO_PROCESSING_SLIDE: "各スライドの音声を生成中...",
    VIDEO_CREATING: "動画を作成中...",
    VIDEO_ENCODING: "動画をエンコード中...",
    VIDEO_FINALIZING: "動画を仕上げ中...",
    slides_ready: "対話生成準備完了"
  },
  
  errors: {
    // エラーコード
    FILE_NOT_FOUND: "ファイルが見つかりません",
    INVALID_FILE_FORMAT: "無効なファイル形式です",
    PDF_PROCESSING_ERROR: "PDF処理中にエラーが発生しました",
    DIALOGUE_GENERATION_ERROR: "対話生成中にエラーが発生しました",
    AUDIO_GENERATION_ERROR: "音声生成中にエラーが発生しました",
    VIDEO_CREATION_ERROR: "動画作成中にエラーが発生しました",
    UNKNOWN_ERROR: "不明なエラーが発生しました",
    NO_TEXT_EXTRACTED: "PDFからテキストを抽出できませんでした",
    NO_SLIDES_EXTRACTED: "スライドを抽出できませんでした",
    INVALID_TARGET_DURATION: "無効な目標時間です",
    INVALID_CONVERSATION_STYLE: "無効な会話スタイルです"
  },
  
  ui: {
    upload: "アップロード",
    generate: "生成",
    download: "ダウンロード",
    regenerate: "再生成",
    cancel: "キャンセル",
    save: "保存",
    edit: "編集",
    delete: "削除",
    loading: "読み込み中...",
    processing: "処理中...",
    completed: "完了",
    error: "エラー",
    success: "成功",
    warning: "警告",
    info: "情報"
  }
};