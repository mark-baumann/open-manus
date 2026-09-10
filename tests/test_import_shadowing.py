"""Regressionstests für SDK-Namenskollisionen (AUG-395).

Streamlit stellt das Verzeichnis des Skripts (``app/``) an den Anfang von
``sys.path``. Ein lokales Paket ``app/mcp`` würde deshalb das installierte
``mcp``-SDK überschreiben, sodass ``from mcp import ClientSession`` auf das
leere lokale ``app/mcp/__init__.py`` zeigt:

    cannot import name 'ClientSession' from 'mcp' (/app/app/mcp/__init__.py)

Diese Tests stellen sicher, dass das lokale Paket umbenannt bleibt und das SDK
nicht mehr verdeckt.
"""

import importlib.util
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent / "app"


def _find_spec_with_app_dir_on_path(module_name: str):
    """Löst ``module_name`` auf, als liefe die App aus dem ``app/``-Verzeichnis."""
    original_path = list(sys.path)
    sys.path.insert(0, str(APP_DIR))
    try:
        return importlib.util.find_spec(module_name)
    finally:
        sys.path[:] = original_path


def test_local_mcp_package_is_renamed():
    assert not (APP_DIR / "mcp").exists(), (
        "app/mcp existiert und verdeckt das installierte mcp-SDK, sobald app/ "
        "auf sys.path liegt (Streamlit). Paket muss app/mcp_server heißen."
    )
    assert (APP_DIR / "mcp_server" / "server.py").is_file()


def test_mcp_sdk_is_not_shadowed_by_local_package():
    spec = _find_spec_with_app_dir_on_path("mcp")

    if spec is None or spec.origin is None:
        # SDK nicht installiert: dann darf der Import wenigstens nicht
        # stillschweigend auf ein lokales Paket zeigen.
        assert not (APP_DIR / "mcp").exists()
        return

    resolved = Path(spec.origin).resolve()
    assert (
        APP_DIR.resolve() not in resolved.parents
    ), f"'import mcp' wurde vom lokalen Paket verdeckt: {resolved}"
