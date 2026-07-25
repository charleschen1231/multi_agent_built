# training/sft_trainer.py
import os
import re
import json
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime


class SFTTrainer:
    """SFT 训练器 - 整合 ms-swift"""
    
    def __init__(self, output_dir: str = "./training_outputs/sft"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def prepare_training_data(self, trajectories: List[Dict], 
                             output_file: str = None) -> str:
        """
        将轨迹数据转换为 SFT 训练格式 (ms-swift 兼容格式)
        
        Args:
            trajectories: 轨迹数据列表
            output_file: 输出文件路径
            
        Returns:
            str: 训练数据文件路径
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.output_dir, f"sft_data_{timestamp}.jsonl")
        
        sft_data = []
        
        for traj in trajectories:
            for step in traj.get('steps', []):
                # 只有有 ground_truth 的步骤才用于训练
                if step.get('ground_truth'):
                    # 转换为 ms-swift 的 messages 格式
                    messages = []
                    
                    # 系统提示词
                    system_prompt = step.get('metadata', {}).get('system_prompt', '')
                    if system_prompt:
                        messages.append({
                            "role": "system",
                            "content": system_prompt
                        })
                    
                    # 用户输入
                    user_content = step.get('prompt', '')
                    if user_content:
                        messages.append({
                            "role": "user",
                            "content": user_content
                        })
                    
                    # 助手输出 (ground_truth)
                    assistant_content = step.get('ground_truth', '')
                    if assistant_content:
                        messages.append({
                            "role": "assistant",
                            "content": assistant_content
                        })
                    
                    if len(messages) >= 2:  # 至少需要 system+assistant 或 user+assistant
                        sft_data.append({
                            "messages": messages,
                            "metadata": {
                                'agent_id': step.get('agent_id'),
                                'trajectory_id': traj.get('trajectory_id'),
                                'sample_id': traj.get('sample_id')
                            }
                        })
        
        # 保存为 JSONL
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in sft_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        return output_file
    
    # ============== System-Level Multi-Agent SFT ==============
    
    def _render_prompt_template(self, template: str, input_data: Dict[str, Any]) -> str:
        """
        渲染 prompt_template，替换 {{input.xxx}} 变量。
        
        Args:
            template: 模板字符串，如 "问题：{{input.user_request}}"
            input_data: 输入数据字典，如 {"user_request": "计算1+1"}
        
        Returns:
            str: 渲染后的字符串
        """
        import re
        result = template
        # 匹配 {{input.xxx}} 或 {{input.xxx.yyy}} 格式
        pattern = r'\{\{input\.(\w+(?:\.\w+)*)\}\}'
        
        def replacer(match):
            key_path = match.group(1)
            keys = key_path.split('.')
            value = input_data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return match.group(0)  # 未找到则保留原样
            return str(value)
        
        result = re.sub(pattern, replacer, result)
        return result
    
    def prepare_agent_sft_data(
        self,
        agent_config: Dict[str, Any],
        dataset_file: str,
        output_file: str = None,
        log_callback: callable = None
    ) -> str:
        """
        为单个 Agent 生成 SFT 训练数据（ms-swift messages 格式）。
        
        根据 agent 的 training.ground_truth 配置，从数据集中提取
        input（用 input_key）和 ground truth（用 gt_key），
        结合 agent 的 instruction_prompt 生成训练样本。
        
        Args:
            agent_config: 单个 agent 的完整配置字典
            dataset_file: 数据集文件路径 (JSONL)
            output_file: 输出文件路径（可选，自动生成）
            log_callback: 日志回调
        
        Returns:
            str: 生成的训练数据文件路径
        """
        agent_id = agent_config.get('agent_id', 'unknown')
        training_config = agent_config.get('training', {})
        ground_truth = training_config.get('ground_truth', {})
        dataset_config = training_config.get('dataset', {})
        instruction_prompt = agent_config.get('instruction_prompt', {})
        
        gt_key = ground_truth.get('gt_key')
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
            output_dir = os.path.join(self.output_dir, 'system_sft')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"{agent_id}_sft_{timestamp}.jsonl")
        
        # 读取数据集
        samples = []
        with open(dataset_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))
        
        if log_callback:
            log_callback(f"[{agent_id}] 读取数据集: {len(samples)} 条样本")
            log_callback(f"[{agent_id}] gt_key={gt_key}, input_key={input_key}")
        
        # 生成 SFT 数据
        sft_data = []
        skipped = 0
        
        for i, sample in enumerate(samples):
            # 获取输入数据
            input_data = sample.get('input', sample)
            
            # 获取 ground truth
            gt_value = sample.get(gt_key)
            if gt_value is None:
                skipped += 1
                continue
            
            # 构建 messages
            messages = []
            
            # 1. System prompt
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # 2. User prompt（渲染模板）
            user_content = self._render_prompt_template(prompt_template, input_data)
            if user_content:
                messages.append({
                    "role": "user",
                    "content": user_content
                })
            
            # 3. Assistant output（ground truth）
            assistant_content = str(gt_value) if not isinstance(gt_value, str) else gt_value
            if assistant_content:
                messages.append({
                    "role": "assistant",
                    "content": assistant_content
                })
            
            if len(messages) >= 2:
                sft_data.append({
                    "messages": messages,
                    "metadata": {
                        'agent_id': agent_id,
                        'sample_index': i
                    }
                })
        
        if skipped > 0 and log_callback:
            log_callback(f"[{agent_id}] 跳过 {skipped} 条缺少 gt_key='{gt_key}' 的样本")
        
        if len(sft_data) == 0:
            raise ValueError(
                f"Agent '{agent_id}': 没有可用的训练样本。"
                f"请检查数据集中是否包含 '{gt_key}' 字段。"
            )
        
        # 保存为 JSONL
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in sft_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        if log_callback:
            log_callback(f"[{agent_id}] 生成训练数据: {len(sft_data)} 条 → {output_file}")
        
        return output_file
    
    def prepare_all_agents_sft_data(
        self,
        config_json: List[Dict],
        dataset_file: str,
        output_dir: str = None,
        log_callback: callable = None
    ) -> Dict[str, Dict]:
        """
        为所有 trainable Agent 生成 SFT 训练数据。
        
        遍历 config_json，找到所有 training.trainable==true && training.mode=="sft" 的 agent，
        为每个 agent 调用 prepare_agent_sft_data() 生成独立的训练数据文件。
        
        Args:
            config_json: 完整的系统配置（agent 列表）
            dataset_file: 数据集文件路径 (JSONL)
            output_dir: 输出目录
            log_callback: 日志回调
        
        Returns:
            Dict: {agent_id: {"data_file": path, "agent_config": config_dict}}
        """
        if output_dir is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(self.output_dir, 'system_sft', f"run_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 找到所有 trainable agents
        trainable_agents = []
        for agent in config_json:
            training = agent.get('training', {})
            if training.get('trainable') and training.get('mode') == 'sft':
                trainable_agents.append(agent)
        
        if not trainable_agents:
            raise ValueError(
                "没有找到可训练的 Agent。请确保至少一个 agent 配置了 "
                "'training': {'trainable': true, 'mode': 'sft'}"
            )
        
        if log_callback:
            agent_names = [a.get('agent_id') for a in trainable_agents]
            log_callback(f"找到 {len(trainable_agents)} 个可训练 Agent: {agent_names}")
        
        # 为每个 agent 生成数据
        result = {}
        for agent in trainable_agents:
            agent_id = agent.get('agent_id', 'unknown')
            output_file = os.path.join(output_dir, f"{agent_id}_sft.jsonl")
            
            try:
                data_file = self.prepare_agent_sft_data(
                    agent_config=agent,
                    dataset_file=dataset_file,
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
    
    def train(self,
              data_file: str,
              model_path: str,
              output_dir: str = None,
              hyperparameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        启动 SFT 训练
        
        Args:
            data_file: 训练数据文件路径
            model_path: 模型路径
            output_dir: 输出目录
            hyperparameters: 超参数字典
            
        Returns:
            Dict: 训练结果信息
        """
        if output_dir is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(self.output_dir, f"run_{timestamp}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 默认超参数
        default_params = {
            'lr': 2e-5,
            'batch_size': 4,
            'num_epochs': 3,
            'max_length': 2048,
            'warmup_ratio': 0.1,
            'weight_decay': 0.01,
            'gradient_accumulation_steps': 1,
            'save_steps': 100,
            'logging_steps': 10,
            'fp16': True
        }
        
        if hyperparameters:
            default_params.update(hyperparameters)
        
        # 推断 model_type
        model_type = self._infer_model_type(model_path)
        
        # 构建 SWIFT 命令
        cmd = [
            'swift', 'sft',
            '--model_type', model_type,
            '--model', model_path,
            '--dataset', data_file,
            '--output_dir', output_dir,
            '--learning_rate', str(default_params['lr']),
            '--num_train_epochs', str(default_params['num_epochs']),
            '--per_device_train_batch_size', str(default_params['batch_size']),
            '--gradient_accumulation_steps', str(default_params['gradient_accumulation_steps']),
            '--save_steps', str(default_params['save_steps']),
            '--logging_steps', str(default_params['logging_steps']),
            '--max_length', str(default_params['max_length']),
            '--warmup_ratio', str(default_params['warmup_ratio']),
            '--weight_decay', str(default_params['weight_decay']),
            '--lr_scheduler_type', 'cosine',
        ]
        
        if default_params['fp16']:
            cmd.append('--fp16')
        
        # 保存训练配置
        config_file = os.path.join(output_dir, 'training_config.json')
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({
                'type': 'sft',
                'model_path': model_path,
                'data_file': data_file,
                'hyperparameters': default_params,
                'command': ' '.join(cmd)
            }, f, ensure_ascii=False, indent=2)
        
        return {
            'command': cmd,
            'output_dir': output_dir,
            'config_file': config_file,
            'status': 'prepared'
        }
    
    def _clean_datasets_cache(self):
        """
        清理 HuggingFace datasets 库的缓存文件，防止 Windows 上
        FileExistsError / OSError 导致训练失败。
        这是 Windows 上 datasets 库的已知问题：残留的 .arrow 和 tmp 文件
        会导致后续的 dataset.map() 操作失败。
        """
        import shutil
        cache_dirs = [
            os.path.expanduser('~/.cache/modelscope/hub/datasets'),
            os.path.expanduser('~/.cache/huggingface/datasets'),
        ]
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    shutil.rmtree(cache_dir)
                except Exception:
                    # 如果部分文件被锁定，尝试逐个删除子目录
                    for subdir in os.listdir(cache_dir):
                        subpath = os.path.join(cache_dir, subdir)
                        try:
                            if os.path.isdir(subpath):
                                shutil.rmtree(subpath, ignore_errors=True)
                        except Exception:
                            pass
    
    def train_with_api(self,
                       data_file: str,
                       model_path: str,
                       output_dir: str = None,
                       hyperparameters: Dict[str, Any] = None,
                       log_callback: callable = None,
                       metrics_callback: callable = None) -> Dict[str, Any]:
        """
        使用 ms-swift 进行训练（优先使用命令行方式，更稳定）
        
        Args:
            data_file: 训练数据文件路径
            model_path: 模型路径
            output_dir: 输出目录
            hyperparameters: 超参数字典
            log_callback: 日志回调函数 (message: str) -> None
            metrics_callback: 指标回调函数 (step: int, loss: float, lr: float) -> None
        """
        import subprocess
        import threading
        
        try:
            # 训练前清理 datasets 缓存，防止 Windows 上缓存文件冲突
            self._clean_datasets_cache()
            if log_callback:
                log_callback("Datasets cache cleaned to prevent file conflicts")
            
            # 设置环境变量禁用 datasets 缓存（双重保险）
            os.environ['HF_DATASETS_DISABLE_CACHING'] = '1'
            
            if output_dir is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_dir = os.path.join(self.output_dir, f"run_{timestamp}")
            
            os.makedirs(output_dir, exist_ok=True)
            
            if log_callback:
                log_callback(f"Creating output directory: {output_dir}")
            
            # 默认超参数
            import torch
            default_params = {
                'lr': 2e-5,
                'batch_size': 4,
                'num_epochs': 3,
                'max_length': 2048,
                'warmup_ratio': 0.1,
                'weight_decay': 0.01,
                'gradient_accumulation_steps': 1,
                'save_steps': 100,
                'logging_steps': 10,
                'fp16': True,
                # 高效训练参数
                'use_lora': True,
                'lora_rank': 8,
                'lora_alpha': 32,
                # Flash Attention 需要 GPU 和 flash_attn 包，CPU 环境下禁用
                'use_flash_attn': torch.cuda.is_available(),
                'gradient_checkpointing': True,
                'quantization': None,
            }
            
            if hyperparameters:
                default_params.update(hyperparameters)
            
            # 强制在 CPU 环境下禁用 Flash Attention（无论前端传什么参数）
            if not torch.cuda.is_available():
                default_params['use_flash_attn'] = False
                if log_callback:
                    log_callback("CPU environment detected, disabling Flash Attention")
            
            if log_callback:
                log_callback(f"Hyperparameters: {default_params}")
            
            # 推断 model_type (可选)
            model_type = self._infer_model_type(model_path)
            
            if log_callback:
                log_callback(f"Model type: {model_type}, Model: {model_path}")
                log_callback(f"Dataset: {data_file}")
            
            # 构建命令行
            cmd = [
                'swift', 'sft',
                '--model', model_path,
                '--dataset', data_file,
                '--output_dir', output_dir,
                '--learning_rate', str(default_params['lr']),
                '--num_train_epochs', str(default_params['num_epochs']),
                '--per_device_train_batch_size', str(default_params['batch_size']),
                '--gradient_accumulation_steps', str(default_params['gradient_accumulation_steps']),
                '--save_steps', str(default_params['save_steps']),
                '--logging_steps', str(default_params['logging_steps']),
                '--max_length', str(default_params['max_length']),
                '--warmup_ratio', str(default_params['warmup_ratio']),
                '--weight_decay', str(default_params['weight_decay']),
                '--lr_scheduler_type', 'cosine',
            ]
            
            # 混合精度训练 - 使用 bf16 (推荐) 或 fp16
            # ms-swift 默认使用 bf16，如果设置 fp16 需要显式关闭 bf16
            if default_params.get('fp16'):
                cmd.extend(['--fp16', 'true'])
                cmd.extend(['--bf16', 'false'])  # 关闭 bf16 避免冲突
            
            # LoRA 参数高效微调
            if default_params.get('use_lora'):
                cmd.extend([
                    '--tuner_type', 'lora',
                    '--lora_rank', str(default_params.get('lora_rank', 8)),
                    '--lora_alpha', str(default_params.get('lora_alpha', 32)),
                    '--lora_dropout', '0.05',
                ])
                if log_callback:
                    log_callback(f"Using LoRA (rank={default_params.get('lora_rank', 8)}, alpha={default_params.get('lora_alpha', 32)})")
            
            # Flash Attention 加速
            if default_params.get('use_flash_attn'):
                cmd.extend(['--attn_impl', 'flash_attn'])
                if log_callback:
                    log_callback("Using Flash Attention for faster training")
            
            # 梯度检查点节省显存
            if default_params.get('gradient_checkpointing'):
                cmd.extend(['--gradient_checkpointing', 'true'])
                if log_callback:
                    log_callback("Using Gradient Checkpointing to save memory")
            
            # 量化训练 (QLoRA)
            quantization = default_params.get('quantization')
            if quantization == '4bit':
                cmd.extend(['--quantization_bit', '4'])
                if log_callback:
                    log_callback("Using 4-bit quantization (QLoRA)")
            elif quantization == '8bit':
                cmd.extend(['--quantization_bit', '8'])
                if log_callback:
                    log_callback("Using 8-bit quantization")
            
            if log_callback:
                log_callback(f"Command: {' '.join(cmd)}")
                log_callback("Starting training with ms-swift (command line)...")
            
            # 使用 subprocess 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # 实时读取输出
            def read_output():
                for line in iter(process.stdout.readline, ''):
                    if line:
                        if log_callback:
                            log_callback(line.strip())
                        # 解析 metrics
                        if metrics_callback and 'loss' in line.lower():
                            self._parse_and_report_metrics(line.strip(), metrics_callback)
                process.stdout.close()
                process.wait()
            
            # 启动读取线程
            output_thread = threading.Thread(target=read_output)
            output_thread.start()
            output_thread.join()
            
            # 检查返回码
            if process.returncode == 0:
                if log_callback:
                    log_callback("Training completed successfully!")
                return {
                    'status': 'completed',
                    'output_dir': output_dir,
                    'message': '训练完成'
                }
            else:
                error_msg = f'Training failed with return code: {process.returncode}'
                if log_callback:
                    log_callback(error_msg)
                return {
                    'status': 'error',
                    'message': error_msg
                }
            
        except FileNotFoundError:
            error_msg = 'swift command not found. Please install ms-swift: pip install ms-swift'
            if log_callback:
                log_callback(error_msg)
            return {
                'status': 'error',
                'message': error_msg
            }
        except Exception as e:
            error_msg = str(e)
            if log_callback:
                log_callback(f"Training error: {error_msg}")
            return {
                'status': 'error',
                'message': error_msg
            }
    
    # ============== System-Level Multi-Agent Training ==============
    
    def train_system_level(
        self,
        config_json: List[Dict],
        dataset_file: str,
        default_hyperparameters: Dict[str, Any] = None,
        log_callback: callable = None,
        metrics_callback: callable = None
    ) -> Dict[str, Any]:
        """
        System-level 多 Agent SFT 训练。
        
        解析 config_json 中的 training 配置，为每个 trainable agent 生成独立数据，
        顺序执行训练，汇总结果。
        
        Args:
            config_json: 完整的系统配置（agent 列表）
            dataset_file: 数据集文件路径 (JSONL)
            default_hyperparameters: 默认超参数（agent 自己的参数会覆盖默认值）
            log_callback: 日志回调 (message: str) -> None
            metrics_callback: 指标回调 (step: int, loss: float, lr: float) -> None
        
        Returns:
            Dict: {
                'status': 'completed' | 'partial' | 'error',
                'mode': 'system_level',
                'agents': [{agent_id, status, output_dir, final_loss, ...}, ...],
                'overall_message': str
            }
        """
        import time
        
        if log_callback:
            log_callback("=" * 60)
            log_callback("System-Level Multi-Agent SFT Training")
            log_callback("=" * 60)
        
        # Step 1: 为所有 trainable agent 生成训练数据
        if log_callback:
            log_callback("\n[Phase 1] 生成各 Agent 训练数据...")
        
        try:
            agents_data = self.prepare_all_agents_sft_data(
                config_json=config_json,
                dataset_file=dataset_file,
                log_callback=log_callback
            )
        except Exception as e:
            error_msg = f"数据生成失败: {str(e)}"
            if log_callback:
                log_callback(error_msg)
            return {
                'status': 'error',
                'mode': 'system_level',
                'agents': [],
                'overall_message': error_msg
            }
        
        # 过滤掉生成失败的 agent
        valid_agents = {aid: data for aid, data in agents_data.items() 
                       if data.get('data_file') is not None}
        
        if not valid_agents:
            return {
                'status': 'error',
                'mode': 'system_level',
                'agents': [],
                'overall_message': '所有 Agent 的训练数据生成均失败'
            }
        
        total_agents = len(valid_agents)
        if log_callback:
            log_callback(f"\n[Phase 2] 开始训练 {total_agents} 个 Agent...")
        
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
            
            # loss weight 信息
            loss_weight = training_config.get('loss', {}).get('weight', 1.0)
            
            if log_callback:
                log_callback(f"\n{'─' * 40}")
                log_callback(f"[{idx+1}/{total_agents}] 训练 Agent: {agent_id}")
                log_callback(f"  模型: {model_path}")
                log_callback(f"  数据: {data_file}")
                log_callback(f"  Loss Weight: {loss_weight}")
                log_callback(f"{'─' * 40}")
            
            # 创建带 agent_id 前缀的回调
            def make_agent_log_cb(agent_name, base_cb):
                def agent_log_cb(msg):
                    if base_cb:
                        base_cb(f"[{agent_name}] {msg}")
                return agent_log_cb
            
            agent_log_cb = make_agent_log_cb(agent_id, log_callback)
            
            # 指标回调 - 添加 agent_id 标识
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
            
            # 执行训练
            start_time = time.time()
            try:
                result = self.train_with_api(
                    data_file=data_file,
                    model_path=model_path,
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
                
                # 提取最终 loss
                metrics = current_agent_results.get('metrics_history', [])
                if metrics:
                    agent_result['final_loss'] = metrics[-1].get('loss')
                
                if status == 'completed':
                    completed_count += 1
                    if log_callback:
                        log_callback(f"[{agent_id}] ✅ 训练完成 (耗时 {elapsed/60:.1f} 分钟)")
                else:
                    failed_count += 1
                    agent_result['error'] = result.get('message', 'Unknown error')
                    if log_callback:
                        log_callback(f"[{agent_id}] ❌ 训练失败: {result.get('message')}")
                
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
                    log_callback(f"[{agent_id}] ❌ 训练异常: {str(e)}")
        
        # Step 3: 汇总结果
        if completed_count == total_agents:
            overall_status = 'completed'
            overall_msg = f'所有 {total_agents} 个 Agent 训练完成'
        elif completed_count > 0:
            overall_status = 'partial'
            overall_msg = f'{completed_count}/{total_agents} 个 Agent 训练完成，{failed_count} 个失败'
        else:
            overall_status = 'error'
            overall_msg = f'所有 {total_agents} 个 Agent 训练均失败'
        
        if log_callback:
            log_callback(f"\n{'=' * 60}")
            log_callback(f"System-Level SFT 完成: {overall_msg}")
            log_callback(f"{'=' * 60}")
        
        return {
            'status': overall_status,
            'mode': 'system_level',
            'agents': agent_results,
            'overall_message': overall_msg
        }
    
    def _parse_and_report_metrics(self, line: str, metrics_callback: callable):
        """尝试从训练输出行中解析 metrics"""
        try:
            loss_match = re.search(r'loss[=:]\s*([\d.]+)', line, re.IGNORECASE)
            step_match = re.search(r'step[=:]\s*(\d+)', line, re.IGNORECASE)
            lr_match = re.search(r'(?:lr|learning_rate)[=:]\s*([\d.eE+-]+)', line, re.IGNORECASE)
            
            if loss_match:
                step = int(step_match.group(1)) if step_match else 0
                loss = float(loss_match.group(1))
                lr = float(lr_match.group(1)) if lr_match else 0.0
                metrics_callback(step, loss, lr)
        except Exception:
            pass
    
    def _infer_model_type(self, model_path: str) -> str:
        """从模型路径推断 model_type (ms-swift 格式)"""
        path_lower = model_path.lower()
        
        # ms-swift 使用下划线格式，如 qwen2_5-0_5b-instruct
        if 'qwen2.5' in path_lower or 'qwen2_5' in path_lower:
            if '0.5b' in path_lower or '0_5b' in path_lower:
                return 'qwen2_5-0_5b-instruct'
            elif '1.5b' in path_lower or '1_5b' in path_lower:
                return 'qwen2_5-1_5b-instruct'
            elif '3b' in path_lower or '3b' in path_lower:
                return 'qwen2_5-3b-instruct'
            elif '7b' in path_lower or '7b' in path_lower:
                return 'qwen2_5-7b-instruct'
            elif '14b' in path_lower or '14b' in path_lower:
                return 'qwen2_5-14b-instruct'
            elif '32b' in path_lower or '32b' in path_lower:
                return 'qwen2_5-32b-instruct'
            else:
                return 'qwen2_5-0_5b-instruct'  # 默认使用 0.5B
        
        elif 'qwen2' in path_lower:
            return 'qwen2-7b-instruct'
        
        elif 'llama' in path_lower:
            return 'llama3-8b-instruct'
        
        elif 'gpt' in path_lower:
            return 'gpt2'  # 默认
        
        return 'qwen2_5-0_5b-instruct'  # 默认使用 Qwen2.5 0.5B
    
    def get_training_script(self, training_info: Dict) -> str:
        """生成训练脚本"""
        cmd = training_info.get('command', [])
        if not cmd:
            return "# 训练命令未生成"
        
        script = "#!/bin/bash\n\n"
        script += "# SFT Training Script\n\n"
        script += " ".join(cmd) + "\n"
        
        return script
