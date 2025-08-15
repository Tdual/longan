from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Response, Request, status
import asyncio
import threading
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import json
from pathlib import Path
import shutil
import os
import csv
import io
from api.core.status_codes import StatusCode
from api.core.job_processor import JobProcessor
from api.core.async_worker import async_worker

# モデル定義
class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    status_code: str  # ステータスコード (PDF_PROCESSING, DIALOGUE_GENERATING, etc.)
    created_at: datetime
    updated_at: datetime
    progress: int  # 0-100
    result_url: Optional[str] = None
    error_code: Optional[str] = None  # エラーコード (FILE_NOT_FOUND, INVALID_FORMAT, etc.)
    estimated_duration: Optional[int] = None  # 推定動画時間（秒）
    target_duration: Optional[int] = None  # 目標動画時間（分）

class JobCreateResponse(BaseModel):
    job_id: str

class GenerateAudioRequest(BaseModel):
    job_id: str
    speed_scale: float = 1.0
    pitch_scale: float = 0.0
    intonation_scale: float = 1.2  # デフォルトで表現豊かに
    volume_scale: float = 1.0

class CreateVideoRequest(BaseModel):
    job_id: str
    slide_numbers: Optional[List[int]] = None  # 指定しない場合は全スライド

class GenerateDialogueRequest(BaseModel):
    job_id: str
    additional_prompt: Optional[str] = None  # AIへの追加指示
    continue_to_video: bool = False  # 対話生成後に音声・動画生成を続けるか

class UpdateDialogueRequest(BaseModel):
    job_id: str
    dialogue_data: Dict[str, List[Dict]]  # 編集された対話データ


# FastAPIアプリケーション
app = FastAPI(
    title="Gen Movie API", 
    version="1.0.0",
    # 大きなファイルのアップロードを許可（100MB）
    max_request_size=100 * 1024 * 1024
)

# アプリケーション起動時に設定を初期化
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    from api.core.settings_manager import SettingsManager
    # SettingsManagerを初期化することで.envファイルのチェックとコピーが実行される
    settings = SettingsManager()
    print("設定マネージャーを初期化しました")

# CORS設定（開発用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に設定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 仮のジョブストレージ（本番ではDynamoDBやRedis使用）
jobs_db = {}

# ファイルストレージパス（本番ではS3使用）
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Gen Movie API", "version": "1.0.0"}

# 認証関連のエンドポイント
class LoginRequest(BaseModel):
    password: str

class AuthStatusResponse(BaseModel):
    auth_enabled: bool
    authenticated: bool = False

@app.get("/api/auth/status")
async def get_auth_status(request: Request):
    """認証状態を取得"""
    return AuthStatusResponse(
        auth_enabled=auth_manager.is_auth_enabled(),
        authenticated=auth_manager.check_auth(request)
    )

@app.post("/api/auth/login")
async def login(login_request: LoginRequest):
    """ログイン"""
    if not auth_manager.is_auth_enabled():
        return {"success": True, "message": "認証は無効です", "token": None}
    
    if auth_manager.verify_password(login_request.password):
        return {"success": True, "message": "ログイン成功", "token": login_request.password}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="パスワードが正しくありません"
        )

from fastapi import Form

@app.post("/api/jobs/upload", response_model=JobCreateResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_duration: int = Form(10),  # デフォルト10分
    speaker1_id: int = Form(2),
    speaker1_name: str = Form("四国めたん"),
    speaker1_speed: float = Form(1.0),
    speaker2_id: int = Form(3),
    speaker2_name: str = Form("ずんだもん"),
    speaker2_speed: float = Form(1.0),
    conversation_style: str = Form("friendly"),
    conversation_style_prompt: str = Form(""),
    knowledge_file: UploadFile = File(None)  # ナレッジファイル
):
    """PDFファイルをアップロードしてジョブを作成"""
    
    # ファイル検証
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDFファイルのみ対応しています")
    
    # ファイルサイズ検証（100MB）
    if file.size and file.size > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="ファイルサイズが大きすぎます（最大100MB）")
    
    # ジョブID生成
    job_id = str(uuid.uuid4())
    
    # ファイル保存（本番ではS3に保存）
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    pdf_path = job_dir / file.filename
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # ナレッジファイルの処理
    knowledge_text = ""
    if knowledge_file and knowledge_file.filename:
        # ナレッジファイルを保存
        knowledge_path = job_dir / knowledge_file.filename
        with open(knowledge_path, "wb") as buffer:
            shutil.copyfileobj(knowledge_file.file, buffer)
        
        # ナレッジファイルからテキストを抽出
        try:
            knowledge_text = extract_text_from_knowledge_file(str(knowledge_path))
        except Exception as e:
            print(f"ナレッジファイルの処理エラー: {e}")
            knowledge_text = ""
    
    # ジョブ情報を保存
    job_status = JobStatus(
        job_id=job_id,
        status="pending",
        status_code=StatusCode.PDF_UPLOADING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        progress=0,
        target_duration=target_duration
    )
    jobs_db[job_id] = job_status
    
    # メタデータを保存（目安時間とキャラクター設定）
    metadata = {
        "target_duration": target_duration,
        "speaker1": {"id": speaker1_id, "name": speaker1_name, "speed": speaker1_speed},
        "speaker2": {"id": speaker2_id, "name": speaker2_name, "speed": speaker2_speed},
        "conversation_style": conversation_style,
        "conversation_style_prompt": conversation_style_prompt,
        "additional_knowledge": knowledge_text
    }
    metadata_file = job_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # 目安時間をファイルに保存（後方互換性のため）
    target_duration_file = job_dir / "target_duration.txt"
    with open(target_duration_file, "w") as f:
        f.write(str(target_duration))
    
    # バックグラウンドでPDF変換を実行（本番ではBatchジョブ起動）
    def run_in_thread():
        asyncio.run(convert_pdf_to_slides(job_id, str(pdf_path), target_duration, metadata))
    
    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True
    thread.start()
    
    return JobCreateResponse(
        job_id=job_id
    )

