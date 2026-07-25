# Multi-Agent System Builder

基于 JSON 配置驱动的多智能体系统构建平台，支持 Agent 编排、SFT/DPO/GRPO 训练及效果验证的一体化工作流。

## 功能特性

- **JSON 配置驱动**：通过 JSON 文件定义多 Agent 系统的数据流、模型、提示词和训练参数
- **可视化编排**：Web 界面直观展示 Agent 间的依赖关系与数据流向
- **多模型支持**：支持本地模型（Qwen/LLaMA 等）和云端 API（OpenAI/Qwen API）
- **完整训练链路**：内置 SFT（监督微调）、DPO（直接偏好优化）、GRPO（强化学习）三种训练范式
- **效果验证**：训练完成后自动进行蒸馏效果验证与评估
- **JWT 认证**：企业级 API 安全认证机制

## 系统架构

```
├── cli/              # 命令行工具（推理 / SFT 训练）
├── configs/          # API 配置文件
├── core/             # 核心模块（JSON 校验、轨迹生成、批量处理、提示词优化）
├── data/             # 数据集管理与格式转换
├── database/         # 数据库模型与管理器（SQLite + SQLAlchemy）
├── evaluation/       # 评估模块
├── examples/         # 配置示例（SFT / DPO / GRPO）
├── llm/              # LLM 抽象层（本地模型 / OpenAI / Qwen API）
├── rollout/          # 轨迹录制
├── runtime/          # 运行时引擎（Agent 执行、状态管理）
├── spec/             # 系统规格解析与数据流图构建
├── static/           # Web 前端（HTML / CSS / JS）
├── training/         # 训练模块（SFT / DPO / GRPO Trainer）
├── web/              # Web 页面组件
├── main_api.py       # FastAPI 后端入口
└── main.py           # 命令行入口
```

## 快速开始

### 环境要求

- Python 3.10+
- CUDA GPU（用于本地模型推理与训练）

### 安装依赖

```bash
pip install -r requirements.txt
```

如需 GRPO 训练，额外安装：

```bash
pip install verl
```

### 配置 API Key

编辑 `configs/api_config.yaml`，填入你的 API Key：

```yaml
qwen_api_key: "your-qwen-api-key"
openai_api_key: "your-openai-api-key"
```

### 启动服务

```bash
python main_api.py
```

访问 `http://localhost:8000` 打开 Web 界面。

### 命令行使用

```bash
# 执行推理
python -m cli.run_infer --config examples/system_sft_config.json

# 执行 SFT 训练
python -m cli.run_sft --config examples/system_sft_config.json
```

## 配置说明

每个 Agent 在 JSON 配置中定义以下字段：

| 字段 | 说明 |
|------|------|
| `agent_id` | Agent 唯一标识 |
| `model.name_or_path` | 模型路径（以 `/` 开头为本地模型，否则为 API 模型名） |
| `instruction_prompt` | 系统指令与提示词模板（支持 `{{input.xxx}}` 变量引用） |
| `input` | 输入来源（`from: "user"` 或上游 Agent ID） |
| `output` | 输出目标（指定下游 Agent 及参数名） |
| `training` | 训练配置（mode / dataset / ground_truth / loss / train_parameters） |

完整示例参见 `examples/` 目录。

## 训练流程

1. **准备数据集**：将训练数据放置于 `data/` 目录，格式为 JSONL
2. **配置训练参数**：在系统配置 JSON 中为每个 Agent 设置 `training` 字段
3. **启动训练**：通过 Web 界面或命令行触发 SFT / DPO / GRPO 训练
4. **验证效果**：训练完成后使用「验证蒸馏效果」功能对比训练前后表现

## 项目结构

```
multi_agent_built/
├── main_api.py          # FastAPI 服务入口（含认证、训练、评估 API）
├── main.py              # 命令行入口
├── requirements.txt     # Python 依赖
├── configs/             # 配置文件
├── core/                # 核心业务逻辑
├── data/                # 数据集
├── database/            # 数据库层
├── evaluation/          # 评估模块
├── examples/            # 示例配置
├── llm/                 # 大模型适配层
├── runtime/             # 运行时引擎
├── spec/                # 配置解析与数据流图
├── static/              # 前端静态资源
├── training/            # 训练模块
└── web/                 # Web 页面组件
```

## License

Private. All rights reserved.
