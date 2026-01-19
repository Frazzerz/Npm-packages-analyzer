from pathlib import Path
from typing import Dict, Tuple
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
        
        if not FileTypeDetector.is_valid_file_for_analysis(file_type):
            synchronized_print(f"   Skipping non-valid file: {file_path.name} (type: {file_type})")
            metrics.generic.file_type = file_type
            metrics.generic.size_bytes = size_bytes
            return metrics
        
        content = FileHandler().read_file(file_path)
        if not content:
            synchronized_print(f"   Empty content: {file_path.name}")
            metrics.generic.file_type = file_type
            metrics.generic.size_bytes = size_bytes
            return metrics
        
        # Pre-process content
        processed_content, pre_metrics = self._preprocess_content(content, file_path, file_type)
        
        # Analyze all categories
        metrics.generic = self.generic_analyzer.analyze( processed_content, *pre_metrics)
        
        metrics.evasion = self.evasion_analyzer.analyze(processed_content, metrics.generic)
        metrics.payload = self.payload_analyzer.analyze(processed_content, package_info)
        metrics.exfiltration = self.exfiltration_analyzer.analyze(processed_content)
        metrics.crypto = self.cryptojacking_analyzer.analyze(processed_content)
        
        metrics.generic.file_type = file_type
        metrics.generic.size_bytes = size_bytes
        return metrics
    
    def _preprocess_content(self, content: str, file_path: Path, file_type: str) -> Tuple[str, Tuple]:
        """Preprocess content: unminify if needed, extract metrics, remove comments"""
        # Check if minified and unminify if necessary
        minified = self.generic_analyzer.pre_analyze(content)
        if minified:
            content = self.generic_analyzer.unminify_code(content)
        
        # Get pre-metrics for JS-like files
        if FileTypeDetector.is_js_like_file(file_type):
            pre_metrics = self.generic_analyzer.pre_analyze_js(content)
            content, num_comments = UtilsForAnalyzer.remove_comments(content, file_path.name)

            num_chars, num_lines, entropy, ws_ratio, num_ws, num_printable = pre_metrics
            return content, (
                num_chars,
                num_lines,
                num_comments,
                entropy,
                ws_ratio,
                num_ws,
                num_printable,
                minified
            )
        
        # For non-JS files, return zeros
        return content, (0, 0, 0, 0.0, 0, 0, 0, minified)