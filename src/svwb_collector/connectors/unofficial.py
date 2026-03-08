from __future__ import annotations

from bs4 import BeautifulSoup

from svwb_collector.connectors.base import BaseConnector
from svwb_collector.models import ConnectorResult, Item


class UnofficialSupportConnector(BaseConnector):
    source_key = "unofficial_support"
    source_name = "非公式補助ソース"
    is_official = False

    URLS = [
        "https://sv-jp.com/",
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
            for idx, anchor in enumerate(soup.select("a")[:50]):
                text = " ".join(anchor.get_text(" ", strip=True).split())
                href = anchor.get("href", "")
                if not href:
                    continue
                full_url = href if href.startswith("http") else f"https://sv-jp.com/{href.lstrip('/')}"
                ext = full_url.rstrip("/").split("/")[-1] or f"unofficial-{idx}"
                result.items.append(
                    Item(
                        source_key=self.source_key,
                        source_name=self.source_name,
                        item_type="reference",
                        external_id=ext,
                        title=text or ext,
                        url=full_url,
                        payload={"origin_url": url},
                        is_official=self.is_official,
                    )
                )
        return result
