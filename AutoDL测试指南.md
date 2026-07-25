# Multi-Agent System Builder — AutoDL 完整测试指南

## 一、机器准备

### 1.1 推荐配置
- **GPU**: RTX 4090-48G × 1
- **镜像**: PyTorch 2.1+ / CUDA 12.1+（AutoDL 默认 PyTorch 镜像即可）
- **系统盘**: 30GB（建议扩容到 50GB，模型权重占空间）

### 1.2 租好机器后
1. 在 AutoDL 控制台点击「开机」
2. 等待 GPU 就绪（约 1-2 分钟）
3. 点击「SSH 连接」获取登录命令，格式类似：
   ```
   ssh -p 12345 root@region-1.autodl.com
   ```
4. 用终端工具（如 PowerShell / Xshell / VS Code Remote）连接

---

## 二、环境部署

### 2.1 上传项目代码

**方式 A：Git 克隆（推荐）**
```bash
# 在 AutoDL 机器上
cd /root/autodl-tmp
git clone <你的仓库地址> multi_agent_built
cd multi_agent_built
```

**方式 B：AutoDL 文件管理上传**
- 在本地将项目打包：`tar -czf multi_agent_built.tar.gz multi_agent_built/`
- 通过 AutoDL 网页「文件管理」上传 tar.gz
- 在 SSH 中解压：`tar -xzf multi_agent_built.tar.gz`

### 2.2 安装依赖

```bash
cd /root/autodl-tmp/multi_agent_built

# 安装基础依赖
pip install -r requirements.txt

# 安装 ms-swift（SFT/DPO 训练框架）
pip install ms-swift

# 安装 verl（GRPO 训练框架，可选，安装耗时较长）
pip install verl
```

### 2.3 配置环境变量

```bash
# 创建 .env 文件
cat > .env << 'EOF'
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE
EOF
```

> **注意**：如果要用 Qwen API 做推理/优化 prompt，还需在 `configs/api_config.yaml` 中配置 Qwen 的 API Key。

### 2.4 创建输出目录

```bash
mkdir -p training_outputs/sft
mkdir -p training_outputs/dpo
mkdir -p training_outputs/grpo
mkdir -p evaluation_outputs
mkdir -p data/rollouts
```

### 2.5 验证环境

```bash
# 检查 GPU
nvidia-smi

# 检查 PyTorch GPU 支持
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}')"

# 检查 ms-swift
swift --version

# 检查 verl（如果安装了）
python3 -c "import verl; print('verl OK')"
```

---

## 三、测试流程总览

```
阶段1: JSON 配置解析验证
    ↓
阶段2: 多 Agent 推理执行
    ↓
阶段3: SFT 训练
    ↓
阶段4: DPO 训练
    ↓
阶段5: GRPO 训练
```

每个阶段都可以独立验证，建议**逐阶段跑通**，不要跳步。

---

## 四、阶段 1 — JSON 配置解析验证

### 目标
验证系统能正确解析 JSON 配置文件，构建 Agent 图。

### 操作

```bash
cd /root/autodl-tmp/multi_agent_built

python3 -c "
from spec.system_spec import SystemSpec

# 测试 SFT 配置
spec = SystemSpec.from_file('examples/system_sft_config.json')
print(f'✅ SFT 配置解析成功: {len(spec.agents)} 个 Agent')
for a in spec.agents:
    print(f'   - {a.agent_id}: model={a.model.name_or_path}')

# 测试 DPO 配置
spec = SystemSpec.from_file('examples/system_dpo_config.json')
print(f'✅ DPO 配置解析成功: {len(spec.agents)} 个 Agent')

# 测试 GRPO 配置
spec = SystemSpec.from_file('examples/system_grpo_config.json')
print(f'✅ GRPO 配置解析成功: {len(spec.agents)} 个 Agent')
"
```

### 预期输出
```
✅ SFT 配置解析成功: 3 个 Agent
   - planner: model=Qwen/Qwen2.5-0.5B-Instruct
   - infer: model=Qwen/Qwen2.5-0.5B-Instruct
   - checker: model=Qwen/Qwen2.5-0.5B-Instruct
✅ DPO 配置解析成功: 3 个 Agent
✅ GRPO 配置解析成功: 3 个 Agent
```

---

## 五、阶段 2 — 多 Agent 推理执行

