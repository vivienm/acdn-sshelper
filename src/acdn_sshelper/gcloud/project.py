from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    """A Google cloud project."""

    id_: str
    name: str
