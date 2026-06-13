from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional

class BaseModelAdapter(ABC):
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.base_url = model_config.get('base_url', '')
        self.api_key = model_config.get('api_key', '')
        self.model_name = model_config.get('name', '')
        self.input_price = model_config.get('input_price', 0)
        self.output_price = model_config.get('output_price', 0)
    
    @abstractmethod
    def format_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def format_response(self, response: Any, streaming: bool = False) -> Any:
        pass
    
    @abstractmethod
    def parse_usage(self, response: Any) -> Dict[str, int]:
        pass
    
    @abstractmethod
    def generate(self, body: Dict[str, Any]) -> Any:
        pass
    
    @abstractmethod
    def generate_stream(self, body: Dict[str, Any]) -> Generator[str, None, None]:
        pass
    
    def get_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens / 1000) * self.input_price + (completion_tokens / 1000) * self.output_price
