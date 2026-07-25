#!/usr/bin/env python
"""检查任务 14 的详细信息"""
import sys
sys.path.insert(0, '.')

from database.db_manager import DatabaseManager
import json

db = DatabaseManager()

job = db.get_training_job(14)
if job:
    print(f"任务 ID: {job.id}")
    print(f"名称: {job.name}")
    print(f"状态: {job.status}")
    print(f"配置: {json.dumps(job.config, indent=2, ensure_ascii=False)}")
    print(f"超参数: {json.dumps(job.hyperparameters, indent=2, ensure_ascii=False)}")
    print(f"输出目录: {job.output_dir}")
    print(f"\n完整日志:")
    print(job.logs if job.logs else "(无日志)")
else:
    print("任务不存在")
