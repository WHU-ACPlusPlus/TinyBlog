#!/bin/bash
# 北辰一号部署 — 先同步代码，再走 uv sync
# 首次部署需要手动安装 uv 和创建 systemd drop-in，之后只需：
#   git pull && uv sync --no-dev && sudo systemctl restart backend-18999

set -e
BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)/src/backend"

echo ">>> Syncing code..."
cd "$(dirname "$0")/.."
git pull

echo ">>> Syncing Python dependencies via uv..."
cd "$BACKEND_DIR"
uv sync --no-dev

echo ">>> Restarting service..."
sudo systemctl restart backend-18999.service

echo ">>> Done."
sleep 1
sudo systemctl status backend-18999.service --no-pager -n 3
