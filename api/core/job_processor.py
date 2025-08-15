"""
ジョブ処理モジュール - 非同期でのデータ処理
"""
import sys
from pathlib import Path
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# プロジェクトのパスを追加
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.append(str(project_root))

from api.core.status_codes import StatusCode
from api.core.async_worker import async_worker

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobProcessor:
    """ジョブ処理の非同期実装"""
    
    @staticmethod
    def process_pdf_sync(job_id: str, pdf_path: str, jobs_db: Dict[str, Any]) -> int:
        """PDF処理の同期版（ワーカーで実行される）"""
        try:
            from api.core.pdf_processor import PDFProcessor
            
            job = jobs_db[job_id]
            job.status_code = StatusCode.PDF_PROCESSING
            job.progress = 10
            job.updated_at = datetime.now()
            
            processor = PDFProcessor(job_id, Path.cwd())
            slide_count = processor.convert_pdf_to_slides(pdf_path)
            
            job.status_code = StatusCode.PDF_COMPLETED
            job.progress = 25
            job.error_code = None  # エラーコードをクリア
            job.updated_at = datetime.now()
            
            logger.info(f"PDF処理完了: {job_id}, スライド数: {slide_count}")
            return slide_count
            
        except Exception as e:
            job = jobs_db[job_id]
            job.status = "failed"
            job.status_code = StatusCode.FAILED
            job.error_code = StatusCode.PDF_PROCESSING_ERROR
            job.updated_at = datetime.now()
            logger.error(f"PDF処理エラー {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def generate_dialogue_sync(job_id: str, additional_prompt: Optional[str], jobs_db: Dict[str, Any]) -> None:
        """対話生成の同期版（ワーカーで実行される）"""
        try:
            import asyncio
            from api.core.dialogue_generator import DialogueGenerator
            from api.core.text_extractor import TextExtractor
            
            job = jobs_db[job_id]
            job.status_code = StatusCode.DIALOGUE_GENERATING
            job.progress = 30
            job.updated_at = datetime.now()
            
            # PDFファイルからテキストを抽出
            job_dir = Path.cwd() / "uploads" / job_id
            pdf_files = list(job_dir.glob("*.pdf"))
            if not pdf_files:
                raise Exception("PDFファイルが見つかりません")
            
            extractor = TextExtractor()
            slide_texts = extractor.extract_text_from_pdf(str(pdf_files[0]))
            
            # 対話生成を実行
            generator = DialogueGenerator()
            
            # 非同期関数を同期で実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                dialogue_data = loop.run_until_complete(
                    generator.extract_text_from_slides(
                        slide_texts, 
                        additional_prompt=additional_prompt,
                        target_duration=10  # デフォルト10分
                    )
                )
                
                # 対話データを保存
                data_dir = Path.cwd() / "data" / job_id
                data_dir.mkdir(parents=True, exist_ok=True)
                
                with open(data_dir / "dialogue_narration_original.json", "w", encoding="utf-8") as f:
                    json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
                    
            finally:
                loop.close()
            
            job.status_code = StatusCode.DIALOGUE_COMPLETED
            job.progress = 60
            job.error_code = None  # エラーコードをクリア
            job.updated_at = datetime.now()
            
            logger.info(f"対話生成完了: {job_id}")
            
        except Exception as e:
            job = jobs_db[job_id]
            job.status = "failed"
            job.status_code = StatusCode.FAILED
            job.error_code = StatusCode.DIALOGUE_GENERATION_ERROR
            job.updated_at = datetime.now()
            logger.error(f"対話生成エラー {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def generate_audio_sync(job_id: str, speed_scale: float, pitch_scale: float, 
                          intonation_scale: float, volume_scale: float, jobs_db: Dict[str, Any]) -> None:
        """音声生成の同期版（ワーカーで実行される）"""
        try:
            from api.core.audio_generator import AudioGenerator
            
            job = jobs_db[job_id]
            job.status_code = StatusCode.AUDIO_GENERATING
            job.progress = 65
            job.updated_at = datetime.now()
            
            generator = AudioGenerator(job_id, Path.cwd())
            generator.generate_audio_files(
                speed_scale=speed_scale,
                pitch_scale=pitch_scale,
                intonation_scale=intonation_scale,
                volume_scale=volume_scale
            )
            
            job.status_code = StatusCode.AUDIO_COMPLETED
            job.progress = 85
            job.error_code = None  # エラーコードをクリア
            job.updated_at = datetime.now()
            
            logger.info(f"音声生成完了: {job_id}")
            
        except Exception as e:
            job = jobs_db[job_id]
            job.status = "failed"
            job.status_code = StatusCode.FAILED
            job.error_code = StatusCode.AUDIO_GENERATION_ERROR
            job.updated_at = datetime.now()
            logger.error(f"音声生成エラー {job_id}: {str(e)}")
            raise
    
    @staticmethod
    def create_video_sync(job_id: str, jobs_db: Dict[str, Any]) -> str:
        """動画作成の同期版（ワーカーで実行される）"""
        try:
            from api.core.video_creator import VideoCreator
            
            job = jobs_db[job_id]
            job.status_code = StatusCode.VIDEO_CREATING
            job.progress = 90
            job.updated_at = datetime.now()
            
            creator = VideoCreator(job_id, Path.cwd())
            video_path = creator.create_video()
            
            job.status = "completed"
            job.status_code = StatusCode.COMPLETED
            job.progress = 100
            job.result_url = f"/api/jobs/{job_id}/download"
            job.error_code = None  # エラーコードをクリア
            job.updated_at = datetime.now()
            
            logger.info(f"動画作成完了: {job_id}, パス: {video_path}")
            return video_path
            
        except Exception as e:
            job = jobs_db[job_id]
            job.status = "failed"
            job.status_code = StatusCode.FAILED
            job.error_code = StatusCode.VIDEO_CREATION_ERROR
            job.updated_at = datetime.now()
            logger.error(f"動画作成エラー {job_id}: {str(e)}")
            raise

    @staticmethod
    async def process_complete_video_async(job_id: str, jobs_db: Dict[str, Any], 
                                         additional_prompt: Optional[str] = None) -> None:
        """完全な動画生成フローを非同期で実行"""
        try:
            job = jobs_db[job_id]
            job.status = "processing"
            job.updated_at = datetime.now()
            
            # 1. PDFファイルパスを取得
            job_dir = Path.cwd() / "uploads" / job_id
            pdf_files = list(job_dir.glob("*.pdf"))
            if not pdf_files:
                raise Exception("PDFファイルが見つかりません")
            
            pdf_path = str(pdf_files[0])
            
            # 2. PDF処理（非同期）
            await async_worker.submit_task(
                f"pdf_{job_id}",
                JobProcessor.process_pdf_sync,
                job_id, pdf_path, jobs_db
            )
            await async_worker.wait_for_task(f"pdf_{job_id}")
            
            # 3. 対話生成（非同期）
            await async_worker.submit_task(
                f"dialogue_{job_id}",
                JobProcessor.generate_dialogue_sync,
                job_id, additional_prompt, jobs_db
            )
            await async_worker.wait_for_task(f"dialogue_{job_id}")
            
            # 4. 音声生成（非同期）
            await async_worker.submit_task(
                f"audio_{job_id}",
                JobProcessor.generate_audio_sync,
                job_id, 1.0, 0.0, 1.2, 1.0, jobs_db
            )
            await async_worker.wait_for_task(f"audio_{job_id}")
            
            # 5. 動画作成（非同期）
            await async_worker.submit_task(
                f"video_{job_id}",
                JobProcessor.create_video_sync,
                job_id, jobs_db
            )
            await async_worker.wait_for_task(f"video_{job_id}")
            
            logger.info(f"完全動画生成完了: {job_id}")
            
        except Exception as e:
            job = jobs_db[job_id]
            job.status = "failed"
            job.status_code = StatusCode.FAILED
            job.updated_at = datetime.now()
            logger.error(f"完全動画生成エラー {job_id}: {str(e)}")
            raise