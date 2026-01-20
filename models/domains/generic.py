from dataclasses import dataclass
from ..code_type import CodeType
@dataclass
class GenericMetrics:
    file_type: str = ""                                         # Magika detect file type
    is_plain_text_file: bool = False                            # Valid file for analysis
    size_bytes: int = 0
    
    number_of_characters: int = 0                               # All characters including comments and blank characters
    total_number_of_non_blank_lines: int = 0                    # Comments + code lines (no blank lines)
    number_of_comments: int = 0

    # After removing comments
    number_of_characters_no_comments: int = 0                   # All characters excluding comments
    number_of_non_blank_lines_no_comments: int = 0              # No comments, no blank lines
    longest_line_length_no_comments: int = 0
    code_type: CodeType = CodeType.NONE
    
    number_of_characters_no_comments_unminified: int = 0
    shannon_entropy_original: float = 0.0
    shannon_entropy_no_comments: float = 0.0
    shannon_entropy_no_comments_unminified: float = 0.0

    number_of_printable_characters: int = 0                     # All printable characters including comments
    number_of_printable_characters_no_comments: int = 0         # All printable characters excluding comments
    #number_of_printable_characters_no_comments_minified: int = 0   # == number_of_printable_characters_no_comments
    number_of_whitespace_characters: int = 0                    # All whitespace characters including comments
    number_of_whitespace_characters_no_comments: int = 0        # All whitespace characters excluding comments
    number_of_whitespace_characters_no_comments_minified: int = 0
    blank_space_and_character_ratio_original: float = 0.0
    blank_space_and_character_ratio_no_comments: float = 0.0
    blank_space_and_character_ratio_no_comments_unminified: float = 0.0