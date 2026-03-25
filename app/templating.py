"""Jinja2 template configuration."""

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

# Matches private/internal network IP addresses
_PRIVATE_IP_RE = re.compile(
    r"^https?://(?:192\.168\.|10\.|172\.(?:1[6-9]|2\d|3[01])\.)"
)

from fastapi.templating import Jinja2Templates

from app.config import settings

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))


def _fromjson(value: str | None) -> dict:
    """Parse a JSON string into a dict; returns {} on failure or None input."""
    if not value:
        return {}
    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


def _format_taipei(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Convert a UTC datetime to Asia/Taipei and format it."""
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TAIPEI_TZ).strftime(fmt)


def _safe_img_url(url: str | None) -> str | None:
    """Rewrite any direct internal-IP image URL through the server-side proxy.

    Prevents the browser from attempting to reach 192.168.x.x / 10.x / 172.16-31.x
    directly, which would trigger Chrome's 'Private Network Access' permission dialog.
    """
    if not url:
        return url
    if not _PRIVATE_IP_RE.match(url):
        return url  # Already a relative path or public URL — leave as-is
    path = urlparse(url).path
    # Strip leading /api/images/ prefix if present (the proxy endpoint adds it back)
    if path.startswith("/api/images/"):
        path = path[len("/api/images/"):]
    path = path.lstrip("/")
    return f"/api/images/proxy/{path}"


templates.env.filters["fromjson"] = _fromjson
templates.env.filters["format_taipei"] = _format_taipei
templates.env.filters["safe_img_url"] = _safe_img_url
