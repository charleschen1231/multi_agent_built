#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Agent System Builder - 功能测试脚本
"""

import json
import os
from database.db_manager import DatabaseManager
from core.json_validator import JSONValidator
from core.trajectory_generator import TrajectoryGenerator
from spec.system_spec import SystemSpec


def test_database():
    """测试数据库功能"""
    print("=" * 60)
    print("测试数据库模块")
    print("=" * 60)
    
    db = DatabaseManager()
    
    # 测试创建数据集
    dataset = db.create_dataset(
        name="测试数据集",
        description="用于测试的数据集",
        type="test",
        file_path="data/test.jsonl",
        file_format="jsonl",
        record_count=10
    )
    print(f"✅ 创建数据集: ID={dataset.id}, Name={dataset.name}")
    
    # 测试查询数据集
    datasets = db.get_all_datasets()
    print(f"✅ 查询数据集: 共 {len(datasets)} 个")
    
    # 测试创建配置
    sample_config = [
        {
            "agent_id": "test_agent",
            "model": {"name_or_path": "test-model"},
            "instruction_prompt": {
                "instruction": "测试指令",
                "prompt_template": "{{input.test}}"
            },
            "input": [{"from": "user", "key": "test"}],
            "output": [{"key": "result", "to": [{"user": True}]}]
        }
    ]
    
    config = db.create_system_config(
        name="测试配置",
        description="用于测试的配置",
        config_json=sample_config
    )
    print(f"✅ 创建配置: ID={config.id}, Name={config.name}")
    
    # 测试查询配置
    configs = db.get_all_system_configs()
    print(f"✅ 查询配置: 共 {len(configs)} 个")
    
    print("✅ 数据库测试通过！\n")
    return True


def test_json_validator():
    """测试 JSON 校验功能"""
    print("=" * 60)
    print("测试 JSON 校验模块")
    print("=" * 60)
    
    validator = JSONValidator()
    
    # 测试有效配置
    valid_config = [
        {
            "agent_id": "planner",
            "model": {"name_or_path": "Qwen2.5-0.5B-Instruct"},
            "instruction_prompt": {
                "instruction": "Planner Agent",
                "prompt_template": "{{input.user_request}}"
            },
            "input": [{"from": "user", "key": "user_request"}],
            "output": [{"key": "plan", "to": [{"agent": "executor", "as": "plan"}]}]
        },
        {
            "agent_id": "executor",
            "model": {"name_or_path": "Qwen2.5-0.5B-Instruct"},
            "instruction_prompt": {
                "instruction": "Executor Agent",
                "prompt_template": "Plan: {{input.plan}}"
            },
            "input": [{"from": "user", "key": "user_request"}, {"from": "planner", "key": "plan"}],
            "output": [{"key": "result", "to": [{"user": True}]}]
        }
    ]
    
    result = validator.validate(valid_config)
    print(f"✅ 有效配置校验: is_valid={result.is_valid}")
    print(f"   执行顺序: {' -> '.join(result.execution_order)}")
    
    # 测试无效配置（循环依赖）
    invalid_config = [
        {
            "agent_id": "agent_a",
            "model": {"name_or_path": "test"},
            "instruction_prompt": {"instruction": "Test", "prompt_template": "{{input.b}}"},
            "input": [{"from": "agent_b", "key": "b"}],
            "output": [{"key": "a", "to": [{"agent": "agent_b", "as": "a"}]}]
        },
        {
            "agent_id": "agent_b",
            "model": {"name_or_path": "test"},
            "instruction_prompt": {"instruction": "Test", "prompt_template": "{{input.a}}"},
            "input": [{"from": "agent_a", "key": "a"}],
            "output": [{"key": "b", "to": [{"agent": "agent_a", "as": "b"}]}]
        }
    ]
    
    result = validator.validate(invalid_config)
    print(f"✅ 无效配置校验: is_valid={result.is_valid}")
    print(f"   错误: {result.errors}")
    
    # 测试数据流图
    graph = validator.get_dataflow_graph(valid_config)
    print(f"✅ 数据流图生成: nodes={len(graph.get('nodes', []))}, edges={len(graph.get('edges', []))}")
    
    print("✅ JSON 校验测试通过！\n")
    return True


def test_trajectory_generator():
    """测试轨迹生成功能"""
    print("=" * 60)
    print("测试轨迹生成模块")
    print("=" * 60)
    
    config = [
        {
            "agent_id": "planner",
            "model": {"name_or_path": "Qwen2.5-0.5B-Instruct"},
            "instruction_prompt": {
                "instruction": "Planner",
                "prompt_template": "Request: {{input.user_request}}"
            },
            "input": [{"from": "user", "key": "user_request"}],
            "output": [{"key": "plan", "to": [{"agent": "executor", "as": "plan"}]}]
        },
        {
            "agent_id": "executor",
            "model": {"name_or_path": "Qwen2.5-0.5B-Instruct"},
            "instruction_prompt": {
                "instruction": "Executor",
                "prompt_template": "Plan: {{input.plan}}"
            },
            "input": [{"from": "planner", "key": "plan"}],
            "output": [{"key": "result", "to": [{"user": True}]}]
        }
    ]
    
    spec = SystemSpec(agents=config)
    generator = TrajectoryGenerator(spec, config_id=1)
    
    # 测试单条轨迹生成
    user_request = {"user_request": "帮我制定一个学习计划"}
    trajectory = generator.generate_trajectory(user_request, sample_id=0)
    
    print(f"✅ 单条轨迹生成: ID={trajectory.trajectory_id}")
    print(f"   步骤数: {len(trajectory.steps)}")
    print(f"   Agents: {[s.agent_id for s in trajectory.steps]}")
    
    # 测试批量轨迹生成
    user_requests = [
        {"user_request": "请求1"},
        {"user_request": "请求2"},
        {"user_request": "请求3"}
    ]
    trajectories = generator.generate_batch(user_requests)
    
    print(f"✅ 批量轨迹生成: 共 {len(trajectories)} 条轨迹")
    
    # 测试统计信息
    stats = generator.get_statistics(trajectories)
    print(f"✅ 统计信息: {stats}")
    
    print("✅ 轨迹生成测试通过！\n")
    return True


def test_trainers():
    """测试训练模块"""
    print("=" * 60)
    print("测试训练模块")
    print("=" * 60)
    
    from training.sft_trainer import SFTTrainer
    from training.dpo_trainer import DPOTrainer
    from training.grpo_trainer import GRPOTrainer
    
    # 测试 SFT Trainer
    sft_trainer = SFTTrainer(output_dir="./test_outputs/sft")
    print("✅ SFT Trainer 初始化成功")
    
    # 模拟轨迹数据
    mock_trajectories = [
        {
            "trajectory_id": "traj_1",
            "sample_id": 0,
            "steps": [
                {
                    "agent_id": "agent1",
                    "prompt": "测试 prompt",
                    "response": "测试响应",
                    "ground_truth": "标准答案",
                    "metadata": {}
                }
            ]
        }
    ]
    
    # 测试数据准备
    data_file = sft_trainer.prepare_training_data(mock_trajectories, "./test_outputs/sft_test.jsonl")
    print(f"✅ SFT 数据准备: {data_file}")
    
    # 测试训练配置生成
    training_info = sft_trainer.train(
        data_file=data_file,
        model_path="Qwen/Qwen2.5-0.5B-Instruct",
        hyperparameters={'lr': 2e-5, 'batch_size': 4, 'num_epochs': 1}
    )
    print(f"✅ SFT 训练配置生成: output_dir={training_info['output_dir']}")
    
    # 测试 DPO Trainer
    dpo_trainer = DPOTrainer(output_dir="./test_outputs/dpo")
    print("✅ DPO Trainer 初始化成功")
    
    dpo_data_file = dpo_trainer.prepare_preference_data(mock_trajectories, "./test_outputs/dpo_test.jsonl")
    print(f"✅ DPO 数据准备: {dpo_data_file}")
    
    # 测试 GRPO Trainer
    grpo_trainer = GRPOTrainer(output_dir="./test_outputs/grpo")
    print("✅ GRPO Trainer 初始化成功")
    
    grpo_data_file = grpo_trainer.prepare_rollout_data(mock_trajectories, "./test_outputs/grpo_test.jsonl")
    print(f"✅ GRPO 数据准备: {grpo_data_file}")
    
    print("✅ 训练模块测试通过！\n")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Multi-Agent System Builder - 功能测试")
    print("=" * 60 + "\n")
    
    tests = [
        ("数据库模块", test_database),
        ("JSON 校验模块", test_json_validator),
        ("轨迹生成模块", test_trajectory_generator),
        ("训练模块", test_trainers)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, True, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"❌ {name} 测试失败: {e}\n")
    
    # 打印测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    for name, passed, error in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
        if error:
            print(f"   错误: {error}")
    
    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)
    
    print(f"\n总计: {passed_count}/{total_count} 个测试通过")
    
    if passed_count == total_count:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")


if __name__ == "__main__":
    run_all_tests()
