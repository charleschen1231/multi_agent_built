#!/usr/bin/env python3
from database.db_manager import DatabaseManager
from database.models import TrajectoryRecord

db = DatabaseManager()
session = db.get_session()

# 获取最新的轨迹
trajectories = session.query(TrajectoryRecord).order_by(TrajectoryRecord.id.desc()).limit(3).all()

print(f'最新 {len(trajectories)} 条轨迹:\n')
for traj in trajectories:
    print(f'轨迹 ID: {traj.id}')
    print(f'配置 ID: {traj.config_id}')
    print(f'输入: {traj.input_request}')
    print(f'步骤数: {len(traj.steps_data) if traj.steps_data else 0}')
    if traj.steps_data:
        for i, step in enumerate(traj.steps_data[:2]):  # 只显示前2步
            print(f'  步骤 {i+1}: {step.get("agent_id")}')
            print(f'    输入: {step.get("input_data")}')
    print()
