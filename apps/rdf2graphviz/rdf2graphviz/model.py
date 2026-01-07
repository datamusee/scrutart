from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Entity:
    uri: str
    label: str
    properties: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class Relation:
    source: str
    predicate: str
    target: str
