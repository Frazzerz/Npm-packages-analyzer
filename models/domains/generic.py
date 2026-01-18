from dataclasses import dataclass
from ..code_type import CodeType
@dataclass
class GenericMetrics:
    file_type: str = "" # Magika detect file type
    size_bytes: int = 0
    number_of_characters: int = 0
    blank_space_and_character_ratio: float = 0.0
    shannon_entropy: float = 0.0
    longest_line_length: int = 0
    number_of_non_empty_lines: int = 0
    code_type: CodeType = CodeType.NONE