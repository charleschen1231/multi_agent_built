#!/usr/bin/env python3
from database.db_manager import DatabaseManager
db = DatabaseManager()

# 获取所有配置
from database.models import SystemConfig
session = db.get_session()
configs = session.query(SystemConfig).all()
print(f'共有 {len(configs)} 个配置')
for c in configs:
    print(f'  ID: {c.id}, 名称: {c.name}')

# 获取最新配置
latest = configs[-1] if configs else None
if latest:
    print(f'\n最新配置: {latest.name}')
    print(f'Agent 数量: {len(latest.config_json)}')
    for agent in latest.config_json:
        agent_id = agent.get('agent_id', 'unknown')
        print(f'  - {agent_id}')
        
    # 显示输入配置
    print('\n第一个 agent 的输入配置:')
    first_agent = latest.config_json[0]
    inputs = first_agent.get('input', [])
    for inp in inputs:
        print(f'  from: {inp.get("from")}, key: {inp.get("key")}')
        
    # 显示完整配置
    print('\n完整配置 JSON:')
    import json
    print(json.dumps(latest.config_json, indent=2, ensure_ascii=False))
