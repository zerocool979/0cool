#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
#  NmapSLM — Unified startup script
#  Usage: ./start.sh [--backend-only | --frontend-only]
# ──────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/.pids"

mkdir -p "$LOG_DIR"

# ── Colors ────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*"; }

banner() {
  echo -e "\n${BOLD}${CYAN}"
  echo "  ███╗   ██╗███╗   ███╗ █████╗ ██████╗     ███████╗██╗     ███╗   ███╗"
  echo "  ████╗  ██║████╗ ████║██╔══██╗██╔══██╗    ██╔════╝██║     ████╗ ████║"
  echo "  ██╔██╗ ██║██╔████╔██║███████║██████╔╝    ███████╗██║     ██╔████╔██║"
  echo "  ██║╚██╗██║██║╚██╔╝██║██╔══██║██╔═══╝     ╚════██║██║     ██║╚██╔╝██║"
  echo "  ██║ ╚████║██║ ╚═╝ ██║██║  ██║██║         ███████║███████╗██║ ╚═╝ ██║"
  echo "  ╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝         ╚══════╝╚══════╝╚═╝     ╚═╝"
  echo -e "${RESET}"
  echo -e "  ${BOLD}Network Scanner + AI  |  v1.0.0  |  100% Offline${RESET}\n"
}

# ── Dependency checks ─────────────────────────────────────
check_deps() {
  info "Memeriksa dependensi…"

  command -v python3 >/dev/null || { error "Python 3 tidak ditemukan"; exit 1; }
  command -v node    >/dev/null || { error "Node.js tidak ditemukan";  exit 1; }
  command -v npm     >/dev/null || { error "npm tidak ditemukan";       exit 1; }

  if command -v nmap >/dev/null; then
    success "Nmap: $(nmap --version | head -1)"
  else
    warn "Nmap tidak ditemukan. Install: sudo apt install nmap"
  fi

  if command -v ollama >/dev/null; then
    success "Ollama: $(ollama --version 2>/dev/null || echo 'installed')"
  else
    warn "Ollama tidak ditemukan. Download: https://ollama.ai"
  fi
}

# ── Backend setup ─────────────────────────────────────────
setup_backend() {
  info "Menyiapkan backend…"
  cd "$BACKEND_DIR"

  if [ ! -d ".venv" ]; then
    info "Membuat virtual environment…"
    python3 -m venv .venv
  fi

  source .venv/bin/activate
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  success "Backend dependencies terpasang"
}

# ── Frontend setup ────────────────────────────────────────
setup_frontend() {
  info "Menyiapkan frontend…"
  cd "$FRONTEND_DIR"

  if [ ! -d "node_modules" ]; then
    info "Menginstall npm packages…"
    npm install --legacy-peer-deps
  fi
  success "Frontend dependencies terpasang"
}

# ── Start backend ─────────────────────────────────────────
start_backend() {
  info "Menjalankan FastAPI backend (port 8000)…"
  cd "$BACKEND_DIR"
  source .venv/bin/activate

  uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info \
    > "$LOG_DIR/backend.log" 2>&1 &

  echo $! >> "$PID_FILE"
  success "Backend berjalan → http://localhost:8000"
  success "API Docs        → http://localhost:8000/docs"
}

# ── Start frontend ────────────────────────────────────────
start_frontend() {
  info "Menjalankan Next.js frontend (port 3000)…"
  cd "$FRONTEND_DIR"

  npm run dev \
    > "$LOG_DIR/frontend.log" 2>&1 &

  echo $! >> "$PID_FILE"
  success "Frontend berjalan → http://localhost:3000"
}

# ── Ollama model check ────────────────────────────────────
check_ollama_model() {
  local MODEL="${OLLAMA_MODEL:-qwen2.5:1.5b}"
  if command -v ollama >/dev/null; then
    if ! ollama list 2>/dev/null | grep -q "$MODEL"; then
      warn "Model '$MODEL' belum ada."
      echo -e "  Jalankan: ${CYAN}ollama pull $MODEL${RESET}"
      echo -e "  Atau untuk model khusus: ${CYAN}ollama pull qwen2.5:7b${RESET}"
    else
      success "Model '$MODEL' tersedia"
    fi
  fi
}

# ── Stop all ──────────────────────────────────────────────
stop_all() {
  if [ -f "$PID_FILE" ]; then
    info "Menghentikan proses…"
    while read -r pid; do
      kill "$pid" 2>/dev/null && info "Proses $pid dihentikan"
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
}

# ── Trap cleanup ──────────────────────────────────────────
trap stop_all EXIT INT TERM

# ── Main ──────────────────────────────────────────────────
banner
rm -f "$PID_FILE"

case "${1:-all}" in
  --backend-only)
    check_deps
    setup_backend
    check_ollama_model
    start_backend
    info "Tekan Ctrl+C untuk berhenti"
    tail -f "$LOG_DIR/backend.log"
    ;;
  --frontend-only)
    check_deps
    setup_frontend
    start_frontend
    info "Tekan Ctrl+C untuk berhenti"
    tail -f "$LOG_DIR/frontend.log"
    ;;
  *)
    check_deps
    setup_backend
    setup_frontend
    check_ollama_model
    start_backend
    sleep 2  # wait for backend to be ready
    start_frontend

    echo ""
    echo -e "${BOLD}${GREEN}✔ NmapSLM berjalan!${RESET}"
    echo -e "  ${BOLD}Dashboard${RESET}  → ${CYAN}http://localhost:3000${RESET}"
    echo -e "  ${BOLD}API Docs${RESET}   → ${CYAN}http://localhost:8000/docs${RESET}"
    echo -e "  ${BOLD}Logs${RESET}       → ${CYAN}$LOG_DIR/${RESET}"
    echo ""
    echo -e "  Tekan ${BOLD}Ctrl+C${RESET} untuk menghentikan semua layanan\n"

    # Follow both logs
    tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
    ;;
esac
