# runtime/agent_runner.py
from jinja2 import Template
from spec.system_spec import AgentSpec
from llm.base import BaseLLM
from llm.qwen_llm import QwenLLM
from llm.openai_llm import OpenAILLM
from typing import Optional, Tuple


class AgentRunner:
    def __init__(self, agent_spec: AgentSpec):
        self.spec = agent_spec

        # 学生模型（需要微调的模型）
        if agent_spec.model_provider == "qwen":
            self.student_llm = QwenLLM(agent_spec.get_model_name())
        elif agent_spec.model_provider == "openai":
            self.student_llm = OpenAILLM(agent_spec.get_model_name())
        else:
            raise ValueError(f"Unsupported student provider: {agent_spec.model_provider}")

        # 教师模型（用于生成 ground truth）
        self.teacher_llm: Optional[BaseLLM] = None
        if agent_spec.teacher_model:
            teacher_provider = agent_spec.teacher_model.provider or "qwen"
            if teacher_provider == "qwen":
                self.teacher_llm = QwenLLM(agent_spec.get_teacher_model_name())
            elif teacher_provider == "openai":
                self.teacher_llm = OpenAILLM(agent_spec.get_teacher_model_name())
            else:
                raise ValueError(f"Unsupported teacher provider: {teacher_provider}")

    def run_with_prompt(self, state: dict, use_teacher: bool = False) -> Tuple[str, str]:
        """运行代理，返回响应和渲染后的提示"""
        # 1. 创建 input_dict
        input_dict = {}
        for input_mapping in self.spec.input:
            key = input_mapping.key
            if key not in state:
                raise KeyError(f"Missing key '{key}' in state for agent '{self.spec.agent_id}'")
            input_dict[key] = state[key]

        # 2. 创建 context 包含 input 字典
        context = {"input": input_dict}

        # 3. 渲染 Prompt
        template = Template(self.spec.instruction_prompt.prompt_template)
        rendered_prompt = template.render(**context)

        # 4. 选择 LLM（教师或学生）
        if use_teacher and self.teacher_llm:
            llm_to_use = self.teacher_llm
            print(f"🎓 使用教师模型：{self.spec.get_teacher_model_name()}")
        else:
            llm_to_use = self.student_llm
            print(f"📚 使用学生模型：{self.spec.get_model_name()}")

        response = llm_to_use.generate(rendered_prompt, self.spec.temperature)

        return response, rendered_prompt

    def generate_teacher_response(self, state: dict) -> str:
        """专门用于教师模型生成 ground truth"""
        if not self.teacher_llm:
            raise RuntimeError("Teacher model not configured")

        response, _ = self.run_with_prompt(state, use_teacher=True)
        return response