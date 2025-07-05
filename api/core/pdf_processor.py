import sys
from pathlib import Path
import os
import json

# srcディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from pdf_converter import PDFConverter
from .text_extractor import TextExtractor
from .dialogue_generator import DialogueGenerator

class PDFProcessor:
    def __init__(self, job_id: str, base_dir: Path):
        self.job_id = job_id
        self.base_dir = base_dir
        self.slides_dir = base_dir / "slides" / job_id
        self.slides_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = base_dir / "data" / job_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def convert_pdf_to_slides(self, pdf_path: str) -> int:
        """PDFをスライド画像に変換"""
        converter = PDFConverter(str(self.slides_dir))
        slide_paths = converter.convert_pdf_to_images(pdf_path)
        return len(slide_paths)
    
    def generate_dialogue_from_pdf(self, pdf_path: str, additional_prompt: str = None, progress_callback=None, target_duration: int = 10) -> str:
        """PDFから対話データを生成"""
        # 1. PDFからテキストを抽出
        text_extractor = TextExtractor()
        slide_texts = text_extractor.extract_text_from_pdf(pdf_path)
        
        # 2. 対話を生成（目安時間を渡す）
        dialogue_generator = DialogueGenerator()
        dialogue_data = dialogue_generator.extract_text_from_slides(
            slide_texts, 
            additional_prompt,
            progress_callback,
            target_duration
        )
        
        # 3. データを保存（AIが既にカタカナで生成しているため変換不要）
        original_dialogue_path = self.data_dir / "dialogue_narration_original.json"
        with open(original_dialogue_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
        
        # 互換性のためkatakanaファイルも同じ内容で保存
        katakana_path = self.data_dir / "dialogue_narration_katakana.json"
        with open(katakana_path, 'w', encoding='utf-8') as f:
            json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
        
        return str(original_dialogue_path)