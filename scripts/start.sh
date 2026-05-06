#!/bin/bash

# ChatBI 启动脚本
# 用于同时启动前端和后端服务

# 检查虚拟环境是否存在
check_venv() {
    VENV_PATH="backend/.venv"
    if [ ! -d "$VENV_PATH" ]; then
        echo "\033[31m错误：虚拟环境不存在！\033[0m"
        echo "请先创建虚拟环境并安装依赖："
        echo "cd backend"
        echo "python3 -m venv .venv"
        echo "source .venv/bin/activate"
        echo "pip install -e ."
        echo ""
        exit 1
    fi
    echo "虚拟环境已找到：$VENV_PATH"
    source "$VENV_PATH/bin/activate"
}

# 检查 Python 依赖是否已安装
check_backend_deps() {
    echo "正在检查 Python 依赖..."
    
    # 检查 backend 目录是否存在
    if [ ! -d "backend" ]; then
        echo "\033[31m错误：backend 目录不存在！\033[0m"
        echo "请确保项目结构完整。"
        exit 1
    fi
    
    # 检查 pyproject.toml 文件是否存在
    if [ ! -f "backend/pyproject.toml" ]; then
        echo "\033[31m错误：backend/pyproject.toml 文件不存在！\033[0m"
        echo "请确保项目结构完整。"
        exit 1
    fi
    
    # 检查虚拟环境是否存在并激活
    check_venv
    
    # 检查关键依赖是否已安装
    DEPENDENCIES=("uvicorn" "fastapi" "mysql-connector-python")
    MISSING_DEPS=()
    
    for dep in "${DEPENDENCIES[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            MISSING_DEPS+=("$dep")
        fi
    done
    
    # 如果有缺失的依赖，提示用户安装
    if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
        echo "\033[33m警告：以下依赖缺失：${MISSING_DEPS[*]}\033[0m"
        echo "请运行以下命令安装缺失的依赖："
        echo "cd backend"
        echo "pip install ${MISSING_DEPS[*]}"
        echo "或者使用 pip install -e . 安装所有依赖"
        echo ""
        # 不退出，只是提示用户
    else
        echo "\033[32m所有 Python 依赖均已安装。\033[0m"
    fi
}

# 检查并终止占用指定端口的进程
check_and_kill_port() {
    local port=$1
    local service_name=$2
    echo "正在检查端口 $port 是否被 $service_name 占用..."
    
    # 使用 lsof 查找占用端口的进程
    local pid=$(lsof -i :$port -t)
    
    if [ -n "$pid" ]; then
        echo "\033[33m警告：端口 $port 被进程 $pid 占用\033[0m"
        
        # 获取进程信息
        local process_info=$(ps -p $pid -o pid,ppid,cmd -h 2>/dev/null)
        echo "进程信息: $process_info"
        
        # 尝试终止进程
        if kill -9 $pid 2>/dev/null; then
            echo "\033[32m成功终止占用端口 $port 的进程 (PID: $pid)\033[0m"
            # 记录被终止的进程信息
            echo "[INFO] Terminated process on port $port: $process_info" >> /tmp/chatbi_port_cleanup.log
        else
            echo "\033[31m错误：无法终止占用端口 $port 的进程 (PID: $pid)\033[0m"
            echo "请手动终止该进程或选择其他端口。"
            return 1
        fi
    else
        echo "\033[32m端口 $port 未被占用，可以继续使用。\033[0m"
    fi
    
    return 0
}

# 检查前端依赖是否已安装
check_frontend_deps() {
    echo "正在检查前端依赖..."
    
    # 检查 frontend 目录是否存在
    if [ ! -d "../frontend" ]; then
        echo "\033[31m错误：frontend 目录不存在！\033[0m"
        echo "请确保项目结构完整。"
        exit 1
    fi
    
    # 检查 package.json 文件是否存在
    if [ ! -f "../frontend/package.json" ]; then
        echo "\033[31m错误：frontend/package.json 文件不存在！\033[0m"
        echo "请确保项目结构完整。"
        exit 1
    fi
    
    # 检查 node_modules 目录是否存在
    if [ ! -d "../frontend/node_modules" ]; then
        echo "\033[33m警告：node_modules 目录不存在，正在执行 npm install...\033[0m"
        cd ../frontend
        npm install
        if [ $? -ne 0 ]; then
            echo "\033[31m错误：npm install 失败！\033[0m"
            echo "请检查网络连接或手动执行 npm install。"
            exit 1
        fi
        cd ..
        echo "\033[32mnpm install 完成。\033[0m"
    else
        echo "\033[32mnode_modules 目录已存在。\033[0m"
    fi
}

