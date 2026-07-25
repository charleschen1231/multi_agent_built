#!/usr/bin/env python3
"""测试模型路由功能"""

from database.db_manager import DatabaseManager
from spec.system_spec import SystemSpec
from core.trajectory_generator import TrajectoryGenerator

db = DatabaseManager()
config = db.get_system_config(3)

print(f'配置ID: {config.id}')
print(f'配置名称: {config.name}')
print()

# 显示每个 agent 的模型
for agent in config.config_json:
    print(f"Agent: {agent['agent_id']} -> Model: {agent['model']['name_or_path']}")
print()

# 生成轨迹
inputs = [{'user_request': '帮我制定一个学习计划'}]
spec = SystemSpec(agents=config.config_json)
generator = TrajectoryGenerator(spec, config_id=config.id)

trajectories = generator.generate_batch(inputs, use_teacher=False)

print(f'生成了 {len(trajectories)} 条轨迹')
for traj in trajectories:
    print(f'\n轨迹: {traj.trajectory_id}')
    for step in traj.steps:
        print(f'  - {step.agent_id}: {step.response[:80]}...')
