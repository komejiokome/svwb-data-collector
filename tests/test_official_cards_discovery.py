from __future__ import annotations

import unittest
from pathlib import Path

from svwb_collector.connectors.official_cards import OfficialCardsConnector


class FakeHTTPClient:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def get_text(self, url: str) -> str:
        return self.mapping[url]


class OfficialCardsDiscoveryTest(unittest.TestCase):
    def test_index_discovery_from_embedded_json(self) -> None:
        index_url = "https://shadowverse-wb.com/ja/deck/cardslist/"
        html = Path("tests/fixtures/official_cards_index_discovery.html").read_text(encoding="utf-8")
        connector = OfficialCardsConnector(FakeHTTPClient({index_url: html}))

        cards = connector._extract_from_html_and_scripts(html, index_url)

        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["card_id"], "3001")
        self.assertEqual(cards[0]["detail_url"], "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=3001")

    def test_build_fallback_detail_url(self) -> None:
        connector = OfficialCardsConnector(FakeHTTPClient({}))
        self.assertEqual(
            connector._build_fallback_detail_url("12345"),
            "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=12345",
        )


if __name__ == "__main__":
    unittest.main()
