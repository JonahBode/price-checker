import io
import json

from price_checker import cli
from price_checker.checker import CheckReport, RegionResult
from price_checker.config import Region, Target
from price_checker.scraper import ScrapeResult


def _sample_report():
    target = Target(name="Flight", url="https://example.com", price_selector=".price")
    us = RegionResult(region=Region(name="us"), result=ScrapeResult("u", "", 200.0, "USD"))
    india = RegionResult(region=Region(name="india"), result=ScrapeResult("u", "", 120.0, "USD"))
    failed = RegionResult(region=Region(name="broken"), error="connection refused")
    return CheckReport(target=target, region_results=[us, india, failed])


def test_format_report_contains_cheapest_and_error():
    text = cli._format_report(_sample_report())
    assert "cheapest region: india" in text
    assert "connection refused" in text


def test_write_csv_rows():
    buf = io.StringIO()
    cli._write_csv([_sample_report()], buf)
    lines = buf.getvalue().splitlines()
    assert lines[0] == "target,url,region,price,currency,error"
    assert any("india" in line and "120.0" in line for line in lines)
    assert any("broken" in line and "connection refused" in line for line in lines)


def test_main_runs_end_to_end(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "regions": [{"name": "local", "proxy": None}],
                "targets": [
                    {
                        "name": "Flight",
                        "url": "https://example.com",
                        "price_selector": ".price",
                    }
                ],
            }
        )
    )

    monkeypatch.setattr(
        "price_checker.checker.fetch_price",
        lambda *a, **kw: ScrapeResult("u", "$10", 10.0, "$"),
    )

    exit_code = cli.main([str(config_path)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Flight" in out
    assert "cheapest region: local" in out


def test_main_returns_partial_failure_exit_code(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "regions": [
                    {"name": "local", "proxy": None},
                    {"name": "broken", "proxy": "http://dead-proxy:1"},
                ],
                "targets": [
                    {
                        "name": "Flight",
                        "url": "https://example.com",
                        "price_selector": ".price",
                    }
                ],
            }
        )
    )

    def fake_fetch_price(url, *, proxies=None, **kwargs):
        if proxies:
            raise OSError("proxy unreachable")
        return ScrapeResult("u", "$10", 10.0, "$")

    monkeypatch.setattr("price_checker.checker.fetch_price", fake_fetch_price)

    exit_code = cli.main([str(config_path)])

    assert exit_code == 2


def test_main_returns_failure_exit_code_when_all_regions_fail(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "regions": [{"name": "local", "proxy": None}],
                "targets": [
                    {
                        "name": "Flight",
                        "url": "https://example.com",
                        "price_selector": ".price",
                    }
                ],
            }
        )
    )

    def fake_fetch_price(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr("price_checker.checker.fetch_price", fake_fetch_price)

    exit_code = cli.main([str(config_path)])

    assert exit_code == 1


def test_main_returns_error_exit_code_for_missing_config(tmp_path, capsys):
    missing_path = tmp_path / "does-not-exist.json"

    exit_code = cli.main([str(missing_path)])

    assert exit_code == 3
    err = capsys.readouterr().err
    assert "failed to load config" in err


def test_main_returns_error_exit_code_for_invalid_config(tmp_path, capsys):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"regions": [], "targets": []}))

    exit_code = cli.main([str(config_path)])

    assert exit_code == 3
    err = capsys.readouterr().err
    assert "failed to load config" in err
