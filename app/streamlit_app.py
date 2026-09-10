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
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _bootstrap_llm_config_from_env() -> None:
    """Erzeugt config/config.toml aus Umgebungsvariablen, falls noch keine existiert.

    Erlaubt es, echte API-Zugangsdaten über Deployment-Secrets (Docker/CI)
    bereitzustellen, ohne Schlüssel im Repository abzulegen.
    """
    config_dir = PROJECT_ROOT / "config"
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
    from app.browser_engines import ENGINE_LABELS, SUPPORTED_ENGINES, describe_engines
    from app.config import LLMSettings, config
except (
    Exception
) as exc:  # Startup-Fehler (z. B. fehlerhafte config.toml) sichtbar machen
    AGENT_FRAMEWORK_ERROR = str(exc)
    config = None


# ──────────────────────────────────────────────────────────────
# LLM über die GUI verbinden (statt nur config.toml / Env-Variablen)
# ──────────────────────────────────────────────────────────────

LLM_PROVIDER_PRESETS = {
    "Anthropic": {
        "api_type": "anthropic",
        "base_url": "https://api.anthropic.com/v1/",
        "model": "claude-3-7-sonnet-20250219",
    },
    "OpenAI": {
        "api_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o",
    },
    "Azure OpenAI": {
        "api_type": "azure",
        "base_url": "",
        "model": "",
    },
    "Ollama (lokal)": {
        "api_type": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
    },
    "Sonstiger OpenAI-kompatibler Anbieter": {
        "api_type": "openai",
        "base_url": "",
        "model": "",
    },
}


def _config_toml_path() -> Path:
    return PROJECT_ROOT / "config" / "config.toml"


def _render_llm_toml_block(settings: dict) -> str:
    lines = ["[llm]"]
    for key in (
        "model",
        "base_url",
        "api_key",
        "max_tokens",
        "temperature",
        "api_type",
        "api_version",
    ):
        value = settings[key]
        if isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def _save_llm_settings(settings: dict) -> None:
    """Schreibt die LLM-Zugangsdaten aus der GUI in config/config.toml.

    Ersetzt ausschließlich den [llm]-Block, alle anderen Abschnitte (Browser,
    Sandbox, MCP, ...) bleiben unverändert erhalten.
    """
    config_path = _config_toml_path()
    new_block = _render_llm_toml_block(settings)

    if config_path.exists():
        original = config_path.read_text()
        pattern = re.compile(r"^\[llm\]\s*\n(?:(?!^\[).*\n?)*", re.MULTILINE)
        if pattern.search(original):
            updated = pattern.sub(new_block, original, count=1)
        else:
            updated = new_block + "\n" + original
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        updated = new_block

    config_path.write_text(updated)

    # Sofort im laufenden Prozess übernehmen, ohne Neustart der App.
    if config is not None:
        config.update_llm_settings("default", LLMSettings(**settings))


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

