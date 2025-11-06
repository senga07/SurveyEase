#!/bin/bash

# SurveyEase Uvicorn 启动脚本（支持热重载）
# 使用方法: ./start_uvicorn.sh [local|test|prod]

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
echo "启动 SurveyEase Backend (Uvicorn)"
echo "环境: $ENV"
echo "========================================="

# 设置环境变量
export ENV=$ENV

# 检查 uvicorn 是否安装
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "错误: 未找到 uvicorn，请先安装依赖"
    exit 1
fi

# 启动应用（开发模式，支持热重载）
# 注意：环境变量 ENV 已在上面的 export 中设置，main.py 会读取该变量
if [ "$ENV" == "local" ]; then
    echo "开发模式: 启用热重载"
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "生产模式: 禁用热重载"
    uvicorn main:app --host 0.0.0.0 --port 8000
fi

