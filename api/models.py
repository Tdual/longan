from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class JobStatusEnum(str, Enum):
    PENDING = "pending"
    SLIDES_READY = "slides_ready"
    GENERATING_AUDIO = "generating_audio"
    AUDIO_READY = "audio_ready"
    CREATING_VIDEO = "creating_video"
    COMPLETED = "completed"
    FAILED = "failed"

class SpeakerEnum(str, Enum):
    METAN = "metan"
    ZUNDAMON = "zundamon"

class DialogueItem(BaseModel):
    speaker: SpeakerEnum
    text: str

class SlideDialogue(BaseModel):
    slide_number: int
    dialogues: List[DialogueItem]

class JobConfig(BaseModel):
    """ジョブ設定"""
    # 音声パラメータ
    speed_scale: float = Field(default=1.0, ge=0.5, le=2.0)
    pitch_scale: float = Field(default=0.0, ge=-0.15, le=0.15)
    intonation_scale: float = Field(default=1.2, ge=0.0, le=2.0)
    volume_scale: float = Field(default=1.0, ge=0.0, le=2.0)
    
    # 動画パラメータ
    fps: int = Field(default=24, ge=1, le=60)
    slide_numbers: Optional[List[int]] = None
    
    # 対話内容（オプション）
    custom_dialogues: Optional[List[SlideDialogue]] = None

class JobMetadata(BaseModel):
    """ジョブメタデータ"""
    original_filename: str
    total_slides: Optional[int] = None
    total_audio_files: Optional[int] = None
    estimated_duration: Optional[float] = None
    file_size_mb: Optional[float] = None