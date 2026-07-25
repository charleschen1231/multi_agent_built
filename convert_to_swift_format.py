#!/usr/bin/env python
"""将数据集转换为 ms-swift 格式"""
import json
import sys

def convert_to_swift_format(input_file, output_file):
    """
    将我们的数据集格式转换为 ms-swift 格式
    
    输入格式:
    {
        "user_request": "...",
        "plan_gt": "...",
        "solution_gt": "...",
        "final_answer_gt": "..."
    }
    
    输出格式 (ms-swift):
    {
        "messages": [
            {"role": "system", "content": "你是一个数学解题助手..."},
            {"role": "user", "content": "计算 15 + 27"},
            {"role": "assistant", "content": "步骤1：...\n步骤2：...\n最终答案：42"}
        ]
    }
    """
    
    system_prompt = """你是一个数学解题助手。请按照以下步骤解决数学问题：
1. 理解问题
2. 制定解题计划
3. 执行计算
4. 验证结果
5. 给出最终答案

请详细展示你的思考过程。"""
    
    converted_data = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                
                # 构建 messages
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data.get('user_request', '')},
                    {"role": "assistant", "content": f"""解题计划：
{data.get('plan_gt', '')}

详细解答：
{data.get('solution_gt', '')}

最终答案：{data.get('final_answer_gt', '')}"""}
                ]
                
                converted_data.append({"messages": messages})
                
            except json.JSONDecodeError as e:
                print(f"Error parsing line: {e}")
                continue
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in converted_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"Converted {len(converted_data)} records")
    print(f"Output saved to: {output_file}")
    
    # 显示示例
    if converted_data:
        print("\n示例数据:")
        print(json.dumps(converted_data[0], ensure_ascii=False, indent=2))

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "test_sft_dataset.jsonl"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "test_sft_dataset_swift.jsonl"
    
    convert_to_swift_format(input_file, output_file)
