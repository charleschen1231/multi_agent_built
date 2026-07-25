#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# 获取最新的配置 (ID: 3 是 Plan-Infer-Check 示例)
cursor.execute('SELECT id, name, config_json FROM system_configs WHERE id = 3')
row = cursor.fetchone()

if row:
    print(f'配置: {row[1]} (ID: {row[0]})')
    config = json.loads(row[2])
    
    for agent in config:
        agent_id = agent.get('agent_id')
        print(f'\n=== {agent_id} ===')
        
        # 显示输出
        outputs = agent.get('output', [])
        print(f'输出数量: {len(outputs)}')
        for out in outputs:
            key = out.get('key')
            to_list = out.get('to', [])
            to_targets = []
            for t in to_list:
                if t.get('user'):
                    to_targets.append('user')
                elif t.get('agent'):
                    to_targets.append(t.get('agent'))
            print(f'  {key} -> {to_targets}')

conn.close()
