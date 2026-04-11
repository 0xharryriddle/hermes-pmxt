"""Tests for exchange initialization helpers."""

from hermes_pmxt import exchanges


def test_normalize_exchange_name_aliases():
    assert exchanges.normalize_exchange_name("Polymarket US") == "polymarket_us"
    assert exchanges.normalize_exchange_name("polymarket-us") == "polymarket_us"
    assert exchanges.normalize_exchange_name("Kalshi") == "kalshi"


def test_limitless_uses_api_key_and_private_key(monkeypatch):
    monkeypatch.setenv("LIMITLESS_API_KEY", "limitless-api")
    monkeypatch.setenv("LIMITLESS_PRIVATE_KEY", "limitless-private")

    captured = {}

    class FakeLimitless:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(exchanges.pmxt, "Limitless", FakeLimitless)

    exchanges._create_exchange("limitless")

    assert captured["api_key"] == "limitless-api"
    assert captured["private_key"] == "limitless-private"


def test_polymarket_us_uses_api_key_and_private_key(monkeypatch):
    monkeypatch.setenv("POLYMARKET_US_API_KEY", "pmus-api")
    monkeypatch.setenv("POLYMARKET_US_PRIVATE_KEY", "pmus-private")

    captured = {}

    class FakePolymarketUS:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(exchanges, "_exchange_class", lambda name: FakePolymarketUS)

    exchanges._create_exchange("polymarket_us")

    assert captured["api_key"] == "pmus-api"
    assert captured["private_key"] == "pmus-private"