@app.get("/api/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """ジョブのステータスを取得"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    return jobs_db[job_id]

@app.post("/api/jobs/{job_id}/generate-audio")
async def generate_audio(
    job_id: str,
    request: GenerateAudioRequest,
    background_tasks: BackgroundTasks
):
    """音声生成を開始"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    job = jobs_db[job_id]
    
    if job.status not in ["slides_ready", "dialogue_ready"]:
        raise HTTPException(
            status_code=400, 
            detail="スライド変換または対話スクリプトの準備が完了していません"
        )
    
    # ステータス更新
    job.status = "generating_audio"
    job.status_code = StatusCode.AUDIO_GENERATING
    job.progress = 30
    job.updated_at = datetime.now()
    
    # バックグラウンドで音声生成（本番ではBatchジョブ）
    background_tasks.add_task(
        generate_audio_task, 
        job_id,
        request.speed_scale,
        request.pitch_scale,
        request.intonation_scale,
        request.volume_scale
    )
    
    return {"message": "音声生成を開始しました"}

@app.post("/api/jobs/{job_id}/create-video")
async def create_video(
    job_id: str,
    request: CreateVideoRequest,
    background_tasks: BackgroundTasks
):
    """動画作成を開始"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    job = jobs_db[job_id]
    
    if job.status != "audio_ready":
        raise HTTPException(
            status_code=400, 
            detail="音声生成が完了していません"
        )
    
    # ステータス更新
    job.status = "creating_video"
    job.status_code = StatusCode.VIDEO_CREATING
    job.progress = 70
    job.updated_at = datetime.now()
    
    # バックグラウンドで動画作成（本番ではBatchジョブ）
    background_tasks.add_task(
        create_video_task,
        job_id,
        request.slide_numbers
    )
    
    return {"message": "動画作成を開始しました"}

@app.get("/api/jobs/{job_id}/download")
async def download_video(job_id: str):
    """完成した動画をダウンロード"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    job = jobs_db[job_id]
    
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="動画が完成していません"
        )
    
    video_path = OUTPUT_DIR / f"{job_id}.mp4"
    
    if not video_path.exists():
        raise HTTPException(
            status_code=404,
            detail="動画ファイルが見つかりません"
        )
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"video_{job_id}.mp4"
    )

@app.post("/api/jobs/{job_id}/generate-dialogue")
async def generate_dialogue_only(
    job_id: str,
    request: GenerateDialogueRequest,
    background_tasks: BackgroundTasks
):
    """対話スクリプトのみを生成（動画は作成しない）"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    job = jobs_db[job_id]
    
    if job.status not in ["slides_ready", "dialogue_ready", "completed"]:
        if job.status == "generating_dialogue":
            print(f"エラー: 対話生成が進行中です。ジョブID: {job_id}, ステータス: {job.status}")
            raise HTTPException(
                status_code=400, 
                detail="対話生成が進行中です。完了までお待ちください。"
            )
        elif job.status == "failed":
            print(f"エラー: 前回の処理が失敗しています。ジョブID: {job_id}, エラー: {job.error}")
            raise HTTPException(
                status_code=400,
                detail=f"前回の処理が失敗しています: {job.error}"
            )
        else:
            print(f"エラー: 対話生成できない状態です。ジョブID: {job_id}, ステータス: {job.status}")
            raise HTTPException(
                status_code=400, 
                detail=f"対話生成できない状態です: {job.status}"
            )
    
    # 再生成の場合はタスクIDにタイムスタンプを付けて重複を避ける
    import time
    if request.additional_prompt:
        task_id = f"dialogue_regen_{job_id}_{int(time.time())}"
    else:
        task_id = f"dialogue_{job_id}"
    
    # 既に同じジョブが実行中かチェック（初回生成の場合のみ）
    if not request.additional_prompt and async_worker.is_task_running(task_id):
        raise HTTPException(
            status_code=409, 
            detail="対話生成が既に実行中です"
        )
    
    # ステータス更新
    job.status = "generating_dialogue"
    job.status_code = StatusCode.DIALOGUE_GENERATING
    job.progress = 30
    job.updated_at = datetime.now()
    
    # 非同期ワーカーで対話生成
    await async_worker.submit_task(
        task_id,
        JobProcessor.generate_dialogue_sync,
        job_id, request.additional_prompt, jobs_db, request.continue_to_video
    )
    
    return {"message": "対話スクリプト生成を開始しました（非同期処理）", "job_id": job_id}

@app.get("/api/jobs/{job_id}/slides")
async def get_slides(job_id: str):
    """スライド画像のリストを取得"""
    
    slides_dir = Path.cwd() / "slides" / job_id
    
    if not slides_dir.exists():
        raise HTTPException(status_code=404, detail="スライドが見つかりません")
    
    slides = []
    for slide_path in sorted(slides_dir.glob("slide_*.png")):
        slide_num = int(slide_path.stem.split("_")[1])
        slides.append({
            "slide_number": slide_num,
            "url": f"/api/jobs/{job_id}/slides/{slide_num}"
        })
    
    return slides

@app.get("/api/jobs/{job_id}/slides/{slide_number}")
async def get_slide_image(job_id: str, slide_number: int):
    """特定のスライド画像を取得"""
    
    slide_path = Path.cwd() / "slides" / job_id / f"slide_{slide_number:03d}.png"
    
    if not slide_path.exists():
        raise HTTPException(status_code=404, detail="スライド画像が見つかりません")
    
    return FileResponse(
        path=slide_path,
        media_type="image/png"
    )

@app.get("/api/jobs/{job_id}/dialogue")
async def get_dialogue(job_id: str):
    """生成された対話スクリプトを取得"""
    
    # 今後はオリジナルデータに直接カタカナが含まれるため、オリジナルを読み込む
    dialogue_path = Path.cwd() / "data" / job_id / "dialogue_narration_original.json"
    
    if not dialogue_path.exists():
        raise HTTPException(status_code=404, detail="対話スクリプトが見つかりません")
    
    with open(dialogue_path, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # 動画時間の概算を計算
    total_seconds = estimate_video_duration(dialogue_data)
    
    return {
        "dialogue_data": dialogue_data,
        "estimated_duration": {
            "seconds": total_seconds,
            "formatted": format_duration(total_seconds)
        }
    }

@app.get("/api/jobs/{job_id}/metadata")
async def get_job_metadata(job_id: str):
    """ジョブのメタデータを取得"""
    
    metadata_path = UPLOAD_DIR / job_id / "metadata.json"
    
    if not metadata_path.exists():
        # デフォルト値を返す
        return {
            "speaker1": {"id": 2, "name": "四国めたん"},
            "speaker2": {"id": 3, "name": "ずんだもん"},
            "target_duration": 10
        }
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)

@app.get("/api/jobs/{job_id}/instruction-history")
async def get_instruction_history(job_id: str):
    """指示履歴を取得"""
    from api.core.instruction_history import InstructionHistory
    
    history = InstructionHistory(job_id, Path.cwd())
    return {"history": history.history}

@app.get("/api/jobs/{job_id}/dialogue/csv")
async def download_dialogue_csv(job_id: str):
    """対話スクリプトをCSV形式でダウンロード"""
    
    dialogue_path = Path.cwd() / "data" / job_id / "dialogue_narration_original.json"
    
    if not dialogue_path.exists():
        raise HTTPException(status_code=404, detail="対話スクリプトが見つかりません")
    
    with open(dialogue_path, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # CSV作成
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer, quoting=csv.QUOTE_MINIMAL)
    
    # ヘッダー
    csv_writer.writerow(['会話番号', 'スライド番号', '発話者名', 'テキスト'])
    
    # データ
    conversation_num = 0
    for slide_key in sorted(dialogue_data.keys(), key=lambda x: int(x.split('_')[1])):
        slide_num = slide_key.split('_')[1]
        dialogues = dialogue_data[slide_key]
        
        for dialogue in dialogues:
            conversation_num += 1
            # メタデータから現在のキャラクター設定を取得
            metadata_path = Path.cwd() / "uploads" / job_id / "metadata.json"
            speaker1_name = "四国めたん"
            speaker2_name = "ずんだもん"
            
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    speaker1_name = metadata.get("speaker1", {}).get("name", "四国めたん")
                    speaker2_name = metadata.get("speaker2", {}).get("name", "ずんだもん")
            
            # speaker1/speaker2形式の場合と、古いmetan/zundamon形式の両方に対応
            if dialogue['speaker'] == 'speaker1' or dialogue['speaker'] == 'metan':
                speaker_display = speaker1_name
            elif dialogue['speaker'] == 'speaker2' or dialogue['speaker'] == 'zundamon':
                speaker_display = speaker2_name
            else:
                speaker_display = dialogue['speaker']  # フォールバック
            csv_writer.writerow([
                conversation_num,
                slide_num,
                speaker_display,
                dialogue['text']
            ])
    
    # CSVをバイトに変換
    csv_content = csv_buffer.getvalue().encode('utf-8-sig')  # BOM付きUTF-8
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=dialogue_{job_id}.csv"
        }
    )

