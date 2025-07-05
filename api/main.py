from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
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

# モデル定義
class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    created_at: datetime
    updated_at: datetime
    progress: int  # 0-100
    message: Optional[str] = None
    result_url: Optional[str] = None
    error: Optional[str] = None

class JobCreateResponse(BaseModel):
    job_id: str
    message: str

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

class UpdateDialogueRequest(BaseModel):
    job_id: str
    dialogue_data: Dict[str, List[Dict]]  # 編集された対話データ

# FastAPIアプリケーション
app = FastAPI(title="Gen Movie API", version="1.0.0")

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

@app.post("/api/jobs/upload", response_model=JobCreateResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """PDFファイルをアップロードしてジョブを作成"""
    
    # ファイル検証
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDFファイルのみ対応しています")
    
    # ジョブID生成
    job_id = str(uuid.uuid4())
    
    # ファイル保存（本番ではS3に保存）
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(exist_ok=True)
    
    pdf_path = job_dir / file.filename
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # ジョブ情報を保存
    job_status = JobStatus(
        job_id=job_id,
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        progress=0,
        message="PDFアップロード完了"
    )
    jobs_db[job_id] = job_status
    
    # バックグラウンドでPDF変換を実行（本番ではBatchジョブ起動）
    background_tasks.add_task(convert_pdf_to_slides, job_id, str(pdf_path))
    
    return JobCreateResponse(
        job_id=job_id,
        message="ジョブを作成しました"
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
    
    if job.status != "slides_ready":
        raise HTTPException(
            status_code=400, 
            detail="スライド変換が完了していません"
        )
    
    # ステータス更新
    job.status = "generating_audio"
    job.progress = 30
    job.message = "音声生成を開始しました"
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
    job.progress = 70
    job.message = "動画作成を開始しました"
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
    
    if job.status not in ["slides_ready", "dialogue_ready"]:
        if job.status == "generating_dialogue":
            raise HTTPException(
                status_code=400, 
                detail="対話生成が進行中です。完了までお待ちください。"
            )
        elif job.status == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"前回の処理が失敗しています: {job.error}"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"対話生成できない状態です: {job.status}"
            )
    
    # ステータス更新
    job.status = "generating_dialogue"
    job.progress = 30
    job.message = "対話スクリプトを生成中..."
    job.updated_at = datetime.now()
    
    # バックグラウンドで対話生成
    def run_in_thread():
        # additional_promptがある場合は再生成とみなす
        is_regeneration = bool(request.additional_prompt)
        asyncio.run(generate_dialogue_task(job_id, request.additional_prompt, is_regeneration))
    
    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True
    thread.start()
    
    return {"message": "対話スクリプト生成を開始しました", "job_id": job_id}

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
    
    dialogue_path = Path.cwd() / "data" / job_id / "dialogue_narration_original.json"
    
    if not dialogue_path.exists():
        raise HTTPException(status_code=404, detail="対話スクリプトが見つかりません")
    
    with open(dialogue_path, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    return dialogue_data

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
    
    # オリジナルデータを保存
    with open(dialogue_path, 'w', encoding='utf-8') as f:
        json.dump(request.dialogue_data, f, ensure_ascii=False, indent=2)
    
    # カタカナ変換版も保存（今は同じデータを保存）
    with open(katakana_path, 'w', encoding='utf-8') as f:
        json.dump(request.dialogue_data, f, ensure_ascii=False, indent=2)
    
    # ジョブステータスを更新
    job = jobs_db[job_id]
    job.status = "dialogue_ready"
    job.message = "対話スクリプトが更新されました"
    job.updated_at = datetime.now()
    
    return {"message": "対話スクリプトを更新しました"}

@app.post("/api/jobs/{job_id}/generate-video")
async def generate_video_complete(
    job_id: str,
    background_tasks: BackgroundTasks
):
    """ワンクリック動画生成（全工程を自動実行）"""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    
    job = jobs_db[job_id]
    
    if job.status not in ["pending", "slides_ready", "dialogue_ready"]:
        raise HTTPException(
            status_code=400, 
            detail="ジョブが適切な状態ではありません"
        )
    
    # ステータス更新
    job.status = "processing"
    job.progress = 10
    job.message = "動画生成を開始しました"
    job.updated_at = datetime.now()
    
    # バックグラウンドで全工程を実行（スレッドで実行してメインスレッドをブロックしない）
    def run_in_thread():
        asyncio.run(generate_complete_video(job_id))
    
    thread = threading.Thread(target=run_in_thread)
    thread.daemon = True
    thread.start()
    
    return {"message": "動画生成を開始しました", "job_id": job_id}

@app.get("/api/jobs", response_model=List[JobStatus])
async def list_jobs():
    """全ジョブのリストを取得"""
    return list(jobs_db.values())

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

# コア機能のインポート
from api.core.pdf_processor import PDFProcessor
from api.core.audio_generator import AudioGenerator
from api.core.video_creator import VideoCreator

# バックグラウンドタスク（本番ではAWS Batchで実行）
async def convert_pdf_to_slides(job_id: str, pdf_path: str):
    """PDFをスライド画像に変換"""
    try:
        job = jobs_db[job_id]
        job.message = "PDFをスライドに変換中..."
        job.progress = 10
        
        # PDFをスライドに変換
        processor = PDFProcessor(job_id, Path.cwd())
        slide_count = processor.convert_pdf_to_slides(pdf_path)
        
        job.message = "対話スクリプトを生成中..."
        job.progress = 15
        job.updated_at = datetime.now()
        
        # 進捗更新用のコールバック
        def update_progress(message: str, progress: float):
            job.message = message
            job.progress = 15 + int(progress * 0.05)  # 15-20%の範囲で進捗表示
            job.updated_at = datetime.now()
        
        # 対話データを生成
        dialogue_path = processor.generate_dialogue_from_pdf(pdf_path, progress_callback=update_progress)
        
        job.status = "slides_ready"
        job.progress = 20
        job.message = f"スライド変換と対話生成が完了しました（{slide_count}枚）"
        job.updated_at = datetime.now()
        
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in convert_pdf_to_slides: {error_msg}")
        job = jobs_db[job_id]
        job.status = "failed"
        job.error = str(e)
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
        job.message = "対話スクリプトを生成中..."
        job.progress = 50
        job.updated_at = datetime.now()
        
        # 進捗更新用のコールバック
        def update_progress(message: str, progress: float):
            job.message = message
            job.progress = 50 + int(progress * 0.1)  # 50-60%の範囲で進捗表示
            job.updated_at = datetime.now()
        
        if is_regeneration and additional_prompt:
            from api.core.text_extractor import TextExtractor
            from api.core.dialogue_generator import DialogueGenerator
            
            # 再生成の場合、どのスライドを再生成するか判断
            dialogue_generator = DialogueGenerator()
            text_extractor = TextExtractor()
            slide_texts = text_extractor.extract_text_from_pdf(pdf_path)
            
            # AIに判断させる
            target_slides = dialogue_generator.analyze_regeneration_request(
                additional_prompt, 
                len(slide_texts)
            )
            
            # 既存の対話データを読み込む
            existing_dialogue_path = Path.cwd() / "data" / job_id / "dialogue_narration_original.json"
            if existing_dialogue_path.exists():
                with open(existing_dialogue_path, 'r', encoding='utf-8') as f:
                    existing_dialogues = json.load(f)
            else:
                existing_dialogues = {}
            
            # 特定のスライドのみ再生成
            dialogue_data = dialogue_generator.regenerate_specific_slides(
                slide_texts,
                existing_dialogues,
                target_slides,
                additional_prompt,
                progress_callback=update_progress
            )
            
            # データを保存
            data_dir = Path.cwd() / "data" / job_id
            data_dir.mkdir(exist_ok=True)
            
            dialogue_path = data_dir / "dialogue_narration_original.json"
            with open(dialogue_path, 'w', encoding='utf-8') as f:
                json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
            
            # カタカナ版も保存
            from api.core.katakana_converter import KatakanaConverter
            katakana_converter = KatakanaConverter()
            dialogue_data_katakana = katakana_converter.convert_dialogue_to_katakana(dialogue_data)
            
            katakana_path = data_dir / "dialogue_narration_katakana.json"
            with open(katakana_path, 'w', encoding='utf-8') as f:
                json.dump(dialogue_data_katakana, f, ensure_ascii=False, indent=2)
        else:
            # 通常の生成
            dialogue_path = processor.generate_dialogue_from_pdf(
                pdf_path, 
                additional_prompt,
                progress_callback=update_progress
            )
        
        # 完了
        job.status = "dialogue_ready"
        job.progress = 60
        job.message = "対話スクリプトが生成されました"
        job.updated_at = datetime.now()
        
    except Exception as e:
        job = jobs_db[job_id]
        job.status = "failed"
        job.error = str(e)
        job.updated_at = datetime.now()

async def generate_complete_video(job_id: str):
    """完全な動画生成フロー（全工程を自動実行）"""
    try:
        job = jobs_db[job_id]
        
        # 1. PDFをスライドに変換
        job.message = "PDFをスライドに変換中..."
        job.progress = 20
        job.updated_at = datetime.now()
        
        # PDFファイルパスを取得
        job_dir = UPLOAD_DIR / job_id
        pdf_files = list(job_dir.glob("*.pdf"))
        if not pdf_files:
            raise Exception("PDFファイルが見つかりません")
        
        pdf_path = str(pdf_files[0])
        
        # PDFを処理
        processor = PDFProcessor(job_id, Path.cwd())
        slide_count = processor.convert_pdf_to_slides(pdf_path)
        
        # 2. 対話データ生成
        job.message = "対話スクリプトを生成中..."
        job.progress = 40
        job.updated_at = datetime.now()
        
        # 進捗更新用のコールバック
        def update_progress(message: str, progress: float):
            job.message = message
            job.progress = 40 + int(progress * 0.2)  # 40-60%の範囲で進捗表示
            job.updated_at = datetime.now()
        
        dialogue_path = processor.generate_dialogue_from_pdf(pdf_path, progress_callback=update_progress)
        
        # 3. 音声生成
        job.message = "音声を生成中..."
        job.progress = 60
        job.updated_at = datetime.now()
        
        audio_generator = AudioGenerator(job_id, Path.cwd())
        audio_count = audio_generator.generate_audio_files(
            speed_scale=1.0,
            pitch_scale=0.0,
            intonation_scale=1.2,
            volume_scale=1.0
        )
        
        # 4. 動画作成
        job.message = "動画を作成中..."
        job.progress = 80
        job.updated_at = datetime.now()
        
        video_creator = VideoCreator(job_id, Path.cwd())
        video_path = video_creator.create_video()
        
        # 5. 完了
        job.status = "completed"
        job.progress = 100
        job.message = "動画生成が完了しました"
        job.result_url = f"/api/jobs/{job_id}/download"
        job.updated_at = datetime.now()
        
    except Exception as e:
        job = jobs_db[job_id]
        job.status = "failed"
        job.error = str(e)
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
        job.message = "音声を生成中..."
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
        job.progress = 60
        job.message = f"音声生成が完了しました（{audio_count}ファイル）"
        job.updated_at = datetime.now()
        
    except Exception as e:
        job = jobs_db[job_id]
        job.status = "failed"
        job.error = str(e)
        job.updated_at = datetime.now()

async def create_video_task(job_id: str, slide_numbers: Optional[List[int]]):
    """動画を作成"""
    try:
        job = jobs_db[job_id]
        job.message = "動画を作成中..."
        job.progress = 80
        
        # 動画作成
        creator = VideoCreator(job_id, Path.cwd())
        video_path = creator.create_video(slide_numbers)
        
        job.status = "completed"
        job.progress = 100
        job.message = "動画作成が完了しました"
        job.result_url = f"/api/jobs/{job_id}/download"
        job.updated_at = datetime.now()
        
    except Exception as e:
        job = jobs_db[job_id]
        job.status = "failed"
        job.error = str(e)
        job.updated_at = datetime.now()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)