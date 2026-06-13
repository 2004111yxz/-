import json
import requests
from typing import Any, Dict, Generator, Optional
from .base_adapter import BaseModelAdapter

class OpenAIAdapter(BaseModelAdapter):
    def format_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return body
    
    def format_response(self, response: Any, streaming: bool = False) -> Any:
        return response
    
    def parse_usage(self, response: Any) -> Dict[str, int]:
        if isinstance(response, dict) and 'usage' in response:
            return {
                'prompt_tokens': response['usage'].get('prompt_tokens', 0),
                'completion_tokens': response['usage'].get('completion_tokens', 0)
            }
        return {'prompt_tokens': 0, 'completion_tokens': 0}
    
    def generate(self, body: Dict[str, Any]) -> Any:
        headers = {
            'Authorization': f"Bearer {self.api_key}",
            'Content-Type': 'application/json'
        }
        
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json={**body, 'stream': False},
            headers=headers,
            timeout=120
        )
        
        resp.raise_for_status()
        return resp.json()
    
    def generate_stream(self, body: Dict[str, Any]) -> Generator[str, None, None]:
        headers = {
            'Authorization': f"Bearer {self.api_key}",
            'Content-Type': 'application/json'
        }
        
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json={**body, 'stream': True},
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
                    yield f'{line_text}\n\n'