echo "正在启动 ChatBI 应用程序..."

# 设置工作目录
cd /Users/zhanh391/PC/ChatBI

# 检查并激活虚拟环境
check_venv

# 检查并清理 8000 端口（后端服务）
if ! check_and_kill_port 8000 "后端服务"; then
    echo "\033[31m错误：无法清理 8000 端口，启动失败。\033[0m"
    exit 1
fi

# 检查 Python 依赖
check_backend_deps

# 定义数据库检查函数
check_database() {
    echo "正在检查 MySQL 数据库连接..."
    
    # 使用 mysql 命令尝试连接数据库
    # -u root: 使用 root 用户
    # -p12345678: 使用密码 12345678
    # --silent: 静默模式，减少输出
    # --execute: 执行一个简单的查询
    # "SELECT 1": 测试查询，如果连接成功则返回 1
    if mysql -uroot -p12345678 --silent --execute "SELECT 1" > /dev/null 2>&1; then
        echo "\033[32m数据库连接成功！\033[0m"
        return 0
    else
        echo "\033[31m错误：无法连接到 MySQL 数据库！\033[0m"
        echo "\033[33m请确保 MySQL 服务正在运行，并且数据库已初始化。\033[0m"
        echo "\033[33m如果数据库尚未初始化，请运行：\033[0m"
        echo "\033[33m  mysql -u root < database/init.sql\033[0m"
        return 1
    fi
}

# 检查数据库连接
if ! check_database; then
    echo "\033[31m错误：数据库检查失败，启动被中止。\033[0m"
    exit 1
fi

# 启动后端服务（在后台运行）
echo "正在启动后端服务..."
cd backend
# 只加载有效的环境变量（忽略注释和空行）
while IFS='=' read -r key value; do
    # 跳过空行和注释行（以#开头）
    if [[ -n "$key" && ! "$key" =~ ^[[:space:]]*# ]]; then
        # 去除值周围的引号（如果存在）
        value="${value%\"}"
        value="${value#\"}"
        export "$key"="$value"
    fi
done < .env

uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "后端服务已启动，PID: $BACKEND_PID"

# 等待后端服务启动（给5秒时间，确保完全启动）
echo "正在等待后端服务启动..."
sleep 5

# 健康检查：验证后端服务是否正常运行
echo "正在对后端服务进行健康检查..."
if curl -s --fail http://localhost:8000/health > /dev/null; then
    echo "\033[32m健康检查通过：后端服务运行正常！\033[0m"
else
    echo "\033[31m健康检查失败：后端服务未正常运行！\033[0m"
    echo "正在查看后端日志以诊断问题..."
    tail -n 10 ../backend.log
    echo "\033[31m后端服务启动失败，终止启动过程。\033[0m"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# 检查并清理 3000 端口（前端服务） - 修改为 3000 端口
if ! check_and_kill_port 3000 "前端服务"; then
    echo "\033[31m错误：无法清理 3000 端口，启动失败。\033[0m"
    exit 1
fi

# 检查前端依赖
check_frontend_deps

# 启动前端服务（在后台运行）
echo "正在启动前端服务..."
cd ../frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端服务已启动，PID: $FRONTEND_PID"

# 显示服务信息
echo ""
echo "==========================================="
echo "ChatBI 应用程序启动成功！"
echo "后端服务: http://localhost:8000"
echo "前端界面: http://localhost:3000"
echo "后端日志: /Users/zhanh391/PC/ChatBI/backend.log"
echo "前端日志: /Users/zhanh391/PC/ChatBI/frontend.log"
echo "==========================================="
echo ""
echo "要停止应用程序，请运行：./scripts/stop.sh"

# 保持脚本运行，以便可以使用 Ctrl+C 停止
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM
wait