AGENT_TYPES = (
    {
        "GeneralAgent": {
            "name": "General Agent",
            "description": "Allzweck-Agent für verschiedene Aufgaben (Manus)",
            "tools": [
                "python_execute",
                "browser_use",
                "str_replace_editor",
                "ask_human",
                "terminate",
            ],
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
            "tools": [
                "python_execute",
                "visualization_preparation",
                "data_visualization",
                "terminate",
            ],
            "agent_class": DataAnalysis,
        },
        "BrowserAgent": {
            "name": "Browser Agent",
            "description": "Automatisiert Web-Interaktionen",
            "tools": ["browser_use", "terminate"],
            "agent_class": BrowserAgent,
        },
    }
    if AGENT_FRAMEWORK_ERROR is None
    else {}
)


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
                    steps.append(
                        {
                            "step": len(steps) + 1,
                            "type": "tool_call",
                            "tool": call.function.name,
                            "content": f"Argumente: {call.function.arguments}",
                            "result": None,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
            if msg.content:
                steps.append(
                    {
                        "step": len(steps) + 1,
                        "type": "thinking",
                        "content": msg.content,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        elif msg.role == "tool":
            for step in reversed(steps):
                if (
                    step["type"] == "tool_call"
                    and step["tool"] == msg.name
                    and step["result"] is None
                ):
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
        st.caption(
            f"Provider: {default_llm.api_type or 'openai-kompatibel'} | Max Tokens: {default_llm.max_tokens}"
        )
    else:
        st.caption("Kein Modell konfiguriert.")

    with st.expander(
        "🔑 LLM verbinden" if not LLM_CONFIGURED else "🔑 LLM-Zugang bearbeiten",
        expanded=not LLM_CONFIGURED,
    ):
        current = config.llm.get("default") if LLM_CONFIGURED else None
        provider_names = list(LLM_PROVIDER_PRESETS.keys())
        default_provider_index = 0
        if current is not None:
            for idx, preset in enumerate(LLM_PROVIDER_PRESETS.values()):
                if preset["api_type"] == current.api_type:
                    default_provider_index = idx
                    break

        with st.form("llm_connect_form", clear_on_submit=False):
            provider = st.selectbox(
                "Anbieter",
                options=provider_names,
                index=default_provider_index,
                help="Voreinstellungen für Modell und Endpunkt-URL je Anbieter.",
            )
            preset = LLM_PROVIDER_PRESETS[provider]

            model = st.text_input(
                "Modell",
                value=current.model if current else preset["model"],
                placeholder="z. B. claude-3-7-sonnet-20250219",
            )
            base_url = st.text_input(
                "Base URL",
                value=current.base_url if current else preset["base_url"],
                placeholder="z. B. https://api.anthropic.com/v1/",
            )
            api_key = st.text_input(
                "API-Key",
                value="",
                type="password",
                placeholder="sk-..."
                if not current
                else "Leer lassen, um den bestehenden Key zu behalten",
            )
            col_a, col_b = st.columns(2)
            with col_a:
                llm_max_tokens = st.number_input(
                    "Max Tokens",
                    min_value=1,
                    value=current.max_tokens if current else 8192,
                    step=256,
                )
            with col_b:
                llm_temperature = st.number_input(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    value=current.temperature if current else 0.0,
                    step=0.1,
                )
            api_version = ""
            if preset["api_type"] == "azure":
                api_version = st.text_input(
                    "API-Version (Azure)",
                    value=current.api_version if current else "2024-08-01-preview",
                )

            save_llm = st.form_submit_button(
                "💾 Speichern & verbinden", use_container_width=True
            )

        if save_llm:
            resolved_api_key = api_key.strip() or (current.api_key if current else "")
            if not model.strip() or not base_url.strip() or not resolved_api_key:
                st.error(
                    "Bitte Modell, Base URL und API-Key ausfüllen, um das LLM zu verbinden."
                )
            else:
                _save_llm_settings(
                    {
                        "model": model.strip(),
                        "base_url": base_url.strip(),
                        "api_key": resolved_api_key,
                        "max_tokens": int(llm_max_tokens),
                        "temperature": float(llm_temperature),
                        "api_type": preset["api_type"],
                        "api_version": api_version,
                    }
                )
                st.success("LLM-Zugang gespeichert. Die App wird neu geladen …")
                st.rerun()

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

    st.markdown("### 🌐 Browser-Engine")
    configured_engine = "chromium"
    if config is not None and config.browser_config is not None:
        configured_engine = config.browser_config.engine or "chromium"
    engine_options = list(SUPPORTED_ENGINES)
    selected_engine = st.selectbox(
        "Engine",
        options=engine_options,
        index=engine_options.index(configured_engine)
        if configured_engine in engine_options
        else 0,
        format_func=lambda x: ENGINE_LABELS.get(x, x),
        help="browser-use 0.1.x nutzt Playwright-Chromium. Chrome/Edge hängen sich an ein System-Binary.",
    )
    os.environ["BROWSER_ENGINE"] = selected_engine
    headless_ui = st.checkbox(
        "Headless",
        value=True
        if not os.environ.get("DISPLAY")
        else bool(
            config.browser_config.headless
            if config is not None and config.browser_config
            else False
        ),
        help="Ohne DISPLAY (Docker/Server) immer Headless.",
    )
    os.environ["BROWSER_HEADLESS"] = "true" if headless_ui else "false"
    st.caption(
        "Firefox/WebKit: nicht unterstützt. Remote: BROWSER_CDP_URL / BROWSER_WSS_URL."
    )

    st.divider()

    st.markdown("### 🔒 Sandbox")
    sandbox_config = config.sandbox if config is not None else None
    if sandbox_config is not None:
        st.caption(
            "✅ Aktiv"
            if sandbox_config.use_sandbox
            else "❌ Inaktiv (Tools laufen direkt im Container)"
        )
        if sandbox_config.use_sandbox:
            st.caption(f"🐳 Docker-Container: {sandbox_config.image}")
            st.caption(f"💾 Memory-Limit: {sandbox_config.memory_limit}")
            st.caption(f"⏱️ Timeout: {sandbox_config.timeout}s")

    st.divider()

    st.markdown("### 🌐 MCP-Server")
    mcp_servers = config.mcp_config.servers if config is not None else {}
    if mcp_servers:
        for server_id, server_cfg in mcp_servers.items():
            st.caption(
                f"🔗 {server_id}: {server_cfg.type} ({server_cfg.url or server_cfg.command})"
            )
    else:
        st.caption("Keine MCP-Server in config/mcp.json konfiguriert.")

# ── Hauptbereich ──────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🚀 Task ausführen",
        "📋 Ergebnisse",
        "📜 Verlauf",
        "🌐 Browser",
        "⚙️ System-Info",
    ]
)

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
            st.error(
                f"❌ Agent-Ausführung fehlgeschlagen: {st.session_state.agent_error}"
            )
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
                with st.expander(
                    f"💭 Schritt {step['step']}: Denkprozess", expanded=False
                ):
                    st.text(step["content"])
            elif step["type"] == "tool_call":
                with st.expander(
                    f"🔧 Schritt {step['step']}: {step['tool']}", expanded=False
                ):
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
        meta_df = pd.DataFrame(
            [
                {
                    "Metrik": "Agent-Typ",
                    "Wert": AGENT_TYPES[st.session_state.agent_type]["name"],
                },
                {
                    "Metrik": "Modell",
                    "Wert": config.llm["default"].model if LLM_CONFIGURED else "N/A",
                },
                {
                    "Metrik": "Schritte",
                    "Wert": len(steps),
                },
                {
                    "Metrik": "Tool-Aufrufe",
                    "Wert": sum(1 for s in steps if s["type"] == "tool_call"),
                },
                {
                    "Metrik": "Sandbox",
                    "Wert": "Aktiv" if config.sandbox.use_sandbox else "Inaktiv",
                },
            ]
        )
        st.dataframe(meta_df, use_container_width=True, hide_index=True)
    elif st.session_state.get("agent_error"):
        st.error(f"❌ Letzter Lauf fehlgeschlagen: {st.session_state.agent_error}")
    else:
        st.info(
            "Führen Sie zuerst einen Task aus (Tab 1). Es werden ausschließlich echte Ausführungsergebnisse angezeigt."
        )

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

        if (
            not st.session_state.task_history
            or st.session_state.task_history[0]["task"] != current_entry["task"]
        ):
            st.session_state.task_history.insert(0, current_entry)

    if st.session_state.task_history:
        df_history = pd.DataFrame(st.session_state.task_history)
        st.dataframe(df_history, use_container_width=True, hide_index=True)

        if st.button("🗑️ Verlauf löschen"):
            st.session_state.task_history = []
            st.rerun()
    else:
        st.info("Noch keine Tasks im Verlauf.")

# ── Tab 4: Browser-Engines ────────────────────────────────────

with tab4:
    st.markdown("### 🌐 Unterstützte Browser-Engines")
    st.markdown(
        "Open Manus steuert den Browser über **browser-use 0.1.x** (Playwright). "
        "Wählbar sind Chromium, Google Chrome und Microsoft Edge. "
        "Firefox und WebKit sind in dieser Version nicht angebunden."
    )
    chrome_path = None
    if config is not None and config.browser_config is not None:
        chrome_path = config.browser_config.chrome_instance_path
    engines_df = pd.DataFrame(
        [
            {
                "Engine": info.id,
                "Name": info.label,
                "Unterstützt": "Ja" if info.supported else "Nein",
                "Status": info.notes,
                "Binary": info.binary_path or "—",
            }
            for info in describe_engines(chrome_path)
        ]
    )
    st.dataframe(engines_df, use_container_width=True, hide_index=True)

    st.markdown("#### Aktive Auswahl")
    st.json(
        {
            "engine": selected_engine,
            "headless": headless_ui,
            "cdp_url": os.environ.get("BROWSER_CDP_URL")
            or (
                config.browser_config.cdp_url
                if config is not None and config.browser_config
                else None
            ),
            "wss_url": os.environ.get("BROWSER_WSS_URL")
            or (
                config.browser_config.wss_url
                if config is not None and config.browser_config
                else None
            ),
        }
    )

    st.caption(
        "Env-Overrides: `BROWSER_ENGINE`, `BROWSER_HEADLESS`, `CHROME_INSTANCE_PATH`, "
        "`BROWSER_CDP_URL`, `BROWSER_WSS_URL`."
    )

# ── Tab 5: System-Info ────────────────────────────────────────

with tab5:
    st.markdown("### ⚙️ System-Informationen")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🤖 Agent-Konfiguration")
        st.json(
            {
                "agent_type": agent_type,
                "agent_name": AGENT_TYPES[agent_type]["name"],
                "tools": AGENT_TYPES[agent_type]["tools"],
                "model": config.llm["default"].model if LLM_CONFIGURED else None,
                "model_configured": LLM_CONFIGURED,
                "temperature": temperature,
                "max_steps": max_steps,
            }
        )

    with col2:
        st.markdown("#### 🔒 Sandbox-Status")
        st.json(
            {
                "sandbox_enabled": config.sandbox.use_sandbox,
                "image": config.sandbox.image,
                "memory_limit": config.sandbox.memory_limit,
                "cpu_limit": config.sandbox.cpu_limit,
                "timeout": config.sandbox.timeout,
            }
        )

    st.divider()

    st.markdown("#### 🌐 MCP-Server")
    st.json(
        {
            "servers": {
                server_id: {"type": cfg.type, "endpoint": cfg.url or cfg.command}
                for server_id, cfg in config.mcp_config.servers.items()
            }
        }
    )

    st.divider()

    st.markdown("#### 📦 Verfügbare Agent-Typen")
    agents_df = pd.DataFrame(
        [
            {
                "Agent": info["name"],
                "Beschreibung": info["description"],
                "Tools": ", ".join(info["tools"]),
            }
            for key, info in AGENT_TYPES.items()
        ]
    )
    st.dataframe(agents_df, use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────

st.divider()
st.caption(
    f"🤖 Open Manus v1.0 | Agent Framework | {datetime.now().strftime('%d.%m.%Y %H:%M')}"
)
