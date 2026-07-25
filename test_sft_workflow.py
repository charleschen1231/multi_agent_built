#!/usr/bin/env python3
"""
System-level SFT 测试脚本
测试完整的 Multi-Agent SFT 微调流程
"""

import json
import requests
import time
from datetime import datetime

# API 配置
BASE_URL = "http://localhost:8000"
TOKEN = None

def login():
    """登录获取 token"""
    global TOKEN
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if response.status_code == 200:
        TOKEN = response.json()["access_token"]
        print("✅ 登录成功")
        return True
    else:
        print(f"❌ 登录失败: {response.text}")
        return False

def get_headers():
    return {"Authorization": f"Bearer {TOKEN}"}

def test_step_1_upload_config():
    """步骤1：上传带 training 配置的 JSON"""
    print("\n" + "="*60)
    print("步骤1: 上传带 Training 配置的 Multi-Agent 系统")
    print("="*60)
    
    with open("test_sft_config.json", "r", encoding="utf-8") as f:
        config_json = json.load(f)
    
    response = requests.post(
        f"{BASE_URL}/api/configs",
        headers=get_headers(),
        json={
            "name": f"MathSolver_SFT_Test_{datetime.now().strftime('%m%d_%H%M')}",
            "description": "用于测试 System-level SFT 的数学解题系统",
            "config_json": config_json
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 配置上传成功")
        print(f"   配置ID: {result['id']}")
        print(f"   配置名称: {result['name']}")
        print(f"   验证状态: {'✅ 有效' if result.get('is_valid') else '❌ 无效'}")
        print(f"   Agent数量: {result.get('agent_count', 'N/A')}")
        if result.get('execution_order'):
            print(f"   执行顺序: {' -> '.join(result['execution_order'])}")
        return result['id']
    else:
        print(f"❌ 配置上传失败: {response.text}")
        return None

def test_step_2_upload_dataset():
    """步骤2：上传训练数据集"""
    print("\n" + "="*60)
    print("步骤2: 上传训练数据集")
    print("="*60)
    
    # 统计数据集条数
    with open("test_sft_dataset.jsonl", "r", encoding="utf-8") as f:
        record_count = sum(1 for _ in f)
    
    response = requests.post(
        f"{BASE_URL}/api/datasets",
        headers=get_headers(),
        json={
            "name": f"MathTrainingData_{datetime.now().strftime('%m%d_%H%M')}",
            "description": "数学问题训练数据集，包含plan_gt, solution_gt, final_answer_gt",
            "type": "train",
            "file_path": "test_sft_dataset.jsonl",
            "file_format": "jsonl",
            "record_count": record_count
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 数据集上传成功")
        print(f"   数据集ID: {result['id']}")
        print(f"   数据集名称: {result['name']}")
        print(f"   记录数: {result.get('record_count', 'N/A')}")
        return result['id']
    else:
        print(f"❌ 数据集上传失败: {response.text}")
        return None

def test_step_3_run_execution(config_id, dataset_id):
    """步骤3：运行执行生成轨迹"""
    print("\n" + "="*60)
    print("步骤3: 运行 Multi-Agent 系统生成轨迹数据")
    print("="*60)
    
    # 先上传测试数据集到执行端点
    with open("test_sft_dataset.jsonl", "r", encoding="utf-8") as f:
        dataset_content = f.read()
    
    response = requests.post(
        f"{BASE_URL}/api/datasets/upload",
        headers=get_headers(),
        files={"file": ("test_data.jsonl", dataset_content, "application/json")}
    )
    
    if response.status_code == 200:
        print(f"✅ 数据集已上传用于执行")
    
    # 执行批量任务
    response = requests.post(
        f"{BASE_URL}/api/configs/{config_id}/execute-batch",
        headers=get_headers(),
        json={
            "inputs": [
                {"user_request": "计算 15 + 27"},
                {"user_request": "求解方程 2x + 5 = 13"},
                {"user_request": "计算 3 × (4 + 5)"}
            ],
            "parallel": True,
            "max_workers": 2,
            "record_trajectory": True
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 批量执行完成")
        print(f"   总任务数: {result.get('total', 0)}")
        print(f"   成功: {result.get('success', 0)}")
        print(f"   失败: {result.get('failed', 0)}")
        return True
    else:
        print(f"❌ 执行失败: {response.text}")
        return False

def test_step_4_create_training_job(config_id, dataset_id):
    """步骤4：创建 SFT 训练任务"""
    print("\n" + "="*60)
    print("步骤4: 创建 System-level SFT 训练任务")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/api/training/jobs",
        headers=get_headers(),
        json={
            "name": f"MathSolver_SFT_Job_{datetime.now().strftime('%m%d_%H%M')}",
            "type": "sft",
            "description": "System-level SFT 训练：同时训练 planner, solver, checker 三个 agent",
            "config_id": config_id,
            "dataset_id": dataset_id,
            "hyperparameters": {
                "lr": 2e-5,
                "num_epochs": 1,
                "batch_size": 2,
                "max_length": 1024,
                "warmup_ratio": 0.1,
                "weight_decay": 0.01,
                "fp16": True
            },
            "data_source": "trajectory"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 训练任务创建成功")
        print(f"   任务ID: {result['id']}")
        print(f"   任务名称: {result['name']}")
        print(f"   状态: {result['status']}")
        print(f"   消息: {result.get('message', '')}")
        return result['id']
    else:
        print(f"❌ 训练任务创建失败: {response.text}")
        return None

def test_step_5_monitor_training(job_id):
    """步骤5：监控训练进度"""
    print("\n" + "="*60)
    print("步骤5: 监控训练进度")
    print("="*60)
    
    max_attempts = 30
    for i in range(max_attempts):
        response = requests.get(
            f"{BASE_URL}/api/training/jobs/{job_id}",
            headers=get_headers()
        )
        
        if response.status_code == 200:
            job = response.json()
            status = job['status']
            
            print(f"[{i+1}/{max_attempts}] 状态: {status}")
            
            if status == 'completed':
                print(f"✅ 训练完成!")
                print(f"   输出目录: {job.get('output_dir', 'N/A')}")
                print(f"   模型路径: {job.get('model_path', 'N/A')}")
                return True
            elif status == 'failed':
                print(f"❌ 训练失败: {job.get('error_message', 'Unknown error')}")
                return False
            elif status == 'stopped':
                print(f"⏹️ 训练已停止")
                return False
        
        time.sleep(2)
    
    print(f"⚠️ 监控超时，请手动检查训练状态")
    return None

def test_step_6_deploy_model(job_id):
    """步骤6：部署训练好的模型"""
    print("\n" + "="*60)
    print("步骤6: 部署训练好的模型")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/api/training/jobs/{job_id}/deploy",
        headers=get_headers(),
        json={
            "create_new_version": True
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 模型部署成功!")
        print(f"   消息: {result['message']}")
        print(f"   配置ID: {result['config_id']}")
        print(f"   模型路径: {result['model_path']}")
        print(f"   更新的Agents: {', '.join(result['updated_agents'])}")
        return True
    else:
        print(f"❌ 模型部署失败: {response.text}")
        return False

def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("System-level SFT 完整测试")
    print("="*60)
    print("\n测试流程:")
    print("1. 登录系统")
    print("2. 上传带 training 配置的 Multi-Agent JSON")
    print("3. 上传训练数据集")
    print("4. 运行执行生成轨迹数据")
    print("5. 创建 SFT 训练任务")
    print("6. 监控训练进度")
    print("7. 部署训练好的模型")
    
    # 步骤1: 登录
    if not login():
        return
    
    # 步骤2: 上传配置
    config_id = test_step_1_upload_config()
    if not config_id:
        return
    
    # 步骤3: 上传数据集
    dataset_id = test_step_2_upload_dataset()
    if not dataset_id:
        return
    
    # 步骤4: 运行执行（可选，如果没有已有轨迹）
    # test_step_3_run_execution(config_id, dataset_id)
    
    # 步骤5: 创建训练任务
    job_id = test_step_4_create_training_job(config_id, dataset_id)
    if not job_id:
        return
    
    # 步骤6: 监控训练
    result = test_step_5_monitor_training(job_id)
    if result:
        # 步骤7: 部署模型
        test_step_6_deploy_model(job_id)
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)

if __name__ == "__main__":
    main()
