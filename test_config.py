"""
模型配置单元测试
=================

测试配置模块的各项功能，包括：
- 环境配置测试
- 模型配置测试
- 配置验证测试
- 配置管理器测试

运行方式：
    python -m pytest test_config.py -v
    或
    python test_config.py
"""

import os
import sys
import unittest
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    Environment,
    ModelProvider,
    ModelConfig,
    EnvironmentConfig,
    ConfigManager,
    config,
    get_provider_name,
    get_all_providers,
    validate_model_config
)


class TestEnvironment(unittest.TestCase):
    """测试环境枚举"""
    
    def test_environment_from_string(self):
        """测试从字符串创建环境枚举"""
        self.assertEqual(Environment.from_string("development"), Environment.DEVELOPMENT)
        self.assertEqual(Environment.from_string("TESTING"), Environment.TESTING)
        self.assertEqual(Environment.from_string("Production"), Environment.PRODUCTION)
        
        # 测试大小写不敏感
        self.assertEqual(Environment.from_string("DEVELOPMENT"), Environment.DEVELOPMENT)
        self.assertEqual(Environment.from_string("  development  "), Environment.DEVELOPMENT)
    
    def test_environment_invalid_value(self):
        """测试无效的环境值"""
        with self.assertRaises(ValueError):
            Environment.from_string("invalid")
        
        with self.assertRaises(ValueError):
            Environment.from_string("staging")  # staging 不是有效环境
    
    def test_environment_get_current(self):
        """测试获取当前环境"""
        # 测试默认环境
        env = Environment.get_current()
        self.assertIsInstance(env, Environment)
        
        # 测试环境变量设置
        os.environ['FLASK_ENV'] = 'production'
        self.assertEqual(Environment.get_current(), Environment.PRODUCTION)
        
        os.environ['FLASK_ENV'] = 'development'
        self.assertEqual(Environment.get_current(), Environment.DEVELOPMENT)
        
        # 测试 ENV 变量（优先级低于 FLASK_ENV）
        os.environ['FLASK_ENV'] = ''
        os.environ['ENV'] = 'testing'
        self.assertEqual(Environment.get_current(), Environment.TESTING)
        
        # 清理
        os.environ.pop('FLASK_ENV', None)
        os.environ.pop('ENV', None)


class TestModelProvider(unittest.TestCase):
    """测试模型提供商枚举"""
    
    def test_provider_from_string(self):
        """测试从字符串创建提供商枚举"""
        self.assertEqual(ModelProvider.from_string("openai"), ModelProvider.OPENAI)
        self.assertEqual(ModelProvider.from_string("deepseek"), ModelProvider.DEEPSEEK)
        self.assertEqual(ModelProvider.from_string("doubao"), ModelProvider.DOUBAN)
        
        # 测试大小写不敏感
        self.assertEqual(ModelProvider.from_string("OpenAI"), ModelProvider.OPENAI)
    
    def test_provider_invalid_value(self):
        """测试无效的提供商值"""
        provider = ModelProvider.from_string("invalid_provider")
        self.assertEqual(provider, ModelProvider.OTHER)
    
    def test_provider_display_name(self):
        """测试提供商显示名称"""
        self.assertEqual(ModelProvider.get_display_name("openai"), "OpenAI")
        self.assertEqual(ModelProvider.get_display_name("deepseek"), "DeepSeek")
        self.assertEqual(ModelProvider.get_display_name("doubao"), "豆包")
        self.assertEqual(ModelProvider.get_display_name("baidu"), "百度文心")


