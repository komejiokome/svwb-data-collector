from __future__ import annotations

import argparse
import importlib
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger("svwb_collector")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SVWB data collector")
    parser.add_argument("--db", default="data/svwb.sqlite")
    parser.add_argument("--cache-dir", default="data/cache")
    parser.add_argument("--json-out", default="exports/latest.json")
    parser.add_argument("--summary-out", default="latest_summary.md")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--min-interval", type=float, default=1.5)
    parser.add_argument("--cache-ttl", type=int, default=60 * 60 * 6)
    parser.add_argument(
        "--sources",
        default="official_cards,svoc,rage,unofficial_support",
        help="Comma-separated source keys (official_cards,svoc,rage,unofficial_support)",
    )
    return parser


def _load_connector(source_key: str, client):
    mapping = {
        "official_cards": ("svwb_collector.connectors.official_cards", "OfficialCardsConnector"),
        "svoc": ("svwb_collector.connectors.svoc", "SvocConnector"),
        "rage": ("svwb_collector.connectors.rage", "RageConnector"),
        "unofficial_support": ("svwb_collector.connectors.unofficial", "UnofficialSupportConnector"),
    }
    if source_key not in mapping:
        raise KeyError(source_key)
    module_name, class_name = mapping[source_key]
    module = importlib.import_module(module_name)
    connector_cls = getattr(module, class_name)
    return connector_cls(client)


def run(args: argparse.Namespace) -> int:
    from svwb_collector.http_client import CachedHTTPClient, HTTPConfig
    from svwb_collector.reporting.exporter import export_json
    from svwb_collector.reporting.summary import write_summary
    from svwb_collector.storage.sqlite_store import SQLiteStore

    selected = [s.strip() for s in str(args.sources).split(",") if s.strip()]

    store = SQLiteStore(Path(args.db))
    run_id = store.create_run()

    client = CachedHTTPClient(
        cache_dir=Path(args.cache_dir),
        config=HTTPConfig(timeout_sec=args.timeout, min_interval_sec=args.min_interval, cache_ttl_sec=args.cache_ttl),
    )

    connectors = []
    try:
        for key in selected:
            connectors.append(_load_connector(key, client))
    except KeyError:
        LOGGER.error("Unknown source keys in --sources: %s", ",".join(selected))
        return 2
    except ModuleNotFoundError as exc:
        LOGGER.error("Missing dependency for selected source(s): %s", exc.name)
        return 2

    warnings: list[str] = []
    blocked_sources: list[str] = []
    source_metrics: dict[str, dict] = {}
    total_items = 0
    for connector in connectors:
        LOGGER.info("Fetching %s", connector.source_name)
        result = connector.fetch()
        warnings.extend(f"{connector.source_key}: {w}" for w in result.warnings)
        if result.blocked_reason:
            blocked_sources.append(f"{connector.source_key}: {result.blocked_reason}")
            warnings.append(f"{connector.source_key}: BLOCKED {result.blocked_reason}")
        counts = store.save_items(run_id, result.items)
        total_items += len(result.items)
        source_metrics[connector.source_key] = {
            **result.metrics,
            "saved_item_count": len(result.items),
            "blocked": bool(result.blocked_reason),
        }
        LOGGER.info(
            "Saved %s items from %s (new=%s updated=%s unchanged=%s)",
            len(result.items),
            connector.source_key,
            counts["new"],
            counts["updated"],
            counts["unchanged"],
        )

    status = "success"
    if blocked_sources or total_items == 0:
        status = "partial"
    store.finish_run(run_id, warning_count=len(warnings), status=status)

    export_json(store.fetch_latest_export(), Path(args.json_out))
    diff_rows = store.fetch_run_diff(run_id)
    write_summary(run_id, diff_rows, warnings, Path(args.summary_out), source_metrics=source_metrics)

    LOGGER.info("run=%s status=%s total_items=%s warnings=%s", run_id, status, total_items, len(warnings))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
