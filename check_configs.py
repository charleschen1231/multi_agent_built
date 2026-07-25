#!/usr/bin/env python
"""检查系统配置中的模型设置"""
from database.db_manager import DatabaseManager

db = DatabaseManager()
configs = db.get_all_system_configs()

print("=" * 60)
print("系统配置列表")
print("=" * 60)

for c in configs:
    print(f"\n配置 ID: {c.id}")
    print(f"名称: {c.name}")
    print(f"Agent 数量: {c.agent_count}")
    
    if c.config_json:
        for agent in c.config_json:
            agent_id = agent.get("agent_id", "unknown")
            model = agent.get("model", {})
            training = agent.get("training", {})
            
            print(f"\n  Agent: {agent_id}")
            print(f"    模型名称: {model.get('name_or_path', 'N/A')}")
            print(f"    可训练: {training.get('trainable', False)}")
            print(f"    训练模式: {training.get('mode', 'N/A')}")
    else:
        print("  无配置数据")
    
    print("-" * 60)
