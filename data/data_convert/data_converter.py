import json
import os

# 获取当前脚本所在的目录 (即 data/data_convert/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (即 multi_agent_built/) -> 向上跳两级
project_root = os.path.dirname(os.path.dirname(current_dir))


def convert_data(input_file, target_framework='swift'):
    # 如果输入的是相对路径，拼接为绝对路径
    if not os.path.isabs(input_file):
        input_file = os.path.join(project_root, input_file)

    output_filename = ""
    data_list = []

    print(f"📂 正在读取数据：{input_file}")

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"找不到文件：{input_file}\n请检查路径是否正确。当前项目根目录：{project_root}")

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # 提取通用字段
            user_prompt = ""
            assistant_response = ""

            if 'messages' in record:
                for msg in record['messages']:
                    if msg['role'] == 'user':
                        user_prompt = msg['content']
                    elif msg['role'] == 'assistant':
                        assistant_response = msg['content']

            # 兼容直接就是 query/response 的情况
            if not user_prompt and 'query' in record:
                user_prompt = record['query']
            if not assistant_response and 'response' in record:
                assistant_response = record['response']

            if not user_prompt:
                continue

            # 根据目标框架格式化
            if target_framework == 'swift_sft':
                # 保留完整的 messages 格式（SWIFT 需要这个）
                data_list.append({
                    "messages": record.get('messages', []),
                    "loss_weight": record.get('loss_weight', 1.0)
                })
                output_filename = "swift_sft_format.jsonl"

            elif target_framework == 'swift_dpo':
                # 暂时用 response 作为 chosen，构造一个假的 rejected
                data_list.append(
                    {"query": user_prompt, "chosen": assistant_response, "rejected": "这是一个错误的回答。"})
                output_filename = "swift_dpo_format.jsonl"

            elif target_framework == 'verl_grpo':
                # VERL GRPO 只需要 prompt
                data_list.append({"prompt": user_prompt})
                output_filename = "verl_grpo_format.jsonl"

    # 输出路径：统一放到 data/rollouts/ 目录下
    output_dir = os.path.join(project_root, 'data', 'rollouts')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in data_list:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"✅ 已为 [{target_framework}] 生成数据：{output_path}, 共 {len(data_list)} 条")
    return output_path


if __name__ == "__main__":
    # 相对路径：相对于项目根目录
    raw_data_rel_path = "data/rollouts/sft_data_*.jsonl"

    print(f"🚀 开始转换数据... (源文件：{raw_data_rel_path})")

    try:
        # 一次性生成所有需要的格式
        convert_data(raw_data_rel_path, 'swift_sft')
        convert_data(raw_data_rel_path, 'swift_dpo')
        convert_data(raw_data_rel_path, 'verl_grpo')
        print("\n🎉 所有数据转换完成！")
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