### 目标
验证 3 个 Agent（planner → infer → checker）能按数据流顺序执行推理。

### 5.1 准备测试数据

```bash
cat > data/test_input.jsonl << 'EOF'
{"user_request": "计算 23 × 47 等于多少？", "final_answer_gt": "1081"}
{"user_request": "一个长方形的长是12cm，宽是8cm，求面积", "final_answer_gt": "96平方厘米"}
{"user_request": "解方程 2x + 6 = 20", "final_answer_gt": "x = 7"}
EOF
```

### 5.2 运行推理

```bash
python3 -c "
import json
from spec.system_spec import SystemSpec
from runtime.executor import SystemExecutor

# 加载配置
spec = SystemSpec.from_file('examples/system_sft_config.json')

# 创建执行器（关闭轨迹记录，仅测试推理）
executor = SystemExecutor(spec.agents, enable_recording=False)

# 读取测试数据
inputs = []
with open('data/test_input.jsonl', 'r') as f:
    for line in f:
        inputs.append(json.loads(line.strip()))

# 执行（不使用 teacher 模型，仅推理）
results = executor.run_batch(inputs, use_teacher_for_gt=False)

print('\\n===== 推理结果 =====')
for i, r in enumerate(results):
    print(f'\\n样本 {i+1}: {r.get(\"user_request\", \"\")}')
    print(f'  Plan: {r.get(\"plan\", \"N/A\")[:100]}')
    print(f'  Answer: {r.get(\"draft_answer\", \"N/A\")[:100]}')
    print(f'  Final: {r.get(\"final_answer\", \"N/A\")[:100]}')
"
```

### 5.3 预期结果
- 3 个样本全部成功执行
- planner 输出解题计划
- infer 根据计划计算答案
- checker 给出最终判定

> **注意**：由于使用 0.5B 小模型，推理质量可能不高，但只要流程跑通即可。

---

## 六、阶段 3 — SFT 训练

### 目标
验证 System-Level SFT 训练流程：数据准备 → ms-swift 训练 → 输出模型。

### 6.1 准备 SFT 数据集

数据集需要包含每个 Agent 的 ground truth：

```bash
cat > data/system_sft_dataset.jsonl << 'EOF'
{"input": {"user_request": "计算 23 × 47"}, "plan_gt": "步骤1: 计算 23×40=920\n步骤2: 计算 23×7=161\n步骤3: 920+161=1081", "draft_answer_gt": "23 × 47 = 1081", "final_answer_gt": "1081"}
{"input": {"user_request": "长方形长12cm宽8cm求面积"}, "plan_gt": "步骤1: 面积公式=长×宽\n步骤2: 12×8=96", "draft_answer_gt": "面积 = 12 × 8 = 96 平方厘米", "final_answer_gt": "96平方厘米"}
{"input": {"user_request": "解方程 2x+6=20"}, "plan_gt": "步骤1: 2x=20-6=14\n步骤2: x=14/2=7", "draft_answer_gt": "x = 7", "final_answer_gt": "x = 7"}
{"input": {"user_request": "100以内所有质数之和"}, "plan_gt": "步骤1: 列出100以内质数\n步骤2: 求和", "draft_answer_gt": "2+3+5+7+11+13+17+19+23+29+31+37+41+43+47+53+59+61+67+71+73+79+83+89+97 = 1060", "final_answer_gt": "1060"}
{"input": {"user_request": "3的5次方是多少"}, "plan_gt": "步骤1: 3^5 = 3×3×3×3×3\n步骤2: 计算结果", "draft_answer_gt": "3^5 = 243", "final_answer_gt": "243"}
EOF
```

### 6.2 运行 SFT 训练

```bash
python3 -c "
import json
from training.sft_trainer import SFTTrainer

trainer = SFTTrainer(output_dir='./training_outputs/sft')

# 加载配置
with open('examples/system_sft_config.json', 'r') as f:
    config = json.load(f)

# 定义超参数（小模型 + 小数据集，快速验证）
hyperparams = {
    'lr': 2e-4,
    'batch_size': 1,
    'num_epochs': 1,
    'max_length': 512,
    'save_steps': 10,
    'logging_steps': 1,
    'use_lora': True,
    'lora_rank': 8,
    'lora_alpha': 16,
}

# 启动 system-level 训练
result = trainer.train_system_level(
    config_json=config,
    dataset_file='data/system_sft_dataset.jsonl',
    default_hyperparameters=hyperparams,
    log_callback=lambda msg: print(msg)
)

print(f'\\n训练结果: {result[\"status\"]} - {result[\"overall_message\"]}')
"
```

