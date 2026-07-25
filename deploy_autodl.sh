#!/bin/bash
# AutoDL 部署脚本 - Multi-Agent System Builder
# 用法: bash deploy_autodl.sh
set -e

echo "=========================================="
echo " Multi-Agent System Builder - AutoDL 部署"
echo "=========================================="

# 1. 环境检查
echo ""
echo "[1/6] 检查环境..."
python3 --version
nvidia-smi 2>/dev/null || echo "WARNING: nvidia-smi 未找到，请确认 GPU 驱动已安装"

# 2. 安装基础依赖
echo ""
echo "[2/6] 安装基础依赖..."
pip install -r requirements.txt --quiet

# 3. 安装训练框架
echo ""
echo "[3/6] 安装训练框架..."
pip install ms-swift --quiet
echo "ms-swift 安装完成"

# verl 是可选的，安装可能耗时较长
pip install verl 2>/dev/null && echo "verl 安装完成" || echo "WARNING: verl 安装失败，GRPO 训练将不可用（不影响 SFT/DPO）"

# 4. 设置环境变量
echo ""
echo "[4/6] 设置环境变量..."
if [ -f .env ]; then
    echo "从 .env 文件加载环境变量"
    export $(grep -v '^#' .env | xargs)
else
    echo "WARNING: .env 文件不存在，请手动设置 OPENAI_API_KEY"
fi

# 5. 创建必要目录
echo ""
echo "[5/6] 创建目录结构..."
mkdir -p training_outputs/sft
mkdir -p training_outputs/dpo
mkdir -p training_outputs/grpo
mkdir -p evaluation_outputs
mkdir -p data/rollouts

# 6. 启动服务器
echo ""
echo "[6/6] 启动 FastAPI 服务器..."
echo "服务器地址: http://0.0.0.0:8000"
echo "前端地址:   http://0.0.0.0:8000/app"
echo "API 文档:   http://0.0.0.0:8000/docs"
echo ""
echo "默认登录账号: admin / admin123"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

python main_api.py
