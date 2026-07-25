import os
import yaml
import httpx
from openai import OpenAI
from llm.base import BaseLLM

class QwenLLM(BaseLLM):
    def __init__(self, model_name: str = None):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        config_path = os.path.join(project_root, "configs", "api_config.yaml")

        if not os.path.exists(config_path):
            config_path = os.path.join(current_dir, "../configs/api_config.yaml")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        cfg = config['qwen']
        self.model = model_name or cfg['model']
        api_key = cfg['api_key']
        base_url = cfg['base_url']

        # 【优化】显式创建 httpx 客户端并指定 Headers
        http_client = httpx.Client(
            follow_redirects=True,
            timeout=60.0,
            headers={
                "User-Agent": "MultiAgentBuilder/1.0",
                "Accept": "application/json"
            }
        )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client
        )

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            if "ascii" in str(e).lower():
                print("❌ 检测到编码错误。请检查系统环境变量是否包含中文。")
            raise e