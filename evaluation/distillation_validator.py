# evaluation/distillation_validator.py
"""
蒸馏效果三向对比验证器

核心逻辑：
1. Teacher GT（教师模型标准答案）—— 从数据集的 *_gt 字段获取
2. Student Before（基座模型推理）—— 加载基座模型对数据集推理
3. Student After（微调后模型推理）—— 加载 LoRA 适配器推理

通过对比三者的指标差异，真实反映蒸馏效果。
"""
import os
import json
import asyncio
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Template

from evaluation.evaluator import SystemEvaluator


class DistillationValidator:
    """蒸馏效果三向对比验证器"""

    def __init__(self, output_dir: str = "./evaluation_outputs"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.evaluator = SystemEvaluator(output_dir=output_dir)

    async def validate(
        self,
        config_json: List[Dict],
        dataset_file: str,
        training_results: List[Dict],
        log_callback: callable = None
    ) -> Dict[str, Any]:
        """
        执行三向对比验证。

        Args:
            config_json: 系统配置（agent 列表）
            dataset_file: 数据集文件路径 (JSONL，包含 *_gt 字段)
            training_results: 训练结果列表，每项包含 agent_id, output_dir, model 等
            log_callback: 日志回调

        Returns:
            Dict: 完整的三向对比验证报告
        """
        timestamp = datetime.now().isoformat()
        report = {
            'status': 'running',
            'timestamp': timestamp,
            'phases': {},
            'agent_results': {},
            'summary': {}
        }

        try:
            # ── Phase 1: 提取 Teacher GT ──
            if log_callback:
                log_callback("[Phase 1/3] 提取教师模型 Ground Truth...")
            await asyncio.sleep(0)

            teacher_outputs = self._extract_teacher_gt(config_json, dataset_file)
            report['phases']['teacher_gt'] = {
                'status': 'completed',
                'sample_count': len(next(iter(teacher_outputs.values()), []))
            }
            if log_callback:
                for aid, outs in teacher_outputs.items():
                    log_callback(f"  [{aid}] {len(outs)} 条教师 GT")

            # ── Phase 2: 基座模型推理 (Student Before) ──
            if log_callback:
                log_callback("[Phase 2/3] 加载基座模型进行推理 (Student Before)...")
            await asyncio.sleep(0)

            # 优先从 training_results 获取基座模型路径（更可靠）
            base_model = None
            for tr in (training_results or []):
                m = tr.get('model', '')
                if m and not m.startswith('./training_outputs') and not m.startswith('training_outputs'):
                    base_model = m
                    break
            if not base_model:
                base_model = config_json[0].get('model', {}).get(
                    'name_or_path', 'Qwen/Qwen2.5-0.5B-Instruct'
                ) if config_json else 'Qwen/Qwen2.5-0.5B-Instruct'
            # 如果仍然是训练输出路径，使用默认值
            if base_model.startswith('./training_outputs') or base_model.startswith('training_outputs'):
                base_model = 'Qwen/Qwen2.5-0.5B-Instruct'

            base_outputs, base_ok = await self._run_model_inference(
                config_json=config_json,
                dataset_file=dataset_file,
                model_path=base_model,
                model_label="基座模型",
                teacher_outputs=teacher_outputs,
                log_callback=log_callback
            )
            report['phases']['student_before'] = {
                'status': 'completed' if base_ok else 'failed',
                'model': base_model,
                'sample_count': len(next(iter(base_outputs.values()), [])) if base_ok else 0
            }

            # ── Phase 3: LoRA 微调模型推理 (Student After) ──
            if log_callback:
                log_callback("[Phase 3/3] 加载微调模型进行推理 (Student After)...")
            await asyncio.sleep(0)

            lora_outputs, lora_ok = {}, False
            for tr in (training_results or []):
                agent_id = tr.get('agent_id', '')
                output_dir = tr.get('output_dir', '')
                if not output_dir or not os.path.exists(output_dir):
                    if log_callback:
                        log_callback(f"  [{agent_id}] 无训练输出目录，跳过")
                    continue

                checkpoint = self._find_checkpoint(output_dir)
                if not checkpoint:
                    if log_callback:
                        log_callback(f"  [{agent_id}] 未找到 checkpoint，跳过")
                    continue

                agent_cfg = self._find_agent_config(config_json, agent_id)
                if not agent_cfg:
                    continue

                # 优先使用 training result 的 model 字段作为基座模型路径
                agent_base = tr.get('model', '') or ''
                if not agent_base or agent_base.startswith('./training_outputs') or agent_base.startswith('training_outputs'):
                    agent_base = agent_cfg.get('model', {}).get(
                        'name_or_path', 'Qwen/Qwen2.5-0.5B-Instruct'
                    )
                # 如果仍然是训练输出路径，使用默认值
                if agent_base.startswith('./training_outputs') or agent_base.startswith('training_outputs'):
                    agent_base = 'Qwen/Qwen2.5-0.5B-Instruct'

                ok = await self._run_lora_inference(
                    agent_id=agent_id,
                    base_model_path=agent_base,
                    checkpoint_path=checkpoint,
                    config_json=config_json,
                    dataset_file=dataset_file,
                    teacher_outputs=teacher_outputs,
                    output_dict=lora_outputs,
                    log_callback=log_callback
                )
                if ok:
                    lora_ok = True

            report['phases']['student_after'] = {
                'status': 'completed' if lora_ok else 'failed',
                'sample_count': len(next(iter(lora_outputs.values()), [])) if lora_ok else 0
            }

            # ── 三向对比评估 ──
            if log_callback:
                log_callback("\n[Evaluation] 三向对比评估...")
            await asyncio.sleep(0)

            all_agent_results = {}

            # 收集所有 agent_id
            all_agents = set()
            all_agents.update(teacher_outputs.keys())
            all_agents.update(base_outputs.keys())
            all_agents.update(lora_outputs.keys())

            for agent_id in all_agents:
                t_outs = teacher_outputs.get(agent_id, [])
                b_outs = base_outputs.get(agent_id, [])
                l_outs = lora_outputs.get(agent_id, [])

                n = min(len(t_outs), max(len(b_outs), len(l_outs), 1))
                t_outs = t_outs[:n]

                agent_result = {'agent_id': agent_id, 'sample_count': n}

                # Before vs Teacher
                if b_outs:
                    b_outs = b_outs[:n]
                    before_eval = self.evaluator.evaluate_agent(
                        agent_id=agent_id,
                        student_outputs=b_outs,
                        teacher_outputs=t_outs
                    )
                    agent_result['before'] = {
                        'metrics': before_eval.get('metrics', {}),
                        'outputs': b_outs[:5]  # 前 5 条示例
                    }
                else:
                    agent_result['before'] = None

                # After vs Teacher
                if l_outs:
                    l_outs = l_outs[:n]
                    after_eval = self.evaluator.evaluate_agent(
                        agent_id=agent_id,
                        student_outputs=l_outs,
                        teacher_outputs=t_outs
                    )
                    agent_result['after'] = {
                        'metrics': after_eval.get('metrics', {}),
                        'outputs': l_outs[:5]
                    }
                else:
                    agent_result['after'] = None

                # 提升幅度
                before_score = 0.0
                after_score = 0.0
                if agent_result.get('before'):
                    before_score = agent_result['before']['metrics'].get(
                        'distillation_quality_score', 0)
                if agent_result.get('after'):
                    after_score = agent_result['after']['metrics'].get(
                        'distillation_quality_score', 0)

                agent_result['improvement'] = {
                    'absolute': round(after_score - before_score, 4),
                    'relative': round(
                        (after_score - before_score) / before_score, 4
                    ) if before_score > 0 else (
                        1.0 if after_score > 0 else 0.0
                    ),
                    'before_score': round(before_score, 4),
                    'after_score': round(after_score, 4),
                }

                # Teacher GT 示例
                agent_result['teacher_gt_samples'] = t_outs[:5]

                all_agent_results[agent_id] = agent_result

                if log_callback:
                    imp = agent_result['improvement']
                    log_callback(
                        f"  [{agent_id}] Before={imp['before_score']:.2%} "
                        f"→ After={imp['after_score']:.2%} "
                        f"(Δ{imp['absolute']:+.2%})"
                    )

            # ── 汇总 ──
            before_scores = [
                r['improvement']['before_score']
                for r in all_agent_results.values()
            ]
            after_scores = [
                r['improvement']['after_score']
                for r in all_agent_results.values()
            ]
            improvements = [
                r['improvement']['absolute']
                for r in all_agent_results.values()
            ]

            avg_before = sum(before_scores) / len(before_scores) if before_scores else 0
            avg_after = sum(after_scores) / len(after_scores) if after_scores else 0
            avg_improvement = sum(improvements) / len(improvements) if improvements else 0

            report['agent_results'] = all_agent_results
            report['summary'] = {
                'avg_before_score': round(avg_before, 4),
                'avg_after_score': round(avg_after, 4),
                'avg_improvement': round(avg_improvement, 4),
                'agents_evaluated': len(all_agent_results),
                'quality_grade': self.evaluator._compute_quality_grade(avg_after),
                'best_agent': max(
                    all_agent_results.keys(),
                    key=lambda a: all_agent_results[a]['improvement']['after_score']
                ) if all_agent_results else None,
                'most_improved_agent': max(
                    all_agent_results.keys(),
                    key=lambda a: all_agent_results[a]['improvement']['absolute']
                ) if all_agent_results else None,
            }
            report['status'] = 'completed'

            if log_callback:
                log_callback(f"\n{'=' * 60}")
                log_callback(f"验证完成")
                log_callback(f"  基座模型平均得分: {avg_before:.2%}")
                log_callback(f"  微调模型平均得分: {avg_after:.2%}")
                log_callback(f"  平均提升幅度: {avg_improvement:+.2%}")
                log_callback(f"  质量等级: {report['summary']['quality_grade']}")
                log_callback(f"{'=' * 60}")

        except Exception as e:
            report['status'] = 'failed'
            report['error'] = str(e)
            report['traceback'] = traceback.format_exc()
            if log_callback:
                log_callback(f"验证失败: {str(e)}")

        # 保存报告
        report_file = self.evaluator.save_report(
            report, f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        report['report_file'] = report_file

        return report

    # ──────────────── 辅助方法 ────────────────

    def _extract_teacher_gt(
        self, config_json: List[Dict], dataset_file: str
    ) -> Dict[str, List[str]]:
        """从数据集提取教师 GT"""
        teacher_outputs: Dict[str, List[str]] = {}

        if not os.path.exists(dataset_file):
            return teacher_outputs

        samples = []
        with open(dataset_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    samples.append(json.loads(line))

        for agent in config_json:
            agent_id = agent.get('agent_id', '')
            training = agent.get('training', {})
            gt_config = training.get('ground_truth', {})
            gt_key = gt_config.get('gt_key', '')

            if not gt_key:
                continue

            outputs = []
            for sample in samples:
                # 支持嵌套 input.xxx 格式
                val = sample.get(gt_key)
                if val is None:
                    # 尝试从 input 嵌套中获取
                    inp = sample.get('input', {})
                    if isinstance(inp, dict):
                        val = inp.get(gt_key)
                if val is not None:
                    outputs.append(str(val))
                else:
                    outputs.append('')

            teacher_outputs[agent_id] = outputs

        return teacher_outputs

    async def _run_model_inference(
        self,
        config_json: List[Dict],
        dataset_file: str,
        model_path: str,
        model_label: str,
        teacher_outputs: Dict[str, List[str]],
        log_callback: callable = None
    ) -> tuple:
        """加载模型并对数据集执行推理"""
        outputs: Dict[str, List[str]] = {}
        success = False

        try:
            # 在线程池中加载模型以避免阻塞
            loop = asyncio.get_event_loop()
            model, tokenizer = await loop.run_in_executor(
                None, self._load_model, model_path
            )
            if model is None:
                if log_callback:
                    log_callback(f"  无法加载模型 {model_path}")
                return outputs, False

            if log_callback:
                log_callback(f"  模型加载成功: {model_path}")

            # 加载数据集
            samples = []
            with open(dataset_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        samples.append(json.loads(line))

            # 对每个 trainable agent 执行推理
            for agent in config_json:
                training = agent.get('training', {})
                if not (training.get('trainable') and training.get('mode') == 'sft'):
                    continue

                agent_id = agent.get('agent_id', '')
                prompt_template = agent.get('instruction_prompt', {}).get(
                    'prompt_template', ''
                )
                instruction = agent.get('instruction_prompt', {}).get(
                    'instruction', ''
                )

                if not prompt_template:
                    continue

                agent_outputs = []
                template = Template(prompt_template)

                for sample in samples:
                    # 构建渲染上下文
                    context = self._build_render_context(
                        agent, sample, teacher_outputs
                    )
                    try:
                        rendered = template.render(**context)
                    except Exception:
                        rendered = prompt_template

                    # 拼接 system instruction + rendered prompt
                    full_prompt = f"{instruction}\n\n{rendered}" if instruction else rendered

                    # 推理
                    response = await loop.run_in_executor(
                        None,
                        self._model_generate,
                        model, tokenizer, full_prompt
                    )
                    agent_outputs.append(response)

                outputs[agent_id] = agent_outputs
                if log_callback:
                    log_callback(f"  [{agent_id}] 推理完成: {len(agent_outputs)} 条")

            success = True

            # 清理模型
            await loop.run_in_executor(None, self._clear_model, model, tokenizer)

        except Exception as e:
            if log_callback:
                log_callback(f"  {model_label} 推理失败: {str(e)}")

        return outputs, success

    async def _run_lora_inference(
        self,
        agent_id: str,
        base_model_path: str,
        checkpoint_path: str,
        config_json: List[Dict],
        dataset_file: str,
        teacher_outputs: Dict[str, List[str]],
        output_dict: Dict[str, List[str]],
        log_callback: callable = None
    ) -> bool:
        """加载 LoRA 适配器并推理单个 agent"""
        try:
            loop = asyncio.get_event_loop()

            model, tokenizer = await loop.run_in_executor(
                None,
                self._load_lora_model,
                base_model_path, checkpoint_path
            )
            if model is None:
                return False

            if log_callback:
                log_callback(f"  [{agent_id}] LoRA 模型加载成功: {checkpoint_path}")

            # 加载数据集
            samples = []
            with open(dataset_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        samples.append(json.loads(line))

            # 找到 agent 配置
            agent_cfg = self._find_agent_config(config_json, agent_id)
            if not agent_cfg:
                return False

            prompt_template = agent_cfg.get('instruction_prompt', {}).get(
                'prompt_template', ''
            )
            instruction = agent_cfg.get('instruction_prompt', {}).get(
                'instruction', ''
            )

            if not prompt_template:
                return False

            agent_outputs = []
            template = Template(prompt_template)

            for sample in samples:
                context = self._build_render_context(
                    agent_cfg, sample, teacher_outputs
                )
                try:
                    rendered = template.render(**context)
                except Exception:
                    rendered = prompt_template

                full_prompt = f"{instruction}\n\n{rendered}" if instruction else rendered

                response = await loop.run_in_executor(
                    None,
                    self._model_generate,
                    model, tokenizer, full_prompt
                )
                agent_outputs.append(response)

            output_dict[agent_id] = agent_outputs
            if log_callback:
                log_callback(
                    f"  [{agent_id}] LoRA 推理完成: {len(agent_outputs)} 条"
                )

            # 清理
            await loop.run_in_executor(None, self._clear_model, model, tokenizer)
            return True

        except Exception as e:
            if log_callback:
                log_callback(f"  [{agent_id}] LoRA 推理失败: {str(e)}")
            return False

    def _build_render_context(
        self,
        agent_config: Dict,
        sample: Dict,
        teacher_outputs: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """为 prompt 模板构建渲染上下文"""
        input_mappings = agent_config.get('input', [])
        input_dict = {}

        for mapping in input_mappings:
            key = mapping.get('key', '')
            from_agent = mapping.get('from', 'user')

            if from_agent == 'user':
                # 从数据集获取
                val = sample.get(key)
                if val is None:
                    inp = sample.get('input', {})
                    if isinstance(inp, dict):
                        val = inp.get(key)
                input_dict[key] = str(val) if val is not None else ''
            else:
                # 从 teacher GT 获取前置 agent 的输出
                gt_list = teacher_outputs.get(from_agent, [])
                # 使用 sample index 对应的 GT
                sample_idx = sample.get('sample_index', 0)
                if isinstance(sample_idx, int) and sample_idx < len(gt_list):
                    input_dict[key] = gt_list[sample_idx]
                else:
                    input_dict[key] = ''

        return {'input': input_dict}

    def _find_agent_config(
        self, config_json: List[Dict], agent_id: str
    ) -> Optional[Dict]:
        for agent in config_json:
            if agent.get('agent_id') == agent_id:
                return agent
        return None

    def _find_checkpoint(self, output_dir: str) -> Optional[str]:
        """在训练输出目录中查找最新的 checkpoint
        
        Args:
            output_dir: 可能是 checkpoint 目录本身，也可能是其父目录
        Returns:
            checkpoint 路径，未找到返回 None
        """
        if not output_dir or not os.path.exists(output_dir):
            return None
        
        # 情况1：output_dir 本身就是 checkpoint 目录（包含 adapter_config.json 或 config.json）
        if os.path.exists(os.path.join(output_dir, 'adapter_config.json')) or \
           os.path.exists(os.path.join(output_dir, 'config.json')):
            return output_dir
        
        # 情况2：在 output_dir 的子目录中查找 checkpoint-*
        search_dirs = [output_dir]

        # 查找 v0-*, v1-* 等子目录
        for d in os.listdir(output_dir):
            full = os.path.join(output_dir, d)
            if os.path.isdir(full) and d.startswith('v'):
                search_dirs.append(full)

        for search_dir in sorted(search_dirs, reverse=True):
            checkpoints = sorted(
                [d for d in os.listdir(search_dir)
                 if d.startswith('checkpoint-') and
                 os.path.isdir(os.path.join(search_dir, d))],
                key=lambda x: int(x.split('-')[1]) if '-' in x else 0,
                reverse=True
            )
            if checkpoints:
                cp = os.path.join(search_dir, checkpoints[0])
                # 确认有 adapter 文件
                if os.path.exists(os.path.join(cp, 'adapter_config.json')):
                    return cp
                # 或者检查是否是完整模型（有 config.json）
                if os.path.exists(os.path.join(cp, 'config.json')):
                    return cp

        return None

    # ──────────────── 模型加载/推理工具 ────────────────

    def _load_model(self, model_path: str):
        """加载模型和 tokenizer"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32

            tokenizer = AutoTokenizer.from_pretrained(
                model_path, trust_remote_code=True, padding_side="left"
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=dtype,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True
            )
            if device == "cpu":
                model = model.to(device)

            return model, tokenizer
        except Exception as e:
            print(f"模型加载失败 [{model_path}]: {e}")
            return None, None

    def _load_lora_model(self, base_model_path: str, checkpoint_path: str):
        """加载 LoRA 适配器模型"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32

            tokenizer = AutoTokenizer.from_pretrained(
                base_model_path, trust_remote_code=True, padding_side="left"
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # 检查是否是 LoRA（有 adapter_config.json）
            has_adapter = os.path.exists(
                os.path.join(checkpoint_path, 'adapter_config.json')
            )

            if has_adapter:
                try:
                    from peft import PeftModel
                    base_model = AutoModelForCausalLM.from_pretrained(
                        base_model_path,
                        torch_dtype=dtype,
                        device_map="auto" if device == "cuda" else None,
                        trust_remote_code=True
                    )
                    model = PeftModel.from_pretrained(
                        base_model, checkpoint_path
                    )
                    model = model.merge_and_unload()
                except ImportError:
                    # 没有 peft，尝试直接用 transformers
                    model = AutoModelForCausalLM.from_pretrained(
                        checkpoint_path,
                        torch_dtype=dtype,
                        device_map="auto" if device == "cuda" else None,
                        trust_remote_code=True
                    )
            else:
                # 完整模型
                model = AutoModelForCausalLM.from_pretrained(
                    checkpoint_path,
                    torch_dtype=dtype,
                    device_map="auto" if device == "cuda" else None,
                    trust_remote_code=True
                )

            if device == "cpu":
                model = model.to(device)

            model.eval()
            return model, tokenizer

        except Exception as e:
            print(f"LoRA 模型加载失败 [{checkpoint_path}]: {e}")
            return None, None

    def _model_generate(
        self, model, tokenizer, prompt: str,
        max_tokens: int = 256, temperature: float = 0.1
    ) -> str:
        """使用模型生成文本"""
        try:
            import torch

            if hasattr(tokenizer, 'apply_chat_template'):
                messages = [
                    {"role": "system", "content": "你是一个有帮助的助手。"},
                    {"role": "user", "content": prompt}
                ]
                text = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            else:
                text = prompt

            inputs = tokenizer([text], return_tensors="pt")
            device = next(model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=max(temperature, 0.01),
                    do_sample=temperature > 0,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id
                )

            generated = outputs[0][inputs['input_ids'].shape[1]:]
            response = tokenizer.decode(generated, skip_special_tokens=True)
            return response.strip()

        except Exception as e:
            return f"[ERROR: {str(e)}]"

    def _clear_model(self, model, tokenizer):
        """清理模型释放显存"""
        try:
            import torch
            del model
            del tokenizer
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