@app.post("/api/jobs/{job_id}/dialogue/csv")
async def upload_dialogue_csv(
    job_id: str,
    file: UploadFile = File(...)
):
    """CSVファイルから対話スクリプトをアップロード"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    # ファイル検証
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="CSVファイルのみ対応しています")
    
    # CSVを読み込む
    content = await file.read()
    
    # エンコーディングを検出して読み込み
    try:
        # まずUTF-8-BOMを試す
        csv_text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            # 次にUTF-8を試す
            csv_text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # Shift-JISを試す
                csv_text = content.decode('shift-jis')
            except UnicodeDecodeError:
                try:
                    # CP932（Windows-31J）を試す
                    csv_text = content.decode('cp932')
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="CSVファイルのエンコーディングが不正です（UTF-8、Shift-JIS、またはCP932を使用してください）")
    
    # CSVをパース（DictReaderを使用してヘッダーを正しく処理）
    csv_reader = csv.DictReader(io.StringIO(csv_text))
    
    # データを検証して読み込み
    dialogue_data = {}
    errors = []
    
    for line_num, row in enumerate(csv_reader, start=2):  # ヘッダーの次から
        # 必要な列が存在するか確認
        required_columns = ['会話番号', 'スライド番号', '発話者名', 'テキスト']
        missing_columns = [col for col in required_columns if col not in row]
        if missing_columns:
            errors.append(f"行{line_num}: 必要な列がありません: {', '.join(missing_columns)}")
            continue
        
        conversation_num = row.get('会話番号', '').strip()
        slide_num = row.get('スライド番号', '').strip()
        speaker_display = row.get('発話者名', '').strip()
        text = row.get('テキスト', '').strip()
        
        # 会話番号の検証（順番チェックはしない）
        try:
            conversation_num_int = int(conversation_num)
            if conversation_num_int < 1:
                errors.append(f"行{line_num}: 会話番号は1以上である必要があります")
                continue
        except ValueError:
            errors.append(f"行{line_num}: 会話番号が数値ではありません: {conversation_num}")
            continue
        
        # スライド番号の検証
        try:
            slide_num_int = int(slide_num)
            if slide_num_int < 1:
                errors.append(f"行{line_num}: スライド番号は1以上である必要があります")
                continue
        except ValueError:
            errors.append(f"行{line_num}: スライド番号が数値ではありません: {slide_num}")
            continue
        
        # 話者の検証と変換
        # メタデータから現在のキャラクター設定を取得
        metadata_path = UPLOAD_DIR / job_id / "metadata.json"
        speaker1_name = "四国めたん"
        speaker2_name = "ずんだもん"
        
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                speaker1_name = metadata.get("speaker1", {}).get("name", "四国めたん")
                speaker2_name = metadata.get("speaker2", {}).get("name", "ずんだもん")
        
        # デバッグ用ログ
        print(f"CSVインポート: 話者判定 - speaker1: {speaker1_name}, speaker2: {speaker2_name}, 入力: {speaker_display.strip()}")
        
        # 話者名の判定を柔軟にする（部分一致も許可）
        if speaker1_name in speaker_display.strip() or speaker_display.strip() in speaker1_name:
            speaker = 'speaker1'
        elif speaker2_name in speaker_display.strip() or speaker_display.strip() in speaker2_name:
            speaker = 'speaker2'
        # speaker1/speaker2形式も受け入れる
        elif speaker_display.strip().lower() in ['speaker1', 'キャラ1', 'キャラクター1']:
            speaker = 'speaker1'
        elif speaker_display.strip().lower() in ['speaker2', 'キャラ2', 'キャラクター2']:
            speaker = 'speaker2'
        else:
            errors.append(f"行{line_num}: 発話者名が不正です（'{speaker1_name}'または'{speaker2_name}'である必要があります）: '{speaker_display}'")
            continue
        
        # テキストの検証
        if not text.strip():
            errors.append(f"行{line_num}: テキストが空です")
            continue
        
        # スライドキーを生成
        slide_key = f"slide_{slide_num_int}"
        
        # データを追加
        if slide_key not in dialogue_data:
            dialogue_data[slide_key] = []
        
        dialogue_data[slide_key].append({
            "speaker": speaker,
            "text": text.strip()
        })
    
    # エラーがある場合は返す
    if errors:
        error_message = "CSVファイルに以下のエラーがあります:\n" + "\n".join(errors[:10])  # 最初の10個のエラーのみ
        if len(errors) > 10:
            error_message += f"\n... 他{len(errors)-10}個のエラー"
        raise HTTPException(status_code=400, detail=error_message)
    
    # 対話データがない場合
    if not dialogue_data:
        raise HTTPException(status_code=400, detail="有効な対話データが含まれていません")
    
    # データを保存
    data_dir = Path.cwd() / "data" / job_id
    data_dir.mkdir(exist_ok=True)
    
    dialogue_path = data_dir / "dialogue_narration_original.json"
    with open(dialogue_path, 'w', encoding='utf-8') as f:
        json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
    
    # 互換性のためkatakanaファイルも同じ内容で保存
    katakana_path = data_dir / "dialogue_narration_katakana.json"
    with open(katakana_path, 'w', encoding='utf-8') as f:
        json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
    
    # 既存の音声ファイルを削除（新しいスクリプトで再生成が必要）
    audio_dir = Path.cwd() / "audio" / job_id
    if audio_dir.exists():
        import shutil
        shutil.rmtree(audio_dir)
        print(f"既存の音声ファイルを削除しました: {audio_dir}")
    
    # ジョブステータスを更新
    job = jobs_db[job_id]
    job.status = "dialogue_ready"
    job.status_code = StatusCode.DIALOGUE_COMPLETED  # 音声生成が必要なことを示す
    job.updated_at = datetime.now()
    
    # 推定時間を再計算
    total_seconds = estimate_video_duration(dialogue_data)
    
    return {
        "message": f"対話スクリプトをインポートしました（{len(dialogue_data)}スライド）", 
        "slide_count": len(dialogue_data),
        "estimated_duration": {
            "seconds": total_seconds,
            "formatted": format_duration(total_seconds)
        }
    }

@app.put("/api/jobs/{job_id}/dialogue")
async def update_dialogue(
    job_id: str,
    request: UpdateDialogueRequest
):
    """対話スクリプトを更新"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    # 対話データを保存
    data_dir = Path.cwd() / "data" / job_id
    data_dir.mkdir(exist_ok=True)
    
    dialogue_path = data_dir / "dialogue_narration_original.json"
    katakana_path = data_dir / "dialogue_narration_katakana.json"
    
    # 受け取ったデータをそのまま保存（AIが既にカタカナで生成）
    with open(dialogue_path, 'w', encoding='utf-8') as f:
        json.dump(request.dialogue_data, f, ensure_ascii=False, indent=2)
    
    # 互換性のためkatakanaファイルも同じ内容で保存
    with open(katakana_path, 'w', encoding='utf-8') as f:
        json.dump(request.dialogue_data, f, ensure_ascii=False, indent=2)
    
    # 既存の音声ファイルを削除（新しいスクリプトで再生成が必要）
    audio_dir = Path.cwd() / "audio" / job_id
    if audio_dir.exists():
        import shutil
        shutil.rmtree(audio_dir)
        print(f"既存の音声ファイルを削除しました: {audio_dir}")
    
    # ジョブステータスを更新
    job = jobs_db[job_id]
    job.status = "dialogue_ready"
    job.status_code = StatusCode.DIALOGUE_COMPLETED  # 音声生成が必要なことを示す
    job.updated_at = datetime.now()
    
    # 推定時間を再計算
    total_seconds = estimate_video_duration(request.dialogue_data)
    
    return {
        "message": "対話スクリプトを更新しました",
        "estimated_duration": {
            "seconds": total_seconds,
            "formatted": format_duration(total_seconds)
        }
    }

