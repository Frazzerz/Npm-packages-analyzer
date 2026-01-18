from dataclasses import dataclass, field
from .aggregate_metrics.generic_aggregate import GenericVersion
from .aggregate_metrics.evasion_aggregate import EvasionVersion
from .aggregate_metrics.payload_aggregate import PayloadVersion
from .aggregate_metrics.exfiltration_aggregate import ExfiltrationVersion
from .aggregate_metrics.crypto_aggregate import CryptoVersion

@dataclass
class VersionMetrics:
    """Aggregated metrics for a specific package version"""
    package: str = ""
    version: str = ""
    
    generic: GenericVersion = field(default_factory=GenericVersion)
    evasion: EvasionVersion = field(default_factory=EvasionVersion)
    payload: PayloadVersion = field(default_factory=PayloadVersion)
    exfiltration: ExfiltrationVersion = field(default_factory=ExfiltrationVersion)
    crypto: CryptoVersion = field(default_factory=CryptoVersion)