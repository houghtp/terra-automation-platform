from datetime import date

import pytest

from app.features.business_automations.marketing_intellegence_hub.clients.ga4_client import Ga4Client


def test_parse_ga4_date_accepts_iso():
    assert Ga4Client._parse_ga4_date("2025-11-23") == date(2025, 11, 23)


def test_parse_ga4_date_accepts_compact_format():
    assert Ga4Client._parse_ga4_date("20251123") == date(2025, 11, 23)


def test_parse_ga4_date_rejects_unexpected_format():
    with pytest.raises(ValueError):
        Ga4Client._parse_ga4_date("11/23/2025")
