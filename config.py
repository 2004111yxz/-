"""
模型管理配置模块
================

提供完整的配置管理解决方案，支持：
- 模型参数的灵活定义
- 环境变量的动态加载
- 多环境配置隔离（开发/测试/生产）
- 配置项类型校验和默认值
- 配置验证和初始化

使用方法：
    from config import config, ModelConfig, Environment
    
    # 获取当前环境配置
    env = config.current_env
    
    # 获取所有模型配置
    models = config.get_models()
    
    # 获取指定模型配置
    model = config.get_model('gpt-3.5-turbo')
"""

import os
import logging
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
import json

logger = logging.getLogger(__name__)


class Environment(Enum):
    """部署环境枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, value: str) -> 'Environment':
        """
        从字符串转换为环境枚举
        
        Args:
            value: 环境名称字符串
            
        Returns:
            Environment: 对应的环境枚举值
            
        Raises:
            ValueError: 当环境名称无效时
        """
        value = value.lower().strip()
        for env in cls:
            if env.value == value:
                return env
        raise ValueError(f"无效的环境名称: {value}，可选值: {[e.value for e in cls]}")
    
    @classmethod
    def get_current(cls) -> 'Environment':
        """
        获取当前环境配置
        
        优先级：
        1. 环境变量 FLASK_ENV
        2. 环境变量 ENV
        3. 默认值 development
        
        Returns:
            Environment: 当前环境枚举值
        """
        env_value = os.environ.get('FLASK_ENV') or os.environ.get('ENV') or 'development'
        try:
            return cls.from_string(env_value)
        except ValueError:
            logger.warning(f"无效的FLASK_ENV/ENV值: {env_value}，使用默认值: development")
            return cls.DEVELOPMENT


class ModelProvider(Enum):
    """模型提供商枚举"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    DOUBAN = "doubao"
    BAIDU = "baidu"
    ALIBABA = "alibaba"
    ANTHROPIC = "anthropic"
    OTHER = "other"
    
    @classmethod
    def from_string(cls, value: str) -> 'ModelProvider':
        """从字符串转换为提供商枚举"""
        value = value.lower().strip()
        for provider in cls:
            if provider.value == value:
                return provider
        logger.warning(f"未知的模型提供商: {value}，使用默认值: other")
        return cls.OTHER
    
    @classmethod
    def get_display_name(cls, value: str) -> str:
        """获取提供商的显示名称"""
        display_names = {
            "openai": "OpenAI",
            "deepseek": "DeepSeek",
            "doubao": "豆包",
            "baidu": "百度文心",
            "alibaba": "阿里通义",
            "anthropic": "Anthropic",
            "other": "其他"
        }
        return display_names.get(value.lower(), value)


