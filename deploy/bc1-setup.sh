#!/bin/bash
# 北辰一号部署设置脚本 — SSH 进 bc-1 后运行
# Usage: bash deploy/bc1-setup.sh

set -e
BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)/src/backend"
SERVICE_NAME="backend-18999"

install_deps() {
    echo ">>> Installing Python 3.11 dependencies..."
    cd "$BACKEND_DIR"
    python3.11 -m venv .venv --clear
    .venv/bin/pip install --quiet fastapi uvicorn[standard] bcrypt pydantic
    .venv/bin/pip install pillow
    echo "Dependencies installed."
}

install_service() {
    echo ">>> Installing systemd user service..."
    mkdir -p ~/.config/systemd/user/
    cat > ~/.config/systemd/user/${SERVICE_NAME}.service << SRV
[Unit]
Description=Tiny Chat Backend (FastAPI :18999)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${BACKEND_DIR}
ExecStart=${BACKEND_DIR}/.venv/bin/python main.py
Restart=on-failure
RestartSec=5
Environment=SMTP_HOST=smtp.feishu.cn
Environment=SMTP_PORT=465
Environment=SMTP_USER=anonymous@becharmkon.cn

[Install]
WantedBy=default.target
SRV
    systemctl --user daemon-reload
    systemctl --user enable --now ${SERVICE_NAME}.service
    echo "Service started."
    sleep 2
    systemctl --user status ${SERVICE_NAME}.service --no-pager -n 5
}

test_proxy() {
    echo ">>> Testing reverse proxy..."
    sleep 1
    curl -s http://127.0.0.1:18999/ | head -5
    echo ""
    echo "You can also test via: curl http://api.becharmkon.cn/"
}

case "${1:-}" in
    deps) install_deps ;;
    service) install_service ;;
    test) test_proxy ;;
    *)
        install_deps
        install_service
        test_proxy
        ;;
esac
