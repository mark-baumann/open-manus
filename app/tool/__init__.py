from app.tool.base import BaseTool
from app.tool.tool_collection import ToolCollection

# Leichtgewichtige Tools (keine externen Abhängigkeiten)
from app.tool.create_chat_completion import CreateChatCompletion
from app.tool.terminate import Terminate

# Tools mit optionalen Abhängigkeiten
try:
    from app.tool.bash import Bash
except ImportError:
    Bash = None  # type: ignore

try:
    from app.tool.browser_use_tool import BrowserUseTool
except ImportError:
    BrowserUseTool = None  # type: ignore

try:
    from app.tool.crawl4ai import Crawl4aiTool
except ImportError:
    Crawl4aiTool = None  # type: ignore

try:
    from app.tool.planning import PlanningTool
except ImportError:
    PlanningTool = None  # type: ignore

try:
    from app.tool.str_replace_editor import StrReplaceEditor
except ImportError:
    StrReplaceEditor = None  # type: ignore

try:
    from app.tool.web_search import WebSearch
except ImportError:
    WebSearch = None  # type: ignore


__all__ = [
    "BaseTool",
    "Bash",
    "BrowserUseTool",
    "Terminate",
    "StrReplaceEditor",
    "WebSearch",
    "ToolCollection",
    "CreateChatCompletion",
    "PlanningTool",
    "Crawl4aiTool",
]
