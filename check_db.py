#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# 获取最新的轨迹
cursor.execute('SELECT id, config_id, input_data, trajectory FROM generated_data ORDER BY id DESC LIMIT 1')
row = cursor.fetchone()

if row:
    print(f'轨迹 ID: {row[0]}')
    print(f'配置 ID: {row[1]}')
    input_data = json.loads(row[2])
    print(f'输入: {input_data}')
    print()
    traj = json.loads(row[3])
    print(f'步骤数: {len(traj)}')
    for step in traj[:2]:
        agent_id = step.get('agent_id')
        step_input = step.get('input_data')
        response = step.get('response')[:100]
        print(f'\n步骤: {agent_id}')
        print(f'输入: {step_input}')
        print(f'响应: {response}...')

conn.close()