### 6.3 预期结果
- 为 planner / infer / checker 各生成一份 SFT 训练数据
- 依次调用 `swift sft` 命令训练
- 训练完成后在 `training_outputs/sft/system_sft/run_xxx/` 下看到各 Agent 的训练输出

### 6.4 常见问题

| 问题 | 解决方案 |
|------|---------|
| `swift command not found` | `pip install ms-swift` |
| CUDA OOM | 减小 `batch_size` 到 1，减小 `max_length` |
| 数据集缓存冲突 | 代码已自动清理缓存，如仍报错可手动删 `~/.cache/huggingface/datasets` |

---

## 七、阶段 4 — DPO 训练

### 目标
验证 DPO 偏好训练流程：构建偏好对 → ms-swift DPO 训练。

### 7.1 准备 DPO 数据集

DPO 需要 chosen（教师/标准答案）和 rejected（学生/较差答案）对：

```bash
cat > data/system_dpo_dataset.jsonl << 'EOF'
{"input": {"user_request": "计算 23 × 47"}, "plan_gt": "步骤1: 23×40=920, 步骤2: 23×7=161, 步骤3: 920+161=1081", "draft_answer_gt": "23 × 47 = 1081", "final_answer_gt": "1081"}
{"input": {"user_request": "长方形长12cm宽8cm求面积"}, "plan_gt": "面积=长×宽=12×8=96", "draft_answer_gt": "面积 = 96 平方厘米", "final_answer_gt": "96平方厘米"}
{"input": {"user_request": "解方程 2x+6=20"}, "plan_gt": "2x=14, x=7", "draft_answer_gt": "x = 7", "final_answer_gt": "x = 7"}
{"input": {"user_request": "3的5次方"}, "plan_gt": "3^5=243", "draft_answer_gt": "243", "final_answer_gt": "243"}
{"input": {"user_request": "100的一半是多少"}, "plan_gt": "100/2=50", "draft_answer_gt": "50", "final_answer_gt": "50"}
EOF
```

### 7.2 运行 DPO 训练

```bash
python3 -c "
import json
from training.dpo_trainer import DPOTrainer

trainer = DPOTrainer(output_dir='./training_outputs/dpo')

with open('examples/system_dpo_config.json', 'r') as f:
    config = json.load(f)

hyperparams = {
    'lr': 5e-7,
    'batch_size': 1,
    'num_epochs': 1,
    'max_length': 512,
    'beta': 0.1,
    'use_lora': True,
    'lora_rank': 8,
    'lora_alpha': 16,
}

result = trainer.train_system_level(
    config_json=config,
    dataset_file='data/system_dpo_dataset.jsonl',
    trajectory_file=None,  # 没有轨迹文件时，只使用数据集 GT
    default_hyperparameters=hyperparams,
    log_callback=lambda msg: print(msg)
)

print(f'\\nDPO 训练结果: {result[\"status\"]} - {result[\"overall_message\"]}')
"
```

### 7.3 注意事项
- DPO 需要同时加载 policy 模型和 reference 模型，显存占用比 SFT 大
- 如果 OOM，确保 `batch_size=1` 并开启 `gradient_checkpointing`
- 没有轨迹文件时，DPO 数据生成可能跳过部分样本（需要 chosen ≠ rejected）

---

## 八、阶段 5 — GRPO 训练

### 目标
验证 GRPO 强化学习训练流程：rollout → reward 计算 → verl 训练。

### 8.1 准备 GRPO 数据集

```bash
cat > data/system_grpo_dataset.jsonl << 'EOF'
{"input": {"user_request": "计算 23 × 47"}, "final_answer_gt": "1081"}
{"input": {"user_request": "长方形长12cm宽8cm求面积"}, "final_answer_gt": "96平方厘米"}
{"input": {"user_request": "解方程 2x+6=20"}, "final_answer_gt": "x = 7"}
{"input": {"user_request": "3的5次方是多少"}, "final_answer_gt": "243"}
{"input": {"user_request": "100的一半"}, "final_answer_gt": "50"}
EOF
```

