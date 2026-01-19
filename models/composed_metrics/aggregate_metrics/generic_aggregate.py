from typing import List
from dataclasses import dataclass, field
from ...code_type import CodeType
@dataclass
class GenericVersion:
    """For a single version"""
    total_files: int = 0
    list_file_types: List[str] = field(default_factory=list)
    len_list_file_types_unique: int = 0                         # to be computed after aggregation
    total_dim_bytes_pkg: int = 0                                # to be computed after aggregation
    total_plain_text_files: int = 0                             # to be computed after aggregation
    total_dim_plain_text_files: int = 0                         # to be computed after aggregation
    total_other_files: int = 0                                  # to be computed after aggregation
    total_dim_bytes_other_files: int = 0                        # to be computed after aggregation

    total_number_of_characters: int = 0                         # All characters including comments, number_of_characters
    total_number_of_non_blank_lines: int = 0                    # Comments + code lines (no blank lines)
    total_number_of_comments: int = 0
    
    total_number_of_characters_no_comments: int = 0             # All characters excluding comments
    total_number_of_non_blank_lines_no_comments: int = 0        # No comments, no blank lines
    longest_line_length_no_comments: int = 0
    code_types: List[CodeType] = field(default_factory=list)
    len_list_code_types_unique: int = 0                         # to be computed after aggregation

    # Deltas is difference between original and no comments
    weighted_avg_shannon_entropy_original: float = 0.0
    weighted_avg_shannon_entropy_no_comments: float = 0.0
    entropy_delta: float = 0.0

    total_number_of_printable_characters: int = 0               # All printable characters including comments
    total_number_of_printable_characters_no_comments: int = 0   # All printable characters excluding comments
    total_number_of_whitespace_characters: int = 0              # All whitespace characters including comments
    total_number_of_whitespace_characters_no_comments: int = 0  # All whitespace characters excluding comments
    weighted_avg_blank_space_and_character_ratio_original: float = 0.0
    weighted_avg_blank_space_and_character_ratio_no_comments: float = 0.0
    blank_space_ratio_delta: float = 0.0
