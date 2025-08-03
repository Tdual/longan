"""
非同期ワーカー - 重い処理を並列実行するためのワーカー
"""
import asyncio
import threading
import concurrent.futures
from typing import Callable, Any, Dict
from pathlib import Path
import logging
from datetime import datetime

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncWorker:
    """非同期処理ワーカー"""
    
    def __init__(self, max_workers: int = 4):
        """
        Args:
            max_workers: 並列実行する最大ワーカー数
        """
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks: Dict[str, asyncio.Task] = {}
        
    async def submit_task(self, task_id: str, func: Callable, *args, **kwargs) -> None:
        """
        タスクを非同期で実行
        
        Args:
            task_id: タスクの一意ID
            func: 実行する関数
            *args, **kwargs: 関数の引数
        """
        logger.info(f"タスク開始: {task_id}")
        
        # 既に同じIDのタスクが実行中の場合はスキップ
        if task_id in self.running_tasks:
            logger.warning(f"タスク {task_id} は既に実行中です")
            return
            
        # 非同期タスクとして実行
        task = asyncio.create_task(self._run_task(task_id, func, *args, **kwargs))
        self.running_tasks[task_id] = task
        
    async def _run_task(self, task_id: str, func: Callable, *args, **kwargs) -> Any:
        """内部タスク実行メソッド"""
        try:
            loop = asyncio.get_event_loop()
            # CPUバウンドなタスクを別スレッドで実行
            result = await loop.run_in_executor(self.executor, func, *args, **kwargs)
            logger.info(f"タスク完了: {task_id}")
            return result
        except Exception as e:
            logger.error(f"タスクエラー {task_id}: {str(e)}")
            raise
        finally:
            # タスクリストから削除
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
                
    def get_running_tasks(self) -> list:
        """実行中のタスク一覧を取得"""
        return list(self.running_tasks.keys())
        
    def is_task_running(self, task_id: str) -> bool:
        """指定タスクが実行中かチェック"""
        return task_id in self.running_tasks
        
    async def wait_for_task(self, task_id: str) -> Any:
        """指定タスクの完了を待機"""
        if task_id in self.running_tasks:
            return await self.running_tasks[task_id]
        return None
        
    def cleanup(self):
        """リソースのクリーンアップ"""
        self.executor.shutdown(wait=True)

# グローバルワーカーインスタンス
async_worker = AsyncWorker(max_workers=6)  # 6つの並列ワーカー