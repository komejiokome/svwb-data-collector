from __future__ import annotations

import unittest
from pathlib import Path

from svwb_collector.connectors.official_cards import OfficialCardsConnector


class FakeHTTPClient:
    def __init__(self, html: str) -> None:
        self.html = html

    def get_text(self, url: str) -> str:
        return self.html


class OfficialCardsConnectorTest(unittest.TestCase):
    def test_parse_cards_from_fixture_html(self) -> None:
        fixture = Path("tests/fixtures/official_cards_sample.html").read_text(encoding="utf-8")
        connector = OfficialCardsConnector(FakeHTTPClient(fixture))
        connector.URLS = ["https://shadowverse-wb.com/ja/cards"]

        result = connector.fetch()

        self.assertEqual(result.source_key, "official_cards")
        self.assertEqual(len(result.items), 2)

        first = result.items[0]
        self.assertEqual(first.title, "Flame Dragon")
        self.assertEqual(first.url, "https://shadowverse-wb.com/cards/1001")
        self.assertEqual(first.item_type, "card")

        second = result.items[1]
        self.assertEqual(second.title, "Ocean Mage")
        self.assertEqual(second.external_id, "1002")


if __name__ == "__main__":
    unittest.main()
