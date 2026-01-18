from dataclasses import dataclass, field
from typing import List

@dataclass
class PayloadMetrics:
    timing_delays_count: int = 0
    list_timing_delays: List[str] = field(default_factory=list)
    eval_count: int = 0
    list_eval: List[str] = field(default_factory=list)
    shell_commands_count: int = 0
    list_shell_commands: List[str] = field(default_factory=list)
    preinstall_scripts: List[str] = field(default_factory=list)