from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


def export_json(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["source_key"]].append(
            {
                "source_name": row["source_name"],
                "is_official": bool(row["is_official"]),
                "item_type": row["item_type"],
                "external_id": row["external_id"],
                "title": row["title"],
                "url": row["url"],
                "published_at": row["published_at"],
                "payload": json.loads(row["payload_json"]),
                "first_seen_run_id": row["first_seen_run_id"],
                "last_seen_run_id": row["last_seen_run_id"],
            }
        )

    payload = {
        "sources": dict(grouped),
        "total_items": len(rows),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
