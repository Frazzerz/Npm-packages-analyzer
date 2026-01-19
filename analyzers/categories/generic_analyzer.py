import math
from typing import Tuple
from models.domains import GenericMetrics
from utils import synchronized_print
import jsbeautifier
from models import CodeType

class GenericAnalyzer:
    """Obtain generic metrics from files"""

    def pre_analyze(self, content: str) -> bool:
        """Pre-analyze to detect minified code"""
        total_number_of_non_blank_lines = len([r for r in content.splitlines() if r.strip()])
        longest_line_length = max(len(r) for r in content.splitlines()) if content.splitlines() else 0
        return self._detect_minified_code(longest_line_length, total_number_of_non_blank_lines)

    def pre_analyze_js(self, content: str) -> Tuple[int, int, float, float, int, int]:
        """Pre-analyze JavaScript code to get basic metrics"""
        number_of_characters = len(content)
        total_number_of_non_blank_lines = len([r for r in content.splitlines() if r.strip()])
        shannon_entropy_original = self._calculate_shannon_entropy(content)
        blank_space_and_character_ratio_original, number_of_whitespace_characters, number_of_printable_characters = self._w_p_ratio(content)
        return number_of_characters, total_number_of_non_blank_lines, shannon_entropy_original, blank_space_and_character_ratio_original, number_of_whitespace_characters, number_of_printable_characters

    def analyze(self, content: str, number_of_characters: int, total_number_of_non_blank_lines: int,
                 number_of_comments: int, shannon_entropy_original: float,  blank_space_and_character_ratio_original: float, 
                 number_of_whitespace_characters: int, number_of_printable_characters: int, minified: bool) -> GenericMetrics:
        generic = GenericMetrics()

        if number_of_characters > 0:
            generic.number_of_characters = number_of_characters
            generic.number_of_characters_no_comments = len(content)
        else:
            generic.number_of_characters = len(content)
            generic.number_of_characters_no_comments = generic.number_of_characters

        if total_number_of_non_blank_lines > 0:
            generic.total_number_of_non_blank_lines = total_number_of_non_blank_lines
            generic.number_of_non_blank_lines_no_comments = len([r for r in content.splitlines() if r.strip()])
        else:
            generic.total_number_of_non_blank_lines = len([r for r in content.splitlines() if r.strip()])
            generic.number_of_non_blank_lines_no_comments = generic.total_number_of_non_blank_lines
        
        if number_of_comments > 0:
            generic.number_of_comments = number_of_comments
        else:
            generic.number_of_comments = 0

        if shannon_entropy_original > 0:
            generic.shannon_entropy_original = shannon_entropy_original
            generic.shannon_entropy_no_comments = self._calculate_shannon_entropy(content)
            generic.entropy_delta = generic.shannon_entropy_original - generic.shannon_entropy_no_comments
        else:
            generic.shannon_entropy_original = self._calculate_shannon_entropy(content)
            generic.shannon_entropy_no_comments = generic.shannon_entropy_original
            generic.entropy_delta = 0.0

        if blank_space_and_character_ratio_original > 0:
            generic.blank_space_and_character_ratio_original = blank_space_and_character_ratio_original
            blank_space_and_character_ratio_no_comments, number_of_whitespace_characters_no_comments, number_of_printable_characters_no_comments = self._w_p_ratio(content)
            generic.blank_space_and_character_ratio_no_comments = blank_space_and_character_ratio_no_comments
            generic.blank_space_ratio_delta = generic.blank_space_and_character_ratio_original - generic.blank_space_and_character_ratio_no_comments
            generic.number_of_whitespace_characters = number_of_whitespace_characters
            generic.number_of_whitespace_characters_no_comments = number_of_whitespace_characters_no_comments
            generic.number_of_printable_characters = number_of_printable_characters
            generic.number_of_printable_characters_no_comments = number_of_printable_characters_no_comments
        else:
            generic.blank_space_and_character_ratio_original, generic.number_of_whitespace_characters, generic.number_of_printable_characters = self._w_p_ratio(content)
            generic.blank_space_and_character_ratio_no_comments = generic.blank_space_and_character_ratio_original
            generic.blank_space_ratio_delta = 0.0
            generic.number_of_whitespace_characters_no_comments = generic.number_of_whitespace_characters
            generic.number_of_printable_characters_no_comments = generic.number_of_printable_characters
        #generic.debug_count_characters = generic.number_of_characters - generic.number_of_whitespace_characters - generic.number_of_printable_characters
        #generic.debug_count_characters_no_comments = generic.number_of_characters_no_comments - generic.number_of_whitespace_characters_no_comments - generic.number_of_printable_characters_no_comments

        generic.longest_line_length_no_comments = max(len(r) for r in content.splitlines()) if content.splitlines() else 0
        
        if minified:
            generic.code_type = CodeType.MINIFIED
        else:
            generic.code_type = CodeType.CLEAR

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
    
    def _w_p_ratio(self, content:str) -> float:
        """Calculate the whitespace to printable character ratio"""
        w = sum(1 for c in content if c.isspace())
        #p = sum(1 for c in content if c in string.printable and not c.isspace())
        p = len(content) - w
        w_p_ratio = w / p if p > 0 else float("inf")
        return w_p_ratio, w, p
    
    def _detect_minified_code(self, longest_line_length: int, number_of_non_blank_lines: int) -> bool:
        """Detect if code is minified"""
        return longest_line_length > 500 and number_of_non_blank_lines < 5
    
    @staticmethod
    def unminify_code(content: str) -> str:
        """Attempt to unminify code"""
        return jsbeautifier.beautify(content)