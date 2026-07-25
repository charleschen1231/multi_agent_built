#!/usr/bin/env python3
"""测试 Web 执行流程的实际返回值"""

import json
import os
from dotenv import load_dotenv
load_dotenv()

from database.db_manager import DatabaseManager
from spec.system_spec import SystemSpec
from core.trajectory_generator import TrajectoryGenerator

db = DatabaseManager()

# 使用有效配置
config_id = 3
config = db.get_system_config(config_id)

print(f"配置: {config.name}")
print(f"Agent 数量: {config.agent_count}")
print(f"执行顺序: {config.execution_order}")

inputs = [{"user_request": "帮我制定一个学习计划"}]
logs = []

try:
    logs.append(f"配置: {config.name} (ID: {config.id})")
    logs.append(f"Agent 数量: {config.agent_count}")
    logs.append(f"执行顺序: {config.execution_order}")
    
    spec = SystemSpec(agents=config.config_json)
    generator = TrajectoryGenerator(spec, config_id=config.id)
    
    trajectories = generator.generate_batch(inputs, use_teacher=False)
    logs.append(f"执行完成！生成了 {len(trajectories)} 条轨迹")
    
    # 收集结果
    results = []
    for traj in trajectories:
        final_output_data = traj.steps[-1].output_data if traj.steps else {}
        results.append({
            'trajectory_id': traj.trajectory_id,
            'final_output': final_output_data
        })
    
    # 准备输出
    final_result = {
        'execution_id': 999,
        'config_name': config.name,
        'sample_count': len(results),
        'outputs': results[:3]
    }
    
    stats = {
        'total_samples': len(inputs),
        'completed': len(results),
        'agents': config.agent_count,
        'execution_order': config.execution_order or []
    }
    
    traj_data = []
    for i, agent_id in enumerate(config.execution_order or []):
        traj_data.append([
            i + 1,
            agent_id,
            "user_request",
            "output"
        ])
    
    # 生成流程图
    def generate_flow_html(execution_order, config_json):
        if not execution_order:
            return "<div style='padding: 20px;'><h4>执行流程</h4><p>未配置执行顺序</p></div>"
        html = ["<div style='padding: 20px;'>"]
        html.append("<h4>执行流程</h4>")
        html.append("<div style='display: flex; align-items: center; flex-wrap: wrap; gap: 10px;'>")
        for i, agent_id in enumerate(execution_order):
            html.append(f"""
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; padding: 15px 25px; border-radius: 8px;'>
                    <strong>{agent_id}</strong>
                </div>
            """)
            if i < len(execution_order) - 1:
                html.append("<span style='font-size: 24px; color: #666;'>→</span>")
        html.append("</div></div>")
        return "".join(html)
    
    flow_html = generate_flow_html(config.execution_order or [], config.config_json)
    
    # 测试所有返回值
    return_values = (
        "✅ 执行完成",
        100,
        "\n".join(logs),
        final_result,
        stats,
        traj_data,
        {"info": "Select a step to view details"},
        "Prompt will be displayed here",
        "Response will be displayed here",
        flow_html
    )
    
    print("\n测试返回值:")
    for i, val in enumerate(return_values):
        val_type = type(val).__name__
        if isinstance(val, str) and not val:
            print(f"  [{i}] ❌ 空字符串!")
        elif val is None:
            print(f"  [{i}] ❌ None!")
        elif isinstance(val, (dict, list)):
            try:
                json_str = json.dumps(val)
                if not json_str:
                    print(f"  [{i}] ❌ JSON 空字符串!")
                else:
                    print(f"  [{i}] ✓ {val_type} (JSON长度: {len(json_str)})")
            except Exception as e:
                print(f"  [{i}] ❌ JSON 序列化失败: {e}")
        else:
            print(f"  [{i}] ✓ {val_type}")
    
except Exception as e:
    import traceback
    print(f"错误: {e}")
    traceback.print_exc()
