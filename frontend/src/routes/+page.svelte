<script lang="ts">
	import { onMount } from 'svelte';
	import { getApiUrl } from '$lib/config';
	
	interface Job {
		job_id: string;
		status: string;
		progress: number;
		message?: string;
		result_url?: string;
		error?: string;
	}

	let selectedFile: File | null = null;
	let currentJob: Job | null = null;
	let isUploading = false;
	let dragover = false;

	async function handleFileSelect(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target.files && target.files[0]) {
			selectedFile = target.files[0];
		}
	}

	async function handleDrop(event: DragEvent) {
		event.preventDefault();
		dragover = false;
		
		const files = event.dataTransfer?.files;
		if (files && files[0]) {
			selectedFile = files[0];
		}
	}

	async function uploadAndGenerate() {
		if (!selectedFile) return;

		isUploading = true;
		try {
			const formData = new FormData();
			formData.append('file', selectedFile);

			const response = await fetch(getApiUrl('/api/jobs/upload'), {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				throw new Error('アップロードに失敗しました');
			}

			const result = await response.json();
			currentJob = {
				job_id: result.job_id,
				status: 'processing',
				progress: 0
			};

			// 処理開始
			await startGeneration(result.job_id);
			
		} catch (error) {
			console.error('エラー:', error);
			alert('アップロードに失敗しました');
		} finally {
			isUploading = false;
		}
	}

	async function startGeneration(jobId: string) {
		try {
			// 動画生成開始
			const response = await fetch(getApiUrl(`/api/jobs/${jobId}/generate-video`), {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (!response.ok) {
				throw new Error('動画生成開始に失敗しました');
			}

			// 進捗監視開始
			pollJobStatus(jobId);
			
		} catch (error) {
			console.error('エラー:', error);
			if (currentJob) {
				currentJob.error = '動画生成に失敗しました';
			}
		}
	}

	async function pollJobStatus(jobId: string) {
		const poll = async () => {
			try {
				const response = await fetch(getApiUrl(`/api/jobs/${jobId}/status`));
				if (!response.ok) return;

				const job = await response.json();
				currentJob = job;

				if (job.status === 'completed' || job.status === 'failed') {
					return; // 完了
				}

				// 3秒後に再試行
				setTimeout(poll, 3000);
			} catch (error) {
				console.error('ステータス取得エラー:', error);
			}
		};

		poll();
	}

	function resetForm() {
		selectedFile = null;
		currentJob = null;
		isUploading = false;
	}
</script>

<svelte:head>
	<title>PDF to Video Generator</title>
</svelte:head>

<main class="container">
	<header>
		<h1>🎬 PDF to Video Generator</h1>
		<p>PDFスライドからずんだもん＆四国めたんの対話動画を自動生成</p>
	</header>

	{#if !currentJob}
		<section class="upload-section">
			<div 
				class="dropzone" 
				class:dragover
				on:dragover|preventDefault={() => dragover = true}
				on:dragleave={() => dragover = false}
				on:drop={handleDrop}
			>
				<div class="drop-content">
					<div class="upload-icon">📁</div>
					<h3>PDFファイルをアップロード</h3>
					<p>ドラッグ&ドロップまたはクリックしてファイルを選択</p>
					
					<input 
						type="file" 
						accept=".pdf" 
						on:change={handleFileSelect}
						class="file-input"
						id="file-input"
					/>
					<label for="file-input" class="file-label">
						ファイルを選択
					</label>
				</div>
			</div>

			{#if selectedFile}
				<div class="file-info">
					<div class="file-details">
						<strong>選択ファイル:</strong> {selectedFile.name}
						<br>
						<strong>サイズ:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
					</div>
					
					<button 
						class="generate-btn" 
						on:click={uploadAndGenerate}
						disabled={isUploading}
					>
						{isUploading ? '処理中...' : '🎥 動画生成開始'}
					</button>
					
					<button class="reset-btn" on:click={resetForm}>
						リセット
					</button>
				</div>
			{/if}
		</section>
	{:else}
		<section class="progress-section">
			<div class="job-info">
				<h3>動画生成中...</h3>
				<div class="job-id">Job ID: {currentJob.job_id}</div>
				
				<div class="progress-bar">
					<div 
						class="progress-fill" 
						style="width: {currentJob.progress}%"
					></div>
				</div>
				
				<div class="status-info">
					<div class="status">ステータス: {currentJob.status}</div>
					<div class="progress-text">{currentJob.progress}% 完了</div>
				</div>

				{#if currentJob.message}
					<div class="message">{currentJob.message}</div>
				{/if}

				{#if currentJob.error}
					<div class="error">❌ {currentJob.error}</div>
				{/if}

				{#if currentJob.status === 'completed' && currentJob.result_url}
					<div class="result">
						<h4>✅ 動画生成完了！</h4>
						<div class="download-section">
							<a 
								href={getApiUrl(currentJob.result_url)} 
								download 
								class="download-btn"
							>
								📥 動画をダウンロード
							</a>
							<video controls class="preview-video">
								<source src={getApiUrl(currentJob.result_url)} type="video/mp4">
								お使いのブラウザは動画再生に対応していません。
							</video>
						</div>
					</div>
				{/if}

				<button class="new-job-btn" on:click={resetForm}>
					新しい動画を作成
				</button>
			</div>
		</section>
	{/if}
</main>

<style>
	.container {
		max-width: 800px;
		margin: 0 auto;
		padding: 2rem;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	header {
		text-align: center;
		margin-bottom: 3rem;
	}

	header h1 {
		font-size: 2.5rem;
		color: #2563eb;
		margin-bottom: 0.5rem;
	}

	header p {
		color: #6b7280;
		font-size: 1.1rem;
	}

	.upload-section {
		margin-bottom: 2rem;
	}

	.dropzone {
		border: 2px dashed #d1d5db;
		border-radius: 12px;
		padding: 3rem;
		text-align: center;
		transition: all 0.3s ease;
		background-color: #f9fafb;
	}

	.dropzone:hover, .dropzone.dragover {
		border-color: #2563eb;
		background-color: #eff6ff;
	}

	.upload-icon {
		font-size: 3rem;
		margin-bottom: 1rem;
	}

	.file-input {
		display: none;
	}

	.file-label {
		display: inline-block;
		background-color: #2563eb;
		color: white;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		cursor: pointer;
		transition: background-color 0.3s ease;
		margin-top: 1rem;
	}

	.file-label:hover {
		background-color: #1d4ed8;
	}

	.file-info {
		margin-top: 2rem;
		padding: 1.5rem;
		background-color: #f3f4f6;
		border-radius: 8px;
	}

	.file-details {
		margin-bottom: 1rem;
		color: #374151;
	}

	.generate-btn {
		background-color: #10b981;
		color: white;
		border: none;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		cursor: pointer;
		font-size: 1rem;
		margin-right: 1rem;
		transition: background-color 0.3s ease;
	}

	.generate-btn:hover {
		background-color: #059669;
	}

	.generate-btn:disabled {
		background-color: #9ca3af;
		cursor: not-allowed;
	}

	.reset-btn, .new-job-btn {
		background-color: #6b7280;
		color: white;
		border: none;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		cursor: pointer;
		font-size: 1rem;
		transition: background-color 0.3s ease;
	}

	.reset-btn:hover, .new-job-btn:hover {
		background-color: #4b5563;
	}

	.progress-section {
		text-align: center;
	}

	.job-info {
		background-color: #f9fafb;
		padding: 2rem;
		border-radius: 12px;
		border: 1px solid #e5e7eb;
	}

	.job-id {
		font-family: monospace;
		color: #6b7280;
		margin-bottom: 1.5rem;
	}

	.progress-bar {
		width: 100%;
		height: 1rem;
		background-color: #e5e7eb;
		border-radius: 6px;
		overflow: hidden;
		margin: 1rem 0;
	}

	.progress-fill {
		height: 100%;
		background-color: #2563eb;
		transition: width 0.3s ease;
	}

	.status-info {
		display: flex;
		justify-content: space-between;
		margin-bottom: 1rem;
		color: #374151;
	}

	.message {
		background-color: #dbeafe;
		color: #1e40af;
		padding: 0.75rem;
		border-radius: 6px;
		margin: 1rem 0;
	}

	.error {
		background-color: #fee2e2;
		color: #dc2626;
		padding: 0.75rem;
		border-radius: 6px;
		margin: 1rem 0;
	}

	.result {
		margin-top: 2rem;
	}

	.download-section {
		margin-top: 1rem;
	}

	.download-btn {
		display: inline-block;
		background-color: #10b981;
		color: white;
		text-decoration: none;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		margin-bottom: 1rem;
		transition: background-color 0.3s ease;
	}

	.download-btn:hover {
		background-color: #059669;
	}

	.preview-video {
		width: 100%;
		max-width: 600px;
		margin-top: 1rem;
		border-radius: 8px;
	}

	.new-job-btn {
		margin-top: 2rem;
	}
</style>