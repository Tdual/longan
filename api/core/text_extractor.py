import fitz  # PyMuPDF
from typing import List
from pathlib import Path

class TextExtractor:
    def __init__(self):
        pass
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[str]:
        """PDFから各ページのテキストを抽出"""
        slide_texts = []
        
        try:
            # PDFを開く
            pdf_document = fitz.open(pdf_path)
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text = page.get_text()
                
                # テキストをクリーンアップ
                text = self._clean_text(text)
                slide_texts.append(text)
            
            pdf_document.close()
            
        except Exception as e:
            print(f"PDF読み込みエラー: {e}")
            # エラー時は空のリストを返す
            return []
        
        return slide_texts
    
    def _clean_text(self, text: str) -> str:
        """テキストのクリーンアップ"""
        # 余分な空白や改行を整理
        lines = text.strip().split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return '\n'.join(cleaned_lines)