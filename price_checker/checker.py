"""Run a target across multiple regions and compare the resulting prices."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Optional

import requests

from .config import Region, Target
from .scraper import PriceNotFoundError, ScrapeResult, fetch_price


@dataclass(frozen=True)
class RegionResult:
    region: Region
    result: Optional[ScrapeResult] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.result is not None


@dataclass(frozen=True)
class CheckReport:
    target: Target
    region_results: List[RegionResult]

    @property
    def successful(self) -> List[RegionResult]:
        return [r for r in self.region_results if r.ok]

    @property
    def cheapest(self) -> Optional[RegionResult]:
        successes = self.successful
        if not successes:
            return None
        return min(successes, key=lambda r: r.result.price)

    @property
    def most_expensive(self) -> Optional[RegionResult]:
        successes = self.successful
        if not successes:
            return None
        return max(successes, key=lambda r: r.result.price)

    @property
    def spread(self) -> Optional[float]:
        """Difference between the most expensive and cheapest price found."""
        cheapest, priciest = self.cheapest, self.most_expensive
        if cheapest is None or priciest is None:
            return None
        return priciest.result.price - cheapest.result.price


def _fetch_region(target: Target, region: Region, fetch_kwargs: dict) -> RegionResult:
    try:
        result = fetch_price(
            target.url,
            price_selector=target.price_selector,
            price_regex=target.price_regex,
            proxies=region.proxies(),
            headers=target.headers,
            **fetch_kwargs,
        )
        return RegionResult(region=region, result=result)
    except (requests.RequestException, PriceNotFoundError, ValueError, OSError) as exc:
        return RegionResult(region=region, error=str(exc))


def check_target(
    target: Target,
    regions: List[Region],
    *,
    max_workers: Optional[int] = None,
    **fetch_kwargs,
) -> CheckReport:
    """Fetch ``target`` once per region (in parallel) and build a :class:`CheckReport`.

    Regions are fetched concurrently with a thread pool since the dominant
    cost is network I/O through each region's proxy; results are returned
    in the same order as ``regions`` regardless of completion order.
    """

    if not regions:
        return CheckReport(target=target, region_results=[])

    workers = max_workers or len(regions)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        region_results = list(
            executor.map(
                lambda region: _fetch_region(target, region, fetch_kwargs), regions
            )
        )

    return CheckReport(target=target, region_results=region_results)


def run_check(
    targets: List[Target],
    regions: List[Region],
    *,
    max_workers: Optional[int] = None,
    **fetch_kwargs,
) -> List[CheckReport]:
    """Check every target against every region."""

    return [
        check_target(target, regions, max_workers=max_workers, **fetch_kwargs)
        for target in targets
    ]
