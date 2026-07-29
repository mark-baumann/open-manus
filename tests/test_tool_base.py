"""Unit-Tests für app/tool/base.py"""

import sys
import pytest

# Direkt importieren, um schwere Abhängigkeiten in app/tool/__init__.py zu vermeiden
from app.tool.base import ToolResult


class TestToolResult:
    """Tests für ToolResult-Modell."""

    def test_create_with_output(self):
        """ToolResult kann mit output erstellt werden."""
        result = ToolResult(output="Erfolg")
        assert result.output == "Erfolg"
        assert result.error is None

    def test_create_with_error(self):
        """ToolResult kann mit error erstellt werden."""
        result = ToolResult(error="Fehler aufgetreten")
        assert result.error == "Fehler aufgetreten"
        assert result.output is None

    def test_bool_true_with_output(self):
        """ToolResult mit output ist truthy."""
        result = ToolResult(output="data")
        assert bool(result) is True

    def test_bool_true_with_error(self):
        """ToolResult mit error ist truthy."""
        result = ToolResult(error="fail")
        assert bool(result) is True

    def test_bool_false_empty(self):
        """Leeres ToolResult ist falsy."""
        result = ToolResult()
        assert bool(result) is False

    def test_str_with_output(self):
        """str() gibt output zurück wenn kein error."""
        result = ToolResult(output="Ergebnis")
        assert str(result) == "Ergebnis"

    def test_str_with_error(self):
        """str() gibt Fehlermeldung zurück wenn error gesetzt."""
        result = ToolResult(error="Fehler")
        assert str(result) == "Error: Fehler"

    def test_add_two_results(self):
        """Zwei ToolResults können addiert werden."""
        r1 = ToolResult(output="Teil1")
        r2 = ToolResult(output="Teil2")
        combined = r1 + r2
        assert combined.output == "Teil1Teil2"

    def test_add_output_and_error(self):
        """ToolResult mit output + ToolResult mit error kombiniert beides."""
        r1 = ToolResult(output="OK")
        r2 = ToolResult(error="Fail")
        combined = r1 + r2
        assert combined.output == "OK"
        assert combined.error == "Fail"

    def test_add_base64_conflict_raises(self):
        """Zwei base64_image-Werte werfen ValueError."""
        r1 = ToolResult(base64_image="img1")
        r2 = ToolResult(base64_image="img2")
        with pytest.raises(ValueError, match="Cannot combine"):
            r1 + r2

    def test_replace(self):
        """replace erstellt neues ToolResult mit geänderten Feldern."""
        r1 = ToolResult(output="alt", error="fehler")
        r2 = r1.replace(output="neu")
        assert r2.output == "neu"
        assert r2.error == "fehler"
        assert r1.output == "alt"  # Original unverändert

    def test_system_field(self):
        """ToolResult unterstützt system-Feld."""
        result = ToolResult(system="Systemmeldung")
        assert result.system == "Systemmeldung"
