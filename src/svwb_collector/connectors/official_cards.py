from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from svwb_collector.connectors.base import BaseConnector
from svwb_collector.models import ConnectorResult, Item

try:
    from bs4 import BeautifulSoup  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    BeautifulSoup = None


class OfficialCardsConnector(BaseConnector):
    source_key = "official_cards"
    source_name = "公式カード一覧 / Deck Portal"
    is_official = True

    INDEX_URLS = [
        "https://shadowverse-wb.com/ja/deck/cardslist/",
        "https://shadowverse-portal.com/deckbuilder/create/1?lang=ja",
    ]
    BLOCKED_REFERENCE_URLS = ["https://shadowverse-wb.com/ja/cards"]
    WB_DETAIL_BASE = "https://shadowverse-wb.com/ja/deck/cardslist/card/"

    def fetch(self) -> ConnectorResult:
        result = ConnectorResult(self.source_key, self.source_name, self.is_official)
        discovered = self._discover_cards(result)
        result.metrics["source_urls"] = list(self.INDEX_URLS)
        result.metrics["discovered_card_count"] = len(discovered)

        if not discovered:
            if any("failed to fetch" in w for w in result.warnings):
                result.blocked_reason = "Index discovery failed for all URLs"
            else:
                result.warnings.append(
                    "discovery: no card ids/urls found in HTML or embedded scripts (API/XHR may be required)"
                )
            result.metrics["fetched_detail_count"] = 0
            result.metrics["saved_item_count"] = 0
            result.metrics["detail_url_examples"] = []
            return result

        detail_success = 0
        detail_examples: list[str] = []
        now = datetime.now(timezone.utc).isoformat()
        for card in discovered:
            detail_url = self._normalize_detail_url(card["detail_url"], card["card_id"])
            if len(detail_examples) < 5 and detail_url not in detail_examples:
                detail_examples.append(detail_url)
            try:
                detail_html = self.client.get_text(detail_url)
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"detail {detail_url}: failed to fetch: {exc}")
                continue

            parsed = self._parse_detail_page(detail_html)
            detail_success += 1

            card_id = card["card_id"]
            title = parsed.get("name") or card.get("name") or f"card-{card_id}"
            payload = {
                "source_url": detail_url,
                "fetched_at": now,
                "cost": parsed.get("cost"),
                "class": parsed.get("class"),
                "rarity": parsed.get("rarity"),
                "kind": parsed.get("kind"),
                "type": parsed.get("type"),
                "stats": parsed.get("stats"),
                "effect": parsed.get("effect"),
                "pack": parsed.get("pack"),
                "is_token": bool(parsed.get("is_token", False)),
                "index_origin": card.get("origin_url"),
            }
            result.items.append(
                Item(
                    source_key=self.source_key,
                    source_name=self.source_name,
                    item_type="card",
                    external_id=card_id,
                    title=title,
                    url=detail_url,
                    payload=payload,
                    is_official=self.is_official,
                )
            )

        result.metrics["fetched_detail_count"] = detail_success
        result.metrics["saved_item_count"] = len(result.items)
        result.metrics["detail_url_examples"] = detail_examples
        if not result.items:
            result.blocked_reason = "Discovery succeeded but all detail pages failed"
        return result

    def _discover_cards(self, result: ConnectorResult) -> list[dict[str, str]]:
        discovered: dict[str, dict[str, str]] = {}

        for index_url in self.INDEX_URLS:
            try:
                html = self.client.get_text(index_url)
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"index {index_url}: failed to fetch: {exc}")
                continue

            for card in self._extract_from_html_and_scripts(html, index_url):
                if card["card_id"] not in discovered:
                    discovered[card["card_id"]] = card

        return list(discovered.values())

    def _extract_from_html_and_scripts(self, html: str, base_url: str) -> list[dict[str, str]]:
        if BeautifulSoup is None:
            return []

        soup = BeautifulSoup(html, "html.parser")
        found: dict[str, dict[str, str]] = {}

        for a in soup.select("a[href]"):
            href = a.get("href", "").strip()
            if "card" not in href.lower():
                continue
            full = urljoin(base_url, href)
            cid = self._extract_card_id(full)
            if not cid:
                continue
            found[cid] = {
                "card_id": cid,
                "detail_url": self._normalize_detail_url(full, cid),
                "name": " ".join(a.get_text(" ", strip=True).split()),
                "origin_url": base_url,
            }

        scripts = [s.get_text("", strip=False) for s in soup.select("script")]
        for script in scripts:
            for candidate in self._extract_json_candidates(script):
                for obj in self._walk_card_like_objects(candidate):
                    cid = str(obj.get("card_id") or obj.get("cardId") or obj.get("id") or "").strip()
                    if not cid:
                        continue
                    detail_url = str(
                        obj.get("detail_url")
                        or obj.get("detailUrl")
                        or obj.get("url")
                        or obj.get("link")
                        or ""
                    ).strip()
                    if not detail_url:
                        detail_url = self._build_fallback_detail_url(cid)
                    full = urljoin(base_url, detail_url)
                    found[cid] = {
                        "card_id": cid,
                        "detail_url": self._normalize_detail_url(full, cid),
                        "name": str(obj.get("card_name") or obj.get("cardName") or obj.get("name") or "").strip(),
                        "origin_url": base_url,
                    }

        return list(found.values())

    def _extract_json_candidates(self, text: str) -> list[Any]:
        payloads: list[Any] = []
        text = text.strip()
        if not text:
            return payloads

        raw_candidates = [text]
        raw_candidates.extend(re.findall(r"=\s*(\{.*\}|\[.*\])\s*;", text, flags=re.DOTALL))
        for raw in raw_candidates:
            try:
                payloads.append(json.loads(raw))
            except Exception:  # noqa: BLE001
                continue
        return payloads

    def _walk_card_like_objects(self, data: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                keys = set(node.keys())
                if {"card_id", "card_name"} & keys or {"cardId", "cardName"} & keys or {"id", "name"} <= keys:
                    out.append(node)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(data)
        return out

    def _parse_detail_page(self, html: str) -> dict[str, Any]:
        if BeautifulSoup is None:
            return {}
        soup = BeautifulSoup(html, "html.parser")

        data: dict[str, Any] = {}
        ld = self._parse_ld_json(soup)
        if ld:
            data.update(ld)

        text = soup.get_text("\n", strip=True)
        data.setdefault("name", self._first_text(soup, ["h1", ".card-name", "[data-card-name]"]))
        data.setdefault("cost", self._extract_by_label(text, ["コスト", "Cost"]))
        data.setdefault("class", self._extract_by_label(text, ["クラス", "Class"]))
        data.setdefault("rarity", self._extract_by_label(text, ["レアリティ", "Rarity"]))
        data.setdefault("kind", self._extract_by_label(text, ["種類", "Kind"]))
        data.setdefault("type", self._extract_by_label(text, ["タイプ", "Type"]))
        data.setdefault("effect", self._extract_by_label(text, ["能力", "効果", "Effect"]))
        data.setdefault("pack", self._extract_by_label(text, ["収録", "パック", "Pack"]))

        atk = self._extract_by_label(text, ["攻撃", "ATK"]) or ""
        life = self._extract_by_label(text, ["体力", "HP"]) or ""
        if atk or life:
            data.setdefault("stats", {"attack": atk, "defense": life})

        token_hint = (data.get("kind") or "") + " " + (data.get("effect") or "")
        data.setdefault("is_token", "トークン" in token_hint or "token" in token_hint.lower())
        return data

    def _parse_ld_json(self, soup) -> dict[str, Any]:
        for script in soup.select("script[type='application/ld+json']"):
            raw = script.get_text("", strip=True)
            try:
                obj = json.loads(raw)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(obj, dict):
                return {
                    "name": obj.get("name"),
                    "effect": obj.get("description"),
                }
        return {}

    def _first_text(self, soup, selectors: list[str]) -> str | None:
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                text = " ".join(node.get_text(" ", strip=True).split())
                if text:
                    return text
        return None

    def _extract_by_label(self, text: str, labels: list[str]) -> str | None:
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:：]?\s*([^\n]+)"
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_card_id(self, url: str) -> str | None:
        parsed = urlparse(url)
        qs_id = parse_qs(parsed.query).get("card_id", [None])[0]
        if qs_id:
            return str(qs_id)
        m = re.search(r"(\d+)(?:/)?$", parsed.path)
        return m.group(1) if m else None

    def _build_fallback_detail_url(self, card_id: str) -> str:
        return f"{self.WB_DETAIL_BASE}?{urlencode({'card_id': card_id})}"

    def _normalize_detail_url(self, candidate_url: str, card_id: str) -> str:
        # WB official details are normalized to /card/?card_id=...
        parsed = urlparse(candidate_url)
        host = (parsed.netloc or "").lower()
        if "shadowverse-wb.com" in host:
            return self._build_fallback_detail_url(card_id)
        return candidate_url
