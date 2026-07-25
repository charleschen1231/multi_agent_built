# spec/system_spec.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import json


# --- 训练配置子模型（必须先定义被引用的类）---
class LossConfig(BaseModel):
    type: str = "ce"
    weight: float = 1.0


class TrainParams(BaseModel):
    lr: float = 2e-5
    batch_size: int = 4
    num_epochs: int = 3


class DatasetConfig(BaseModel):
    input_key: str


class GroundTruthConfig(BaseModel):
    output_key: str
    gt_key: str  # 数据集中真实标签的键名
    use_teacher_generation: bool = False  # 是否使用教师模型生成 ground truth


class TrainingConfig(BaseModel):
    mode: str = "sft"
    trainable: bool = True
    dataset: Optional[DatasetConfig] = None
    ground_truth: Optional[GroundTruthConfig] = None
    loss: Optional[LossConfig] = None
    train_parameters: Optional[TrainParams] = None


# --- 输入输出映射 ---
class IOMapping(BaseModel):
    from_agent: str = Field(..., alias="from")  # 处理 JSON 中的 "from" 关键字
    key: str

    class Config:
        populate_by_name = True


class OutputMappingTarget(BaseModel):
    agent: Optional[str] = None
    user: Optional[bool] = False
    as_key: Optional[str] = Field(None, alias="as")

    class Config:
        populate_by_name = True


class OutputMapping(BaseModel):
    key: str
    to: List[OutputMappingTarget]


# --- Agent 定义 ---
class PromptConfig(BaseModel):
    instruction: str
    prompt_template: str


class ModelConfig(BaseModel):
    name_or_path: str
    provider: Optional[str] = "qwen"


class TeacherModelConfig(BaseModel):
    name_or_path: str
    provider: Optional[str] = "qwen"


class AgentSpec(BaseModel):
    agent_id: str
    model: ModelConfig
    instruction_prompt: PromptConfig
    input: List[IOMapping]
    output: List[OutputMapping]
    training: Optional[TrainingConfig] = None
    teacher_model: Optional[TeacherModelConfig] = None  # 教师模型配置（用于蒸馏）

    # 兼容 Phase 1 的简单字段 (如果用户混用)
    model_provider: Optional[str] = "qwen"
    temperature: float = 0.7

    def get_model_name(self) -> str:
        return self.model.name_or_path

    def get_teacher_model_name(self) -> Optional[str]:
        if self.teacher_model:
            return self.teacher_model.name_or_path
        return None


# --- 系统配置 (关键修复!) ---
class SystemSpec(BaseModel):
    agents: List[AgentSpec]

    @classmethod
    def from_file(cls, file_path: str) -> 'SystemSpec':
        """从 JSON 文件加载系统配置"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(agents=data)


# --- 辅助函数 (保持不变) ---
def load_agent_list(json_data: List[Dict]) -> List[AgentSpec]:
    """从 JSON 数据加载 Agent 列表"""
    return [AgentSpec(**item) for item in json_data]