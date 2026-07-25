# core/prompt_optimizer.py
"""
Prompt 优化器 - 使用 GPT-4o 优化系统 Prompt
"""
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# OpenAI 客户端
try:
    from openai import OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') or os.getenv('openai-apikey')
    openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except:
    openai_client = None


@dataclass
class OptimizationResult:
    """优化结果"""
    original_instruction: str
    original_template: str
    optimized_instruction: str
    optimized_template: str
    improvements: List[str]
    reasoning: str


class PromptOptimizer:
    """Prompt 优化器"""
    
    # 优化提示词模板
    OPTIMIZATION_SYSTEM_PROMPT = """你是专业的 Prompt 优化专家。你的任务是优化 Multi-Agent System 中的 Agent Prompt。

优化原则：
1. 明确性：指令应该清晰、具体、无歧义
2. 结构化：使用清晰的结构和格式
3. 上下文感知：充分利用输入变量
4. 输出规范：明确指定输出格式和要求
5. 角色一致性：保持 Agent 角色定位清晰

请分析原始 Prompt 的问题，并提供优化后的版本。输出必须是 JSON 格式。"""

    OPTIMIZATION_USER_TEMPLATE = """请优化以下 Agent 的 Prompt：

【Agent ID】
{agent_id}

【原始 Instruction】
{instruction}

【原始 Prompt Template】
{template}

【输入变量】
{input_vars}

【输出要求】
{output_requirements}

【上下文信息】
- 该 Agent 在系统中的位置：{position}
- 前置 Agent：{prev_agents}
- 后置 Agent：{next_agents}

请提供优化后的 Prompt，并解释改进点。输出格式：
{{
    "optimized_instruction": "优化后的系统指令",
    "optimized_template": "优化后的提示词模板",
    "improvements": ["改进点1", "改进点2", ...],
    "reasoning": "优化思路说明"
}}"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化优化器
        
        Args:
            api_key: OpenAI API Key，如果不提供则使用环境变量
        """
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = openai_client
        
        if not self.client:
            raise ValueError("未配置 OpenAI API Key")
    
    def optimize_agent_prompt(self, agent_config: Dict[str, Any],
                             system_context: Dict[str, Any] = None) -> OptimizationResult:
        """
        优化单个 Agent 的 Prompt
        
        Args:
            agent_config: Agent 配置
            system_context: 系统上下文信息
            
        Returns:
            优化结果
        """
        agent_id = agent_config.get('agent_id', 'unknown')
        instruction = agent_config.get('instruction_prompt', {}).get('instruction', '')
        template = agent_config.get('instruction_prompt', {}).get('prompt_template', '')
        
        # 准备输入变量描述
        input_vars = []
        for inp in agent_config.get('input', []):
            var_desc = f"- {inp.get('key')} (来自 {inp.get('from')})"
            if inp.get('as'):
                var_desc += f" [别名为 {inp.get('as')}]"
            input_vars.append(var_desc)
        
        # 准备输出要求描述
        output_reqs = []
        for out in agent_config.get('output', []):
            req_desc = f"- {out.get('key')}"
            targets = out.get('to', [])
            if targets:
                target_names = [t.get('agent', 'user') for t in targets]
                req_desc += f" -> {', '.join(target_names)}"
            output_reqs.append(req_desc)
        
        # 准备上下文信息
        context = system_context or {}
        
        # 构建优化提示
        user_prompt = self.OPTIMIZATION_USER_TEMPLATE.format(
            agent_id=agent_id,
            instruction=instruction,
            template=template,
            input_vars='\n'.join(input_vars) if input_vars else '无',
            output_requirements='\n'.join(output_reqs) if output_reqs else '无特定要求',
            position=context.get('position', '中间节点'),
            prev_agents=', '.join(context.get('prev_agents', ['user'])),
            next_agents=', '.join(context.get('next_agents', ['output']))
        )
        
        # 调用 GPT-4o
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.OPTIMIZATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return OptimizationResult(
                original_instruction=instruction,
                original_template=template,
                optimized_instruction=result.get('optimized_instruction', instruction),
                optimized_template=result.get('optimized_template', template),
                improvements=result.get('improvements', []),
                reasoning=result.get('reasoning', '')
            )
            
        except Exception as e:
            print(f"优化失败: {e}")
            # 返回原始配置
            return OptimizationResult(
                original_instruction=instruction,
                original_template=template,
                optimized_instruction=instruction,
                optimized_template=template,
                improvements=[f"优化失败: {str(e)}"],
                reasoning=""
            )
    
    def optimize_system_prompts(self, config: List[Dict[str, Any]]) -> List[OptimizationResult]:
        """
        优化整个系统的所有 Agent Prompt
        
        Args:
            config: 系统配置（Agent 列表）
            
        Returns:
            每个 Agent 的优化结果列表
        """
        results = []
        
        # 构建 Agent 关系图
        agent_ids = [a['agent_id'] for a in config]
        
        for i, agent in enumerate(config):
            agent_id = agent['agent_id']
            print(f"\n优化 Agent: {agent_id}")
            
            # 确定上下文信息
            prev_agents = []
            next_agents = []
            
            for inp in agent.get('input', []):
                if inp.get('from') != 'user':
                    prev_agents.append(inp['from'])
            
            for out in agent.get('output', []):
                for target in out.get('to', []):
                    if target.get('agent'):
                        next_agents.append(target['agent'])
            
            position = '起始节点' if i == 0 else ('结束节点' if i == len(config) - 1 else '中间节点')
            
            context = {
                'position': position,
                'prev_agents': list(set(prev_agents)) if prev_agents else ['user'],
                'next_agents': list(set(next_agents)) if next_agents else ['output']
            }
            
            result = self.optimize_agent_prompt(agent, context)
            results.append(result)
            
            print(f"  ✓ 优化完成，改进点: {len(result.improvements)}")
        
        return results
    
    def apply_optimization(self, config: List[Dict[str, Any]], 
                          results: List[OptimizationResult]) -> List[Dict[str, Any]]:
        """
        将优化结果应用到配置
        
        Args:
            config: 原始配置
            results: 优化结果列表
            
        Returns:
            优化后的配置
        """
        optimized_config = []
        
        for agent, result in zip(config, results):
            optimized_agent = dict(agent)
            
            if 'instruction_prompt' not in optimized_agent:
                optimized_agent['instruction_prompt'] = {}
            
            optimized_agent['instruction_prompt']['instruction'] = result.optimized_instruction
            optimized_agent['instruction_prompt']['prompt_template'] = result.optimized_template
            
            # 添加优化元数据
            optimized_agent['prompt_optimization'] = {
                'optimized': True,
                'improvements': result.improvements,
                'reasoning': result.reasoning
            }
            
            optimized_config.append(optimized_agent)
        
        return optimized_config


