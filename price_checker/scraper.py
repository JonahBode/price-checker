"""Fetch a page (optionally through a proxy) and extract a price from it."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; price-checker/0.1; "
    "+https://github.com/JonahBode/price-checker)"
)

# A reasonably common subset of ISO 4217 currency codes. Restricting the
# 3-letter currency match to this list avoids false positives like "SKU 123"
# being parsed as currency "SKU".
_ISO_CURRENCY_CODES = (
    "USD|EUR|GBP|JPY|CNY|INR|VND|AUD|CAD|CHF|HKD|SGD|SEK|NOK|DKK|NZD|"
    "KRW|MXN|BRL|ZAR|THB|IDR|MYR|PHP|TRY|RUB|AED|SAR|PLN|CZK"
)

# Matches things like "$1,234.56", "1.234,56 EUR", "Rs. 4999", "1234"
_PRICE_PATTERN = re.compile(
    rf"(?P<currency>[€£$¥₹]|\b(?:{_ISO_CURRENCY_CODES})\b)?\s*"
    r"(?P<amount>\d[\d,.\s]*\d|\d)"
    rf"\s*(?P<currency_suffix>[€£$¥₹]|\b(?:{_ISO_CURRENCY_CODES})\b)?"
)


class PriceNotFoundError(RuntimeError):
    """Raised when a price could not be located/parsed on a page."""


@dataclass(frozen=True)
class ScrapeResult:
    url: str
    raw_text: str
    price: float
    currency: Optional[str] = None


def _normalize_amount(amount: str) -> float:
    """Turn a human formatted number into a float.

    Handles both ``1,234.56`` (US) and ``1.234,56`` (EU) style grouping.
    """

    amount = amount.strip()
    if "," in amount and "." in amount:
        if amount.rfind(",") > amount.rfind("."):
            # European style: '.' thousands, ',' decimal
            amount = amount.replace(".", "").replace(",", ".")
        else:
            # US style: ',' thousands, '.' decimal
            amount = amount.replace(",", "")
    elif "," in amount:
        # Ambiguous: treat as thousands separator unless it looks like a
        # decimal (exactly two digits after the comma).
        head, _, tail = amount.rpartition(",")
        if len(tail) == 2:
            amount = amount.replace(",", ".")
        else:
            amount = amount.replace(",", "")
    return float(amount.replace(" ", ""))


def extract_price(text: str) -> ScrapeResult:
    """Extract a price from a snippet of text.

    Raises :class:`PriceNotFoundError` if no price-like substring is found.
    """

    match = _PRICE_PATTERN.search(text)
    if not match:
        raise PriceNotFoundError(f"could not find a price in {text!r}")

    amount_str = match.group("amount")
    try:
        amount = _normalize_amount(amount_str)
    except ValueError as exc:
        raise PriceNotFoundError(f"could not parse amount from {text!r}") from exc

    currency = match.group("currency") or match.group("currency_suffix")
    return ScrapeResult(url="", raw_text=text.strip(), price=amount, currency=currency)


def fetch_price(
    url: str,
    *,
    price_selector: Optional[str] = None,
    price_regex: Optional[str] = None,
    proxies: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: float = 20.0,
    session: Optional[requests.Session] = None,
) -> ScrapeResult:
    """Fetch ``url`` (optionally through ``proxies``) and extract a price.

    Either ``price_selector`` (a CSS selector resolved with BeautifulSoup)
    or ``price_regex`` (applied to the full page text) must be provided.
    If both are given, the selector is tried first and the regex is used
    as a fallback.
    """

    if not price_selector and not price_regex:
        raise ValueError("must provide price_selector and/or price_regex")

    req_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        req_headers.update(headers)

    http = session or requests
    response = http.get(url, proxies=proxies, headers=req_headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    snippet = None
    selector_status = None
    if price_selector:
        element = soup.select_one(price_selector)
        if element is None:
            selector_status = f"selector {price_selector!r} matched no element"
        else:
            snippet = element.get_text(" ", strip=True)
            if not snippet:
                selector_status = f"selector {price_selector!r} matched an empty element"

    if not snippet and price_regex:
        match = re.search(price_regex, response.text)
        if match:
            snippet = match.group(0)

    if not snippet:
        tried = []
        if selector_status:
            tried.append(selector_status)
        elif price_selector:
            tried.append(f"selector {price_selector!r}")
        if price_regex:
            tried.append(f"regex {price_regex!r} matched no text")
        raise PriceNotFoundError(
            f"no price found on {url} (tried {' and '.join(tried)})"
        )

    result = extract_price(snippet)
    return ScrapeResult(
        url=url, raw_text=result.raw_text, price=result.price, currency=result.currency
    )