class TestModelConfig(unittest.TestCase):
    """测试模型配置数据类"""
    
    def test_model_config_creation(self):
        """测试模型配置创建"""
        model = ModelConfig(
            name="gpt-3.5-turbo",
            display_name="GPT-3.5-Turbo",
            provider="openai",
            base_url="https://api.openai.com/v1",
            api_key="sk-test123",
            input_price=0.0015,
            output_price=0.002
        )
        
        self.assertEqual(model.name, "gpt-3.5-turbo")
        self.assertEqual(model.display_name, "GPT-3.5-Turbo")
        self.assertEqual(model.provider, "openai")
        self.assertEqual(model.base_url, "https://api.openai.com/v1")
        self.assertEqual(model.input_price, 0.0015)
        self.assertEqual(model.output_price, 0.002)
        self.assertEqual(model.status, 1)
        self.assertEqual(model.sort, 10)
    
    def test_model_config_default_values(self):
        """测试默认配置值"""
        model = ModelConfig(
            name="test-model",
            base_url="https://api.test.com/v1",
            api_key="sk-test"
        )
        
        self.assertEqual(model.display_name, "test-model")  # 默认使用name
        self.assertEqual(model.provider, "openai")  # 默认provider
        self.assertEqual(model.input_price, 0.0)  # 默认价格
        self.assertEqual(model.output_price, 0.0)
        self.assertEqual(model.status, 1)  # 默认启用
        self.assertEqual(model.sort, 10)
        self.assertEqual(model.remark, "")
        self.assertEqual(model.version, 1)
    
    def test_model_config_type_conversion(self):
        """测试类型转换"""
        model = ModelConfig(
            name="test",
            base_url="https://api.test.com/v1/",
            api_key="sk-test",
            input_price="0.0015",  # 字符串转浮点数
            output_price="0.002",
            status="1",  # 字符串转整数
            sort="10"
        )
        
        self.assertIsInstance(model.input_price, float)
        self.assertIsInstance(model.output_price, float)
        self.assertIsInstance(model.status, int)
        self.assertIsInstance(model.sort, int)
        
        # URL末尾斜杠应被去除
        self.assertEqual(model.base_url, "https://api.test.com/v1")
    
    def test_model_config_validation_valid(self):
        """测试有效配置的验证"""
        model = ModelConfig(
            name="valid-model",
            base_url="https://api.test.com/v1",
            api_key="sk-valid123456"
        )
        
        errors = model.validate()
        self.assertEqual(len(errors), 0)
    
    def test_model_config_validation_empty_name(self):
        """测试空名称验证"""
        model = ModelConfig(
            name="",
            base_url="https://api.test.com/v1",
            api_key="sk-test"
        )
        
        errors = model.validate()
        self.assertIn("模型名称不能为空", errors)
    
    def test_model_config_validation_invalid_url(self):
        """测试无效URL验证"""
        model = ModelConfig(
            name="test",
            base_url="invalid-url",
            api_key="sk-test"
        )
        
        errors = model.validate()
        self.assertTrue(any("API地址格式不正确" in e for e in errors))
    
    def test_model_config_validation_negative_price(self):
        """测试负价格验证"""
        model = ModelConfig(
            name="test",
            base_url="https://api.test.com/v1",
            api_key="sk-test",
            input_price=-0.001,
            output_price=-0.002
        )
        
        errors = model.validate()
        self.assertTrue(any("输入价格不能为负数" in e for e in errors))
        self.assertTrue(any("输出价格不能为负数" in e for e in errors))
    
    def test_model_config_validation_invalid_status(self):
        """测试无效状态值验证"""
        model = ModelConfig(
            name="test",
            base_url="https://api.test.com/v1",
            api_key="sk-test",
            status=2
        )
        
        errors = model.validate()
        self.assertTrue(any("状态值只能是0（禁用）或1（启用）" in e for e in errors))
    
    def test_model_config_to_dict(self):
        """测试转换为字典"""
        model = ModelConfig(
            name="test",
            base_url="https://api.test.com/v1",
            api_key="sk-test",
            input_price=0.001,
            output_price=0.002
        )
        
        data = model.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data['name'], "test")
        self.assertEqual(data['base_url'], "https://api.test.com/v1")
        self.assertEqual(data['input_price'], 0.001)
    
    def test_model_config_from_dict(self):
        """测试从字典创建"""
        data = {
            'name': 'test',
            'base_url': 'https://api.test.com/v1',
            'api_key': 'sk-test',
            'input_price': 0.001,
            'output_price': 0.002
        }
        
        model = ModelConfig.from_dict(data)
        
        self.assertEqual(model.name, 'test')
        self.assertEqual(model.base_url, 'https://api.test.com/v1')
        self.assertEqual(model.input_price, 0.001)


