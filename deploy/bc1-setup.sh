#!/bin/bash
# 北辰一号部署设置脚本
# 在 bc-1 上以 becharm 用户运行

set -e

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$BASE_DIR/src/backend"

install_service() {
    echo "=== Installing systemd user service ==="
    mkdir -p ~/.config/systemd/user/
    cat > ~/.config/systemd/user/backend-18999.service << 'EOF'
[Unit]
Description=Tiny Chat Backend (FastAPI :18999)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=BACKEND_DIR_PLACEHOLDER
ExecStart=/usr/bin/uv run python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
    sed -i "s|BACKEND_DIR_PLACEHOLDER|$BACKEND_DIR|" ~/.config/systemd/user/backend-18999.service
    systemctl --user daemon-reload
    systemctl --user enable --now backend-18999.service
    echo "OK - Service started"
}

setup_nginx() {
    echo "=== Setting up nginx reverse proxy ==="
    if [ -f /etc/nginx/sites-enabled/api.becharmkon.cn ]; then
        echo "nginx config exists, reloading..."
        sudo nginx -t && sudo systemctl reload nginx
        return
    fi
    echo "Please create /etc/nginx/sites-enabled/api.becharmkon.cn manually"
}

case "${1:-}" in
    --install-service) install_service ;;
    --setup-nginx) setup_nginx ;;
    --all)
        install_service
        setup_nginx
        ;;
    *)
        echo "Usage: $0 [--install-service|--setup-nginx|--all]"
        ;;
esac
