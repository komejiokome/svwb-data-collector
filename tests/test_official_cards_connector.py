from __future__ import annotations

import unittest
from pathlib import Path

from svwb_collector.connectors.official_cards import OfficialCardsConnector


class FakeHTTPClient:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def get_text(self, url: str) -> str:
        return self.mapping[url]


class OfficialCardsConnectorTest(unittest.TestCase):
    def test_fetch_uses_discovery_and_detail_pages(self) -> None:
        index_url = "https://shadowverse-wb.com/ja/deck/cardslist/"
        index_html = Path("tests/fixtures/official_cards_index_discovery.html").read_text(encoding="utf-8")
        detail_html = Path("tests/fixtures/official_card_detail_3001.html").read_text(encoding="utf-8")

        mapping = {
            index_url: index_html,
            "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=3001": detail_html,
            "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=3002": detail_html.replace("Knight", "Mage"),
        }
        connector = OfficialCardsConnector(FakeHTTPClient(mapping))
        connector.INDEX_URLS = [index_url]

        result = connector.fetch()

        self.assertEqual(result.source_key, "official_cards")
        self.assertEqual(result.metrics["discovered_card_count"], 2)
        self.assertEqual(result.metrics["fetched_detail_count"], 2)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(
            result.items[0].payload["source_url"],
            "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=3001",
        )
        self.assertIn(
            "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=3001",
            result.metrics["detail_url_examples"],
        )


if __name__ == "__main__":
    unittest.main()
