<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { getApiUrl } from '$lib/config';
	
	interface Job {
		job_id: string;
		status: string;
		progress: number;
		message?: string;
		result_url?: string;
		error?: string;
	}

	interface DialogueData {
		[key: string]: Array<{
			speaker: string;
			text: string;
		}>;
	}

	interface Slide {
		slide_number: number;
		url: string;
	}

	let selectedFile: File | null = null;
	let currentJob: Job | null = null;
	let isUploading = false;
	let dragover = false;
	let dialogueData: DialogueData | null = null;
	let editingDialogue = false;
	let additionalPrompt = '';
	let currentStep: 'upload' | 'dialogue' | 'video' = 'upload';
	let slides: Slide[] = [];
	let isRegenerating = false;
	

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

			// ステータス監視開始（対話生成は既にサーバー側で行われる）
			// currentStepは自動的に更新される
			pollJobStatus(result.job_id);
			
		} catch (error) {
			console.error('エラー:', error);
			alert('アップロードに失敗しました');
		} finally {
			isUploading = false;
		}
	}

	async function generateDialogue(jobId: string, regenerate = false) {
		try {
			if (regenerate) {
				console.log('再生成開始:', { 
					jobId, 
					additionalPrompt,
					currentJobStatus: currentJob?.status,
					isRegenerating
				});
				isRegenerating = true;
				await tick(); // UIの更新を強制
			}
			
			const response = await fetch(getApiUrl(`/api/jobs/${jobId}/generate-dialogue`), {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					job_id: jobId,
					additional_prompt: regenerate ? additionalPrompt : null
				})
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(errorData.detail || '対話生成開始に失敗しました');
			}

			// 進捗監視開始
			pollJobStatus(jobId);
			
		} catch (error) {
			console.error('エラー:', error);
			alert(error.message || '対話生成に失敗しました');
			if (currentJob) {
				currentJob.error = error.message || '対話生成に失敗しました';
			}
			isRegenerating = false;
		}
	}

	async function startVideoGeneration(jobId: string) {
		try {
			// 編集された対話データがあれば保存
			if (editingDialogue && dialogueData) {
				await updateDialogue(jobId);
			}

			const response = await fetch(getApiUrl(`/api/jobs/${jobId}/generate-video`), {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				}
			});

			if (!response.ok) {
				throw new Error('動画生成開始に失敗しました');
			}

			currentStep = 'video';
			// 進捗監視開始
			pollJobStatus(jobId);
			
		} catch (error) {
			console.error('エラー:', error);
			if (currentJob) {
				currentJob.error = '動画生成に失敗しました';
			}
		}
	}

	async function loadDialogue(jobId: string, forceReload = false) {
		try {
			console.log('対話データ読み込み開始:', { jobId, forceReload, isRegenerating });
			
			// キャッシュを無効化するためのタイムスタンプを追加
			const timestamp = forceReload || isRegenerating ? `?t=${Date.now()}` : '';
			
			// 対話データを取得
			const dialogueResponse = await fetch(getApiUrl(`/api/jobs/${jobId}/dialogue${timestamp}`));
			if (!dialogueResponse.ok) {
				console.error('対話データ取得失敗:', dialogueResponse.status);
				return;
			}

			dialogueData = await dialogueResponse.json();
			console.log('対話データ取得成功:', Object.keys(dialogueData).length + 'スライド');
			
			// スライド画像も取得
			const slidesResponse = await fetch(getApiUrl(`/api/jobs/${jobId}/slides${timestamp}`));
			if (slidesResponse.ok) {
				slides = await slidesResponse.json();
				console.log('スライド画像取得成功:', slides.length + '枚');
			}
			
			currentStep = 'dialogue';
			console.log('currentStep更新:', currentStep);
			
			// 強制的にUIを更新
			await tick();
		} catch (error) {
			console.error('対話データ取得エラー:', error);
		}
	}

	async function updateDialogue(jobId: string) {
		try {
			const response = await fetch(getApiUrl(`/api/jobs/${jobId}/dialogue`), {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					job_id: jobId,
					dialogue_data: dialogueData
				})
			});

			if (!response.ok) {
				throw new Error('対話データ更新に失敗しました');
			}
		} catch (error) {
			console.error('対話データ更新エラー:', error);
		}
	}

	async function pollJobStatus(jobId: string) {
		console.log('ポーリング開始:', { jobId, currentStep });
		const poll = async () => {
			try {
				const response = await fetch(getApiUrl(`/api/jobs/${jobId}/status`));
				if (!response.ok) return;

				const job = await response.json();
				currentJob = job;
				console.log('ジョブステータス:', {
					status: job.status,
					progress: job.progress,
					message: job.message,
					dialogueData: !!dialogueData,
					currentStep
				});

				if (job.status === 'dialogue_ready' || job.status === 'slides_ready') {
					if (!dialogueData || isRegenerating) {
						console.log(`${job.status}検知、対話データ読み込み開始 (再生成: ${isRegenerating})`);
						// 対話データを読み込む
						await loadDialogue(jobId, true);  // 強制リロード
						isRegenerating = false;
						return; // ポーリング停止
					}
				} else if (job.status === 'completed' || job.status === 'failed') {
					console.log('処理完了/失敗:', job.status);
					isRegenerating = false;
					return; // 完了
				}

				// dialogue編集画面では、generating_dialogue以外はポーリング不要
				if (currentStep === 'dialogue' && job.status !== 'generating_dialogue') {
					return;
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
		dialogueData = null;
		editingDialogue = false;
		additionalPrompt = '';
		currentStep = 'upload';
		isRegenerating = false;
	}

	function addDialogueItem(slideKey: string) {
		if (!dialogueData) return;
		dialogueData[slideKey] = [
			...dialogueData[slideKey],
			{ speaker: 'metan', text: '' }
		];
	}

	function removeDialogueItem(slideKey: string, index: number) {
		if (!dialogueData) return;
		dialogueData[slideKey] = dialogueData[slideKey].filter((_, i) => i !== index);
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

	{#if currentStep === 'upload' && !currentJob}
		<section class="upload-section">
			<div 
				class="dropzone" 
				class:dragover
				role="button"
				tabindex="0"
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
						{isUploading ? '処理中...' : '📝 対話スクリプト生成'}
					</button>
					
					<button class="reset-btn" on:click={resetForm}>
						リセット
					</button>
				</div>
			{/if}
		</section>
	{:else if currentStep === 'dialogue' && dialogueData}
		<section class="dialogue-section">
			<h3>📝 対話スクリプト編集</h3>
			
			<div class="dialogue-controls">
				<button class="edit-btn" on:click={() => editingDialogue = !editingDialogue}>
					{editingDialogue ? '編集を終了' : '✏️ スクリプトを編集'}
				</button>
				<button class="generate-btn" on:click={() => currentJob && startVideoGeneration(currentJob.job_id)}>
					🎥 動画生成開始
				</button>
			</div>

			<div class="additional-prompt-section">
				<label for="additional-prompt">AIへの追加指示（再生成時に使用）:</label>
				<textarea 
					id="additional-prompt"
					bind:value={additionalPrompt}
					placeholder="例: 1枚目のスライドをもっとカジュアルに / 全体的に初心者向けに / 最初と最後のスライドを修正"
					rows="3"
					disabled={isRegenerating}
				></textarea>
				<button 
					class="regenerate-btn" 
					on:click={() => currentJob && generateDialogue(currentJob.job_id, true)}
					disabled={currentJob?.status === 'generating_dialogue' || isRegenerating || !additionalPrompt.trim()}
				>
					{isRegenerating ? '⏳ 再生成中...' : '🔄 スクリプト再生成'}
				</button>
				{#if isRegenerating && currentJob}
					<div class="regeneration-status">
						<div class="status-message">🤖 {currentJob.message || 'AIが修正対象を判断中...'}</div>
						<div class="progress-bar">
							<div class="progress-fill" style="width: {currentJob.progress}%"></div>
						</div>
					</div>
				{/if}
			</div>

			<div class="dialogue-list">
				{#each Object.entries(dialogueData) as [slideKey, dialogues]}
					<div class="slide-dialogue">
						<div class="slide-header">
							{#if slides.length > 0}
								{@const slideNum = parseInt(slideKey.split('_')[1])}
								{@const slide = slides.find(s => s.slide_number === slideNum)}
								{#if slide}
									<img src={getApiUrl(slide.url)} alt="Slide {slideNum}" class="slide-thumbnail" />
								{/if}
							{/if}
							<h4>{slideKey.replace('_', ' ')}</h4>
						</div>
						{#each dialogues as dialogue, index}
							<div class="dialogue-item">
								<div class="speaker-label {dialogue.speaker}">
									{dialogue.speaker === 'metan' ? '四国めたん' : 'ずんだもん'}
								</div>
								{#if editingDialogue}
									<textarea 
										bind:value={dialogue.text}
										class="dialogue-text-edit"
										rows="2"
									></textarea>
									<button 
										class="remove-btn" 
										on:click={() => removeDialogueItem(slideKey, index)}
									>
										✕
									</button>
								{:else}
									<div class="dialogue-text">{dialogue.text}</div>
								{/if}
							</div>
						{/each}
						{#if editingDialogue}
							<button 
								class="add-dialogue-btn" 
								on:click={() => addDialogueItem(slideKey)}
							>
								＋ セリフを追加
							</button>
						{/if}
					</div>
				{/each}
			</div>
		</section>
	{:else if currentJob}
		<section class="progress-section">
			<div class="job-info">
				<h3>{currentStep === 'video' ? '動画生成中...' : '対話スクリプト生成中...'}</h3>
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
		max-width: 1000px;
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

	/* 対話編集セクション */
	.dialogue-section {
		max-width: 100%;
	}

	.dialogue-controls {
		display: flex;
		gap: 1rem;
		margin-bottom: 2rem;
	}

	.edit-btn {
		background-color: #3b82f6;
		color: white;
		border: none;
		padding: 0.75rem 1.5rem;
		border-radius: 8px;
		cursor: pointer;
		transition: background-color 0.3s ease;
	}

	.edit-btn:hover {
		background-color: #2563eb;
	}

	.additional-prompt-section {
		background-color: #f3f4f6;
		padding: 1.5rem;
		border-radius: 8px;
		margin-bottom: 2rem;
	}

	.additional-prompt-section label {
		display: block;
		font-weight: bold;
		margin-bottom: 0.5rem;
		color: #374151;
	}

	.additional-prompt-section textarea {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		resize: vertical;
		font-family: inherit;
		margin-bottom: 1rem;
	}

	.regenerate-btn {
		background-color: #8b5cf6;
		color: white;
		border: none;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		cursor: pointer;
		transition: background-color 0.3s ease;
	}

	.regenerate-btn:hover {
		background-color: #7c3aed;
	}

	.regenerate-btn:disabled {
		background-color: #d1d5db;
		color: #9ca3af;
		cursor: not-allowed;
	}

	.regeneration-status {
		margin-top: 1rem;
		padding: 1rem;
		background-color: #f0f9ff;
		border: 1px solid #60a5fa;
		border-radius: 6px;
	}

	.status-message {
		font-size: 0.875rem;
		color: #1e40af;
		margin-bottom: 0.5rem;
	}

	.dialogue-list {
		max-height: 600px;
		overflow-y: auto;
		border: 1px solid #e5e7eb;
		border-radius: 8px;
		padding: 1rem;
		background-color: #ffffff;
	}

	.slide-dialogue {
		margin-bottom: 2rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.slide-dialogue:last-child {
		border-bottom: none;
	}

	.slide-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1rem;
	}

	.slide-thumbnail {
		width: 150px;
		height: auto;
		border-radius: 6px;
		border: 1px solid #e5e7eb;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.slide-dialogue h4 {
		color: #1f2937;
		text-transform: capitalize;
	}

	.dialogue-item {
		display: flex;
		align-items: flex-start;
		margin-bottom: 0.75rem;
		gap: 0.75rem;
	}

	.speaker-label {
		min-width: 100px;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.875rem;
		font-weight: bold;
	}

	.speaker-label.metan {
		background-color: #fef3c7;
		color: #92400e;
	}

	.speaker-label.zundamon {
		background-color: #d1fae5;
		color: #065f46;
	}

	.dialogue-text {
		flex: 1;
		padding: 0.5rem;
		background-color: #f9fafb;
		border-radius: 6px;
		line-height: 1.5;
	}

	.dialogue-text-edit {
		flex: 1;
		padding: 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		resize: vertical;
		font-family: inherit;
	}

	.remove-btn {
		background-color: #ef4444;
		color: white;
		border: none;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
		cursor: pointer;
		font-size: 0.875rem;
	}

	.remove-btn:hover {
		background-color: #dc2626;
	}

	.add-dialogue-btn {
		background-color: #f3f4f6;
		color: #4b5563;
		border: 1px dashed #9ca3af;
		padding: 0.5rem 1rem;
		border-radius: 6px;
		cursor: pointer;
		width: 100%;
		margin-top: 0.5rem;
		transition: all 0.3s ease;
	}

	.add-dialogue-btn:hover {
		background-color: #e5e7eb;
		border-color: #6b7280;
	}

	/* 進捗セクション */
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