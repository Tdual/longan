<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	interface Provider {
		id: string;
		name: string;
		models: string[];
		configured: boolean;
		masked_key?: string;
		key_source?: string;
		requires_region?: boolean;
		region?: string;
	}

	interface ProviderSettings {
		providers: Provider[];
		default_provider: string;
		default_models: { [key: string]: string };
		temperature: number;
		max_tokens: number;
	}

	let settings: ProviderSettings | null = null;
	let isLoading = true;
	let isSaving = false;
	let testingProvider: string | null = null;
	let testResult: { [key: string]: { valid: boolean; message: string } } = {};
	let selectedProviderId: string | null = null; // 選択されたプロバイダーのID

	// 新規API キー入力用
	let newApiKeys: { [key: string]: string } = {};
	let newSecretKeys: { [key: string]: string } = {}; // AWS Bedrock用
	let newRegions: { [key: string]: string } = {};
	let selectedModels: { [key: string]: string } = {};

	onMount(async () => {
		await loadSettings();
	});

	async function loadSettings() {
		isLoading = true;
		try {
			const response = await fetch('/api/settings/providers');
			if (response.ok) {
				settings = await response.json();
				// 既存の設定を反映
				if (settings) {
					// デフォルトプロバイダーを選択状態にする
					selectedProviderId = settings.default_provider;
					
					settings.providers.forEach(provider => {
						if (settings!.default_models && settings!.default_models[provider.id]) {
							selectedModels[provider.id] = settings!.default_models[provider.id];
						} else if (provider.models.length > 0) {
							selectedModels[provider.id] = provider.models[0];
						}
						if (provider.region) {
							newRegions[provider.id] = provider.region;
						}
					});
				}
			} else {
				console.error('設定の読み込みに失敗しました');
			}
		} catch (error) {
			console.error('設定の読み込み中にエラーが発生しました:', error);
		} finally {
			isLoading = false;
		}
	}

	async function testApiKey(providerId: string) {
		testingProvider = providerId;
		testResult[providerId] = { valid: false, message: 'テスト中...' };

		try {
			let apiKey = newApiKeys[providerId];
			// AWS Bedrockの場合は特別な処理
			if (providerId === 'bedrock' && newSecretKeys[providerId]) {
				apiKey = `${apiKey}|${newSecretKeys[providerId]}`;
			}

			const response = await fetch('/api/settings/test-key', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					provider: providerId,
					api_key: apiKey || undefined,
					region: newRegions[providerId] || undefined
				})
			});

			if (!response.ok) {
				console.error('APIキーテスト失敗:', response.status, response.statusText);
				const errorText = await response.text();
				console.error('エラー内容:', errorText);
				testResult[providerId] = { valid: false, message: `エラー: ${response.status}` };
			} else {
				const result = await response.json();
				console.log('APIキーテスト結果:', result);
				testResult[providerId] = result;
			}
		} catch (error) {
			console.error('APIキーテストエラー:', error);
			testResult[providerId] = { valid: false, message: 'テストに失敗しました' };
		} finally {
			testingProvider = null;
		}
	}

	async function saveProviderConfig(providerId: string) {
		if (!newApiKeys[providerId]) {
			alert('APIキーを入力してください');
			return;
		}

		// AWS Bedrockの場合はシークレットキーも必須
		if (providerId === 'bedrock' && !newSecretKeys[providerId]) {
			alert('シークレットアクセスキーも入力してください');
			return;
		}

		isSaving = true;
		try {
			let apiKey = newApiKeys[providerId];
			// AWS Bedrockの場合は特別な処理
			if (providerId === 'bedrock' && newSecretKeys[providerId]) {
				apiKey = `${apiKey}|${newSecretKeys[providerId]}`;
			}

			const response = await fetch('/api/settings/provider', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					provider: providerId,
					api_key: apiKey,
					region: newRegions[providerId] || undefined,
					model: selectedModels[providerId] || undefined
				})
			});

			if (response.ok) {
				// 入力フィールドをクリア
				newApiKeys[providerId] = '';
				newSecretKeys[providerId] = '';
				// 設定を再読み込み
				await loadSettings();
				alert('設定を保存しました');
			} else {
				alert('設定の保存に失敗しました');
			}
		} catch (error) {
			console.error('設定の保存中にエラーが発生しました:', error);
			alert('設定の保存中にエラーが発生しました');
		} finally {
			isSaving = false;
		}
	}

	async function deleteProviderConfig(providerId: string) {
		if (!confirm('このプロバイダーの設定を削除しますか？')) {
			return;
		}

		try {
			const response = await fetch(`/api/settings/provider/${providerId}`, {
				method: 'DELETE'
			});

			if (response.ok) {
				await loadSettings();
				alert('設定を削除しました');
			} else {
				alert('設定の削除に失敗しました');
			}
		} catch (error) {
			console.error('設定の削除中にエラーが発生しました:', error);
			alert('設定の削除中にエラーが発生しました');
		}
	}

	async function updateDefaultProvider(providerId: string) {
		selectedProviderId = providerId;
		try {
			const response = await fetch('/api/settings', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					default_provider: providerId
				})
			});

			if (response.ok) {
				await loadSettings();
			} else {
				alert('デフォルトプロバイダーの更新に失敗しました');
			}
		} catch (error) {
			console.error('デフォルトプロバイダーの更新中にエラーが発生しました:', error);
		}
	}

	async function updateGeneralSettings() {
		if (!settings) return;

		try {
			const response = await fetch('/api/settings', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					temperature: settings.temperature,
					max_tokens: settings.max_tokens,
					default_model: selectedModels
				})
			});

			if (response.ok) {
				alert('設定を更新しました');
			} else {
				alert('設定の更新に失敗しました');
			}
		} catch (error) {
			console.error('設定の更新中にエラーが発生しました:', error);
			alert('設定の更新中にエラーが発生しました');
		}
	}
