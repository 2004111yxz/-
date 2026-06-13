# AI 中转平台

基于 Flask 的统一 AI 模型中转服务平台，支持多模型适配、流式响应、账户安全体系等核心功能。

## 技术栈

- **框架**: Flask 2.3.3
- **数据库**: SQLite / PostgreSQL
- **密码加密**: Argon2id
- **API 协议**: OpenAI 兼容

## 项目结构

```
src/
├── adapters/          # 模型适配层
│   ├── base_adapter.py      # 抽象适配器接口
│   ├── openai_adapter.py    # OpenAI 适配
│   ├── deepseek_adapter.py  # DeepSeek 适配
│   ├── doubao_adapter.py    # 豆包适配
│   └── adapter_factory.py   # 适配器工厂
├── api/               # API 路由层
│   ├── chat_api.py          # 聊天接口
│   └── video_api.py         # 视频生成接口
├── config/            # 配置层
│   └── settings.py          # 配置管理
├── security/          # 安全模块
│   └── password.py          # 密码策略与加密
├── services/          # 业务服务层
│   ├── user_service.py      # 用户服务
│   ├── model_service.py     # 模型服务
│   ├── chat_service.py      # 聊天服务
│   └── video_service.py     # 视频服务
├── utils/             # 工具层
│   └── database.py          # 数据库封装
└── app.py             # 应用入口
```

## 快速开始

### 环境要求

- Python 3.8+
- pip 包管理工具

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

创建 `.env` 文件：

```env
FLASK_APP=src/app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
PORT=5000
# PostgreSQL (可选)
# DATABASE_URL=postgresql://user:password@host:port/database
```

### 启动服务

```bash
python -m src.app
```

## API 接口

### 聊天接口

**POST** `/v1/chat/completions`

请求示例：
```json
{
    "model": "gpt-3.5-turbo",
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "stream": true
}
```

### 视频生成接口

**POST** `/v1/videos/generations`

请求示例：
```json
{
    "prompt": "A beautiful sunset over the ocean",
    "negative_prompt": "blurry, dark",
    "style": "cinematic",
    "duration": 10,
    "resolution": "1080p"
}
```

## 模型适配

新增模型适配需实现 `BaseModelAdapter` 接口：

```python
from src.adapters.base_adapter import BaseModelAdapter

class CustomAdapter(BaseModelAdapter):
    def format_request(self, body):
        # 格式化请求
        pass
    
    def format_response(self, response, streaming=False):
        # 格式化响应
        pass
    
    def parse_usage(self, response):
        # 解析使用量
        pass
    
    def generate(self, body):
        # 同步调用
        pass
    
    def generate_stream(self, body):
        # 流式调用
        pass
```

## 安全特性

- **密码策略**: 长度≥8位，包含大小写字母、数字、特殊字符中至少3类
- **加密算法**: Argon2id 慢哈希
- **防暴力破解**: 连续5次失败锁定15分钟
- **API 密钥认证**: Bearer Token 认证

## 许可证

MIT License
