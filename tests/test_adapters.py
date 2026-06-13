import unittest
from unittest.mock import Mock, patch
from src.adapters.openai_adapter import OpenAIAdapter
from src.adapters.deepseek_adapter import DeepSeekAdapter

class TestOpenAIAdapter(unittest.TestCase):
    def setUp(self):
        self.model_config = {
            'name': 'gpt-3.5-turbo',
            'base_url': 'https://api.openai.com/v1',
            'api_key': 'sk-test-key',
            'input_price': 0.0015,
            'output_price': 0.002
        }
        self.adapter = OpenAIAdapter(self.model_config)
    
    def test_format_request(self):
        body = {'model': 'gpt-3.5-turbo', 'messages': [{'role': 'user', 'content': 'Hello'}]}
        result = self.adapter.format_request(body)
        self.assertEqual(result, body)
    
    def test_parse_usage(self):
        response = {
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 20
            }
        }
        usage = self.adapter.parse_usage(response)
        self.assertEqual(usage['prompt_tokens'], 10)
        self.assertEqual(usage['completion_tokens'], 20)
    
    def test_get_cost(self):
        cost = self.adapter.get_cost(1000, 1000)
        self.assertEqual(cost, 0.0035)

class TestDeepSeekAdapter(unittest.TestCase):
    def setUp(self):
        self.model_config = {
            'name': 'deepseek-chat',
            'base_url': 'https://api.deepseek.com/v1',
            'api_key': 'sk-deepseek-key',
            'input_price': 0.0005,
            'output_price': 0.0015
        }
        self.adapter = DeepSeekAdapter(self.model_config)
    
    def test_get_cost(self):
        cost = self.adapter.get_cost(1000, 1000)
        self.assertEqual(cost, 0.002)

if __name__ == '__main__':
    unittest.main()
