"""Unit-Tests für app/schema.py"""

import pytest
from app.schema import (
    AgentState,
    Function,
    Memory,
    Message,
    Role,
    ToolCall,
    ToolChoice,
)


class TestRole:
    """Tests für Role-Enum."""

    def test_role_values(self):
        """Alle erwarteten Rollen sind vorhanden."""
        assert Role.SYSTEM.value == "system"
        assert Role.USER.value == "user"
        assert Role.ASSISTANT.value == "assistant"
        assert Role.TOOL.value == "tool"

    def test_role_count(self):
        """Es gibt genau 4 Rollen."""
        assert len(Role) == 4


class TestToolChoice:
    """Tests für ToolChoice-Enum."""

    def test_tool_choice_values(self):
        """Alle erwarteten Tool-Choice-Werte sind vorhanden."""
        assert ToolChoice.NONE.value == "none"
        assert ToolChoice.AUTO.value == "auto"
        assert ToolChoice.REQUIRED.value == "required"


class TestAgentState:
    """Tests für AgentState-Enum."""

    def test_agent_state_values(self):
        """Alle erwarteten Agent-Zustände sind vorhanden."""
        assert AgentState.IDLE.value == "IDLE"
        assert AgentState.RUNNING.value == "RUNNING"
        assert AgentState.FINISHED.value == "FINISHED"
        assert AgentState.ERROR.value == "ERROR"


class TestFunction:
    """Tests für Function-Modell."""

    def test_create_function(self):
        """Function kann mit name und arguments erstellt werden."""
        func = Function(name="test_func", arguments='{"key": "value"}')
        assert func.name == "test_func"
        assert func.arguments == '{"key": "value"}'


class TestToolCall:
    """Tests für ToolCall-Modell."""

    def test_create_tool_call(self):
        """ToolCall kann mit id und function erstellt werden."""
        func = Function(name="test_func", arguments="{}")
        call = ToolCall(id="call_123", function=func)
        assert call.id == "call_123"
        assert call.type == "function"
        assert call.function.name == "test_func"


