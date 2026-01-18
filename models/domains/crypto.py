from dataclasses import dataclass, field
from typing import List

@dataclass
class CryptoMetrics:
    crypto_addresses: int = 0
    list_crypto_addresses: List[str] = field(default_factory=list)
    cryptocurrency_name: int = 0
    list_cryptocurrency_names: List[str] = field(default_factory=list)
    wallet_detection: int = 0
    wallet_detection_list: List[str] = field(default_factory=list)
    replaced_crypto_addresses: int = 0
    replaced_crypto_addresses_list: List[str] = field(default_factory=list)
    hook_provider: int = 0