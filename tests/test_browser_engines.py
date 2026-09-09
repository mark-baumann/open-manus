from types import SimpleNamespace

import pytest

from app.browser_engines import (
    browser_use_launch_kwargs,
    build_browser_config_kwargs,
    describe_engines,
    normalize_engine,
    resolve_engine_binary,
)


def test_normalize_engine_aliases():
    assert normalize_engine(None) == "chromium"
    assert normalize_engine("Chrome") == "chrome"
    assert normalize_engine("edge") == "msedge"
    assert normalize_engine("google-chrome") == "chrome"
    assert normalize_engine("safari") == "webkit"


def test_unsupported_engine_raises():
    with pytest.raises(ValueError, match="Firefox"):
        build_browser_config_kwargs(env={"BROWSER_ENGINE": "firefox", "DISPLAY": ":0"})


def test_headless_default_without_display():
    kwargs = build_browser_config_kwargs(env={"BROWSER_ENGINE": "chromium"})
    assert kwargs["headless"] is True
    assert "--no-sandbox" in kwargs["extra_chromium_args"]
    assert kwargs["engine"] == "chromium"


def test_headless_false_when_display_and_setting():
    settings = SimpleNamespace(
        engine="chromium",
        headless=False,
        disable_security=True,
        extra_chromium_args=[],
        chrome_instance_path=None,
        wss_url=None,
        cdp_url=None,
        proxy=None,
    )
    kwargs = build_browser_config_kwargs(settings, env={"DISPLAY": ":0"})
    assert kwargs["headless"] is False
    assert "extra_chromium_args" not in kwargs


def test_env_overrides_settings():
    settings = SimpleNamespace(
        engine="chromium",
        headless=False,
        disable_security=False,
        extra_chromium_args=["--foo"],
        chrome_instance_path=None,
        wss_url=None,
        cdp_url=None,
        proxy=None,
    )
    kwargs = build_browser_config_kwargs(
        settings,
        env={
            "BROWSER_ENGINE": "chrome",
            "BROWSER_HEADLESS": "true",
            "CHROME_INSTANCE_PATH": "/tmp/fake-chrome",
            "BROWSER_CDP_URL": "http://127.0.0.1:9222",
        },
    )
    assert kwargs["engine"] == "chrome"
    assert kwargs["headless"] is True
    assert kwargs["chrome_instance_path"] == "/tmp/fake-chrome"
    assert kwargs["cdp_url"] == "http://127.0.0.1:9222"
    assert "--foo" in kwargs["extra_chromium_args"]
    assert "--no-sandbox" in kwargs["extra_chromium_args"]


def test_browser_use_launch_kwargs_strips_engine():
    kwargs = browser_use_launch_kwargs(env={"BROWSER_ENGINE": "chromium"})
    assert "engine" not in kwargs
    assert kwargs["headless"] is True


def test_describe_engines_includes_unsupported():
    infos = describe_engines()
    ids = [info.id for info in infos]
    assert ids == ["chromium", "chrome", "msedge", "firefox", "webkit"]
    chromium = infos[0]
    assert chromium.supported is True
    firefox = next(info for info in infos if info.id == "firefox")
    assert firefox.supported is False


def test_resolve_engine_binary_explicit_path():
    assert resolve_engine_binary("chrome", "/opt/custom/chrome") == "/opt/custom/chrome"
    assert resolve_engine_binary("chromium") is None
