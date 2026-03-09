from __future__ import annotations

from bs4 import BeautifulSoup

from svwb_collector.connectors.base import BaseConnector
from svwb_collector.models import ConnectorResult, Item


class RageConnector(BaseConnector):
    source_key = "rage"
    source_name = "RAGE Shadowverse Pro League"
    is_official = True

    URLS = [
        "https://rage-esports.jp/shadowverse/",
        "https://rage-esports.jp/news/",
    ]

    def fetch(self) -> ConnectorResult:
        result = ConnectorResult(self.source_key, self.source_name, self.is_official)
        for url in self.URLS:
            try:
                html = self.client.get_text(url)
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"{url}: {exc}")
                continue
            soup = BeautifulSoup(html, "html.parser")
            for idx, anchor in enumerate(soup.select("a")):
                text = " ".join(anchor.get_text(" ", strip=True).split())
                href = anchor.get("href", "")
                haystack = (text + href).lower()
                if "shadowverse" not in haystack and "デッキ" not in text:
                    continue
                full_url = href if href.startswith("http") else self._join(url, href)
                item_type = "deck" if ("deck" in haystack or "デッキ" in text) else "news"
                ext = full_url.rstrip("/").split("/")[-1] or f"rage-{idx}"
                result.items.append(
                    Item(
                        source_key=self.source_key,
                        source_name=self.source_name,
                        item_type=item_type,
                        external_id=ext,
                        title=text or ext,
                        url=full_url,
                        payload={"origin_url": url},
                        is_official=self.is_official,
                    )
                )
        return result

    @staticmethod
    def _join(base: str, path: str) -> str:
        if path.startswith("/"):
            root = "/".join(base.split("/")[:3])
            return f"{root}{path}"
        return f"{base.rstrip('/')}/{path.lstrip('/')}"
