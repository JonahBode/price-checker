import pytest

from price_checker.config import Region, Target, load_config


def test_load_config_from_dict():
    config = load_config(
        {
            "regions": [
                {"name": "local", "proxy": None},
                {"name": "india", "proxy": "http://in-proxy:8080"},
            ],
            "targets": [
                {
                    "name": "Flight",
                    "url": "https://example.com/flight",
                    "price_selector": ".price",
                }
            ],
        }
    )

    assert config.regions == [
        Region(name="local", proxy=None),
        Region(name="india", proxy="http://in-proxy:8080"),
    ]
    assert config.targets[0].name == "Flight"
    assert config.targets[0].price_selector == ".price"


def test_region_proxies():
    assert Region(name="local").proxies() is None
    proxied = Region(name="india", proxy="http://p:1")
    assert proxied.proxies() == {"http": "http://p:1", "https": "http://p:1"}


def test_target_requires_selector_or_regex():
    with pytest.raises(ValueError):
        Target(name="bad", url="https://example.com")


def test_load_config_requires_regions_and_targets():
    with pytest.raises(ValueError):
        load_config({"regions": [], "targets": [{"name": "x", "url": "u", "price_selector": "s"}]})

    with pytest.raises(ValueError):
        load_config({"regions": [{"name": "local"}], "targets": []})
