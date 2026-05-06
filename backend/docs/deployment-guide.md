# ChatBI 后端服务部署指南

## 目录
- [1. 环境要求](#1-环境要求)
- [2. 部署方式](#2-部署方式)
- [3. Docker 部署](#3-docker-部署)
- [4. 本地部署](#4-本地部署)
- [5. 数据库初始化](#5-数据库初始化)
- [6. Nginx 配置](#6-nginx-配置)
- [7. 系统服务配置](#7-系统服务配置)
- [8. 日志配置](#8-日志配置)
- [9. 备份策略](#9-备份策略)
- [10. 监控与维护](#10-监控与维护)
- [11. 安全建议](#11-安全建议)

## 1. 环境要求

### 硬件要求
- CPU: 至少 2 核
- 内存: 至少 4GB
- 磁盘: 至少 20GB 可用空间（建议使用 SSD）
- 网络: 稳定的网络连接

### 软件要求
- 操作系统: Ubuntu 20.04/22.04, CentOS 7/8, 或 macOS
- Docker: 20.10+
- Docker Compose: 1.29+
- MySQL: 8.0+
- Redis: 7.0+
- Python: 3.12+

### 网络端口
| 服务 | 端口 | 用途 |
|------|------|------|
| ChatBI 后端 | 8000 | API 服务 |
| MySQL | 3306 | 数据库服务 |
| Redis | 6379 | 缓存服务 |
| Prometheus | 9091 | 监控指标 |
| Nginx | 80/443 | 反向代理 |

## 2. 部署方式

ChatBI 后端服务支持两种部署方式：

### Docker 部署（推荐）
- 适用于开发、测试和生产环境
- 隔离性好，依赖管理简单
- 支持多环境配置
- 易于扩展和维护

### 本地部署
- 适用于开发和测试环境
- 直接运行 Python 服务
- 需要手动管理依赖
- 适合快速原型开发

## 3. Docker 部署

### 准备工作
1. 确保 Docker 和 Docker Compose 已安装并运行
2. 克隆项目代码
3. 创建 .env 文件（基于 .env.example）

```bash
# 复制环境变量配置文件
cp .env.example .env

# 编辑 .env 文件，根据实际环境修改配置
nano .env
```

### 部署步骤

1. 构建镜像
```bash
# 构建后端服务镜像
docker-compose build chatbi-backend
```

2. 启动服务
```bash
# 在后台启动所有服务
docker-compose up -d
```

3. 检查服务状态
```bash
# 查看容器状态
docker-compose ps

# 查看后端服务日志
docker-compose logs -f chatbi-backend

# 查看数据库服务日志
docker-compose logs -f mysql

# 查看Redis服务日志
docker-compose logs -f redis
```

4. 验证服务
```bash
# 测试API是否正常运行
curl http://localhost:8000/health

# 访问API文档
open http://localhost:8000/docs
```

### 生产环境优化

1. 移除开发模式的 `--reload` 参数
2. 使用 Gunicorn 替代 Uvicorn 提高性能
3. 配置 Nginx 作为反向代理
4. 启用 SSL/TLS 加密
5. 配置健康检查和自动重启

修改 `docker-compose.yml` 中的命令：
```yaml
# 替换原来的 CMD
CMD ["gunicorn", "src.main:app", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100"]
```

## 4. 本地部署

### 准备工作
1. 安装 Python 3.12+
2. 安装 MySQL 8.0+
3. 安装 Redis 7.0+
4. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 部署步骤

1. 创建 .env 文件
```bash
cp .env.example .env
nano .env
```

2. 初始化数据库
```bash
# 运行数据库迁移
alembic upgrade head

# 或者直接导入初始化脚本
mysql -u root -p chatbi < database/init.sql
```

3. 启动服务
```bash
# 启动后端服务
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 或者使用开发模式（自动重载）
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

4. 验证服务
```bash
curl http://localhost:8000/health
open http://localhost:8000/docs
```

## 5. 数据库初始化

### 使用 Alembic 迁移（推荐）

Alembic 是数据库迁移工具，用于管理数据库结构变更。

```bash
# 查看当前迁移状态
alembic current

# 生成新的迁移脚本
alembic revision --autogenerate -m "添加新功能"

# 应用迁移
alembic upgrade head

# 回滚到上一个版本
alembic downgrade -1

# 查看所有迁移历史
alembic history
```

### 使用 SQL 脚本初始化

对于新部署，可以直接使用 `database/init.sql` 脚本初始化数据库：

```bash
# 连接到 MySQL
mysql -u root -p

# 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS chatbi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 使用数据库
USE chatbi;

# 导入初始化脚本
SOURCE /path/to/ChatBI/backend/database/init.sql;
```

## 6. Nginx 配置

为提高性能和安全性，建议使用 Nginx 作为反向代理。

### Nginx 配置文件示例 (`/etc/nginx/sites-available/chatbi`)

```nginx
# ChatBI 后端服务 Nginx 配置
upstream chatbi_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name chatbi.example.com;
    client_max_body_size 50M;
    
    # 强制重定向到 HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name chatbi.example.com;
    
    # SSL 证书配置
    ssl_certificate /etc/letsencrypt/live/chatbi.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chatbi.example.com/privkey.pem;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    add_header X-XSS-Protection "1; mode=block";
    
    # 静态文件缓存（如果需要）
    location /static/ {
        alias /var/www/chatbi/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # API 代理
    location /api/ {
        proxy_pass http://chatbi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size 50M;
    }
    
    # 健康检查端点
    location /health {
        proxy_pass http://chatbi_backend/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 根路径重定向到 API 文档
    location = / {
        return 302 /docs;
    }
    
    # 日志配置
    access_log /var/log/nginx/chatbi-access.log;
    error_log /var/log/nginx/chatbi-error.log;
}
```

### 启用 Nginx 配置

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/chatbi /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

## 7. 系统服务配置

为确保服务在系统重启后自动启动，建议使用 systemd 服务。

### systemd 服务文件 (`/etc/systemd/system/chatbi-backend.service`)

```ini
[Unit]
Description=ChatBI Backend Service
After=network.target mysql.target redis.target
Requires=mysql.target redis.target

[Service]
Type=simple
User=chatbi
Group=chatbi
WorkingDirectory=/opt/chatbi/backend
Environment=PYTHONPATH=/opt/chatbi/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/chatbi/backend/venv/bin/gunicorn src.main:app --bind 0.0.0.0:8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker --timeout 120 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100
Restart=always
RestartSec=10

# 日志配置
StandardOutput=journal
StandardError=journal

# 资源限制
LimitNOFILE=65536
LimitNPROC=65536

# 安全配置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/chatbi /var/www/chatbi/uploads

[Install]
WantedBy=multi-user.target
```

### 创建服务用户和目录

```bash
# 创建服务用户
sudo useradd --system --shell /bin/false chatbi

# 创建工作目录
sudo mkdir -p /opt/chatbi/backend
sudo chown -R chatbi:chatbi /opt/chatbi/backend

# 创建日志和上传目录
sudo mkdir -p /var/log/chatbi /var/www/chatbi/uploads
sudo chown -R chatbi:chatbi /var/log/chatbi /var/www/chatbi/uploads
```

### 启用服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务开机自启
sudo systemctl enable chatbi-backend

# 启动服务
sudo systemctl start chatbi-backend

# 查看服务状态
sudo systemctl status chatbi-backend

# 查看服务日志
sudo journalctl -u chatbi-backend -f
```

## 8. 日志配置

### 后端服务日志

在 `.env` 文件中配置日志文件路径：

```
LOG_FILE=/var/log/chatbi/backend.log
LOG_MAX_SIZE=104857600  # 100MB
LOG_BACKUP_COUNT=5
```

### 日志轮转配置 (`/etc/logrotate.d/chatbi`)

```bash
/var/log/chatbi/*.log {
    daily
    missingok
    rotate 5
    compress
    delaycompress
    notifempty
    create 640 chatbi chatbi
    sharedscripts
    postrotate
        systemctl reload chatbi-backend > /dev/null
    endscript
}
```

### 配置日志轮转

```bash
# 测试日志轮转配置
sudo logrotate -d /etc/logrotate.d/chatbi

# 手动执行日志轮转
sudo logrotate -f /etc/logrotate.d/chatbi
```

## 9. 备份策略

### 数据库备份

```bash
# 创建备份目录
mkdir -p /backup/chatbi/database

# 创建备份脚本 (/opt/chatbi/backup/backup-db.sh)
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/chatbi/database"
DB_NAME="chatbi"
DB_USER="root"
DB_PASSWORD="your_strong_password"

# 创建备份文件
mysqldump -u $DB_USER -p$DB_PASSWORD $DB_NAME > $BACKUP_DIR/chatbi_${DATE}.sql

# 压缩备份文件
gzip $BACKUP_DIR/chatbi_${DATE}.sql

# 删除超过7天的备份
find $BACKUP_DIR -name "chatbi_*.sql.gz" -mtime +7 -delete

# 记录备份日志
echo "[$(date)] 数据库备份完成: chatbi_${DATE}.sql.gz" >> $BACKUP_DIR/backup.log
```

### 设置定时备份

```bash
# 编辑 crontab
crontab -e

# 添加每日凌晨2点备份任务
0 2 * * * /opt/chatbi/backup/backup-db.sh
```

### 文件备份

```bash
# 备份上传文件
tar -czf /backup/chatbi/uploads/chatbi_uploads_$(date +%Y%m%d).tar.gz /var/www/chatbi/uploads/

# 备份配置文件
tar -czf /backup/chatbi/config/chatbi_config_$(date +%Y%m%d).tar.gz /opt/chatbi/backend/.env /opt/chatbi/backend/docker-compose.yml /etc/nginx/sites-available/chatbi
```

## 10. 监控与维护

### 健康检查端点

ChatBI 后端提供 `/health` 端点用于健康检查：

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "1.0.0"
}
```

### Prometheus 监控

1. 在 `.env` 文件中启用监控：
```
PROMETHEUS_PORT=9091
```

2. 访问监控指标：
```
http://localhost:9091/metrics
```

3. 配置 Prometheus 采集：
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'chatbi-backend'
    static_configs:
      - targets: ['chatbi.example.com:9091']
```

### 常见问题排查

| 问题 | 解决方案 |
|------|----------|
| 数据库连接失败 | 检查 .env 中的数据库配置，确认 MySQL 服务正在运行 |
| Redis 连接失败 | 检查 .env 中的 Redis 配置，确认 Redis 服务正在运行 |
| API 无法访问 | 检查防火墙设置，确认端口 8000 已开放 |
| 文件上传失败 | 检查上传目录权限，确认 /var/www/chatbi/uploads 目录可写 |
| 数据库迁移失败 | 检查 alembic 版本是否与数据库结构匹配，运行 alembic current 查看当前状态 |

## 11. 安全建议

### 数据库安全
- 使用强密码，避免使用默认密码
- 限制数据库用户权限，避免使用 root 用户
- 定期更新 MySQL 版本
- 启用 SSL 连接
- 配置防火墙，仅允许必要 IP 访问数据库端口

### 系统安全
- 使用非 root 用户运行服务
- 定期更新操作系统和软件包
- 启用防火墙（ufw/iptables）
- 配置 SSH 密钥认证，禁用密码登录
- 定期审查系统日志

### 应用安全
- 使用 HTTPS 加密通信
- 配置安全 HTTP 头
- 实施输入验证和输出编码
- 定期进行安全审计
- 限制文件上传类型和大小
- 实施速率限制防止暴力破解
- 定期更新依赖包

### 备份与恢复
- 定期备份数据库和关键配置文件
- 测试备份恢复流程
- 将备份存储在异地
- 使用加密备份

### 监控与告警
- 配置系统资源监控（CPU、内存、磁盘）
- 设置服务可用性监控
- 配置日志异常检测
- 设置告警通知（邮件、短信、Slack）

### 审计与合规
- 记录所有 API 访问日志
- 实施访问控制和权限管理
- 定期审查用户权限
- 遵守数据保护法规（GDPR、个人信息保护法等）

> **重要提示**：以上配置为生产环境部署建议。在实际部署前，请根据具体需求调整配置，并进行充分测试。