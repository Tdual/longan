import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class InstructionHistory:
    """再生成指示の履歴を管理するクラス"""
    
    def __init__(self, job_id: str, base_dir: Path):
        self.job_id = job_id
        self.history_file = base_dir / "data" / job_id / "instruction_history.json"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_history()
    
    def _load_history(self):
        """履歴ファイルを読み込む"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
        else:
            self.history = {}
    
    def _save_history(self):
        """履歴ファイルに保存"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def add_instruction(self, slide_numbers: List[int], instruction: str):
        """指示を履歴に追加"""
        timestamp = datetime.now().isoformat()
        
        for slide_num in slide_numbers:
            slide_key = f"slide_{slide_num}"
            if slide_key not in self.history:
                self.history[slide_key] = []
            
            self.history[slide_key].append({
                "timestamp": timestamp,
                "instruction": instruction
            })
        
        self._save_history()
    
    def get_slide_history(self, slide_number: int) -> List[Dict]:
        """特定のスライドの履歴を取得"""
        slide_key = f"slide_{slide_number}"
        return self.history.get(slide_key, [])
    
    def get_combined_instruction(self, slide_number: int, new_instruction: str) -> str:
        """過去の指示と新しい指示を組み合わせる"""
        history = self.get_slide_history(slide_number)
        
        if not history:
            return new_instruction
        
        # 過去の指示をまとめる
        combined = "このスライドに対する過去の指示:\n"
        for i, hist in enumerate(history, 1):
            combined += f"{i}. {hist['instruction']}\n"
        
        combined += f"\n今回の新しい指示:\n{new_instruction}\n"
        combined += "\n重要: すべての指示を考慮して対話を生成してください。"
        
        return combined
    
    def clear_slide_history(self, slide_number: int):
        """特定のスライドの履歴をクリア"""
        slide_key = f"slide_{slide_number}"
        if slide_key in self.history:
            del self.history[slide_key]
            self._save_history()
    
    def clear_all_history(self):
        """すべての履歴をクリア"""
        self.history = {}
        self._save_history()