@dataclass
class ModelConfig:
    """
    模型配置数据类
    
    Attributes:
        name: 模型唯一标识符（用于API调用）
        display_name: 显示名称（界面友好名称）
        provider: 模型提供商
        base_url: API基础地址
        api_key: API密钥
        input_price: 输入价格（元/千Token）
        output_price: 输出价格（元/千Token）
        status: 状态（1=启用，0=禁用）
        sort: 排序权重（数字越小越靠前）
        remark: 备注信息
        version: 配置版本号
        
    Example:
        >>> model = ModelConfig(
        ...     name="gpt-3.5-turbo",
        ...     display_name="GPT-3.5-Turbo",
        ...     provider="openai",
        ...     base_url="https://api.openai.com/v1",
        ...     api_key="sk-xxx",
        ...     input_price=0.0015,
        ...     output_price=0.002
        ... )
    """
    name: str
    display_name: str = ""
    provider: str = "openai"
    base_url: str = ""
    api_key: str = ""
    input_price: float = 0.0
    output_price: float = 0.0
    status: int = 1
    sort: int = 10
    remark: str = ""
    version: int = 1
    
    def __post_init__(self):
        """初始化后处理"""
        # 类型校验和转换
        self.name = str(self.name).strip()
        self.display_name = str(self.display_name or self.name).strip()
        self.provider = str(self.provider or "openai").strip().lower()
        self.base_url = str(self.base_url or "").strip().rstrip('/')
        self.api_key = str(self.api_key or "").strip()
        self.input_price = float(self.input_price or 0.0)
        self.output_price = float(self.output_price or 0.0)
        # 注意：status=0 时 '0 or 1' 会返回 1，需要特殊处理
        self.status = int(self.status) if self.status is not None else 1
        self.sort = int(self.sort) if self.sort is not None else 10
        self.remark = str(self.remark or "").strip()
        self.version = int(self.version or 1)
    
    def validate(self) -> List[str]:
        """
        验证模型配置的有效性
        
        Returns:
            List[str]: 验证错误列表，如果为空则表示配置有效
        """
        errors = []
        
        # 检查必填字段
        if not self.name:
            errors.append("模型名称不能为空")
        elif len(self.name) > 100:
            errors.append("模型名称不能超过100个字符")
        
        if not self.base_url:
            errors.append("API地址不能为空")
        elif not self.is_valid_url(self.base_url):
            errors.append(f"API地址格式不正确: {self.base_url}")
        
        # 检查价格范围
        if self.input_price < 0:
            errors.append("输入价格不能为负数")
        
        if self.output_price < 0:
            errors.append("输出价格不能为负数")
        
        # 检查状态值
        if self.status not in [0, 1]:
            errors.append("状态值只能是0（禁用）或1（启用）")
        
        # 检查排序值
        if self.sort < 0:
            errors.append("排序值不能为负数")
        
        return errors
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """检查URL格式是否有效"""
        if not url:
            return False
        url = url.lower()
        return url.startswith('http://') or url.startswith('https://')
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelConfig':
        """从字典创建实例"""
        if not data:
            raise ValueError("配置数据不能为空")
        return cls(**data)
    
    def get_provider_display(self) -> str:
        """获取提供商的显示名称"""
        return ModelProvider.get_display_name(self.provider)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class EnvironmentConfig:
    """
    环境配置数据类
    
    Attributes:
        env: 环境名称
        debug: 是否调试模式
        log_level: 日志级别
        database_url: 数据库连接URL
        secret_key: 密钥
        allow_origins: 允许的源（跨域）
        rate_limit: 速率限制（请求/分钟）
    """
    env: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "INFO"
    database_url: Optional[str] = None
    secret_key: str = "moran-ai-platform-2024"
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit: int = 60
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.env, str):
            self.env = Environment.from_string(self.env)
        
        # 根据环境设置默认debug模式
        if self.env == Environment.DEVELOPMENT:
            self.debug = True
        elif self.env == Environment.PRODUCTION:
            self.debug = False
        else:
            self.debug = bool(self.debug)
        
        self.debug = bool(self.debug)
        self.log_level = str(self.log_level).upper()
        self.database_url = os.environ.get('DATABASE_URL') if not self.database_url else self.database_url
        if isinstance(self.allow_origins, str):
            self.allow_origins = [o.strip() for o in self.allow_origins.split(',')]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'env': self.env.value if isinstance(self.env, Environment) else self.env,
            'debug': self.debug,
            'log_level': self.log_level,
            'database_url': self.database_url,
            'secret_key': self.secret_key,
            'allow_origins': self.allow_origins,
            'rate_limit': self.rate_limit
        }
    
    def validate(self) -> List[str]:
        """验证环境配置的有效性"""
        errors = []
        
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            errors.append(f"无效的日志级别: {self.log_level}，可选值: {valid_log_levels}")
        
        if self.rate_limit <= 0:
            errors.append("速率限制必须大于0")
        
        return errors


