#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试说明文档中的第一个 JSON 示例 (plan -> inference -> check)
"""

import json
from core.json_validator import JSONValidator
from core.trajectory_generator import TrajectoryGenerator
from spec.system_spec import SystemSpec
from database.db_manager import DatabaseManager

# 说明文档中的第一个 JSON 示例 (plan -> inference -> check)
json_config = [
  {
    "agent_id": "planner",
    "model": {
      "name_or_path": "Qwen2.5-32B-Instruct"
    },
    "instruction_prompt": {
      "instruction": "你是 Planner Agent：把用户需求拆成可执行的步骤计划。",
      "prompt_template": "用户需求：{{input.user_request}}\n请输出 JSON 格式的 plan。"
    },
    "input": [
      { "from": "user", "key": "user_request" }
    ],
    "output": [
      { "key": "plan", "to": [ { "agent": "infer", "as": "plan" } ] }
    ]
  },
  {
    "agent_id": "infer",
    "model": {
      "name_or_path": "Qwen2.5-32B-Instruct"
    },
    "instruction_prompt": {
      "instruction": "你是 Inference Agent：按照 plan 解决问题并生成答案。",
      "prompt_template": "Plan：{{input.plan}}\n问题：{{input.user_request}}\n请给出答案："
    },
    "input": [
      { "from": "user", "key": "user_request" },
      { "from": "planner", "key": "plan" }
    ],
    "output": [
      { "key": "draft_answer", "to": [ { "agent": "checker", "as": "draft_answer" } ] }
    ]
  },
  {
    "agent_id": "checker",
    "model": {
      "name_or_path": "Qwen2.5-32B-Instruct"
    },
    "instruction_prompt": {
      "instruction": "你是 Checker Agent：检查答案是否正确、是否满足格式要求，并给出最终输出。",
      "prompt_template": "问题：{{input.user_request}}\n候选答案：{{input.draft_answer}}\n请输出：{verdict, feedback, final_answer}"
    },
    "input": [
      { "from": "user", "key": "user_request" },
      { "from": "infer", "key": "draft_answer" }
    ],
    "output": [
      { "key": "final_answer", "to": [ { "user": True } ] },
      { "key": "verdict", "to": [ { "user": True } ] },
      { "key": "feedback", "to": [ { "user": True } ] }
    ]
  }
]


def test_json_validation():
    """测试 JSON 校验"""
    print("\n" + "="*60)
    print("1. JSON 校验测试")
    print("="*60)
    
    validator = JSONValidator()
    result = validator.validate(json_config)
    
    print(f"   校验结果: {'✅ 有效' if result.is_valid else '❌ 无效'}")
    print(f"   执行顺序: {' -> '.join(result.execution_order)}")
    
    if result.errors:
        print(f"   错误: {result.errors}")
    if result.warnings:
        print(f"   警告: {result.warnings}")
    
    print(f"   Agent 输入:")
    for agent_id, inputs in result.agent_inputs.items():
        print(f"     {agent_id}: {inputs}")
    
    print(f"   Agent 输出:")
    for agent_id, outputs in result.agent_outputs.items():
        print(f"     {agent_id}: {outputs}")
    
    return result.is_valid


def test_dataflow_graph():
    """测试数据流图"""
    print("\n" + "="*60)
    print("2. 数据流图生成")
    print("="*60)
    
    validator = JSONValidator()
    graph = validator.get_dataflow_graph(json_config)
    
    print(f"   节点数: {len(graph.get('nodes', []))}")
    print(f"   边数: {len(graph.get('edges', []))}")
    print(f"   节点列表:")
    for node in graph.get('nodes', []):
        print(f"     - {node['id']} ({node.get('type', 'agent')})")
    
    print(f"   边列表:")
    for edge in graph.get('edges', []):
        print(f"     - {edge['from']} -> {edge['to']} ({edge.get('label', '')})")
    
    return True


def test_trajectory_generation():
    """测试轨迹生成"""
    print("\n" + "="*60)
    print("3. 轨迹生成测试")
    print("="*60)
    
    spec = SystemSpec(agents=json_config)
    generator = TrajectoryGenerator(spec, config_id=1)
    
    user_request = {"user_request": "帮我制定一个学习计划，准备下周的数学考试"}
    trajectory = generator.generate_trajectory(user_request, sample_id=0)
    
    print(f"   轨迹ID: {trajectory.trajectory_id}")
    print(f"   样本ID: {trajectory.sample_id}")
    print(f"   步骤数: {len(trajectory.steps)}")
    print(f"   输入请求: {trajectory.input_request}")
    
    print(f"   执行流程:")
    for step in trajectory.steps:
        print(f"\n   步骤 {step.step_index + 1}: {step.agent_id}")
        print(f"     输入数据: {step.input_data}")
        print(f"     Prompt: {step.prompt[:80]}...")
        print(f"     Response: {step.response[:80]}...")
        print(f"     输出数据: {step.output_data}")
    
    print(f"\n   最终输出: {trajectory.final_output}")
    
    return True


def test_database_storage():
    """测试数据库存储"""
    print("\n" + "="*60)
    print("4. 数据库存储测试")
    print("="*60)
    
    db = DatabaseManager()
    
    # 保存配置到数据库
    config = db.create_system_config(
        name="Plan-Infer-Check 示例",
        description="说明文档中的第一个 JSON 示例",
        config_json=json_config
    )
    
    print(f"   配置已保存到数据库: ID={config.id}")
    
    # 更新校验状态
    validator = JSONValidator()
    result = validator.validate(json_config)
    
    db.update_config_validation(
        config_id=config.id,
        is_valid=result.is_valid,
        execution_order=result.execution_order
    )
    
    print(f"   校验状态已更新: is_valid={result.is_valid}")
    
    # 查询配置
    saved_config = db.get_system_config(config.id)
    print(f"   从数据库读取配置: {saved_config.name}")
    print(f"   Agent 数量: {saved_config.agent_count}")
    print(f"   执行顺序: {saved_config.execution_order}")
    
    return True


def test_export_formats():
    """测试导出格式"""
    print("\n" + "="*60)
    print("5. 导出格式测试")
    print("="*60)
    
    spec = SystemSpec(agents=json_config)
    generator = TrajectoryGenerator(spec, config_id=1)
    
    # 生成一些轨迹
    user_requests = [
        {"user_request": "请求1: 制定学习计划"},
        {"user_request": "请求2: 制定健身计划"}
    ]
    trajectories = generator.generate_batch(user_requests)
    
    # 导出为 SFT 格式
    sft_file = generator.export_to_sft_format(trajectories, "./test_outputs/first_json_sft.jsonl")
    print(f"   SFT 格式导出: {sft_file}")
    
    # 导出为 DPO 格式
    dpo_file = generator.export_to_dpo_format(trajectories, "./test_outputs/first_json_dpo.jsonl")
    print(f"   DPO 格式导出: {dpo_file}")
    
    # 导出为 GRPO 格式
    grpo_file = generator.export_to_grpo_format(trajectories, "./test_outputs/first_json_grpo.json")
    print(f"   GRPO 格式导出: {grpo_file}")
    
    # 读取并显示 SFT 文件内容
    print(f"\n   SFT 文件内容预览:")
    with open(sft_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f.readlines()[:2]):
            data = json.loads(line)
            print(f"     记录 {i+1}:")
            print(f"       instruction: {data['instruction'][:50]}...")
            print(f"       output: {data['output'][:50]}...")
    
    return True


def main():
    """主函数"""
    print("\n" + "="*60)
    print("测试说明文档中的第一个 JSON 示例")
    print("(plan -> inference -> check)")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    tests = [
        ("JSON 校验", test_json_validation),
        ("数据流图", test_dataflow_graph),
        ("轨迹生成", test_trajectory_generation),
        ("数据库存储", test_database_storage),
        ("导出格式", test_export_formats)
    ]
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 打印最终报告
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\n总计: {passed_count}/{total_count} 个测试通过")
    
    if passed_count == total_count:
        print("\n🎉 第一个 JSON 示例测试全部通过！")
        print("系统已正确实现 plan -> inference -> check 流程")
    else:
        print("\n⚠️ 部分测试失败")


if __name__ == "__main__":
    main()
