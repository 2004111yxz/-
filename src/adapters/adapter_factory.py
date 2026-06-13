from typing import Dict, Optional, Type
from .base_adapter import BaseModelAdapter
from .openai_adapter import OpenAIAdapter
from .deepseek_adapter import DeepSeekAdapter
from .doubao_adapter import DoubaoAdapter

ADAPTER_MAP: Dict[str, Type[BaseModelAdapter]] = {
    'openai': OpenAIAdapter,
    'deepseek': DeepSeekAdapter,
    'doubao': DoubaoAdapter,
}

class AdapterFactory:
    @staticmethod
    def get_adapter(model_config: Dict) -> BaseModelAdapter:
        model_name = model_config.get('name', '')
        
        if model_name.startswith('gpt-'):
            return OpenAIAdapter(model_config)
        elif model_name.startswith('deepseek-'):
            return DeepSeekAdapter(model_config)
        elif model_name.startswith('doubao-') or model_name == 'doubao':
            return DoubaoAdapter(model_config)
        
        for adapter_name, adapter_class in ADAPTER_MAP.items():
            if adapter_name in model_name.lower():
                return adapter_class(model_config)
        
        return OpenAIAdapter(model_config)
    
    @staticmethod
    def register_adapter(adapter_name: str, adapter_class: Type[BaseModelAdapter]):
        ADAPTER_MAP[adapter_name] = adapter_class
