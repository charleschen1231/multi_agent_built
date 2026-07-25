# llm/model_factory.py
"""模型工厂 - 根据模型名称自动选择对应的 LLM 类"""

from typing import Optional
from llm.base import BaseLLM
from llm.openai_llm import OpenAILLM
from llm.qwen_llm import QwenLLM
from llm.local_llm import LocalLLM


class ModelFactory:
    """模型工厂类"""
    
    # Qwen 模型名称映射（从配置名称到阿里云实际模型名称）
    QWEN_MODEL_MAPPING = {
        'qwen2.5-32b-instruct': 'qwen-plus',
        'qwen2.5-7b-instruct': 'qwen-turbo',
        'qwen2.5-0.5b-instruct': 'qwen-turbo',
        'qwen2.5-14b-instruct': 'qwen-plus',
        'qwen2.5-72b-instruct': 'qwen-max',
    }
    
    @staticmethod
    def map_qwen_model(model_name: str) -> str:
        """将配置中的 Qwen 模型名称映射到阿里云实际支持的模型名称"""
        model_lower = model_name.lower()
        # 尝试精确匹配
        if model_lower in ModelFactory.QWEN_MODEL_MAPPING:
            return ModelFactory.QWEN_MODEL_MAPPING[model_lower]
        # 尝试模糊匹配
        for key, value in ModelFactory.QWEN_MODEL_MAPPING.items():
            if key in model_lower or model_lower in key:
                return value
        # 默认使用 qwen-plus
        return 'qwen-plus'
    
    @staticmethod
    def create_llm(model_name: str) -> BaseLLM:
        """
        根据模型名称创建对应的 LLM 实例
        
        Args:
            model_name: 模型名称或路径，如 "gpt-4o", "Qwen2.5-32B-Instruct"
            
        Returns:
            BaseLLM: 对应的 LLM 实例
        """
        model_name_lower = model_name.lower()
        
        # OpenAI 模型
        if any(name in model_name_lower for name in ['gpt-4', 'gpt-3.5', 'gpt4', 'gpt3.5']):
            return OpenAILLM(model_name)
        
        # Qwen 模型 - 检查是否是本地模型路径或需要映射到 API
        elif any(name in model_name_lower for name in ['qwen', '通义千问']):
            # 如果是完整路径（包含 / 或 \\），使用本地加载
            if '/' in model_name or '\\' in model_name or model_name.startswith('.'):
                return LocalLLM(model_name)
            # 否则映射到阿里云 API
            else:
                mapped_model = ModelFactory.map_qwen_model(model_name)
                return QwenLLM(mapped_model)
        
        # 本地模型路径（包含 / 或 \\）
        elif '/' in model_name or '\\' in model_name or model_name.startswith('.'):
            return LocalLLM(model_name)
        
        # 默认使用 OpenAI（兼容 GPT-4o）
        else:
            # 如果无法识别模型类型，默认使用 OpenAI
            # 因为许多模型都提供 OpenAI 兼容的 API 接口
            return OpenAILLM(model_name)
    
    @staticmethod
    def get_model_type(model_name: str) -> str:
        """
        获取模型类型
        
        Args:
            model_name: 模型名称
            
        Returns:
            str: 模型类型 (openai/qwen/unknown)
        """
        model_name_lower = model_name.lower()
        
        if any(name in model_name_lower for name in ['gpt-4', 'gpt-3.5', 'gpt4', 'gpt3.5']):
            return 'openai'
        elif any(name in model_name_lower for name in ['qwen', '通义千问']):
            return 'qwen'
        else:
            return 'unknown'
