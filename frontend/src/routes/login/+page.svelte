<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";

  let password = "";
  let isLoading = false;
  let errorMessage = "";
  let authEnabled = false;

  onMount(async () => {
    // 認証状態をチェック
    await checkAuthStatus();
  });

  async function checkAuthStatus() {
    try {
      const response = await fetch("/api/auth/status");
      if (response.ok) {
        const data = await response.json();
        authEnabled = data.auth_enabled;

        // 認証が無効、または既に認証済みの場合はメインページにリダイレクト
        if (!authEnabled || data.authenticated) {
          goto("/");
          return;
        }
      }
    } catch (error) {
      console.error("認証状態の確認に失敗:", error);
    }
  }

  async function handleLogin() {
    if (!password.trim()) {
      errorMessage = "パスワードを入力してください";
      return;
    }

    isLoading = true;
    errorMessage = "";

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // トークンをローカルストレージに保存
        if (data.token) {
          localStorage.setItem("auth_token", data.token);
        }

        // メインページにリダイレクト
        goto("/");
      } else {
        errorMessage = data.detail || "ログインに失敗しました";
      }
    } catch (error) {
      console.error("ログインエラー:", error);
      errorMessage = "ログインに失敗しました";
    } finally {
      isLoading = false;
    }
  }

  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === "Enter") {
      handleLogin();
    }
  }
</script>

<svelte:head>
  <title>ログイン - longan</title>
</svelte:head>

<main class="login-container">
  <div class="login-card">
    <div class="login-header">
      <img src="/favicon.png" alt="longan" class="logo" />
      <h1>longan</h1>
      <p>PDFスライドからVOICEVOXキャラクターによる対話動画を自動生成</p>
    </div>

    <div class="login-form">
      <h2>ログイン</h2>

      {#if errorMessage}
        <div class="error-message">
          ❌ {errorMessage}
        </div>
      {/if}

      <div class="form-group">
        <label for="password">パスワード</label>
        <input
          type="password"
          id="password"
          bind:value={password}
          on:keypress={handleKeyPress}
          placeholder="パスワードを入力してください"
          disabled={isLoading}
        />
      </div>

      <button
        class="login-btn"
        on:click={handleLogin}
        disabled={isLoading || !password.trim()}
      >
        {isLoading ? "ログイン中..." : "ログイン"}
      </button>
    </div>
  </div>
</main>

<style>
  .login-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
  }

  .login-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    padding: 40px;
    width: 100%;
    max-width: 400px;
  }

  .login-header {
    text-align: center;
    margin-bottom: 30px;
  }

  .logo {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
  }

  .login-header h1 {
    margin: 0 0 8px 0;
    color: #333;
    font-size: 2rem;
  }

  .login-header p {
    margin: 0;
    color: #666;
    font-size: 0.9rem;
    line-height: 1.4;
  }

  .login-form h2 {
    margin: 0 0 20px 0;
    color: #333;
    text-align: center;
  }

  .form-group {
    margin-bottom: 20px;
  }

  .form-group label {
    display: block;
    margin-bottom: 8px;
    color: #333;
    font-weight: 500;
  }

  .form-group input {
    width: 100%;
    padding: 12px;
    border: 2px solid #e1e5e9;
    border-radius: 8px;
    font-size: 16px;
    transition: border-color 0.2s;
    box-sizing: border-box;
  }

  .form-group input:focus {
    outline: none;
    border-color: #667eea;
  }

  .form-group input:disabled {
    background-color: #f5f5f5;
    cursor: not-allowed;
  }

  .login-btn {
    width: 100%;
    padding: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .login-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .login-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .error-message {
    background-color: #fee;
    color: #c33;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 20px;
    text-align: center;
    border: 1px solid #fcc;
  }
</style>
