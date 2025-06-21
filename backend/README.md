# Web下载器

这是一个基于Python FastAPI构建的高性能Web文件下载器，支持多线程下载、断点续传、暂停恢复等功能。

## 目录结构

```
backend/
├── app/                # 应用核心代码
│   ├── api/            # API接口定义
│   ├── models/         # 数据模型
│   ├── services/       # 业务逻辑服务
│   ├── utils/          # 工具函数
│   └── config.py       # 配置文件
├── downloads/          # 下载文件存储目录
├── logs/               # 日志文件目录
├── main.py             # 应用入口文件
└── requirements.txt    # 项目依赖
```

## 运行方式

### 本地开发

```bash
# 安装依赖
pip install -r app/requirements.txt

# 启动服务
python main.py
```