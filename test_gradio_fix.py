#!/usr/bin/env python3
"""测试 Gradio 返回值格式"""

import json

# 模拟成功时的返回值
success_return = (
    "✅ 执行完成",
    100,
    "日志内容",
    {"output": "test"},  # final_output - JSON
    {"stats": "test"},   # exec_stats - JSON
    [["step1", "agent1", "input1", "output1"]],  # trajectory_list - Dataframe
    {"info": "Select a step"},  # step_detail - JSON
    "Prompt here",  # step_prompt - Textbox
    "Response here",  # step_response - Textbox
    "Flow HTML"  # flow_visualization - Markdown
)

# 模拟错误时的返回值
error_return = (
    "❌ 执行失败",
    0,
    "错误日志",
    {"error": "Execution failed"},  # final_output - JSON
    {"status": "failed"},  # exec_stats - JSON
    [],  # trajectory_list - Dataframe
    {"error": "Error details"},  # step_detail - JSON
    "Error details",  # step_prompt - Textbox
    "Error occurred",  # step_response - Textbox
    "Error in flow"  # flow_visualization - Markdown
)

print("成功返回值数量:", len(success_return))
print("错误返回值数量:", len(error_return))

# 检查每个值的类型
print("\n成功返回值类型:")
for i, val in enumerate(success_return):
    print(f"  [{i}] {type(val).__name__}: {str(val)[:50]}")

print("\n错误返回值类型:")
for i, val in enumerate(error_return):
    print(f"  [{i}] {type(val).__name__}: {str(val)[:50]}")

# 测试 JSON 序列化
print("\n测试 JSON 序列化:")
for i, val in enumerate(success_return):
    if isinstance(val, (dict, list)):
        try:
            json_str = json.dumps(val)
            print(f"  [{i}] ✓ JSON 序列化成功")
        except Exception as e:
            print(f"  [{i}] ✗ JSON 序列化失败: {e}")
