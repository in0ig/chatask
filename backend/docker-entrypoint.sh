#!/bin/bash
# ChatBI 后端启动脚本
# 等待 MySQL 就绪 → 运行 alembic 迁移 → 启动服务

set -e

echo "⏳ 等待 MySQL 就绪..."
until python -c "
import pymysql, os, sys
try:
    pymysql.connect(
        host=os.environ.get('DB_HOST', 'mysql'),
        port=int(os.environ.get('DB_PORT', 3306)),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'chatbi'),
    )
    sys.exit(0)
except Exception:
    sys.exit(1)
"; do
    echo "   MySQL 未就绪，5秒后重试..."
    sleep 5
done

echo "✅ MySQL 已就绪"

echo "🔄 运行数据库迁移（alembic upgrade head）..."
alembic upgrade head

echo "🚀 启动后端服务..."
exec "$@"
