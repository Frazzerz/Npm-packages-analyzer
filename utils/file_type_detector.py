from pathlib import Path
from typing import Optional
from magika import Magika

class FileTypeDetector:
    """Detects file types using Google's Magika"""
    
    _magika_instance: Optional[Magika] = None
    
    # Plain text files
    VALID_TYPES = {
        'javascript', 'typescript', 'coffeescript',
        'shell', 'c', 'cpp', 'python', 
        'json', 'jsonl', 'yaml', 'ini',
        'markdown', # possibile presenza di ind. crypto nel README o CHANGELOG
    }
    
    @classmethod
    def get_magika(cls) -> Magika:
        """Lazy initialization of Magika instance (singleton pattern)"""
        if cls._magika_instance is None:
            cls._magika_instance = Magika()
        return cls._magika_instance
    
    @classmethod
    def detect_file_type(cls, file_path: Path) -> str:
        """Detect file type using Magika. Returns the detected file type label (e.g., 'javascript', 'zip', 'png')"""
        try:
            magika = cls.get_magika()
            result = magika.identify_path(file_path)
            return result.output.label
        except Exception as e:
            print(f"Error detecting file type for {file_path}: {e}")
            return 'unknown'
    
    @classmethod
    def is_valid_file_for_analysis(cls, file_type: str) -> bool:
        """Check if the detected file type should be treated as text"""
        return file_type.lower() in cls.VALID_TYPES
    
    @classmethod
    def is_js_like_file(cls, file_type: str) -> bool:
        """Check if the file type is JavaScript or similar (for comment removal)"""
        return file_type.lower() in {'javascript', 'typescript'}