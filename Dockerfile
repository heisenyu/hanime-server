# 多阶段构建 - 前端构建
FROM node:18-alpine as frontend-build
WORKDIR /app/frontend

# 使用清华NPM镜像
RUN npm config set registry https://registry.npmmirror.com

# 复制并安装依赖
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npx vite build

# 后端构建
FROM python:3.10-slim

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR /app

# 使用清华pip镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# 复制后端代码
COPY backend/ /app/backend/
WORKDIR /app/backend

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装nginx
RUN apt-get update && \
    apt-get install -y nginx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 从前端构建阶段复制构建结果
COPY --from=frontend-build /app/frontend/dist /var/www/html

# 复制nginx配置
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 复制启动脚本
COPY start.sh /app/
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 7788

# 启动服务
CMD ["/app/start.sh"] 