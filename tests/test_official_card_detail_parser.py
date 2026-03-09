from __future__ import annotations

import unittest
from pathlib import Path

from svwb_collector.connectors.official_cards import OfficialCardsConnector


class FakeHTTPClient:
    def get_text(self, url: str) -> str:  # pragma: no cover
        raise NotImplementedError


class OfficialCardDetailParserTest(unittest.TestCase):
    def test_parse_detail_page_fields(self) -> None:
        html = Path("tests/fixtures/official_card_detail_3001.html").read_text(encoding="utf-8")
        connector = OfficialCardsConnector(FakeHTTPClient())

        parsed = connector._parse_detail_page(html)

        self.assertEqual(parsed["name"], "Knight")
        self.assertEqual(parsed["cost"], "3")
        self.assertEqual(parsed["class"], "ロイヤル")
        self.assertEqual(parsed["rarity"], "Bronze")
        self.assertEqual(parsed["kind"], "フォロワー")
        self.assertEqual(parsed["type"], "兵士")
        self.assertEqual(parsed["stats"]["attack"], "2")
        self.assertEqual(parsed["stats"]["defense"], "3")
        self.assertEqual(parsed["effect"], "突進")
        self.assertEqual(parsed["pack"], "Basic")

    def test_parser_used_with_card_query_url_shape(self) -> None:
        connector = OfficialCardsConnector(FakeHTTPClient())
        normalized = connector._normalize_detail_url(
            "https://shadowverse-wb.com/ja/deck/cardslist/3001/",
            "3001",
        )
        self.assertEqual(normalized, "https://shadowverse-wb.com/ja/deck/cardslist/card/?card_id=3001")


if __name__ == "__main__":
    unittest.main()
