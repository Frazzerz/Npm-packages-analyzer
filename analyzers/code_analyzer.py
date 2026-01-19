from pathlib import Path
from typing import Dict
from .categories import EvasionAnalyzer, PayloadAnalyzer, ExfiltrationAnalyzer, CryptojackingAnalyzer, GenericAnalyzer
from models.composed_metrics import FileMetrics
from utils import FileHandler, synchronized_print, FileTypeDetector, UtilsForAnalyzer
class CodeAnalyzer:
    """Coordinates analysis across all categories"""
    
    def __init__(self):
        self.generic_analyzer = GenericAnalyzer()
        self.evasion_analyzer = EvasionAnalyzer()
        self.payload_analyzer = PayloadAnalyzer()
        self.exfiltration_analyzer = ExfiltrationAnalyzer()
        self.cryptojacking_analyzer = CryptojackingAnalyzer()

    def analyze_file(self, file_path: Path, package_info: Dict) -> FileMetrics:
        """Analyze a single file and return all metrics"""
        metrics = FileMetrics(
            package=package_info['name'],
            version=package_info['version'],
            file_path=package_info['file_name'],
        )
        file_type = FileTypeDetector.detect_file_type(file_path)
        size_bytes = file_path.stat().st_size
        # Initialize counts
        number_of_characters = 0
        total_number_of_non_blank_lines = 0
        number_of_comments = 0
        shannon_entropy_original = 0.0
        number_of_whitespace_characters = 0
        number_of_printable_characters = 0
        blank_space_and_character_ratio_original = 0.0
        
        if FileTypeDetector.is_valid_file_for_analysis(file_type):
            content = FileHandler().read_file(file_path)
            if not content:
                synchronized_print(f"   Empty content: {file_path.name}")
            else:
                minified = self.generic_analyzer.pre_analyze(content)
                if minified:
                    content = self.generic_analyzer.unminify_code(content)
                if FileTypeDetector.is_js_like_file(file_type):
                    number_of_characters, total_number_of_non_blank_lines, shannon_entropy_original, blank_space_and_character_ratio_original, number_of_whitespace_characters, number_of_printable_characters = self.generic_analyzer.pre_analyze_js(content)
                    content, number_of_comments = UtilsForAnalyzer.remove_comments(content, file_path.name)
                metrics.generic = self.generic_analyzer.analyze(content, number_of_characters, total_number_of_non_blank_lines, number_of_comments, shannon_entropy_original, blank_space_and_character_ratio_original, number_of_whitespace_characters, number_of_printable_characters, minified)
                metrics.evasion = self.evasion_analyzer.analyze(content, metrics.generic)
                metrics.payload = self.payload_analyzer.analyze(content, package_info)
                metrics.exfiltration = self.exfiltration_analyzer.analyze(content)
                metrics.crypto = self.cryptojacking_analyzer.analyze(content)
        else:
            synchronized_print(f"   Skipping non-valid file for analysis: {file_path.name} (detected type: {file_type})")
        metrics.generic.file_type = file_type
        metrics.generic.size_bytes = size_bytes
        return metrics
    
    '''
    def _analyze_single_file_wrapper(self, file_path: Path, version: str, package_dir: Path, source: SourceType) -> FileMetrics:
        import time
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Analysis timeout for {file_path.name}")
        
        start = time.time()
        try:
            synchronized_print(f"[START] Analyzing {file_path.name}")
            
            # Set 30 second timeout per file
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 seconds max per file
            
            result = self._analyze_single_file(file_path, version, package_dir, source)
            
            signal.alarm(0)  # Cancel alarm
            
            elapsed = time.time() - start
            synchronized_print(f"[DONE] {file_path.name} in {elapsed:.2f}s")
            return result
            
        except TimeoutError as e:
            signal.alarm(0)
            synchronized_print(f"[TIMEOUT] {file_path.name} after {time.time()-start:.2f}s")
            return None
            
        except Exception as e:
            signal.alarm(0)
            synchronized_print(f"[ERROR] {file_path.name}: {e}")
            return None
    '''