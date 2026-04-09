"""Tests for exchange initialization helpers."""

from hermes_pmxt import exchanges


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
