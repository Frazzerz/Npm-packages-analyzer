from dataclasses import dataclass, field
from typing import List

@dataclass
class PayloadMetrics:
    timing_delays_count: int = 0
    list_timing_delays: List[str] = field(default_factory=list)
    len_list_timing_delays_unique: int = 0
    eval_count: int = 0
    list_eval: List[str] = field(default_factory=list)
    len_list_eval_unique: int = 0
    shell_commands_count: int = 0
    list_shell_commands: List[str] = field(default_factory=list)
    len_list_shell_commands_unique: int = 0
    preinstall_scripts: List[str] = field(default_factory=list)