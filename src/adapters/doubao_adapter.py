import json
import requests
from typing import Any, Dict, Generator
from .base_adapter import BaseModelAdapter

class DoubaoAdapter(BaseModelAdapter):
    def format_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        formatted = {
            'model': self.model_name,
            'messages': body.get('messages', []),
            'temperature': body.get('temperature', 0.7),
            'max_tokens': body.get('max_tokens', 2048),
            'stream': body.get('stream', False)
        }
        return formatted
    
    def format_response(self, response: Any, streaming: bool = False) -> Any:
        if streaming:
            return response
        
        if isinstance(response, dict):
            choices = response.get('result', '')
            return {
                'id': response.get('id', ''),
                'object': 'chat.completion',
                'created': int(response.get('created', 0)),
                'model': self.model_name,
                'choices': [{
                    'index': 0,
                    'message': {
                        'role': 'assistant',
                        'content': choices
                    },
                    'finish_reason': 'stop'
                }],
                'usage': {
                    'prompt_tokens': response.get('usage', {}).get('prompt_tokens', 0),
                    'completion_tokens': response.get('usage', {}).get('completion_tokens', 0),
                    'total_tokens': response.get('usage', {}).get('total_tokens', 0)
                }
            }
        return response
    
    def parse_usage(self, response: Any) -> Dict[str, int]:
        if isinstance(response, dict):
            usage = response.get('usage', {})
            return {
                'prompt_tokens': usage.get('prompt_tokens', 0),
                'completion_tokens': usage.get('completion_tokens', 0)
            }
        return {'prompt_tokens': 0, 'completion_tokens': 0}
    
    def generate(self, body: Dict[str, Any]) -> Any:
        headers = {
            'Authorization': f"Bearer {self.api_key}",
            'Content-Type': 'application/json'
        }
        
        formatted_body = self.format_request(body)
        formatted_body['stream'] = False
        
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=formatted_body,
            headers=headers,
            timeout=120
        )
        
        resp.raise_for_status()
        return self.format_response(resp.json())
    
    def generate_stream(self, body: Dict[str, Any]) -> Generator[str, None, None]:
        headers = {
            'Authorization': f"Bearer {self.api_key}",
            'Content-Type': 'application/json'
        }
        
        formatted_body = self.format_request(body)
        formatted_body['stream'] = True
        
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=formatted_body,
            headers=headers,
            stream=True,
            timeout=120
        )
        
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                line_text = line.decode('utf-8', errors='ignore').strip()
                if line_text.startswith('data: '):
                    data_str = line_text[6:].strip()
                    if data_str == '[DONE]':
                        yield 'data: [DONE]\n\n'
                        break
                    try:
                        data = json.loads(data_str)
                        formatted_data = {
                            'id': data.get('id', ''),
                            'object': 'chat.completion.chunk',
                            'created': data.get('created', 0),
                            'model': self.model_name,
                            'choices': [{
                                'index': 0,
                                'delta': {
                                    'content': data.get('result', '') if 'result' in data else ''
                                },
                                'finish_reason': None
                            }]
                        }
                        yield f"data: {json.dumps(formatted_data)}\n\n"
                    except json.JSONDecodeError:
                        yield f'{line_text}\n\n'
