from dataclasses import dataclass, field
from typing import List
@dataclass
class EvasionMetrics:
    obfuscation_patterns_count: int = 0
    list_obfuscation_patterns: List[str] = field(default_factory=list)
    len_list_obfuscation_patterns_unique: int = 0
    possible_obfuscated: bool = False
    platform_detections_count: int = 0
    list_platform_detections: List[str] = field(default_factory=list)
    len_list_platform_detections_unique: int = 0