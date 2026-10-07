#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
  echo "Run as the normal Vicky user; sudo is used only to install systemd files."
  exit 1
fi

RUN_USER="$(id -un)"
USER_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
LLAMA_SERVER="${VICKY_LLAMA_SERVER:-$USER_HOME/llama.cpp/build/bin/llama-server}"
MODEL_PATH="${VICKY_AI_MODEL_PATH:-$USER_HOME/models/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
MODEL_ALIAS="${VICKY_AI_IMPORTANCE_MODEL:-local-model}"
MODEL_TIMEOUT="${VICKY_AI_IMPORTANCE_TIMEOUT:-60}"

[[ -x "$LLAMA_SERVER" ]] || {
  echo "Missing executable llama-server: $LLAMA_SERVER"
  exit 1
}
[[ -r "$MODEL_PATH" ]] || {
  echo "Missing readable GGUF model: $MODEL_PATH"
  exit 1
}

unit_file="$(mktemp)"
dropin_file="$(mktemp)"
trap 'rm -f "$unit_file" "$dropin_file"' EXIT

cat >"$unit_file" <<EOF
[Unit]
Description=Vicky local AI importance sorter
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
Group=$(id -gn)
WorkingDirectory=$USER_HOME/llama.cpp
ExecStart=$LLAMA_SERVER --model $MODEL_PATH --alias $MODEL_ALIAS --host 127.0.0.1 --port 8080 --ctx-size 2048 --threads 4 --parallel 1
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

cat >"$dropin_file" <<EOF
[Unit]
Wants=vicky-llama-sorter.service
After=vicky-llama-sorter.service

[Service]
Environment=VICKY_AI_IMPORTANCE_SORT=1
Environment=VICKY_AI_IMPORTANCE_URL=http://127.0.0.1:8080/v1/chat/completions
Environment=VICKY_AI_IMPORTANCE_MODEL=$MODEL_ALIAS
Environment=VICKY_AI_IMPORTANCE_TIMEOUT=$MODEL_TIMEOUT
EOF

sudo install -m 0644 "$unit_file" /etc/systemd/system/vicky-llama-sorter.service
sudo install -d -m 0755 /etc/systemd/system/awtrix-news.service.d
sudo install -m 0644 "$dropin_file" \
  /etc/systemd/system/awtrix-news.service.d/ai-importance.conf
sudo systemctl daemon-reload

echo "Local AI sorter service and awtrix-news integration installed but not started."
echo "Start and verify:"
echo "  sudo systemctl enable --now vicky-llama-sorter.service"
echo "  curl -fsS http://127.0.0.1:8080/health"
echo "  sudo systemctl restart awtrix-news.service"
