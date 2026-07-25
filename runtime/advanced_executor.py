# runtime/advanced_executor.py
"""
高级执行引擎 - 支持分支、循环、条件跳转
"""
import json
import re
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NodeType(Enum):
    """节点类型"""
    NORMAL = "normal"
    BRANCH = "branch"
    LOOP = "loop"
    LOOP_CONTROLLER = "loop_controller"


@dataclass
class ExecutionContext:
    """执行上下文"""
    state: Dict[str, Any] = field(default_factory=dict)
    iteration_count: Dict[str, int] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    loop_stack: List[str] = field(default_factory=list)
    
    def get(self, key: str, default=None):
        """获取状态值"""
        return self.state.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置状态值"""
        self.state[key] = value
    
    def increment_iteration(self, loop_id: str) -> int:
        """增加迭代计数"""
        self.iteration_count[loop_id] = self.iteration_count.get(loop_id, 0) + 1
        return self.iteration_count[loop_id]
    
    def get_iteration(self, loop_id: str) -> int:
        """获取当前迭代次数"""
        return self.iteration_count.get(loop_id, 0)


class ConditionEvaluator:
    """条件表达式求值器"""
    
    @staticmethod
    def evaluate(condition: str, context: ExecutionContext) -> bool:
        """
        评估条件表达式
        
        支持的条件格式：
        - {{input.key}} == 'value'
        - {{input.key}} > 5
        - {{input.score}} >= 8 && {{input.iteration}} < 3
        - {{input.flag}} == true
        """
        if not condition:
            return True
        
        # 替换模板变量
        def replace_var(match):
            var_path = match.group(1).strip()
            # 处理 input.xxx 格式
            if var_path.startswith('input.'):
                key = var_path[6:]  # 去掉 'input.'
                value = context.get(key)
                return json.dumps(value) if value is not None else 'null'
            return match.group(0)
        
        # 替换 {{...}} 格式
        expr = re.sub(r'\{\{(.+?)\}\}', replace_var, condition)
        
        # 替换布尔值
        expr = expr.replace('true', 'True').replace('false', 'False')
        expr = expr.replace('&&', ' and ').replace('||', ' or ')
        expr = expr.replace('==', '==').replace('!=', '!=')
        
        try:
            # 安全求值
            result = eval(expr, {"__builtins__": {}}, {})
            return bool(result)
        except Exception as e:
            print(f"条件求值错误: {expr}, 错误: {e}")
            return False


class AdvancedExecutor:
    """高级执行引擎"""
    
    def __init__(self, config: List[Dict], llm_callback: Optional[Callable] = None):
        """
        初始化执行引擎
        
        Args:
            config: Agent 配置列表
            llm_callback: LLM 调用回调函数 (prompt, system_prompt) -> response
        """
        self.config = config
        self.agents = {a['agent_id']: a for a in config}
        self.llm_callback = llm_callback or self._default_llm_callback
        self.condition_evaluator = ConditionEvaluator()
        
    def _default_llm_callback(self, prompt: str, system_prompt: str = "") -> str:
        """默认 LLM 回调（模拟）"""
        return f"[模拟响应] System: {system_prompt[:30]}... Prompt: {prompt[:50]}..."
    
    def execute(self, user_input: Dict[str, Any], 
                max_steps: int = 100) -> Dict[str, Any]:
        """
        执行多 Agent 系统
        
        Args:
            user_input: 用户输入
            max_steps: 最大执行步数（防止无限循环）
            
        Returns:
            执行结果
        """
        context = ExecutionContext()
        context.state = dict(user_input)
        
        execution_log = []
        step_count = 0
        
        # 找到入口 Agent（从 user 接收输入的）
        current_agent_id = self._find_entry_agent()
        
        while current_agent_id and step_count < max_steps:
            step_count += 1
            agent = self.agents.get(current_agent_id)
            
            if not agent:
                break
            
            print(f"\n[Step {step_count}] 执行 Agent: {current_agent_id}")
            
            # 执行 Agent
            result = self._execute_agent(agent, context)
            
            execution_log.append({
                'step': step_count,
                'agent_id': current_agent_id,
                'input': result['input'],
                'output': result['output'],
                'timestamp': datetime.now().isoformat()
            })
            
            # 确定下一个 Agent
            next_agent_id = self._determine_next_agent(agent, context, result)
            
            if next_agent_id is None:
                print(f"执行完成，共 {step_count} 步")
                break
                
            current_agent_id = next_agent_id
        
        if step_count >= max_steps:
            print(f"警告：达到最大步数限制 {max_steps}")
        
        return {
            'final_state': context.state,
            'execution_log': execution_log,
            'total_steps': step_count
        }
    
    def execute_batch(self, inputs: List[Dict[str, Any]], 
                      max_steps: int = 100) -> List[Dict[str, Any]]:
        """
        批量执行
        
        Args:
            inputs: 多个用户输入
            max_steps: 每输入最大步数
            
        Returns:
            每个输入的执行结果列表
        """
        results = []
        for i, user_input in enumerate(inputs):
            print(f"\n{'='*60}")
            print(f"处理第 {i+1}/{len(inputs)} 个输入")
            print(f"{'='*60}")
            result = self.execute(user_input, max_steps)
            results.append(result)
        return results
    
    def _find_entry_agent(self) -> Optional[str]:
        """找到入口 Agent（接收 user 输入的）"""
        for agent_id, agent in self.agents.items():
            inputs = agent.get('input', [])
            for inp in inputs:
                if inp.get('from') == 'user':
                    return agent_id
        # 默认返回第一个
        return list(self.agents.keys())[0] if self.agents else None
    
    def _execute_agent(self, agent: Dict, context: ExecutionContext) -> Dict[str, Any]:
        """执行单个 Agent"""
        agent_id = agent['agent_id']
        
        # 准备输入数据
        input_data = self._prepare_input(agent, context)
        
        # 渲染 prompt
        prompt_template = agent.get('instruction_prompt', {}).get('prompt_template', '')
        prompt = self._render_template(prompt_template, input_data)
        
        system_prompt = agent.get('instruction_prompt', {}).get('instruction', '')
        
        # 调用 LLM，传入 Agent 配置以便使用正确的模型
        response = self.llm_callback(prompt, system_prompt, agent)
        
        # 处理输出
        output_config = agent.get('output', [])
        output_data = {}
        
        if output_config:
            # 假设第一个输出键为主输出
            main_key = output_config[0].get('key', 'output')
            output_data[main_key] = response
            context.set(main_key, response)
        
        return {
            'input': input_data,
            'prompt': prompt,
            'response': response,
            'output': output_data
        }
    
    def _prepare_input(self, agent: Dict, context: ExecutionContext) -> Dict[str, Any]:
        """准备 Agent 输入数据"""
        input_data = {}
        
        for inp in agent.get('input', []):
            from_source = inp.get('from')
            key = inp.get('key')
            alias = inp.get('as', key)
            
            if from_source == 'user':
                input_data[alias] = context.get(key)
            elif from_source in self.agents:
                # 从其他 Agent 的输出获取
                input_data[alias] = context.get(key)
            elif from_source == 'self':
                # 从自身状态获取（用于循环）
                input_data[alias] = context.get(key)
        
        return input_data
    
    def _render_template(self, template: str, data: Dict) -> str:
        """渲染模板"""
        result = template
        
        # 处理 {{input.xxx}} 格式
        def replace_input(match):
            key = match.group(1).strip()
            if key.startswith('input.'):
                key = key[6:]
            value = data.get(key, '')
            return str(value) if value is not None else ''
        
        result = re.sub(r'\{\{(.+?)\}\}', replace_input, result)
        return result
    
    def _determine_next_agent(self, current_agent: Dict, 
                              context: ExecutionContext,
                              result: Dict) -> Optional[str]:
        """确定下一个要执行的 Agent"""
        agent_type = current_agent.get('type', 'normal')
        
        # 处理分支节点
        if agent_type == 'branch' or 'branches' in current_agent:
            return self._handle_branch(current_agent, context)
        
        # 处理循环控制器
        if agent_type == 'loop_controller' or 'loop' in current_agent:
            return self._handle_loop(current_agent, context)
        
        # 普通节点：按输出配置确定下一个
        output_config = current_agent.get('output', [])
        if output_config and output_config[0].get('to'):
            targets = output_config[0]['to']
            for target in targets:
                if target.get('agent'):
                    return target['agent']
                elif target.get('user'):
                    return None  # 输出给用户，结束
        
        return None
    
    def _handle_branch(self, agent: Dict, context: ExecutionContext) -> Optional[str]:
        """处理分支逻辑"""
        branches = agent.get('branches', {})
        conditions = branches.get('conditions', [])
        default_target = branches.get('default')
        
        print(f"  评估分支条件...")
        
        for branch in conditions:
            condition = branch.get('condition', '')
            target = branch.get('target')
            
            if self.condition_evaluator.evaluate(condition, context):
                print(f"  条件满足: {condition} -> {target}")
                return target
        
        print(f"  使用默认分支: {default_target}")
        return default_target
    
    def _handle_loop(self, agent: Dict, context: ExecutionContext) -> Optional[str]:
        """处理循环逻辑"""
        loop_config = agent.get('loop', agent.get('loop_config', {}))
        agent_id = agent['agent_id']
        
        # 增加迭代计数
        iteration = context.increment_iteration(agent_id)
        max_iterations = loop_config.get('max_iterations', 3)
        
        print(f"  循环迭代: {iteration}/{max_iterations}")
        
        # 评估循环条件
        condition = loop_config.get('condition', '')
        should_continue = self.condition_evaluator.evaluate(condition, context)
        
        if should_continue and iteration < max_iterations:
            # 继续循环
            on_continue = loop_config.get('on_continue', {})
            next_agent = on_continue.get('next', agent_id)
            
            # 更新循环变量
            output_mapping = on_continue.get('output', {})
            for key, expr in output_mapping.items():
                # 简单表达式求值
                if ' + 1' in expr:
                    current_val = context.get(key, 0)
                    context.set(key, current_val + 1)
                else:
                    context.set(key, expr)
            
            print(f"  继续循环 -> {next_agent}")
            return next_agent
        else:
            # 退出循环
            on_exit = loop_config.get('on_exit', {})
            next_agent = on_exit.get('next')
            
            # 设置最终输出
            output_mapping = on_exit.get('output', {})
            for key, expr in output_mapping.items():
                if expr == 'last_solution':
                    context.set(key, context.get('solution'))
                elif expr == 'critic_feedback.score':
                    feedback = context.get('critic_feedback', {})
                    context.set(key, feedback.get('score'))
            
            print(f"  退出循环 -> {next_agent}")
            return next_agent


# 便捷函数
def execute_config(config: List[Dict], user_input: Dict[str, Any],
                   llm_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """便捷执行函数"""
    executor = AdvancedExecutor(config, llm_callback)
    return executor.execute(user_input)


def execute_batch(config: List[Dict], inputs: List[Dict[str, Any]],
                  llm_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """便捷批量执行函数"""
    executor = AdvancedExecutor(config, llm_callback)
    return executor.execute_batch(inputs)
