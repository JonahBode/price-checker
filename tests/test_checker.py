from price_checker.checker import check_target, run_check
from price_checker.config import Region, Target
from price_checker.scraper import ScrapeResult


def _target():
    return Target(name="Flight", url="https://example.com", price_selector=".price")


def test_check_target_success_and_failure(monkeypatch):
    regions = [Region(name="us"), Region(name="india", proxy="http://p:1")]

    def fake_fetch_price(url, *, price_selector=None, price_regex=None, proxies=None, headers=None, **kwargs):
        if proxies is None:
            return ScrapeResult(url=url, raw_text="$100", price=100.0, currency="$")
        raise RuntimeError("proxy timed out")

    monkeypatch.setattr("price_checker.checker.fetch_price", fake_fetch_price)

    report = check_target(_target(), regions)

    assert len(report.region_results) == 2
    us_result, india_result = report.region_results
    assert us_result.ok and us_result.result.price == 100.0
    assert not india_result.ok
    assert "proxy timed out" in india_result.error

    assert report.successful == [us_result]
    assert report.cheapest is us_result
    assert report.most_expensive is us_result
    assert report.spread == 0.0


def test_check_target_computes_spread(monkeypatch):
    regions = [Region(name="us"), Region(name="india", proxy="http://in:1")]

    def fake_fetch_price(url, *, price_selector=None, price_regex=None, proxies=None, headers=None, **kwargs):
        price = 120.0 if proxies else 200.0
        return ScrapeResult(url=url, raw_text="", price=price, currency="USD")

    monkeypatch.setattr("price_checker.checker.fetch_price", fake_fetch_price)

    report = check_target(_target(), regions)

    assert report.cheapest.region.name == "india"
    assert report.most_expensive.region.name == "us"
    assert report.spread == 80.0


def test_run_check_multiple_targets(monkeypatch):
    regions = [Region(name="us")]
    targets = [_target(), Target(name="Hotel", url="https://example.com/h", price_selector=".p")]

    monkeypatch.setattr(
        "price_checker.checker.fetch_price",
        lambda *a, **kw: ScrapeResult(url="u", raw_text="", price=50.0, currency="USD"),
    )

    reports = run_check(targets, regions)
    assert len(reports) == 2
    assert all(r.successful for r in reports)
