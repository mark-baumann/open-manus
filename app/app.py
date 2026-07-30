"""
Open Manus — Streamlit App
===========================
Web-Oberfläche für Agent-Konfiguration, Task-Ausführung und Ergebnisanzeige.
"""

import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional

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
# Agent-Simulator
# ──────────────────────────────────────────────────────────────

AGENT_TYPES = {
    "GeneralAgent": {
        "name": "General Agent",
        "description": "Allzweck-Agent für verschiedene Aufgaben",
        "tools": ["web_search", "python_execute", "browser", "file_ops"],
    },
    "CodeAgent": {
        "name": "Code Agent",
        "description": "Spezialisiert auf Programmierung & Code-Generierung",
        "tools": ["python_execute", "str_replace_editor", "create_chat_completion"],
    },
    "DataAnalysisAgent": {
        "name": "Datenanalyse-Agent",
        "description": "Analysiert Daten und erstellt Visualisierungen",
        "tools": ["python_execute", "web_search", "browser"],
    },
    "BrowserAgent": {
        "name": "Browser Agent",
        "description": "Automatisiert Web-Interaktionen",
        "tools": ["browser", "web_search"],
    },
}

LLM_MODELS = {
    "GPT-4o": {"provider": "OpenAI", "max_tokens": 4096},
    "GPT-4o-mini": {"provider": "OpenAI", "max_tokens": 4096},
    "Claude 3.5 Sonnet": {"provider": "Anthropic", "max_tokens": 4096},
    "Claude 3 Opus": {"provider": "Anthropic", "max_tokens": 4096},
    "Gemini 1.5 Pro": {"provider": "Google", "max_tokens": 8192},
    "Llama 3.1 70B": {"provider": "Ollama", "max_tokens": 4096},
}


def simulate_agent_execution(task: str, agent_type: str, model: str, max_steps: int) -> List[dict]:
    """Simuliert die Agent-Ausführung mit realistischen Schritten."""
    steps = []
    agent_info = AGENT_TYPES[agent_type]
    tools = agent_info["tools"]
    
    # Schritt 1: Planung
    steps.append({
        "step": 1,
        "type": "thinking",
        "content": f"Analysiere Aufgabe: '{task}'\nIdentifiziere benötigte Tools: {', '.join(tools)}",
        "timestamp": datetime.now().isoformat(),
    })
    
    # Schritt 2: Tool-Aufrufe
    for i, tool in enumerate(tools[:min(len(tools), max_steps - 2)]):
        steps.append({
            "step": i + 2,
            "type": "tool_call",
            "tool": tool,
            "content": f"Rufe Tool '{tool}' auf...",
            "result": f"Ergebnis von {tool}: Erfolgreich ausgeführt.",
            "timestamp": datetime.now().isoformat(),
        })
    
    # Letzter Schritt: Zusammenfassung
    steps.append({
        "step": len(steps) + 1,
        "type": "response",
        "content": f"Aufgabe abgeschlossen: '{task}'\n\n"
                  f"📊 Zusammenfassung:\n"
                  f"- Agent-Typ: {agent_info['name']}\n"
                  f"- Modell: {model}\n"
                  f"- Verwendete Tools: {len(tools)}\n"
                  f"- Schritte: {len(steps) + 1}\n\n"
                  f"✅ Alle Operationen erfolgreich durchgeführt.",
        "timestamp": datetime.now().isoformat(),
    })
    
    return steps


# ──────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────

st.title("🤖 Open Manus")
st.markdown("**Agent-Konfiguration & Task-Ausführung — Open Manus Web UI**")

# ── Seitenleiste ──────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Agent-Konfiguration")
    
    agent_type = st.selectbox(
        "Agent-Typ",
        options=list(AGENT_TYPES.keys()),
        format_func=lambda x: AGENT_TYPES[x]["name"],
        help="Wählen Sie den Agent-Typ für Ihre Aufgabe.",
    )
    
    # Agent-Info
    agent_info = AGENT_TYPES[agent_type]
    st.caption(f"📝 {agent_info['description']}")
    st.caption(f"🔧 Tools: {', '.join(agent_info['tools'])}")
    
    st.divider()
    
    st.markdown("### 🧠 LLM-Einstellungen")
    
    model = st.selectbox(
        "Modell",
        options=list(LLM_MODELS.keys()),
        index=0,
    )
    
    model_info = LLM_MODELS[model]
    st.caption(f"Provider: {model_info['provider']} | Max Tokens: {model_info['max_tokens']}")
    
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=0.7,
        step=0.1,
    )
    
    max_steps = st.slider(
        "Maximale Schritte",
        min_value=1,
        max_value=20,
        value=5,
        help="Maximale Anzahl an Agent-Schritten pro Task.",
    )
    
    st.divider()
    
    st.markdown("### 🔒 Sandbox")
    use_sandbox = st.checkbox("Sandbox aktivieren", value=True)
    if use_sandbox:
        st.caption("✅ Ausführung in isolierter Umgebung")
        st.caption("🐳 Docker-Container: python:3.12-slim")
        st.caption("💾 Memory-Limit: 512 MB")
        st.caption("⏱️ Timeout: 300s")
    
    st.divider()
    
    st.markdown("### 🌐 MCP-Server")
    mcp_enabled = st.checkbox("MCP-Server verbinden", value=False)
    if mcp_enabled:
        mcp_url = st.text_input("MCP-Server URL", value="http://localhost:8000")

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
        st.session_state.agent_model = model
        
        # Fortschrittsbalken
        progress_bar = st.progress(0, text="Initialisiere Agent...")
        status_text = st.empty()
        
        # Simulation der Ausführung
        steps = simulate_agent_execution(task, agent_type, model, max_steps)
        
        for i, step in enumerate(steps):
            progress = (i + 1) / len(steps)
            progress_bar.progress(progress, text=f"Schritt {step['step']}/{len(steps)}: {step['type']}")
            
            if step["type"] == "tool_call":
                status_text.info(f"🔧 {step['tool']}: {step['result']}")
            elif step["type"] == "thinking":
                status_text.info(f"💭 Denke nach...")
            
            time.sleep(0.3)
        
        progress_bar.progress(1.0, text="✅ Abgeschlossen")
        status_text.success("Agent-Ausführung erfolgreich beendet!")
        
        st.session_state.agent_steps = steps
        st.session_state.agent_result = steps[-1]["content"]
        
        st.balloons()
    
    elif execute_button:
        st.warning("Bitte geben Sie eine Aufgabe ein.")

