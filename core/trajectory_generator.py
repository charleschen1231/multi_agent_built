# core/trajectory_generator.py
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from spec.system_spec import SystemSpec, AgentSpec
from core.json_validator import JSONValidator

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# OpenAI 客户端
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or os.getenv('openai-apikey')
    openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except:
    openai_client = None


@dataclass
class TrajectoryStep:
    """轨迹步骤"""
    step_index: int
    agent_id: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    prompt: str = ""
    response: str = ""
    output_data: Dict[str, Any] = field(default_factory=dict)
    ground_truth: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trajectory:
    """完整轨迹"""
    trajectory_id: str
    sample_id: int
    config_id: int
    input_request: Dict[str, Any] = field(default_factory=dict)
    steps: List[TrajectoryStep] = field(default_factory=list)
    final_output: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            'trajectory_id': self.trajectory_id,
            'sample_id': self.sample_id,
            'config_id': self.config_id,
            'input_request': self.input_request,
            'steps': [s.to_dict() for s in self.steps],
            'final_output': self.final_output,
            'created_at': self.created_at
        }
    
    def add_step(self, step: TrajectoryStep):
        self.steps.append(step)
    
    def get_agent_outputs(self, agent_id: str) -> List[TrajectoryStep]:
        """获取指定 Agent 的所有输出"""
        return [s for s in self.steps if s.agent_id == agent_id]


