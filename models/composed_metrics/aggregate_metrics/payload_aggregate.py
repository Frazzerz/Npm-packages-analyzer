from dataclasses import dataclass, field
from typing import List
@dataclass
class PayloadVersion:
    """For a single version"""
    timing_delays_count: int = 0
    list_timing_delays: List[str] = field(default_factory=list)
    len_list_timing_delays_unique: int = 0  # to be computed after aggregation
    eval_count: int = 0
    list_eval: List[str] = field(default_factory=list)
    len_list_eval_unique: int = 0  # to be computed after aggregation
    shell_commands_count: int = 0
    list_shell_commands: List[str] = field(default_factory=list)
    len_list_shell_commands_unique: int = 0  # to be computed after aggregation
    preinstall_scripts: List[str] = field(default_factory=list)