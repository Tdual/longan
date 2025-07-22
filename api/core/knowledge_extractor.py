import os
from docx import Document
import zipfile
import xml.etree.ElementTree as ET
import fitz  # PyMuPDF
import csv
from pathlib import Path
from typing import Optional

def extract_text_from_knowledge_file(file_path: str) -> str:
    """ナレッジファイルからテキストを抽出する"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
    
    extension = file_path.suffix.lower()
    
    if extension == '.txt':
        return extract_text_from_txt(file_path)
    elif extension == '.md':
        return extract_text_from_md(file_path)
    elif extension == '.docx':
        return extract_text_from_docx(file_path)
    elif extension == '.pptx':
        return extract_text_from_pptx(file_path)
    elif extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif extension == '.csv':
        return extract_text_from_csv(file_path)
    elif extension in ['.rtf', '.odt']:
        return extract_text_from_other_formats(file_path)
    else:
        raise ValueError(f"対応していないファイル形式: {extension}")

def extract_text_from_txt(file_path: Path) -> str:
    """txtファイルからテキストを抽出"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # UTF-8で読めない場合はShift-JISを試す
        try:
            with open(file_path, 'r', encoding='shift-jis') as f:
                return f.read()
        except UnicodeDecodeError:
            # CP932を試す
            with open(file_path, 'r', encoding='cp932') as f:
                return f.read()

def extract_text_from_md(file_path: Path) -> str:
    """mdファイルからテキストを抽出"""
    # マークダウンファイルは基本的にテキストファイルと同じ
    return extract_text_from_txt(file_path)

def extract_text_from_docx(file_path: Path) -> str:
    """docxファイルからテキストを抽出"""
    try:
        doc = Document(file_path)
        text_parts = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())
        
        return '\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"Wordファイルの読み取りエラー: {e}")

def extract_text_from_pptx(file_path: Path) -> str:
    """pptxファイルからテキストを抽出"""
    try:
        text_parts = []
        
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            # スライドファイルを取得
            slide_files = [f for f in zip_file.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
            
            for slide_file in sorted(slide_files):
                with zip_file.open(slide_file) as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()
                    
                    # テキストを抽出（名前空間を考慮）
                    for text_elem in root.iter():
                        if text_elem.tag.endswith('}t'):  # テキスト要素
                            if text_elem.text and text_elem.text.strip():
                                text_parts.append(text_elem.text.strip())
        
        return '\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"PowerPointファイルの読み取りエラー: {e}")

def extract_text_from_pdf(file_path: Path) -> str:
    """PDFファイルからテキストを抽出"""
    try:
        text_parts = []
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                text_parts.append(text.strip())
        
        doc.close()
        return '\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"PDFファイルの読み取りエラー: {e}")

def extract_text_from_csv(file_path: Path) -> str:
    """CSVファイルからテキストを抽出"""
    try:
        text_parts = []
        
        # まずUTF-8で試す
        try:
            with open(file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    row_text = ' '.join([cell.strip() for cell in row if cell.strip()])
                    if row_text:
                        text_parts.append(row_text)
        except UnicodeDecodeError:
            # UTF-8で読めない場合はShift-JISを試す
            with open(file_path, 'r', encoding='shift-jis', newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    row_text = ' '.join([cell.strip() for cell in row if cell.strip()])
                    if row_text:
                        text_parts.append(row_text)
        
        return '\n'.join(text_parts)
    except Exception as e:
        raise ValueError(f"CSVファイルの読み取りエラー: {e}")

def extract_text_from_other_formats(file_path: Path) -> str:
    """その他のファイル形式からテキストを抽出（RTF、ODT等）"""
    # RTFやODTは複雑な形式のため、基本的にはテキストファイルとして読み込む
    # より高度な処理が必要な場合は専用ライブラリを追加する
    try:
        return extract_text_from_txt(file_path)
    except Exception as e:
        raise ValueError(f"ファイルの読み取りエラー ({file_path.suffix}): {e}")