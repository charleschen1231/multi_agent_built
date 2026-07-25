#!/usr/bin/env python3
from database.db_manager import DatabaseManager
from spec.system_spec import SystemSpec
from core.trajectory_generator import TrajectoryGenerator

db = DatabaseManager()

# 使用最新的配置 (ID: 7)
config = db.get_system_config(7)
print(f'配置: {config.name}')
print(f'Agent 数量: {len(config.config_json)}')

# 生成轨迹 - 使用正确的输入 key
math_problem = "解方程: 2x + 5 = 15"
inputs = [{'math_problem': math_problem}]

print(f'\n输入问题: {math_problem}')
print(f'输入数据: {inputs}')

spec = SystemSpec(agents=config.config_json)
generator = TrajectoryGenerator(spec, config_id=config.id)

trajectories = generator.generate_batch(inputs, use_teacher=False)

print(f'\n生成了 {len(trajectories)} 条轨迹')
for traj in trajectories:
    print(f'\n轨迹: {traj.trajectory_id}')
    print(f'输入请求: {traj.input_request}')
    for step in traj.steps:
        print(f'\n  === {step.agent_id} ===')
        print(f'  输入数据: {step.input_data}')
        print(f'  Prompt: {step.prompt[:200]}...')
        print(f'  响应: {step.response[:200]}...')
