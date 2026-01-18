import math
from typing import Tuple
from models.domains import GenericMetrics
from utils import synchronized_print
import jsbeautifier
from models import CodeType

class GenericAnalyzer:
    """Obtain generic metrics from files"""

    def pre_analyze(self, content: str) -> Tuple[int, int, bool]:
        """Pre-analyze to get longest line length, number of non-empty lines, and detect if minified"""
        number_of_non_empty_lines = len([r for r in content.splitlines() if r.strip()])
        longest_line_length = max(len(r) for r in content.splitlines()) if content.splitlines() else 0
        minified = self._detect_minified_code(longest_line_length, number_of_non_empty_lines)
        return longest_line_length, number_of_non_empty_lines, minified

    def analyze(self, content: str, longest_line_length: int, number_of_non_empty_lines: int, minified: bool) -> GenericMetrics:
        generic = GenericMetrics()
        
        if not minified:
            generic.code_type = CodeType.CLEAR
            generic.longest_line_length = longest_line_length
            generic.number_of_non_empty_lines = number_of_non_empty_lines
        else:
            generic.code_type = CodeType.MINIFIED
            generic.longest_line_length = max(len(r) for r in content.splitlines()) if content.splitlines() else 0
            generic.number_of_non_empty_lines = len([r for r in content.splitlines() if r.strip()])
        
        generic.number_of_characters = len(content)
        whitespace_count = sum(1 for c in content if c.isspace())
        generic.blank_space_and_character_ratio = whitespace_count / generic.number_of_characters if generic.number_of_characters else 0.0
        generic.shannon_entropy = self._calculate_shannon_entropy(content)
        
        
        return generic

    def _calculate_shannon_entropy(self, content: str) -> float:
        """Calculate Shannon entropy of the content"""
        if not content:
            return 0.0

        # Calculate frequency of each character in the content
        freq = {}
        for char in content:
            freq[char] = freq.get(char, 0) + 1

        # Calculate the Shannon entropy
        entropy = 0.0
        length = len(content)
        for count in freq.values():
            probability = count / length
            entropy -= probability * math.log2(probability)

        return entropy
    
    def _detect_minified_code(self, longest_line_length: int, number_of_non_empty_lines: int) -> bool:
        """Detect if code is minified"""
        return longest_line_length > 500 and number_of_non_empty_lines < 5
    
    @staticmethod
    def unminify_code(content: str) -> str:
        """Attempt to unminify code"""
        return jsbeautifier.beautify(content)