### 8.2 运行 GRPO 训练

```bash
python3 -c "
import json
from training.grpo_trainer import GRPOTrainer

trainer = GRPOTrainer(output_dir='./training_outputs/grpo')

with open('examples/system_grpo_config.json', 'r') as f:
    config = json.load(f)

hyperparams = {
    'lr': 1e-6,
    'batch_size': 1,
    'num_epochs': 1,
    'max_length': 512,
    'rollout_batch_size': 4,
    'mini_batch_size': 1,
    'kl_coef': 0.01,
    'clip_range': 0.2,
    'num_generations': 2,
}

result = trainer.train_system_level(
    config_json=config,
    dataset_file='data/system_grpo_dataset.jsonl',
    trajectory_file=None,
    default_hyperparameters=hyperparams,
    log_callback=lambda msg: print(msg)
)

print(f'\\nGRPO 训练结果: {result[\"status\"]} - {result[\"overall_message\"]}')
"
```

### 8.3 注意事项
- GRPO 依赖 verl + vLLM，环境要求最高
- 如果 verl 未安装，会报错 `verl not found`
- vLLM 需要 CUDA 12.1+ 和较新的 GPU 驱动
- 4090-48G 跑 0.5B 模型的 GRPO 应该没问题

---

## 九、Web UI 测试（可选）

如果想通过 Web 界面操作整个流程：

```bash
# 启动 Gradio Web UI
python3 main_web.py --host 0.0.0.0 --port 7860
```

然后在浏览器访问：
- 本地：`http://localhost:7860`
- AutoDL：通过「自定义服务」或 SSH 隧道访问

Web UI 功能模块：
1. **仪表盘** — 查看系统概览
2. **系统构建器** — 上传/编辑 JSON 配置
3. **数据资产** — 管理数据集
4. **执行中心** — 运行多 Agent 推理
5. **轨迹追溯** — 查看执行轨迹
6. **训练工厂** — 启动 SFT/DPO/GRPO 训练

---

## 十、测试检查清单

完成以下所有项即表示全流程跑通：

- [ ] 阶段 1：JSON 配置解析成功（3 个配置文件均通过）
- [ ] 阶段 2：推理执行成功（3 个样本全部输出结果）
- [ ] 阶段 3：SFT 训练完成（至少 1 个 Agent 训练成功）
- [ ] 阶段 4：DPO 训练完成（至少 1 个 Agent 训练成功）
- [ ] 阶段 5：GRPO 训练完成（至少 1 个 Agent 训练成功）
- [ ] Web UI 能正常启动并访问（可选）

---

## 十一、常见问题速查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `CUDA out of memory` | 显存不足 | 减小 batch_size / max_length，开启 LoRA |
| `swift command not found` | ms-swift 未安装 | `pip install ms-swift` |
| `verl not found` | verl 未安装 | `pip install verl` |
| 模型下载慢 | HuggingFace 网络问题 | 使用 modelscope 镜像或提前下载模型到本地 |
| 训练卡住不动 | 数据集缓存问题 | 代码已自动清理，也可手动删 `~/.cache/huggingface/datasets` |
| GRPO rollout 失败 | vLLM 不兼容 | 检查 CUDA 版本，确保 ≥12.1 |
| API Key 失效 | OPENAI_API_KEY 过期 | 更新 `.env` 文件中的 key |

---

## 十二、模型下载优化

如果 HuggingFace 下载模型太慢，可以预先下载：

```bash
# 使用 modelscope 下载（国内更快）
pip install modelscope

python3 -c "
from modelscope import snapshot_download
snapshot_download('Qwen/Qwen2.5-0.5B-Instruct', cache_dir='./models')
"
```

然后在 JSON 配置中使用本地路径：
```json
"model": {
    "name_or_path": "./models/Qwen/Qwen2.5-0.5B-Instruct"
}
```

---

## 十三、费用估算

| 项目 | 单价 | 预计耗时 | 费用 |
|------|------|---------|------|
| 4090-48G | ¥2.93/时 | 约 4-6 小时 | ¥12-18 |
| 系统盘 30GB | ¥0.10/日 | 1 天 | ¥0.10 |
| **合计** | | | **约 ¥12-18** |

> 建议先充值 ¥30-50，足够完成全流程测试。