@app.post("/api/jobs/{job_id}/generate-video")
async def generate_video_complete(
    job_id: str,
    background_tasks: BackgroundTasks
):
    """ワンクリック動画生成（全工程を自動実行・非同期処理）"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    job = jobs_db[job_id]
    
    if job.status not in ["pending", "slides_ready", "dialogue_ready"]:
        raise HTTPException(
            status_code=400, 
            detail="ジョブが適切な状態ではありません"
        )
    
    # 既に同じジョブが実行中かチェック
    if async_worker.is_task_running(f"complete_{job_id}"):
        raise HTTPException(
            status_code=409, 
            detail="このジョブは既に処理中です"
        )
    
    # ステータス更新
    job.status = "processing"
    job.status_code = StatusCode.PROCESSING
    job.progress = 5
    job.updated_at = datetime.now()
    
    # 非同期で全工程を実行（直接呼び出し）
    asyncio.create_task(JobProcessor.process_complete_video_async(job_id, jobs_db))
    
    return {"message": "動画生成を開始しました（非同期処理）", "job_id": job_id}

@app.get("/api/jobs", response_model=List[JobStatus])
async def list_jobs():
    """全ジョブのリストを取得"""
    return list(jobs_db.values())

@app.get("/api/system/status")
async def get_system_status():
    """システム状態を取得"""
    running_tasks = async_worker.get_running_tasks()
    return {
        "running_tasks": running_tasks,
        "active_jobs": len([job for job in jobs_db.values() if job.status == "processing"]),
        "total_jobs": len(jobs_db),
        "worker_capacity": async_worker.max_workers
    }

@app.get("/api/speakers")
async def get_speakers():
    """利用可能なVOICEVOXスピーカー一覧を取得"""
    import requests
    
    # Docker環境の場合はvoicevoxホスト名を使用
    if os.path.exists("/.dockerenv"):
        voicevox_url = "http://voicevox:50021"
    else:
        voicevox_url = os.getenv("VOICEVOX_URL", "http://localhost:50021")
    
    try:
        response = requests.get(f"{voicevox_url}/speakers", timeout=5)
        response.raise_for_status()
        speakers = response.json()
        
        # フロントエンドで使いやすい形式に整形
        formatted_speakers = []
        for speaker in speakers:
            for style in speaker['styles']:
                formatted_speakers.append({
                    "speaker_name": speaker['name'],
                    "speaker_uuid": speaker['speaker_uuid'],
                    "style_name": style['name'],
                    "style_id": style['id'],
                    "display_name": f"{speaker['name']} ({style['name']})"
                })
        
        return formatted_speakers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VOICEVOXへの接続に失敗しました: {str(e)}")

class VoiceSampleRequest(BaseModel):
    speaker_id: int
    speaker_name: Optional[str] = None
    speed: Optional[float] = None
    text: str

@app.post("/api/voice-sample")
async def generate_voice_sample(request: VoiceSampleRequest):
    """指定したスピーカーでサンプル音声を生成"""
    import requests
    
    voicevox_url = os.getenv("VOICEVOX_URL", "http://localhost:50021")
    
    try:
        # 音声クエリの作成
        query_response = requests.post(
            f"{voicevox_url}/audio_query",
            params={
                "text": request.text,
                "speaker": request.speaker_id
            }
        )
        query_response.raise_for_status()
        
        # 音声合成パラメータを調整
        synthesis_data = query_response.json()
        
        # 速度調整
        if request.speed:
            synthesis_data["speedScale"] = request.speed
        elif request.speaker_name == "九州そら":
            # 速度が指定されていない場合、九州そらはデフォルトで1.2倍速
            synthesis_data["speedScale"] = 1.2
        
        # 音声合成
        synthesis_response = requests.post(
            f"{voicevox_url}/synthesis",
            params={"speaker": request.speaker_id},
            json=synthesis_data
        )
        synthesis_response.raise_for_status()
        
        return Response(
            content=synthesis_response.content,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"inline; filename=sample_{request.speaker_id}.wav"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音声生成に失敗しました: {str(e)}")

@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """ジョブを削除"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    # ファイル削除（本番ではS3から削除）
    job_dir = UPLOAD_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
    
    output_file = OUTPUT_DIR / f"{job_id}.mp4"
    if output_file.exists():
        output_file.unlink()
    
    # ジョブ情報削除
    del jobs_db[job_id]
    
    return {"message": "ジョブを削除しました"}

