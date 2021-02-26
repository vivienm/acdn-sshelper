from dataclasses import dataclass
from ipaddress import IPv4Address
from typing import Optional

from .zone import Zone


@dataclass(frozen=True)
class Instance:
    """A Google cloud instance."""

    name: str
    zone: Zone
    internal_ip: IPv4Address
    external_ip: Optional[IPv4Address]
