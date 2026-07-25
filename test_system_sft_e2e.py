"""End-to-end test for System-Level SFT"""
import requests
import json
import time

BASE = "http://127.0.0.1:8000"

# 1. Login
r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}"}
print("1. Login OK")

# 2. Upload system SFT config
with open("examples/system_sft_config.json", encoding="utf-8") as f:
    config_data = json.load(f)

r = requests.post(f"{BASE}/api/configs/validate", headers=h, json={"config_json": config_data})
print(f"2. Config validate: {r.status_code} -> {r.json().get('is_valid')}")

r = requests.post(f"{BASE}/api/configs", headers=h, json={
    "name": "System-SFT-Test (Plan-Infer-Check)",
    "config_json": config_data
})
config_id = r.json().get("id")
print(f"3. Config saved: id={config_id}")

# 3. Upload system SFT dataset
r = requests.post(f"{BASE}/api/datasets", headers=h, json={
    "name": "SystemSFT_Math_6samples",
    "type": "train",
    "file_path": "data/system_sft_dataset.jsonl",
    "file_format": "jsonl",
    "record_count": 6
})
dataset_id = r.json().get("id")
print(f"4. Dataset created: id={dataset_id}")

# 4. Create system-level training job
r = requests.post(f"{BASE}/api/training/jobs", headers=h, json={
    "name": "System-Level SFT Test",
    "type": "sft",
    "description": "System-level multi-agent SFT test",
    "config_id": config_id,
    "dataset_id": dataset_id,
    "data_source": "dataset",
    "training_mode": "auto",
    "hyperparameters": {
        "num_epochs": 1,
        "batch_size": 2,
        "max_length": 512,
        "use_lora": True,
        "use_flash_attn": False,
        "gradient_checkpointing": True
    }
})
job = r.json()
job_id = job.get("id")
print(f"5. Training job created: id={job_id}, status={job.get('status')}")

# 5. Monitor progress
print("\n6. Monitoring training progress...")
for i in range(5):
    time.sleep(10)
    r = requests.get(f"{BASE}/api/training/jobs/{job_id}", headers=h)
    j = r.json()
    status = j.get("status")
    metrics = j.get("metrics") or {}
    logs = j.get("logs") or ""
    
    if metrics.get("mode") == "system_level":
        agents = metrics.get("agents", [])
        completed = [a for a in agents if a.get("status") == "completed"]
        print(f"   [{i+1}/5] mode=system_level | completed={len(completed)}/{len(agents)} | status={status}")
        for a in agents:
            print(f"      {a['agent_id']}: {a['status']}" + (f" loss={a.get('final_loss', 'N/A')}" if a.get('final_loss') else ""))
    else:
        last_log = logs.split('\n')[-1] if logs else "waiting..."
        print(f"   [{i+1}/5] status={status} | {last_log[:80]}")
    
    if status in ("completed", "failed"):
        break

# 6. Final result
print("\n7. Final job status:")
r = requests.get(f"{BASE}/api/training/jobs/{job_id}", headers=h)
j = r.json()
metrics = j.get("metrics") or {}
print(f"   Status: {j['status']}")
if metrics.get("mode") == "system_level":
    print(f"   Mode: system_level")
    print(f"   Message: {metrics.get('overall_message', '')}")
    for a in metrics.get("agents", []):
        print(f"   Agent '{a['agent_id']}': {a['status']}" +
              (f" | loss={a.get('final_loss', 'N/A')}" if a.get('final_loss') else "") +
              (f" | output={a.get('output_dir', '')}" if a.get('output_dir') else "") +
              (f" | error={a.get('error', '')}" if a.get('error') else ""))
else:
    print(f"   Metrics: {json.dumps(metrics, indent=2)[:200]}")

print("\nDone!")
