# ChatBI 后端 Dockerfile

# ==================== 构建阶段 ====================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# 安装编译依赖（含 unixODBC 开发库，支持 pyodbc）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev gcc g++ curl ca-certificates unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 并同步依赖到 .venv
# 使用 pip 安装 uv（避免从 github.com 下载，支持国内镜像源）
COPY pyproject.toml uv.lock ./
ENV UV_HTTP_TIMEOUT=300
RUN pip install uv -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    uv sync --no-dev --frozen --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# ==================== 最终镜像 ====================
FROM python:3.12-slim-bookworm

WORKDIR /app

# 安装运行时系统依赖与 SQL Server ODBC 驱动
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg2 apt-transport-https default-mysql-client unixodbc \
    && curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 venv
COPY --from=builder /app/.venv /app/.venv

# 复制源码
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/
COPY config/ ./config/

# 复制启动脚本（转换行尾符 + 赋权，兼容 Windows CRLF）
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

# 创建日志目录
RUN mkdir -p /var/log/chatbi

# 激活 venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
