# llm/local_llm.py
"""本地模型加载 - 使用 Transformers 加载开源模型"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from llm.base import BaseLLM


class LocalLLM(BaseLLM):
    """本地 LLM 实现 - 使用 Transformers 加载模型"""
    
    # 模型缓存，避免重复加载
    _model_cache = {}
    _tokenizer_cache = {}
    
    def __init__(self, model_name: str, device: str = None):
        """
        初始化本地模型
        
        Args:
            model_name: 模型名称或路径，如 "Qwen/Qwen2.5-0.5B-Instruct"
            device: 运行设备，默认自动选择 (cuda/cpu)
        """
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载模型和 tokenizer
        self._load_model()
    
    def _load_model(self):
        """加载模型和 tokenizer（使用缓存）"""
        if self.model_name not in LocalLLM._model_cache:
            print(f"正在加载模型: {self.model_name}...")
            print(f"使用设备: {self.device}")
            
            # 加载 tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                padding_side="left"
            )
            
            # 设置 pad_token（如果未设置）
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # 加载模型
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                trust_remote_code=True
            )
            
            if self.device == "cpu":
                model = model.to(self.device)
            
            # 缓存模型
            LocalLLM._model_cache[self.model_name] = model
            LocalLLM._tokenizer_cache[self.model_name] = tokenizer
            
            print(f"模型加载完成!")
        
        self.model = LocalLLM._model_cache[self.model_name]
        self.tokenizer = LocalLLM._tokenizer_cache[self.model_name]
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 512) -> str:
        """
        生成文本
        
        Args:
            prompt: 输入提示
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            
        Returns:
            str: 生成的文本
        """
        # 构建消息格式（适用于 Instruct 模型）
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # 应用 chat template
        if hasattr(self.tokenizer, 'apply_chat_template'):
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            text = prompt
        
        # 编码输入
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        
        # 生成
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # 解码输出（只取生成的部分）
        generated_ids = [
            output_ids[len(input_ids):] 
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        
        return response.strip()
    
    @staticmethod
    def clear_cache():
        """清除模型缓存，释放内存"""
        LocalLLM._model_cache.clear()
        LocalLLM._tokenizer_cache.clear()
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
