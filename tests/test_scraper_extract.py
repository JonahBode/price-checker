import pytest

from price_checker.scraper import PriceNotFoundError, extract_price


@pytest.mark.parametrize(
    "text,expected_price,expected_currency",
    [
        ("$1,234.56", 1234.56, "$"),
        ("1.234,56 EUR", 1234.56, "EUR"),
        ("Rs. 4999", 4999.0, None),
        ("Total: 999", 999.0, None),
        ("₹ 45,000", 45000.0, "₹"),
        ("SKU 123", 123.0, None),
    ],
)
def test_extract_price(text, expected_price, expected_currency):
    result = extract_price(text)
    assert result.price == expected_price
    assert result.currency == expected_currency


def test_extract_price_not_found():
    with pytest.raises(PriceNotFoundError):
        extract_price("no numbers here")