class TrajectoryGenerator:
    """轨迹生成器"""
    
    def __init__(self, system_spec: SystemSpec, config_id: int = None):
        self.spec = system_spec
        self.config_id = config_id
        self.agents = {a.agent_id: a for a in system_spec.agents}
        self.execution_order = self._get_execution_order()
        self.validator = JSONValidator()
    
    def _get_execution_order(self) -> List[str]:
        """获取执行顺序"""
        validator = JSONValidator()
        result = validator.validate([a.model_dump() for a in self.spec.agents])
        return result.execution_order if result.execution_order else list(self.agents.keys())
    
    def generate_trajectory(self, user_request: Dict[str, Any],
                           sample_id: int = 0,
                           use_teacher: bool = False,
                           teacher_outputs: Dict[str, str] = None) -> Trajectory:
        """
        为单个输入生成轨迹
        
        Args:
            user_request: 用户请求数据
            sample_id: 样本ID
            use_teacher: 是否使用教师模型输出
            teacher_outputs: 预生成的教师模型输出
            
        Returns:
            Trajectory: 生成的轨迹
        """
        trajectory_id = f"traj_{self.config_id}_{sample_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        trajectory = Trajectory(
            trajectory_id=trajectory_id,
            sample_id=sample_id,
            config_id=self.config_id or 0,
            input_request=user_request
        )
        
        # 状态容器
        state = dict(user_request)
        
        # 按顺序执行每个 Agent
        for step_idx, agent_id in enumerate(self.execution_order):
            agent = self.agents.get(agent_id)
            if not agent:
                continue
            
            # 准备输入
            input_data = self._prepare_input(agent, state)
            
            # 渲染 prompt
            prompt = self._render_prompt(agent, input_data)
            
            # 获取输出 (调用 OpenAI API)
            if use_teacher and teacher_outputs and agent_id in teacher_outputs:
                response = teacher_outputs[agent_id]
            elif openai_client:
                # 调用 OpenAI API
                try:
                    system_prompt = agent.instruction_prompt.instruction
                    response = self._call_openai(system_prompt, prompt)
                except Exception as e:
                    response = f"[Error calling OpenAI: {str(e)}]"
            else:
                # 模拟响应
                response = f"[Simulated response from {agent_id}]"
            
            # 获取 ground truth (如果配置了教师模型)
            ground_truth = None
            if agent.training and agent.training.ground_truth:
                gt_key = agent.training.ground_truth.gt_key
                if gt_key in user_request:
                    ground_truth = user_request[gt_key]
            
            # 确定输出键
            output_key = agent.output[0].key if agent.output else "output"
            output_data = {output_key: response}
            
            # 更新状态
            state[output_key] = response
            
            # 创建轨迹步骤
            step = TrajectoryStep(
                step_index=step_idx,
                agent_id=agent_id,
                input_data=input_data,
                prompt=prompt,
                response=response,
                output_data=output_data,
                ground_truth=ground_truth,
                metadata={
                    'model': agent.get_model_name(),
                    'teacher_model': agent.get_teacher_model_name(),
                    'loss_weight': agent.training.loss.weight if agent.training and agent.training.loss else 1.0
                }
            )
            
            trajectory.add_step(step)
        
        # 收集最终输出
        trajectory.final_output = self._collect_final_output(state)
        
        return trajectory
    
    def generate_batch(self, user_requests: List[Dict[str, Any]],
                      use_teacher: bool = False) -> List[Trajectory]:
        """
        批量生成轨迹
        
        Args:
            user_requests: 用户请求列表
            use_teacher: 是否使用教师模型
            
        Returns:
            List[Trajectory]: 轨迹列表
        """
        trajectories = []
        
        for i, request in enumerate(user_requests):
            trajectory = self.generate_trajectory(
                user_request=request,
                sample_id=i,
                use_teacher=use_teacher
            )
            trajectories.append(trajectory)
        
        return trajectories
    
    def _prepare_input(self, agent: AgentSpec, state: Dict[str, Any]) -> Dict[str, Any]:
        """准备 Agent 输入"""
        input_data = {}
        
        for inp in agent.input:
            key = inp.key
            from_source = inp.from_agent  # 使用 from_agent 字段
            
            # 根据 from_agent 字段决定数据来源
            if from_source == "user":
                # 从用户输入获取
                if key in state:
                    input_data[key] = state[key]
                else:
                    input_data[key] = None
            else:
                # 从其他 agent 的输出获取
                if key in state:
                    input_data[key] = state[key]
                else:
                    input_data[key] = None
        
        return input_data
    
    def _render_prompt(self, agent: AgentSpec, input_data: Dict[str, Any]) -> str:
        """渲染 Prompt"""
        from jinja2 import Template
        
        context = {"input": input_data}
        template = Template(agent.instruction_prompt.prompt_template)
        return template.render(**context)
    
    def _call_openai(self, system_prompt: str, user_prompt: str, model: str = "gpt-4o") -> str:
        """调用 OpenAI API"""
        if not openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    
    def _collect_final_output(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """收集最终输出"""
        final_output = {}
        
        # 找到最后一个 Agent 的输出
        if self.execution_order:
            last_agent_id = self.execution_order[-1]
            last_agent = self.agents.get(last_agent_id)
            if last_agent and last_agent.output:
                for out in last_agent.output:
                    key = out.key
                    if key in state:
                        final_output[key] = state[key]
        
        return final_output
    
    def export_to_sft_format(self, trajectories: List[Trajectory],
                            output_file: str) -> str:
        """
        导出为 SFT 训练格式 (ms-swift 兼容)
        
        Args:
            trajectories: 轨迹列表
            output_file: 输出文件路径
            
        Returns:
            str: 输出文件路径
        """
        sft_data = []
        
        for traj in trajectories:
            for step in traj.steps:
                if step.ground_truth:
                    sft_data.append({
                        'instruction': step.prompt,
                        'input': '',
                        'output': step.ground_truth,
                        'history': [],
                        'system': self.agents.get(step.agent_id, {}).instruction_prompt.instruction if step.agent_id in self.agents else '',
                        'metadata': {
                            'agent_id': step.agent_id,
                            'trajectory_id': traj.trajectory_id,
                            'sample_id': traj.sample_id
                        }
                    })
        
        # 保存为 JSONL
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in sft_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        return output_file
    
    def export_to_dpo_format(self, trajectories: List[Trajectory],
                            output_file: str) -> str:
        """
        导出为 DPO 训练格式
        
        Args:
            trajectories: 轨迹列表
            output_file: 输出文件路径
            
        Returns:
            str: 输出文件路径
        """
        dpo_data = []
        
        for traj in trajectories:
            for step in traj.steps:
                if step.ground_truth and step.response != step.ground_truth:
                    dpo_data.append({
                        'instruction': step.prompt,
                        'input': '',
                        'chosen': step.ground_truth,  # 更好的回答
                        'rejected': step.response,     # 较差的回答
                        'metadata': {
                            'agent_id': step.agent_id,
                            'trajectory_id': traj.trajectory_id
                        }
                    })
        
        # 保存为 JSONL
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in dpo_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        return output_file
    
    def export_to_grpo_format(self, trajectories: List[Trajectory],
                             output_file: str) -> str:
        """
        导出为 GRPO 训练格式
        
        Args:
            trajectories: 轨迹列表
            output_file: 输出文件路径
            
        Returns:
            str: 输出文件路径
        """
        grpo_data = []
        
        for traj in trajectories:
            # GRPO 需要完整的轨迹
            steps_data = []
            for step in traj.steps:
                steps_data.append({
                    'agent_id': step.agent_id,
                    'prompt': step.prompt,
                    'response': step.response,
                    'ground_truth': step.ground_truth,
                    'metadata': step.metadata
                })
            
            grpo_data.append({
                'trajectory_id': traj.trajectory_id,
                'input_request': traj.input_request,
                'steps': steps_data,
                'final_output': traj.final_output
            })
        
        # 保存为 JSON
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(grpo_data, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def get_statistics(self, trajectories: List[Trajectory]) -> Dict[str, Any]:
        """获取轨迹统计信息"""
        stats = {
            'total_trajectories': len(trajectories),
            'total_steps': sum(len(t.steps) for t in trajectories),
            'agents_involved': set(),
            'avg_steps_per_trajectory': 0,
            'has_ground_truth': 0
        }
        
        for traj in trajectories:
            for step in traj.steps:
                stats['agents_involved'].add(step.agent_id)
                if step.ground_truth:
                    stats['has_ground_truth'] += 1
        
        if trajectories:
            stats['avg_steps_per_trajectory'] = stats['total_steps'] / len(trajectories)
        
        stats['agents_involved'] = list(stats['agents_involved'])
        
        return stats
