from dataclasses import dataclass


@dataclass(frozen=True)
class Section:
    name: str
    position: int  # Posición en el listado original, comenzando en 1.
    url: str | None = None