# ── Tab 2: Ergebnisse ─────────────────────────────────────────

with tab2:
    if "agent_steps" in st.session_state and st.session_state.agent_steps:
        steps = st.session_state.agent_steps
        
        st.markdown("### 📋 Ausführungsergebnis")
        
        # Zusammenfassung
        st.success(st.session_state.agent_result)
        
        st.divider()
        
        # Schritt-für-Schritt
        st.markdown("### 🔍 Ausführungsschritte")
        
        for step in steps:
            if step["type"] == "thinking":
                with st.expander(f"💭 Schritt {step['step']}: Planung", expanded=False):
                    st.text(step["content"])
            elif step["type"] == "tool_call":
                with st.expander(f"🔧 Schritt {step['step']}: {step['tool']}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Aufruf:**")
                        st.code(step["content"], language="text")
                    with col2:
                        st.markdown("**Ergebnis:**")
                        st.success(step["result"])
            elif step["type"] == "response":
                with st.expander(f"✅ Schritt {step['step']}: Antwort", expanded=True):
                    st.markdown(step["content"])
        
        # Metadaten
        st.divider()
        st.markdown("### 📊 Ausführungs-Metadaten")
        meta_df = pd.DataFrame([{
            "Metrik": "Agent-Typ",
            "Wert": AGENT_TYPES[st.session_state.agent_type]["name"],
        }, {
            "Metrik": "Modell",
            "Wert": st.session_state.agent_model,
        }, {
            "Metrik": "Schritte",
            "Wert": len(steps),
        }, {
            "Metrik": "Tool-Aufrufe",
            "Wert": sum(1 for s in steps if s["type"] == "tool_call"),
        }, {
            "Metrik": "Sandbox",
            "Wert": "Aktiv" if use_sandbox else "Inaktiv",
        }])
        st.dataframe(meta_df, use_container_width=True, hide_index=True)
    else:
        st.info("Führen Sie zuerst einen Task aus (Tab 1).")
        
        st.markdown("### 💡 Beispiel-Ergebnis")
        st.markdown("""
        ```
        ✅ Aufgabe abgeschlossen: 'Analysiere die aktuellen Top-5 Python-Bibliotheken'
        
        📊 Zusammenfassung:
        - Agent-Typ: General Agent
        - Modell: GPT-4o
        - Verwendete Tools: 4
        - Schritte: 6
        
        ✅ Alle Operationen erfolgreich durchgeführt.
        ```
        """)

# ── Tab 3: Verlauf ───────────────────────────────────────────

with tab3:
    st.markdown("### 📜 Task-Verlauf")
    
    if "task_history" not in st.session_state:
        st.session_state.task_history = []
    
    if "agent_task" in st.session_state and "agent_steps" in st.session_state:
        current_entry = {
            "task": st.session_state.agent_task,
            "agent_type": AGENT_TYPES[st.session_state.agent_type]["name"],
            "model": st.session_state.agent_model,
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
            "model": model,
            "model_provider": LLM_MODELS[model]["provider"],
            "max_tokens": LLM_MODELS[model]["max_tokens"],
            "temperature": temperature,
            "max_steps": max_steps,
        })
    
    with col2:
        st.markdown("#### 🔒 Sandbox-Status")
        st.json({
            "sandbox_enabled": use_sandbox,
            "image": "python:3.12-slim" if use_sandbox else "N/A",
            "memory_limit": "512m" if use_sandbox else "N/A",
            "cpu_limit": 1.0 if use_sandbox else "N/A",
            "timeout": 300 if use_sandbox else "N/A",
            "network_enabled": False,
        })
    
    st.divider()
    
    st.markdown("#### 🌐 MCP-Server")
    st.json({
        "mcp_enabled": mcp_enabled,
        "server_url": mcp_url if mcp_enabled else "N/A",
        "type": "sse" if mcp_enabled else "N/A",
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
