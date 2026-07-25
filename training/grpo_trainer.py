# training/grpo_trainer.py
import os
import re
import json
import shutil
import subprocess
import threading
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from collections import Counter


class GRPOTrainer:
    """GRPO 训练器 - 整合 verl，支持 System-Level 多 Agent GRPO 训练"""
    
    def __init__(self, output_dir: str = "./training_outputs/grpo"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        # LLM judge cache to avoid redundant API calls
        self._llm_judge_cache = {}
    
    # ============== Reward Computation (B1) ==============
    
    def compute_rewards(self,
                       trajectories: List[Dict],
                       reward_spec: List[Dict],
                       reward_functions: Dict[str, Callable] = None,
                       log_callback: callable = None) -> List[Dict]:
        """
        计算奖励值
        
        Args:
            trajectories: 轨迹列表
            reward_spec: 奖励规格配置
            reward_functions: 自定义奖励函数字典
            log_callback: 日志回调
            
        Returns:
            List[Dict]: 带有奖励值的轨迹
        """
        for traj_idx, traj in enumerate(trajectories):
            total_reward = 0.0
            rewards = {}
            
            for spec in reward_spec:
                reward_id = spec.get('reward_id', 'unknown')
                reward_type = spec.get('type', '')
                weight = spec.get('weight', 1.0)
                
                if reward_type in ('gt_match', 'gt_match_or_rule_or_model', 'gt_match_or_model'):
                    reward = self._compute_gt_match_reward(traj, spec)
                
                elif reward_type == 'rule':
                    reward = self._compute_rule_reward(traj, spec)
                
                elif reward_type == 'llm_judge':
                    reward = self._compute_llm_judge_reward(traj, spec, log_callback)
                
                elif reward_type == 'custom' and reward_functions:
                    func = reward_functions.get(reward_id)
                    if func:
                        reward = func(traj)
                    else:
                        reward = 0.0
                else:
                    reward = 0.0
                
                weighted_reward = reward * weight
                rewards[reward_id] = {
                    'raw': reward,
                    'weight': weight,
                    'weighted': weighted_reward
                }
                total_reward += weighted_reward
            
            traj['rewards'] = rewards
            traj['total_reward'] = total_reward
            
            if log_callback and traj_idx % 10 == 0:
                log_callback(f"Trajectory {traj_idx}: total_reward={total_reward:.4f}")
        
        return trajectories
    
    def _compute_gt_match_reward(self, traj: Dict, spec: Dict) -> float:
        """
        计算 ground truth 匹配奖励。
        
        使用多层匹配策略：
        1. 完全匹配 → 1.0
        2. Token-level F1 score
        3. ROUGE-L (最长公共子序列)
        """
        target_agent = spec.get('on', {}).get('agent')
        output_key = spec.get('on', {}).get('output_key')
        
        for step in traj.get('steps', []):
            if step.get('agent_id') == target_agent:
                response = step.get('response', '')
                ground_truth = step.get('ground_truth', '')
                
                if not ground_truth or not response:
                    return 0.0
                
                response_stripped = response.strip()
                gt_stripped = ground_truth.strip()
                
                # 1. Exact match
                if response_stripped == gt_stripped:
                    return 1.0
                
                # 2. Token-level F1
                f1_score = self._compute_token_f1(response_stripped, gt_stripped)
                
                # 3. ROUGE-L
                rouge_l = self._compute_rouge_l(response_stripped, gt_stripped)
                
                # Return best of F1 and ROUGE-L
                return max(f1_score, rouge_l)
        
        return 0.0
    
    def _compute_token_f1(self, prediction: str, reference: str) -> float:
        """计算 token-level F1 score"""
        pred_tokens = prediction.lower().split()
        ref_tokens = reference.lower().split()
        
        if not ref_tokens:
            return 0.0
        if not pred_tokens:
            return 0.0
        
        pred_counter = Counter(pred_tokens)
        ref_counter = Counter(ref_tokens)
        
        # True positives: tokens in both
        tp = sum((pred_counter & ref_counter).values())
        
        # Precision and Recall
        precision = tp / len(pred_tokens) if pred_tokens else 0.0
        recall = tp / len(ref_tokens) if ref_tokens else 0.0
        
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * precision * recall / (precision + recall)
        return f1
    
    def _compute_rouge_l(self, prediction: str, reference: str) -> float:
        """计算 ROUGE-L (Longest Common Subsequence based)"""
        pred_tokens = prediction.lower().split()
        ref_tokens = reference.lower().split()
        
        if not pred_tokens or not ref_tokens:
            return 0.0
        
        # Dynamic programming LCS
        m, n = len(ref_tokens), len(pred_tokens)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_tokens[i-1] == pred_tokens[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        
        lcs_length = dp[m][n]
        
        precision = lcs_length / n if n > 0 else 0.0
        recall = lcs_length / m if m > 0 else 0.0
        
        if precision + recall == 0:
            return 0.0
        
        f1 = 2 * precision * recall / (precision + recall)
        return f1
    
    def _compute_rule_reward(self, traj: Dict, spec: Dict) -> float:
        """
        计算规则奖励。
        
        支持的规则类型:
        - json_format: 检查是否为有效 JSON
        - length: 检查长度约束
        - regex: 正则表达式匹配
        - contains: 包含指定字符串
        - starts_with / ends_with: 前缀/后缀检查
        """
        rule = spec.get('rule', '')
        target_agent = spec.get('on', {}).get('agent')
        
        for step in traj.get('steps', []):
            if step.get('agent_id') == target_agent:
                response = step.get('response', '')
                
                if not response:
                    return 0.0
                
                # JSON format check
                if 'json' in rule.lower() or rule.startswith('must_follow_format'):
                    # Try to extract JSON from response
                    try:
                        # Try direct parse
                        json.loads(response)
                        return 1.0
                    except json.JSONDecodeError:
                        # Try to find JSON block in response
                        json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', response)
                        if json_match:
                            try:
                                json.loads(json_match.group())
                                return 0.8  # Partial credit for embedded JSON
                            except json.JSONDecodeError:
                                return 0.0
                        return 0.0
                
                # Length constraint
                if 'length' in rule.lower():
                    min_len = spec.get('min_length', 10)
                    max_len = spec.get('max_length', float('inf'))
                    if min_len <= len(response) <= max_len:
                        return 1.0
                    return 0.0
                
                # Regex pattern matching
                if 'regex' in rule.lower() or spec.get('pattern'):
                    pattern = spec.get('pattern', rule.replace('regex:', '').strip())
                    try:
                        if re.search(pattern, response):
                            return 1.0
                        return 0.0
                    except re.error:
                        return 0.0
                
                # Contains check
                if 'contains' in rule.lower():
                    required = spec.get('required_strings', [])
                    if not required:
                        # Try to extract from rule description
                        match = re.search(r'contains\((.*?)\)', rule)
                        if match:
                            required = [s.strip() for s in match.group(1).split(',')]
                    
                    if required:
                        all_present = all(s in response for s in required)
                        return 1.0 if all_present else 0.0
                
                # Starts/ends with
                if 'starts_with' in rule.lower():
                    prefix = spec.get('prefix', '')
                    return 1.0 if response.strip().startswith(prefix) else 0.0
                
                if 'ends_with' in rule.lower():
                    suffix = spec.get('suffix', '')
                    return 1.0 if response.strip().endswith(suffix) else 0.0
        
        return 0.0
    
    def _compute_llm_judge_reward(self, traj: Dict, spec: Dict, 
                                   log_callback: callable = None) -> float:
        """
        使用 LLM 评判计算奖励 — 实际调用 GPT-4o API。
        
        Args:
            traj: 轨迹字典
            spec: reward_spec 中的单个规格
            log_callback: 日志回调
        
        Returns:
            float: 0.0 ~ 1.0 之间的奖励值
        """
        judge_model = spec.get('judge_model', {}).get('name_or_path', 'gpt-4o')
        target_agent = spec.get('on', {}).get('agent')
        output_key = spec.get('on', {}).get('output_key', '')
        
        # Find the target agent's response
        response = ''
        ground_truth = ''
        for step in traj.get('steps', []):
            if step.get('agent_id') == target_agent:
                response = step.get('response', '')
                ground_truth = step.get('ground_truth', '')
                break
        
        if not response:
            return 0.0
        
        # Build cache key
        cache_key = f"{target_agent}:{hash(response[:200])}"
        if cache_key in self._llm_judge_cache:
            return self._llm_judge_cache[cache_key]
        
        # Build judge prompt
        judge_prompt = self._build_judge_prompt(
            response=response,
            ground_truth=ground_truth,
            agent_id=target_agent,
            output_key=output_key,
            spec=spec
        )
        
        try:
            from llm.model_factory import ModelFactory
            llm = ModelFactory.create_llm(judge_model)
            judge_response = llm.generate(judge_prompt, temperature=0.1)
            
            # Parse numeric score from response
            score = self._parse_judge_score(judge_response)
            
            if log_callback:
                log_callback(f"LLM Judge ({judge_model}) for {target_agent}: "
                           f"score={score:.2f}, response={judge_response[:100]}")
            
            # Cache the result
            self._llm_judge_cache[cache_key] = score
            return score
            
        except Exception as e:
            if log_callback:
                log_callback(f"LLM Judge error for {target_agent}: {str(e)}")
            # Fallback: return 0.0 instead of random
            return 0.0
    
    def _build_judge_prompt(self, response: str, ground_truth: str,
                            agent_id: str, output_key: str, spec: Dict) -> str:
        """构建 LLM judge 的评判 prompt"""
        criteria = spec.get('criteria', f'Evaluate the quality of the {agent_id} agent\'s output.')
        
        prompt = f"""You are an expert evaluator. Rate the following output on a scale of 0.0 to 1.0.

## Evaluation Criteria
{criteria}

## Agent: {agent_id} (output_key: {output_key})

## Output to Evaluate
{response}

"""
        if ground_truth:
            prompt += f"""## Reference (Ground Truth)
{ground_truth}

"""
        
        prompt += """## Instructions
1. Compare the output against the reference (if provided) or evaluate based on the criteria.
2. Give a score between 0.0 and 1.0 where:
   - 1.0 = Perfect (exact match or excellent quality)
   - 0.7-0.9 = Good (minor issues)
   - 0.4-0.6 = Acceptable (some issues)
   - 0.1-0.3 = Poor (significant issues)
   - 0.0 = Completely wrong or empty

Respond with ONLY a single number (e.g., 0.85), nothing else."""
        
        return prompt
    
    def _parse_judge_score(self, response: str) -> float:
        """从 LLM judge 响应中解析数值分数"""
        response = response.strip()
        
        # Try direct float parse
        try:
            score = float(response)
            return max(0.0, min(1.0, score))
        except ValueError:
            pass
        
        # Try to find a number in the response
        numbers = re.findall(r'0?\.\d+|[01]\.0', response)
        if numbers:
            try:
                score = float(numbers[0])
                return max(0.0, min(1.0, score))
            except ValueError:
                pass
        
        # Try to find integer percentage
        pct_match = re.search(r'(\d+)\s*%', response)
        if pct_match:
            return max(0.0, min(1.0, int(pct_match.group(1)) / 100.0))
        
        return 0.0
    
    # ============== Rollout Data Preparation ==============
    
    def prepare_rollout_data(self,
                            trajectories: List[Dict],
                            output_file: str = None) -> str:
        """
        将轨迹数据转换为 GRPO Rollout 格式
        
        Args:
            trajectories: 轨迹数据列表
            output_file: 输出文件路径
            
        Returns:
            str: 训练数据文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.output_dir, f"grpo_data_{timestamp}.jsonl")
        
        grpo_data = []
        
        for traj in trajectories:
            rollout_steps = []
            for step in traj.get('steps', []):
                rollout_steps.append({
                    'agent_id': step.get('agent_id'),
                    'prompt': step.get('prompt', ''),
                    'response': step.get('response', ''),
                    'ground_truth': step.get('ground_truth'),
                    'metadata': step.get('metadata', {})
                })
            
            grpo_data.append({
                'trajectory_id': traj.get('trajectory_id'),
                'input_request': traj.get('input_request', {}),
                'steps': rollout_steps,
                'final_output': traj.get('final_output', {}),
                'rewards': {}
            })
        
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in grpo_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        return output_file
    
    # ============== Per-Agent GRPO Data Generation (B3, B4) ==============
    
    def prepare_agent_grpo_data(
        self,
        agent_config: Dict[str, Any],
        dataset_file: str,
        reward_spec: List[Dict],
        trajectory_file: str = None,
        output_file: str = None,
        log_callback: callable = None
    ) -> str:
        """
        为单个 Agent 生成 GRPO 训练数据。
        
        格式: 每行一个 sample，包含 prompt 和对应的 reward。
        用于 verl 的 GRPO 训练。
        
        Args:
            agent_config: 单个 agent 的完整配置
            dataset_file: 数据集文件路径
            reward_spec: 奖励规格配置
            trajectory_file: 轨迹文件路径
            output_file: 输出文件路径
            log_callback: 日志回调
        
        Returns:
            str: 生成的训练数据文件路径
        """
        agent_id = agent_config.get('agent_id', 'unknown')
        instruction_prompt = agent_config.get('instruction_prompt', {})
        system_prompt = instruction_prompt.get('instruction', '')
        prompt_template = instruction_prompt.get('prompt_template', '')
        training_config = agent_config.get('training', {})
        dataset_config = training_config.get('dataset', {})
        rollout_config = training_config.get('rollout', {})
        input_key = dataset_config.get('input_key', rollout_config.get('dataset_input_key', 'input'))
        
        if not prompt_template:
            raise ValueError(f"Agent '{agent_id}' 缺少 instruction_prompt.prompt_template 配置")
        
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(self.output_dir, 'system_grpo')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{agent_id}_grpo_{timestamp}.jsonl")
        
        # 读取数据集
        samples = []
        with open(dataset_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        
        if log_callback:
            log_callback(f"[{agent_id}] 读取数据集: {len(samples)} 条样本")
        
        # 如果有轨迹文件，读取 agent 的 response 和 GT
        agent_trajectories = {}
        if trajectory_file and os.path.exists(trajectory_file):
            with open(trajectory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = json.loads(line)
                        if record.get('agent_id') == agent_id:
                            sample_id = record.get('meta', {}).get('sample_id', -1)
                            agent_trajectories[sample_id] = record
        
        if log_callback and agent_trajectories:
            log_callback(f"[{agent_id}] 从轨迹文件读取: {len(agent_trajectories)} 条")
        
        # 生成 GRPO 训练数据
        grpo_data = []
        
        for i, sample in enumerate(samples):
            input_data = sample.get('input', sample)
            
            # 渲染 prompt
            user_content = self._render_prompt_template(prompt_template, input_data)
            
            # 构建完整 prompt (system + user)
            full_prompt = f"{system_prompt}\n\n{user_content}" if system_prompt else user_content
            
            # 获取 agent 的 response (如果有)
            traj_record = agent_trajectories.get(i)
            response = ''
            ground_truth = ''
            if traj_record:
                for msg in traj_record.get('messages', []):
                    if msg.get('role') == 'assistant':
                        response = msg.get('content', '')
                ground_truth = traj_record.get('ground_truth', '')
            
            # 构建 GRPO sample
            grpo_sample = {
                'prompt': full_prompt,
                'agent_id': agent_id,
                'sample_index': i,
                'input_data': input_data,
                'response': response,
                'ground_truth': ground_truth,
                'reference': {}  # Will be populated from dataset GT fields
            }
            
            # Add reference GT from dataset for reward computation
            for rspec in reward_spec:
                ref_config = rspec.get('reference', {})
                if ref_config.get('from') == 'dataset':
                    ref_key = ref_config.get('key', '')
                    ref_value = sample.get(ref_key)
                    if ref_value is not None:
                        grpo_sample['reference'][ref_key] = ref_value
            
            grpo_data.append(grpo_sample)
        
        # 保存为 JSONL
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in grpo_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        if log_callback:
            log_callback(f"[{agent_id}] 生成 GRPO 训练数据: {len(grpo_data)} 条 → {output_file}")
        
        return output_file
    
    def _render_prompt_template(self, template: str, input_data: Dict[str, Any]) -> str:
        """渲染 prompt_template，替换 {{input.xxx}} 变量"""
        result = template
        pattern = r'\{\{input\.(\w+(?:\.\w+)*)\}\}'
        
        def replacer(match):
            key_path = match.group(1)
            keys = key_path.split('.')
            value = input_data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return match.group(0)
            return str(value)
        
        result = re.sub(pattern, replacer, result)
        return result
    
    def _extract_reward_spec_for_agent(
        self, 
        agent_id: str, 
        config_json: List[Dict],
        agent_config: Dict = None
    ) -> List[Dict]:
        """
        从系统配置中提取与指定 agent 相关的 reward_spec。
        
        查找逻辑：
        1. 遍历所有 agent 的 training.reward_spec
        2. 过滤 apply_to_agents 包含当前 agent_id 的 reward
        3. 如果 agent_config 中配置了 learn_from，则进一步按 reward_id 白名单过滤
        """
        relevant_specs = []
        
        for agent in config_json:
            training = agent.get('training', {})
            reward_specs = training.get('reward_spec', [])
            
            for rspec in reward_specs:
                apply_to = rspec.get('apply_to_agents', [])
                if agent_id in apply_to:
                    relevant_specs.append(rspec)
        
        # Apply learn_from filter if specified in agent_config
        if agent_config:
            learn_from = agent_config.get('training', {}).get('learn_from', [])
            if learn_from:
                relevant_specs = [
                    spec for spec in relevant_specs
                    if spec.get('reward_id') in learn_from
                ]
        
        return relevant_specs
    
    def _extract_grpo_hparams(self, config_json: List[Dict]) -> Dict[str, Any]:
        """从系统配置中提取 GRPO 超参数"""
        for agent in config_json:
            training = agent.get('training', {})
            hparams = training.get('grpo_hparams', {})
            if hparams:
                return hparams
        return {}
    
    # ============== Subprocess-Based GRPO Training (B2) ==============
    
    def train_with_subprocess(
        self,
        data_file: str,
        model_path: str,
        reward_spec: List[Dict],
        output_dir: str = None,
        hyperparameters: Dict[str, Any] = None,
        log_callback: callable = None,
        metrics_callback: callable = None
    ) -> Dict[str, Any]:
        """
        使用 verl subprocess 进行 GRPO 训练。
        
        Args:
            data_file: 训练数据文件路径
            model_path: 模型路径
            reward_spec: 奖励规格配置
            output_dir: 输出目录
            hyperparameters: 超参数字典
            log_callback: 日志回调
            metrics_callback: 指标回调
        
        Returns:
            Dict: 训练结果
        """
        try:
            if output_dir is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_dir = os.path.join(self.output_dir, f"run_{timestamp}")
            
            os.makedirs(output_dir, exist_ok=True)
            
            default_params = {
                'lr': 1e-6,
                'batch_size': 4,
                'num_epochs': 1,
                'max_length': 2048,
                'rollout_batch_size': 64,
                'mini_batch_size': 8,
                'kl_coef': 0.01,
                'clip_range': 0.2,
                'advantage': 'gae',
                'warmup_ratio': 0.1,
                'gradient_accumulation_steps': 1,
                'save_steps': 100,
                'logging_steps': 10,
                'fp16': True,
                'num_generations': 4,  # GRPO: number of generations per prompt
            }
            
            if hyperparameters:
                default_params.update(hyperparameters)
            
            model_type = self._infer_model_type(model_path)
            
            if log_callback:
                log_callback(f"Model type: {model_type}, Model: {model_path}")
                log_callback(f"Dataset: {data_file}")
                log_callback(f"GRPO Hyperparameters: {default_params}")
            
            # Build verl GRPO config
            verl_config = {
                'model': {
                    'path': model_path,
                    'type': model_type
                },
                'data': {
                    'train_files': data_file,
                    'train_batch_size': default_params['rollout_batch_size'],
                    'max_prompt_length': default_params['max_length'],
                    'max_response_length': default_params['max_length'],
                },
                'algorithm': {
                    'kl_penalty': 'kl',
                    'kl_ctrl': {
                        'kl_coef': default_params['kl_coef']
                    },
                    'adv_estimator': default_params['advantage'],
                },
                'trainer': {
                    'total_epochs': default_params['num_epochs'],
                    'project_name': 'multi_agent_grpo',
                    'experiment_name': os.path.basename(output_dir),
                    'logger': ['console'],
                    'save_freq': default_params['save_steps'],
                    'test_freq': default_params['logging_steps'],
                    'nnodes': 1,
                    'n_gpus_per_node': 1,
                },
                'actor_rollout_ref': {
                    'model': {
                        'path': model_path,
                    },
                    'actor': {
                        'optim': {
                            'lr': default_params['lr'],
                        },
                        'ppo_mini_batch_size': default_params['mini_batch_size'],
                        'ppo_micro_batch_size': default_params['batch_size'],
                        'clip_range': default_params['clip_range'],
                        'ppo_epochs': 1,
                    },
                    'rollout': {
                        'name': 'vllm',
                        'n': default_params['num_generations'],
                        'temperature': 1.0,
                        'tensor_model_parallel_size': 1,
                    },
                    'ref': {
                        'log_prob_micro_batch_size': default_params['batch_size'],
                    }
                },
                'reward_spec': reward_spec,
                'output_dir': output_dir
            }
            
            # Save verl config
            config_file = os.path.join(output_dir, 'verl_config.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(verl_config, f, ensure_ascii=False, indent=2)
            
            if log_callback:
                log_callback(f"verl config saved to: {config_file}")
            
            # Build command — try multiple verl entry points
            cmd = self._build_verl_command(config_file, default_params)
            
            if log_callback:
                log_callback(f"Command: {' '.join(cmd)}")
                log_callback("Starting GRPO training with verl (subprocess)...")
            
            # Execute via subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        stripped = line.strip()
                        if log_callback:
                            log_callback(stripped)
                        if metrics_callback:
                            self._parse_and_report_metrics(stripped, metrics_callback)
                process.stdout.close()
                process.wait()
            
            output_thread = threading.Thread(target=read_output)
            output_thread.start()
            output_thread.join()
            
            if process.returncode == 0:
                if log_callback:
                    log_callback("GRPO Training completed successfully!")
                return {
                    'status': 'completed',
                    'output_dir': output_dir,
                    'message': 'GRPO 训练完成'
                }
            else:
                error_msg = f'GRPO Training failed with return code: {process.returncode}'
                if log_callback:
                    log_callback(error_msg)
                return {
                    'status': 'error',
                    'message': error_msg
                }
        
        except FileNotFoundError:
            error_msg = ('verl not found. Please install verl: pip install verl\n'
                        'Or use: pip install "verl[all]"')
            if log_callback:
                log_callback(error_msg)
            return {'status': 'error', 'message': error_msg}
        except Exception as e:
            error_msg = str(e)
            if log_callback:
                log_callback(f"GRPO Training error: {error_msg}")
            return {'status': 'error', 'message': error_msg}
    
    def _build_verl_command(self, config_file: str, params: Dict) -> List[str]:
        """构建 verl GRPO 训练命令"""
        # Try different verl entry points
        # verl uses ray-based training, so the entry point may vary
        return [
            'python', '-m', 'verl.trainer.main_ppo',
            '--config', config_file,
            'data.train_batch_size=' + str(params.get('rollout_batch_size', 64)),
            'trainer.total_epochs=' + str(params.get('num_epochs', 1)),
            'actor_rollout_ref.actor.optim.lr=' + str(params.get('lr', 1e-6)),
        ]
    
    def _parse_and_report_metrics(self, line: str, metrics_callback: callable):
        """尝试从训练输出行中解析 metrics"""
        try:
            loss_match = re.search(r'loss[=:]\s*([\d.]+)', line, re.IGNORECASE)
            step_match = re.search(r'(?:step|epoch)[=:]\s*(\d+)', line, re.IGNORECASE)
            reward_match = re.search(r'reward[=:]\s*([\d.]+)', line, re.IGNORECASE)
            lr_match = re.search(r'(?:lr|learning_rate)[=:]\s*([\d.eE+-]+)', line, re.IGNORECASE)
            
            if loss_match or reward_match:
                step = int(step_match.group(1)) if step_match else 0
                loss = float(loss_match.group(1)) if loss_match else 0.0
                lr = float(lr_match.group(1)) if lr_match else 0.0
                metrics_callback(step, loss, lr)
        except Exception:
            pass
    
    # ============== System-Level Multi-Agent GRPO Training (B3) ==============
    
    def train_system_level(
        self,
        config_json: List[Dict],
        dataset_file: str,
        trajectory_file: str = None,
        default_hyperparameters: Dict[str, Any] = None,
        log_callback: callable = None,
        metrics_callback: callable = None
    ) -> Dict[str, Any]:
        """
        System-level 多 Agent GRPO 训练。
        
        解析 config_json 中的 training 配置，为每个 trainable GRPO agent:
        1. 提取 reward_spec（从所有 agent 的配置中收集）
        2. 生成 rollout 数据
        3. 计算 rewards
        4. 执行 GRPO 训练
        
        Args:
            config_json: 完整的系统配置（agent 列表）
            dataset_file: 数据集文件路径
            trajectory_file: 轨迹文件路径
            default_hyperparameters: 默认超参数
            log_callback: 日志回调
            metrics_callback: 指标回调
        
        Returns:
            Dict: 训练结果
        """
        import time
        
        if log_callback:
            log_callback("=" * 60)
            log_callback("System-Level Multi-Agent GRPO Training")
            log_callback("=" * 60)
        
        # 找到所有 trainable GRPO agents
        trainable_agents = []
        for agent in config_json:
            training = agent.get('training', {})
            if training.get('trainable') and training.get('mode') == 'grpo':
                trainable_agents.append(agent)
        
        if not trainable_agents:
            raise ValueError(
                "没有找到可训练的 GRPO Agent。请确保至少一个 agent 配置了 "
                "'training': {'trainable': true, 'mode': 'grpo'}"
            )
        
        if log_callback:
            agent_names = [a.get('agent_id') for a in trainable_agents]
            log_callback(f"找到 {len(trainable_agents)} 个可训练 GRPO Agent: {agent_names}")
        
        # 收集所有 reward_spec
        all_reward_specs = []
        for agent in config_json:
            training = agent.get('training', {})
            specs = training.get('reward_spec', [])
            all_reward_specs.extend(specs)
        
        if log_callback:
            log_callback(f"收集到 {len(all_reward_specs)} 个 reward_spec")
            for spec in all_reward_specs:
                log_callback(f"  - {spec.get('reward_id')}: type={spec.get('type')}, "
                           f"on={spec.get('on', {}).get('agent')}, "
                           f"apply_to={spec.get('apply_to_agents', [])}")
        
        # 提取 GRPO 超参数
        grpo_hparams = self._extract_grpo_hparams(config_json)
        if default_hyperparameters:
            merged_params = dict(default_hyperparameters)
            merged_params.update(grpo_hparams)
        else:
            merged_params = grpo_hparams
        
        if log_callback:
            log_callback(f"GRPO 超参数: {merged_params}")
        
        total_agents = len(trainable_agents)
        agent_results = []
        completed_count = 0
        failed_count = 0
        
        for idx, agent_config in enumerate(trainable_agents):
            agent_id = agent_config.get('agent_id', 'unknown')
            training_config = agent_config.get('training', {})
            model_path = agent_config.get('model', {}).get('name_or_path', 'Qwen/Qwen2.5-0.5B-Instruct')
            
            # 提取与该 agent 相关的 reward_spec（支持 learn_from 过滤）
            agent_reward_specs = self._extract_reward_spec_for_agent(agent_id, config_json, agent_config=agent_config)
            if not agent_reward_specs:
                # Fallback: use all reward specs
                agent_reward_specs = all_reward_specs
            
            # Per-agent hyperparameters
            agent_params = dict(merged_params)
            agent_train_params = training_config.get('train_parameters', {})
            if agent_train_params:
                agent_params.update(agent_train_params)
            
            loss_weight = training_config.get('loss', {}).get('weight', 1.0)
            
            if log_callback:
                learn_from = training_config.get('learn_from', [])
                policy_role = training_config.get('policy_role', 'actor')
                log_callback(f"\n{'─' * 40}")
                log_callback(f"[{idx+1}/{total_agents}] GRPO 训练 Agent: {agent_id}")
                log_callback(f"  模型: {model_path}")
                log_callback(f"  Policy Role: {policy_role}")
                log_callback(f"  Learn From: {learn_from if learn_from else 'all rewards'}")
                log_callback(f"  Reward Specs: {len(agent_reward_specs)}")
                log_callback(f"  Loss Weight: {loss_weight}")
                log_callback(f"{'─' * 40}")
            
            def make_agent_log_cb(agent_name, base_cb):
                def agent_log_cb(msg):
                    if base_cb:
                        base_cb(f"[{agent_name}] {msg}")
                return agent_log_cb
            
            agent_log_cb = make_agent_log_cb(agent_id, log_callback)
            
            current_agent_results = {'agent_id': agent_id, 'metrics_history': []}
            
            def make_agent_metrics_cb(agent_name, base_cb, results_ref):
                def agent_metrics_cb(step, loss, lr):
                    results_ref['metrics_history'].append({
                        'step': step, 'loss': loss, 'lr': lr
                    })
                    if base_cb:
                        base_cb(step, loss, lr)
                return agent_metrics_cb
            
            agent_metrics_cb = make_agent_metrics_cb(
                agent_id, metrics_callback, current_agent_results
            )
            
            start_time = time.time()
            
            try:
                # Step 1: Prepare GRPO data for this agent
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_dir = os.path.join(self.output_dir, 'system_grpo', 
                                         f"{agent_id}_{timestamp}")
                
                data_file = self.prepare_agent_grpo_data(
                    agent_config=agent_config,
                    dataset_file=dataset_file,
                    reward_spec=agent_reward_specs,
                    trajectory_file=trajectory_file,
                    output_file=os.path.join(output_dir, f"{agent_id}_grpo.jsonl"),
                    log_callback=agent_log_cb
                )
                
                # Step 2: Train
                result = self.train_with_subprocess(
                    data_file=data_file,
                    model_path=model_path,
                    reward_spec=agent_reward_specs,
                    output_dir=output_dir,
                    hyperparameters=agent_params,
                    log_callback=agent_log_cb,
                    metrics_callback=agent_metrics_cb
                )
                
                elapsed = time.time() - start_time
                status = result.get('status', 'error')
                
                agent_result = {
                    'agent_id': agent_id,
                    'status': 'completed' if status == 'completed' else 'failed',
                    'model': model_path,
                    'data_file': data_file,
                    'output_dir': result.get('output_dir'),
                    'reward_specs': len(agent_reward_specs),
                    'loss_weight': loss_weight,
                    'train_params': agent_params,
                    'elapsed_seconds': round(elapsed, 1),
                    'message': result.get('message', '')
                }
                
                metrics = current_agent_results.get('metrics_history', [])
                if metrics:
                    agent_result['final_loss'] = metrics[-1].get('loss')
                
                if status == 'completed':
                    completed_count += 1
                    if log_callback:
                        log_callback(f"[{agent_id}] ✅ GRPO 训练完成 (耗时 {elapsed/60:.1f} 分钟)")
                else:
                    failed_count += 1
                    agent_result['error'] = result.get('message', 'Unknown error')
                    if log_callback:
                        log_callback(f"[{agent_id}] ❌ GRPO 训练失败: {result.get('message')}")
                
                agent_results.append(agent_result)
                
            except Exception as e:
                failed_count += 1
                agent_results.append({
                    'agent_id': agent_id,
                    'status': 'failed',
                    'model': model_path,
                    'error': str(e)
                })
                if log_callback:
                    log_callback(f"[{agent_id}] ❌ GRPO 训练异常: {str(e)}")
        
        # 汇总结果
        if completed_count == total_agents:
            overall_status = 'completed'
            overall_msg = f'所有 {total_agents} 个 Agent GRPO 训练完成'
        elif completed_count > 0:
            overall_status = 'partial'
            overall_msg = f'{completed_count}/{total_agents} 个 Agent GRPO 训练完成，{failed_count} 个失败'
        else:
            overall_status = 'error'
            overall_msg = f'所有 {total_agents} 个 Agent GRPO 训练均失败'
        
        if log_callback:
            log_callback(f"\n{'=' * 60}")
            log_callback(f"System-Level GRPO 完成: {overall_msg}")
            log_callback(f"{'=' * 60}")
        
        return {
            'status': overall_status,
            'mode': 'system_level_grpo',
            'agents': agent_results,
            'overall_message': overall_msg
        }
    
    # ============== Model Type Inference ==============
    
    def _infer_model_type(self, model_path: str) -> str:
        """从模型路径推断 model_type"""
        path_lower = model_path.lower()
        
        if 'qwen2.5' in path_lower or 'qwen2_5' in path_lower:
            if '0.5b' in path_lower or '0_5b' in path_lower:
                return 'qwen2_5-0_5b-instruct'
            elif '1.5b' in path_lower or '1_5b' in path_lower:
                return 'qwen2_5-1_5b-instruct'
            elif '3b' in path_lower:
                return 'qwen2_5-3b-instruct'
            elif '7b' in path_lower:
                return 'qwen2_5-7b-instruct'
            elif '14b' in path_lower:
                return 'qwen2_5-14b-instruct'
            elif '32b' in path_lower:
                return 'qwen2_5-32b-instruct'
            else:
                return 'qwen2_5-0_5b-instruct'
        
        elif 'qwen2' in path_lower:
            return 'qwen2-7b-instruct'
        
        elif 'llama' in path_lower:
            return 'llama3-8b-instruct'
        
        return 'qwen2_5-0_5b-instruct'
    
    def get_training_script(self, training_info: Dict) -> str:
        """生成训练脚本"""
        cmd = training_info.get('command', [])
        if not cmd:
            return "# 训练命令未生成"
        
        script = "#!/bin/bash\n\n"
        script += "# GRPO Training Script\n\n"
        script += " ".join(cmd) + "\n"
        
        return script
