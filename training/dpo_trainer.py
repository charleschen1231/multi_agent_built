# training/dpo_trainer.py
import os
import re
import json
import shutil
import subprocess
import threading
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime


class DPOTrainer:
    """DPO 训练器 - 整合 ms-swift，支持 System-Level 多 Agent DPO 训练"""
    
    def __init__(self, output_dir: str = "./training_outputs/dpo"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    # ============== Prompt Template Rendering ==============
    
    def _render_prompt_template(self, template: str, input_data: Dict[str, Any]) -> str:
        """
        渲染 prompt_template，替换 {{input.xxx}} 变量。
        
        Args:
            template: 模板字符串，如 "问题：{{input.user_request}}"
            input_data: 输入数据字典，如 {"user_request": "计算1+1"}
        
        Returns:
            str: 渲染后的字符串
        """
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
    
    # ============== Basic Preference Data Preparation ==============
    
    def prepare_preference_data(self,
                               trajectories: List[Dict],
                               output_file: str = None) -> str:
        """
        将轨迹数据转换为 DPO 偏好训练格式
        
        Args:
            trajectories: 轨迹数据列表 (包含 chosen 和 rejected 对)
            output_file: 输出文件路径
            
        Returns:
            str: 训练数据文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.output_dir, f"dpo_data_{timestamp}.jsonl")
        
        dpo_data = []
        
        for traj in trajectories:
            for step in traj.get('steps', []):
                response = step.get('response', '')
                ground_truth = step.get('ground_truth', '')
                
                if response and ground_truth and response != ground_truth:
                    dpo_data.append({
                        'instruction': step.get('prompt', ''),
                        'input': '',
                        'chosen': ground_truth,
                        'rejected': response,
                        'metadata': {
                            'agent_id': step.get('agent_id'),
                            'trajectory_id': traj.get('trajectory_id'),
                            'sample_id': traj.get('sample_id')
                        }
                    })
        
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in dpo_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        return output_file
    
    def prepare_preference_data_from_pairs(self,
                                          preference_pairs: List[Dict],
                                          output_file: str = None) -> str:
        """
        从偏好对准备训练数据
        
        Args:
            preference_pairs: 偏好对列表
            output_file: 输出文件路径
            
        Returns:
            str: 训练数据文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.output_dir, f"dpo_data_{timestamp}.jsonl")
        
        dpo_data = []
        
        for pair in preference_pairs:
            dpo_data.append({
                'instruction': pair.get('prompt', ''),
                'input': pair.get('input', ''),
                'chosen': pair.get('chosen', ''),
                'rejected': pair.get('rejected', ''),
                'metadata': pair.get('metadata', {})
            })
        
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in dpo_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        return output_file
    
    # ============== Trajectory-Based Preference Pairs (A3) ==============
    
    def build_preference_pairs_from_trajectories(
        self,
        trajectory_records: List[Dict],
        log_callback: callable = None
    ) -> List[Dict]:
        """
        从执行轨迹构建 DPO 偏好对。
        
        在蒸馏流程中：
        - chosen = teacher model output (ground truth from Phase 1)
        - rejected = student model output (from Phase 2)
        
        Args:
            trajectory_records: TrajectoryRecorder 格式的轨迹记录列表
                每个元素格式: {
                    "agent_id": str,
                    "messages": [{"role":"user","content":...}, {"role":"assistant","content":...}],
                    "ground_truth": str,  # teacher output
                    "meta": {"sample_id": int, ...}
                }
            log_callback: 日志回调
        
        Returns:
            List[Dict]: 偏好对列表 [{prompt, chosen, rejected, metadata}, ...]
        """
        preference_pairs = []
        
        for record in trajectory_records:
            agent_id = record.get('agent_id', 'unknown')
            ground_truth = record.get('ground_truth', '')
            messages = record.get('messages', [])
            meta = record.get('meta', {})
            
            # 提取 prompt (user message)
            prompt = ''
            student_response = ''
            for msg in messages:
                if msg.get('role') == 'user':
                    prompt = msg.get('content', '')
                elif msg.get('role') == 'assistant':
                    student_response = msg.get('content', '')
            
            # 只有当 teacher GT 和 student response 都存在且不同时才创建偏好对
            if ground_truth and student_response and ground_truth != student_response:
                preference_pairs.append({
                    'prompt': prompt,
                    'chosen': ground_truth,     # teacher output (preferred)
                    'rejected': student_response,  # student output (less preferred)
                    'metadata': {
                        'agent_id': agent_id,
                        'sample_id': meta.get('sample_id', 0),
                        'model': meta.get('model', ''),
                        'teacher_model': meta.get('teacher_model', ''),
                        'loss_weight': meta.get('loss_weight', 1.0)
                    }
                })
        
        if log_callback:
            log_callback(f"从轨迹构建偏好对: {len(preference_pairs)} 对 "
                        f"(从 {len(trajectory_records)} 条轨迹记录)")
        
        return preference_pairs
    
    def build_preference_pairs_from_trajectory_file(
        self,
        trajectory_file: str,
        log_callback: callable = None
    ) -> List[Dict]:
        """
        从轨迹 JSONL 文件构建偏好对。
        
        Args:
            trajectory_file: TrajectoryRecorder 生成的 JSONL 文件路径
            log_callback: 日志回调
        
        Returns:
            List[Dict]: 偏好对列表
        """
        records = []
        with open(trajectory_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        
        if log_callback:
            log_callback(f"读取轨迹文件: {trajectory_file} ({len(records)} 条记录)")
        
        return self.build_preference_pairs_from_trajectories(records, log_callback)
    
    # ============== Per-Agent DPO Data Generation (A2, A4) ==============
    
    def prepare_agent_dpo_data(
        self,
        agent_config: Dict[str, Any],
        dataset_file: str,
        trajectory_file: str = None,
        output_file: str = None,
        log_callback: callable = None
    ) -> str:
        """
        为单个 Agent 生成 DPO 训练数据（ms-swift DPO 格式）。
        
        数据来源有两种：
        1. 从轨迹文件: chosen=teacher GT, rejected=student output
        2. 从数据集: chosen=gt_key 字段, rejected=需要另外提供
        
        输出 SWIFT DPO 格式:
        {
            "messages": [{"role": "system", "content": ...}, {"role": "user", "content": ...}],
            "chosen": "teacher output",
            "rejected": "student output"
        }
        
        Args:
            agent_config: 单个 agent 的完整配置字典
            dataset_file: 数据集文件路径 (JSONL)
            trajectory_file: 轨迹文件路径（可选，用于提取 student output）
            output_file: 输出文件路径
            log_callback: 日志回调
        
        Returns:
            str: 生成的训练数据文件路径
        """
        agent_id = agent_config.get('agent_id', 'unknown')
        training_config = agent_config.get('training', {})
        ground_truth_config = training_config.get('ground_truth', {})
        dataset_config = training_config.get('dataset', {})
        instruction_prompt = agent_config.get('instruction_prompt', {})
        
        gt_key = ground_truth_config.get('gt_key')
        input_key = dataset_config.get('input_key', 'input')
        system_prompt = instruction_prompt.get('instruction', '')
        prompt_template = instruction_prompt.get('prompt_template', '')
        
        if not gt_key:
            raise ValueError(f"Agent '{agent_id}' 缺少 training.ground_truth.gt_key 配置")
        
        if not prompt_template:
            raise ValueError(f"Agent '{agent_id}' 缺少 instruction_prompt.prompt_template 配置")
        
        # 生成输出文件路径
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(self.output_dir, 'system_dpo')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{agent_id}_dpo_{timestamp}.jsonl")
        
        # 读取数据集获取 ground truth (chosen)
        samples = []
        with open(dataset_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        
        if log_callback:
            log_callback(f"[{agent_id}] 读取数据集: {len(samples)} 条样本")
            log_callback(f"[{agent_id}] gt_key={gt_key}, input_key={input_key}")
        
        # 如果有轨迹文件，读取 student outputs (rejected)
        student_outputs = {}
        if trajectory_file and os.path.exists(trajectory_file):
            with open(trajectory_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = json.loads(line)
                        if record.get('agent_id') == agent_id:
                            sample_id = record.get('meta', {}).get('sample_id', -1)
                            # 提取 student response
                            for msg in record.get('messages', []):
                                if msg.get('role') == 'assistant':
                                    student_outputs[sample_id] = msg.get('content', '')
            
            if log_callback:
                log_callback(f"[{agent_id}] 从轨迹文件读取 student outputs: {len(student_outputs)} 条")
        
        # 生成 DPO 数据
        dpo_data = []
        skipped = 0
        
        for i, sample in enumerate(samples):
            input_data = sample.get('input', sample)
            
            # 获取 ground truth (chosen)
            gt_value = sample.get(gt_key)
            if gt_value is None:
                skipped += 1
                continue
            
            # 获取 student output (rejected)
            rejected_value = student_outputs.get(i, '')
            
            # 如果没有 student output，跳过该样本（DPO 需要 chosen 和 rejected 对）
            if not rejected_value:
                skipped += 1
                continue
            
            # chosen 和 rejected 不能相同
            chosen_str = str(gt_value) if not isinstance(gt_value, str) else gt_value
            if chosen_str.strip() == rejected_value.strip():
                skipped += 1
                continue
            
            # 构建 messages
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            user_content = self._render_prompt_template(prompt_template, input_data)
            if user_content:
                messages.append({"role": "user", "content": user_content})
            
            if len(messages) >= 1:
                dpo_data.append({
                    "messages": messages,
                    "chosen": chosen_str,
                    "rejected": rejected_value,
                    "metadata": {
                        'agent_id': agent_id,
                        'sample_index': i
                    }
                })
        
        if skipped > 0 and log_callback:
            log_callback(f"[{agent_id}] 跳过 {skipped} 条样本 (缺少 GT 或 student output 或两者相同)")
        
        if len(dpo_data) == 0:
            raise ValueError(
                f"Agent '{agent_id}': 没有可用的 DPO 训练样本。"
                f"请确保数据集中包含 '{gt_key}' 字段，且有对应的 student output。"
            )
        
        # 保存为 JSONL
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in dpo_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        if log_callback:
            log_callback(f"[{agent_id}] 生成 DPO 训练数据: {len(dpo_data)} 条 → {output_file}")
        
        return output_file
    
    def prepare_all_agents_dpo_data(
        self,
        config_json: List[Dict],
        dataset_file: str,
        trajectory_file: str = None,
        output_dir: str = None,
        log_callback: callable = None
    ) -> Dict[str, Dict]:
        """
        为所有 trainable DPO Agent 生成训练数据。
        
        Args:
            config_json: 完整的系统配置（agent 列表）
            dataset_file: 数据集文件路径 (JSONL)
            trajectory_file: 轨迹文件路径
            output_dir: 输出目录
            log_callback: 日志回调
        
        Returns:
            Dict: {agent_id: {"data_file": path, "agent_config": config_dict}}
        """
        if output_dir is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(self.output_dir, 'system_dpo', f"run_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        trainable_agents = []
        for agent in config_json:
            training = agent.get('training', {})
            if training.get('trainable') and training.get('mode') == 'dpo':
                trainable_agents.append(agent)
        
        if not trainable_agents:
            raise ValueError(
                "没有找到可训练的 DPO Agent。请确保至少一个 agent 配置了 "
                "'training': {'trainable': true, 'mode': 'dpo'}"
            )
        
        if log_callback:
            agent_names = [a.get('agent_id') for a in trainable_agents]
            log_callback(f"找到 {len(trainable_agents)} 个可训练 DPO Agent: {agent_names}")
        
        # 检查数据集是否是纯 DPO 格式（包含 chosen/rejected）
        is_pure_dpo = self._is_pure_dpo_dataset(dataset_file)
        
        result = {}
        if is_pure_dpo:
            # 纯 DPO 格式：直接按 agent_id 分割
            if log_callback:
                log_callback("检测到纯 DPO 数据集格式，按 agent_id 分割...")
            result = self._split_pure_dpo_by_agent(
                config_json=trainable_agents,
                dataset_file=dataset_file,
                output_dir=output_dir,
                log_callback=log_callback
            )
        else:
            # SFT 格式：需要生成偏好对
            if log_callback:
                log_callback("检测到 SFT 数据集格式，生成 DPO 偏好对...")
            for agent in trainable_agents:
                agent_id = agent.get('agent_id', 'unknown')
                output_file = os.path.join(output_dir, f"{agent_id}_dpo.jsonl")
                
                try:
                    data_file = self.prepare_agent_dpo_data(
                        agent_config=agent,
                        dataset_file=dataset_file,
                        trajectory_file=trajectory_file,
                        output_file=output_file,
                        log_callback=log_callback
                    )
                    result[agent_id] = {
                        'data_file': data_file,
                        'agent_config': agent
                    }
                except Exception as e:
                    if log_callback:
                        log_callback(f"[{agent_id}] 数据生成失败: {str(e)}")
                    result[agent_id] = {
                        'data_file': None,
                        'agent_config': agent,
                        'error': str(e)
                    }
        
        return result
    
    def _is_pure_dpo_dataset(self, dataset_file: str) -> bool:
        """
        检查数据集是否是纯 DPO 格式（包含 chosen/rejected 字段）
        
        Args:
            dataset_file: 数据集文件路径
        
        Returns:
            bool: True 如果是纯 DPO 格式
        """
        try:
            with open(dataset_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if not first_line:
                    return False
                sample = json.loads(first_line)
                return 'chosen' in sample and 'rejected' in sample
        except Exception:
            return False
    
    def _convert_to_swift_dpo_format(self, sample: Dict) -> Dict:
        """
        将 DPO 数据转换为 ms-swift 4.4.2 兼容格式。
        
        ms-swift DPO 要求: {"messages": [{"role": "user", "content": ...}], "chosen": ..., "rejected": ...}
        兼容旧格式: {"instruction": ..., "input": ..., "chosen": ..., "rejected": ...}
        """
        # 如果已有 messages 字段且格式正确，直接返回
        if 'messages' in sample:
            return sample
        
        # 转换 instruction/input 格式为 messages 格式
        instruction = sample.get('instruction', '')
        input_text = sample.get('input', '')
        
        # 构建 user content
        if instruction and input_text:
            user_content = f"{instruction}\n{input_text}"
        elif instruction:
            user_content = instruction
        elif input_text:
            user_content = input_text
        else:
            user_content = ''
        
        result = {
            'messages': [{'role': 'user', 'content': user_content}],
            'chosen': sample.get('chosen', ''),
            'rejected': sample.get('rejected', ''),
        }
        # 保留 metadata
        if 'metadata' in sample:
            result['metadata'] = sample['metadata']
        
        return result

    def _split_pure_dpo_by_agent(
        self,
        config_json: List[Dict],
        dataset_file: str,
        output_dir: str,
        log_callback: callable = None
    ) -> Dict[str, Dict]:
        """
        将纯 DPO 数据集按 agent_id 分割成多个文件
        
        Args:
            config_json: Agent 配置列表
            dataset_file: DPO 数据集文件
            output_dir: 输出目录
            log_callback: 日志回调
        
        Returns:
            Dict: {agent_id: {"data_file": path, "agent_config": config}}
        """
        result = {}
        
        # 读取所有样本并按 agent_id 分组
        samples_by_agent = {}
        with open(dataset_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                sample = json.loads(line)
                agent_id = sample.get('metadata', {}).get('agent_id')
                if not agent_id:
                    continue
                if agent_id not in samples_by_agent:
                    samples_by_agent[agent_id] = []
                samples_by_agent[agent_id].append(sample)
        
        # 为每个 agent 生成独立文件（转换为 ms-swift 格式）
        for agent in config_json:
            agent_id = agent.get('agent_id', '')
            if agent_id not in samples_by_agent:
                if log_callback:
                    log_callback(f"[{agent_id}] 数据集中没有该 agent 的样本，跳过")
                result[agent_id] = {
                    'data_file': None,
                    'agent_config': agent,
                    'error': f'数据集中没有 agent_id={agent_id} 的样本'
                }
                continue
            
            output_file = os.path.join(output_dir, f"{agent_id}_dpo.jsonl")
            samples = samples_by_agent[agent_id]
            
            # 写入文件（自动转换为 ms-swift DPO 格式）
            with open(output_file, 'w', encoding='utf-8') as f:
                for sample in samples:
                    converted = self._convert_to_swift_dpo_format(sample)
                    f.write(json.dumps(converted, ensure_ascii=False) + '\n')
            
            if log_callback:
                log_callback(f"[{agent_id}] 生成了 {len(samples)} 个 DPO 偏好对 -> {output_file}")
            
            result[agent_id] = {
                'data_file': output_file,
                'agent_config': agent
            }
        
        return result
    
    # ============== Cache Cleanup (Windows fix) ==============
    
    def _clean_datasets_cache(self):
        """清理 HuggingFace datasets 库的缓存文件，防止 Windows 上 FileExistsError"""
        cache_dirs = [
            os.path.expanduser('~/.cache/modelscope/hub/datasets'),
            os.path.expanduser('~/.cache/huggingface/datasets'),
        ]
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                except Exception:
                    for subdir in os.listdir(cache_dir):
                        subpath = os.path.join(cache_dir, subdir)
                        try:
                            if os.path.isdir(subpath):
                                shutil.rmtree(subpath, ignore_errors=True)
                        except Exception:
                            pass
    
    # ============== Subprocess-Based Training (A1) ==============
    
    def train_with_subprocess(
        self,
        data_file: str,
        model_path: str,
        ref_model_path: str = None,
        output_dir: str = None,
        hyperparameters: Dict[str, Any] = None,
        log_callback: callable = None,
        metrics_callback: callable = None
    ) -> Dict[str, Any]:
        """
        使用 ms-swift subprocess 进行 DPO 训练。
        
        Args:
            data_file: 训练数据文件路径
            model_path: 模型路径 (策略模型)
            ref_model_path: 参考模型路径
            output_dir: 输出目录
            hyperparameters: 超参数字典
            log_callback: 日志回调
            metrics_callback: 指标回调
        
        Returns:
            Dict: 训练结果
        """
        try:
            self._clean_datasets_cache()
            if log_callback:
                log_callback("Datasets cache cleaned to prevent file conflicts")
            
            os.environ['HF_DATASETS_DISABLE_CACHING'] = '1'
            
            if output_dir is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_dir = os.path.join(self.output_dir, f"run_{timestamp}")
            
            os.makedirs(output_dir, exist_ok=True)
            
            if ref_model_path is None:
                ref_model_path = model_path
            
            import torch
            default_params = {
                'lr': 5e-7,
                'batch_size': 2,
                'num_epochs': 3,
                'max_length': 2048,
                'beta': 0.1,
                'warmup_ratio': 0.1,
                'weight_decay': 0.01,
                'gradient_accumulation_steps': 4,
                'save_steps': 100,
                'logging_steps': 10,
                'use_lora': True,
                'lora_rank': 8,
                'lora_alpha': 32,
                'use_flash_attn': torch.cuda.is_available(),
                'gradient_checkpointing': True,
            }
            
            if hyperparameters:
                default_params.update(hyperparameters)
            
            if not torch.cuda.is_available():
                default_params['use_flash_attn'] = False
                if log_callback:
                    log_callback("CPU environment detected, disabling Flash Attention")
            
            model_type = self._infer_model_type(model_path)
            
            if log_callback:
                log_callback(f"Model type: {model_type}, Model: {model_path}")
                log_callback(f"Ref Model: {ref_model_path}")
                log_callback(f"Dataset: {data_file}")
                log_callback(f"Hyperparameters: {default_params}")
            
            # Build swift rlhf command (DPO is default, no need to specify --rlhf_type)
            # Note: rlhf_type field is Literal type, HfArgumentParser cannot parse it from CLI
            cmd = [
                'swift', 'rlhf',
                '--model', model_path,
                # Note: --ref_model is NOT allowed with LoRA (ref model is auto-derived from frozen base weights)
                '--dataset', data_file,
                '--output_dir', output_dir,
                '--learning_rate', str(default_params['lr']),
                '--num_train_epochs', str(default_params['num_epochs']),
                '--per_device_train_batch_size', str(default_params['batch_size']),
                '--gradient_accumulation_steps', str(default_params['gradient_accumulation_steps']),
                '--beta', str(default_params['beta']),
                '--save_steps', str(default_params['save_steps']),
                '--logging_steps', str(default_params['logging_steps']),
                '--max_length', str(default_params['max_length']),
                '--warmup_ratio', str(default_params['warmup_ratio']),
                '--weight_decay', str(default_params['weight_decay']),
                '--lr_scheduler_type', 'cosine',
            ]
            
            # 使用 bf16（现代 GPU 默认），与模型 dtype 保持一致
            # 避免 fp16 与 bfloat16 模型冲突
            cmd.extend(['--bf16', 'true'])
            
            if default_params.get('use_lora'):
                cmd.extend([
                    '--tuner_type', 'lora',
                    '--lora_rank', str(default_params.get('lora_rank', 8)),
                    '--lora_alpha', str(default_params.get('lora_alpha', 32)),
                    '--lora_dropout', '0.05',
                ])
                if log_callback:
                    log_callback(f"Using LoRA (rank={default_params.get('lora_rank', 8)}, "
                               f"alpha={default_params.get('lora_alpha', 32)})")
            
            if default_params.get('use_flash_attn'):
                cmd.extend(['--attn_impl', 'flash_attn'])
            
            if default_params.get('gradient_checkpointing'):
                cmd.extend(['--gradient_checkpointing', 'true'])
            
            if log_callback:
                log_callback(f"Command: {' '.join(cmd)}")
                log_callback("Starting DPO training with ms-swift (subprocess)...")
            
            # Save training config
            config_file = os.path.join(output_dir, 'training_config.json')
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'type': 'dpo',
                    'model_path': model_path,
                    'ref_model_path': ref_model_path,
                    'data_file': data_file,
                    'hyperparameters': default_params,
                    'command': ' '.join(cmd)
                }, f, ensure_ascii=False, indent=2)
            
            # Execute via subprocess
            output_lines = []  # 保存所有输出行
            
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
                        output_lines.append(stripped)  # 保存输出
                        if log_callback:
                            log_callback(stripped)
                        # Parse metrics from output
                        if metrics_callback and 'loss' in stripped.lower():
                            self._parse_and_report_metrics(stripped, metrics_callback)
                process.stdout.close()
                process.wait()
            
            output_thread = threading.Thread(target=read_output)
            output_thread.start()
            output_thread.join()
            
            if process.returncode == 0:
                if log_callback:
                    log_callback("DPO Training completed successfully!")
                return {
                    'status': 'completed',
                    'output_dir': output_dir,
                    'message': 'DPO 训练完成'
                }
            else:
                error_msg = f'DPO Training failed with return code: {process.returncode}'
                # 保存完整错误日志到文件
                error_log_file = os.path.join(output_dir, 'error.log')
                with open(error_log_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(output_lines))
                
                if log_callback:
                    log_callback(error_msg)
                    log_callback(f"完整错误日志已保存: {error_log_file}")
                    # 打印最后 20 行错误信息
                    last_lines = output_lines[-20:] if len(output_lines) > 20 else output_lines
                    if last_lines:
                        log_callback("最后 20 行错误输出:")
                        for line in last_lines:
                            log_callback(f"  {line}")
                
                return {
                    'status': 'error',
                    'message': error_msg,
                    'error_log': '\n'.join(output_lines[-50:])  # 返回最后 50 行
                }
        
        except FileNotFoundError:
            error_msg = 'swift command not found. Please install ms-swift: pip install ms-swift'
            if log_callback:
                log_callback(error_msg)
            return {'status': 'error', 'message': error_msg}
        except Exception as e:
            error_msg = str(e)
            if log_callback:
                log_callback(f"DPO Training error: {error_msg}")
            return {'status': 'error', 'message': error_msg}
    
    def _parse_and_report_metrics(self, line: str, metrics_callback: callable):
        """尝试从训练输出行中解析 metrics"""
        try:
            # 尝试匹配常见格式: "loss=0.123" 或 "'loss': 0.123"
            import re as _re
            loss_match = _re.search(r'loss[=:]\s*([\d.]+)', line, _re.IGNORECASE)
            step_match = _re.search(r'step[=:]\s*(\d+)', line, _re.IGNORECASE)
            lr_match = _re.search(r'(?:lr|learning_rate)[=:]\s*([\d.eE+-]+)', line, _re.IGNORECASE)
            
            if loss_match:
                step = int(step_match.group(1)) if step_match else 0
                loss = float(loss_match.group(1))
                lr = float(lr_match.group(1)) if lr_match else 0.0
                metrics_callback(step, loss, lr)
        except Exception:
            pass
    
    # ============== System-Level Multi-Agent DPO Training (A2) ==============
    
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
        System-level 多 Agent DPO 训练。
        
        解析 config_json 中的 training 配置，为每个 trainable DPO agent 生成独立数据，
        顺序执行训练，汇总结果。
        
        Args:
            config_json: 完整的系统配置（agent 列表）
            dataset_file: 数据集文件路径 (JSONL)
            trajectory_file: 轨迹文件路径（用于 student outputs）
            default_hyperparameters: 默认超参数
            log_callback: 日志回调
            metrics_callback: 指标回调
        
        Returns:
            Dict: 训练结果
        """
        import time
        
        # 如果没有提供 log_callback，使用默认 print 输出，确保错误信息可见
        if log_callback is None:
            log_callback = lambda msg: print(msg)
        
        if log_callback:
            log_callback("=" * 60)
            log_callback("System-Level Multi-Agent DPO Training")
            log_callback("=" * 60)
        
        # Step 1: 为所有 trainable DPO agent 生成训练数据
        if log_callback:
            log_callback("\n[Phase 1] 生成各 Agent DPO 训练数据...")
        
        try:
            agents_data = self.prepare_all_agents_dpo_data(
                config_json=config_json,
                dataset_file=dataset_file,
                trajectory_file=trajectory_file,
                log_callback=log_callback
            )
        except Exception as e:
            error_msg = f"数据生成失败: {str(e)}"
            if log_callback:
                log_callback(error_msg)
            return {
                'status': 'error',
                'mode': 'system_level_dpo',
                'agents': [],
                'overall_message': error_msg
            }
        
        valid_agents = {aid: data for aid, data in agents_data.items() 
                       if data.get('data_file') is not None}
        
        if not valid_agents:
            return {
                'status': 'error',
                'mode': 'system_level_dpo',
                'agents': [],
                'overall_message': '所有 Agent 的 DPO 训练数据生成均失败'
            }
        
        total_agents = len(valid_agents)
        if log_callback:
            log_callback(f"\n[Phase 2] 开始 DPO 训练 {total_agents} 个 Agent...")
        
        # Step 2: 顺序训练每个 agent
        agent_results = []
        completed_count = 0
        failed_count = 0
        
        for idx, (agent_id, agent_data) in enumerate(valid_agents.items()):
            agent_config = agent_data['agent_config']
            data_file = agent_data['data_file']
            training_config = agent_config.get('training', {})
            
            # 获取 agent 专属的超参数
            agent_params = dict(default_hyperparameters or {})
            agent_train_params = training_config.get('train_parameters', {})
            if agent_train_params:
                agent_params.update(agent_train_params)
                if log_callback:
                    log_callback(f"[{agent_id}] 使用自定义参数: {agent_train_params}")
            
            # 获取 agent 的模型路径
            model_path = agent_config.get('model', {}).get('name_or_path', 'Qwen/Qwen2.5-0.5B-Instruct')
            ref_model_path = agent_config.get('model', {}).get('ref_model_path', model_path)
            
            loss_weight = training_config.get('loss', {}).get('weight', 1.0)
            
            if log_callback:
                log_callback(f"\n{'─' * 40}")
                log_callback(f"[{idx+1}/{total_agents}] DPO 训练 Agent: {agent_id}")
                log_callback(f"  模型: {model_path}")
                log_callback(f"  参考模型: {ref_model_path}")
                log_callback(f"  数据: {data_file}")
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
                result = self.train_with_subprocess(
                    data_file=data_file,
                    model_path=model_path,
                    ref_model_path=ref_model_path,
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
                        log_callback(f"[{agent_id}] ✅ DPO 训练完成 (耗时 {elapsed/60:.1f} 分钟)")
                else:
                    failed_count += 1
                    error_msg = result.get('message', 'Unknown error')
                    error_log = result.get('error_log', '')
                    agent_result['error'] = error_msg
                    if error_log:
                        agent_result['error_log'] = error_log
                    if log_callback:
                        log_callback(f"[{agent_id}] ❌ DPO 训练失败: {error_msg}")
                        if error_log:
                            log_callback(f"[{agent_id}] 错误详情 (最后20行):")
                            for line in error_log.split('\n')[-20:]:
                                log_callback(f"  {line}")
                
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
                    log_callback(f"[{agent_id}] ❌ DPO 训练异常: {str(e)}")
        
        # Step 3: 汇总结果
        if completed_count == total_agents:
            overall_status = 'completed'
            overall_msg = f'所有 {total_agents} 个 Agent DPO 训练完成'
        elif completed_count > 0:
            overall_status = 'partial'
            overall_msg = f'{completed_count}/{total_agents} 个 Agent DPO 训练完成，{failed_count} 个失败'
        else:
            overall_status = 'error'
            overall_msg = f'所有 {total_agents} 个 Agent DPO 训练均失败'
        
        if log_callback:
            log_callback(f"\n{'=' * 60}")
            log_callback(f"System-Level DPO 完成: {overall_msg}")
            log_callback(f"{'=' * 60}")
        
        return {
            'status': overall_status,
            'mode': 'system_level_dpo',
            'agents': agent_results,
            'overall_message': overall_msg
        }
    
    # ============== Model Type Inference ==============
    
    def _infer_model_type(self, model_path: str) -> str:
        """从模型路径推断 model_type (ms-swift 格式)"""
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
        
        elif 'gpt' in path_lower:
            return 'gpt2'
        
        return 'qwen2_5-0_5b-instruct'
    
    def get_training_script(self, training_info: Dict) -> str:
        """生成训练脚本"""
        cmd = training_info.get('command', [])
        if not cmd:
            return "# 训练命令未生成"
        
        script = "#!/bin/bash\n\n"
        script += "# DPO Training Script\n\n"
        script += " ".join(cmd) + "\n"
        
        return script
