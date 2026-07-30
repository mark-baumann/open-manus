"""Unit-Tests für app/utils/files_utils.py"""

import pytest
from app.utils.files_utils import clean_path, should_exclude_file


class TestShouldExcludeFile:
    """Tests für die should_exclude_file-Funktion."""

    def test_excluded_filename(self):
        """Dateien mit ausgeschlossenen Namen werden erkannt."""
        assert should_exclude_file(".DS_Store") is True
        assert should_exclude_file("package-lock.json") is True
        assert should_exclude_file("tsconfig.json") is True

    def test_not_excluded_filename(self):
        """Normale Dateinamen werden nicht ausgeschlossen."""
        assert should_exclude_file("main.py") is False
        assert should_exclude_file("README.md") is False
        assert should_exclude_file("app.py") is False

    def test_excluded_directory(self):
        """Dateien in ausgeschlossenen Verzeichnissen werden erkannt."""
        assert should_exclude_file("node_modules/package/index.js") is True
        assert should_exclude_file(".git/config") is True
        assert should_exclude_file("dist/bundle.js") is True
        assert should_exclude_file("build/output.txt") is True

    def test_not_excluded_directory(self):
        """Dateien in normalen Verzeichnissen werden nicht ausgeschlossen."""
        assert should_exclude_file("src/main.py") is False
        assert should_exclude_file("app/utils/helper.py") is False

    def test_excluded_extension(self):
        """Dateien mit ausgeschlossenen Endungen werden erkannt."""
        assert should_exclude_file("image.png") is True
        assert should_exclude_file("photo.jpg") is True
        assert should_exclude_file("icon.svg") is True
        assert should_exclude_file("data.db") is True

    def test_not_excluded_extension(self):
        """Dateien mit normalen Endungen werden nicht ausgeschlossen."""
        assert should_exclude_file("script.py") is False
        assert should_exclude_file("config.yaml") is False
        assert should_exclude_file("document.md") is False


class TestCleanPath:
    """Tests für die clean_path-Funktion."""

    def test_leading_slash_removed(self):
        """Führender Schrägstrich wird entfernt und Workspace-Präfix bereinigt."""
        assert clean_path("/workspace/test.txt") == "test.txt"

    def test_workspace_prefix_removed(self):
        """Workspace-Präfix wird entfernt."""
        assert clean_path("workspace/test.txt") == "test.txt"

    def test_workspace_slash_prefix_removed(self):
        """workspace/-Präfix wird entfernt."""
        assert clean_path("workspace/subdir/file.py") == "subdir/file.py"

    def test_already_clean_path(self):
        """Bereits bereinigter Pfad bleibt unverändert."""
        assert clean_path("test.txt") == "test.txt"
        assert clean_path("subdir/file.py") == "subdir/file.py"

    def test_custom_workspace_path(self):
        """Benutzerdefinierter Workspace-Pfad wird verwendet."""
        assert clean_path("/home/user/project/file.py", "/home/user") == "project/file.py"

    def test_empty_path(self):
        """Leerer Pfad bleibt leer."""
        assert clean_path("") == ""

    def test_multiple_slashes(self):
        """Mehrere Schrägstriche und Workspace-Präfix werden bereinigt."""
        assert clean_path("///workspace/test.txt") == "test.txt"
