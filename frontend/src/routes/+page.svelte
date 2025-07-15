<script lang="ts">
  import { onMount, tick } from "svelte";
  import { goto } from "$app/navigation";
  import { authenticatedFetch } from "$lib/auth";
  // getApiUrl は削除されました - 直接URLパスを使用

  interface Job {
    job_id: string;
    status: string;
    status_ja?: string;
    progress: number;
    message?: string;
    message_ja?: string;
    result_url?: string;
    error?: string;
    error_ja?: string;
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

  interface DialogueResponse {
    dialogue_data: DialogueData;
    estimated_duration: {
      seconds: number;
      formatted: string;
    };
  }

  let selectedFile: File | null = null;
  let currentJob: Job | null = null;
  let isUploading = false;
  let dragover = false;
  let dialogueData: DialogueData | null = null;
  let estimatedDuration: { seconds: number; formatted: string } | null = null;
  let editingDialogue = false;
  let additionalPrompt = "";
  let currentStep: "upload" | "dialogue" | "video" = "upload";
  let slides: Slide[] = [];
  let isRegenerating = false;
  let instructionHistory: any = {};
  let showHistory = false;
  let showHistoryForSlide: string | null = null;
  let targetDuration = 10; // デフォルト10分
  let availableSpeakers: any[] = [];
  let selectedSpeaker1Id = 2;
  let selectedSpeaker2Id = 3;
  let speaker1Speed = 1.0;
  let speaker2Speed = 1.0;
  let speakersLoading = false;
  let showRecommendations = false;
  let playingSampleId: number | null = null;
  let currentJobMetadata: any = null; // 現在のジョブのメタデータ
  let modalImageUrl: string | null = null; // モーダル表示用の画像URL
  let isUpdatingDialogue = false; // 対話データ更新中フラグ
  let selectedConversationStyle = "friendly"; // 選択された会話スタイル
  let showApiKeyWarning = false; // APIキー未設定警告の表示
  let hasAnyApiKey = false; // いずれかのAPIキーが設定されているか
  let isAuthenticated = false; // 認証状態
  let authEnabled = false; // 認証が有効かどうか

  // ステータス表示用のヘルパー関数
  function getDisplayStatus(job: Job): string {
    return job.status_ja || job.status;
  }

  function getDisplayMessage(job: Job): string {
    return job.message_ja || job.message || "";
  }

  function getDisplayError(job: Job): string {
    return job.error_ja || job.error || "";
  }

  // 会話スタイルの定義
  const conversationStyles = [
    {
      id: "radio",
      name: "🎤 ラジオ風",
      description: "リスナーに語りかけるような親しみやすいスタイル",
      prompt:
        "ラジオ番組のようにリスナーに語りかけるスタイルで。「リスナーのみなさん」「いかがでしょうか」などの表現を使い、暖かく親しみやすい雰囲気で。",
    },
    {
      id: "business",
      name: "💼 ビジネスライク",
      description: "プロフェッショナルで信頼感のあるスタイル",
      prompt:
        "ビジネスシーンに適したプロフェッショナルなスタイルで。敬語を適切に使い、論理的で説得力のある説明を心がけて。",
    },
    {
      id: "friendly",
      name: "😊 友達風",
      description: "カジュアルでフレンドリーなスタイル",
      prompt:
        "友達同士が話しているようなカジュアルなスタイルで。「だよね～」「っていうか」など、日常会話のような表現で。",
    },
    {
      id: "educational",
      name: "🎓 教育番組風",
      description: "子供向け教育番組のようなスタイル",
      prompt:
        "教育番組のようにわかりやすく、楽しく学べるスタイルで。「みんなも一緒に考えてみよう！」「すごい発見だね！」など、前向きな表現で。",
    },
    {
      id: "news",
      name: "📰 ニュース番組風",
      description: "キャスターが伝えるようなスタイル",
      prompt:
        "ニュース番組のように事実を正確に伝えるスタイルで。「さて、続いては」「詳しく見ていきましょう」など、フォーマルな表現で。",
    },
    {
      id: "podcast",
      name: "🎧 ポッドキャスト風",
      description: "ディープな話題を探求するスタイル",
      prompt:
        "ポッドキャストのように深い話題を探求するスタイルで。「これは興味深い点ですね」「もう少し掘り下げてみると」など、思考を深める表現で。",
    },
    {
      id: "variety",
      name: "🎨 バラエティ番組風",
      description: "明るく楽しいエンターテイメント風",
      prompt:
        "バラエティ番組のように明るく楽しいスタイルで。ツッコミやボケ、驚きのリアクションなどを取り入れて。「えー！」「マジで！？」など。",
    },
    {
      id: "commentary",
      name: "🎮 実況解説風",
      description: "スポーツ実況のような臨場感あるスタイル",
      prompt:
        "スポーツ実況のように臨場感あふれるスタイルで。「おっと、これは！」「素晴らしい展開です！」など、テンポよく盛り上げて。",
    },
  ];

  // ビジネス向けおすすめ組み合わせ
  const businessRecommendations = [
    {
      name: "最もプロフェッショナル",
      description: "企業向けプレゼンや研修動画に最適",
      speaker1: { id: 13, name: "青山龍星" },
      speaker2: { id: 16, name: "九州そら" },
    },
    {
      name: "バランス型",
      description: "幅広いビジネスシーンに対応",
      speaker1: { id: 11, name: "玄野武宏" },
      speaker2: { id: 8, name: "春日部つむぎ" },
    },
    {
      name: "若手向け",
      description: "スタートアップや若手向けコンテンツに",
      speaker1: { id: 14, name: "冥鳴ひまり" },
      speaker2: { id: 12, name: "白上虎太郎" },
    },
  ];

  async function loadSpeakers() {
    speakersLoading = true;
    try {
      const response = await authenticatedFetch("/api/speakers");
      if (response.ok) {
        availableSpeakers = await response.json();
      }
    } catch (error) {
      console.error("スピーカー一覧の取得に失敗:", error);
    } finally {
      speakersLoading = false;
    }
  }

  onMount(async () => {
    // 認証チェックを最初に実行
    await checkAuthStatus();

    loadSpeakers();
    // APIキーの設定状態をチェック
    await checkApiKeyStatus();
  });

  async function checkAuthStatus() {
    try {
      const response = await authenticatedFetch("/api/auth/status");
      if (response.ok) {
        const data = await response.json();
        authEnabled = data.auth_enabled;
        isAuthenticated = data.authenticated;

        // 認証が有効で未認証の場合はログインページにリダイレクト
        if (authEnabled && !isAuthenticated) {
          goto("/login");
          return;
        }
      }
    } catch (error) {
      console.error("認証状態の確認に失敗:", error);
    }
  }

  async function checkApiKeyStatus() {
    try {
      const response = await fetch("/api/settings/providers");
      if (response.ok) {
        const data = await response.json();
        // いずれかのプロバイダーが設定されているかチェック
        hasAnyApiKey = data.providers.some((p: any) => p.configured);

        // APIキーが1つも設定されていない場合は警告を表示
        if (!hasAnyApiKey) {
          showApiKeyWarning = true;
        }
      }
    } catch (error) {
      console.error("APIキー状態の確認に失敗:", error);
    }
  }

  // スピーカーが変更されたときに速度を自動調整
  $: if (availableSpeakers.length > 0 && selectedSpeaker1Id) {
    const speaker1 = availableSpeakers.find(
      (s) => s.style_id === selectedSpeaker1Id
    );
    if (speaker1 && speaker1.speaker_name === "九州そら") {
      speaker1Speed = 1.5;
    } else if (
      speaker1 &&
      speaker1.speaker_name !== "九州そら" &&
      speaker1Speed === 1.5
    ) {
      // 九州そら以外が選択された場合は1.0に戻す
      speaker1Speed = 1.0;
    }
  }

  $: if (availableSpeakers.length > 0 && selectedSpeaker2Id) {
    const speaker2 = availableSpeakers.find(
      (s) => s.style_id === selectedSpeaker2Id
    );
    if (speaker2 && speaker2.speaker_name === "九州そら") {
      speaker2Speed = 1.5;
    } else if (
      speaker2 &&
      speaker2.speaker_name !== "九州そら" &&
      speaker2Speed === 1.5
    ) {
      // 九州そら以外が選択された場合は1.0に戻す
      speaker2Speed = 1.0;
    }
  }

  function applyRecommendation(recommendation: any) {
    selectedSpeaker1Id = recommendation.speaker1.id;
    selectedSpeaker2Id = recommendation.speaker2.id;
    showRecommendations = false;
  }

  async function playVoiceSample(
    speakerId: number,
    speakerName: string,
    speed: number
  ) {
    try {
      playingSampleId = speakerId;

      const sampleText =
        speakerName === "ずんだもん"
          ? "こんにちは！ずんだもんなのだ！"
          : `こんにちは！${speakerName}です。よろしくお願いします。`;

      const response = await fetch("/api/voice-sample", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          speaker_id: speakerId,
          speaker_name: speakerName,
          speed: speed,
          text: sampleText,
        }),
      });

      if (response.ok) {
        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);

        await audio.play();

        // メモリリークを防ぐためにURLを解放
        audio.addEventListener("ended", () => {
          URL.revokeObjectURL(audioUrl);
          playingSampleId = null;
        });
      } else {
        playingSampleId = null;
      }
    } catch (error) {
      console.error("サンプルボイスの再生に失敗:", error);
      playingSampleId = null;
    }
  }

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
      formData.append("file", selectedFile);
      formData.append("target_duration", targetDuration.toString());
      // 選択されたスピーカー情報を取得
      const speaker1 = availableSpeakers.find(
        (s) => s.style_id === selectedSpeaker1Id
      );
      const speaker2 = availableSpeakers.find(
        (s) => s.style_id === selectedSpeaker2Id
      );

      formData.append("speaker1_id", selectedSpeaker1Id.toString());
      formData.append(
        "speaker1_name",
        speaker1 ? speaker1.speaker_name : "四国めたん"
      );
      formData.append("speaker1_speed", speaker1Speed.toString());
      formData.append("speaker2_id", selectedSpeaker2Id.toString());
      formData.append(
        "speaker2_name",
        speaker2 ? speaker2.speaker_name : "ずんだもん"
      );
      formData.append("speaker2_speed", speaker2Speed.toString());

      // 会話スタイル情報を追加
      const selectedStyle = conversationStyles.find(
        (s) => s.id === selectedConversationStyle
      );
      formData.append("conversation_style", selectedConversationStyle);
      formData.append(
        "conversation_style_prompt",
        selectedStyle ? selectedStyle.prompt : ""
      );

      const response = await fetch("/api/jobs/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("アップロードに失敗しました");
      }

      const result = await response.json();
      currentJob = {
        job_id: result.job_id,
        status: "processing",
        progress: 0,
      };

      // 進行状況画面に切り替える（重要！）
      currentStep = "dialogue";

      // ステータス監視開始（対話生成は既にサーバー側で行われる）
      pollJobStatus(result.job_id);
    } catch (error) {
      console.error("エラー:", error);
      alert("アップロードに失敗しました");
    } finally {
      isUploading = false;
    }
  }

  async function generateDialogue(jobId: string, regenerate = false) {
    try {
      if (regenerate) {
        console.log("再生成開始:", {
          jobId,
          additionalPrompt,
          currentJobStatus: currentJob?.status,
          isRegenerating,
        });
        isRegenerating = true;
        await tick(); // UIの更新を強制
      }

      const response = await fetch(`/api/jobs/${jobId}/generate-dialogue`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          job_id: jobId,
          additional_prompt: regenerate ? additionalPrompt : null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "対話生成開始に失敗しました");
      }

      // 進捗監視開始
      pollJobStatus(jobId);
    } catch (error) {
      console.error("エラー:", error);
      alert(error.message || "対話生成に失敗しました");
      if (currentJob) {
        currentJob.error = error.message || "対話生成に失敗しました";
      }
      isRegenerating = false;
    }
  }

  async function startVideoGeneration(jobId: string) {
    try {
      // 編集中の場合は先に編集を終了
      if (editingDialogue) {
        editingDialogue = false;
        await tick(); // UIの更新を待つ
      }

      // 対話データがあれば必ず保存（編集された可能性があるため）
      if (dialogueData) {
        await updateDialogue(jobId);
        // 保存完了を待つ
        await new Promise((resolve) => setTimeout(resolve, 500));
      }

      const response = await fetch(`/api/jobs/${jobId}/generate-video`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("動画生成開始に失敗しました");
      }

      currentStep = "video";
      // 進捗監視開始
      pollJobStatus(jobId);
    } catch (error) {
      console.error("エラー:", error);
      if (currentJob) {
        currentJob.error = "動画生成に失敗しました";
      }
    }
  }

  async function loadDialogue(jobId: string, forceReload = false) {
    try {
      console.log("対話データ読み込み開始:", {
        jobId,
        forceReload,
        isRegenerating,
      });

      // キャッシュを無効化するためのタイムスタンプを追加
      const timestamp = forceReload || isRegenerating ? `?t=${Date.now()}` : "";

      // 対話データを取得
      const dialogueResponse = await fetch(
        `/api/jobs/${jobId}/dialogue${timestamp}`
      );
      if (!dialogueResponse.ok) {
        console.error("対話データ取得失敗:", dialogueResponse.status);
        return;
      }

      const dialogueResult: DialogueResponse = await dialogueResponse.json();
      console.log("Raw dialogueResult:", dialogueResult);
      console.log(
        "dialogue_data keys before assignment:",
        Object.keys(dialogueResult.dialogue_data)
      );

      // Svelteの反応性を確実にするため、新しいオブジェクトとして割り当て
      dialogueData = { ...dialogueResult.dialogue_data };
      estimatedDuration = dialogueResult.estimated_duration;

      // デバッグ用ログ
      console.log(
        "対話データ取得成功:",
        Object.keys(dialogueData).length + "スライド"
      );
      console.log("推定動画時間:", estimatedDuration?.formatted);
      console.log("dialogueData after assignment:", dialogueData);
      console.log("dialogueData keys:", Object.keys(dialogueData));

      // スライド画像も取得
      const slidesResponse = await fetch(
        `/api/jobs/${jobId}/slides${timestamp}`
      );
      if (slidesResponse.ok) {
        slides = await slidesResponse.json();
        console.log("スライド画像取得成功:", slides.length + "枚");
      }

      // 指示履歴も取得
      await loadInstructionHistory(jobId);

      // メタデータも取得
      await loadJobMetadata(jobId);

      currentStep = "dialogue";
      console.log("currentStep更新:", currentStep);

      // 強制的にUIを更新
      await tick();
    } catch (error) {
      console.error("対話データ取得エラー:", error);
    }
  }

  async function loadInstructionHistory(jobId: string) {
    try {
      const response = await fetch(`/api/jobs/${jobId}/instruction-history`);
      if (response.ok) {
        const data = await response.json();
        instructionHistory = data.history || {};
        console.log("指示履歴取得成功:", instructionHistory);
      }
    } catch (error) {
      console.error("指示履歴取得エラー:", error);
    }
  }

  async function loadJobMetadata(jobId: string) {
    try {
      const response = await fetch(`/api/jobs/${jobId}/metadata`);
      if (response.ok) {
        currentJobMetadata = await response.json();
        console.log("メタデータ取得成功:", currentJobMetadata);
      }
    } catch (error) {
      console.error("メタデータ取得エラー:", error);
    }
  }

  async function updateDialogue(jobId: string) {
    try {
      isUpdatingDialogue = true;

      const response = await fetch(`/api/jobs/${jobId}/dialogue`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          job_id: jobId,
          dialogue_data: dialogueData,
        }),
      });

      if (!response.ok) {
        throw new Error("対話データ更新に失敗しました");
      }

      const result = await response.json();

      // 推定時間を更新
      if (result.estimated_duration) {
        estimatedDuration = result.estimated_duration;
      }

      console.log("対話データ更新成功");
    } catch (error) {
      console.error("対話データ更新エラー:", error);
    } finally {
      isUpdatingDialogue = false;
    }
  }

  async function pollJobStatus(jobId: string) {
    console.log("ポーリング開始:", { jobId, currentStep });
    const poll = async () => {
      try {
        // 対話データ更新中はポーリングをスキップ
        if (isUpdatingDialogue) {
          setTimeout(poll, 3000);
          return;
        }

        const response = await fetch(`/api/jobs/${jobId}/status`);
        if (!response.ok) return;

        const job = await response.json();
        currentJob = job;
        console.log("ジョブステータス:", {
          status: job.status,
          progress: job.progress,
          message: job.message,
          dialogueData: !!dialogueData,
          currentStep,
          editingDialogue,
        });

        if (job.status === "dialogue_ready" || job.status === "slides_ready") {
          // 対話編集画面で編集中の場合は、データを再読み込みしない
          if (currentStep === "dialogue" && editingDialogue) {
            console.log("編集中のため、データ再読み込みをスキップ");
            return; // ポーリング停止
          }

          if (!dialogueData || isRegenerating) {
            console.log(
              `${job.status}検知、対話データ読み込み開始 (再生成: ${isRegenerating})`
            );
            // 対話データを読み込む
            await loadDialogue(jobId, true); // 強制リロード

            // 対話データ生成完了（全体調整とカタカナ変換も含む）
            console.log("対話データ生成完了（全体調整とカタカナ変換済み）");

            isRegenerating = false;
            return; // ポーリング停止
          }
        } else if (job.status === "completed" || job.status === "failed") {
          console.log("処理完了/失敗:", job.status);
          isRegenerating = false;
          return; // 完了
        }

        // dialogue編集画面で対話データが既に存在する場合は、generating_dialogue以外はポーリング不要
        if (
          currentStep === "dialogue" &&
          dialogueData &&
          job.status !== "generating_dialogue"
        ) {
          return;
        }

        // 3秒後に再試行
        setTimeout(poll, 3000);
      } catch (error) {
        console.error("ステータス取得エラー:", error);
      }
    };

    poll();
  }

  function resetForm() {
    selectedFile = null;
    currentJob = null;
    isUploading = false;
    dialogueData = null;
    estimatedDuration = null;
    editingDialogue = false;
    additionalPrompt = "";
    currentStep = "upload";
    isRegenerating = false;
    showHistoryForSlide = null;
    targetDuration = 10; // デフォルトに戻す
  }

  function addDialogueItem(slideKey: string) {
    if (!dialogueData) return;
    // 最後の発話者と逆のスピーカーを選択
    const lastSpeaker =
      dialogueData[slideKey].length > 0
        ? dialogueData[slideKey][dialogueData[slideKey].length - 1].speaker
        : "speaker2";
    const nextSpeaker = lastSpeaker === "speaker1" ? "speaker2" : "speaker1";

    dialogueData[slideKey] = [
      ...dialogueData[slideKey],
      { speaker: nextSpeaker, text: "" },
    ];
  }

  function removeDialogueItem(slideKey: string, index: number) {
    if (!dialogueData) return;
    dialogueData[slideKey] = dialogueData[slideKey].filter(
      (_, i) => i !== index
    );
  }

  function openImageModal(imageUrl: string) {
    modalImageUrl = imageUrl;
  }

  function closeImageModal() {
    modalImageUrl = null;
  }

  function toggleSlideHistory(slideKey: string) {
    if (showHistoryForSlide === slideKey) {
      showHistoryForSlide = null;
    } else {
      showHistoryForSlide = slideKey;
    }
  }

  async function downloadCSV(jobId: string) {
    try {
      const response = await fetch(`/api/jobs/${jobId}/dialogue/csv`);
      if (!response.ok) {
        throw new Error("CSVダウンロードに失敗しました");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dialogue_${jobId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("CSVダウンロードエラー:", error);
      alert("CSVダウンロードに失敗しました");
    }
  }

  async function handleCSVUpload(event: Event) {
    const target = event.target as HTMLInputElement;
    if (!target.files || !target.files[0] || !currentJob) return;

    const file = target.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(
        `/api/jobs/${currentJob.job_id}/dialogue/csv`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "CSVアップロードに失敗しました");
      }

      const result = await response.json();

      // 推定時間を更新
      if (result.estimated_duration) {
        estimatedDuration = result.estimated_duration;
      }

      alert(`${result.message}`);

      // 対話データを再読み込み
      await loadDialogue(currentJob.job_id, true);
    } catch (error) {
      console.error("CSVアップロードエラー:", error);
      alert(error.message || "CSVアップロードに失敗しました");
    } finally {
      // ファイル選択をリセット
      target.value = "";
    }
  }
