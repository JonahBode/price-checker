from unittest.mock import Mock

import pytest

from price_checker.scraper import PriceNotFoundError, fetch_price


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _fake_session(html):
    session = Mock()
    session.get.return_value = FakeResponse(html)
    return session


def test_fetch_price_with_selector():
    html = "<html><body><span class='price'>$123.45</span></body></html>"
    session = _fake_session(html)

    result = fetch_price(
        "https://example.com/item",
        price_selector=".price",
        proxies={"http": "http://proxy:8080", "https": "http://proxy:8080"},
        session=session,
    )

    assert result.price == 123.45
    assert result.currency == "$"
    session.get.assert_called_once()
    _, kwargs = session.get.call_args
    assert kwargs["proxies"] == {"http": "http://proxy:8080", "https": "http://proxy:8080"}


def test_fetch_price_with_regex_fallback():
    html = "<html><body>Total price: 4,999</body></html>"
    session = _fake_session(html)

    result = fetch_price(
        "https://example.com/item",
        price_selector=".missing",
        price_regex=r"Total price:\s*([\d,.]+)",
        session=session,
    )

    assert result.price == 4999.0


def test_fetch_price_raises_when_not_found():
    html = "<html><body><span class='other'>no price</span></body></html>"
    session = _fake_session(html)

    with pytest.raises(PriceNotFoundError):
        fetch_price("https://example.com/item", price_selector=".price", session=session)


def test_fetch_price_requires_selector_or_regex():
    with pytest.raises(ValueError):
        fetch_price("https://example.com/item")
