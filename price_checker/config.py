"""Configuration models for price_checker.

A configuration file is a JSON document describing the *regions* (VPN
exit points / proxy servers) to route requests through, and the
*targets* (pages) whose price should be compared across those regions.

Example::

    {
      "regions": [
        {"name": "us", "proxy": null},
        {"name": "india", "proxy": "http://in-proxy.example.com:8080"},
        {"name": "vietnam", "proxy": "socks5h://vn-proxy.example.com:1080"}
      ],
      "targets": [
        {
          "name": "Example flight",
          "url": "https://example.com/flights/123",
          "price_selector": ".price",
          "currency_hint": "USD"
        }
      ]
    }

``proxy`` values are passed straight through to ``requests`` (both the
``http`` and ``https`` schemes use the same proxy URL). Use whatever
VPN/proxy provider you like as long as it exposes an HTTP or SOCKS
proxy endpoint in the region you want to test from -- this project does
not manage VPN connections itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class Region:
    """A named vantage point to issue requests from.

    ``proxy`` should be a proxy URL understood by ``requests``, e.g.
    ``"http://host:port"`` or ``"socks5h://host:port"``. Use ``None`` to
    make the request directly (no proxy), which is useful as a
    baseline/control region.
    """

    name: str
    proxy: Optional[str] = None

    def proxies(self) -> Optional[Dict[str, str]]:
        """Return a ``requests``-compatible proxies mapping."""
        if not self.proxy:
            return None
        return {"http": self.proxy, "https": self.proxy}


@dataclass(frozen=True)
class Target:
    """A single page whose price should be checked."""

    name: str
    url: str
    price_selector: Optional[str] = None
    price_regex: Optional[str] = None
    currency_hint: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.price_selector and not self.price_regex:
            raise ValueError(
                f"target {self.name!r} must define price_selector and/or price_regex"
            )


@dataclass(frozen=True)
class AppConfig:
    regions: List[Region]
    targets: List[Target]


def _region_from_dict(data: Dict[str, Any]) -> Region:
    return Region(name=data["name"], proxy=data.get("proxy"))


def _target_from_dict(data: Dict[str, Any]) -> Target:
    return Target(
        name=data["name"],
        url=data["url"],
        price_selector=data.get("price_selector"),
        price_regex=data.get("price_regex"),
        currency_hint=data.get("currency_hint"),
        headers=dict(data.get("headers", {})),
    )


def load_config(source: Union[str, Path, Dict[str, Any]]) -> AppConfig:
    """Load an :class:`AppConfig` from a JSON file path or an already
    parsed dict (useful for tests)."""

    if isinstance(source, dict):
        data = source
    else:
        data = json.loads(Path(source).read_text(encoding="utf-8"))

    regions = [_region_from_dict(r) for r in data.get("regions", [])]
    targets = [_target_from_dict(t) for t in data.get("targets", [])]

    if not regions:
        raise ValueError("config must define at least one region")
    if not targets:
        raise ValueError("config must define at least one target")

    return AppConfig(regions=regions, targets=targets)
