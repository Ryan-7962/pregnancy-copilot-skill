from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


COOKIE_FILE_ENV = "PREGNANCY_COPILOT_XHS_COOKIE_FILE"
REQUIRED_COOKIE_NAMES = ("a1", "web_session")
DEFAULT_COOKIE_PATH = Path.home() / ".config" / "pregnancy-copilot" / "secrets" / "xiaohongshu_cookie.txt"


@dataclass(frozen=True)
class CookieValidationStatus:
    valid: bool
    present_names: tuple[str, ...]
    missing_required_names: tuple[str, ...]


def normalize_xhs_cookie_input(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("Cookie input is empty")
    if "\t" in text or text.startswith("# Netscape HTTP Cookie File"):
        pairs = _parse_netscape_cookie(text)
    else:
        pairs = _parse_cookie_header(text)
    if not pairs:
        raise ValueError("Cookie input has no valid name/value pairs")
    return "; ".join(f"{name}={cookie_value}" for name, cookie_value in pairs)


def validate_xhs_cookie_header(cookie_header: str) -> CookieValidationStatus:
    try:
        pairs = _parse_cookie_header(cookie_header.strip())
    except ValueError:
        pairs = []
    present = tuple(sorted({name for name, _ in pairs}))
    missing = tuple(name for name in REQUIRED_COOKIE_NAMES if name not in present)
    return CookieValidationStatus(
        valid=bool(pairs) and not missing,
        present_names=present,
        missing_required_names=missing,
    )


def write_xhs_cookie_secret(
    cookie_input: str,
    destination: str | Path = DEFAULT_COOKIE_PATH,
    *,
    replace: bool = False,
    pregnancy_data_root: str | Path | None = None,
) -> Path:
    normalized = normalize_xhs_cookie_input(cookie_input)
    path = Path(destination).expanduser().resolve()
    if pregnancy_data_root is not None:
        data_root = Path(pregnancy_data_root).expanduser().resolve()
        if path == data_root or path.is_relative_to(data_root):
            raise ValueError("Xiaohongshu credentials must be stored outside pregnancy-data")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists() and not replace:
        raise FileExistsError(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(normalized + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.chmod(path, 0o600)
    return path


def load_xhs_cookie_header(path: str | Path | None = None) -> str:
    configured = path or os.environ.get(COOKIE_FILE_ENV) or DEFAULT_COOKIE_PATH
    cookie_path = Path(configured).expanduser()
    if not cookie_path.exists():
        raise FileNotFoundError(
            f"Xiaohongshu Cookie file not found; configure {COOKIE_FILE_ENV} in the Agent environment"
        )
    normalized = normalize_xhs_cookie_input(cookie_path.read_text(encoding="utf-8"))
    status = validate_xhs_cookie_header(normalized)
    if not status.valid:
        names = ", ".join(status.missing_required_names)
        raise ValueError(f"Xiaohongshu Cookie file is missing required names: {names}")
    return normalized


def _parse_cookie_header(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for part in text.split(";"):
        item = part.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError("Malformed Cookie header")
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value or any(char.isspace() for char in name):
            raise ValueError("Malformed Cookie header")
        pairs.append((name, value))
    return pairs


def _parse_netscape_cookie(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 7:
            raise ValueError("Malformed Netscape Cookie file")
        domain, _, _, _, _, name, value = fields
        if not domain.lstrip(".").endswith("xiaohongshu.com") or not name or not value:
            continue
        pairs.append((name.strip(), value.strip()))
    return pairs
