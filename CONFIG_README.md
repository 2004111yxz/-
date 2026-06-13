# 模型配置系统文档

## 概述

本配置系统为墨冉AI平台提供完整的配置管理解决方案，支持模型参数的灵活定义、环境变量的动态加载、多环境配置隔离以及配置项的类型校验。

## 核心功能

### 1. 多环境配置支持

系统支持三种部署环境：

| 环境 | 说明 | 调试模式 | 速率限制 | 日志级别 |
|------|------|----------|----------|----------|
| `development` | 开发环境 | 开启 | 100请求/分钟 | DEBUG |
| `testing` | 测试环境 | 开启 | 60请求/分钟 | INFO |
| `production` | 生产环境 | 关闭 | 30请求/分钟 | WARNING |

### 2. 模型配置

#### 模型字段说明

| 字段名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `name` | string | ✅ | 模型唯一标识符 | `gpt-4` |
| `display_name` | string | ❌ | 界面显示名称 | `GPT-4` |
| `provider` | string | ❌ | 模型提供商 | `openai` |
| `base_url` | string | ✅ | API基础地址 | `https://api.openai.com/v1` |
| `api_key` | string | ✅ | API密钥 | `sk-xxx` |
| `input_price` | float | ✅ | 输入价格(元/千Token) | `0.0015` |
| `output_price` | float | ✅ | 输出价格(元/千Token) | `0.002` |
| `status` | int | ❌ | 状态(0=禁用,1=启用) | `1` |
| `sort` | int | ❌ | 排序权重 | `10` |
| `remark` | string | ❌ | 备注信息 | `仅工作时间可用` |

#### 支持的模型提供商

| 提供商标识 | 显示名称 |
|------------|----------|
| `openai` | OpenAI |
| `deepseek` | DeepSeek |
| `doubao` | 豆包 |
| `baidu` | 百度文心 |
| `alibaba` | 阿里通义 |
| `anthropic` | Anthropic |
| `other` | 其他 |

### 3. 配置验证

系统提供完整的配置验证功能：

```python
from config import ModelConfig, validate_model_config

# 创建配置
model = ModelConfig(
    name="gpt-4",
    base_url="https://api.openai.com/v1",
    api_key="sk-test123"
)

# 验证配置
errors = model.validate()
if errors:
    print("配置验证失败:", errors)
else:
    print("配置有效")
```

## 使用方法

### 1. 基本使用

```python
from config import config, ModelConfig

# 获取配置管理器实例
print(f"当前环境: {config.current_env.value}")

# 获取所有启用的模型
models = config.get_models(enabled_only=True)
for model in models:
    print(f"{model.display_name}: ¥{model.input_price}/千Token")
```

### 2. 添加自定义模型

```python
# 添加单个模型
success = config.add_model({
    'name': 'my-custom-model',
    'display_name': '我的自定义模型',
    'provider': 'openai',
    'base_url': 'https://api.example.com/v1',
    'api_key': 'sk-custom-key',
    'input_price': 0.001,
    'output_price': 0.002,
    'status': 1,
    'sort': 5
})

if success:
    print("模型添加成功")
```

### 3. 配置验证

```python
# 验证所有配置
results = config.validate_all()
if results:
    print("发现配置错误:")
    for key, errors in results.items():
        print(f"  {key}: {errors}")
else:
    print("所有配置有效")
```

### 4. 导出/导入配置

```python
# 导出配置到文件
config.export_config('my-config.json')

# 从文件导入配置
config.import_config('my-config.json')
```

## 环境变量配置

### 支持的环境变量

| 变量名 | 说明 | 可选值 | 默认值 |
|--------|------|--------|--------|
| `FLASK_ENV` | 部署环境 | `development`, `testing`, `production` | `development` |
| `ENV` | 部署环境（备选） | 同上 | `development` |
| `DATABASE_URL` | 数据库连接URL | PostgreSQL连接字符串 | - |
| `SECRET_KEY` | 应用密钥 | 自定义字符串 | `moran-ai-platform-2024` |
| `LOG_LEVEL` | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `RATE_LIMIT` | API速率限制 | 正整数 | 环境相关 |
| `ALLOW_ORIGINS` | 允许的跨域源 | 逗号分隔的域名列表 | `*` |

