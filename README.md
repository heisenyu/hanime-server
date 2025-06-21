# HanimeViewer

HanimeViewer 是一个用于观看和下载动画视频的Web应用程序，采用现代化的前后端分离架构，由FastAPI后端和Vue.js前端组成。本项目提供友好的用户界面和高效的下载功能，支持视频搜索、浏览、播放和下载。

## 目录

- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [目录结构](#目录结构)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 功能特性

### 视频浏览与搜索
- 支持按类别、标签、上传时间等多维度浏览视频
- 强大的搜索功能，支持模糊搜索和精确匹配
- 视频信息展示，包括标题、封面、时长、标签等

### 视频播放
- 流畅的在线播放体验
- 自适应播放器，支持多种分辨率
- 播放历史记录

### 视频下载
- 高性能多线程下载功能
- 断点续传支持，意外中断可继续下载
- 下载任务管理（暂停、恢复、取消）
- 下载进度实时显示

### 系统功能
- 响应式界面设计，支持多种设备访问
- 代理设置支持，解决网络访问限制问题
- Docker容器化部署，简化安装和维护

## 技术架构

### 后端技术栈
- **FastAPI**: 高性能的Python Web框架
- **Loguru**: 结构化日志记录
- **aiohttp**: 异步HTTP客户端/服务器
- **SQLite**: 轻量级数据库

### 前端技术栈
- **Vue.js**: 渐进式JavaScript框架
- **Ant Design Vue**: UI组件库
- **Axios**: HTTP客户端
- **TypeScript**: 类型安全的JavaScript

### 部署环境
- **Docker & Docker Compose**: 容器化部署
- **Nginx**: 高性能Web服务器和反向代理

## 快速开始

### 使用Docker Compose启动（推荐）

1. 克隆仓库

```bash
git clone https://github.com/your-username/hanime-server.git
cd hanime-server
```

2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 根据需要编辑.env文件
nano .env  # 或使用其他编辑器
```

3. 创建数据目录

```bash
# 创建下载和日志存储目录
mkdir -p data/downloads data/logs
```

4. 启动服务

```bash
docker-compose up -d
```

5. 访问应用

- 前端应用: `http://localhost` (或配置的FRONTEND_PORT端口)
- 后端API: `http://localhost:8000` (或配置的BACKEND_PORT端口)
- API文档: `http://localhost:8000/docs` (或配置的BACKEND_PORT端口)

### 手动安装

#### 后端安装

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 创建目录
mkdir -p downloads logs

# 运行服务
python main.py
```

#### 前端安装

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 开发模式运行
npm run dev

# 构建生产版本
npm run build
```

## 详细配置

### 环境变量配置

根目录下的`.env`文件中可以配置以下参数:

| 变量名 | 描述 | 默认值 | 必填 |
|---|---|---|---|
| APP_NAME | 应用名称 | HanimeViewer | 否 |
| APP_DESCRIPTION | 应用描述 | HanimeViewer API服务 | 否 |
| APP_VERSION | 应用版本 | 1.0.0 | 否 |
| RELOAD | 是否启用热重载 | False | 否 |
| HOST | 后端服务主机 | 0.0.0.0 | 否 |
| PORT | 后端服务端口 | 8000 | 否 |
| BACKEND_PORT | Docker映射的后端服务端口 | 8000 | 否 |
| FRONTEND_PORT | Docker映射的前端服务端口 | 80 | 否 |
| HANIME_BASE_URL | 基础API URL | https://hanime1.me | 否 |
| DOWNLOAD_PATH | 下载文件存储路径 | ./data/downloads | 否 |
| LOG_PATH | 日志文件存储路径 | ./data/logs | 否 |
| USE_PROXY | 是否使用代理 | False | 否 |
| PROXY_URL | 代理服务器URL | | 否 |
| USE_DOWNLOAD_PROXY | 是否为下载使用专用代理 | False | 否 |
| DOWNLOAD_PROXY_URL | 下载专用代理URL | | 否 |
| USER_AGENT | HTTP请求的User-Agent | Mozilla/5.0 ... | 否 |
| LOG_LEVEL | 日志级别 | INFO | 否 |

### Docker配置

Docker Compose配置支持以下功能:

- 自动构建前后端服务
- 数据卷映射，保证数据持久化
- 环境变量传递
- 网络配置，确保服务间通信

### Nginx配置

前端服务使用Nginx配置实现:

- 静态文件服务
- API请求反向代理
- 下载文件反向代理
- 默认首页配置

## 目录结构

```
hanime-server/
├── backend/                # FastAPI后端
│   ├── app/                # 应用核心代码
│   │   ├── api/            # API接口定义
│   │   │   ├── endpoints/  # 各模块的API端点
│   │   │   └── routes.py   # 路由配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑服务
│   │   ├── utils/          # 工具函数
│   │   └── config.py       # 配置文件
│   ├── downloads/          # 下载文件存储目录
│   ├── logs/               # 日志文件目录
│   ├── main.py             # 应用入口文件
│   ├── requirements.txt    # 项目依赖
│   └── Dockerfile          # 后端Docker配置
├── frontend/               # Vue.js前端
│   ├── src/                # 源代码
│   │   ├── api/            # API调用封装
│   │   ├── assets/         # 静态资源
│   │   ├── components/     # 组件
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # 状态管理
│   │   ├── types/          # 类型定义
│   │   ├── utils/          # 工具函数
│   │   ├── App.vue         # 根组件
│   │   └── main.ts         # 入口文件
│   ├── Dockerfile          # 前端Docker配置
│   └── nginx.conf          # Nginx配置
├── data/                   # 数据目录
│   ├── downloads/          # 下载文件目录
│   └── logs/               # 日志文件目录
├── docker-compose.yml      # Docker Compose配置
├── .env.example            # 环境变量示例
├── .env                    # 环境变量配置(本地)
├── .gitignore              # Git忽略文件配置
├── .dockerignore           # Docker忽略文件配置
└── README.md               # 项目说明文档
```

## 开发指南

### 代码风格

- 后端：遵循PEP 8 Python代码风格
- 前端：遵循Vue风格指南和TypeScript最佳实践

### 后端开发

1. 设置Python虚拟环境:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. 运行开发服务器:

```bash
python main.py
```

3. API文档访问:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 前端开发

1. 安装依赖:

```bash
cd frontend
npm install
```

2. 运行开发服务器:

```bash
npm run dev
```

3. 构建生产版本:

```bash
npm run build
```

## 常见问题

### Q: 如何修改前后端通信端口?
A: 修改`.env`文件中的`BACKEND_PORT`和`FRONTEND_PORT`变量，然后重启Docker容器。

### Q: 视频无法播放或下载速度很慢怎么办?
A: 尝试配置代理服务。在`.env`文件中设置`USE_PROXY=True`和`PROXY_URL=你的代理地址`。

### Q: 如何查看应用日志?
A: 日志文件存储在`data/logs`目录中，也可以通过Docker命令查看容器日志:
```bash
docker logs hanime-server-backend
docker logs hanime-server-frontend
```

### Q: 下载的视频存储在哪里?
A: 下载的视频存储在`data/downloads`目录中，可以通过文件浏览器直接访问。

## 贡献指南

欢迎提交问题报告和代码贡献！请按以下步骤操作:

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启Pull Request

## 许可证

本项目采用MIT许可证。详见`LICENSE`文件。 