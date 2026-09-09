from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence


SUPPORTED_ENGINES = ("chromium", "chrome", "msedge")
UNSUPPORTED_ENGINES = {
    "firefox": "browser-use 0.1.x steuert Playwright-Chromium; Firefox wird nicht unterstützt.",
    "webkit": "browser-use 0.1.x steuert Playwright-Chromium; WebKit wird nicht unterstützt.",
}

ENGINE_LABELS = {
    "chromium": "Playwright Chromium (Standard)",
    "chrome": "Google Chrome (System-Binary)",
    "msedge": "Microsoft Edge (System-Binary)",
}

_CHROME_CANDIDATES = (
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/opt/google/chrome/chrome",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)

_MSEDGE_CANDIDATES = (
    "/usr/bin/microsoft-edge-stable",
    "/usr/bin/microsoft-edge",
    "/opt/microsoft/msedge/msedge",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)

_DOCKER_CHROMIUM_ARGS = (
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
)


@dataclass(frozen=True)
class EngineInfo:
    id: str
    label: str
    supported: bool
    notes: str
    binary_path: Optional[str] = None


def normalize_engine(engine: Optional[str]) -> str:
    value = (engine or "chromium").strip().lower()
    aliases = {
        "chrome": "chrome",
        "google-chrome": "chrome",
        "google_chrome": "chrome",
        "chromium": "chromium",
        "msedge": "msedge",
        "edge": "msedge",
        "microsoft-edge": "msedge",
        "firefox": "firefox",
        "webkit": "webkit",
        "safari": "webkit",
    }
    return aliases.get(value, value)


def _first_existing(paths: Sequence[str]) -> Optional[str]:
    for path in paths:
        if path and Path(path).is_file():
            return path
    return None


def resolve_engine_binary(
    engine: str, chrome_instance_path: Optional[str] = None
) -> Optional[str]:
    if chrome_instance_path:
        return chrome_instance_path
    normalized = normalize_engine(engine)
    if normalized == "chrome":
        return _first_existing(_CHROME_CANDIDATES)
    if normalized == "msedge":
        return _first_existing(_MSEDGE_CANDIDATES)
    return None


def is_headless_default(env: Optional[Mapping[str, str]] = None) -> bool:
    source = env if env is not None else os.environ
    explicit = source.get("BROWSER_HEADLESS")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}
    return not bool(source.get("DISPLAY"))


def describe_engines(chrome_instance_path: Optional[str] = None) -> list[EngineInfo]:
    infos: list[EngineInfo] = []
    for engine_id in SUPPORTED_ENGINES:
        binary = resolve_engine_binary(
            engine_id, chrome_instance_path if engine_id != "chromium" else None
        )
        notes = "Gebündeltes Playwright-Chromium, kein System-Browser nötig."
        if engine_id in {"chrome", "msedge"}:
            notes = (
                f"System-Binary gefunden: {binary}"
                if binary
                else "Kein System-Binary gefunden — Fallback auf Playwright Chromium."
            )
        infos.append(
            EngineInfo(
                id=engine_id,
                label=ENGINE_LABELS[engine_id],
                supported=True,
                notes=notes,
                binary_path=binary,
            )
        )
    for engine_id, reason in UNSUPPORTED_ENGINES.items():
        infos.append(
            EngineInfo(
                id=engine_id,
                label=engine_id,
                supported=False,
                notes=reason,
            )
        )
    return infos


def _truthy(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return None


def build_browser_config_kwargs(
    settings: Any = None,
    env: Optional[Mapping[str, str]] = None,
) -> dict[str, Any]:
    source = env if env is not None else os.environ
    engine = normalize_engine(
        source.get("BROWSER_ENGINE") or getattr(settings, "engine", None) or "chromium"
    )
    if engine in UNSUPPORTED_ENGINES:
        raise ValueError(
            f"Browser-Engine '{engine}' wird nicht unterstützt. {UNSUPPORTED_ENGINES[engine]}"
        )

    headless_env = _truthy(source.get("BROWSER_HEADLESS"))
    if headless_env is not None:
        headless = headless_env
    elif settings is not None and getattr(settings, "headless", None) is not None:
        headless = bool(settings.headless)
        if settings.headless is False and not source.get("DISPLAY"):
            headless = True
    else:
        headless = is_headless_default(source)

    kwargs: dict[str, Any] = {
        "headless": headless,
        "disable_security": True,
    }

    if settings is not None:
        kwargs["disable_security"] = bool(getattr(settings, "disable_security", True))
        extra_args = list(getattr(settings, "extra_chromium_args", None) or [])
        chrome_instance_path = getattr(settings, "chrome_instance_path", None) or None
        wss_url = getattr(settings, "wss_url", None) or None
        cdp_url = getattr(settings, "cdp_url", None) or None
        proxy = getattr(settings, "proxy", None)
        if proxy and getattr(proxy, "server", None):
            kwargs["proxy"] = proxy
    else:
        extra_args = []
        chrome_instance_path = None
        wss_url = None
        cdp_url = None

    chrome_instance_path = source.get("CHROME_INSTANCE_PATH") or chrome_instance_path
    wss_url = source.get("BROWSER_WSS_URL") or wss_url
    cdp_url = source.get("BROWSER_CDP_URL") or cdp_url

    resolved_binary = resolve_engine_binary(engine, chrome_instance_path)
    if engine in {"chrome", "msedge"} and resolved_binary:
        kwargs["chrome_instance_path"] = resolved_binary
    elif chrome_instance_path:
        kwargs["chrome_instance_path"] = chrome_instance_path

    if wss_url:
        kwargs["wss_url"] = wss_url
    if cdp_url:
        kwargs["cdp_url"] = cdp_url

    merged_args = list(extra_args)
    if headless or not source.get("DISPLAY"):
        for arg in _DOCKER_CHROMIUM_ARGS:
            if arg not in merged_args:
                merged_args.append(arg)
    if merged_args:
        kwargs["extra_chromium_args"] = merged_args

    kwargs["engine"] = engine if engine in SUPPORTED_ENGINES else "chromium"
    return kwargs


def browser_use_launch_kwargs(
    settings: Any = None, env: Optional[Mapping[str, str]] = None
) -> dict[str, Any]:
    kwargs = build_browser_config_kwargs(settings, env)
    kwargs.pop("engine", None)
    return kwargs
