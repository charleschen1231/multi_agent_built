#!/usr/bin/env python
"""检查训练任务日志"""
import sys
sys.path.insert(0, '.')

from database.db_manager import DatabaseManager

db = DatabaseManager()

print("=" * 60)
print("最近的训练任务")
print("=" * 60)

jobs = db.get_all_training_jobs()
for job in jobs[-5:]:  # 最近5个任务
    print(f"\n任务 ID: {job.id}")
    print(f"  名称: {job.name}")
    print(f"  类型: {job.type}")
    print(f"  状态: {job.status}")
    print(f"  输出目录: {job.output_dir}")
    print(f"  创建时间: {job.created_at}")
    print(f"  日志:")
    if job.logs:
        # 只显示最后500字符
        logs = job.logs[-500:] if len(job.logs) > 500 else job.logs
        for line in logs.split('\n'):
            print(f"    {line}")
    else:
        print("    (无日志)")
    print("-" * 60)