</script>

<svelte:head>
  <title>longan - PDF to Video Generator</title>
</svelte:head>

<main class="container">
  <header>
    <div class="header-content">
      <div>
        <h1>
          <img src="/favicon.png" alt="longan" class="logo-icon" /> longan
        </h1>
        <p>PDFスライドからVOICEVOXキャラクターによる対話動画を自動生成</p>
      </div>
      <a href="/settings" class="settings-link"> ⚙️ LLM設定 </a>
    </div>
  </header>

  {#if currentStep === "upload"}
    <section class="upload-section">
      {#if !selectedFile}
        <div
          class="dropzone"
          class:dragover
          role="button"
          tabindex="0"
          on:dragover|preventDefault={() => (dragover = true)}
          on:dragleave={() => (dragover = false)}
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
            <label for="file-input" class="file-label"> ファイルを選択 </label>
          </div>
        </div>
      {/if}

      {#if selectedFile}
        <div class="file-info">
          <div class="file-details">
            <strong>選択ファイル:</strong>
            {selectedFile.name}
            <br />
            <strong>サイズ:</strong>
            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
          </div>

          <div class="duration-setting">
            <label for="target-duration">目安動画時間:</label>
            <input
              type="number"
              id="target-duration"
              bind:value={targetDuration}
              min="1"
              max="60"
              step="1"
            />
            <span>分</span>
          </div>

          <div class="conversation-style-settings">
            <h4>会話スタイル</h4>
            <div class="style-grid">
              {#each conversationStyles as style}
                <div class="style-option">
                  <input
                    type="radio"
                    id="style-{style.id}"
                    name="conversationStyle"
                    value={style.id}
                    bind:group={selectedConversationStyle}
                  />
                  <label for="style-{style.id}" class="style-label">
                    <span class="style-name">{style.name}</span>
                    <span class="style-description">{style.description}</span>
                  </label>
                </div>
              {/each}
            </div>
          </div>

          <div class="speaker-settings">
            <h4>キャラクター設定</h4>
            <button
              class="recommendation-toggle"
              on:click={() => (showRecommendations = !showRecommendations)}
              disabled={playingSampleId !== null}
            >
              💼 ビジネス向けおすすめを見る
            </button>

            {#if showRecommendations}
              <div class="recommendations">
                <h5>ビジネス向けおすすめ組み合わせ</h5>
                {#each businessRecommendations as rec}
                  <div class="recommendation-item">
                    <div class="rec-header">
                      <strong>{rec.name}</strong>
                      <button
                        class="apply-btn"
                        on:click={() => applyRecommendation(rec)}
                        disabled={playingSampleId !== null}
                      >
                        この組み合わせを使う
                      </button>
                    </div>
                    <p class="rec-description">{rec.description}</p>
                    <p class="rec-speakers">
                      説明役: {rec.speaker1.name} / 聞き役: {rec.speaker2.name}
                    </p>
                  </div>
                {/each}
              </div>
            {/if}

            {#if speakersLoading}
              <p>読み込み中...</p>
            {:else}
              <div class="speaker-row">
                <label for="speaker1">話者1（説明役）:</label>
                <select
                  id="speaker1"
                  bind:value={selectedSpeaker1Id}
                  disabled={playingSampleId !== null}
                >
                  {#each availableSpeakers as speaker}
                    <option value={speaker.style_id}>
                      {speaker.display_name}
                    </option>
                  {/each}
                </select>
                <button
                  class="sample-btn"
                  class:loading={playingSampleId === selectedSpeaker1Id}
                  on:click={() => {
                    const speaker = availableSpeakers.find(
                      (s) => s.style_id === selectedSpeaker1Id
                    );
                    if (speaker)
                      playVoiceSample(
                        selectedSpeaker1Id,
                        speaker.speaker_name,
                        speaker1Speed
                      );
                  }}
                  disabled={playingSampleId !== null}
                  title="サンプルボイスを再生"
                >
                  {#if playingSampleId === selectedSpeaker1Id}
                    <span class="spinner"></span>
                  {:else}
                    🔊
                  {/if}
                </button>
              </div>
              <div class="speed-row">
                <label for="speaker1-speed"
                  >話者1の速度: {speaker1Speed.toFixed(1)}倍</label
                >
                <input
                  type="range"
                  id="speaker1-speed"
                  bind:value={speaker1Speed}
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  class="speed-slider"
                />
              </div>
              <div class="speaker-row">
                <label for="speaker2">話者2（聞き役）:</label>
                <select
                  id="speaker2"
                  bind:value={selectedSpeaker2Id}
                  disabled={playingSampleId !== null}
                >
                  {#each availableSpeakers as speaker}
                    <option value={speaker.style_id}>
                      {speaker.display_name}
                    </option>
                  {/each}
                </select>
                <button
                  class="sample-btn"
                  class:loading={playingSampleId === selectedSpeaker2Id}
                  on:click={() => {
                    const speaker = availableSpeakers.find(
                      (s) => s.style_id === selectedSpeaker2Id
                    );
                    if (speaker)
                      playVoiceSample(
                        selectedSpeaker2Id,
                        speaker.speaker_name,
                        speaker2Speed
                      );
                  }}
                  disabled={playingSampleId !== null}
                  title="サンプルボイスを再生"
                >
                  {#if playingSampleId === selectedSpeaker2Id}
                    <span class="spinner"></span>
                  {:else}
                    🔊
                  {/if}
                </button>
              </div>
              <div class="speed-row">
                <label for="speaker2-speed"
                  >話者2の速度: {speaker2Speed.toFixed(1)}倍</label
                >
                <input
                  type="range"
                  id="speaker2-speed"
                  bind:value={speaker2Speed}
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  class="speed-slider"
                />
              </div>
            {/if}
          </div>

          {#if dialogueData && currentJob}
            <button
              class="back-to-dialogue-btn"
              on:click={() => {
                currentStep = "dialogue";
              }}
            >
              📝 スクリプト編集に戻る
            </button>
          {:else}
            <button
              class="generate-btn"
              on:click={uploadAndGenerate}
              disabled={isUploading || playingSampleId !== null}
            >
              {isUploading ? "処理中..." : "📝 対話スクリプト生成"}
            </button>
          {/if}

          <button class="reset-btn" on:click={resetForm}> リセット </button>
        </div>
      {/if}
    </section>
  {:else if currentStep === "dialogue" && dialogueData}
    <section class="dialogue-section">
      <h3>📝 対話スクリプト編集</h3>

      {#if estimatedDuration}
        <div class="duration-estimate">
          <span class="duration-icon">⏱️</span>
          <span class="duration-text"
            >推定動画時間: <strong>{estimatedDuration.formatted}</strong></span
          >
        </div>
      {/if}

      <div class="dialogue-controls">
        <button
          class="back-to-settings-btn"
          on:click={() => {
            const confirmed = confirm(
              "キャラクター設定に戻りますか？\n\n現在の対話スクリプトの内容は保持されますが、編集中の変更は失われる可能性があります。"
            );
            if (confirmed) {
              currentStep = "upload";
              // currentJobとdialogueDataは保持して、後で戻れるようにする
              editingDialogue = false;
              isRegenerating = false;
            }
          }}
        >
          ⬅️ キャラクター設定に戻る
        </button>
        <button
          class="edit-btn"
          on:click={async () => {
            if (editingDialogue && currentJob) {
              // 編集を終了する前に保存
              await updateDialogue(currentJob.job_id);
            }
            editingDialogue = !editingDialogue;
          }}
        >
          {editingDialogue ? "編集を終了" : "✏️ スクリプトを編集"}
        </button>
        <button
          class="csv-download-btn"
          on:click={async () => {
            if (!currentJob) return;
            // 編集中でなくても、念のためデータを保存
            if (dialogueData) {
              await updateDialogue(currentJob.job_id);
              // 保存完了を待つ
              await new Promise((resolve) => setTimeout(resolve, 500));
            }
            await downloadCSV(currentJob.job_id);
          }}
        >
          📥 CSVダウンロード
        </button>
        <button
          class="csv-upload-btn"
          on:click={() => document.getElementById("csv-upload-input")?.click()}
        >
          📤 CSVアップロード
        </button>
        <input
          id="csv-upload-input"
          type="file"
          accept=".csv"
          style="display: none"
          on:change={handleCSVUpload}
        />
        <button
          class="generate-btn"
          on:click={() => currentJob && startVideoGeneration(currentJob.job_id)}
        >
          🎥 動画生成開始
        </button>
      </div>

      <div class="edit-notice">
        <span class="notice-icon">⚠️</span>
        <span class="notice-text">
          <strong>編集時の注意：</strong>英単語はカタカナで入力してください。
          アルファベットのまま入力すると音声生成時に正しく読み上げられない場合があります。
          <br />
          例: API → エーピーアイ、Claude → クロード、USB → ユーエスビー、CLI → シーエルアイ
        </span>
      </div>

      <div class="additional-prompt-section">
        <label for="additional-prompt">
          AIへの追加指示（再生成時に使用）
          {#if editingDialogue}
            <span style="color: #999;">※編集中は使用できません</span>
          {/if}
          :</label
        >
        <textarea
          id="additional-prompt"
          bind:value={additionalPrompt}
          placeholder="例: 1枚目のスライドをもっとカジュアルに / 全体的に初心者向けに / 最初と最後のスライドを修正"
          rows="3"
          disabled={isRegenerating || editingDialogue}
        ></textarea>
        <button
          class="regenerate-btn"
          on:click={() =>
            currentJob && generateDialogue(currentJob.job_id, true)}
          disabled={currentJob?.status === "generating_dialogue" ||
            isRegenerating ||
            !additionalPrompt.trim() ||
            editingDialogue}
        >
          {isRegenerating ? "⏳ 再生成中..." : "🔄 スクリプト再生成"}
        </button>
        {#if isRegenerating && currentJob}
          <div class="regeneration-status">
            <div class="status-message">
              🤖 {getDisplayMessage(currentJob) || "AIが修正対象を判断中..."}
            </div>
            <div class="progress-bar">
              <div
                class="progress-fill"
                style="width: {currentJob.progress}%"
              ></div>
            </div>
          </div>
        {/if}
      </div>

      <div class="dialogue-list">
        {#each Object.entries(dialogueData) as [slideKey, dialogues]}
          {@const slideNum = parseInt(slideKey.split("_")[1])}
          {@const slideHistory = instructionHistory[slideKey] || []}
          <div class="slide-dialogue">
            <div class="slide-header">
              {#if slides.length > 0}
                {@const slide = slides.find((s) => s.slide_number === slideNum)}
                {#if slide}
                  <img
                    src={slide.url}
                    alt="Slide {slideNum}"
                    class="slide-thumbnail clickable"
                    on:click={() => openImageModal(slide.url)}
                    role="button"
                    tabindex="0"
                    on:keydown={(e) =>
                      e.key === "Enter" && openImageModal(slide.url)}
                  />
                {/if}
              {/if}
              <h4>{slideKey.replace("slide_", "スライド")}</h4>
              {#if slideHistory.length > 0}
                <button
                  class="history-toggle"
                  on:click={() => toggleSlideHistory(slideKey)}
                  title="指示履歴を表示"
                >
                  📝 履歴 ({slideHistory.length})
                </button>
              {/if}
            </div>
            {#if showHistoryForSlide === slideKey}
              <div class="instruction-history">
                <h5>再生成指示履歴:</h5>
                {#each slideHistory as hist, idx}
                  <div class="history-item">
                    <div class="history-timestamp">
                      {new Date(hist.timestamp).toLocaleString("ja-JP")}
                    </div>
                    <div class="history-instruction">
                      {hist.instruction}
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
            {#each dialogues as dialogue, index}
              <div class="dialogue-item">
                <div class="speaker-label {dialogue.speaker}">
                  {#if dialogue.speaker === "speaker1"}
                    {currentJobMetadata?.speaker1?.name || "話者1"}
                  {:else if dialogue.speaker === "speaker2"}
                    {currentJobMetadata?.speaker2?.name || "話者2"}
                  {:else if dialogue.speaker === "metan"}
                    四国めたん
                  {:else if dialogue.speaker === "zundamon"}
                    ずんだもん
                  {:else}
                    {dialogue.speaker}
                  {/if}
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
  {:else if currentJob && (isUploading || currentJob.status === "processing" || currentJob.status === "generating_dialogue" || currentStep === "video" || (currentStep === "dialogue" && !dialogueData))}
    <section class="progress-section">
      <div class="job-info">
        <h3>
          {currentStep === "video"
            ? "動画生成中..."
            : "対話スクリプト生成中..."}
        </h3>
        <div class="job-id">Job ID: {currentJob.job_id}</div>

        <div class="progress-bar">
          <div
            class="progress-fill"
            style="width: {currentJob.progress}%"
          ></div>
        </div>

        <div class="status-info">
          <div class="status">ステータス: {getDisplayStatus(currentJob)}</div>
          <div class="progress-text">{currentJob.progress}% 完了</div>
        </div>

        {#if getDisplayMessage(currentJob)}
          <div class="message">{getDisplayMessage(currentJob)}</div>
        {/if}

        {#if getDisplayError(currentJob)}
          <div class="error">❌ {getDisplayError(currentJob)}</div>
        {/if}

        {#if currentJob.status === "completed" && currentJob.result_url}
          <div class="result">
            <h4>✅ 動画生成完了！</h4>
            <div class="download-section">
              <a href={currentJob.result_url} download class="download-btn">
                📥 動画をダウンロード
              </a>
              <video controls class="preview-video">
                <source src={currentJob.result_url} type="video/mp4" />
                お使いのブラウザは動画再生に対応していません。
              </video>
            </div>
            <div class="action-buttons">
              <button
                class="back-to-script-btn"
                on:click={() => {
                  if (currentJob && dialogueData) {
                    currentStep = "dialogue";
                  }
                }}
              >
                📝 スクリプトに戻る
              </button>
            </div>
          </div>
        {/if}

        <button class="new-job-btn" on:click={resetForm}>
          新しい動画を作成
        </button>
      </div>
    </section>
  {/if}

  <!-- APIキー警告ポップアップ -->
  {#if showApiKeyWarning}
    <div class="modal-overlay" on:click={() => (showApiKeyWarning = false)}>
      <div class="api-key-warning" on:click|stopPropagation>
        <h2>⚠️ LLMプロバイダーの設定が必要です</h2>
        <p>
          AIによる対話生成を利用するには、LLMプロバイダーのAPIキーを設定してください。
        </p>
        <div class="warning-actions">
          <a href="/settings" class="primary-btn"> ⚙️ 設定画面へ </a>
          <button
            class="secondary-btn"
            on:click={() => (showApiKeyWarning = false)}
          >
            後で設定
          </button>
        </div>
      </div>
    </div>
  {/if}
</main>

{#if modalImageUrl}
  <div
    class="modal-overlay"
    on:click={closeImageModal}
    role="button"
    tabindex="0"
    on:keydown={(e) => e.key === "Escape" && closeImageModal()}
  >
    <div class="modal-content" on:click|stopPropagation>
      <button class="modal-close" on:click={closeImageModal}>✕</button>
      <img src={modalImageUrl} alt="拡大画像" class="modal-image" />
    </div>
  </div>
{/if}

<style>
  .container {
    max-width: 1000px;
    margin: 0 auto;
    padding: 2rem;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      sans-serif;
  }

  header {
    margin-bottom: 3rem;
  }

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header-content > div {
    text-align: center;
    flex: 1;
  }

  .settings-link {
    background-color: #6b7280;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    text-decoration: none;
    font-size: 0.9rem;
    transition: background-color 0.3s ease;
    white-space: nowrap;
  }

  .settings-link:hover {
    background-color: #4b5563;
  }

  header h1 {
    font-size: 2.5rem;
    color: #2563eb;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .logo-icon {
    width: 2.5rem;
    height: 2.5rem;
    object-fit: contain;
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

  .dropzone:hover,
  .dropzone.dragover {
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

  .reset-btn,
  .new-job-btn {
    background-color: #6b7280;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.3s ease;
  }

  .reset-btn:hover,
  .new-job-btn:hover {
    background-color: #4b5563;
  }

  /* 対話編集セクション */
  .dialogue-section {
    max-width: 100%;
  }

  .duration-estimate {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background-color: #e0f2fe;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    border: 1px solid #7dd3fc;
  }

  .duration-icon {
    font-size: 1.25rem;
  }

  .duration-text {
    color: #0369a1;
    font-size: 1rem;
  }

  .duration-text strong {
    font-weight: 600;
    color: #0c4a6e;
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

  .csv-download-btn,
  .csv-upload-btn {
    background-color: #059669;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }

  .csv-download-btn:hover,
  .csv-upload-btn:hover {
    background-color: #047857;
  }

  .refine-btn {
    background-color: #f59e0b;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    margin-right: 1rem;
    transition: background-color 0.3s ease;
  }

  .refine-btn:hover {
    background-color: #d97706;
  }

  .edit-notice {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    background-color: #fef3c7;
    border: 1px solid #fbbf24;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
  }

  .notice-icon {
    font-size: 1.25rem;
    flex-shrink: 0;
  }

  .notice-text {
    color: #92400e;
    font-size: 0.9rem;
    line-height: 1.5;
  }

  .notice-text strong {
    font-weight: 600;
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
    position: relative;
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

  /* 会話スタイル設定 */
  .conversation-style-settings {
    margin: 2rem 0;
  }

  .conversation-style-settings h4 {
    margin-bottom: 1rem;
    color: #1f2937;
  }

  .style-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
  }

  .style-option {
    position: relative;
  }

  .style-option input[type="radio"] {
    position: absolute;
    opacity: 0;
  }

  .style-label {
    display: flex;
    flex-direction: column;
    padding: 1rem;
    border: 2px solid #e5e7eb;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    background-color: white;
  }

  .style-option input[type="radio"]:checked + .style-label {
    border-color: #3b82f6;
    background-color: #eff6ff;
  }

  .style-option input[type="radio"]:hover + .style-label {
    border-color: #93c5fd;
  }

  .style-name {
    font-weight: 600;
    font-size: 1.1rem;
    color: #1f2937;
    margin-bottom: 0.25rem;
  }

  .style-description {
    font-size: 0.875rem;
    color: #6b7280;
    line-height: 1.4;
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

  .action-buttons {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-top: 1.5rem;
  }

  .back-to-script-btn {
    background-color: #3b82f6;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.3s ease;
  }

  .back-to-script-btn:hover {
    background-color: #2563eb;
  }

  /* 目安時間設定スタイル */
  .duration-setting {
    margin: 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .duration-setting label {
    font-weight: 500;
    color: #374151;
  }

  .duration-setting input {
    width: 80px;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 1rem;
    text-align: center;
  }

  .duration-setting span {
    color: #6b7280;
  }

  /* キャラクター設定スタイル */
  .speaker-settings {
    margin: 1.5rem 0;
    padding: 1rem;
    background-color: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
  }

  .speaker-settings h4 {
    margin: 0 0 1rem 0;
    color: #374151;
    font-size: 1.1rem;
  }

  .speaker-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.75rem;
  }

  .speaker-row:last-child {
    margin-bottom: 0;
  }

  .speaker-row label {
    min-width: 150px;
    font-weight: 500;
    color: #374151;
  }

  .speaker-row select {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 1rem;
    background-color: white;
    cursor: pointer;
  }

  .speaker-row select:hover {
    border-color: #9ca3af;
  }

  .speaker-row select:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }

  .speed-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-top: 0.5rem;
    margin-bottom: 1rem;
    padding-left: 166px; /* label幅 + gap分のインデント */
  }

  .speed-row label {
    min-width: 150px;
    font-size: 0.9rem;
    color: #6b7280;
  }

  .speed-slider {
    flex: 1;
    height: 6px;
    background: #e5e7eb;
    border-radius: 3px;
    outline: none;
    -webkit-appearance: none;
  }

  .speed-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #2563eb;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .speed-slider::-webkit-slider-thumb:hover {
    transform: scale(1.1);
    background: #1d4ed8;
  }

  .speed-slider::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #2563eb;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
  }

  .speed-slider::-moz-range-thumb:hover {
    transform: scale(1.1);
    background: #1d4ed8;
  }

  .recommendation-toggle {
    background-color: #f3f4f6;
    color: #1f2937;
    border: 1px solid #d1d5db;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    margin-bottom: 1rem;
    transition: all 0.2s ease;
    font-weight: 500;
  }

  .recommendation-toggle:hover {
    background-color: #e5e7eb;
    border-color: #9ca3af;
  }

  .recommendations {
    background-color: #f0f9ff;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1.5rem;
  }

  .recommendations h5 {
    margin: 0 0 1rem 0;
    color: #1e40af;
    font-size: 1rem;
  }

  .recommendation-item {
    background-color: white;
    border: 1px solid #dbeafe;
    border-radius: 6px;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
  }

  .recommendation-item:last-child {
    margin-bottom: 0;
  }

  .rec-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .rec-header strong {
    color: #1f2937;
    font-size: 0.95rem;
  }

  .apply-btn {
    background-color: #3b82f6;
    color: white;
    border: none;
    padding: 0.25rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: background-color 0.2s ease;
  }

  .apply-btn:hover {
    background-color: #2563eb;
  }

  .rec-description {
    color: #6b7280;
    font-size: 0.875rem;
    margin: 0 0 0.25rem 0;
  }

  .rec-speakers {
    color: #374151;
    font-size: 0.875rem;
    margin: 0;
  }

  .sample-btn {
    background-color: #10b981;
    color: white;
    border: none;
    padding: 0.5rem;
    border-radius: 6px;
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.2s ease;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .sample-btn:hover {
    background-color: #059669;
    transform: scale(1.05);
  }

  .sample-btn:active {
    transform: scale(0.95);
  }

  .sample-btn:disabled {
    background-color: #9ca3af;
    cursor: not-allowed;
    transform: none;
  }

  .sample-btn.loading {
    background-color: #6b7280;
  }

  .spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    0% {
      transform: rotate(0deg);
    }
    100% {
      transform: rotate(360deg);
    }
  }

  select:disabled,
  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* 指示履歴スタイル */
  .history-toggle {
    background-color: #e0f2fe;
    color: #0369a1;
    border: 1px solid #7dd3fc;
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-left: auto;
  }

  .history-toggle:hover {
    background-color: #bae6fd;
    border-color: #38bdf8;
  }

  .instruction-history {
    background-color: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
  }

  .instruction-history h5 {
    margin: 0 0 0.75rem 0;
    color: #0369a1;
    font-size: 0.9rem;
    font-weight: 600;
  }

  .history-item {
    background-color: white;
    border: 1px solid #e0e7ff;
    border-radius: 6px;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
  }

  .history-item:last-child {
    margin-bottom: 0;
  }

  .history-timestamp {
    font-size: 0.75rem;
    color: #6b7280;
    margin-bottom: 0.25rem;
  }

  .history-instruction {
    color: #1f2937;
    font-size: 0.875rem;
    line-height: 1.5;
  }

  /* 画像クリック可能スタイル */
  .slide-thumbnail.clickable {
    cursor: pointer;
    transition: transform 0.2s ease;
  }

  .slide-thumbnail.clickable:hover {
    transform: scale(1.05);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
  }

  /* モーダルスタイル */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    cursor: pointer;
  }

  .modal-content {
    position: relative;
    max-width: 90vw;
    max-height: 90vh;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    cursor: default;
  }

  .modal-image {
    max-width: 100%;
    max-height: 90vh;
    border-radius: 8px;
    display: block;
  }

  .modal-close {
    position: absolute;
    top: -40px;
    right: 0;
    background-color: white;
    border: none;
    border-radius: 50%;
    width: 36px;
    height: 36px;
    font-size: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  .modal-close:hover {
    background-color: #f3f4f6;
    transform: scale(1.1);
  }

  /* APIキー警告ポップアップ */
  .api-key-warning {
    background-color: white;
    border-radius: 12px;
    padding: 2rem;
    max-width: 500px;
    box-shadow:
      0 20px 25px -5px rgba(0, 0, 0, 0.1),
      0 10px 10px -5px rgba(0, 0, 0, 0.04);
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .api-key-warning h2 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    color: #dc2626;
  }

  .api-key-warning p {
    margin-bottom: 1.5rem;
    color: #4b5563;
    line-height: 1.6;
  }

  .warning-actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
  }

  .warning-actions .primary-btn {
    background-color: #2563eb;
    color: white;
    padding: 0.75rem 2rem;
    border-radius: 8px;
    text-decoration: none;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    transition: background-color 0.3s ease;
  }

  .warning-actions .primary-btn:hover {
    background-color: #1d4ed8;
  }

  .warning-actions .secondary-btn {
    background-color: #e5e7eb;
    color: #4b5563;
    padding: 0.75rem 2rem;
    border-radius: 8px;
    border: none;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }

  .warning-actions .secondary-btn:hover {
    background-color: #d1d5db;
  }

  .back-to-settings-btn {
    background-color: #6b7280;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.3s ease;
  }

  .back-to-settings-btn:hover {
    background-color: #4b5563;
  }

  .dialogue-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 2rem;
    align-items: center;
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

  .csv-download-btn,
  .csv-upload-btn {
    background-color: #059669;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }

  .csv-download-btn:hover,
  .csv-upload-btn:hover {
    background-color: #047857;
  }

  .back-to-dialogue-btn {
    background-color: #3b82f6;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    cursor: pointer;
    transition: background-color 0.3s ease;
  }

  .back-to-dialogue-btn:hover {
    background-color: #2563eb;
  }
</style>
