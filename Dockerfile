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

# 后端构建与最终镜像
FROM python:3.10-slim

# 设置环境变量
ENV TZ=Asia/Shanghai \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive

# 设置时区
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


# 一步到位：配置国内镜像源并安装必要软件
RUN set -ex && \
    # 配置 apt 使用镜像
    rm -rf /etc/apt/sources.list.d/* /etc/apt/sources.list && \
    echo "deb http://mirrors.ustc.edu.cn/debian bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.ustc.edu.cn/debian bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.ustc.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    # 更新并安装
    apt-get update && \
    apt-get install -y nginx && \
    # 使用清华pip镜像
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    # 清理缓存
    apt-get clean && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/* /var/log/apt/* /var/log/dpkg.log

# 设置工作目录
WORKDIR /app

# 复制后端代码
COPY backend/ /app/backend/
WORKDIR /app/backend

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 从前端构建阶段复制构建结果
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# 复制nginx配置
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 复制启动脚本并设置权限
COPY start.sh /app/
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 7788

# 启动服务
CMD ["/app/start.sh"] 