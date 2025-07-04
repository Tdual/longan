from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
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
        
        # 対話データを生成
        dialogue_path = processor.generate_dialogue_from_pdf(pdf_path)
        
        job.status = "slides_ready"
        job.progress = 20
        job.message = f"スライド変換と対話生成が完了しました（{slide_count}枚）"
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