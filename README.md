# 🤖 Open Manus

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)](https://streamlit.io/)

**Open-Source Agent Framework** — Multi-Agent-System mit Tool-Use, Sandbox-Execution und A2A-Protokoll.

## 📋 Beschreibung

Open Manus ist ein modulares, erweiterbares Agent-Framework für die Entwicklung und Orchestrierung von KI-Agenten. Es bietet vordefinierte Agent-Typen (General, Code, Data Analysis, Browser), eine umfangreiche Tool-Sammlung, Sandbox-Execution und Unterstützung für das Agent-to-Agent (A2A) Protokoll.

- **Multi-Agent-System** — GeneralAgent, CodeAgent, DataAnalysisAgent, BrowserAgent
- **Tool-Collection** — Web Search, Python Execute, Browser, File Operations, StrReplaceEditor
- **Sandbox-Execution** — Docker-basierte isolierte Code-Ausführung
- **A2A-Protokoll** — Agent-to-Agent-Kommunikation

## ✨ Features

- 🤖 **Vier Agent-Typen** — General, Code, Data Analysis, Browser
- 🛠️ **Umfangreiche Tools** — Web Search (Google, Bing, DuckDuckGo, Baidu), Python Execute, Browser, File Ops
- 📦 **Sandbox** — Docker-basierte isolierte Ausführungsumgebung
- 🔗 **A2A-Protokoll** — Agent-to-Agent-Kommunikation für Multi-Agent-Workflows
- 🎨 **Chart-Visualisierung** — Integrierte Diagramm-Tools
- 📋 **Handbook-Compliance** — Regelbasierte Agent-Validierung
- 🖥️ **Streamlit-App** — Interaktive Agent-Konfiguration und Task-Ausführung
- 🧪 **Test-Suite** — pytest-Tests für Tools, Sandbox und Schema

## 🚀 Installation

```bash
# Repository klonen
git clone https://github.com/mark-baumann/open-manus.git
cd open-manus

# Virtuelle Umgebung erstellen
python3 -m venv .venv
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Für Sandbox-Features
docker --version  # Docker muss installiert sein
```

## 🎮 Nutzung

### Streamlit-App

```bash
streamlit run app.py
```

Die App bietet:
- **Agent-Konfiguration** — Agent-Typ, LLM-Modell, Tools auswählen
- **Task-Ausführung** — Tasks an Agenten delegieren und Ergebnisse anzeigen
- **Tool-Explorer** — Verfügbare Tools durchsuchen und testen

### CLI

```bash
# Hauptprogramm
python main.py

# Flow ausführen
python run_flow.py

# MCP-Server starten
python run_mcp.py
python run_mcp_server.py
```

### Tests

```bash
pytest tests/ -v
```

## 🏗️ Tech-Stack

| Komponente | Technologie |
|---|---|
| **Sprache** | Python 3.10+ |
| **LLM** | Multi-Provider (OpenAI, Anthropic, Google, Ollama) |
| **Sandbox** | Docker |
| **Protokoll** | A2A (Agent-to-Agent) |
| **UI** | Streamlit |
| **Testing** | pytest |

## 📁 Projektstruktur

```
open-manus/
├── app.py                      # Streamlit-App
├── main.py                     # Haupt-CLI
├── run_flow.py                 # Flow-Ausführung
├── run_mcp.py                  # MCP-Integration
├── run_mcp_server.py           # MCP-Server
├── sandbox_main.py             # Sandbox-Entrypoint
├── setup.py                    # Package-Setup
├── app/
│   ├── config.py               # Konfiguration
│   ├── schema.py               # Daten-Schema
│   ├── handbook_compliance.py  # Regel-Validierung
│   ├── tool/
│   │   ├── base.py             # Tool-Basisklasse
│   │   ├── tool_collection.py  # Tool-Registry
│   │   ├── terminate.py        # Terminierungs-Tool
│   │   ├── web_search.py       # Web-Suche
│   │   ├── str_replace_editor.py
│   │   ├── search/             # Google, Bing, DuckDuckGo, Baidu
│   │   ├── sandbox/            # Sandbox-Tools
│   │   └── chart_visualization/
│   ├── sandbox/                # Docker-Sandbox
│   ├── daytona/                # Daytona-Integration
│   └── utils/                  # Logger, File-Utils
├── protocol/
│   └── a2a/                    # Agent-to-Agent-Protokoll
├── tests/
│   ├── test_tool_collection.py
│   ├── test_tool_base.py
│   ├── test_schema.py
│   ├── test_handbook_compliance.py
│   └── sandbox/
└── logs/                       # Agent-Logs
```

## 👤 Autor

**Mark Baumann** — [GitHub](https://github.com/mark-baumann)

---

*Für Fragen oder Beiträge: Issue erstellen oder Pull Request öffnen.*
