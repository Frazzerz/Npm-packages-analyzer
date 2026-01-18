from pathlib import Path
from typing import Optional
from magika import Magika

class FileTypeDetector:
    """Detects file types using Google's Magika"""
    
    _magika_instance: Optional[Magika] = None
    
    # Plain text files
    VALID_TYPES = {
        # Executable code / scripts
        'javascript', 'typescript', 'coffeescript',
        'jsx', 'tsx', 'vue',
        'bash', 'shell', 'powershell',
        'python', 'ruby', 'php', 'perl', 'lua',
        'go', 'rust', 'java', 'kotlin', 'scala', 'swift',
        'c', 'cpp', 'csharp', 'objectivec',
        'solidity', 'zig', 'nim', 'haskell', 'txt',
        
        # Config, manifest, build/deploy scripts
        'json', 'jsonl',
        'yaml', 'toml', 'ini', 'xml',
        'hcl',
        'dockerfile', 'makefile', 'cmake', 'gradle', 'bazel',
        'gitmodules', 'gitattributes',
        'npmrc',

        # Readme.md
        'markdown',
    }
    
    @classmethod
    def get_magika(cls) -> Magika:
        """Lazy initialization of Magika instance (singleton pattern)"""
        if cls._magika_instance is None:
            cls._magika_instance = Magika()
        return cls._magika_instance
    
    @classmethod
    def detect_file_type(cls, file_path: Path) -> str:
        """
        Detect file type using Magika
        Returns the detected file type label (e.g., 'javascript', 'zip', 'png')
        """
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