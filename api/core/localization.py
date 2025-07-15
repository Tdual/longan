"""
ローカライゼーションサービス
ステータス、進捗メッセージ、エラーメッセージの日本語翻訳を提供
"""

import re
from typing import Dict, Optional


class LocalizationService:
    """ローカライゼーションサービス"""
    
    # ステータス翻訳辞書
    STATUS_TRANSLATIONS = {
        "pending": "待機中",
        "slides_ready": "スライド準備完了",
        "generating_dialogue": "対話生成中",
        "dialogue_ready": "対話準備完了",
        "generating_audio": "音声生成中",
        "audio_ready": "音声準備完了",
        "creating_video": "動画作成中",
        "processing": "処理中",
        "completed": "完了",
        "failed": "失敗"
    }
    
    # エラーメッセージ翻訳辞書
    ERROR_TRANSLATIONS = {
        "Upload failed": "アップロードに失敗しました",
        "PDF conversion failed": "PDF変換に失敗しました",
        "Dialogue generation failed": "対話生成に失敗しました",
        "Audio generation failed": "音声生成に失敗しました",
        "Video creation failed": "動画作成に失敗しました",
        "VOICEVOX connection failed": "VOICEVOXへの接続に失敗しました",
        "File not found": "ファイルが見つかりません",
        "Invalid file format": "無効なファイル形式です",
        "Processing timeout": "処理がタイムアウトしました",
        "Insufficient disk space": "ディスク容量が不足しています",
        "Network connection error": "ネットワーク接続エラーです"
    }
    
    # 進捗メッセージの翻訳パターン（既に日本語のメッセージはそのまま返す）
    PROGRESS_MESSAGE_PATTERNS = [
        # 英語パターンから日本語への変換
        (r"Converting PDF to slides\.\.\.", "PDFをスライドに変換中..."),
        (r"Generating dialogue for slide (\d+)/(\d+)\.\.\.", r"スライド\1/\2の対話を生成中..."),
        (r"Regenerating dialogue for slide (\d+)\.\.\.", r"スライド\1の対話を再生成中..."),
        (r"Generating dialogue script\.\.\.", "対話スクリプトを生成中..."),
        (r"Generating audio\.\.\.", "音声を生成中..."),
        (r"Creating video\.\.\.", "動画を作成中..."),
        (r"Processing\.\.\.", "処理中..."),
        (r"Uploading file\.\.\.", "ファイルをアップロード中..."),
        (r"Preparing slides\.\.\.", "スライドを準備中..."),
        (r"Finalizing\.\.\.", "最終処理中..."),
    ]
    
    def __init__(self):
        """初期化"""
        pass
    
    def get_status_message(self, status: str, locale: str = "ja") -> str:
        """
        ステータスの翻訳を取得
        
        Args:
            status: 英語ステータス
            locale: ロケール（現在は'ja'のみサポート）
            
        Returns:
            翻訳されたステータス、見つからない場合は元のステータス
        """
        if locale == "ja":
            return self.STATUS_TRANSLATIONS.get(status, status)
        return status
    
    def get_progress_message(self, message: str, locale: str = "ja") -> str:
        """
        進捗メッセージの翻訳を取得
        
        Args:
            message: 元のメッセージ
            locale: ロケール（現在は'ja'のみサポート）
            
        Returns:
            翻訳されたメッセージ、パターンが見つからない場合は元のメッセージ
        """
        if locale != "ja" or not message:
            return message
            
        # 既に日本語の場合はそのまま返す
        if self._is_japanese_message(message):
            return message
            
        # パターンマッチングで翻訳
        for pattern, translation in self.PROGRESS_MESSAGE_PATTERNS:
            match = re.match(pattern, message)
            if match:
                if match.groups():
                    # グループがある場合は置換
                    return re.sub(pattern, translation, message)
                else:
                    # グループがない場合は直接置換
                    return translation
        
        return message
    
    def get_error_message(self, error: str, locale: str = "ja") -> str:
        """
        エラーメッセージの翻訳を取得
        
        Args:
            error: 英語エラーメッセージ
            locale: ロケール（現在は'ja'のみサポート）
            
        Returns:
            翻訳されたエラーメッセージ、見つからない場合は元のエラーメッセージ
        """
        if locale != "ja" or not error:
            return error
            
        # 既に日本語の場合はそのまま返す
        if self._is_japanese_message(error):
            return error
            
        # 完全一致での翻訳
        translated = self.ERROR_TRANSLATIONS.get(error)
        if translated:
            return translated
            
        # 部分一致での翻訳
        for english_error, japanese_error in self.ERROR_TRANSLATIONS.items():
            if english_error.lower() in error.lower():
                return japanese_error
                
        return error
    
    def _is_japanese_message(self, message: str) -> bool:
        """
        メッセージが日本語かどうかを判定
        
        Args:
            message: 判定するメッセージ
            
        Returns:
            日本語の場合True
        """
        if not message:
            return False
            
        # ひらがな、カタカナ、漢字が含まれている場合は日本語と判定
        japanese_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', message)
        return len(japanese_chars) > 0
    
    def add_status_translation(self, status: str, translation: str) -> None:
        """
        新しいステータス翻訳を追加
        
        Args:
            status: 英語ステータス
            translation: 日本語翻訳
        """
        self.STATUS_TRANSLATIONS[status] = translation
    
    def add_error_translation(self, error: str, translation: str) -> None:
        """
        新しいエラーメッセージ翻訳を追加
        
        Args:
            error: 英語エラーメッセージ
            translation: 日本語翻訳
        """
        self.ERROR_TRANSLATIONS[error] = translation


# グローバルインスタンス
localization_service = LocalizationService()