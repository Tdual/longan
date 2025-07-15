"""
認証機能
"""

import os
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

class AuthManager:
    """認証管理クラス"""
    
    def __init__(self):
        self.login_password = os.getenv("LOGIN_PASSWORD", "").strip()
        self.auth_enabled = bool(self.login_password)
    
    def is_auth_enabled(self) -> bool:
        """認証が有効かどうかを返す"""
        return self.auth_enabled
    
    def verify_password(self, password: str) -> bool:
        """パスワードを検証"""
        if not self.auth_enabled:
            return True  # 認証が無効の場合は常にTrue
        return password == self.login_password
    
    def check_auth(self, request: Request) -> bool:
        """リクエストの認証状態をチェック"""
        if not self.auth_enabled:
            return True  # 認証が無効の場合は常にTrue
        
        # Authorizationヘッダーをチェック
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False
        
        # Bearer トークン形式をチェック
        if not auth_header.startswith("Bearer "):
            return False
        
        token = auth_header[7:]  # "Bearer " を除去
        return self.verify_password(token)

# グローバルインスタンス
auth_manager = AuthManager()

def require_auth(request: Request):
    """認証が必要なエンドポイント用のデコレータ"""
    if not auth_manager.check_auth(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )