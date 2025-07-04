from pdf2image import convert_from_path
import os
from pathlib import Path

class PDFConverter:
    def __init__(self, output_dir="slides"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def convert_pdf_to_images(self, pdf_path, dpi=300):
        """PDFファイルを画像に変換"""
        print(f"PDFを変換中: {pdf_path}")
        
        images = convert_from_path(pdf_path, dpi=dpi)
        
        image_paths = []
        for i, image in enumerate(images):
            image_path = self.output_dir / f"slide_{i+1:03d}.png"
            image.save(image_path, "PNG")
            image_paths.append(str(image_path))
            print(f"  スライド {i+1} を保存: {image_path}")
        
        return image_paths