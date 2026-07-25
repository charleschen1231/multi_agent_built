#!/usr/bin/env python
"""转换 test_sft_dataset.jsonl 为 ms-swift 格式"""
import json

# 读取旧格式数据
with open('test_sft_dataset.jsonl', 'r', encoding='utf-8') as f:
    old_data = [json.loads(line) for line in f if line.strip()]

# 转换为新格式
new_data = []
system_prompt = "你是一个数学解题助手。请按照以下步骤解决数学问题：\n1. 理解问题\n2. 制定解题计划\n3. 执行计算\n4. 验证结果\n5. 给出最终答案\n\n请详细展示你的思考过程。"

for item in old_data:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": item.get('user_request', '')},
        {"role": "assistant", "content": f"{item.get('plan_gt', '')}\n\n{item.get('solution_gt', '')}\n\n最终答案：{item.get('final_answer_gt', '')}"}
    ]
    new_data.append({"messages": messages})

# 保存为新格式
with open('test_sft_dataset.jsonl', 'w', encoding='utf-8') as f:
    for item in new_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"✓ 已转换 {len(new_data)} 条数据为 ms-swift 格式")
print("示例数据:")
print(json.dumps(new_data[0], ensure_ascii=False, indent=2))