class ConfigManager:
    """
    配置管理器
    
    核心功能：
    1. 管理多环境配置
    2. 管理模型配置
    3. 配置验证和初始化
    4. 配置持久化支持
    
    Attributes:
        current_env: 当前环境
        _models: 模型配置字典
        
    Example:
        >>> config = ConfigManager()
        >>> config.load_from_env()
        >>> model = config.get_model('gpt-3.5-turbo')
    """
    
    # 默认模型配置
    DEFAULT_MODELS: List[Dict[str, Any]] = [
        {
            "name": "gpt-3.5-turbo",
            "display_name": "GPT-3.5-Turbo",
            "provider": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "",
            "input_price": 0.0015,
            "output_price": 0.002,
            "status": 1,
            "sort": 10
        },
        {
            "name": "deepseek-chat",
            "display_name": "DeepSeek Chat",
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "input_price": 0.0005,
            "output_price": 0.0015,
            "status": 1,
            "sort": 20
        }
    ]
    
    # 支持的环境配置
    ENVIRONMENTS: Dict[str, Dict[str, Any]] = {
        "development": {
            "debug": True,
            "log_level": "DEBUG",
            "rate_limit": 100,
            "allow_origins": ["*"]
        },
        "testing": {
            "debug": True,
            "log_level": "INFO",
            "rate_limit": 60,
            "allow_origins": ["*"]
        },
        "production": {
            "debug": False,
            "log_level": "WARNING",
            "rate_limit": 30,
            "allow_origins": []  # 生产环境应配置具体域名
        }
    }
    
    def __init__(self):
        """初始化配置管理器"""
        self.current_env = Environment.get_current()
        self.env_config: Optional[EnvironmentConfig] = None
        self._models: Dict[str, ModelConfig] = {}
        self._validation_errors: List[str] = []
        
        # 加载配置
        self.load_from_env()
    
    def load_from_env(self) -> None:
        """
        从环境变量加载配置
        
        支持的环境变量：
        - FLASK_ENV / ENV: 部署环境
        - DATABASE_URL: 数据库连接URL
        - SECRET_KEY: 应用密钥
        - LOG_LEVEL: 日志级别
        - RATE_LIMIT: API速率限制
        - ALLOW_ORIGINS: 允许的跨域源
        """
        logger.info(f"加载配置，环境: {self.current_env.value}")
        
        # 加载环境配置
        env_defaults = self.ENVIRONMENTS.get(self.current_env.value, {})
        self.env_config = EnvironmentConfig(
            env=self.current_env,
            debug=env_defaults.get('debug', True),
            log_level=os.environ.get('LOG_LEVEL', env_defaults.get('log_level', 'INFO')),
            database_url=os.environ.get('DATABASE_URL'),
            secret_key=os.environ.get('SECRET_KEY', 'moran-ai-platform-2024'),
            allow_origins=os.environ.get('ALLOW_ORIGINS', ','.join(env_defaults.get('allow_origins', ['*']))),
            rate_limit=int(os.environ.get('RATE_LIMIT', env_defaults.get('rate_limit', 60)))
        )
        
        # 配置日志
        logging.getLogger().setLevel(getattr(logging, self.env_config.log_level))
        
        logger.debug(f"环境配置加载完成: {self.env_config}")
    
    def add_model(self, model: Union[Dict[str, Any], ModelConfig], validate: bool = True) -> bool:
        """
        添加或更新模型配置
        
        Args:
            model: 模型配置数据
            validate: 是否验证配置有效性
            
        Returns:
            bool: 添加是否成功
        """
        try:
            # 转换为 ModelConfig 对象
            if isinstance(model, dict):
                model_config = ModelConfig(**model)
            else:
                model_config = model
            
            # 验证配置
            if validate:
                errors = model_config.validate()
                if errors:
                    error_msg = f"模型 {model_config.name} 配置验证失败: {', '.join(errors)}"
                    logger.error(error_msg)
                    self._validation_errors.append(error_msg)
                    return False
            
            # 添加到配置字典
            self._models[model_config.name] = model_config
            logger.debug(f"添加模型配置: {model_config.name}")
            return True
            
        except Exception as e:
            error_msg = f"添加模型配置失败: {str(e)}"
            logger.error(error_msg)
            self._validation_errors.append(error_msg)
            return False
    
    def get_model(self, name: str) -> Optional[ModelConfig]:
        """
        获取指定模型配置
        
        Args:
            name: 模型名称
            
        Returns:
            Optional[ModelConfig]: 模型配置，如果不存在则返回None
        """
        return self._models.get(name)
    
    def get_models(self, enabled_only: bool = False) -> List[ModelConfig]:
        """
        获取所有模型配置
        
        Args:
            enabled_only: 是否只返回启用的模型
            
        Returns:
            List[ModelConfig]: 模型配置列表
        """
        models = list(self._models.values())
        
        if enabled_only:
            models = [m for m in models if m.status == 1]
        
        # 按排序字段排序
        models.sort(key=lambda x: (x.sort, x.name))
        return models
    
    def remove_model(self, name: str) -> bool:
        """
        移除模型配置
        
        Args:
            name: 模型名称
            
        Returns:
            bool: 移除是否成功
        """
        if name in self._models:
            del self._models[name]
            logger.debug(f"移除模型配置: {name}")
            return True
        return False
    
    def load_models_from_dict(self, models_data: List[Dict[str, Any]]) -> int:
        """
        从字典列表加载模型配置
        
        Args:
            models_data: 模型配置字典列表
            
        Returns:
            int: 成功加载的模型数量
        """
        count = 0
        for model_data in models_data:
            if self.add_model(model_data):
                count += 1
        logger.info(f"从数据加载了 {count}/{len(models_data)} 个模型配置")
        return count
    
    def load_default_models(self) -> int:
        """
        加载默认模型配置
        
        Returns:
            int: 成功加载的模型数量
        """
        return self.load_models_from_dict(self.DEFAULT_MODELS)
    
    def validate_all(self) -> Dict[str, List[str]]:
        """
        验证所有配置
        
        Returns:
            Dict[str, List[str]]: 验证结果，键为配置项，值为错误列表
        """
        results = {}
        
        # 验证环境配置
        if self.env_config:
            env_errors = self.env_config.validate()
            if env_errors:
                results['environment'] = env_errors
        
        # 验证所有模型配置
        for name, model in self._models.items():
            errors = model.validate()
            if errors:
                results[f'model:{name}'] = errors
        
        # 添加初始化时的错误
        if self._validation_errors:
            results['_init_errors'] = self._validation_errors
        
        return results
    
    def get_validation_report(self) -> str:
        """
        获取配置验证报告
        
        Returns:
            str: 格式化的验证报告
        """
        results = self.validate_all()
        
        if not results:
            return "✓ 所有配置验证通过"
        
        lines = ["配置验证失败：", ""]
        for key, errors in results.items():
            lines.append(f"【{key}】")
            for error in errors:
                lines.append(f"  - {error}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        导出配置为字典
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "environment": {
                "current": self.current_env.value,
                "config": self.env_config.to_dict() if self.env_config else {}
            },
            "models": {
                name: model.to_dict() 
                for name, model in self._models.items()
            },
            "validation_errors": self._validation_errors
        }
    
    def export_config(self, filepath: str) -> bool:
        """
        导出配置到JSON文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            bool: 导出是否成功
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"配置已导出到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, filepath: str) -> bool:
        """
        从JSON文件导入配置
        
        Args:
            filepath: 文件路径
            
        Returns:
            bool: 导入是否成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 导入模型配置
            if 'models' in data:
                for name, model_data in data['models'].items():
                    self.add_model(model_data, validate=False)
            
            logger.info(f"配置已从: {filepath} 导入")
            return True
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False
    
    def __repr__(self) -> str:
        """返回配置管理器的字符串表示"""
        return (
            f"ConfigManager("
            f"env={self.current_env.value}, "
            f"models={len(self._models)}, "
            f"errors={len(self._validation_errors)})"
        )


# 创建全局配置实例
config = ConfigManager()


def get_provider_name(provider: str) -> str:
    """
    获取提供商显示名称的便捷函数
    
    Args:
        provider: 提供商标识符
        
    Returns:
        str: 显示名称
    """
    return ModelProvider.get_display_name(provider)


def get_all_providers() -> List[Dict[str, str]]:
    """
    获取所有可用提供商列表
    
    Returns:
        List[Dict[str, str]]: 提供商列表，每个元素包含 value 和 label
    """
    return [
        {"value": p.value, "label": ModelProvider.get_display_name(p.value)}
        for p in ModelProvider
    ]


def validate_model_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证模型配置的便捷函数
    
    Args:
        config: 模型配置字典
        
    Returns:
        tuple[bool, List[str]]: (是否有效, 错误列表)
    """
    try:
        model = ModelConfig(**config)
        errors = model.validate()
        return (len(errors) == 0, errors)
    except Exception as e:
        return (False, [str(e)])


# 导出所有公共接口
__all__ = [
    'Environment',
    'ModelProvider',
    'ModelConfig',
    'EnvironmentConfig',
    'ConfigManager',
    'config',
    'get_provider_name',
    'get_all_providers',
    'validate_model_config'
]
