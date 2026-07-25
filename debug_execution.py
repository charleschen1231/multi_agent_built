#!/usr/bin/env python3
"""调试执行流程"""

import json
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# 模拟 Gradio 的 JSON 组件解析
def test_json_component(value, name):
    """测试 JSON 组件是否能解析"""
    try:
        if isinstance(value, (dict, list)):
            json_str = json.dumps(value)
            if not json_str:
                print(f"❌ {name}: JSON 字符串为空")
                return False
            parsed = json.loads(json_str)
            print(f"✓ {name}: 正常")
            return True
        elif isinstance(value, str):
            if not value:
                print(f"⚠️ {name}: 空字符串 (可能导致问题)")
            else:
                print(f"✓ {name}: 字符串 '{value[:30]}...'")
            return True
        else:
            print(f"✓ {name}: {type(value).__name__}")
            return True
    except Exception as e:
        print(f"❌ {name}: 错误 - {e}")
        return False

# 导入实际代码
from database.db_manager import DatabaseManager
from spec.system_spec import SystemSpec
from core.trajectory_generator import TrajectoryGenerator

db = DatabaseManager()

# 获取配置
configs = db.get_all_system_configs()
if not configs:
    print("没有配置")
    sys.exit(1)

config = configs[-1]
print(f"\n使用配置: {config.name}")
print(f"执行顺序: {config.execution_order}")

# 模拟执行
inputs = [{"user_request": "测试请求"}]

try:
    spec = SystemSpec(agents=config.config_json)
    generator = TrajectoryGenerator(spec, config_id=config.id)
    trajectories = generator.generate_batch(inputs, use_teacher=False)
    
    # 收集结果
    results = []
    for traj in trajectories:
        final_output_data = traj.steps[-1].output_data if traj.steps else {}
        results.append({
            'trajectory_id': traj.trajectory_id,
            'final_output': final_output_data
        })
    
    # 准备输出（复制 execution_flow.py 中的逻辑）
    final_result = {
        'execution_id': 1,
        'config_name': config.name,
        'sample_count': len(results),
        'outputs': results[:3]
    }
    
    stats = {
        'total_samples': len(inputs),
        'completed': len(results),
        'agents': config.agent_count,
        'execution_order': config.execution_order
    }
    
    traj_data = []
    for i, agent_id in enumerate(config.execution_order or []):
        traj_data.append([
            i + 1,
            agent_id,
            "user_request",
            "output"
        ])
    
    # 测试所有返回值
    print("\n测试返回值:")
    test_json_component("✅ 执行完成", "status")
    test_json_component(100, "progress")
    test_json_component("日志内容", "logs")
    test_json_component(final_result, "final_result")
    test_json_component(stats, "stats")
    test_json_component(traj_data, "traj_data")
    test_json_component({"info": "Select a step"}, "step_detail")
    test_json_component("Prompt here", "step_prompt")
    test_json_component("Response here", "step_response")
    test_json_component("Flow HTML", "flow_html")
    
except Exception as e:
    import traceback
    print(f"\n执行失败: {e}")
    traceback.print_exc()
