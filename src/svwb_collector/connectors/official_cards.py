from __future__ import annotations

from html.parser import HTMLParser

from svwb_collector.connectors.base import BaseConnector
from svwb_collector.models import ConnectorResult, Item

try:
    from bs4 import BeautifulSoup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    BeautifulSoup = None


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._in_a = False
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = {k: (v or "") for k, v in attrs}
        self._href = attr_map.get("href", "")
        self._in_a = True
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_a:
            self.links.append((self._href.strip(), " ".join("".join(self._text).split())))
            self._in_a = False
            self._href = ""
            self._text = []


class OfficialCardsConnector(BaseConnector):
    source_key = "official_cards"
    source_name = "公式カード一覧 / Deck Portal"
    is_official = True

    URLS = [
        "https://shadowverse-wb.com/ja/cards",
        "https://shadowverse-portal.com/deckbuilder/create/1?lang=ja",
    ]

    def fetch(self) -> ConnectorResult:
        result = ConnectorResult(self.source_key, self.source_name, self.is_official)
        fetch_failures = 0
        for url in self.URLS:
            try:
                html = self.client.get_text(url)
            except Exception as exc:  # noqa: BLE001
                fetch_failures += 1
                result.warnings.append(f"{url}: {exc}")
                continue

            links = self._extract_links(html)
            cards = [(href, text) for href, text in links if "card" in href.lower()]
            for idx, (href, text) in enumerate(cards):
                if not href:
                    continue
                title = text or f"card-{idx}"
                full_url = href if href.startswith("http") else self._join(url, href)
                external_id = full_url.rstrip("/").split("/")[-1] or f"card-{idx}"
                result.items.append(
                    Item(
                        source_key=self.source_key,
                        source_name=self.source_name,
                        item_type="card",
                        external_id=external_id,
                        title=title,
                        url=full_url,
                        payload={"origin_url": url},
                        is_official=self.is_official,
                    )
                )

        if not result.items and fetch_failures == len(self.URLS):
            result.blocked_reason = "All official card URLs were unreachable or blocked"
        return result

    def _extract_links(self, html: str) -> list[tuple[str, str]]:
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            return [
                (a.get("href", "").strip(), " ".join(a.get_text(" ", strip=True).split()))
                for a in soup.select("a")
            ]

        parser = _AnchorParser()
        parser.feed(html)
        return parser.links

    @staticmethod
    def _join(base: str, path: str) -> str:
        if path.startswith("/"):
            root = "/".join(base.split("/")[:3])
            return f"{root}{path}"
        return f"{base.rstrip('/')}/{path.lstrip('/')}"
