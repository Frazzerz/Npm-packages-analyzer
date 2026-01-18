from dataclasses import dataclass, field
from typing import List

@dataclass
class CryptoVersion:
    """For a single version"""
    crypto_addresses: int = 0
    list_crypto_addresses: List[str] = field(default_factory=list)
    len_list_crypto_addresses_unique: int = 0      # to be computed after aggregation
    cryptocurrency_name: int = 0
    list_cryptocurrency_names: List[str] = field(default_factory=list)
    len_list_cryptocurrency_names_unique: int = 0  # to be computed after aggregation
    wallet_detection: int = 0
    replaced_crypto_addresses: int = 0
    hook_provider: int = 0