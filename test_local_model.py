#!/usr/bin/env python3
"""测试本地模型加载"""

from llm.model_factory import ModelFactory

# 测试模型工厂的路由
print("测试模型路由:")
test_models = [
    'gpt-4o',
    'Qwen2.5-32B-Instruct',
    'Qwen/Qwen2.5-0.5B-Instruct',
    './models/qwen-7b',
]

for model in test_models:
    model_type = ModelFactory.get_model_type(model)
    print(f'  {model} -> {model_type}')

print("\n测试加载本地模型 (Qwen2.5-0.5B-Instruct):")
print("(首次运行会从 HuggingFace 下载模型，约 1GB，请耐心等待...)")

try:
    llm = ModelFactory.create_llm('Qwen/Qwen2.5-0.5B-Instruct')
    print(f"模型类型: {type(llm).__name__}")
    
    # 测试生成
    prompt = "你好，请用一句话介绍自己。"
    print(f"\n提示: {prompt}")
    response = llm.generate(prompt, max_tokens=50)
    print(f"响应: {response}")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
