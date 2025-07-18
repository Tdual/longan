# Status codes for job processing
class StatusCode:
    # Job status codes
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    
    # Processing stage codes
    PDF_UPLOADING = "PDF_UPLOADING"
    PDF_PROCESSING = "PDF_PROCESSING"
    PDF_EXTRACTING_TEXT = "PDF_EXTRACTING_TEXT"
    PDF_GENERATING_SLIDES = "PDF_GENERATING_SLIDES"
    DIALOGUE_GENERATING = "DIALOGUE_GENERATING"
    DIALOGUE_PROCESSING = "DIALOGUE_PROCESSING"
    AUDIO_GENERATING = "AUDIO_GENERATING"
    AUDIO_PROCESSING_SLIDE = "AUDIO_PROCESSING_SLIDE"
    VIDEO_CREATING = "VIDEO_CREATING"
    VIDEO_ENCODING = "VIDEO_ENCODING"
    VIDEO_FINALIZING = "VIDEO_FINALIZING"
    
    # Error codes
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    PDF_PROCESSING_ERROR = "PDF_PROCESSING_ERROR"
    DIALOGUE_GENERATION_ERROR = "DIALOGUE_GENERATION_ERROR"
    AUDIO_GENERATION_ERROR = "AUDIO_GENERATION_ERROR"
    VIDEO_CREATION_ERROR = "VIDEO_CREATION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    NO_TEXT_EXTRACTED = "NO_TEXT_EXTRACTED"
    NO_SLIDES_EXTRACTED = "NO_SLIDES_EXTRACTED"
    INVALID_TARGET_DURATION = "INVALID_TARGET_DURATION"
    INVALID_CONVERSATION_STYLE = "INVALID_CONVERSATION_STYLE"