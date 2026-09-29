# price-checker

Check whether a website shows different (dynamic) prices depending on
where the request appears to come from -- for example, comparing flight
or hotel prices as seen from the US, India, or Vietnam.

This tool does **not** manage VPN connections for you. Instead, you
point it at proxy servers (HTTP or SOCKS) located in the regions you
want to test from -- many VPN providers and commercial proxy services
expose such endpoints. `price_checker` then fetches each configured
page through every region's proxy and reports the extracted price side
by side, so you can see the spread and the cheapest region.

## Install

```bash
pip install -r requirements.txt
```

## Configure

Create a JSON config describing your regions (proxies) and targets
(pages + how to find the price on them). See
[`config.example.json`](config.example.json):

```json
{
  "regions": [
    { "name": "local", "proxy": null },
    { "name": "india", "proxy": "http://in-proxy.example.com:8080" },
    { "name": "vietnam", "proxy": "socks5h://vn-proxy.example.com:1080" }
  ],
  "targets": [
    {
      "name": "Example flight search",
      "url": "https://example.com/flights?from=JFK&to=DEL",
      "price_selector": ".price-total"
    }
  ]
}
```

* `proxy: null` (or omitted) issues the request directly with no proxy
  -- useful as your local/control baseline.
* `price_selector` is a CSS selector (resolved with BeautifulSoup)
  pointing at the element containing the price.
* `price_regex` can be used instead of, or as a fallback to,
  `price_selector` -- it is matched against the raw page HTML/text.

## Run

```bash
python -m price_checker config.example.json
python -m price_checker config.example.json --csv results.csv
```

For each target this prints the price seen from every region, flags
any region that failed to load, and highlights the cheapest region and
the price spread.

Exit codes: `0` if every region/target succeeded, `1` if none
succeeded, `2` if some (but not all) region/target checks failed --
handy for detecting partial failures in scripts/CI.

## Notes & limitations

* Respect the target website's terms of service and `robots.txt`
  before scraping it.
* Some sites vary price based on signals other than IP geolocation
  (account history, device, currency/locale cookies, etc.), so results
  should be treated as a starting point for investigation, not proof.
* Proxy reliability varies a lot by provider; a region reporting an
  error usually means the proxy itself failed, not that the price is
  unavailable.
