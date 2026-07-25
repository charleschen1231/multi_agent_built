import os
import yaml
import httpx  # <--- 必须导入 httpx
from openai import OpenAI
from llm.base import BaseLLM

class OpenAILLM(BaseLLM):
    def __init__(self, model_name: str = None):
        # 保持与你 QwenLLM 一致的路径查找逻辑，确保稳健
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, "configs", "api_config.yaml")

        if not os.path.exists(config_path):
            config_path = os.path.join(current_dir, "../configs/api_config.yaml")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        cfg = config['openai']
        self.model = model_name or cfg['model']
        api_key = cfg['api_key']
        base_url = cfg['base_url']

        # 【核心修复】显式创建 httpx 客户端
        # 这能防止 openai 库自动创建默认客户端时，因读取系统环境变量（可能含中文）导致 Header 编码错误
        http_client = httpx.Client(
            follow_redirects=True,
            timeout=60.0,
            # 可选：强制指定纯 ASCII 的 User-Agent，彻底杜绝隐患
            headers={
                "User-Agent": "MultiAgentBuilder/1.0",
                "Accept": "application/json"
            }
        )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client  # <--- 传入自定义客户端
        )

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content