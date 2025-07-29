from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    path: str
    scale: int
    algo: str
