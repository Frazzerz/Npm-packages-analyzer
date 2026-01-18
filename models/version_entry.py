from dataclasses import dataclass
from enum import Enum

class SourceType(Enum):
    TARBALL = "tarball"
@dataclass
class VersionEntry:
    '''Represents a specific version entry of a package'''
    name: str           # e.g. 1.1.2, 1.1.1-local, 2.1.0-candidate, posthog-node@5.18.0
    source: SourceType
    ref: object         # Local Path