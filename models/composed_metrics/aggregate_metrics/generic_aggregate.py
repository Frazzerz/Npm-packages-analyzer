from typing import List
from dataclasses import dataclass, field
from ...code_type import CodeType
@dataclass
class GenericVersion:
    """For a single version"""
    total_files: int = 0
    list_file_types: List[str] = field(default_factory=list)
    len_list_file_types_unique: int = 0  # to be computed after aggregation
    total_dim_bytes_pkg: int = 0         # to be computed after aggregation
    total_plain_text_files: int = 0      # to be computed after aggregation
    total_dim_plain_text_files: int = 0  # to be computed after aggregation
    total_other_files: int = 0           # to be computed after aggregation
    total_dim_bytes_other_files: int = 0 # to be computed after aggregation
    total_number_of_characters: int = 0
    weighted_avg_blank_space_and_character_ratio: float = 0
    weighted_avg_shannon_entropy: float = 0
    longest_line_length: int = 0
    code_types: List[CodeType] = field(default_factory=list)
    len_list_code_types_unique: int = 0  # to be computed after aggregation