</script>

<div class="container">
	<div class="header">
		<button
			on:click={() => goto('/')}
			class="back-button"
		>
			← 戻る
		</button>
		<h1>⚙️ LLMプロバイダー設定</h1>
		<div style="width: 100px;"></div>
	</div>

	{#if isLoading}
		<div class="loading-container">
			<div class="spinner"></div>
		</div>
	{:else if settings}
		<!-- プロバイダー一覧 -->
		<div class="providers-container">
			{#each settings.providers as provider}
				<div class="provider-card">
					<div class="provider-header">
						<label class="provider-radio">
							<input
								type="radio"
								name="default_provider"
								value={provider.id}
								checked={settings.default_provider === provider.id}
								on:change={() => updateDefaultProvider(provider.id)}
							/>
							<div class="provider-info">
								<h2>{provider.name}</h2>
								<div class="provider-status">
									{#if provider.configured}
										<span class="status-badge status-configured">✓ 設定済み</span>
										{#if provider.key_source === 'environment'}
											<span class="text-gray-500 text-sm">(環境変数)</span>
										{/if}
										{#if provider.masked_key}
											<span class="text-gray-500 text-sm">キー: {provider.masked_key}</span>
										{/if}
									{:else}
										<span class="status-badge status-not-configured">未設定</span>
									{/if}
								</div>
							</div>
						</label>
						{#if provider.configured && selectedProviderId === provider.id}
							<button
								on:click={() => deleteProviderConfig(provider.id)}
								class="delete-button"
							>
								削除
							</button>
						{/if}
					</div>

					{#if selectedProviderId === provider.id}
						<div class="provider-details">
							<!-- モデル選択 -->
							<div class="form-group">
								<label>使用するモデル</label>
								<select bind:value={selectedModels[provider.id]}>
									{#each provider.models as model}
										<option value={model}>{model}</option>
									{/each}
								</select>
							</div>

							<!-- API キー入力 -->
							<div class="form-group">
								<label>
									{provider.id === 'bedrock' ? 'AWS アクセスキーID' : 'APIキー'}
									{#if provider.configured}
										<span style="font-weight: normal; color: #6b7280; font-size: 0.75rem;">(新しいキーを入力して更新)</span>
									{/if}
								</label>
								<input
									type="password"
									bind:value={newApiKeys[provider.id]}
									placeholder={provider.configured ? '新しいAPIキーを入力' : 'APIキーを入力'}
								/>
							</div>

							{#if provider.id === 'bedrock'}
								<div class="form-group">
									<label>
										AWS シークレットアクセスキー
										{#if provider.configured}
											<span style="font-weight: normal; color: #6b7280; font-size: 0.75rem;">(新しいキーを入力して更新)</span>
										{/if}
									</label>
									<input
										type="password"
										bind:value={newSecretKeys[provider.id]}
										placeholder={provider.configured ? '新しいシークレットキーを入力' : 'シークレットアクセスキーを入力'}
									/>
								</div>
							{/if}

							{#if provider.requires_region}
								<div class="form-group">
									<label>リージョン</label>
									<input
										type="text"
										bind:value={newRegions[provider.id]}
										placeholder="例: ap-northeast-1"
									/>
								</div>
							{/if}

							<div class="button-group">
								<button
									on:click={() => testApiKey(provider.id)}
									disabled={(!newApiKeys[provider.id] && !provider.configured) || testingProvider === provider.id || (provider.id === 'bedrock' && !newSecretKeys[provider.id] && !provider.configured)}
									class="test-button"
								>
									{testingProvider === provider.id ? 'テスト中...' : (provider.configured && !newApiKeys[provider.id] ? '既存のキーをテスト' : 'テスト')}
								</button>
								<button
									on:click={() => saveProviderConfig(provider.id)}
									disabled={!newApiKeys[provider.id] || isSaving || (provider.id === 'bedrock' && !newSecretKeys[provider.id])}
									class="save-button"
								>
									{isSaving ? '保存中...' : '保存'}
								</button>
							</div>

							{#if testResult[provider.id]}
								<div
									class="test-result {testResult[provider.id].valid ? 'valid' : 'invalid'}"
								>
									{testResult[provider.id].message}
								</div>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>

		<!-- 全般設定 -->
		<div class="general-settings">
			<h2>全般設定</h2>
			
			<div class="form-group">
				<label>Temperature (0.0 - 2.0)</label>
				<input
					type="number"
					bind:value={settings.temperature}
					min="0"
					max="2"
					step="0.1"
				/>
				<p class="help-text">
					値が高いほど創造的な回答になります
				</p>
			</div>

			<div class="form-group">
				<label>最大トークン数</label>
				<input
					type="number"
					bind:value={settings.max_tokens}
					min="100"
					max="32000"
					step="100"
				/>
				<p class="help-text">
					生成される回答の最大長
				</p>
			</div>

			<button
				on:click={updateGeneralSettings}
				class="update-button"
			>
				全般設定を更新
			</button>
		</div>
	{/if}
</div>

<style>
	.container {
		max-width: 1000px;
		margin: 0 auto;
		padding: 2rem;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	.header {
		margin-bottom: 3rem;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.back-button {
		background-color: #6b7280;
		color: white;
		padding: 0.5rem 1rem;
		border-radius: 8px;
		text-decoration: none;
		font-size: 0.9rem;
		transition: background-color 0.3s ease;
		border: none;
		cursor: pointer;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
	}

	.back-button:hover {
		background-color: #4b5563;
	}

	h1 {
		font-size: 2.5rem;
		color: #2563eb;
		margin: 0;
		text-align: center;
		flex: 1;
	}

	.loading-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 400px;
	}

	.spinner {
		width: 50px;
		height: 50px;
		border: 3px solid #f3f3f3;
		border-top: 3px solid #2563eb;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		0% { transform: rotate(0deg); }
		100% { transform: rotate(360deg); }
	}

	.providers-container {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.provider-card {
		background-color: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		transition: box-shadow 0.3s ease;
	}

	.provider-card:hover {
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	.provider-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0;
		padding-bottom: 1rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.provider-radio {
		display: flex;
		align-items: center;
		gap: 1rem;
		cursor: pointer;
		flex: 1;
	}

	.provider-radio input[type="radio"] {
		width: 1.25rem;
		height: 1.25rem;
		accent-color: #2563eb;
		cursor: pointer;
	}

	.provider-info {
		flex: 1;
	}

	.provider-info h2 {
		font-size: 1.5rem;
		color: #1f2937;
		margin: 0 0 0.5rem 0;
	}

	.provider-status {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		margin-top: 0.25rem;
	}

	.status-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.75rem;
		border-radius: 9999px;
		font-weight: 500;
	}

	.status-configured {
		background-color: #d1fae5;
		color: #065f46;
	}

	.status-not-configured {
		background-color: #fed7aa;
		color: #9a3412;
	}

	.provider-details {
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		animation: slideDown 0.3s ease-out;
	}

	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.delete-button {
		background-color: transparent;
		color: #dc2626;
		border: 1px solid #dc2626;
		padding: 0.25rem 0.75rem;
		border-radius: 6px;
		font-size: 0.875rem;
		cursor: pointer;
		transition: all 0.3s ease;
	}

	.delete-button:hover {
		background-color: #dc2626;
		color: white;
	}

	.form-group {
		margin-bottom: 1.5rem;
	}

	.form-group label {
		display: block;
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
		margin-bottom: 0.5rem;
	}

	.form-group select,
	.form-group input[type="text"],
	.form-group input[type="password"],
	.form-group input[type="number"] {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 1rem;
		transition: border-color 0.3s ease;
		background-color: white;
	}

	.form-group select:focus,
	.form-group input:focus {
		outline: none;
		border-color: #2563eb;
		box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
	}

	.form-group .help-text {
		font-size: 0.75rem;
		color: #6b7280;
		margin-top: 0.25rem;
	}

	.button-group {
		display: flex;
		gap: 0.75rem;
		margin-top: 1rem;
	}

	.test-button {
		background-color: #6b7280;
		color: white;
		border: none;
		padding: 0.75rem 1.5rem;
		border-radius: 6px;
		font-size: 0.875rem;
		cursor: pointer;
		transition: background-color 0.3s ease;
	}

	.test-button:hover:not(:disabled) {
		background-color: #4b5563;
	}

	.save-button {
		background-color: #2563eb;
		color: white;
		border: none;
		padding: 0.75rem 1.5rem;
		border-radius: 6px;
		font-size: 0.875rem;
		cursor: pointer;
		transition: background-color 0.3s ease;
	}

	.save-button:hover:not(:disabled) {
		background-color: #1d4ed8;
	}

	.test-button:disabled,
	.save-button:disabled {
		background-color: #e5e7eb;
		color: #9ca3af;
		cursor: not-allowed;
	}

	.test-result {
		margin-top: 1rem;
		padding: 1rem;
		border-radius: 6px;
		font-size: 0.875rem;
	}

	.test-result.valid {
		background-color: #d1fae5;
		color: #065f46;
		border: 1px solid #10b981;
	}

	.test-result.invalid {
		background-color: #fee2e2;
		color: #991b1b;
		border: 1px solid #ef4444;
	}

	.general-settings {
		background-color: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 2rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
		margin-top: 2rem;
	}

	.general-settings h2 {
		font-size: 1.5rem;
		color: #1f2937;
		margin: 0 0 1.5rem 0;
	}

	.update-button {
		background-color: #2563eb;
		color: white;
		border: none;
		padding: 0.75rem 1.5rem;
		border-radius: 6px;
		font-size: 0.875rem;
		cursor: pointer;
		transition: background-color 0.3s ease;
		margin-top: 1rem;
	}

	.update-button:hover {
		background-color: #1d4ed8;
	}

	:global(body) {
		background-color: #f9fafb;
	}
</style>