# LLMプロバイダー設定関連のエンドポイント
@app.get("/api/settings/providers")
async def get_providers():
    """利用可能なLLMプロバイダーの一覧と状態を取得"""
    settings_manager = SettingsManager()
    
    # 利用可能なプロバイダー
    available_providers = LLMFactory.get_available_providers()
    
    # APIキーの状態
    key_status = settings_manager.get_all_keys_status()
    
    # 現在の設定
    settings = settings_manager.get_settings()
    
    # 結果を統合
    providers = []
    for provider_info in available_providers:
        provider_id = provider_info["id"]
        status = key_status.get(provider_id.value, {})
        
        providers.append({
            "id": provider_id.value,
            "name": provider_info["name"],
            "models": provider_info["models"],
            "configured": status.get("configured", False),
            "masked_key": status.get("masked_key"),
            "key_source": status.get("source"),
            "requires_region": provider_info.get("requires_region", False),
            "region": status.get("region") if provider_id.value == "bedrock" else None
        })
    
    return {
        "providers": providers,
        "default_provider": settings.get("default_provider"),
        "default_models": settings.get("default_model"),
        "temperature": settings.get("temperature"),
        "max_tokens": settings.get("max_tokens")
    }

class ProviderConfig(BaseModel):
    provider: str
    api_key: str
    region: Optional[str] = None  # AWS Bedrockの場合
    model: Optional[str] = None

@app.post("/api/settings/provider")
async def save_provider_config(config: ProviderConfig):
    """プロバイダーの設定とAPIキーを保存"""
    settings_manager = SettingsManager()
    
    # APIキーを保存
    settings_manager.save_api_key(config.provider, config.api_key)
    
    # AWS Bedrockの場合はリージョンも保存
    if config.provider == "bedrock" and config.region:
        # 環境変数に設定（一時的）
        os.environ["AWS_DEFAULT_REGION"] = config.region
    
    # デフォルトプロバイダーとして設定
    settings = settings_manager.get_settings()
    settings["default_provider"] = config.provider
    if config.model:
        if "default_model" not in settings:
            settings["default_model"] = {}
        settings["default_model"][config.provider] = config.model
    settings_manager.save_settings(settings)
    
    return {"message": "プロバイダー設定を保存しました"}

@app.delete("/api/settings/provider/{provider}")
async def delete_provider_config(provider: str):
    """プロバイダーの設定を削除"""
    settings_manager = SettingsManager()
    
    # APIキーを削除
    settings_manager.delete_api_key(provider)
    
    # デフォルトプロバイダーだった場合は変更
    settings = settings_manager.get_settings()
    if settings.get("default_provider") == provider:
        # 他の設定済みプロバイダーを探す
        key_status = settings_manager.get_all_keys_status()
        for other_provider, status in key_status.items():
            if other_provider != provider and status.get("configured"):
                settings["default_provider"] = other_provider
                break
        else:
            # 設定済みプロバイダーがない場合はOpenAIをデフォルトに
            settings["default_provider"] = "openai"
    
    settings_manager.save_settings(settings)
    
    return {"message": "プロバイダー設定を削除しました"}

class TestKeyRequest(BaseModel):
    provider: str
    api_key: str
    region: Optional[str] = None  # AWS Bedrockの場合

