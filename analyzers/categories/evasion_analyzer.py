import re
from typing import List, Pattern
from utils import UtilsForAnalyzer
from models.domains import EvasionMetrics
from utils import synchronized_print
class EvasionAnalyzer:
    """Analyze evasion techniques"""

    OBFUSCATION_PATTERNS: List[Pattern] = [
        re.compile(r'_?0x[0-9a-fA-F]{6,}'),                                                   # Hexadecimal values and variables (at least 6 hex values), e.g. 0x58e7a2 or _0x5f3b1c
        re.compile(r'parseInt\(_?0x[0-9a-fA-F]{6,}', re.IGNORECASE),                          # ParseInt with hexadecimals, e.g. parseInt(0x58e7a2
        re.compile(r'try\{.{0,1000}?\}catch\(_?0x[0-9a-fA-F]{6,}\)', re.IGNORECASE | re.DOTALL),  # limit 1000 chars inside try-catch to avoid performance issues
        #re.compile(r'try\{.*?\}catch\(_?0x[0-9a-fA-F]{6,}\)', re.IGNORECASE),                 # Try-catch blocks with obfuscated vars, e.g. try{...}catch(_0x5f3b1c)
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
            r'(?:\w{1,30}\.)?platform\(?\)?\s*[!=]==?\s*[\'"](?:win(?:32|64|dows)?|linux|darwin|mac(?:os)?)[\'"]|'  # Limit \w+
            r'\w{0,30}\.arch\s*\(\s*\)'  # Limit \w*
            r')',
            re.IGNORECASE
        ),
        # [!=]==? -> ==, ===, !=, !==
        # \' for escape
        # darwin  macOS
        # (?:...) non-capturing group, best performance, do not allocate memory to capture the group
    ]
    '''
    re.compile(
            r'(?:'
            r'(\w+\.)?platform\(?\)?\s*[!=]==?\s*[\'"](?:win(?:32|64|dows)?|linux|darwin|mac(?:os)?)[\'"]|'
            r'\w*\.arch\s*\(\s*\)'
            r')',
            re.IGNORECASE
        ),
    '''

    def analyze(self, content: str, longest_line_length: int) -> EvasionMetrics:
        evasion = EvasionMetrics()

        evasion.obfuscation_patterns_count, evasion.list_obfuscation_patterns = UtilsForAnalyzer.detect_patterns(content, self.OBFUSCATION_PATTERNS)
        evasion.len_list_obfuscation_patterns_unique = len(set(evasion.list_obfuscation_patterns))
        evasion.platform_detections_count, evasion.list_platform_detections = UtilsForAnalyzer.detect_patterns(content, self.PLATFORM_PATTERNS)
        evasion.len_list_platform_detections_unique = len(set(evasion.list_platform_detections))
        evasion.possible_obfuscated = self._detect_obfuscated_code(evasion.obfuscation_patterns_count, longest_line_length)
        
        return evasion
    
    @staticmethod
    def _detect_obfuscated_code(obfuscation_patterns_count: int, longest_line_length: int) -> bool:
        """Detect if code is obfuscated"""
        #Simple heuristic and threshold to checks one of obfuscation pattern. Experimental field
        return obfuscation_patterns_count > 15 and longest_line_length > 200