### 配置示例

**开发环境 (.env):**
```bash
FLASK_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
RATE_LIMIT=100
ALLOW_ORIGINS=*
```

**生产环境 (.env):**
```bash
FLASK_ENV=production
DEBUG=false
LOG_LEVEL=WARNING
RATE_LIMIT=30
ALLOW_ORIGINS=https://your-domain.com
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SECRET_KEY=your-secure-secret-key-here
```

## API 参考

### Environment 枚举

```python
class Environment(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, value: str) -> 'Environment':
        """从字符串转换为环境枚举"""
        
    @classmethod
    def get_current(cls) -> 'Environment':
        """获取当前环境配置"""
```

### ModelProvider 枚举

```python
class ModelProvider(Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    DOUBAN = "doubao"
    BAIDU = "baidu"
    ALIBABA = "alibaba"
    ANTHROPIC = "anthropic"
    OTHER = "other"
```

### ModelConfig 数据类

```python
@dataclass
class ModelConfig:
    name: str                                    # 模型名称
    display_name: str = ""                       # 显示名称
    provider: str = "openai"                     # 提供商
    base_url: str = ""                           # API地址
    api_key: str = ""                            # API密钥
    input_price: float = 0.0                     # 输入价格
    output_price: float = 0.0                    # 输出价格
    status: int = 1                              # 状态
    sort: int = 10                              # 排序
    remark: str = ""                             # 备注
    version: int = 1                             # 版本号
    
    def validate(self) -> List[str]:
        """验证配置有效性"""
        
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        """从字典创建"""
```

### ConfigManager 类

```python
class ConfigManager:
    current_env: Environment                     # 当前环境
    env_config: EnvironmentConfig              # 环境配置
    
    def add_model(self, model: Union[Dict, ModelConfig], validate: bool = True) -> bool:
        """添加或更新模型配置"""
        
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """获取指定模型配置"""
        
    def get_models(self, enabled_only: bool = False) -> List[ModelConfig]:
        """获取所有模型配置"""
        
    def remove_model(self, name: str) -> bool:
        """移除模型配置"""
        
    def validate_all(self) -> Dict[str, List[str]]:
        """验证所有配置"""
        
    def to_dict(self) -> Dict[str, Any]:
        """导出配置为字典"""
        
    def export_config(self, filepath: str) -> bool:
        """导出配置到文件"""
        
    def import_config(self, filepath: str) -> bool:
        """从文件导入配置"""
```

## 单元测试

运行配置模块的单元测试：

```bash
python test_config.py
```

测试覆盖：
- ✅ 环境配置测试
- ✅ 模型提供商测试
- ✅ 模型配置测试
- ✅ 环境配置验证测试
- ✅ 配置管理器测试
- ✅ 辅助函数测试
- ✅ 完整工作流程集成测试

## 文件结构

```
项目根目录/
├── config.py              # 配置模块（核心）
├── config.example.env     # 环境变量配置模板
├── models.example.json    # 模型配置示例
├── test_config.py         # 单元测试
└── CONFIG_README.md       # 本文档
```

## 最佳实践

### 1. 生产环境配置

- 使用环境变量而非硬编码配置
- 设置复杂的 `SECRET_KEY`
- 配置具体的 `ALLOW_ORIGINS` 而非 `*`
- 使用 PostgreSQL 数据库
- 设置合理的 `RATE_LIMIT`

### 2. 配置验证

- 在添加配置前进行验证
- 定期运行 `config.validate_all()` 检查配置状态
- 导出配置备份

### 3. 模型管理

- 为不同环境使用不同的模型配置
- 定期更新 API 密钥
- 监控模型使用情况和费用

## 更新日志

### v1.0.0 (2024-06-13)
- 实现完整的配置管理系统
- 支持多环境配置
- 添加配置验证功能
- 提供单元测试
- 完善文档说明
