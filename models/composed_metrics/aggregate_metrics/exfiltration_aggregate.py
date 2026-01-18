from dataclasses import dataclass, field
from typing import List

@dataclass
class ExfiltrationVersion:
    """For a single version"""
    scan_functions_count: int = 0
    list_scan_functions: List[str] = field(default_factory=list)
    len_list_scan_functions_unique: int = 0  # to be computed after aggregation
    sensitive_elements_count: int = 0
    list_sensitive_elements: List[str] = field(default_factory=list)
    len_list_sensitive_elements_unique: int = 0  # to be computed after aggregation
    data_transmission_count: int = 0
    list_data_transmissions: List[str] = field(default_factory=list)
    len_list_data_transmissions_unique: int = 0  # to be computed after aggregation