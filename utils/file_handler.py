from pathlib import Path
from typing import List
import json
import shutil
import os
from utils.logging_utils import OutputTarget, synchronized_print

'''
class TooManyFilesError(Exception):
    pass
'''
class FileHandler:
    """Handles file and directory operations"""
    
    @staticmethod
    def load_packages_from_json(path: str) -> List[str]:
        """Load package names from a JSON file"""        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [data] if isinstance(data, str) else data
        except Exception as e:
            raise SystemExit(f"Error reading JSON {path}: {e}")
    
    @staticmethod
    def get_all_files(directory: Path) -> List[Path]:   #max_files: int = 2000
        """Find all files in directory (recursive) excluding certain directories, files and extensions."""
        files: List[Path] = []
        directory_str = str(directory)
        for root, dirs, filenames in os.walk(directory_str):
            for name in filenames:
                files.append(Path(root) / name)
                #if len(files) > max_files:
                #    raise TooManyFilesError(f"Too many files {max_files} in directory {directory}")
        return files
    
    @staticmethod
    def read_file(file_path: Path) -> str:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            synchronized_print(f"   Non-UTF8 file, skipped: {file_path.name}", target=OutputTarget.FILE_ONLY)
            return ""
        except Exception as e:
            synchronized_print(f"Error reading {file_path}: {e}", target=OutputTarget.FILE_ONLY)
            return ""

    @staticmethod
    def delete_previous_analysis() -> None:
        """Delete all results from previous analysis (repos, other_versions/extracted, log file, output directory)"""
        dirs_to_delete = ['analysis_results']
        for dir_name in dirs_to_delete:
            dir_path = Path(dir_name)
            if dir_path.exists() and dir_path.is_dir():
                shutil.rmtree(dir_path)
                #print(f"Deleted directory: {dir_path}")

        log_file = Path('log.txt')
        if log_file.exists() and log_file.is_file():
            log_file.unlink()
            #print(f"Deleted log file: {log_file}")

    @staticmethod
    def delete_exctracted_dir(package: str) -> None:
        extracted_dir = Path("tarballs") / package.replace('/', '_') / "extracted"
        if extracted_dir.exists() and extracted_dir.is_dir():
            shutil.rmtree(extracted_dir)
            #print(f"Deleted extracted directory: {extracted_dir}")