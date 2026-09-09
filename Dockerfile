# ═══════════════════════════════════════════════════════════════
# Dockerfile — Standard-Template für alle Streamlit-Apps
# ═══════════════════════════════════════════════════════════════
# Kopiere diese Datei in jedes App-Repo und passe PORT an.

FROM python:3.12-slim

WORKDIR /app

# System-Abhängigkeiten + Chromium-Runtime (kein playwright --with-deps:
# ttf-unifont / ttf-ubuntu-font-family existieren auf Debian Trixie nicht)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-liberation \
    fonts-unifont \
    libnss3 \
    libnspr4 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxshmfence1 \
    && for spec in \
         "libatk1.0-0t64 libatk1.0-0" \
         "libatk-bridge2.0-0t64 libatk-bridge2.0-0" \
         "libatspi2.0-0t64 libatspi2.0-0" \
         "libcups2t64 libcups2" \
         "libasound2t64 libasound2"; do \
         set -- $spec; \
         apt-get install -y --no-install-recommends "$1" \
           || apt-get install -y --no-install-recommends "$2"; \
       done \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Streamlit separat installieren (vermeidet Versions-Konflikte mit gepinnten Deps)
RUN pip install --no-cache-dir "streamlit>=1.28.0"
RUN playwright install chromium
ENV BROWSER_ENGINE=chromium
ENV BROWSER_HEADLESS=true

# App-Code
COPY . .

# Port (pro App anpassen: 8501-8519)
ARG PORT=8516
# ARG allein reicht nicht: CMD/HEALTHCHECK laufen zur Container-Laufzeit,
# nicht beim Build, daher als ENV re-exportieren.
ENV PORT=$PORT
EXPOSE $PORT

# Healthcheck — start-period gibt Streamlit Zeit zum Starten, bevor Checks zählen
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:${PORT}/_stcore/health')"

# Streamlit
CMD streamlit run app/streamlit_app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
