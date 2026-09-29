"""Run a target across multiple regions and compare the resulting prices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import Region, Target
from .scraper import ScrapeResult, fetch_price


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


def check_target(target: Target, regions: List[Region], **fetch_kwargs) -> CheckReport:
    """Fetch ``target`` once per region and build a :class:`CheckReport`."""

    region_results: List[RegionResult] = []
    for region in regions:
        try:
            result = fetch_price(
                target.url,
                price_selector=target.price_selector,
                price_regex=target.price_regex,
                proxies=region.proxies(),
                headers=target.headers,
                **fetch_kwargs,
            )
            region_results.append(RegionResult(region=region, result=result))
        except Exception as exc:  # noqa: BLE001 - report per-region failures
            region_results.append(RegionResult(region=region, error=str(exc)))

    return CheckReport(target=target, region_results=region_results)


def run_check(targets: List[Target], regions: List[Region], **fetch_kwargs) -> List[CheckReport]:
    """Check every target against every region."""

    return [check_target(target, regions, **fetch_kwargs) for target in targets]
