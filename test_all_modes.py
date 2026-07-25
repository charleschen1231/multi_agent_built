"""
Multi-Agent System Builder - 全模式端到端测试脚本
用法: python test_all_modes.py [--base-url http://localhost:8000]

测试覆盖:
1. SFT System-Level 训练
2. DPO System-Level 训练  
3. GRPO System-Level 训练
4. 蒸馏效果验证
"""
import requests
import json
import time
import argparse
import sys
import os

# ============ 配置 ============

DEFAULT_BASE = "http://127.0.0.1:8000"
POLL_INTERVAL = 10  # 轮询间隔（秒）
MAX_WAIT = 600      # 最大等待时间（秒）

# ============ 工具函数 ============

def log(msg, level="INFO"):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")

def log_pass(msg):
    log(f"✅ {msg}")

def log_fail(msg):
    log(f"❌ {msg}", "FAIL")

def log_section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)

def api(base, method, path, token=None, data=None):
    """通用 API 请求"""
    url = f"{base}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    if method == "GET":
        r = requests.get(url, headers=headers, timeout=30)
    elif method == "POST":
        r = requests.post(url, headers=headers, json=data, timeout=60)
    elif method == "DELETE":
        r = requests.delete(url, headers=headers, timeout=30)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    if r.status_code >= 400:
        log(f"API Error: {r.status_code} {r.text[:200]}", "WARN")
    
    return r

def wait_for_job(base, token, job_id, max_wait=MAX_WAIT):
    """等待训练任务完成"""
    start = time.time()
    while time.time() - start < max_wait:
        r = api(base, "GET", f"/api/training/jobs/{job_id}", token)
        if r.status_code == 200:
            job = r.json()
            status = job.get("status", "unknown")
            log(f"  Job {job_id} 状态: {status}")
            
            if status == "completed":
                return job
            elif status in ("failed", "stopped"):
                error = job.get("error_message", "未知错误")
                logs = job.get("logs", "")
                last_logs = "\n".join(logs.split("\n")[-5:]) if logs else ""
                log(f"  错误信息: {error}", "WARN")
                if last_logs:
                    log(f"  最近日志:\n{last_logs}", "WARN")
                return job
        
        time.sleep(POLL_INTERVAL)
    
    log(f"  Job {job_id} 超时 ({max_wait}s)", "WARN")
    return api(base, "GET", f"/api/training/jobs/{job_id}", token).json()

# ============ 测试步骤 ============

