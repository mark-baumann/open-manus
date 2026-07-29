"""Unit-Tests für app/tool/tool_collection.py"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock

# Direkt importieren, um schwere Abhängigkeiten in app/tool/__init__.py zu vermeiden
from app.tool.base import BaseTool, ToolResult
from app.tool.tool_collection import ToolCollection


class DummyTool(BaseTool):
    """Einfacher Dummy-Tool für Tests."""
    name: str = "dummy"
    description: str = "Ein Dummy-Tool"

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(output=f"executed: {kwargs}")


class FailingTool(BaseTool):
    """Tool das immer fehlschlägt."""
    name: str = "failing"
    description: str = "Ein fehlschlagendes Tool"

    async def execute(self, **kwargs) -> ToolResult:
        raise Exception("absichtlicher Fehler")


class TestToolCollection:
    """Tests für ToolCollection."""

    def test_create_empty(self):
        """Leere ToolCollection kann erstellt werden."""
        coll = ToolCollection()
        assert len(list(coll)) == 0

    def test_create_with_tools(self):
        """ToolCollection kann mit Tools erstellt werden."""
        t1 = DummyTool(name="tool1")
        t2 = DummyTool(name="tool2")
        coll = ToolCollection(t1, t2)
        assert len(list(coll)) == 2

    def test_tool_map(self):
        """tool_map enthält Tools nach Namen."""
        t1 = DummyTool(name="tool1")
        t2 = DummyTool(name="tool2")
        coll = ToolCollection(t1, t2)
        assert coll.tool_map["tool1"] is t1
        assert coll.tool_map["tool2"] is t2

    def test_to_params(self):
        """to_params gibt Liste von Tool-Parametern zurück."""
        t1 = DummyTool(name="tool1")
        coll = ToolCollection(t1)
        params = coll.to_params()
        assert len(params) == 1
        assert params[0]["type"] == "function"
        assert params[0]["function"]["name"] == "tool1"

    def test_get_tool_existing(self):
        """get_tool gibt vorhandenes Tool zurück."""
        t1 = DummyTool(name="tool1")
        coll = ToolCollection(t1)
        assert coll.get_tool("tool1") is t1

    def test_get_tool_missing(self):
        """get_tool gibt None für nicht vorhandenes Tool zurück."""
        coll = ToolCollection()
        assert coll.get_tool("nonexistent") is None

    def test_add_tool(self):
        """add_tool fügt ein Tool hinzu."""
        coll = ToolCollection()
        t1 = DummyTool(name="tool1")
        result = coll.add_tool(t1)
        assert result is coll  # Fluent-Interface
        assert coll.get_tool("tool1") is t1

    def test_add_tool_duplicate(self):
        """add_tool überspringt doppelte Tools."""
        t1 = DummyTool(name="tool1")
        t2 = DummyTool(name="tool1")
        coll = ToolCollection(t1)
        coll.add_tool(t2)
        assert len(list(coll)) == 1  # Kein Duplikat

    def test_add_tools(self):
        """add_tools fügt mehrere Tools hinzu."""
        coll = ToolCollection()
        t1 = DummyTool(name="tool1")
        t2 = DummyTool(name="tool2")
        coll.add_tools(t1, t2)
        assert len(list(coll)) == 2

    @pytest.mark.asyncio
    async def test_execute_existing_tool(self):
        """execute führt vorhandenes Tool aus."""
        t1 = DummyTool(name="tool1")
        coll = ToolCollection(t1)
        result = await coll.execute(name="tool1", tool_input={"key": "val"})
        assert result.output == "executed: {'key': 'val'}"

    @pytest.mark.asyncio
    async def test_execute_missing_tool(self):
        """execute gibt ToolFailure für nicht vorhandenes Tool zurück."""
        coll = ToolCollection()
        result = await coll.execute(name="nonexistent", tool_input={})
        assert result.error == "Tool nonexistent is invalid"

    @pytest.mark.asyncio
    async def test_execute_all(self):
        """execute_all führt alle Tools aus."""
        t1 = DummyTool(name="tool1")
        t2 = DummyTool(name="tool2")
        coll = ToolCollection(t1, t2)
        results = await coll.execute_all()
        assert len(results) == 2
        assert results[0].output == "executed: {}"
        assert results[1].output == "executed: {}"

    def test_iteration(self):
        """ToolCollection ist iterierbar."""
        t1 = DummyTool(name="tool1")
        t2 = DummyTool(name="tool2")
        coll = ToolCollection(t1, t2)
        names = [t.name for t in coll]
        assert names == ["tool1", "tool2"]
