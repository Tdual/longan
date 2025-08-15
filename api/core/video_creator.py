import sys
from pathlib import Path
from typing import List, Optional

# srcディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from dialogue_video_creator import DialogueVideoCreator

class VideoCreator:
    def __init__(self, job_id: str, base_dir: Path):
        self.job_id = job_id
        self.base_dir = base_dir
        self.slides_dir = base_dir / "slides" / job_id
        self.audio_dir = base_dir / "audio" / job_id
        self.output_dir = base_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
    def create_video(self, slide_numbers: Optional[List[int]] = None) -> str:
        """動画を作成"""
        
        # スライド画像のパスを取得
        image_paths = []
        slide_files = sorted(self.slides_dir.glob("slide_*.png"))
        
        if slide_numbers:
            # 指定されたスライドのみ使用
            for num in slide_numbers:
                slide_path = self.slides_dir / f"slide_{num:03d}.png"
                if slide_path.exists():
                    image_paths.append(str(slide_path))
        else:
            # 全スライドを使用
            image_paths = [str(p) for p in slide_files]
        
        if not image_paths:
            raise Exception("スライド画像が見つかりません")
        
        # 音声ファイル情報を構築
        dialogue_audio_info = {}
        
        for i, image_path in enumerate(image_paths):
            slide_num = int(Path(image_path).stem.split("_")[1])
            slide_key = f"slide_{slide_num}"
            dialogue_audio_info[slide_key] = []
            
            # 該当するスライドの音声ファイルを探す
            audio_files = sorted(self.audio_dir.glob(f"slide_{slide_num:03d}_*_*.wav"))
            
            print(f"スライド {slide_num} ({slide_key}): 音声ファイル {len(audio_files)} 個見つかりました")
            
            for audio_file in audio_files:
                # ファイル名から話者を特定
                parts = audio_file.stem.split("_")
                if len(parts) >= 4:
                    speaker = parts[3]
                    dialogue_audio_info[slide_key].append({
                        "speaker": speaker,
                        "audio_path": str(audio_file)
                    })
                    print(f"  - {audio_file.name}: speaker={speaker}")
        
        # 動画作成
        creator = DialogueVideoCreator()
        output_path = self.output_dir / f"{self.job_id}.mp4"
        
        creator.create_dialogue_video(
            image_paths,
            dialogue_audio_info,
            str(output_path)
        )
        
        return str(output_path)