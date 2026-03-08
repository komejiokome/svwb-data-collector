from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from urllib import robotparser
from urllib.parse import urlparse
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)

try:
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    requests = None


@dataclass(slots=True)
class HTTPConfig:
    user_agent: str = "svwb-data-collector/1.0 (+https://github.com/example/svwb-data-collector)"
    timeout_sec: int = 20
    max_retries: int = 3
    backoff_sec: float = 1.5
    cache_ttl_sec: int = 60 * 60 * 6
    min_interval_sec: float = 1.0


class CachedHTTPClient:
    def __init__(self, cache_dir: Path, config: HTTPConfig | None = None) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.config = config or HTTPConfig()
        self._session = requests.Session() if requests is not None else None
        if self._session is not None:
            self._session.headers.update({"User-Agent": self.config.user_agent})
        self._last_request_at: dict[str, float] = {}
        self._robots: dict[str, robotparser.RobotFileParser] = {}
        self._robots_loaded: dict[str, bool] = {}

    def get_text(self, url: str) -> str:
        cached = self._read_cache(url)
        if cached is not None:
            return cached

        self._respect_robots(url)
        self._rate_limit(url)

        last_error: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                text = self._fetch(url)
                self._write_cache(url, text)
                self._last_request_at[urlparse(url).netloc] = time.time()
                return text
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                sleep_sec = self.config.backoff_sec * attempt
                LOGGER.warning("Request failed %s (attempt %s/%s): %s", url, attempt, self.config.max_retries, exc)
                time.sleep(sleep_sec)

        raise RuntimeError(f"failed to fetch {url}: {last_error}")

    def _fetch(self, url: str) -> str:
        if self._session is not None:
            response = self._session.get(url, timeout=self.config.timeout_sec)
            response.raise_for_status()
            return response.text

        req = Request(url, headers={"User-Agent": self.config.user_agent})
        with urlopen(req, timeout=self.config.timeout_sec) as res:  # noqa: S310
            return res.read().decode("utf-8", errors="replace")

    def _rate_limit(self, url: str) -> None:
        host = urlparse(url).netloc
        last_ts = self._last_request_at.get(host)
        if not last_ts:
            return
        elapsed = time.time() - last_ts
        if elapsed < self.config.min_interval_sec:
            time.sleep(self.config.min_interval_sec - elapsed)

    def _respect_robots(self, url: str) -> None:
        parsed = urlparse(url)
        host = parsed.netloc
        if host not in self._robots:
            robots_url = f"{parsed.scheme}://{host}/robots.txt"
            rp = robotparser.RobotFileParser()
            loaded = True
            try:
                rp.set_url(robots_url)
                rp.read()
            except Exception as exc:  # noqa: BLE001
                loaded = False
                LOGGER.warning("Could not read robots.txt %s: %s", robots_url, exc)
            self._robots[host] = rp
            self._robots_loaded[host] = loaded

        if not self._robots_loaded.get(host, False):
            LOGGER.warning("robots.txt unavailable for %s; allowing request with caution", host)
            return

        rp = self._robots[host]
        if rp and not rp.can_fetch(self.config.user_agent, url):
            raise RuntimeError(f"Disallowed by robots.txt: {url}")

    def _cache_path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, url: str) -> str | None:
        path = self._cache_path(url)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        created_at = payload.get("created_at", 0)
        if time.time() - created_at > self.config.cache_ttl_sec:
            return None
        return str(payload.get("text", ""))

    def _write_cache(self, url: str, text: str) -> None:
        path = self._cache_path(url)
        payload = {"created_at": time.time(), "url": url, "text": text}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