@app.post("/api/settings/test-key")
async def test_api_key(request: TestKeyRequest):
    """APIキーの有効性をテスト"""
    settings_manager = SettingsManager()
    
    # AWS Bedrockの場合は一時的にリージョンを設定
    if request.provider == "bedrock" and request.region:
        old_region = os.environ.get("AWS_DEFAULT_REGION")
        os.environ["AWS_DEFAULT_REGION"] = request.region
    
    try:
        result = await settings_manager.test_api_key(request.provider, request.api_key, request.region)
        return result
    finally:
        # AWS Bedrockのリージョンを元に戻す
        if request.provider == "bedrock" and request.region:
            if old_region:
                os.environ["AWS_DEFAULT_REGION"] = old_region
            else:
                os.environ.pop("AWS_DEFAULT_REGION", None)

class SettingsUpdate(BaseModel):
    default_provider: Optional[str] = None
    default_model: Optional[Dict[str, str]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

@app.put("/api/settings")
async def update_settings(update: SettingsUpdate):
    """全般的な設定を更新"""
    settings_manager = SettingsManager()
    settings = settings_manager.get_settings()
    
    if update.default_provider is not None:
        settings["default_provider"] = update.default_provider
    if update.default_model is not None:
        settings["default_model"] = update.default_model
    if update.temperature is not None:
        settings["temperature"] = update.temperature
    if update.max_tokens is not None:
        settings["max_tokens"] = update.max_tokens
    
    settings_manager.save_settings(settings)
    
    return {"message": "設定を更新しました"}

# コア機能のインポート
from api.core.pdf_processor import PDFProcessor
from api.core.audio_generator import AudioGenerator
from api.core.video_creator import VideoCreator
from api.core.settings_manager import SettingsManager
from api.core.llm_provider import LLMFactory, LLMProvider
from api.core.auth import auth_manager, require_auth
from api.core.knowledge_extractor import extract_text_from_knowledge_file

# バックグラウンドタスク（本番ではAWS Batchで実行）
async def convert_pdf_to_slides(job_id: str, pdf_path: str, target_duration: int = 10, metadata: dict = None):
    """PDFをスライド画像に変換"""
    try:
        job = jobs_db[job_id]
        job.progress = 10
        job.status_code = StatusCode.PDF_PROCESSING
        
        # PDFをスライドに変換
        processor = PDFProcessor(job_id, Path.cwd())
        slide_count = processor.convert_pdf_to_slides(pdf_path)
        
        job.progress = 15
        job.updated_at = datetime.now()
        
        # 進捗更新用のコールバック
        def update_progress(message: str, progress: float):
            # PDFからスライド変換が15%まで、対話生成が15-95%の範囲
            job.progress = 15 + int(progress * 0.8)  # 15-95%の範囲で進捗表示
            job.updated_at = datetime.now()
        
        # メタデータがある場合はスピーカー情報と会話スタイル、ナレッジを取得
        speaker_info = None
        conversation_style_prompt = None
        additional_knowledge = None
        if metadata:
            speaker_info = {
                'speaker1': metadata.get('speaker1'),
                'speaker2': metadata.get('speaker2')
            }
            conversation_style_prompt = metadata.get('conversation_style_prompt', '')
            additional_knowledge = metadata.get('additional_knowledge', '')
        
        # プロンプトを結合（会話スタイル + ナレッジ）
        combined_prompt = conversation_style_prompt
        if additional_knowledge:
            # 会話スタイルとナレッジがある場合は結合
            if combined_prompt:
                combined_prompt = f"{combined_prompt}\n\n{additional_knowledge}"
            else:
                combined_prompt = additional_knowledge
        
        # 対話データを生成（目安時間とスピーカー情報、会話スタイルを渡す）
        job.status_code = StatusCode.DIALOGUE_GENERATING
        dialogue_path = await processor.generate_dialogue_from_pdf(
            pdf_path, 
            additional_prompt=combined_prompt,
            progress_callback=update_progress, 
            target_duration=target_duration,
            speaker_info=speaker_info,
            additional_knowledge=additional_knowledge
        )
        
        job.status = "slides_ready"
        job.status_code = StatusCode.DIALOGUE_COMPLETED
        job.progress = 50
        job.updated_at = datetime.now()
        
        # 音声と動画生成を続ける
        await generate_complete_video(job_id)
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in convert_pdf_to_slides: {error_msg}")
        job = jobs_db[job_id]
        job.status = "failed"
        job.status_code = StatusCode.FAILED
        job.error_code = StatusCode.PDF_PROCESSING_ERROR
        job.updated_at = datetime.now()

async def generate_dialogue_task(job_id: str, additional_prompt: Optional[str] = None, is_regeneration: bool = False):
    """対話スクリプトのみを生成するタスク"""
    try:
        job = jobs_db[job_id]
        
        # PDFファイルパスを取得
        job_dir = UPLOAD_DIR / job_id
        pdf_files = list(job_dir.glob("*.pdf"))
        if not pdf_files:
            raise Exception("PDFファイルが見つかりません")
        
        pdf_path = str(pdf_files[0])
        
        # PDFを処理（スライドは既に生成済みの場合はスキップ）
        processor = PDFProcessor(job_id, Path.cwd())
        
        # 対話データ生成（追加プロンプトがあれば渡す）
        job.progress = 50
        job.updated_at = datetime.now()
        
        # 進捗更新用のコールバック
        def update_progress(message: str, progress: float):
            # 再生成の場合は0-95%の範囲で進捗表示
            job.progress = int(progress * 0.95)
            job.updated_at = datetime.now()
        
        # メタデータを読み込む
        metadata = None
        speaker_info = None
        target_duration = 10  # デフォルト
        additional_knowledge = None
        
        metadata_file = job_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                target_duration = metadata.get("target_duration", 10)
                speaker_info = {
                    'speaker1': metadata.get('speaker1'),
                    'speaker2': metadata.get('speaker2')
                }
                additional_knowledge = metadata.get('additional_knowledge', '')
        else:
            # 互換性のため古い形式も確認
            target_duration_file = job_dir / "target_duration.txt"
            if target_duration_file.exists():
                with open(target_duration_file, "r") as f:
                    target_duration = int(f.read().strip())
        
        if is_regeneration and additional_prompt:
            from api.core.text_extractor import TextExtractor
            from api.core.dialogue_generator import DialogueGenerator
            from api.core.instruction_history import InstructionHistory
            
            # 再生成の場合、どのスライドを再生成するか判断
            dialogue_generator = DialogueGenerator()
            text_extractor = TextExtractor()
            slide_texts = text_extractor.extract_text_from_pdf(pdf_path)
            
            # AIに判断させる
            target_slides = await dialogue_generator.analyze_regeneration_request(
                additional_prompt, 
                len(slide_texts)
            )
            
            # 指示履歴を管理
            history = InstructionHistory(job_id, Path.cwd())
            history.add_instruction(target_slides, additional_prompt)
            
            # 既存の対話データを読み込む
            existing_dialogue_path = Path.cwd() / "data" / job_id / "dialogue_narration_original.json"
            if existing_dialogue_path.exists():
                with open(existing_dialogue_path, 'r', encoding='utf-8') as f:
                    existing_dialogues = json.load(f)
            else:
                existing_dialogues = {}
            
            # 特定のスライドのみ再生成
            dialogue_data = await dialogue_generator.regenerate_specific_slides(
                slide_texts,
                existing_dialogues,
                target_slides,
                additional_prompt,
                progress_callback=update_progress,
                instruction_history=history,
                target_duration=target_duration,
                speaker_info=speaker_info,
                additional_knowledge=additional_knowledge
            )
            
            # データを保存
            data_dir = Path.cwd() / "data" / job_id
            data_dir.mkdir(exist_ok=True)
            
            dialogue_path = data_dir / "dialogue_narration_original.json"
            with open(dialogue_path, 'w', encoding='utf-8') as f:
                json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
            
            # 互換性のためkatakanaファイルも同じ内容で保存
            katakana_path = data_dir / "dialogue_narration_katakana.json"
            with open(katakana_path, 'w', encoding='utf-8') as f:
                json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
            
            # 推定時間を計算して保存
            total_seconds = estimate_video_duration(dialogue_data)
            job.estimated_duration = total_seconds
        else:
            # 通常の生成
            # メタデータから会話スタイルプロンプトを取得
            conversation_style_prompt = metadata.get('conversation_style_prompt', '') if metadata else ''
            if additional_prompt:
                # 追加プロンプトがある場合は結合
                full_prompt = f"{conversation_style_prompt}\n\n{additional_prompt}" if conversation_style_prompt else additional_prompt
            else:
                full_prompt = conversation_style_prompt
            
            dialogue_path = await processor.generate_dialogue_from_pdf(
                pdf_path, 
                additional_prompt=full_prompt,
                progress_callback=update_progress,
                target_duration=target_duration,
                speaker_info=speaker_info,
                additional_knowledge=additional_knowledge
            )
            
            # 推定時間を計算して保存
            with open(dialogue_path, 'r', encoding='utf-8') as f:
                dialogue_data = json.load(f)
            total_seconds = estimate_video_duration(dialogue_data)
            job.estimated_duration = total_seconds
        
        # 完了
        job.status = "dialogue_ready"
        job.status_code = StatusCode.COMPLETED
        job.progress = 100
        job.error_code = None  # エラーコードをクリアして過去のエラー表示を防ぐ
        job.updated_at = datetime.now()
        
    except Exception as e:
        job = jobs_db[job_id]
        job.status = "failed"
        job.status_code = StatusCode.FAILED
        job.error_code = StatusCode.DIALOGUE_GENERATION_ERROR
        job.updated_at = datetime.now()

async def generate_complete_video(job_id: str):
    """完全な動画生成フロー（全工程を自動実行）"""
    try:
        job = jobs_db[job_id]
        
        # 1. PDFをスライドに変換（必要な場合のみ）
        slides_dir = Path.cwd() / "slides" / job_id
        if not slides_dir.exists() or not list(slides_dir.glob("slide_*.png")):
            job.status_code = StatusCode.PDF_PROCESSING
            job.progress = 10
            job.updated_at = datetime.now()
            
            # PDFファイルパスを取得
            job_dir = UPLOAD_DIR / job_id
            pdf_files = list(job_dir.glob("*.pdf"))
            if not pdf_files:
                raise Exception("PDFファイルが見つかりません")
            
            pdf_path = str(pdf_files[0])
            
            # PDFを処理
            job.status_code = StatusCode.PDF_GENERATING_SLIDES
            job.progress = 15
            job.updated_at = datetime.now()
            
            processor = PDFProcessor(job_id, Path.cwd())
            slide_count = processor.convert_pdf_to_slides(pdf_path)
        else:
            # 既存のスライドを使用
            job.progress = 20
            job.updated_at = datetime.now()
            slide_count = len(list(slides_dir.glob("slide_*.png")))
            print(f"既存のスライドを使用: {slide_count}枚")
        
        # 2. 対話データの確認・生成
        data_dir = Path.cwd() / "data" / job_id
        dialogue_path = data_dir / "dialogue_narration_original.json"
        
        # 既に対話データが存在するかチェック
        if not dialogue_path.exists():
            job.status_code = StatusCode.DIALOGUE_GENERATING
            job.progress = 25
            job.updated_at = datetime.now()
            
            # 進捗更新用のコールバック
            def update_progress(message: str, progress: float):
                if "生成中" in message:
                    job.status_code = StatusCode.DIALOGUE_PROCESSING
                job.progress = 25 + int(progress * 0.35)  # 25-60%の範囲で進捗表示
                job.updated_at = datetime.now()
            
            # ジョブから目標時間を取得
            target_duration = job.target_duration or 10  # デフォルト10分
            
            # メタデータからスピーカー情報を取得
            metadata_path = job_dir / "metadata.json"
            metadata = None
            speaker_info = None
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    speaker_info = metadata.get('speakers', {})
            
            dialogue_path = processor.generate_dialogue_from_pdf(
                pdf_path, 
                progress_callback=update_progress,
                target_duration=target_duration,
                speaker_info=speaker_info
            )
        else:
            # 既存の対話データを使用
            job.progress = 60
            job.updated_at = datetime.now()
            print(f"既存の対話データを使用: {dialogue_path}")
        
        # 3. 音声生成
        job.status_code = StatusCode.AUDIO_GENERATING
        job.progress = 60
        job.updated_at = datetime.now()
        
        # 音声生成の進捗を細かく更新
        audio_generator = AudioGenerator(job_id, Path.cwd())
        
        # スライド数を取得して進捗計算用に使用
        with open(dialogue_path, 'r', encoding='utf-8') as f:
            dialogue_data = json.load(f)
        total_slides = len(dialogue_data)
        
        # 各スライドの処理前に進捗を更新するためのラッパー
        original_generate = audio_generator.generate_audio_files
        def generate_with_progress(*args, **kwargs):
            # 内部で各スライドを処理する際に進捗を更新
            job.status_code = StatusCode.AUDIO_PROCESSING_SLIDE
            result = original_generate(*args, **kwargs)
            return result
        
        audio_count = generate_with_progress(
            speed_scale=1.0,
            pitch_scale=0.0,
            intonation_scale=1.2,
            volume_scale=1.0
        )
        
        # 4. 動画作成
        job.status_code = StatusCode.VIDEO_CREATING
        job.progress = 80
        job.updated_at = datetime.now()
        
        video_creator = VideoCreator(job_id, Path.cwd())
        
        # 動画エンコーディング中のステータス更新
        job.status_code = StatusCode.VIDEO_ENCODING
        job.progress = 85
        job.updated_at = datetime.now()
        
        video_path = video_creator.create_video()
        
        # 動画ファイナライズ
        job.status_code = StatusCode.VIDEO_FINALIZING
        job.progress = 95
        job.updated_at = datetime.now()
        
        # 5. 完了
        job.status = "completed"
        job.status_code = StatusCode.COMPLETED
        job.progress = 100
        job.result_url = f"/api/jobs/{job_id}/download"
        job.error_code = None  # エラーコードをクリアして過去のエラー表示を防ぐ
        job.updated_at = datetime.now()
        
    except Exception as e:
        import traceback
        error_msg = f"Error in generate_complete_video: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # コンソールにエラーを出力
        job = jobs_db[job_id]
        job.status = "failed"
        job.status_code = StatusCode.FAILED
        job.error_code = StatusCode.VIDEO_CREATION_ERROR
        job.updated_at = datetime.now()

async def generate_audio_task(
    job_id: str,
    speed_scale: float,
    pitch_scale: float,
    intonation_scale: float,
    volume_scale: float
):
    """音声を生成"""
    try:
        job = jobs_db[job_id]
        job.progress = 40
        
        # 音声生成
        generator = AudioGenerator(job_id, Path.cwd())
        audio_count = generator.generate_audio_files(
            speed_scale=speed_scale,
            pitch_scale=pitch_scale,
            intonation_scale=intonation_scale,
            volume_scale=volume_scale
        )
        
        job.status = "audio_ready"
        job.status_code = StatusCode.COMPLETED
        job.progress = 60
        job.error_code = None  # エラーコードをクリアして過去のエラー表示を防ぐ
        job.updated_at = datetime.now()
        
    except Exception as e:
        job = jobs_db[job_id]
        job.status = "failed"
        job.status_code = StatusCode.FAILED
        job.error_code = StatusCode.AUDIO_GENERATION_ERROR
        job.updated_at = datetime.now()

async def create_video_task(job_id: str, slide_numbers: Optional[List[int]]):
    """動画を作成"""
    try:
        job = jobs_db[job_id]
        job.progress = 80
        
        # 動画作成
        creator = VideoCreator(job_id, Path.cwd())
        video_path = creator.create_video(slide_numbers)
        
        job.status = "completed"
        job.status_code = StatusCode.COMPLETED
        job.progress = 100
        job.result_url = f"/api/jobs/{job_id}/download"
        job.error_code = None  # エラーコードをクリアして過去のエラー表示を防ぐ
        job.updated_at = datetime.now()
        
    except Exception as e:
        import traceback
        error_msg = f"Error in generate_complete_video: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # コンソールにエラーを出力
        job = jobs_db[job_id]
        job.status = "failed"
        job.status_code = StatusCode.FAILED
        job.error_code = StatusCode.VIDEO_CREATION_ERROR
        job.updated_at = datetime.now()

# 動画時間の概算関数
def estimate_video_duration(dialogue_data: Dict[str, List[Dict]]) -> float:
    """対話データから動画時間を概算"""
    total_chars = 0
    total_dialogues = 0
    
    for slide_key, dialogues in dialogue_data.items():
        for dialogue in dialogues:
            text = dialogue.get("text", "")
            total_chars += len(text)
            total_dialogues += 1
    
    # 概算:
    # - 日本語の読み上げ速度: 約300-350文字/分（VOICEVOXのデフォルト速度）
    # - スライド間の間隔: 0.5秒 × スライド数
    # - 対話間の間隔: 0.3秒 × 対話数
    
    chars_per_second = 5.5  # 330文字/分 ÷ 60秒
    text_duration = total_chars / chars_per_second
    
    slide_count = len(dialogue_data)
    slide_transition_duration = slide_count * 0.5
    dialogue_pause_duration = total_dialogues * 0.3
    
    total_seconds = text_duration + slide_transition_duration + dialogue_pause_duration
    
    return round(total_seconds, 1)

def format_duration(seconds: float) -> str:
    """秒数を分:秒形式にフォーマット"""
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    return f"{minutes}分{remaining_seconds}秒"

@app.post("/api/jobs/{job_id}/generate-video")
async def generate_video_directly(job_id: str, background_tasks: BackgroundTasks):
    """スライド準備完了後、動画生成を直接実行"""
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    
    # ジョブが適切な状態であることを確認
    if job.status not in ["slides_ready", "audio_ready"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Job must be in 'slides_ready' or 'audio_ready' state. Current: {job.status}"
        )
    
    # 動画生成タスクを開始
    job.status = "processing"
    job.status_code = StatusCode.VIDEO_CREATING
    job.updated_at = datetime.now()
    
    background_tasks.add_task(generate_complete_video, job_id)
    
    return {"message": "Video generation started", "job_id": job_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)