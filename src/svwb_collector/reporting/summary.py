from __future__ import annotations

from collections import Counter
from pathlib import Path


def write_summary(
    run_id: int,
    diff_rows: list[dict],
    warnings: list[str],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    diff_counter = Counter(row["change_type"] for row in diff_rows)
    source_counter = Counter(row["source_key"] for row in diff_rows)

    lines = [
        "# latest_summary",
        "",
        f"- run_id: {run_id}",
        f"- new: {diff_counter.get('new', 0)}",
        f"- updated: {diff_counter.get('updated', 0)}",
        f"- warnings: {len(warnings)}",
        "",
        "## Source impact",
    ]
    for source_key, count in sorted(source_counter.items()):
        lines.append(f"- {source_key}: {count} changes")

    lines.extend(["", "## Warnings"])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")

    lines.extend(["", "## Changed items"])
    if diff_rows:
        for row in diff_rows[:50]:
            lines.append(
                f"- [{row['change_type']}] {row['source_key']}/{row['item_type']} {row['title']} ({row['url']})"
            )
    else:
        lines.append("- no changes")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
