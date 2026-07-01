"""Check the public GitHub repo for the latest released version (git tag).

Tags follow semver with NO ``v`` prefix (e.g. ``2.34.12``). The result is
cached in Redis so we never hit GitHub on every page load and stay well within
the unauthenticated rate limit.
"""
import logging
import re

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Public repo that holds the release tags.
DEFAULT_REPO = "tuergeist/contract-manager"

CACHE_KEY = "latest_version:github_tag"
CACHE_TTL = 60 * 60  # 1 hour
TIMEOUT = 10

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_version(value: str) -> tuple[int, int, int] | None:
    """Parse a ``x.y.z`` semver string into a comparable tuple.

    Returns ``None`` for anything that is not a plain three-part numeric
    version (e.g. ``dev``, ``2.1``, ``2.1.0-rc1``).
    """
    if not value:
        return None
    match = _SEMVER_RE.match(value.strip().lstrip("v"))
    if not match:
        return None
    return tuple(int(g) for g in match.groups())  # type: ignore[return-value]


def _fetch_latest_tag_from_github() -> str | None:
    """Fetch the highest semver tag from the GitHub tags API."""
    repo = getattr(settings, "GITHUB_RELEASE_REPO", DEFAULT_REPO)
    url = f"https://api.github.com/repos/{repo}/tags?per_page=100"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # An optional token raises the rate limit and allows private repos.
    token = getattr(settings, "GITHUB_RELEASE_TOKEN", "") or getattr(
        settings, "GITHUB_FEEDBACK_TOKEN", ""
    )
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.get(url, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        logger.warning("Version check: GitHub request failed: %s", exc)
        return None

    if not response.is_success:
        logger.warning(
            "Version check: GitHub returned HTTP %s", response.status_code
        )
        return None

    best: tuple[int, int, int] | None = None
    best_name: str | None = None
    for tag in response.json():
        name = tag.get("name", "")
        parsed = parse_version(name)
        if parsed and (best is None or parsed > best):
            best = parsed
            best_name = name
    return best_name


def get_latest_version() -> str | None:
    """Return the newest released version tag, cached in Redis.

    Returns ``None`` when the lookup fails (offline, rate limited, etc.) so the
    frontend simply shows no banner rather than an error.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        # Empty string is a cached "lookup failed" marker – treat as no result.
        return cached or None

    latest = _fetch_latest_tag_from_github()
    # Cache even a failed lookup (as "") to avoid hammering GitHub on errors.
    cache.set(CACHE_KEY, latest or "", CACHE_TTL)
    return latest
