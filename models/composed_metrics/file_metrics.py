from dataclasses import dataclass, field
from ..domains import GenericMetrics, EvasionMetrics, CryptoMetrics #PayloadMetrics, ExfiltrationMetrics,

@dataclass
class FileMetrics:
    """Metrics for a single file (all int variables represent counts, unless otherwise specified)"""
    package: str = ""
    version: str = ""
    file_path: str = ""
    generic: GenericMetrics = field(default_factory=GenericMetrics)
    evasion: EvasionMetrics = field(default_factory=EvasionMetrics)
    #payload: PayloadMetrics = field(default_factory=PayloadMetrics)
    #exfiltration: ExfiltrationMetrics = field(default_factory=ExfiltrationMetrics)
    crypto: CryptoMetrics = field(default_factory=CryptoMetrics)