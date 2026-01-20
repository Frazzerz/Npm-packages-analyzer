from dataclasses import dataclass, field
from typing import List
@dataclass
class EvasionVersion:
    """For a single version"""
    obfuscation_patterns_count: int = 0
    list_obfuscation_patterns: List[str] = field(default_factory=list)
    len_list_obfuscation_patterns_unique: int = 0  # to be computed after aggregation
    list_possible_presence_of_obfuscated_files: List[str] = field(default_factory=list)     # experimental porpuse
    len_list_possible_presence_of_obfuscated_files_unique: int = 0  # experimental porpuse, to be computed after aggregation
    platform_detections_count: int = 0
    list_platform_detections: List[str] = field(default_factory=list)
    len_list_platform_detections_unique: int = 0   # to be computed after aggregation