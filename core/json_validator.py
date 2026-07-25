# core/json_validator.py
import json
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from spec.system_spec import SystemSpec, AgentSpec


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    agent_inputs: Dict[str, List[str]] = field(default_factory=dict)
    agent_outputs: Dict[str, List[str]] = field(default_factory=dict)
    
    def add_error(self, message: str):
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def to_dict(self) -> dict:
        return {
            'is_valid': self.is_valid and len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'execution_order': self.execution_order,
            'agent_inputs': self.agent_inputs,
            'agent_outputs': self.agent_outputs
        }


class JSONValidator:
    """JSON 配置校验器"""
    
    def __init__(self):
        self.result = ValidationResult()
    
    def validate(self, json_data: Any) -> ValidationResult:
        """
        校验 JSON 配置
        
        Args:
            json_data: JSON 数据 (可以是 dict, list 或 JSON 字符串)
            
        Returns:
            ValidationResult: 校验结果
        """
        self.result = ValidationResult()
        
        # 1. 解析 JSON
        data = self._parse_json(json_data)
        if data is None:
            return self.result
        
        # 2. 验证基本结构
        if not self._validate_structure(data):
            return self.result
        
        # 3. 使用 Pydantic 验证每个 Agent
        agents = self._validate_agents(data)
        if not agents:
            return self.result
        
        # 4. 验证数据流
        self._validate_dataflow(agents)
        
        # 5. 验证训练配置
        self._validate_training_config(agents)
        
        # 6. 构建执行图并检测循环
        self._build_execution_graph(agents)
        
        # 如果没有错误，标记为有效
        if not self.result.errors:
            self.result.is_valid = True
        
        return self.result
    
    def validate_file(self, file_path: str) -> ValidationResult:
        """从文件校验 JSON 配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.validate(content)
        except FileNotFoundError:
            self.result = ValidationResult()
            self.result.add_error(f"文件不存在: {file_path}")
            return self.result
        except Exception as e:
            self.result = ValidationResult()
            self.result.add_error(f"读取文件失败: {str(e)}")
            return self.result
    
    def _parse_json(self, json_data: Any) -> Optional[List[Dict]]:
        """解析 JSON 数据"""
        try:
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data
            
            if not isinstance(data, list):
                self.result.add_error("JSON 根元素必须是数组 (Agent 列表)")
                return None
            
            if len(data) == 0:
                self.result.add_error("Agent 列表不能为空")
                return None
            
            return data
            
        except json.JSONDecodeError as e:
            self.result.add_error(f"JSON 解析错误: {str(e)}")
            return None
        except Exception as e:
            self.result.add_error(f"解析失败: {str(e)}")
            return None
    
    def _validate_structure(self, data: List[Dict]) -> bool:
        """验证基本结构"""
        valid = True
        
        for i, agent in enumerate(data):
            # 检查必需字段
            if 'agent_id' not in agent:
                self.result.add_error(f"第 {i+1} 个 Agent 缺少 'agent_id' 字段")
                valid = False
            
            if 'model' not in agent:
                self.result.add_error(f"第 {i+1} 个 Agent 缺少 'model' 字段")
                valid = False
            
            if 'instruction_prompt' not in agent:
                self.result.add_error(f"第 {i+1} 个 Agent 缺少 'instruction_prompt' 字段")
                valid = False
            
            if 'input' not in agent:
                self.result.add_error(f"第 {i+1} 个 Agent 缺少 'input' 字段")
                valid = False
            
            if 'output' not in agent:
                self.result.add_error(f"第 {i+1} 个 Agent 缺少 'output' 字段")
                valid = False
        
        # 检查 agent_id 唯一性
        agent_ids = [a.get('agent_id') for a in data if 'agent_id' in a]
        if len(agent_ids) != len(set(agent_ids)):
            duplicates = [aid for aid in agent_ids if agent_ids.count(aid) > 1]
            self.result.add_error(f"存在重复的 agent_id: {set(duplicates)}")
            valid = False
        
        return valid
    
    def _validate_agents(self, data: List[Dict]) -> Optional[List[AgentSpec]]:
        """使用 Pydantic 验证每个 Agent"""
        agents = []
        
        for i, agent_data in enumerate(data):
            try:
                agent = AgentSpec(**agent_data)
                agents.append(agent)
                
                # 记录输入输出
                self.result.agent_inputs[agent.agent_id] = [
                    f"{inp.from_agent}.{inp.key}" for inp in agent.input
                ]
                self.result.agent_outputs[agent.agent_id] = [
                    out.key for out in agent.output
                ]
                
            except Exception as e:
                self.result.add_error(f"Agent '{agent_data.get('agent_id', f'#{i+1}')}' 验证失败: {str(e)}")
        
        return agents if agents else None
    
    def _validate_dataflow(self, agents: List[AgentSpec]):
        """验证数据流连接"""
        agent_ids = {a.agent_id for a in agents}
        output_keys = {}  # key -> agent_id
        
        # 收集所有输出
        for agent in agents:
            for out in agent.output:
                if out.key in output_keys:
                    self.result.add_warning(
                        f"输出键 '{out.key}' 被多个 Agent 定义"
                    )
                output_keys[out.key] = agent.agent_id
        
        # 验证每个输入
        for agent in agents:
            for inp in agent.input:
                from_agent = inp.from_agent
                
                # 特殊值 'user' 表示用户输入
                if from_agent == 'user':
                    continue
                
                if from_agent not in agent_ids:
                    self.result.add_error(
                        f"Agent '{agent.agent_id}' 的输入引用了不存在的 Agent: '{from_agent}'"
                    )
        
        # 验证输出目标
        for agent in agents:
            for out in agent.output:
                for target in out.to:
                    if target.agent and target.agent not in agent_ids:
                        self.result.add_error(
                            f"Agent '{agent.agent_id}' 的输出 '{out.key}' 指向不存在的 Agent: '{target.agent}'"
                        )
    
    def _validate_training_config(self, agents: List[AgentSpec]):
        """验证训练配置"""
        has_training = False
        
        for agent in agents:
            if agent.training:
                has_training = True
                
                # 验证训练模式
                if agent.training.mode not in ['sft', 'dpo', 'grpo']:
                    self.result.add_error(
                        f"Agent '{agent.agent_id}' 的训练模式必须是 'sft', 'dpo' 或 'grpo'"
                    )
                
                # SFT 需要 ground_truth
                if agent.training.mode == 'sft':
                    if not agent.training.ground_truth:
                        self.result.add_error(
                            f"Agent '{agent.agent_id}' 的 SFT 训练需要配置 ground_truth"
                        )
        
        if has_training:
            self.result.add_warning("检测到训练配置，请确保数据集格式正确")
    
    def _build_execution_graph(self, agents: List[AgentSpec]):
        """构建执行图并检测循环依赖"""
        G = nx.DiGraph()
        
        # 添加节点
        for agent in agents:
            G.add_node(agent.agent_id)
        
        # 添加边 (基于输入输出依赖)
        for agent in agents:
            for inp in agent.input:
                if inp.from_agent != 'user':
                    G.add_edge(inp.from_agent, agent.agent_id)
        
        # 检测循环
        try:
            cycles = list(nx.simple_cycles(G))
            if cycles:
                for cycle in cycles:
                    self.result.add_error(f"检测到循环依赖: {' -> '.join(cycle)}")
            else:
                # 拓扑排序
                self.result.execution_order = list(nx.topological_sort(G))
        except Exception as e:
            self.result.add_error(f"执行图分析失败: {str(e)}")
    
    def get_dataflow_graph(self, json_data: Any) -> Dict:
        """
        获取数据流图 (用于可视化)
        
        Returns:
            {
                'nodes': [{'id': str, 'label': str, 'type': str}],
                'edges': [{'from': str, 'to': str, 'label': str}]
            }
        """
        result = self.validate(json_data)
        
        if not result.is_valid:
            return {'error': result.errors}
        
        data = self._parse_json(json_data)
        if not data:
            return {'error': ['解析失败']}
        
        nodes = []
        edges = []
        
        # 添加用户节点
        nodes.append({
            'id': 'user',
            'label': 'User Input',
            'type': 'input'
        })
        
        # 添加 Agent 节点
        for agent_data in data:
            agent_id = agent_data.get('agent_id')
            nodes.append({
                'id': agent_id,
                'label': agent_id,
                'type': 'agent'
            })
            
            # 添加输入边
            for inp in agent_data.get('input', []):
                from_agent = inp.get('from')
                key = inp.get('key')
                if from_agent:
                    edges.append({
                        'from': from_agent,
                        'to': agent_id,
                        'label': key
                    })
            
            # 添加输出边
            for out in agent_data.get('output', []):
                key = out.get('key')
                for target in out.get('to', []):
                    if target.get('user'):
                        edges.append({
                            'from': agent_id,
                            'to': 'output',
                            'label': key
                        })
                    elif target.get('agent'):
                        edges.append({
                            'from': agent_id,
                            'to': target.get('agent'),
                            'label': f"{key} -> {target.get('as', key)}"
                        })
        
        # 添加输出节点
        if any(e['to'] == 'output' for e in edges):
            nodes.append({
                'id': 'output',
                'label': 'Final Output',
                'type': 'output'
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'execution_order': result.execution_order
        }