class TestEnvironmentConfig(unittest.TestCase):
    """测试环境配置数据类"""
    
    def test_environment_config_creation(self):
        """测试环境配置创建"""
        env_config = EnvironmentConfig(
            env=Environment.DEVELOPMENT,
            debug=True,
            log_level="INFO",
            rate_limit=60
        )
        
        self.assertEqual(env_config.env, Environment.DEVELOPMENT)
        self.assertTrue(env_config.debug)
        self.assertEqual(env_config.log_level, "INFO")
        self.assertEqual(env_config.rate_limit, 60)
    
    def test_environment_config_from_string(self):
        """测试从字符串创建环境配置"""
        env_config = EnvironmentConfig(env="production")
        
        self.assertEqual(env_config.env, Environment.PRODUCTION)
        # 生产环境默认关闭debug模式
        self.assertFalse(env_config.debug)
        
        # 测试开发环境
        dev_config = EnvironmentConfig(env="development")
        self.assertEqual(dev_config.env, Environment.DEVELOPMENT)
        self.assertTrue(dev_config.debug)
    
    def test_environment_config_validation(self):
        """测试环境配置验证"""
        # 有效配置
        env_config = EnvironmentConfig(
            env=Environment.PRODUCTION,
            log_level="WARNING",
            rate_limit=30
        )
        
        errors = env_config.validate()
        self.assertEqual(len(errors), 0)
        
        # 无效日志级别
        env_config = EnvironmentConfig(log_level="INVALID")
        errors = env_config.validate()
        self.assertTrue(any("无效的日志级别" in e for e in errors))
        
        # 无效速率限制
        env_config = EnvironmentConfig(rate_limit=0)
        errors = env_config.validate()
        self.assertTrue(any("速率限制必须大于0" in e for e in errors))