# 便捷函数
def optimize_prompts(config: List[Dict[str, Any]], 
                    api_key: Optional[str] = None) -> tuple:
    """
    便捷优化函数
    
    Args:
        config: 系统配置
        api_key: OpenAI API Key
        
    Returns:
        (优化后的配置, 优化结果列表)
    """
    optimizer = PromptOptimizer(api_key)
    results = optimizer.optimize_system_prompts(config)
    optimized_config = optimizer.apply_optimization(config, results)
    return optimized_config, results


def compare_prompts(original: Dict, optimized: Dict) -> str:
    """
    生成优化对比文本
    
    Args:
        original: 原始配置
        optimized: 优化后配置
        
    Returns:
        对比文本
    """
    agent_id = original.get('agent_id', 'unknown')
    
    orig_inst = original.get('instruction_prompt', {}).get('instruction', '')
    opt_inst = optimized.get('instruction_prompt', {}).get('instruction', '')
    
    orig_temp = original.get('instruction_prompt', {}).get('prompt_template', '')
    opt_temp = optimized.get('instruction_prompt', {}).get('prompt_template', '')
    
    improvements = optimized.get('prompt_optimization', {}).get('improvements', [])
    
    comparison = f"""
## Agent: {agent_id}

### 改进点
"""
    for i, imp in enumerate(improvements, 1):
        comparison += f"{i}. {imp}\n"
    
    comparison += f"""
### Instruction 对比

**原始:**
{orig_inst}

**优化后:**
{opt_inst}

### Template 对比

**原始:**
{orig_temp}

**优化后:**
{opt_temp}

---
"""
    return comparison
