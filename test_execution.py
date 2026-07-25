#!/usr/bin/env python3
"""测试执行流程"""

import json
import os
from dotenv import load_dotenv
load_dotenv()

from database.db_manager import DatabaseManager
from spec.system_spec import SystemSpec
from core.trajectory_generator import TrajectoryGenerator

# 加载数据库
db = DatabaseManager()

# 获取最新的配置
configs = db.get_all_system_configs()
print(f"数据库中有 {len(configs)} 个配置")

if configs:
    config = configs[-1]  # 获取最新的配置
    print(f"\n使用配置: {config.name} (ID: {config.id})")
    print(f"配置内容: {json.dumps(config.config_json, ensure_ascii=False, indent=2)[:500]}...")
    
    # 获取数据集
    datasets = db.get_all_datasets()
    print(f"\n数据库中有 {len(datasets)} 个数据集")
    
    if datasets:
        dataset = datasets[-1]
        print(f"使用数据集: {dataset.name} (ID: {dataset.id})")
        
        # 读取数据集内容
        try:
            with open(dataset.file_path, 'r', encoding='utf-8') as f:
                if dataset.file_format == 'jsonl':
                    inputs = [json.loads(line) for line in f.readlines()]
                else:
                    inputs = json.load(f)
            print(f"数据集内容: {inputs}")
        except Exception as e:
            print(f"读取数据集失败: {e}")
            inputs = [{"user_request": "这是一个测试请求"}]
    else:
        print("没有数据集，使用默认输入")
        inputs = [{"user_request": "帮我制定一个学习计划"}]
    
    # 测试轨迹生成
    print("\n开始生成轨迹...")
    try:
        spec = SystemSpec(agents=config.config_json)
        generator = TrajectoryGenerator(spec, config_id=config.id)
        
        trajectories = generator.generate_batch(inputs, use_teacher=False)
        
        print(f"成功生成 {len(trajectories)} 条轨迹")
        
        for i, traj in enumerate(trajectories):
            print(f"\n轨迹 {i+1}:")
            print(f"  ID: {traj.trajectory_id}")
            print(f"  步骤数: {len(traj.steps)}")
            for step in traj.steps:
                print(f"    - {step.agent_id}: {step.response[:100]}...")
                
    except Exception as e:
        print(f"生成轨迹失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("数据库中没有配置，请先上传配置")
