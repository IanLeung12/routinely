"""Cache paid API responses and require explicit permission for cache misses."""

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path


class LiveApiDisabled(RuntimeError):
    """A cache miss requires a live API call, but LIVE_API is not enabled."""


def live_api_enabled() -> bool:
    return os.environ.get("LIVE_API") == "1"


def request_key(namespace: str, request: dict) -> str:
    payload = namespace + json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cached_call(
    namespace: str,
    request: dict,
    fn: Callable[[], dict],
    cache_dir: Path | None = None,
) -> dict:
    if cache_dir is None:
        cache_dir = Path(
            os.environ.get("API_CACHE_DIR", Path(__file__).resolve().parents[3] / ".cache" / "api")
        )
    directory = cache_dir / namespace
    path = directory / f"{request_key(namespace, request)}.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    if not live_api_enabled():
        raise LiveApiDisabled("Set LIVE_API=1 to allow a paid API call on a cache miss")

    result = fn()
    # Serialize before creating a temporary file so invalid responses leave no debris.
    serialized = json.dumps(result)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result
