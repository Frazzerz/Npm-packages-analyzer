import re
from typing import Dict, List, Pattern
from utils import UtilsForAnalyzer
import jsbeautifier
from models.domains import EvasionMetrics
from models import SourceType, CodeType
from utils import synchronized_print
class EvasionAnalyzer:
    """Analyze evasion techniques"""

    OBFUSCATION_PATTERNS: List[Pattern] = [
        re.compile(r'_?0x[0-9a-fA-F]{6,}'),                                                   # Hexadecimal values and variables (at least 6 hex values), e.g. 0x58e7a2 or _0x5f3b1c
        re.compile(r'parseInt\(_?0x[0-9a-fA-F]{6,}', re.IGNORECASE),                          # ParseInt with hexadecimals, e.g. parseInt(0x58e7a2
        re.compile(r'try\{.*?\}catch\(_?0x[0-9a-fA-F]{6,}\)', re.IGNORECASE),                 # Try-catch blocks with obfuscated vars, e.g. try{...}catch(_0x5f3b1c)
        re.compile(r'const\s+_?0x[0-9a-fA-F]{6,}\s*=\s*_?0x[0-9a-fA-F]{6,}', re.IGNORECASE),  # Constant assignments with obfuscated names, e.g. const _0x5f3b1c = _0x5f3b1d 
        re.compile(r'_?0x[0-9a-fA-F]{6,}\(_?0x[0-9a-fA-F]{6,}'),                              # Function calls with hex parameters, e.g. _0x5f3b1c(0x58e7a2
        # \s for spaces
        # + at least one
        # * zero or more
        # ? facoltative
        # . matches any character except newline
        # re.IGNORECASE for case insensitive, re.DOTALL to match newlines  
    ]

    PLATFORM_PATTERNS: List[Pattern] = [
        # process.platform() == 'win32'  platform === "linux"
        # .arch() returns the CPU architecture of the operating system on which Node.js is running
        re.compile(
            r'(?:'
            r'(\w+\.)?platform\(?\)?\s*[!=]==?\s*[\'"](?:win(?:32|64|dows)?|linux|darwin|mac(?:os)?)[\'"]|'
            r'\w*\.arch\s*\(\s*\)'
            r')',
            re.IGNORECASE
        ),
        # [!=]==? -> ==, ===, !=, !==
        # \' for escape
        # darwin  macOS
        # (?:...) non-capturing group, best performance, do not allocate memory to capture the group
    ]

    def analyze(self, content: str, package_info: Dict) -> EvasionMetrics:
        evasion = EvasionMetrics()
        if not content:
            return evasion
        
        if self._detect_minified_code(package_info['file_name']):
            #synchronized_print(f"Minified code detected: {package_info['file_name']}")
            evasion.code_type = CodeType.MINIFIED
            content = self.unminify_code(content)
            #synchronized_print("Code unminified")

        evasion.obfuscation_patterns_count, evasion.list_obfuscation_patterns = UtilsForAnalyzer.detect_patterns(content, self.OBFUSCATION_PATTERNS)
        evasion.platform_detections_count, evasion.list_platform_detections = UtilsForAnalyzer.detect_patterns(content, self.PLATFORM_PATTERNS)

        
        if package_info['info'] == SourceType.DEOBFUSCATED:
            evasion.code_type = CodeType.DEOBFUSCATED
        elif (self._detect_obfuscated_code(evasion.obfuscation_patterns_count, max(len(r) for r in content.splitlines() ) if content.splitlines() else 0 )):
            evasion.code_type = CodeType.OBFUSCATED
        else:
            evasion.code_type = CodeType.CLEAR
        return evasion
    
    @staticmethod
    def _detect_obfuscated_code(obfuscation_patterns_count: int, longest_line_length: int) -> bool:
        """Detect if code is obfuscated"""
        #Simple heuristic checks for obfuscation
        return obfuscation_patterns_count > 15 and longest_line_length > 30000           # Thresholds for obfuscation detection
    
    @staticmethod
    def _detect_minified_code(file_name: str) -> bool:
        """Detect if code is minified"""
        return file_name.endswith('.min.js')

    def unminify_code(self, content: str) -> str:
        """Attempt to unminify code"""
        return jsbeautifier.beautify(content)