class TestConfigManager(unittest.TestCase):
    """测试配置管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = ConfigManager()
        # 清空默认模型，确保测试独立
        self.manager._models.clear()
    
    def test_config_manager_creation(self):
        """测试配置管理器创建"""
        self.assertIsInstance(self.manager.current_env, Environment)
        self.assertIsNotNone(self.manager.env_config)
    
    def test_add_model(self):
        """测试添加模型"""
        model_data = {
            'name': 'test-model',
            'base_url': 'https://api.test.com/v1',
            'api_key': 'sk-test123456'
        }
        
        result = self.manager.add_model(model_data)
        self.assertTrue(result)
        
        # 验证模型已添加
        model = self.manager.get_model('test-model')
        self.assertIsNotNone(model)
        self.assertEqual(model.name, 'test-model')
    
    def test_add_model_validation(self):
        """测试添加无效模型"""
        model_data = {
            'name': '',
            'base_url': 'invalid',
            'api_key': 'sk-test'
        }
        
        result = self.manager.add_model(model_data, validate=True)
        self.assertFalse(result)
    
    def test_remove_model(self):
        """测试移除模型"""
        # 先添加
        self.manager.add_model({
            'name': 'temp-model',
            'base_url': 'https://api.test.com',
            'api_key': 'sk-test'
        })
        
        # 再移除
        result = self.manager.remove_model('temp-model')
        self.assertTrue(result)
        
        # 验证已移除
        model = self.manager.get_model('temp-model')
        self.assertIsNone(model)
    
    def test_get_models(self):
        """测试获取所有模型"""
        # 添加多个模型
        self.manager.add_model({
            'name': 'model-a',
            'base_url': 'https://api.a.com',
            'api_key': 'sk-a'
        }, validate=False)
        
        self.manager.add_model({
            'name': 'model-b',
            'base_url': 'https://api.b.com',
            'api_key': 'sk-b',
            'sort': 5
        }, validate=False)
        
        models = self.manager.get_models()
        self.assertGreaterEqual(len(models), 2)
        
        # 验证排序
        names = [m.name for m in models]
        self.assertIn('model-a', names)
        self.assertIn('model-b', names)
    
    def test_get_models_enabled_only(self):
        """测试只获取启用的模型"""
        self.manager.add_model({
            'name': 'enabled-model',
            'base_url': 'https://api.test.com',
            'api_key': 'sk-test',
            'status': 1
        }, validate=False)
        
        self.manager.add_model({
            'name': 'disabled-model',
            'base_url': 'https://api.test.com',
            'api_key': 'sk-test',
            'status': 0
        }, validate=False)
        
        enabled_models = self.manager.get_models(enabled_only=True)
        enabled_names = [m.name for m in enabled_models]
        
        self.assertIn('enabled-model', enabled_names)
        self.assertNotIn('disabled-model', enabled_names)
    
    def test_validate_all(self):
        """测试验证所有配置"""
        # 添加有效模型
        self.manager.add_model({
            'name': 'valid-model',
            'base_url': 'https://api.test.com',
            'api_key': 'sk-test123456'
        }, validate=False)
        
        # 添加无效模型
        self.manager.add_model({
            'name': 'invalid-model',
            'base_url': 'invalid-url',
            'api_key': 'sk-test'
        }, validate=False)
        
        results = self.manager.validate_all()
        
        self.assertIn('model:invalid-model', results)
        self.assertNotIn('model:valid-model', results)
    
    def test_to_dict(self):
        """测试导出配置为字典"""
        data = self.manager.to_dict()
        
        self.assertIn('environment', data)
        self.assertIn('models', data)
        self.assertIsInstance(data['models'], dict)


class TestHelperFunctions(unittest.TestCase):
    """测试辅助函数"""
    
    def test_get_provider_name(self):
        """测试获取提供商名称"""
        self.assertEqual(get_provider_name("openai"), "OpenAI")
        self.assertEqual(get_provider_name("deepseek"), "DeepSeek")
        self.assertEqual(get_provider_name("doubao"), "豆包")
        self.assertEqual(get_provider_name("unknown"), "unknown")
    
    def test_get_all_providers(self):
        """测试获取所有提供商"""
        providers = get_all_providers()
        
        self.assertIsInstance(providers, list)
        self.assertGreater(len(providers), 0)
        
        # 验证结构
        for provider in providers:
            self.assertIn('value', provider)
            self.assertIn('label', provider)
    
    def test_validate_model_config(self):
        """测试验证模型配置函数"""
        # 有效配置
        valid, errors = validate_model_config({
            'name': 'test',
            'base_url': 'https://api.test.com',
            'api_key': 'sk-test123456'
        })
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
        
        # 无效配置
        invalid, errors = validate_model_config({
            'name': '',
            'base_url': 'invalid'
        })
        self.assertFalse(invalid)
        self.assertGreater(len(errors), 0)


class TestConfigIntegration(unittest.TestCase):
    """配置模块集成测试"""
    
    def test_full_config_workflow(self):
        """测试完整的配置工作流程"""
        # 1. 创建配置管理器
        manager = ConfigManager()
        # 清空默认模型，确保测试独立
        manager._models.clear()
        
        # 2. 添加模型
        models_to_add = [
            {
                'name': 'gpt-4',
                'display_name': 'GPT-4',
                'provider': 'openai',
                'base_url': 'https://api.openai.com/v1',
                'api_key': 'sk-test-openai',
                'input_price': 0.03,
                'output_price': 0.06,
                'status': 1,
                'sort': 10
            },
            {
                'name': 'deepseek-v2',
                'display_name': 'DeepSeek V2',
                'provider': 'deepseek',
                'base_url': 'https://api.deepseek.com/v1',
                'api_key': 'sk-test-deepseek',
                'input_price': 0.001,
                'output_price': 0.002,
                'status': 1,
                'sort': 20
            }
        ]
        
        for model_data in models_to_add:
            success = manager.add_model(model_data)
            self.assertTrue(success)
        
        # 3. 验证所有配置
        validation_results = manager.validate_all()
        # 不应该有验证错误
        model_errors = {k: v for k, v in validation_results.items() if k.startswith('model:')}
        self.assertEqual(len(model_errors), 0)
        
        # 4. 获取配置
        gpt4 = manager.get_model('gpt-4')
        self.assertIsNotNone(gpt4)
        self.assertEqual(gpt4.display_name, 'GPT-4')
        self.assertEqual(gpt4.input_price, 0.03)
        
        # 5. 获取所有启用的模型
        enabled_models = manager.get_models(enabled_only=True)
        self.assertGreaterEqual(len(enabled_models), 2)
        
        # 6. 导出配置
        config_dict = manager.to_dict()
        self.assertIn('models', config_dict)
        self.assertIn('gpt-4', config_dict['models'])


if __name__ == '__main__':
    # 运行测试
    print("=" * 60)
    print("运行模型配置单元测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestEnvironment))
    suite.addTests(loader.loadTestsFromTestCase(TestModelProvider))
    suite.addTests(loader.loadTestsFromTestCase(TestModelConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestEnvironmentConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestHelperFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
        print(f"失败: {len(result.failures)}")
        print(f"错误: {len(result.errors)}")
    print("=" * 60)
