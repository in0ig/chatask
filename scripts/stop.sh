#!/bin/bash

# ChatBI 停止脚本
# 用于安全停止前后端服务
# 验证需求 5.5

echo "Stopping ChatBI application..."
echo "========================================="

# 查找并杀死后端进程
backend_pid=""
echo "Checking backend service..."
backend_process=$(pgrep -f "uvicorn.*src.main:app" | head -1)
if [ -n "$backend_process" ]; then
    backend_pid=$backend_process
    echo "Found backend process (PID: $backend_pid)"
    echo "Are you sure you want to terminate this process? (y/N): "
    read -r confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        kill -TERM $backend_pid
        if kill -0 $backend_pid 2>/dev/null; then
            echo "Backend process did not terminate gracefully, forcing kill..."
            kill -9 $backend_pid 2>/dev/null
        fi
        echo "Backend process (PID: $backend_pid) terminated successfully."
    else
        echo "Backend process termination cancelled by user."
    fi
else
    echo "No backend process found."
fi

# 查找并杀死前端进程
frontend_pid=""
echo -e "\nChecking frontend service..."
frontend_process=$(pgrep -f "npm run dev" | head -1)
if [ -n "$frontend_process" ]; then
    frontend_pid=$frontend_process
    echo "Found frontend process (PID: $frontend_pid)"
    echo "Are you sure you want to terminate this process? (y/N): "
    read -r confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        kill -TERM $frontend_pid
        if kill -0 $frontend_pid 2>/dev/null; then
            echo "Frontend process did not terminate gracefully, forcing kill..."
            kill -9 $frontend_pid 2>/dev/null
        fi
        echo "Frontend process (PID: $frontend_pid) terminated successfully."
    else
        echo "Frontend process termination cancelled by user."
    fi
else
    echo "No frontend process found."
fi

# 清理日志文件
echo -e "\nCleaning up log files..."
if [ -f "backend.log" ]; then
    rm -f backend.log
    echo "Removed backend.log"
else
    echo "backend.log not found, skipping..."
fi

if [ -f "frontend.log" ]; then
    rm -f frontend.log
    echo "Removed frontend.log"
else
    echo "frontend.log not found, skipping..."
fi

# 创建新的空日志文件
echo -e "\nCreating new empty log files..."
touch backend.log
if [ -f "backend.log" ]; then
    echo "Created backend.log"
else
    echo "Failed to create backend.log"
fi

touch frontend.log
if [ -f "frontend.log" ]; then
    echo "Created frontend.log"
else
    echo "Failed to create frontend.log"
fi

echo "========================================="
echo "ChatBI application stopped successfully."