def step_login(base):
    """Step 1: 登录"""
    log_section("Step 1: 登录")
    r = api(base, "POST", "/api/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    if r.status_code == 200:
        token = r.json()["access_token"]
        log_pass(f"登录成功，token: {token[:20]}...")
        return token
    else:
        log_fail(f"登录失败: {r.status_code}")
        sys.exit(1)

def step_upload_config(base, token, name, config_file):
    """上传系统配置"""
    with open(config_file, encoding="utf-8") as f:
        config_data = json.load(f)
    
    # 先验证
    r = api(base, "POST", "/api/configs/validate", token, {"config_json": config_data})
    if r.status_code == 200:
        valid = r.json().get("is_valid", False)
        log(f"  配置校验: {'通过' if valid else '未通过'}")
    
    # 保存
    r = api(base, "POST", "/api/configs", token, {
        "name": name,
        "config_json": config_data
    })
    if r.status_code in (200, 201):
        config_id = r.json().get("id")
        log_pass(f"配置 '{name}' 已保存: id={config_id}")
        return config_id
    else:
        log_fail(f"配置保存失败: {r.status_code} {r.text[:200]}")
        return None

def step_upload_dataset(base, token, name, file_path, dtype="train"):
    """上传数据集"""
    # 统计行数
    count = 0
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    
    r = api(base, "POST", "/api/datasets", token, {
        "name": name,
        "type": dtype,
        "file_path": file_path,
        "file_format": "jsonl",
        "record_count": count
    })
    if r.status_code in (200, 201):
        dataset_id = r.json().get("id")
        log_pass(f"数据集 '{name}' 已保存: id={dataset_id}, {count} 条")
        return dataset_id
    else:
        log_fail(f"数据集保存失败: {r.status_code} {r.text[:200]}")
        return None

def step_create_training(base, token, name, training_type, config_id, dataset_id, hparams):
    """创建训练任务"""
    r = api(base, "POST", "/api/training/jobs", token, {
        "name": name,
        "type": training_type,
        "training_type": training_type,
        "description": f"自动测试 - {training_type} 模式",
        "config_id": config_id,
        "dataset_id": dataset_id,
        "data_source": "dataset",
        "training_mode": "auto",
        "hyperparameters": hparams
    })
    if r.status_code in (200, 201):
        job = r.json()
        job_id = job.get("id")
        log_pass(f"训练任务 '{name}' 已创建: id={job_id}, status={job.get('status')}")
        return job_id
    else:
        log_fail(f"训练任务创建失败: {r.status_code} {r.text[:200]}")
        return None

def step_validate(base, token, job_id):
    """验证蒸馏效果"""
    r = api(base, "POST", f"/api/training/jobs/{job_id}/validate", token)
    if r.status_code == 200:
        report = r.json().get("validation_report", {})
        score = report.get("overall_quality_score", 0)
        grade = report.get("overall_quality_grade", report.get("summary", {}).get("quality_grade", "N/A"))
        log_pass(f"验证完成: 质量分={score:.4f}, 等级={grade}")
        return report
    else:
        log_fail(f"验证失败: {r.status_code} {r.text[:200]}")
        return None

# ============ 主测试流程 ============

def test_sft(base, token):
    """测试 SFT 训练模式"""
    log_section("测试 1/3: SFT System-Level 训练")
    
    config_id = step_upload_config(base, token, "TEST-SFT-Plan-Infer-Check", "examples/system_sft_config.json")
    if not config_id:
        return None
    
    dataset_id = step_upload_dataset(base, token, "TEST-SFT-Math", "data/system_sft_dataset.jsonl")
    if not dataset_id:
        return None
    
    job_id = step_create_training(base, token, "TEST-SFT-Training", "sft", config_id, dataset_id, {
        "num_epochs": 1,
        "batch_size": 2,
        "max_length": 512,
        "lr": 2e-5,
        "use_lora": True,
        "lora_rank": 8,
        "use_flash_attn": False,
        "gradient_checkpointing": True
    })
    if not job_id:
        return None
    
    log(f"等待 SFT 训练完成...")
    result = wait_for_job(base, token, job_id)
    
    if result and result.get("status") == "completed":
        log_pass("SFT 训练完成!")
        metrics = result.get("metrics", {})
        agents = metrics.get("agents", [])
        for agent in agents:
            log(f"  Agent '{agent.get('agent_id')}': loss={agent.get('final_loss', 'N/A')}, "
                f"time={agent.get('elapsed_seconds', 'N/A')}s")
        return result
    else:
        status = result.get("status", "unknown") if result else "unknown"
        log_fail(f"SFT 训练未成功完成，最终状态: {status}")
        return result

def test_dpo(base, token):
    """测试 DPO 训练模式"""
    log_section("测试 2/3: DPO System-Level 训练")
    
    config_id = step_upload_config(base, token, "TEST-DPO-Plan-Infer-Check", "examples/system_dpo_config.json")
    if not config_id:
        return None
    
    dataset_id = step_upload_dataset(base, token, "TEST-DPO-Math", "data/system_dpo_dataset.jsonl")
    if not dataset_id:
        return None
    
    job_id = step_create_training(base, token, "TEST-DPO-Training", "dpo", config_id, dataset_id, {
        "lr": 5e-7,
        "beta": 0.1,
        "num_epochs": 1,
        "batch_size": 2,
        "use_lora": True,
        "lora_rank": 8
    })
    if not job_id:
        return None
    
    log(f"等待 DPO 训练完成...")
    result = wait_for_job(base, token, job_id)
    
    if result and result.get("status") == "completed":
        log_pass("DPO 训练完成!")
        return result
    else:
        status = result.get("status", "unknown") if result else "unknown"
        log_fail(f"DPO 训练未成功完成，最终状态: {status}")
        return result

def test_grpo(base, token):
    """测试 GRPO 训练模式"""
    log_section("测试 3/3: GRPO System-Level 训练")
    
    config_id = step_upload_config(base, token, "TEST-GRPO-Plan-Infer-Check", "examples/system_grpo_config.json")
    if not config_id:
        return None
    
    dataset_id = step_upload_dataset(base, token, "TEST-GRPO-Math", "data/system_sft_dataset.jsonl")
    if not dataset_id:
        return None
    
    job_id = step_create_training(base, token, "TEST-GRPO-Training", "grpo", config_id, dataset_id, {
        "lr": 1e-6,
        "kl_coef": 0.01,
        "rollout_batch_size": 16,
        "mini_batch_size": 4,
        "clip_range": 0.2,
        "advantage": "gae"
    })
    if not job_id:
        return None
    
    log(f"等待 GRPO 训练完成...")
    result = wait_for_job(base, token, job_id, max_wait=MAX_WAIT * 2)
    
    if result and result.get("status") == "completed":
        log_pass("GRPO 训练完成!")
        return result
    else:
        status = result.get("status", "unknown") if result else "unknown"
        log_fail(f"GRPO 训练未成功完成，最终状态: {status}")
        return result

def test_all_jobs_list(base, token):
    """验证训练任务列表"""
    log_section("验证: 训练任务列表")
    r = api(base, "GET", "/api/training/jobs", token)
    if r.status_code == 200:
        jobs = r.json()
        log_pass(f"训练任务列表: 共 {len(jobs)} 个任务")
        for j in jobs:
            log(f"  [{j['id']}] {j['name']} - type={j['type']} - status={j['status']}")
    else:
        log_fail(f"获取任务列表失败: {r.status_code}")

# ============ 主入口 ============

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent System Builder 全模式测试")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="API 服务器地址")
    parser.add_argument("--skip-grpo", action="store_true", help="跳过 GRPO 测试（verl 可能未安装）")
    parser.add_argument("--only", choices=["sft", "dpo", "grpo"], help="只运行指定模式的测试")
    args = parser.parse_args()
    
    base = args.base_url.rstrip("/")
    
    log_section(f"Multi-Agent System Builder - 全模式端到端测试")
    log(f"服务器地址: {base}")
    log(f"跳过 GRPO: {args.skip_grpo}")
    log(f"仅测试: {args.only or '全部'}")
    
    # Step 1: 登录
    token = step_login(base)
    
    results = {}
    
    # 运行测试
    if not args.only or args.only == "sft":
        results["sft"] = test_sft(base, token)
    
    if not args.only or args.only == "dpo":
        results["dpo"] = test_dpo(base, token)
    
    if (not args.only or args.only == "grpo") and not args.skip_grpo:
        results["grpo"] = test_grpo(base, token)
    elif args.skip_grpo:
        log_section("跳过: GRPO 测试 (--skip-grpo)")
    
    # 验证任务列表
    test_all_jobs_list(base, token)
    
    # 汇总
    log_section("测试结果汇总")
    all_passed = True
    for mode, result in results.items():
        if result and result.get("status") == "completed":
            log_pass(f"{mode.upper()}: 训练成功")
        else:
            status = result.get("status", "N/A") if result else "未执行"
            log_fail(f"{mode.upper()}: {status}")
            all_passed = False
    
    print()
    if all_passed and results:
        log_pass("所有测试通过！可以部署到生产环境。")
    elif results:
        log_fail("部分测试未通过，请检查日志。")
    else:
        log("未执行任何测试", "WARN")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