class TestMessage:
    """Tests für Message-Modell."""

    def test_user_message(self):
        """user_message erstellt eine User-Nachricht."""
        msg = Message.user_message("Hallo Welt")
        assert msg.role == Role.USER.value
        assert msg.content == "Hallo Welt"

    def test_system_message(self):
        """system_message erstellt eine System-Nachricht."""
        msg = Message.system_message("Du bist ein Assistent.")
        assert msg.role == Role.SYSTEM.value
        assert msg.content == "Du bist ein Assistent."

    def test_assistant_message(self):
        """assistant_message erstellt eine Assistant-Nachricht."""
        msg = Message.assistant_message("Ich helfe gerne.")
        assert msg.role == Role.ASSISTANT.value
        assert msg.content == "Ich helfe gerne."

    def test_assistant_message_empty(self):
        """assistant_message ohne content erstellt leere Nachricht."""
        msg = Message.assistant_message()
        assert msg.role == Role.ASSISTANT.value
        assert msg.content is None

    def test_tool_message(self):
        """tool_message erstellt eine Tool-Nachricht."""
        msg = Message.tool_message(
            content="Ergebnis", name="search", tool_call_id="call_1"
        )
        assert msg.role == Role.TOOL.value
        assert msg.content == "Ergebnis"
        assert msg.name == "search"
        assert msg.tool_call_id == "call_1"

    def test_message_add_list(self):
        """Message + list ergibt Liste mit Message vorne."""
        msg = Message.user_message("A")
        result = msg + [Message.user_message("B")]
        assert len(result) == 2
        assert result[0].content == "A"
        assert result[1].content == "B"

    def test_message_add_message(self):
        """Message + Message ergibt Liste mit beiden."""
        msg1 = Message.user_message("A")
        msg2 = Message.user_message("B")
        result = msg1 + msg2
        assert len(result) == 2
        assert result[0].content == "A"
        assert result[1].content == "B"

    def test_list_radd_message(self):
        """list + Message ergibt Liste mit Message hinten."""
        msg1 = Message.user_message("A")
        msg2 = Message.user_message("B")
        result = [msg1] + msg2
        assert len(result) == 2
        assert result[0].content == "A"
        assert result[1].content == "B"

    def test_message_add_type_error(self):
        """Message + nicht-Message/Liste wirft TypeError."""
        msg = Message.user_message("A")
        with pytest.raises(TypeError):
            msg + 42

    def test_to_dict_basic(self):
        """to_dict konvertiert Basis-Nachricht korrekt."""
        msg = Message.user_message("Test")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Test"}

    def test_to_dict_with_tool_calls(self):
        """to_dict enthält tool_calls wenn vorhanden."""
        func = Function(name="f", arguments="{}")
        call = ToolCall(id="c1", function=func)
        msg = Message(role=Role.ASSISTANT, tool_calls=[call])
        d = msg.to_dict()
        assert d["role"] == "assistant"
        assert "tool_calls" in d
        assert len(d["tool_calls"]) == 1

    def test_to_dict_with_base64_image(self):
        """to_dict enthält base64_image wenn vorhanden."""
        msg = Message.user_message("Bild", base64_image="abc123")
        d = msg.to_dict()
        assert d["base64_image"] == "abc123"

    def test_from_tool_calls(self):
        """from_tool_calls erstellt Assistant-Nachricht aus ToolCalls."""
        func = Function(name="search", arguments='{"q": "test"}')
        call = ToolCall(id="call_1", function=func)
        msg = Message.from_tool_calls(tool_calls=[call], content="Suche...")
        assert msg.role == Role.ASSISTANT.value
        assert msg.content == "Suche..."
        assert len(msg.tool_calls) == 1


class TestMemory:
    """Tests für Memory-Modell."""

    def test_add_message(self):
        """add_message fügt eine Nachricht hinzu."""
        mem = Memory()
        msg = Message.user_message("Test")
        mem.add_message(msg)
        assert len(mem.messages) == 1
        assert mem.messages[0].content == "Test"

    def test_add_messages(self):
        """add_messages fügt mehrere Nachrichten hinzu."""
        mem = Memory()
        msgs = [Message.user_message("A"), Message.user_message("B")]
        mem.add_messages(msgs)
        assert len(mem.messages) == 2

    def test_max_messages_limit(self):
        """Alte Nachrichten werden bei Überschreitung von max_messages entfernt."""
        mem = Memory(max_messages=3)
        for i in range(5):
            mem.add_message(Message.user_message(str(i)))
        assert len(mem.messages) == 3
        assert mem.messages[0].content == "2"
        assert mem.messages[-1].content == "4"

    def test_clear(self):
        """clear löscht alle Nachrichten."""
        mem = Memory()
        mem.add_message(Message.user_message("Test"))
        mem.clear()
        assert len(mem.messages) == 0

    def test_get_recent_messages(self):
        """get_recent_messages gibt die letzten n Nachrichten zurück."""
        mem = Memory()
        for i in range(5):
            mem.add_message(Message.user_message(str(i)))
        recent = mem.get_recent_messages(2)
        assert len(recent) == 2
        assert recent[0].content == "3"
        assert recent[1].content == "4"

    def test_to_dict_list(self):
        """to_dict_list konvertiert alle Nachrichten in Dicts."""
        mem = Memory()
        mem.add_message(Message.user_message("A"))
        mem.add_message(Message.system_message("B"))
        result = mem.to_dict_list()
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "system"

    def test_default_max_messages(self):
        """Standard max_messages ist 100."""
        mem = Memory()
        assert mem.max_messages == 100

    def test_empty_memory(self):
        """Neue Memory ist leer."""
        mem = Memory()
        assert len(mem.messages) == 0
