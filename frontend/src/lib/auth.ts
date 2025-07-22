/**
 * 認証関連のユーティリティ
 */

// 認証トークンを取得
export function getAuthToken(): string | null {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('auth_token');
  }
  return null;
}

// 認証トークンを設定
export function setAuthToken(token: string): void {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('auth_token', token);
  }
}

// 認証トークンを削除
export function removeAuthToken(): void {
  if (typeof localStorage !== 'undefined') {
    localStorage.removeItem('auth_token');
  }
}

// 認証ヘッダーを取得
export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (token) {
    return {
      'Authorization': `Bearer ${token}`
    };
  }
  return {};
}

// fetch関数のラッパー（認証ヘッダーを自動追加）
export async function authenticatedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const authHeaders = getAuthHeaders();
  
  const mergedOptions: RequestInit = {
    ...options,
    headers: {
      ...authHeaders,
      ...options.headers,
    },
  };
  
  return fetch(url, mergedOptions);
}