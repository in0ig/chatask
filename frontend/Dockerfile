# ChatBI 前端 Dockerfile
# 多阶段构建：Node 构建 → nginx 静态服务

# ==================== 构建阶段 ====================
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package.json package-lock.json ./

# 安装依赖
RUN npm ci --ignore-scripts

# 复制源码并构建
COPY . .
RUN npm run build

# ==================== 生产阶段 ====================
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置（由根目录 nginx.conf 提供）
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
