"""price_checker: check dynamic pricing for a page across multiple VPN/proxy regions."""

from .config import Region, Target, load_config
from .scraper import PriceNotFoundError, ScrapeResult, fetch_price
from .checker import CheckReport, RegionResult, run_check

__all__ = [
    "Region",
    "Target",
    "load_config",
    "PriceNotFoundError",
    "ScrapeResult",
    "fetch_price",
    "CheckReport",
    "RegionResult",
    "run_check",
]

__version__ = "0.1.0"
