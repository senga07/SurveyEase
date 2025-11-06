#!/bin/bash

# SurveyEase 启动脚本
# 使用方法: ./start.sh [local|test|prod]

set -e

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# 切换到项目目录
cd "$PROJECT_DIR"

# 获取环境参数，默认为 local
ENV=${1:-local}

# 验证环境参数
if [[ ! "$ENV" =~ ^(local|test|prod)$ ]]; then
    echo "错误: 无效的环境参数 '$ENV'"
    echo "使用方法: $0 [local|test|prod]"
    exit 1
fi

echo "========================================="
echo "启动 SurveyEase Backend"
echo "环境: $ENV"
echo "========================================="

# 设置环境变量
export ENV=$ENV

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo "错误: 未找到 Python，请先安装 Python"
    exit 1
fi

# 检查依赖
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "警告: 未找到虚拟环境，建议使用虚拟环境运行"
fi

# 启动应用
echo "正在启动应用..."
python main.py --env "$ENV"

