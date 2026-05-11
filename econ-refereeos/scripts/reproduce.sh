#!/usr/bin/env bash
# EconRefereeOS 一键复现
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== EconRefereeOS 复现脚本 ==="

if [ ! -d ".venv" ]; then
    echo "[1/3] 创建虚拟环境..."
    python3 -m venv .venv
fi

source .venv/bin/activate
echo "[2/3] 安装依赖..."
pip install -q -r requirements.txt

echo "[3/3] 运行 4-agent 审稿流水线..."
python src/orchestrator.py

echo ""
echo "=== 复现完毕 ==="
