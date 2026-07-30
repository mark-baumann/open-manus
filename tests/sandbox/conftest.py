"""Conftest für Sandbox-Tests — überspringt Tests wenn Docker nicht verfügbar ist."""
import pytest


def pytest_collection_modifyitems(config, items):
    """Überspringt Sandbox-Tests wenn Docker fehlt."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception:
        skip_msg = "Docker ist nicht verfügbar — Sandbox-Tests werden übersprungen"
        for item in items:
            # Nur Tests im sandbox-Verzeichnis überspringen
            if "sandbox" in str(item.fspath):
                item.add_marker(pytest.mark.skip(reason=skip_msg))
