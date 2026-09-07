"""
Open Manus — Streamlit App
===========================
Web-Oberfläche für Agent-Konfiguration und echte Task-Ausführung.

Führt den jeweils ausgewählten Agenten (Manus, SWE-Agent, Data-Analysis-Agent,
Browser-Agent) über die reale Agent-Engine aus. Es werden keine Ergebnisse
simuliert — ohne gültige LLM-Konfiguration wird das transparent angezeigt,
statt einen erfundenen Ablauf vorzutäuschen.
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st


def _bootstrap_llm_config_from_env() -> None:
    """Erzeugt config/config.toml aus Umgebungsvariablen, falls noch keine existiert.

    Erlaubt es, echte API-Zugangsdaten über Deployment-Secrets (Docker/CI)
    bereitzustellen, ohne Schlüssel im Repository abzulegen.
    """
    config_dir = Path(__file__).resolve().parent.parent / "config"
    config_path = config_dir / "config.toml"
    if config_path.exists():
        return

    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return

    model = os.environ.get("LLM_MODEL", "claude-3-7-sonnet-20250219")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.anthropic.com/v1/")
    api_type = os.environ.get("LLM_API_TYPE", "anthropic")
    api_version = os.environ.get("LLM_API_VERSION", "")
    max_tokens = os.environ.get("LLM_MAX_TOKENS", "8192")
    temperature = os.environ.get("LLM_TEMPERATURE", "0.0")

    config_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "[llm]\n"
        f'model = "{model}"\n'
        f'base_url = "{base_url}"\n'
        f'api_key = "{api_key}"\n'
        f"max_tokens = {max_tokens}\n"
        f"temperature = {temperature}\n"
        f'api_type = "{api_type}"\n'
        f'api_version = "{api_version}"\n'
    )


_bootstrap_llm_config_from_env()

AGENT_FRAMEWORK_ERROR: Optional[str] = None
try:
    from app.agent.browser import BrowserAgent
    from app.agent.data_analysis import DataAnalysis
    from app.agent.manus import Manus
    from app.agent.swe import SWEAgent
    from app.config import config
except Exception as exc:  # Startup-Fehler (z. B. fehlerhafte config.toml) sichtbar machen
    AGENT_FRAMEWORK_ERROR = str(exc)
    config = None


# ──────────────────────────────────────────────────────────────
# Konfiguration
# ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Open Manus",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# Verfügbare Agenten (reale Agent-Klassen aus app/agent)
# ──────────────────────────────────────────────────────────────

AGENT_TYPES = {
    "GeneralAgent": {
        "name": "General Agent",
        "description": "Allzweck-Agent für verschiedene Aufgaben (Manus)",
        "tools": ["python_execute", "browser_use", "str_replace_editor", "ask_human", "terminate"],
        "agent_class": Manus,
    },
    "CodeAgent": {
        "name": "Code Agent",
        "description": "Spezialisiert auf Programmierung & Code-Generierung (SWE-Agent)",
        "tools": ["bash", "str_replace_editor", "terminate"],
        "agent_class": SWEAgent,
    },
    "DataAnalysisAgent": {
        "name": "Datenanalyse-Agent",
        "description": "Analysiert Daten und erstellt Visualisierungen",
        "tools": ["python_execute", "visualization_preparation", "data_visualization", "terminate"],
        "agent_class": DataAnalysis,
    },
    "BrowserAgent": {
        "name": "Browser Agent",
        "description": "Automatisiert Web-Interaktionen",
        "tools": ["browser_use", "terminate"],
        "agent_class": BrowserAgent,
    },
} if AGENT_FRAMEWORK_ERROR is None else {}


def _is_llm_configured() -> bool:
    """Prüft, ob echte (nicht-Platzhalter) LLM-Zugangsdaten konfiguriert sind."""
    if config is None:
        return False
    try:
        llm_settings = config.llm.get("default")
    except Exception:
        return False
    if llm_settings is None:
        return False
    api_key = (llm_settings.api_key or "").strip()
    return bool(api_key) and api_key.upper() != "YOUR_API_KEY"


LLM_CONFIGURED = _is_llm_configured()


async def _create_agent(agent_class, max_steps: int, temperature: float):
    """Instanziiert den gewählten Agenten mit den UI-Einstellungen."""
    if agent_class is Manus:
        agent = await Manus.create()
    else:
        agent = agent_class()
    agent.max_steps = max_steps
    agent.llm.temperature = temperature
    return agent


def _messages_to_steps(messages: List) -> List[dict]:
    """Wandelt die echten Agent-Memory-Messages in anzeigbare Ausführungsschritte um."""
    steps: List[dict] = []
    for msg in messages:
        if msg.role == "user":
            continue
        if msg.role == "assistant":
            if msg.tool_calls:
                for call in msg.tool_calls:
                    steps.append({
                        "step": len(steps) + 1,
                        "type": "tool_call",
                        "tool": call.function.name,
                        "content": f"Argumente: {call.function.arguments}",
                        "result": None,
                        "timestamp": datetime.now().isoformat(),
                    })
            if msg.content:
                steps.append({
                    "step": len(steps) + 1,
                    "type": "thinking",
                    "content": msg.content,
                    "timestamp": datetime.now().isoformat(),
                })
        elif msg.role == "tool":
            for step in reversed(steps):
                if step["type"] == "tool_call" and step["tool"] == msg.name and step["result"] is None:
                    step["result"] = msg.content
                    break
    if steps:
        steps[-1] = {**steps[-1], "type": "response"}
    return steps


async def _run_agent(agent_class, task: str, max_steps: int, temperature: float):
    """Führt den realen Agenten aus (inkl. Cleanup) und liefert Ergebnis plus Ausführungsschritte."""
    agent = await _create_agent(agent_class, max_steps, temperature)
    result = await agent.run(task)
    steps = _messages_to_steps(agent.memory.messages)
    return result, steps


# ──────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────

st.title("🤖 Open Manus")
st.markdown("**Agent-Konfiguration & Task-Ausführung — Open Manus Web UI**")

if AGENT_FRAMEWORK_ERROR:
    st.error(
        "⚠️ Die Agent-Engine konnte nicht geladen werden. Fehler:\n\n"
        f"```\n{AGENT_FRAMEWORK_ERROR}\n```"
    )
    st.stop()

if not LLM_CONFIGURED:
    st.warning(
        "⚠️ **Keine echte LLM-Konfiguration gefunden.** Diese App führt Agenten "
        "ausschließlich mit einem echten LLM-Zugang aus — es werden keine "
        "Demo-/Beispielergebnisse angezeigt.\n\n"
        "So aktivierst du echte Ausführungen:\n"
        "- Lokal: `config/config.toml` aus `config/config.example.toml` erstellen und einen "
        "echten API-Key eintragen, oder\n"
        "- Im Deployment: Umgebungsvariable `LLM_API_KEY` setzen (optional `LLM_MODEL`, "
        "`LLM_BASE_URL`, `LLM_API_TYPE`, `LLM_API_VERSION`)."
    )

# ── Seitenleiste ──────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Agent-Konfiguration")

    agent_type = st.selectbox(
        "Agent-Typ",
        options=list(AGENT_TYPES.keys()),
        format_func=lambda x: AGENT_TYPES[x]["name"],
        help="Wählen Sie den Agent-Typ für Ihre Aufgabe.",
    )

    agent_info = AGENT_TYPES[agent_type]
    st.caption(f"📝 {agent_info['description']}")
    st.caption(f"🔧 Tools: {', '.join(agent_info['tools'])}")

    st.divider()

    st.markdown("### 🧠 LLM-Einstellungen")

    if LLM_CONFIGURED:
        default_llm = config.llm["default"]
        st.caption(f"Modell: **{default_llm.model}**")
        st.caption(f"Provider: {default_llm.api_type or 'openai-kompatibel'} | Max Tokens: {default_llm.max_tokens}")
    else:
        st.caption("Kein Modell konfiguriert — siehe Hinweis oben.")

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1,
        help="Wird direkt an das reale LLM für diesen Lauf übergeben.",
    )

    max_steps = st.slider(
        "Maximale Schritte",
        min_value=1,
        max_value=20,
        value=5,
        help="Maximale Anzahl an echten Agent-Schritten pro Task.",
    )

    st.divider()

    st.markdown("### 🔒 Sandbox")
    sandbox_config = config.sandbox if config is not None else None
    if sandbox_config is not None:
        st.caption("✅ Aktiv" if sandbox_config.use_sandbox else "❌ Inaktiv (Tools laufen direkt im Container)")
        if sandbox_config.use_sandbox:
            st.caption(f"🐳 Docker-Container: {sandbox_config.image}")
            st.caption(f"💾 Memory-Limit: {sandbox_config.memory_limit}")
            st.caption(f"⏱️ Timeout: {sandbox_config.timeout}s")

    st.divider()

    st.markdown("### 🌐 MCP-Server")
    mcp_servers = config.mcp_config.servers if config is not None else {}
    if mcp_servers:
        for server_id, server_cfg in mcp_servers.items():
            st.caption(f"🔗 {server_id}: {server_cfg.type} ({server_cfg.url or server_cfg.command})")
    else:
        st.caption("Keine MCP-Server in config/mcp.json konfiguriert.")

# ── Hauptbereich ──────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Task ausführen",
    "📋 Ergebnisse",
    "📜 Verlauf",
    "⚙️ System-Info",
])

# ── Tab 1: Task ausführen ─────────────────────────────────────

with tab1:
    st.markdown("### 🚀 Task definieren & ausführen")

    task = st.text_area(
        "Aufgabe",
        value="Analysiere die aktuellen Top-5 Python-Bibliotheken für Machine Learning und erstelle eine Vergleichstabelle.",
        height=120,
        placeholder="Beschreiben Sie die Aufgabe, die der Agent ausführen soll...",
        help="Je präziser die Beschreibung, desto besser das Ergebnis.",
    )

    col1, col2 = st.columns(2)
    with col1:
        execute_button = st.button(
            "🤖 Agent starten",
            type="primary",
            use_container_width=True,
            disabled=not LLM_CONFIGURED,
        )
    with col2:
        clear_button = st.button(
            "🗑️ Zurücksetzen",
            use_container_width=True,
        )

    if clear_button:
        st.session_state.agent_steps = None
        st.session_state.agent_result = None
        st.rerun()

    if execute_button and task.strip():
        st.session_state.agent_task = task
        st.session_state.agent_type = agent_type

        with st.spinner("Agent läuft — echte LLM-Aufrufe und Tool-Ausführungen..."):
            try:
                result, steps = asyncio.run(
                    _run_agent(agent_info["agent_class"], task, max_steps, temperature)
                )
                st.session_state.agent_steps = steps
                st.session_state.agent_result = result
                st.session_state.agent_error = None
            except Exception as exc:
                st.session_state.agent_steps = None
                st.session_state.agent_result = None
                st.session_state.agent_error = str(exc)

        if st.session_state.get("agent_error"):
            st.error(f"❌ Agent-Ausführung fehlgeschlagen: {st.session_state.agent_error}")
        else:
            st.success("Agent-Ausführung erfolgreich beendet!")

    elif execute_button:
        st.warning("Bitte geben Sie eine Aufgabe ein.")

# ── Tab 2: Ergebnisse ─────────────────────────────────────────

with tab2:
    if st.session_state.get("agent_steps"):
        steps = st.session_state.agent_steps

        st.markdown("### 📋 Ausführungsergebnis")
        st.success(st.session_state.agent_result)

        st.divider()

        st.markdown("### 🔍 Ausführungsschritte")

        for step in steps:
            if step["type"] == "thinking":
                with st.expander(f"💭 Schritt {step['step']}: Denkprozess", expanded=False):
                    st.text(step["content"])
            elif step["type"] == "tool_call":
                with st.expander(f"🔧 Schritt {step['step']}: {step['tool']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Aufruf:**")
                        st.code(step["content"], language="json")
                    with col2:
                        st.markdown("**Ergebnis:**")
                        st.success(step["result"] or "Kein Ergebnis erfasst.")
            elif step["type"] == "response":
                with st.expander(f"✅ Schritt {step['step']}: Antwort", expanded=True):
                    st.markdown(step["content"])

        st.divider()
        st.markdown("### 📊 Ausführungs-Metadaten")
        meta_df = pd.DataFrame([{
            "Metrik": "Agent-Typ",
            "Wert": AGENT_TYPES[st.session_state.agent_type]["name"],
        }, {
            "Metrik": "Modell",
            "Wert": config.llm["default"].model if LLM_CONFIGURED else "N/A",
        }, {
            "Metrik": "Schritte",
            "Wert": len(steps),
        }, {
            "Metrik": "Tool-Aufrufe",
            "Wert": sum(1 for s in steps if s["type"] == "tool_call"),
        }, {
            "Metrik": "Sandbox",
            "Wert": "Aktiv" if config.sandbox.use_sandbox else "Inaktiv",
        }])
        st.dataframe(meta_df, use_container_width=True, hide_index=True)
    elif st.session_state.get("agent_error"):
        st.error(f"❌ Letzter Lauf fehlgeschlagen: {st.session_state.agent_error}")
    else:
        st.info("Führen Sie zuerst einen Task aus (Tab 1). Es werden ausschließlich echte Ausführungsergebnisse angezeigt.")

# ── Tab 3: Verlauf ───────────────────────────────────────────

with tab3:
    st.markdown("### 📜 Task-Verlauf")

    if "task_history" not in st.session_state:
        st.session_state.task_history = []

    if st.session_state.get("agent_task") and st.session_state.get("agent_steps"):
        current_entry = {
            "task": st.session_state.agent_task,
            "agent_type": AGENT_TYPES[st.session_state.agent_type]["name"],
            "model": config.llm["default"].model if LLM_CONFIGURED else "N/A",
            "steps": len(st.session_state.agent_steps),
            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "status": "Erfolgreich",
        }

        if not st.session_state.task_history or st.session_state.task_history[0]["task"] != current_entry["task"]:
            st.session_state.task_history.insert(0, current_entry)

    if st.session_state.task_history:
        df_history = pd.DataFrame(st.session_state.task_history)
        st.dataframe(df_history, use_container_width=True, hide_index=True)

        if st.button("🗑️ Verlauf löschen"):
            st.session_state.task_history = []
            st.rerun()
    else:
        st.info("Noch keine Tasks im Verlauf.")

# ── Tab 4: System-Info ────────────────────────────────────────

with tab4:
    st.markdown("### ⚙️ System-Informationen")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🤖 Agent-Konfiguration")
        st.json({
            "agent_type": agent_type,
            "agent_name": AGENT_TYPES[agent_type]["name"],
            "tools": AGENT_TYPES[agent_type]["tools"],
            "model": config.llm["default"].model if LLM_CONFIGURED else None,
            "model_configured": LLM_CONFIGURED,
            "temperature": temperature,
            "max_steps": max_steps,
        })

    with col2:
        st.markdown("#### 🔒 Sandbox-Status")
        st.json({
            "sandbox_enabled": config.sandbox.use_sandbox,
            "image": config.sandbox.image,
            "memory_limit": config.sandbox.memory_limit,
            "cpu_limit": config.sandbox.cpu_limit,
            "timeout": config.sandbox.timeout,
        })

    st.divider()

    st.markdown("#### 🌐 MCP-Server")
    st.json({
        "servers": {
            server_id: {"type": cfg.type, "endpoint": cfg.url or cfg.command}
            for server_id, cfg in config.mcp_config.servers.items()
        }
    })

    st.divider()

    st.markdown("#### 📦 Verfügbare Agent-Typen")
    agents_df = pd.DataFrame([{
        "Agent": info["name"],
        "Beschreibung": info["description"],
        "Tools": ", ".join(info["tools"]),
    } for key, info in AGENT_TYPES.items()])
    st.dataframe(agents_df, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────

st.divider()
st.caption(f"🤖 Open Manus v1.0 | Agent Framework | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
