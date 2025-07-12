"""
LLMプロバイダーの抽象化層
OpenAI, Claude, Gemini, AWS Bedrockをサポート
"""
from typing import Protocol, Dict, List, Optional, Any
from abc import ABC, abstractmethod
import os
import json
from dataclasses import dataclass
from enum import Enum

class LLMProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    GEMINI = "gemini"
    BEDROCK = "bedrock"

@dataclass
class LLMConfig:
    provider: LLMProvider
    api_key: Optional[str] = None
    region: Optional[str] = None  # AWS Bedrock用
    model_id: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000

class LLMInterface(ABC):
    """LLMプロバイダーの共通インターフェース"""
    
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> str:
        """テキスト生成"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """プロバイダーが利用可能かチェック"""
        pass

class OpenAIAdapter(LLMInterface):
    """OpenAI APIアダプター"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=config.api_key or os.getenv("OPENAI_API_KEY"))
            self.model = config.model_id or "gpt-4o"
        except ImportError:
            self.client = None
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> str:
        if not self.client:
            raise Exception("OpenAI client not initialized")
        
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
    
    def is_available(self) -> bool:
        return self.client is not None and (self.config.api_key or os.getenv("OPENAI_API_KEY"))

class ClaudeAdapter(LLMInterface):
    """Claude (Anthropic) APIアダプター"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        try:
            import anthropic
            self.client = anthropic.Anthropic(
                api_key=config.api_key or os.getenv("ANTHROPIC_API_KEY")
            )
            self.model = config.model_id or "claude-3-opus-20240229"
        except ImportError:
            self.client = None
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> str:
        if not self.client:
            raise Exception("Claude client not initialized")
        
        # Claudeは system と user を組み合わせる
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # response_formatがJSONの場合、プロンプトに指示を追加
        if response_format and response_format.get("type") == "json_object":
            combined_prompt += "\n\nPlease respond with valid JSON only."
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "user", "content": combined_prompt}
            ]
        )
        
        return message.content[0].text
    
    def is_available(self) -> bool:
        return self.client is not None and (self.config.api_key or os.getenv("ANTHROPIC_API_KEY"))

class GeminiAdapter(LLMInterface):
    """Google Gemini APIアダプター"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        try:
            import google.generativeai as genai
            api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(
                    config.model_id or "gemini-pro"
                )
            else:
                self.model = None
        except ImportError:
            self.model = None
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> str:
        if not self.model:
            raise Exception("Gemini model not initialized")
        
        # Geminiは system と user を組み合わせる
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # response_formatがJSONの場合、プロンプトに指示を追加
        if response_format and response_format.get("type") == "json_object":
            combined_prompt += "\n\nPlease respond with valid JSON only."
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        response = self.model.generate_content(
            combined_prompt,
            generation_config=generation_config
        )
        
        return response.text
    
    def is_available(self) -> bool:
        return self.model is not None

class BedrockAdapter(LLMInterface):
    """AWS Bedrock APIアダプター"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        try:
            import boto3
            # AWS認証情報を使用
            # AWSの認証情報を設定
            # api_keyフィールドには "ACCESS_KEY_ID|SECRET_ACCESS_KEY" の形式で保存される
            if config.api_key and '|' in config.api_key:
                access_key_id, secret_access_key = config.api_key.split('|', 1)
            else:
                access_key_id = config.api_key or os.getenv("AWS_ACCESS_KEY_ID")
                secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=config.region or os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1"),
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key
            )
            self.model_id = config.model_id or "anthropic.claude-3-opus-20240229-v1:0"
        except ImportError:
            self.client = None
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        response_format: Optional[Dict] = None
    ) -> str:
        if not self.client:
            raise Exception("Bedrock client not initialized")
        
        # Bedrockのモデルに応じてリクエストを構築
        if "claude" in self.model_id:
            # Claude on Bedrock
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            if response_format and response_format.get("type") == "json_object":
                combined_prompt += "\n\nPlease respond with valid JSON only."
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": combined_prompt}
                ]
            }
        else:
            # その他のモデル（Llama, Mistral等）
            combined_prompt = f"{system_prompt}\n\n{user_prompt}"
            if response_format and response_format.get("type") == "json_object":
                combined_prompt += "\n\nPlease respond with valid JSON only."
            
            request_body = {
                "prompt": combined_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        # モデルに応じてレスポンスを解析
        if "claude" in self.model_id:
            return response_body['content'][0]['text']
        else:
            return response_body.get('completion', response_body.get('generation', ''))
    
    def is_available(self) -> bool:
        return self.client is not None

class LLMFactory:
    """LLMプロバイダーのファクトリー"""
    
    @staticmethod
    def create(config: LLMConfig) -> LLMInterface:
        """設定に基づいてLLMインスタンスを作成"""
        if config.provider == LLMProvider.OPENAI:
            return OpenAIAdapter(config)
        elif config.provider == LLMProvider.CLAUDE:
            return ClaudeAdapter(config)
        elif config.provider == LLMProvider.GEMINI:
            return GeminiAdapter(config)
        elif config.provider == LLMProvider.BEDROCK:
            return BedrockAdapter(config)
        else:
            raise ValueError(f"Unknown provider: {config.provider}")
    
    @staticmethod
    def get_available_providers() -> List[Dict[str, Any]]:
        """利用可能なプロバイダーのリストを返す"""
        providers = []
        
        # OpenAI
        try:
            config = LLMConfig(provider=LLMProvider.OPENAI)
            adapter = OpenAIAdapter(config)
            providers.append({
                "id": LLMProvider.OPENAI,
                "name": "OpenAI",
                "models": ["gpt-4o", "gpt-4", "gpt-3.5-turbo"],
                "requires_key": True,
                "available": adapter.is_available()
            })
        except:
            pass
        
        # Claude
        try:
            config = LLMConfig(provider=LLMProvider.CLAUDE)
            adapter = ClaudeAdapter(config)
            providers.append({
                "id": LLMProvider.CLAUDE,
                "name": "Claude (Anthropic)",
                "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
                "requires_key": True,
                "available": adapter.is_available()
            })
        except:
            pass
        
        # Gemini
        try:
            config = LLMConfig(provider=LLMProvider.GEMINI)
            adapter = GeminiAdapter(config)
            providers.append({
                "id": LLMProvider.GEMINI,
                "name": "Google Gemini",
                "models": ["gemini-pro", "gemini-pro-vision"],
                "requires_key": True,
                "available": adapter.is_available()
            })
        except:
            pass
        
        # Bedrock
        try:
            config = LLMConfig(provider=LLMProvider.BEDROCK)
            adapter = BedrockAdapter(config)
            providers.append({
                "id": LLMProvider.BEDROCK,
                "name": "AWS Bedrock",
                "models": [
                    "anthropic.claude-3-opus-20240229-v1:0",
                    "anthropic.claude-3-sonnet-20240229-v1:0",
                    "meta.llama3-70b-instruct-v1:0"
                ],
                "requires_key": True,
                "requires_region": True,
                "available": adapter.is_available()
            })
        except:
            pass
        
        return providers