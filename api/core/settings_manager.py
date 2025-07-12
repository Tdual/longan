"""
設定管理システム
LLMプロバイダーの設定とAPIキーを管理
"""
import os
from pathlib import Path
from typing import Dict, Optional, Any
from dotenv import load_dotenv, set_key

class SettingsManager:
    """設定とAPIキーの管理"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        # プロジェクトルートディレクトリを探す
        # Dockerコンテナ内では/appがルート、ローカルではdocker-compose.ymlを探す
        if Path("/app").exists() and Path("/app/api").exists():
            # Dockerコンテナ内
            self.project_root = Path("/app")
        else:
            # ローカル環境
            self.project_root = Path.cwd()
            while self.project_root != self.project_root.parent:
                if (self.project_root / "docker-compose.yml").exists():
                    break
                self.project_root = self.project_root.parent
        
        self.env_file = self.project_root / ".env"
        self.env_example_file = self.project_root / ".env.example"
        
        # .envファイルが存在しない場合は.env.exampleをコピー
        if not self.env_file.exists():
            if self.env_example_file.exists():
                import shutil
                shutil.copy2(self.env_example_file, self.env_file)
                print(f".env.exampleを.envにコピーしました: {self.env_file}")
            else:
                # .env.exampleも存在しない場合は空のファイルを作成
                self.env_file.touch()
                print(f"空の.envファイルを作成しました: {self.env_file}")
        
        # .envファイルをロード
        load_dotenv(self.env_file)
    
    def _get_env_key_name(self, provider: str) -> str:
        """プロバイダーに対応する環境変数名を取得"""
        env_keys = {
            "openai": "OPENAI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY",
            "bedrock": "AWS_BEDROCK_CREDENTIALS"  # ACCESS_KEY|SECRET_KEY形式
        }
        return env_keys.get(provider, f"{provider.upper()}_API_KEY")
    
    def get_settings(self) -> Dict[str, Any]:
        """設定を取得"""
        # すべて環境変数から読み込む
        settings = {
            "default_provider": os.getenv("USE_MODEL", "openai"),
            "default_model": {
                "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
                "claude": os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229"),
                "gemini": os.getenv("GEMINI_MODEL", "gemini-pro"),
                "bedrock": os.getenv("BEDROCK_MODEL", "anthropic.claude-3-opus-20240229-v1:0")
            },
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4000"))
        }
        
        # AWS Bedrockのリージョン設定
        if os.getenv("AWS_DEFAULT_REGION"):
            settings["bedrock_region"] = os.getenv("AWS_DEFAULT_REGION")
        
        return settings
    
    def save_settings(self, settings: Dict[str, Any]):
        """設定を保存"""
        # すべて.envファイルに保存
        if "default_provider" in settings:
            set_key(self.env_file, "USE_MODEL", settings["default_provider"])
        
        if "default_model" in settings:
            for provider, model in settings["default_model"].items():
                if provider == "openai":
                    set_key(self.env_file, "OPENAI_MODEL", model)
                elif provider == "claude":
                    set_key(self.env_file, "CLAUDE_MODEL", model)
                elif provider == "gemini":
                    set_key(self.env_file, "GEMINI_MODEL", model)
                elif provider == "bedrock":
                    set_key(self.env_file, "BEDROCK_MODEL", model)
        
        if "temperature" in settings:
            set_key(self.env_file, "LLM_TEMPERATURE", str(settings["temperature"]))
        if "max_tokens" in settings:
            set_key(self.env_file, "LLM_MAX_TOKENS", str(settings["max_tokens"]))
        if "bedrock_region" in settings:
            set_key(self.env_file, "AWS_DEFAULT_REGION", settings["bedrock_region"])
        
        # 環境変数を再読み込み
        load_dotenv(self.env_file, override=True)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """APIキーを取得"""
        env_key = self._get_env_key_name(provider)
        
        # .envファイルから読み込む
        value = os.getenv(env_key)
        
        # Bedrockの場合は特殊処理（古い形式との互換性）
        if provider == "bedrock" and not value:
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            if access_key and secret_key:
                return f"{access_key}|{secret_key}"
        
        return value
    
    def save_api_key(self, provider: str, api_key: str):
        """APIキーを保存"""
        env_key = self._get_env_key_name(provider)
        
        # .envファイルに保存
        set_key(self.env_file, env_key, api_key)
        
        # Bedrockの場合は特殊処理（ACCESS_KEY|SECRET_KEY形式を分割）
        if provider == "bedrock" and "|" in api_key:
            access_key, secret_key = api_key.split("|", 1)
            set_key(self.env_file, "AWS_ACCESS_KEY_ID", access_key)
            set_key(self.env_file, "AWS_SECRET_ACCESS_KEY", secret_key)
        
        # 環境変数を再読み込み
        load_dotenv(self.env_file, override=True)
    
    def delete_api_key(self, provider: str):
        """APIキーを削除"""
        env_key = self._get_env_key_name(provider)
        
        if self.env_file.exists():
            # .envファイルから削除（空文字列を設定）
            set_key(self.env_file, env_key, "")
            
            # Bedrockの場合は関連キーも削除
            if provider == "bedrock":
                set_key(self.env_file, "AWS_ACCESS_KEY_ID", "")
                set_key(self.env_file, "AWS_SECRET_ACCESS_KEY", "")
            
            # 環境変数を再読み込み
            load_dotenv(self.env_file, override=True)
    
    def get_provider_status(self, provider: str) -> Dict[str, Any]:
        """プロバイダーの設定状態を取得"""
        api_key = self.get_api_key(provider)
        
        if api_key:
            # APIキーの一部をマスク
            if provider == "bedrock" and "|" in api_key:
                # Bedrockの場合
                parts = api_key.split("|")
                masked = f"{parts[0][:10]}..." if len(parts[0]) > 10 else "***"
            else:
                masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
            
            return {
                "configured": True,
                "masked_key": masked,
                "key_source": "environment"  # すべて.envファイルから
            }
        else:
            return {
                "configured": False
            }
    
    def get_all_keys_status(self) -> Dict[str, Dict[str, Any]]:
        """すべてのAPIキーの状態を取得（キー自体は返さない）"""
        providers = ["openai", "claude", "gemini", "bedrock"]
        status = {}
        
        for provider in providers:
            status[provider] = self.get_provider_status(provider)
        
        # AWS Bedrockの場合は追加情報
        if status["bedrock"]["configured"]:
            status["bedrock"]["region"] = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
        
        return status
    
    async def test_api_key(self, provider: str, api_key: Optional[str] = None, region: Optional[str] = None) -> Dict[str, Any]:
        """APIキーの有効性をテスト"""
        from .llm_provider import LLMFactory, LLMConfig, LLMProvider
        
        try:
            # テスト用の設定を作成
            config = LLMConfig(
                provider=LLMProvider(provider),
                api_key=api_key or self.get_api_key(provider),
                region=region if provider == "bedrock" else None
            )
            
            # アダプターを作成
            llm = LLMFactory.create(config)
            
            # 簡単なテストプロンプトを実行
            if llm.is_available():
                try:
                    result = await llm.generate(
                        system_prompt="You are a helpful assistant.",
                        user_prompt="Say 'Hello' in one word.",
                        max_tokens=10
                    )
                    return {
                        "valid": True,
                        "message": "APIキーは有効です",
                        "test_response": result[:50]
                    }
                except Exception as e:
                    error_message = str(e)
                    print(f"APIキーテストエラー: {error_message}")  # デバッグ用
                    
                    # OpenAI特有のエラーメッセージ
                    if "Invalid API key" in error_message or "Incorrect API key" in error_message or "invalid_api_key" in error_message:
                        return {
                            "valid": False,
                            "message": "無効なAPIキーです"
                        }
                    elif "quota" in error_message.lower() or "insufficient_quota" in error_message:
                        return {
                            "valid": False,
                            "message": "APIクォータを超過しています"
                        }
                    else:
                        return {
                            "valid": False,
                            "message": f"APIキーのテストに失敗しました: {error_message}"
                        }
            else:
                return {
                    "valid": False,
                    "message": "プロバイダーが利用できません"
                }
        except Exception as e:
            return {
                "valid": False,
                "message": f"APIキーのテスト中にエラーが発生しました: {str(e)}"
            }